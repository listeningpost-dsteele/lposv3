"""SO-022 Release Publication and SO-024 Documentation Drift Audit handler tests."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from lpos_engine.errors import ValidationError
from lpos_engine.publication import (
    HANDLERS,
    diff_documentation_coverage,
    enforce_docs_gate,
    enumerate_documented_surfaces,
    record_publication_actions,
    report_documentation_drift,
    standard_handlers,
    verify_release_gates,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


class ReleaseGateTests(unittest.TestCase):
    def test_release_gates_pass_on_this_checkout_without_rerunning_verifier(self) -> None:
        result = verify_release_gates({"repo_root": str(REPO_ROOT), "skip_verifier": True,
                                       "verifier_passed": True})
        self.assertTrue(all(result["gates"].values()))
        self.assertEqual(result["version"], "4.2.0")

    def test_release_gates_fail_loudly_on_an_empty_tree(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValidationError):
                verify_release_gates({"repo_root": directory})

    def test_docs_gate_requires_the_patch_notes_page(self) -> None:
        result = enforce_docs_gate({"repo_root": str(REPO_ROOT)})
        self.assertEqual(result["docs_gate"], "passed")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "RELEASE.json").write_text(json.dumps({"version": "9.9.9"}))
            with self.assertRaises(ValidationError):
                enforce_docs_gate({"repo_root": directory})
            waived = enforce_docs_gate({"repo_root": directory, "no_user_facing_change": True})
            self.assertEqual(waived["docs_gate"], "waived")

    def test_publication_actions_are_record_only_and_approval_bound(self) -> None:
        result = record_publication_actions({"repo_root": str(REPO_ROOT)})
        self.assertEqual(result["mode"], "record-only")
        self.assertTrue(result["approval_required"])
        kinds = {action["kind"] for action in result["actions"]}
        self.assertEqual(kinds, {"vcs_push", "drive_update", "site_deploy"})


class DocumentationDriftTests(unittest.TestCase):
    def test_enumeration_comes_from_the_packaged_system(self) -> None:
        result = enumerate_documented_surfaces({})
        self.assertIn("SO-001", result["surfaces"])
        self.assertIn("SO-024", result["surfaces"])
        self.assertIn("skill:skill-evolution", result["surfaces"])
        self.assertIn("module:dashboard", result["surfaces"])

    def test_this_release_has_no_documentation_drift(self) -> None:
        surfaces = enumerate_documented_surfaces({})
        diff = diff_documentation_coverage(
            {"repo_root": str(REPO_ROOT), "STEP-ENUMERATE": surfaces}
        )
        self.assertFalse(diff["wiki_missing"])
        self.assertEqual(diff["undocumented"], [])

    def test_drift_report_is_persisted_under_the_hermes_root(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            report = report_documentation_drift(
                {"hermes_root": directory, "STEP-DIFF": {"checked": 3, "undocumented": ["module:x"]}}
            )
            self.assertEqual(report["status"], "drift")
            written = json.loads(Path(report["report_path"]).read_text())
            self.assertEqual(written["undocumented"], ["module:x"])

    def test_standard_handlers_cover_all_new_standing_operations(self) -> None:
        merged = standard_handlers()
        for name in (
            "discover_connector_inventory",
            "audit_connectors",
            "alert_connector_transitions",
            "inventory_compliance_controls",
            "audit_compliance_controls",
            "stage_compliance_remediation",
            "publish_compliance_report",
            *HANDLERS,
        ):
            self.assertIn(name, merged)


if __name__ == "__main__":
    unittest.main()
