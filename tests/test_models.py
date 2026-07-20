from __future__ import annotations

import json
import unittest

from lpos_engine.canonical import canonical_json, digest, text_digest
from lpos_engine.errors import ValidationError
from lpos_engine.models import (
    ActionPlan,
    Artifact,
    CompletionReport,
    ConflictRecord,
    ReviewDecision,
    ReviewEnvelope,
    TaskEnvelope,
    TaskStatus,
    WorkflowDefinition,
    WorkflowStep,
)


class ModelTests(unittest.TestCase):
    def task(self, **overrides):
        values = dict(
            task_id="TASK-1",
            principal_instruction="Do the work",
            lead_guild="Engineering",
            lead_specialist="PROFILE-ENGINEERING",
            required_capabilities=("software_architecture",),
            material=False,
            materiality_basis=("routine_internal_reversible",),
        )
        values.update(overrides)
        return TaskEnvelope(**values)

    def test_canonical_hash_is_order_independent(self):
        self.assertEqual(digest({"a": 1, "b": 2}), digest({"b": 2, "a": 1}))

    def test_task_capabilities_are_normalized_and_deduplicated(self):
        task = self.task(required_capabilities=("Software Architecture", "software_architecture"))
        self.assertEqual(task.required_capabilities, ("software_architecture",))

    def test_material_task_requires_basis(self):
        with self.assertRaises(ValidationError):
            self.task(material=True, materiality_basis=())

    def test_invalid_model_class_rejected(self):
        with self.assertRaises(ValidationError):
            self.task(model_class="named-vendor")

    def test_asked_conflict_requires_question(self):
        with self.assertRaises(ValidationError):
            ConflictRecord(
                levels=("instruction", "specification"),
                description="Conflict",
                resolution="asked",
            )

    def test_artifact_hash_is_enforced(self):
        artifact = Artifact.create(
            artifact_id="ART-1",
            task_id="TASK-1",
            media_type="text/plain",
            content="hello",
        )
        self.assertEqual(artifact.content_hash, text_digest("hello"))
        with self.assertRaises(ValidationError):
            Artifact(
                artifact_id="ART-1",
                task_id="TASK-1",
                media_type="text/plain",
                content="hello",
                content_hash="0" * 64,
            )

    def test_artifact_context_reference_requires_id_and_sha256_together(self):
        with self.assertRaises(ValidationError):
            Artifact.create(
                artifact_id="ART-CTX",
                task_id="TASK-1",
                media_type="text/plain",
                content="content",
                context_bundle_id="CTX-1",
            )
        with self.assertRaises(ValidationError):
            Artifact.create(
                artifact_id="ART-CTX",
                task_id="TASK-1",
                media_type="text/plain",
                content="content",
                context_bundle_id="CTX-1",
                context_bundle_hash="not-a-digest",
            )

    def test_action_hash_binds_exact_payload(self):
        plan = ActionPlan.create(
            action_id="ACT-1",
            task_id="TASK-1",
            kind="external send",
            parameters={"to": "a@example.com", "body": "hello"},
            external=True,
            reversible=False,
            idempotency_key="send-1",
        )
        parsed = json.loads(plan.exact_action)
        self.assertEqual(digest(parsed), plan.action_hash)
        parsed["parameters"]["body"] = "changed"
        with self.assertRaises(ValidationError):
            ActionPlan(
                action_id=plan.action_id,
                task_id=plan.task_id,
                kind=plan.kind,
                parameters=parsed["parameters"],
                external=True,
                reversible=False,
                approval_required=True,
                exact_action=canonical_json(parsed),
                action_hash=plan.action_hash,
                idempotency_key=plan.idempotency_key,
            )

    def test_external_action_cannot_disable_approval(self):
        with self.assertRaises(ValidationError):
            ActionPlan.create(
                action_id="ACT-1",
                task_id="TASK-1",
                kind="external_send",
                parameters={},
                external=True,
                reversible=True,
                approval_required=False,
                idempotency_key="send-1",
            )

    def test_review_exclusions_are_immutable(self):
        base = dict(
            brief="brief",
            baseline=None,
            artifact={"task_id": "TASK-1"},
            interpretation_contract={"task_id": "TASK-1"},
            artifact_specification={"artifact_id": "ART-1"},
            mapped_craft_standards=(),
            verification_evidence=(),
            intended_outcome="outcome",
        )
        ReviewEnvelope(**base)
        with self.assertRaises(ValidationError):
            ReviewEnvelope(**base, excluded_always=("creator_private_reasoning",))

    def test_workflow_cycle_is_rejected(self):
        with self.assertRaises(ValidationError):
            WorkflowDefinition(
                so_id="SO-1",
                model_class="routine",
                steps=(
                    WorkflowStep("STEP-A", "a", ("STEP-B",)),
                    WorkflowStep("STEP-B", "b", ("STEP-A",)),
                ),
            )

    def test_completion_report_must_be_completed(self):
        with self.assertRaises(ValidationError):
            CompletionReport(
                task_id="TASK-1",
                status=TaskStatus.EXECUTING,
                result_summary="done",
                artifact_id=None,
                artifact_hash=None,
                material=False,
                review_decision=None,
                review_isolated=None,
                actions=(),
                evidence_ids=(),
                decision_ids=(),
                limitations=(),
            )

    def test_round_trip_task(self):
        task = self.task()
        self.assertEqual(TaskEnvelope.from_dict(task.to_dict()), task)
