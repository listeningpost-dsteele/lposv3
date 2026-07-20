from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from lpos_engine.context import ContextCompiler, SpecRepository
from lpos_engine.errors import ContextIsolationError, ValidationError
from lpos_engine.models import (
    Artifact,
    ArtifactSpecification,
    InterpretationContract,
    ReviewEnvelope,
    TaskEnvelope,
)
from lpos_engine.routing import CapabilityRegistry, CapabilityRouter, SpecialistProfile


class RoutingTests(unittest.TestCase):
    def setUp(self):
        self.router = CapabilityRouter(CapabilityRegistry.default())

    def test_single_complete_engineering_profile(self):
        route = self.router.route(("software_architecture", "testing"))
        self.assertEqual(route.lead_specialist, "SPECIALIST-011")
        self.assertFalse(route.missing_capabilities)
        self.assertIn("CS-007", route.craft_standards)

    def test_multiple_profiles_cover_cross_domain_request(self):
        route = self.router.route(("software_implementation", "customer_communication"))
        selected = {route.lead_specialist, *route.supporting_specialists}
        self.assertEqual(selected, {"SPECIALIST-012", "SPECIALIST-019"})
        self.assertFalse(route.missing_capabilities)

    def test_missing_capability_is_explicit(self):
        route = self.router.route(("licensed_medical_judgment",))
        self.assertEqual(route.missing_capabilities, ("licensed_medical_judgment",))
        self.assertTrue(route.substitutions)

    def test_empty_request_defaults_to_executive_coordination(self):
        route = self.router.route(())
        self.assertEqual(route.lead_specialist, "SPECIALIST-001")

    def test_duplicate_profile_ids_rejected(self):
        profile = SpecialistProfile.from_dict(
            {
                "specialist_id": "PROFILE-X",
                "name": "X",
                "guild": "X",
                "capabilities": ["x"],
                "craft_standards": [],
                "model_class": "routine",
            }
        )
        with self.assertRaises(ValidationError):
            CapabilityRegistry((profile, profile))


class ContextTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "skills" / "independent-reviewer").mkdir(parents=True)
        (self.root / "CHIP-KERNEL.md").write_text("# Kernel\nAlways loaded.\n", encoding="utf-8")
        (self.root / "SPECIALISTS.md").write_text(
            "# Specialists\n\n## SPECIALIST-001 Alpha\nAlpha body.\n\n## SPECIALIST-002 Beta\nBeta body.\n",
            encoding="utf-8",
        )
        (self.root / "CRAFT-STANDARDS.md").write_text(
            "# Standards\n\n## CS-003 Artifact\nArtifact body.\n\n## CS-999 Other\nDo not load.\n",
            encoding="utf-8",
        )
        (self.root / "skills" / "independent-reviewer" / "SKILL.md").write_text(
            "# Reviewer\nUse only the envelope.", encoding="utf-8"
        )
        self.compiler = ContextCompiler(SpecRepository(self.root))
        self.task = TaskEnvelope(
            task_id="TASK-1",
            principal_instruction="Build it",
            lead_guild="Engineering",
            lead_specialist="SPECIALIST-001",
            craft_standards=("CS-003",),
            required_capabilities=("software_architecture",),
            material=True,
            materiality_basis=("modifies_long_lived_specification",),
            model_class="executive",
        )
        self.contract = InterpretationContract(
            task_id="TASK-1",
            instruction_verbatim="Build it",
            interpretation="Build only it",
            invariants=("Preserve A",),
            conflicts=(),
            verification_plan=("Test A",),
            spec_ref="SPEC-1",
        )
        self.spec = ArtifactSpecification(artifact_id="ART-1", invariants=("Preserve A",))

    def tearDown(self):
        self.temp.cleanup()

    def test_extracts_only_requested_sections(self):
        bundle = self.compiler.compile_task(
            task=self.task,
            interpretation=self.contract,
            artifact_specification=self.spec,
        )
        self.assertIn("Alpha body", bundle.content)
        self.assertIn("Artifact body", bundle.content)
        self.assertNotIn("Beta body", bundle.content)
        self.assertNotIn("Do not load", bundle.content)

    def test_missing_component_is_reported(self):
        task = TaskEnvelope.from_dict({**self.task.to_dict(), "lead_specialist": "SPECIALIST-404"})
        bundle = self.compiler.compile_task(
            task=task,
            interpretation=self.contract,
            artifact_specification=self.spec,
        )
        self.assertIn("SPECIALIST-404", bundle.missing_components)

    def test_review_context_is_fresh_and_declares_exclusions(self):
        artifact = Artifact.create(
            artifact_id="ART-1",
            task_id="TASK-1",
            media_type="text/plain",
            content="result",
        )
        envelope = ReviewEnvelope(
            brief="Build it",
            baseline=None,
            artifact=artifact.to_dict(),
            interpretation_contract=self.contract.to_dict(),
            artifact_specification=self.spec.to_dict(),
            mapped_craft_standards=("CS-003",),
            verification_evidence=("tests passed",),
            intended_outcome="working result",
        )
        bundle = self.compiler.compile_review(envelope)
        self.assertEqual(bundle.purpose, "review")
        self.assertIn("creator_private_reasoning", bundle.excluded)
        self.assertNotIn("# LPOS Creation Context", bundle.content)
        self.assertIn("Use only the envelope", bundle.content)

    def test_non_review_bundle_fails_isolation_check(self):
        bundle = self.compiler.compile_task(
            task=self.task,
            interpretation=self.contract,
            artifact_specification=self.spec,
        )
        with self.assertRaises(ContextIsolationError):
            self.compiler.assert_review_isolated(bundle)

    def test_context_budget_is_enforced(self):
        compiler = ContextCompiler(SpecRepository(self.root), max_chars=1000)
        task = TaskEnvelope.from_dict(
            {**self.task.to_dict(), "principal_instruction": "x" * 2000}
        )
        contract = InterpretationContract(
            task_id="TASK-1",
            instruction_verbatim="x" * 2000,
            interpretation="x",
            invariants=(),
            conflicts=(),
            verification_plan=("test",),
            spec_ref=None,
        )
        with self.assertRaises(ValidationError):
            compiler.compile_task(task=task, interpretation=contract, artifact_specification=self.spec)
