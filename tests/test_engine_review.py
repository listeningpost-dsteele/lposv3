from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from lpos_engine.adapters import AdapterRegistry, DeterministicModelAdapter, RecordingActionAdapter
from lpos_engine.engine import LPOSRuntime, RuntimeConfig
from lpos_engine.errors import AdapterError, PolicyViolation
from lpos_engine.models import MaterialitySignals, MessageIdentity, ReviewDecision, TaskStatus

from support import RuntimeTestCase


class EngineReviewTests(RuntimeTestCase):
    def submit_material(self):
        return self.runtime.submit_task(
            "Build the runtime",
            required_capabilities=("software_architecture", "testing"),
            materiality_signals=MaterialitySignals(modifies_long_lived_specification=True),
        )

    def interpret_and_spec(self, task):
        self.runtime.record_interpretation(
            task.task_id,
            instruction_verbatim=task.principal_instruction,
            interpretation="Build a tested runtime and nothing else",
            invariants=("Preserve canonical LPOS identifiers",),
            verification_plan=("Run tests",),
            spec_ref="SPEC-1",
        )
        return self.runtime.record_artifact_spec(
            task.task_id,
            invariants=("Preserve canonical LPOS identifiers",),
        )

    def test_material_execution_requires_contract(self):
        task = self.submit_material()
        spec = self.runtime.record_artifact_spec(task.task_id)
        with self.assertRaises(PolicyViolation):
            self.runtime.create_artifact(task.task_id, artifact_specification=spec)

    def test_material_execution_requires_artifact_spec(self):
        task = self.submit_material()
        self.runtime.record_interpretation(
            task.task_id,
            instruction_verbatim=task.principal_instruction,
            interpretation="Build it",
            invariants=(),
            verification_plan=("test",),
            spec_ref=None,
        )
        with self.assertRaises(PolicyViolation):
            self.runtime.create_artifact(task.task_id)

    def test_full_material_vertical_slice_completes(self):
        task = self.submit_material()
        spec = self.interpret_and_spec(task)
        artifact = self.runtime.create_artifact(task.task_id, artifact_specification=spec)
        review = self.runtime.review_latest_artifact(
            task.task_id,
            intended_outcome="A tested LPOS runtime",
        )
        self.assertEqual(review.decision, ReviewDecision.PASS)
        self.assertEqual(self.runtime.store.get_task(task.task_id)["status"], TaskStatus.COMPLETED)
        report = self.runtime.store.get_completion_report(task.task_id)
        self.assertEqual(report.artifact_hash, artifact.content_hash)
        self.assertTrue(report.review_isolated)
        self.assertNotEqual(self.creator.last_creation_context.bundle_id, self.reviewer.last_review_context.bundle_id)
        self.assertNotIn("# LPOS Creation Context", self.reviewer.last_review_context.content)

    def test_review_rejection_enters_correction_state(self):
        self.creator.artifact_factory = lambda task, context: "[[REJECT]] bad artifact"
        task = self.submit_material()
        spec = self.interpret_and_spec(task)
        self.runtime.create_artifact(task.task_id, artifact_specification=spec)
        review = self.runtime.review_latest_artifact(
            task.task_id,
            intended_outcome="A tested runtime",
            auto_complete=False,
        )
        self.assertEqual(review.decision, ReviewDecision.REJECT)
        self.assertEqual(
            self.runtime.store.get_task(task.task_id)["status"],
            TaskStatus.CORRECTION_REQUIRED,
        )
        with self.assertRaises(PolicyViolation):
            self.runtime.complete_task(task.task_id, result_summary="not done")

    def test_material_task_cannot_complete_without_review(self):
        task = self.submit_material()
        spec = self.interpret_and_spec(task)
        self.runtime.create_artifact(task.task_id, artifact_specification=spec)
        with self.assertRaises(PolicyViolation):
            self.runtime.complete_task(task.task_id, result_summary="not reviewed")

    def test_nonmaterial_task_can_complete_without_review(self):
        task = self.runtime.submit_task(
            "Draft an internal note",
            required_capabilities=("writing",),
        )
        artifact = self.runtime.create_artifact(task.task_id)
        report = self.runtime.complete_task(task.task_id, result_summary="Draft complete")
        self.assertFalse(report.material)
        self.assertIsNone(report.review_decision)
        self.assertEqual(report.artifact_hash, artifact.content_hash)

    def test_external_action_waits_for_exact_verified_approval(self):
        task = self.submit_material()
        spec = self.interpret_and_spec(task)
        self.runtime.create_artifact(task.task_id, artifact_specification=spec)
        plan, request = self.runtime.plan_action(
            task.task_id,
            kind="external_send",
            parameters={"to": "customer@example.com", "body": "ready"},
            external=True,
            reversible=False,
            idempotency_key="task-send",
        )
        self.assertEqual(self.runtime.store.get_task(task.task_id)["status"], TaskStatus.AWAITING_APPROVAL)
        self.runtime.grant_action_approval(
            request.question_id,
            message_identity=MessageIdentity(
                channel="email",
                provider="test",
                message_id="m1",
                thread_id="t1",
                sender="principal@example.com",
            ),
            verified_identity="principal@example.com",
        )
        self.runtime.apply_action(plan.action_id)
        self.assertEqual(self.runtime.store.get_task(task.task_id)["status"], TaskStatus.EXECUTING)
        self.assertEqual(len(self.action_adapter.applied), 1)

    def test_missing_route_capability_blocks_submission(self):
        with self.assertRaises(AdapterError):
            self.runtime.submit_task(
                "Provide licensed judgment",
                required_capabilities=("licensed_medical_judgment",),
            )
        self.assertEqual(self.runtime.store.list_events(stream_type="task"), [])

    def test_same_adapter_review_is_disclosed_but_context_isolated(self):
        with tempfile.TemporaryDirectory() as d:
            only = DeterministicModelAdapter("only")
            runtime = LPOSRuntime(
                RuntimeConfig(database_path=Path(d) / "state.db"),
                adapters=AdapterRegistry(
                    model_adapters=(only,),
                    action_adapters=(RecordingActionAdapter(),),
                ),
            )
            task = runtime.submit_task(
                "Material work",
                required_capabilities=("software_architecture",),
                materiality_signals=MaterialitySignals(modifies_long_lived_specification=True),
            )
            runtime.record_interpretation(
                task.task_id,
                instruction_verbatim=task.principal_instruction,
                interpretation="Material work",
                invariants=(),
                verification_plan=("review",),
                spec_ref="SPEC",
            )
            spec = runtime.record_artifact_spec(task.task_id)
            runtime.create_artifact(task.task_id, artifact_specification=spec)
            runtime.review_latest_artifact(task.task_id, intended_outcome="done")
            report = runtime.store.get_completion_report(task.task_id)
            self.assertTrue(any("same model adapter" in item for item in report.limitations))
            self.assertTrue(report.review_isolated)
