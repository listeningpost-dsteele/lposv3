from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from lpos_engine.errors import ValidationError
from lpos_engine.managed_execution import ManagedExecution, ManagedRunRequest, RiskTier


FAKE_HERMES = r'''#!/usr/bin/env python3
import hashlib, json, pathlib, sys
args = sys.argv[1:]
prompt = args[args.index("-q") + 1]
if "COMPILED CONTRACT:\n" in prompt:
    contract = json.loads(prompt.split("COMPILED CONTRACT:\n", 1)[1])
    workdir = pathlib.Path(contract["task"]["constraints"]["workdir"])
    artifact_rel = contract["task"]["constraints"]["artifact_path"]
    artifact = workdir / artifact_rel
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text("managed artifact\n", encoding="utf-8")
    sha = hashlib.sha256(artifact.read_bytes()).hexdigest()
    receipt = {
        "schema": "lpos.managed-contribution.v1",
        "run_id": contract["run_id"],
        "specialist_id": contract["task"]["lead_specialist"],
        "status": "completed",
        "artifact_path": artifact_rel,
        "artifact_sha256": sha,
        "summary": "created fixture artifact",
        "capability_gap": [],
        "evidence": ["artifact written"],
    }
    pathlib.Path(contract["receipt_path"]).write_text(json.dumps(receipt), encoding="utf-8")
else:
    envelope = json.loads(prompt.split("REVIEW ENVELOPE:\n", 1)[1])
    marker = "Write only the machine-readable review receipt at "
    review_path = pathlib.Path(prompt.split(marker, 1)[1].split(" with schema", 1)[0])
    review = {
        "schema": "lpos.managed-review.v1",
        "run_id": envelope["run_id"],
        "reviewer_id": envelope["reviewer_specialist"],
        "decision": "PASS",
        "artifact_sha256": envelope["artifact_sha256"],
        "source_sha256": envelope["source_sha256"],
        "corrections": [],
        "evidence_reviewed": ["artifact hash", "source hash", "checks"],
        "summary": "fresh-context fixture review passed",
    }
    review_path.write_text(json.dumps(review), encoding="utf-8")
print("fixture child complete")
'''


class ManagedExecutionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=self.repo, check=True)
        subprocess.run(["git", "config", "user.email", "fixture@example.com"], cwd=self.repo, check=True)
        subprocess.run(["git", "config", "user.name", "Fixture"], cwd=self.repo, check=True)
        (self.repo / "README.md").write_text("fixture\n", encoding="utf-8")
        subprocess.run(["git", "add", "README.md"], cwd=self.repo, check=True)
        subprocess.run(["git", "commit", "-qm", "fixture"], cwd=self.repo, check=True)
        self.head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=self.repo, text=True).strip()
        self.hermes = self.root / "fake-agent"
        self.hermes.write_text(FAKE_HERMES, encoding="utf-8")
        self.hermes.chmod(0o755)
        self.state = self.root / "state"

    def tearDown(self):
        self.temp.cleanup()

    def request(self, **overrides):
        values = {
            "instruction": "Create a fixture artifact.",
            "workdir": self.repo,
            "specialist_id": "SPECIALIST-INTEGRATION-ENGINEER",
            "reviewer_id": "SPECIALIST-SOFTWARE-REVIEWER",
            "artifact_path": "result.txt",
            "required_capabilities": ("integration",),
            "toolsets": ("file", "terminal"),
            "checks": ("python3 -c \"import pathlib; assert pathlib.Path('result.txt').is_file()\"",),
            "risk_tier": RiskTier.LOCAL_IMPLEMENTATION,
            "state_root": self.state,
            "hermes_command": str(self.hermes),
            "expected_repo": self.repo,
            "expected_head": self.head,
        }
        values.update(overrides)
        return ManagedRunRequest(**values)

    def test_non_mocked_subprocess_flow_completes_with_hash_bound_review(self):
        result = ManagedExecution(self.request()).run()
        self.assertEqual(result["status"], "completed")
        self.assertTrue(result["completion_latch"])
        self.assertEqual(result["review"]["reviewer_id"], "SPECIALIST-SOFTWARE-REVIEWER")
        self.assertEqual(result["artifact"]["sha256"], result["review"]["artifact_sha256"])
        self.assertEqual(result["source"]["sha256"], result["review"]["source_sha256"])
        self.assertEqual(result["correction_cycles"], 0)
        self.assertTrue(all(item["passed"] for item in result["checks"]))

    def test_capability_gap_is_terminal_before_child_execution(self):
        result = ManagedExecution(self.request(required_capabilities=("not-a-real-capability",))).run()
        self.assertEqual(result["status"], "capability_gap")
        self.assertFalse(result["completion_latch"])
        self.assertIn("specialist_capability:not_a_real_capability", result["capability_gap"])
        self.assertFalse((self.repo / "result.txt").exists())

    def test_same_specialist_cannot_review(self):
        with self.assertRaisesRegex(ValidationError, "different specialist"):
            self.request(reviewer_id="SPECIALIST-INTEGRATION-ENGINEER")

    def test_consequential_tier_requires_separate_authorization(self):
        with self.assertRaisesRegex(ValidationError, "separate explicit authorization"):
            self.request(risk_tier=RiskTier.CONSEQUENTIAL)

    def test_more_than_two_corrections_is_rejected(self):
        with self.assertRaisesRegex(ValidationError, "between 0 and 2"):
            self.request(max_corrections=3)

    def test_artifact_path_cannot_escape_workdir(self):
        with self.assertRaisesRegex(ValidationError, "relative path"):
            self.request(artifact_path="../escape.txt")
        self.assertFalse((self.root / "escape.txt").exists())


if __name__ == "__main__":
    unittest.main()
