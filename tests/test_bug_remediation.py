from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from lpos_engine.adapters.bug_remediation import BUG_REMEDIATION_HANDLERS
from lpos_engine.operations import StandingOperationRunner
from lpos_engine.store import SQLiteStore
from lpos_engine.workflows import load


def bug_report(component_hint: str = "support-engineering-fixture") -> dict:
    return {
        "report_id": "BUG-0001",
        "source": "web-app",
        "reporter": {
            "contact": "reporter@example.com",
            "channel": "email",
            "verified": True,
        },
        "submitted_at": "2030-01-07T12:00:00Z",
        "summary": "Preview save returns the old headline",
        "environment": {"os": "macOS", "build_id": "fixture"},
        "steps_to_reproduce": ["Open preview", "Edit headline", "Save"],
        "expected": "New headline persists",
        "actual": "Old headline persists",
        "severity": "medium",
        "artifacts": ["log://fixture/bug-0001"],
        "component_hint": component_hint,
    }


class BugRemediationWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.store = SQLiteStore(Path(self.temp.name) / "state.db")
        self.runner = StandingOperationRunner(self.store, BUG_REMEDIATION_HANDLERS)
        self.workflow = load("SO-022")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_dry_run_resolves_reproduced_bug_without_live_side_effects(self) -> None:
        result = self.runner.run(
            self.workflow,
            scheduled_for="2030-01-07T12:00:00Z:resolve",
            initial_context={"bug_report": bug_report()},
        )
        self.assertEqual(result.run.result.value, "ok")
        self.assertEqual(result.outputs["STEP-RESOLVE"]["outcome"], "resolved")
        self.assertEqual(result.outputs["STEP-REGRESSION"]["failing_fixture"]["initial_result"], "FAIL")
        self.assertEqual(result.outputs["STEP-VERIFY"]["fixture_result"], "PASS")
        self.assertEqual(result.outputs["STEP-VERIFY"]["suite_result"], "PASS")
        self.assertEqual(result.outputs["STEP-REVIEW"]["decision"], "PASS")
        self.assertEqual(result.outputs["STEP-RESOLVE"]["production_change"], "approval-gated")
        self.assertTrue(result.outputs["STEP-NOTIFY"]["notification"]["sent"])
        self.assertEqual(len(self.store.list_evidence()), 1)

    def test_dry_run_escalates_unreproducible_bug_with_full_package(self) -> None:
        result = self.runner.run(
            self.workflow,
            scheduled_for="2030-01-07T12:00:00Z:escalate",
            initial_context={"bug_report": bug_report("unreproducible-fixture")},
        )
        self.assertEqual(result.run.result.value, "ok")
        escalation = result.outputs["STEP-RESOLVE"]
        self.assertEqual(escalation["outcome"], "escalated")
        self.assertEqual(escalation["reason"], "not_reproducible")
        package = escalation["diagnostic_package"]
        self.assertEqual(package["repro"]["status"], "not_reproducible")
        self.assertEqual(package["regression"]["status"], "skipped")
        self.assertEqual(package["diagnosis"]["status"], "not_localized")
        self.assertEqual(len(package["attempts"]["attempts"]), 0)
        self.assertTrue(result.outputs["STEP-NOTIFY"]["notification"]["sent"])
        self.assertEqual(len(self.store.list_evidence()), 1)


if __name__ == "__main__":
    unittest.main()
