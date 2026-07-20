from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from jsonschema import FormatChecker
from jsonschema.validators import validator_for

from lpos_engine.adapters.subprocess_host import SubprocessModelAdapter
from lpos_engine.context import ContextCompiler, SpecRepository
from lpos_engine.models import (
    ActionPlan,
    Artifact,
    ArtifactSpecification,
    InterpretationContract,
    ReviewEnvelope,
    TaskEnvelope,
)


class SchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime_root = Path(__file__).resolve().parents[1]
        cls.schema_root = cls.runtime_root / "schemas"

    def validate(self, name, instance):
        schema = json.loads((self.schema_root / name).read_text(encoding="utf-8"))
        validator_cls = validator_for(schema)
        validator_cls.check_schema(schema)
        validator_cls(schema, format_checker=FormatChecker()).validate(instance)

    def test_all_schema_documents_are_valid(self):
        files = sorted(self.schema_root.glob("*.schema.json"))
        self.assertGreaterEqual(len(files), 15)
        for path in files:
            with self.subTest(path=path.name):
                schema = json.loads(path.read_text(encoding="utf-8"))
                validator_for(schema).check_schema(schema)

    def test_task_contract_artifact_and_action_match_schemas(self):
        task = TaskEnvelope(
            task_id="TASK-1",
            principal_instruction="Do it",
            lead_guild="Engineering",
            lead_specialist="PROFILE-ENGINEERING",
            required_capabilities=("testing",),
            material=True,
            materiality_basis=("changes_approved_artifact",),
        )
        contract = InterpretationContract(
            task_id="TASK-1",
            instruction_verbatim="Do it",
            interpretation="Do it exactly",
            invariants=(),
            conflicts=(),
            verification_plan=("test",),
            spec_ref="SPEC-1",
        )
        artifact = Artifact.create(
            artifact_id="ART-1",
            task_id="TASK-1",
            media_type="text/plain",
            content="result",
        )
        action = ActionPlan.create(
            action_id="ACT-1",
            task_id="TASK-1",
            kind="external_send",
            parameters={"to": "a@example.com"},
            external=True,
            reversible=False,
            idempotency_key="send-1",
        )
        self.validate("task-envelope.schema.json", task.to_dict())
        self.validate("interpretation-contract.schema.json", contract.to_dict())
        self.validate("artifact.schema.json", artifact.to_dict())
        self.validate("action-plan.schema.json", action.to_dict())

    def test_review_envelope_matches_schema(self):
        task = TaskEnvelope(
            task_id="TASK-1",
            principal_instruction="Do it",
            lead_guild="Engineering",
            lead_specialist="PROFILE-ENGINEERING",
            material=True,
            materiality_basis=("changes_approved_artifact",),
        )
        contract = InterpretationContract(
            task_id="TASK-1",
            instruction_verbatim="Do it",
            interpretation="Do it",
            invariants=(),
            conflicts=(),
            verification_plan=("test",),
            spec_ref=None,
        )
        artifact = Artifact.create(
            artifact_id="ART-1",
            task_id="TASK-1",
            media_type="text/plain",
            content="result",
        )
        spec = ArtifactSpecification(artifact_id="ART-1")
        envelope = ReviewEnvelope(
            brief=task.principal_instruction,
            baseline=None,
            artifact=artifact.to_dict(),
            interpretation_contract=contract.to_dict(),
            artifact_specification=spec.to_dict(),
            mapped_craft_standards=(),
            verification_evidence=(),
            intended_outcome="done",
        )
        self.validate("review-envelope.schema.json", envelope.to_dict())


class SubprocessAdapterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.script = self.root / "adapter.py"
        self.script.write_text(
            """
import json, sys
value=json.load(sys.stdin)
if value['operation']=='create_artifact':
    print(json.dumps({'content':'from subprocess','media_type':'text/plain','evidence':['ok'],'assumptions':[],'adapter_metadata':{}}))
else:
    context=value['context']
    print(json.dumps({'decision':'PASS','isolation':'fresh_context:'+context['bundle_id'],'recomputed':'all','contract_violations':[],'truth':[],'reasoning':[],'craft':[],'outcome':[],'regressions':[],'required_corrections':[],'strengths_to_preserve':[],'evidence_reviewed':[]}))
""".strip(),
            encoding="utf-8",
        )
        self.adapter = SubprocessModelAdapter(
            "subprocess",
            (sys.executable, str(self.script)),
            model_classes=frozenset({"executive", "review"}),
            capabilities=frozenset({"software_architecture", "independent_review", "quality_assurance"}),
        )
        self.compiler = ContextCompiler(SpecRepository(None))
        self.task = TaskEnvelope(
            task_id="TASK-1",
            principal_instruction="Do it",
            lead_guild="Engineering",
            lead_specialist="PROFILE-ENGINEERING",
            required_capabilities=("software_architecture",),
            material=True,
            materiality_basis=("changes_approved_artifact",),
            model_class="executive",
        )
        self.contract = InterpretationContract(
            task_id="TASK-1",
            instruction_verbatim="Do it",
            interpretation="Do it",
            invariants=(),
            conflicts=(),
            verification_plan=("test",),
            spec_ref=None,
        )
        self.spec = ArtifactSpecification(artifact_id="ART-1")

    def tearDown(self):
        self.temp.cleanup()

    def test_create_protocol(self):
        context = self.compiler.compile_task(
            task=self.task,
            interpretation=self.contract,
            artifact_specification=self.spec,
        )
        output = self.adapter.create_artifact(self.task, context)
        self.assertEqual(output.content, "from subprocess")

    def test_review_protocol(self):
        artifact = Artifact.create(
            artifact_id="ART-1",
            task_id="TASK-1",
            media_type="text/plain",
            content="result",
        )
        envelope = ReviewEnvelope(
            brief="Do it",
            baseline=None,
            artifact=artifact.to_dict(),
            interpretation_contract=self.contract.to_dict(),
            artifact_specification=self.spec.to_dict(),
            mapped_craft_standards=(),
            verification_evidence=(),
            intended_outcome="done",
        )
        context = self.compiler.compile_review(envelope)
        result = self.adapter.review(envelope, context)
        self.assertEqual(result.decision.value, "PASS")
        self.assertIn(context.bundle_id, result.isolation)


class CLITests(unittest.TestCase):
    def test_demo_command_completes(self):
        runtime_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as d:
            env = dict(__import__("os").environ)
            env["PYTHONPATH"] = str(runtime_root / "src")
            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "lpos_engine",
                    "demo",
                    "--workspace",
                    d,
                ],
                cwd=runtime_root,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            result = json.loads(completed.stdout)
            self.assertEqual(result["completion_report"]["status"], "completed")
            self.assertTrue((Path(d) / "events.jsonl").is_file())
