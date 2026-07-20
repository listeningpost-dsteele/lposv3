from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

from lpos_engine.actions import ActionService
from lpos_engine.adapters import AdapterRegistry, DeterministicModelAdapter, RecordingActionAdapter
from lpos_engine.adapters.subprocess_host import SubprocessModelAdapter
from lpos_engine.approvals import ApprovalService, IdentityVerifier
from lpos_engine.context import ContextCompiler, SpecRepository
from lpos_engine.engine import LPOSRuntime, RuntimeConfig
from lpos_engine.errors import AdapterError, ContextIsolationError, ValidationError
from lpos_engine.models import (
    ActionStatus,
    ArtifactSpecification,
    InterpretationContract,
    MaterialitySignals,
    MessageIdentity,
    OperationResult,
    ReviewDecision,
    ReviewResult,
    TaskEnvelope,
    TaskStatus,
    WorkflowDefinition,
    WorkflowStep,
)
from lpos_engine.operations import StandingOperationRunner
from lpos_engine.store import SQLiteStore


class MissingActionAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.store = SQLiteStore(self.root / "state.db")
        self.store.create_task(
            TaskEnvelope(
                task_id="TASK-MISSING-ADAPTER",
                principal_instruction="Apply only after approval",
                lead_guild="Operations",
                lead_specialist="PROFILE-OPERATIONS",
                required_capabilities=("operations",),
                material=False,
                materiality_basis=("routine_internal_reversible",),
            )
        )
        self.approvals = ApprovalService(
            self.store,
            IdentityVerifier({"email": ("principal@example.com",)}),
        )
        self.actions = ActionService(self.store, AdapterRegistry(), self.approvals)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_missing_executor_does_not_consume_grant_or_claim_action(self) -> None:
        plan, request = self.actions.plan(
            task_id="TASK-MISSING-ADAPTER",
            kind="external_send",
            parameters={"to": "customer@example.com", "body": "hello"},
            external=True,
            reversible=False,
            idempotency_key="missing-executor",
        )
        assert request is not None
        grant = self.approvals.grant(
            request=request,
            message_identity=MessageIdentity(
                channel="email",
                provider="test",
                message_id="approval-message",
                thread_id=request.question_id,
                sender="principal@example.com",
            ),
            verified_identity="principal@example.com",
        )

        with self.assertRaises(AdapterError):
            self.actions.apply(plan.action_id)

        state = self.store.get_action(plan.action_id)
        self.assertEqual(state["status"], ActionStatus.APPROVED)
        with self.store.connection() as connection:
            consumed = connection.execute(
                "SELECT consumed_at FROM approval_grants WHERE grant_id = ?",
                (grant.grant_id,),
            ).fetchone()["consumed_at"]
        self.assertIsNone(consumed)


class RegistryValidationTests(unittest.TestCase):
    def test_model_metadata_must_be_normalized_and_typed(self) -> None:
        malformed = DeterministicModelAdapter("malformed")
        malformed.capabilities = frozenset({"Security Review"})
        with self.assertRaises(ValidationError):
            AdapterRegistry(model_adapters=(malformed,))

        malformed = DeterministicModelAdapter("malformed")
        malformed.available = "yes"
        with self.assertRaises(ValidationError):
            AdapterRegistry(model_adapters=(malformed,))

        malformed = DeterministicModelAdapter("malformed")
        malformed.priority = True
        with self.assertRaises(ValidationError):
            AdapterRegistry(model_adapters=(malformed,))

    def test_action_metadata_rejects_string_kinds_and_duplicate_normalization(self) -> None:
        malformed = RecordingActionAdapter()
        malformed.kinds = "external_send"
        with self.assertRaises(ValidationError):
            AdapterRegistry(action_adapters=(malformed,))

        malformed = RecordingActionAdapter(kinds=frozenset({"external-send", "external_send"}))
        with self.assertRaises(ValidationError):
            AdapterRegistry(action_adapters=(malformed,))

    def test_strict_exclusion_never_reselects_failed_model(self) -> None:
        only = DeterministicModelAdapter("only")
        registry = AdapterRegistry(model_adapters=(only,))
        with self.assertRaises(AdapterError):
            registry.select_model(
                model_class="executive",
                required_capabilities=("testing",),
                purpose="creation",
                exclude_names=("only",),
                allow_excluded_fallback=False,
            )


class SubprocessBoundaryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.script = self.root / "host.py"
        self.script.write_text(
            """
import json
import sys
import time

mode = sys.argv[1]
request = json.load(sys.stdin)
if mode == "nonzero":
    print("provider failure", file=sys.stderr)
    raise SystemExit(7)
if mode == "invalid":
    print("not-json")
    raise SystemExit(0)
if mode == "array":
    print("[]")
    raise SystemExit(0)
if mode == "oversized":
    print(json.dumps({"content": "x" * 2000}))
    raise SystemExit(0)
if mode == "timeout":
    time.sleep(2)
    print(json.dumps({"content": "late"}))
    raise SystemExit(0)
print(json.dumps({
    "content": "ok",
    "media_type": "text/plain",
    "evidence": [],
    "assumptions": [],
    "adapter_metadata": {}
}))
""".strip(),
            encoding="utf-8",
        )
        self.task = TaskEnvelope(
            task_id="TASK-SUBPROCESS",
            principal_instruction="Create an artifact",
            lead_guild="Engineering",
            lead_specialist="PROFILE-ENGINEERING",
            required_capabilities=("software_architecture",),
            material=False,
            materiality_basis=("routine_internal_reversible",),
            creator_adapter="host",
        )
        contract = InterpretationContract(
            task_id=self.task.task_id,
            instruction_verbatim=self.task.principal_instruction,
            interpretation=self.task.principal_instruction,
            invariants=(),
            conflicts=(),
            verification_plan=("validate",),
            spec_ref=None,
        )
        self.context = ContextCompiler(SpecRepository(None)).compile_task(
            task=self.task,
            interpretation=contract,
            artifact_specification=ArtifactSpecification("ART-SUBPROCESS"),
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def adapter(self, mode: str, **overrides) -> SubprocessModelAdapter:
        arguments = {
            "model_classes": frozenset({"executive"}),
            "capabilities": frozenset({"Software Architecture"}),
            "timeout_seconds": 5,
            "max_stdout_bytes": 10_000,
        }
        arguments.update(overrides)
        return SubprocessModelAdapter(
            "host",
            (sys.executable, str(self.script), mode),
            **arguments,
        )

    def test_constructor_normalizes_capabilities_and_rejects_unsafe_values(self) -> None:
        adapter = self.adapter("ok")
        self.assertEqual(adapter.capabilities, frozenset({"software_architecture"}))
        for kwargs in (
            {"timeout_seconds": 0},
            {"max_stdout_bytes": 0},
            {"priority": -1},
            {"available": "yes"},
        ):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValidationError):
                self.adapter("ok", **kwargs)
        with self.assertRaises(ValidationError):
            SubprocessModelAdapter(
                "host",
                "python host.py",
                model_classes=frozenset({"executive"}),
                capabilities=frozenset(),
            )

    def test_protocol_errors_are_explicit(self) -> None:
        cases = {
            "nonzero": {},
            "invalid": {},
            "array": {},
            "oversized": {"max_stdout_bytes": 100},
            "timeout": {"timeout_seconds": 1},
        }
        for mode, overrides in cases.items():
            with self.subTest(mode=mode), self.assertRaises(AdapterError):
                self.adapter(mode, **overrides).create_artifact(self.task, self.context)


class ModelFallbackAndReviewBoundaryTests(unittest.TestCase):
    class FailingCreator(DeterministicModelAdapter):
        def create_artifact(self, task, context):
            self.last_creation_context = context
            raise AdapterError("primary provider unavailable")

    class UnattestedReviewer(DeterministicModelAdapter):
        def review(self, envelope, context):
            self.last_review_context = context
            return ReviewResult(
                decision=ReviewDecision.PASS,
                isolation="claimed fresh context without bundle identity",
                recomputed="nothing trustworthy",
            )

    def test_creator_failure_uses_capability_equivalent_fallback_and_records_decision(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            primary = self.FailingCreator("primary", priority=1)
            fallback = DeterministicModelAdapter("fallback", priority=2)
            runtime = LPOSRuntime(
                RuntimeConfig(database_path=Path(directory) / "state.db"),
                adapters=AdapterRegistry(model_adapters=(primary, fallback)),
            )
            task = runtime.submit_task(
                "Create a tested architecture note",
                required_capabilities=("software_architecture", "testing"),
            )
            artifact = runtime.create_artifact(task.task_id)

            self.assertEqual(task.creator_adapter, "primary")
            self.assertEqual(artifact.created_by_adapter, "fallback")
            self.assertEqual(
                primary.last_creation_context.bundle_id,
                fallback.last_creation_context.bundle_id,
            )
            decisions = runtime.store.list_decisions(task.task_id)
            self.assertEqual(len(decisions), 1)
            self.assertIn("fallback", decisions[0].decision.lower())

    def test_bad_review_context_attestation_is_rejected_and_not_persisted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            creator = DeterministicModelAdapter("creator", priority=1)
            reviewer = self.UnattestedReviewer(
                "reviewer",
                priority=1,
                supports_creation=False,
            )
            runtime = LPOSRuntime(
                RuntimeConfig(database_path=Path(directory) / "state.db"),
                adapters=AdapterRegistry(model_adapters=(creator, reviewer)),
            )
            task = runtime.submit_task(
                "Create material work",
                required_capabilities=("software_architecture",),
                materiality_signals=MaterialitySignals(
                    modifies_long_lived_specification=True
                ),
            )
            runtime.record_interpretation(
                task.task_id,
                instruction_verbatim=task.principal_instruction,
                interpretation="Create only the requested material work",
                invariants=("Preserve Principal authority",),
                verification_plan=("Run isolated review",),
                spec_ref="SPEC",
            )
            spec = runtime.record_artifact_spec(task.task_id)
            runtime.create_artifact(task.task_id, artifact_specification=spec)

            with self.assertRaises(ContextIsolationError):
                runtime.review_latest_artifact(task.task_id, intended_outcome="done")

            self.assertEqual(
                runtime.store.get_task(task.task_id)["status"],
                TaskStatus.REVIEWING,
            )
            self.assertIsNone(
                runtime.store.get_latest_review(
                    task.task_id,
                    runtime.store.get_latest_artifact(task.task_id).content_hash,
                )
            )


class ExampleModelHostEndToEndTests(unittest.TestCase):
    def test_example_host_completes_material_vertical_slice(self) -> None:
        runtime_root = Path(__file__).resolve().parents[1]
        host = SubprocessModelAdapter(
            "example-model-host",
            (sys.executable, str(runtime_root / "examples" / "example_model_host.py")),
            model_classes=frozenset({"executive", "review"}),
            capabilities=frozenset(
                {
                    "software_architecture",
                    "testing",
                    "independent_review",
                    "quality_assurance",
                }
            ),
        )
        with tempfile.TemporaryDirectory() as directory:
            runtime = LPOSRuntime(
                RuntimeConfig(database_path=Path(directory) / "state.db"),
                adapters=AdapterRegistry(model_adapters=(host,)),
            )
            task = runtime.submit_task(
                "Build a protocol integration artifact",
                required_capabilities=("software_architecture", "testing"),
                materiality_signals=MaterialitySignals(
                    modifies_long_lived_specification=True
                ),
            )
            runtime.record_interpretation(
                task.task_id,
                instruction_verbatim=task.principal_instruction,
                interpretation="Build only the protocol integration artifact.",
                invariants=("Use the exact persisted context.",),
                verification_plan=("Review in a fresh context.",),
                spec_ref="Runtime/examples/example_model_host.py",
            )
            spec = runtime.record_artifact_spec(task.task_id)
            artifact = runtime.create_artifact(
                task.task_id, artifact_specification=spec
            )
            review = runtime.review_latest_artifact(
                task.task_id,
                intended_outcome="A passing protocol integration artifact",
            )
            report = runtime.store.get_completion_report(task.task_id)

            self.assertEqual(artifact.created_by_adapter, "example-model-host")
            self.assertEqual(review.decision, ReviewDecision.PASS)
            self.assertEqual(report.status, TaskStatus.COMPLETED)
            self.assertTrue(report.review_isolated)



class WorkflowSerializationBoundaryTests(unittest.TestCase):
    def test_non_json_handler_output_becomes_a_persisted_error_run(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = SQLiteStore(Path(directory) / "state.db")
            runner = StandingOperationRunner(
                store,
                handlers={"bad": lambda context: {"opaque": object()}},
            )
            workflow = WorkflowDefinition(
                so_id="SO-NONJSON",
                model_class="routine",
                steps=(WorkflowStep("STEP-BAD", "bad"),),
            )
            execution = runner.run(workflow, scheduled_for="2026-07-20")
            self.assertEqual(execution.run.result, OperationResult.ERROR)
            self.assertIn("not JSON compatible", execution.outputs["__error__"]["error"])
            self.assertEqual(len(store.list_evidence()), 1)

    def test_workflow_outputs_are_recursively_immutable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = SQLiteStore(Path(directory) / "state.db")
            source = {"nested": {"value": "original"}}
            runner = StandingOperationRunner(
                store,
                handlers={"collect": lambda context: source},
            )
            workflow = WorkflowDefinition(
                so_id="SO-FROZEN",
                model_class="routine",
                steps=(WorkflowStep("STEP-COLLECT", "collect"),),
            )
            execution = runner.run(workflow, scheduled_for="2026-07-20")
            source["nested"]["value"] = "mutated"
            self.assertEqual(
                execution.outputs["STEP-COLLECT"]["nested"]["value"],
                "original",
            )
            with self.assertRaises(TypeError):
                execution.outputs["STEP-COLLECT"]["nested"]["value"] = "tampered"


if __name__ == "__main__":
    unittest.main()
