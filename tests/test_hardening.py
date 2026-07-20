from __future__ import annotations

import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

from lpos_engine.actions import ActionService
from lpos_engine.adapters import (
    AdapterRegistry,
    DeterministicModelAdapter,
    RecordingActionAdapter,
    SandboxedFileActionAdapter,
)
from lpos_engine.approvals import ApprovalService, IdentityVerifier
from lpos_engine.canonical import parse_timestamp, text_digest, utc_now
from lpos_engine.engine import LPOSRuntime, RuntimeConfig
from lpos_engine.errors import (
    ActionExecutionError,
    AdapterError,
    ConcurrencyError,
    PolicyViolation,
    ValidationError,
)
from lpos_engine.models import (
    ActionPlan,
    ActionStatus,
    EvidenceRecord,
    EvidenceStatus,
    MaterialitySignals,
    MessageIdentity,
    OperationResult,
    StandingOperationRun,
    TaskEnvelope,
    TaskStatus,
)
from lpos_engine.store import SQLiteStore

from support import RuntimeTestCase


class CanonicalHardeningTests(unittest.TestCase):
    def test_action_parameters_are_deep_copied_and_deeply_immutable(self):
        source = {
            "headers": {"x-request": "original"},
            "items": [{"name": "alpha"}],
        }
        plan = ActionPlan.create(
            action_id="ACT-DEEP",
            task_id="TASK-DEEP",
            kind="external_send",
            parameters=source,
            external=True,
            reversible=False,
            idempotency_key="deep-freeze",
        )
        original_hash = plan.action_hash

        source["headers"]["x-request"] = "mutated"
        source["items"][0]["name"] = "mutated"

        self.assertEqual(plan.parameters["headers"]["x-request"], "original")
        self.assertEqual(plan.parameters["items"][0]["name"], "alpha")
        self.assertEqual(plan.action_hash, original_hash)
        with self.assertRaises(TypeError):
            plan.parameters["headers"]["x-request"] = "tampered"
        with self.assertRaises(TypeError):
            plan.parameters["items"][0]["name"] = "tampered"

    def test_naive_timestamp_is_rejected(self):
        with self.assertRaises(ValidationError):
            parse_timestamp("2026-07-20T12:00:00")

    def test_nonfinite_json_number_is_rejected_before_hashing(self):
        with self.assertRaises(ValidationError):
            ActionPlan.create(
                action_id="ACT-NAN",
                task_id="TASK-NAN",
                kind="external_send",
                parameters={"value": float("nan")},
                external=True,
                reversible=False,
                idempotency_key="nan",
            )


class AdapterHardeningTests(unittest.TestCase):
    def test_partial_capability_substitution_is_not_silent(self):
        adapter = DeterministicModelAdapter(
            "partial",
            capabilities=frozenset({"testing"}),
        )
        registry = AdapterRegistry(model_adapters=(adapter,))
        with self.assertRaises(AdapterError):
            registry.select_model(
                model_class="executive",
                required_capabilities=("testing", "security_review"),
                purpose="creation",
            )

    def test_locality_requirement_rejects_remote_only_adapter(self):
        adapter = DeterministicModelAdapter("remote", local=False)
        registry = AdapterRegistry(model_adapters=(adapter,))
        with self.assertRaises(AdapterError):
            registry.select_model(
                model_class="executive",
                required_capabilities=("testing",),
                purpose="creation",
                require_local=True,
            )


class ActionTransactionHardeningTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.store = SQLiteStore(self.root / "state.db")
        self.store.create_task(
            TaskEnvelope(
                task_id="TASK-ACTION",
                principal_instruction="Perform the exact action",
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
        self.recording = RecordingActionAdapter()
        self.files = SandboxedFileActionAdapter(self.root / "files")
        self.actions = ActionService(
            self.store,
            AdapterRegistry(action_adapters=(self.recording, self.files)),
            self.approvals,
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    @staticmethod
    def message(message_id: str = "grant-message") -> MessageIdentity:
        return MessageIdentity(
            channel="email",
            provider="test",
            message_id=message_id,
            thread_id="thread",
            sender="principal@example.com",
        )

    def approved_external_action(self):
        plan, request = self.actions.plan(
            task_id="TASK-ACTION",
            kind="external_send",
            parameters={"to": "customer@example.com", "body": "hello"},
            external=True,
            reversible=False,
            idempotency_key="atomic-approval",
        )
        grant = self.approvals.grant(
            request=request,
            message_identity=self.message(),
            verified_identity="principal@example.com",
        )
        return plan, grant

    def consumed_at(self, grant_id: str) -> str | None:
        with self.store.connection() as conn:
            row = conn.execute(
                "SELECT consumed_at FROM approval_grants WHERE grant_id = ?",
                (grant_id,),
            ).fetchone()
        return None if row is None else row["consumed_at"]

    def test_stale_execution_claim_does_not_consume_approval(self):
        plan, grant = self.approved_external_action()
        state = self.store.get_action(plan.action_id)
        self.assertEqual(state["status"], ActionStatus.APPROVED)
        self.assertEqual(state["version"], 1)

        with self.assertRaises(ConcurrencyError):
            self.store.claim_action_execution(
                plan.action_id,
                expected_version=0,
                grant_id=grant.grant_id,
            )

        self.assertIsNone(self.consumed_at(grant.grant_id))
        self.assertEqual(self.store.get_action(plan.action_id)["status"], ActionStatus.APPROVED)

        result = self.actions.apply(plan.action_id)
        self.assertTrue(result.success)
        self.assertIsNotNone(self.consumed_at(grant.grant_id))
        self.assertEqual(len(self.recording.applied), 1)

    def test_grant_and_execution_transitions_are_visible_in_audit_stream(self):
        plan, _ = self.approved_external_action()
        self.actions.apply(plan.action_id)
        transitions = [
            event["payload"]
            for event in self.store.list_events(stream_type="action", stream_id=plan.action_id)
            if event["event_type"] == "action.status_changed"
        ]
        self.assertIn({"from": "approved", "to": "executing", "result": None, "version": 2}, transitions)
        self.assertEqual(self.store.get_action(plan.action_id)["status"], ActionStatus.SUCCEEDED)

    def test_failed_action_is_terminal_and_not_reexecuted(self):
        plan, _ = self.actions.plan(
            task_id="TASK-ACTION",
            kind="filesystem_write",
            parameters={"path": "../escape.txt", "content": "blocked"},
            external=False,
            reversible=True,
            idempotency_key="terminal-failure",
        )
        with self.assertRaises(ActionExecutionError):
            self.actions.apply(plan.action_id)
        event_count = len(self.store.list_events(stream_type="action", stream_id=plan.action_id))
        with self.assertRaises(PolicyViolation):
            self.actions.apply(plan.action_id)
        self.assertEqual(
            len(self.store.list_events(stream_type="action", stream_id=plan.action_id)),
            event_count,
        )

    def test_file_adapter_requires_safe_overwrite_contract(self):
        target = self.root / "files" / "existing.txt"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("baseline", encoding="utf-8")

        no_guard, _ = self.actions.plan(
            task_id="TASK-ACTION",
            kind="filesystem_write",
            parameters={"path": "existing.txt", "content": "changed"},
            external=False,
            reversible=True,
            idempotency_key="overwrite-no-guard",
        )
        with self.assertRaises(ActionExecutionError):
            self.actions.apply(no_guard.action_id)
        self.assertEqual(target.read_text(encoding="utf-8"), "baseline")

        guarded, _ = self.actions.plan(
            task_id="TASK-ACTION",
            kind="filesystem_write",
            parameters={
                "path": "existing.txt",
                "content": "changed",
                "expected_sha256": text_digest("baseline"),
            },
            external=False,
            reversible=True,
            idempotency_key="overwrite-guarded",
        )
        result = self.actions.apply(guarded.action_id)
        self.assertTrue(result.success)
        self.assertEqual(target.read_text(encoding="utf-8"), "changed")

    def test_file_adapter_rejects_absolute_path_and_checksum_for_missing_file(self):
        absolute, _ = self.actions.plan(
            task_id="TASK-ACTION",
            kind="filesystem_write",
            parameters={"path": str(self.root / "outside.txt"), "content": "blocked"},
            external=False,
            reversible=True,
            idempotency_key="absolute-path",
        )
        with self.assertRaises(ActionExecutionError):
            self.actions.apply(absolute.action_id)

        missing, _ = self.actions.plan(
            task_id="TASK-ACTION",
            kind="filesystem_write",
            parameters={
                "path": "missing.txt",
                "content": "blocked",
                "expected_sha256": "0" * 64,
            },
            external=False,
            reversible=True,
            idempotency_key="missing-baseline",
        )
        with self.assertRaises(ActionExecutionError):
            self.actions.apply(missing.action_id)
        self.assertFalse((self.root / "files" / "missing.txt").exists())


class RuntimeBindingHardeningTests(RuntimeTestCase):
    def submit_material(self):
        task = self.runtime.submit_task(
            "Build a durable runtime artifact",
            required_capabilities=("software_architecture", "testing"),
            materiality_signals=MaterialitySignals(modifies_long_lived_specification=True),
        )
        contract = self.runtime.record_interpretation(
            task.task_id,
            instruction_verbatim=task.principal_instruction,
            interpretation="Build only the requested durable runtime artifact",
            invariants=("Preserve Principal authority",),
            verification_plan=("Run deterministic tests",),
            spec_ref="SPEC-1",
        )
        spec = self.runtime.record_artifact_spec(
            task.task_id,
            invariants=("Preserve Principal authority",),
        )
        return task, contract, spec

    def test_creation_and_review_contexts_are_persisted_by_hash(self):
        task, _, spec = self.submit_material()
        artifact = self.runtime.create_artifact(task.task_id, artifact_specification=spec)
        creation = self.runtime.store.get_context_bundle(artifact.context_bundle_id)
        self.assertIsNotNone(creation)
        self.assertEqual(creation.bundle_hash, artifact.context_bundle_hash)
        self.assertEqual(creation.purpose, "creation")

        self.runtime.review_latest_artifact(
            task.task_id,
            intended_outcome="A verified runtime artifact",
            auto_complete=False,
        )
        review = self.runtime.store.get_latest_review(task.task_id, artifact.content_hash)
        review_context = self.runtime.store.get_context_bundle(review["review_context_id"])
        self.assertIsNotNone(review_context)
        self.assertEqual(review_context.purpose, "review")
        self.assertNotEqual(review_context.bundle_id, creation.bundle_id)
        self.assertNotIn("# LPOS Creation Context", review_context.content)

    def test_specification_change_invalidates_existing_artifact_for_review(self):
        task, _, spec = self.submit_material()
        self.runtime.create_artifact(task.task_id, artifact_specification=spec)
        self.runtime.record_artifact_spec(
            task.task_id,
            artifact_id=spec.artifact_id,
            invariants=("A different invariant",),
            history=("Changed after artifact creation",),
        )
        with self.assertRaises(PolicyViolation):
            self.runtime.review_latest_artifact(
                task.task_id,
                intended_outcome="A verified runtime artifact",
                auto_complete=False,
            )

    def test_contract_change_is_blocked_during_execution(self):
        task, _, spec = self.submit_material()
        self.runtime.create_artifact(task.task_id, artifact_specification=spec)
        self.assertEqual(self.runtime.store.get_task(task.task_id)["status"], TaskStatus.EXECUTING)
        with self.assertRaises(PolicyViolation):
            self.runtime.record_interpretation(
                task.task_id,
                instruction_verbatim=task.principal_instruction,
                interpretation="Mutated after execution",
                invariants=(),
                verification_plan=("test",),
                spec_ref="SPEC-2",
            )

    def test_duplicate_completion_does_not_create_orphan_evidence(self):
        task = self.runtime.submit_task(
            "Draft an internal note",
            required_capabilities=("writing",),
        )
        self.runtime.create_artifact(task.task_id)
        self.runtime.complete_task(task.task_id, result_summary="Draft completed")
        before = len(self.runtime.store.list_evidence(task.task_id))
        with self.assertRaises(PolicyViolation):
            self.runtime.complete_task(task.task_id, result_summary="Duplicate completion")
        self.assertEqual(len(self.runtime.store.list_evidence(task.task_id)), before)

    def test_terminal_task_rejects_contract_and_spec_mutation(self):
        task = self.runtime.submit_task(
            "Draft an internal note",
            required_capabilities=("writing",),
        )
        self.runtime.create_artifact(task.task_id)
        self.runtime.complete_task(task.task_id, result_summary="Draft completed")
        with self.assertRaises(PolicyViolation):
            self.runtime.record_interpretation(
                task.task_id,
                instruction_verbatim=task.principal_instruction,
                interpretation="late mutation",
                invariants=(),
                verification_plan=("test",),
                spec_ref=None,
            )
        with self.assertRaises(PolicyViolation):
            self.runtime.record_artifact_spec(task.task_id)

    def test_runtime_retry_reuses_waiting_action_and_blocks_a_second_action(self):
        task, _, spec = self.submit_material()
        self.runtime.create_artifact(task.task_id, artifact_specification=spec)
        first_plan, first_request = self.runtime.plan_action(
            task.task_id,
            kind="external_send",
            parameters={"to": "customer@example.com", "body": "exact"},
            external=True,
            reversible=False,
            idempotency_key="runtime-waiting",
        )
        second_plan, second_request = self.runtime.plan_action(
            task.task_id,
            kind="external_send",
            parameters={"to": "customer@example.com", "body": "exact"},
            external=True,
            reversible=False,
            idempotency_key="runtime-waiting",
        )
        self.assertEqual(second_plan.action_id, first_plan.action_id)
        self.assertEqual(second_request.question_id, first_request.question_id)
        with self.assertRaises(PolicyViolation):
            self.runtime.plan_action(
                task.task_id,
                kind="external_send",
                parameters={"to": "other@example.com", "body": "different"},
                external=True,
                reversible=False,
                idempotency_key="second-action",
            )


class OperationLeaseHardeningTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.store = SQLiteStore(Path(self.temp.name) / "state.db")

    def tearDown(self) -> None:
        self.temp.cleanup()

    @staticmethod
    def evidence(evidence_id: str) -> EvidenceRecord:
        return EvidenceRecord(
            id=evidence_id,
            recommendation="Record the operation",
            owner="LPOS Engine",
            expected_outcome="One owner completes",
            baseline="A claim exists",
            target="Only the active owner can finalize",
            observed="Attempted finalization",
            confidence=1.0,
            measurement="transactional claim ownership",
            fallback_used=False,
            review_date=None,
            status=EvidenceStatus.MEASURED,
        )

    def test_stale_claim_can_be_reclaimed_and_old_worker_cannot_finalize(self):
        key = "SO-21:2026-07-20T12:00:00Z"
        self.store.claim_operation(
            so_id="SO-21",
            run_id="RUN-OLD",
            idempotency_key=key,
            lease_seconds=1,
        )
        old_claim_time = (datetime.now(UTC) - timedelta(minutes=5)).isoformat().replace("+00:00", "Z")
        with self.store.transaction() as conn:
            conn.execute(
                "UPDATE operation_claims SET claimed_at = ? WHERE idempotency_key = ?",
                (old_claim_time, key),
            )
        self.store.claim_operation(
            so_id="SO-21",
            run_id="RUN-NEW",
            idempotency_key=key,
            lease_seconds=1,
        )

        old_evidence = self.evidence("EVID-OLD")
        old_run = StandingOperationRun(
            so_id="SO-21",
            run_id="RUN-OLD",
            idempotency_key=key,
            started_at=old_claim_time,
            finished_at=utc_now(),
            result=OperationResult.OK,
            outputs_ref="sha256:" + "0" * 64,
            evidence_id=old_evidence.id,
            fallback_used=False,
            model_class="routine",
        )
        before = len(self.store.list_evidence())
        with self.assertRaises(ConcurrencyError):
            self.store.save_operation_run(old_run, evidence=old_evidence)
        self.assertEqual(len(self.store.list_evidence()), before)

        new_evidence = self.evidence("EVID-NEW")
        new_run = StandingOperationRun(
            so_id="SO-21",
            run_id="RUN-NEW",
            idempotency_key=key,
            started_at=utc_now(),
            finished_at=utc_now(),
            result=OperationResult.OK,
            outputs_ref="sha256:" + "1" * 64,
            evidence_id=new_evidence.id,
            fallback_used=False,
            model_class="routine",
        )
        persisted = self.store.save_operation_run(new_run, evidence=new_evidence)
        self.assertEqual(persisted.run_id, "RUN-NEW")
        self.assertEqual([item.id for item in self.store.list_evidence()], ["EVID-NEW"])

class EnvelopeImmutabilityTests(unittest.TestCase):
    def test_contract_sequences_are_copied_into_tuples(self):
        from lpos_engine.models import ConflictRecord, InterpretationContract

        invariants = ["preserve authority"]
        conflicts = [
            ConflictRecord(
                levels=["instruction", "specification"],
                description="A recorded conflict",
                resolution="precedence",
            )
        ]
        plan = ["run tests"]
        contract = InterpretationContract(
            task_id="TASK-IMMUTABLE",
            instruction_verbatim="Do it",
            interpretation="Do it exactly",
            invariants=invariants,
            conflicts=conflicts,
            verification_plan=plan,
            spec_ref=None,
        )
        invariants.append("late mutation")
        conflicts.clear()
        plan.append("late mutation")
        self.assertEqual(contract.invariants, ("preserve authority",))
        self.assertEqual(len(contract.conflicts), 1)
        self.assertEqual(contract.verification_plan, ("run tests",))
        self.assertIsInstance(contract.conflicts[0].levels, tuple)

    def test_completion_action_summaries_are_deeply_immutable(self):
        from lpos_engine.models import CompletionReport

        source = [{"action_id": "ACT-1", "detail": {"status": "succeeded"}}]
        report = CompletionReport(
            task_id="TASK-IMMUTABLE",
            status=TaskStatus.COMPLETED,
            result_summary="Done",
            artifact_id=None,
            artifact_hash=None,
            material=False,
            review_decision=None,
            review_isolated=None,
            actions=source,
            evidence_ids=(),
            decision_ids=(),
            limitations=(),
        )
        source[0]["detail"]["status"] = "tampered"
        self.assertEqual(report.actions[0]["detail"]["status"], "succeeded")
        with self.assertRaises(TypeError):
            report.actions[0]["detail"]["status"] = "tampered"


class DistributionIntegrityTests(unittest.TestCase):
    def test_human_readable_and_packaged_schemas_are_identical(self):
        runtime_root = Path(__file__).resolve().parents[1]
        public = runtime_root / "schemas"
        packaged = runtime_root / "src" / "lpos_engine" / "schemas"
        public_files = {path.name: path.read_bytes() for path in public.glob("*.schema.json")}
        packaged_files = {path.name: path.read_bytes() for path in packaged.glob("*.schema.json")}
        self.assertEqual(packaged_files, public_files)

    def test_human_readable_and_packaged_registry_are_identical(self):
        runtime_root = Path(__file__).resolve().parents[1]
        public = runtime_root / "config" / "default_registry.json"
        packaged = runtime_root / "src" / "lpos_engine" / "config" / "default_registry.json"
        self.assertEqual(packaged.read_bytes(), public.read_bytes())

    def test_package_version_matches_pyproject(self):
        import tomllib
        import lpos_engine

        runtime_root = Path(__file__).resolve().parents[1]
        project = tomllib.loads((runtime_root / "pyproject.toml").read_text(encoding="utf-8"))
        self.assertEqual(project["project"]["version"], lpos_engine.__version__)


class StoreMigrationAndBindingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.db = self.root / "state.db"
        self.store = SQLiteStore(self.db)

    def tearDown(self) -> None:
        self.temp.cleanup()

    @staticmethod
    def task(task_id: str) -> TaskEnvelope:
        return TaskEnvelope(
            task_id=task_id,
            principal_instruction="Build an artifact",
            lead_guild="Engineering",
            lead_specialist="PROFILE-ENGINEERING",
            required_capabilities=("testing",),
            material=False,
            materiality_basis=("routine_internal_reversible",),
        )

    def test_migration_is_recorded_and_database_passes_integrity_check(self):
        migrations = self.store.list_migrations()
        self.assertEqual([item["migration_name"] for item in migrations], ["001_initial.sql"])
        self.assertEqual(len(migrations[0]["checksum"]), 64)
        self.assertEqual(self.store.integrity_check(), "ok")
        reopened = SQLiteStore(self.db)
        self.assertEqual(reopened.list_migrations(), migrations)

    def test_changed_applied_migration_checksum_is_rejected(self):
        with self.store.transaction() as conn:
            conn.execute(
                "UPDATE schema_migrations SET checksum = ? WHERE migration_name = ?",
                ("0" * 64, "001_initial.sql"),
            )
        with self.assertRaises(ValidationError):
            SQLiteStore(self.db)

    def test_artifact_specification_cannot_be_rebound_to_another_task(self):
        from lpos_engine.models import ArtifactSpecification

        self.store.create_task(self.task("TASK-A"))
        self.store.create_task(self.task("TASK-B"))
        spec = ArtifactSpecification(artifact_id="ART-SHARED")
        self.store.save_artifact_spec("TASK-A", spec)
        with self.assertRaises(ConcurrencyError):
            self.store.save_artifact_spec("TASK-B", spec)

    def test_artifact_identity_cannot_be_rebound_to_another_task(self):
        from lpos_engine.models import Artifact

        self.store.create_task(self.task("TASK-A"))
        self.store.create_task(self.task("TASK-B"))
        self.store.save_artifact(
            Artifact.create(
                artifact_id="ART-SHARED",
                task_id="TASK-A",
                media_type="text/plain",
                content="first",
            )
        )
        with self.assertRaises(ConcurrencyError):
            self.store.save_artifact(
                Artifact.create(
                    artifact_id="ART-SHARED",
                    task_id="TASK-B",
                    media_type="text/plain",
                    content="second",
                )
            )
