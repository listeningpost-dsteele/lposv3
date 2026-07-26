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
    enforce_customer_facing_quality,
    enforce_docs_gate,
    enumerate_documented_surfaces,
    record_publication_actions,
    report_documentation_drift,
    standard_handlers,
    verify_release_gates,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


class ReleaseGateTests(unittest.TestCase):
    @staticmethod
    def quality_evidence(**overrides: object) -> dict[str, object]:
        artifact_hash = "a" * 64
        evidence: dict[str, object] = {
            "artifact_id": "LPOS-v4.5.0",
            "artifact_sha256": artifact_hash,
            "artifact_kind": "customer-facing-release",
            "required_skills_loaded": ["anti-slop-editor", "design-anti-slop-reviewer"],
            "deterministic_blockers": [],
            "writing_lint_passed": True,
            "fabricated_proof": False,
            "unsupported_claims": [],
            "verified_viewports": ["desktop", "mobile"],
            "accessibility_passed": True,
            "interactions_verified": True,
            "named_pattern_review_passed": True,
            "independent_review": {
                "verdict": "PASS",
                "artifact_sha256": artifact_hash,
                "isolated": True,
                "fresh_context": True,
            },
        }
        evidence.update(overrides)
        return evidence

    def test_release_gates_pass_on_this_checkout_without_rerunning_verifier(self) -> None:
        result = verify_release_gates({"repo_root": str(REPO_ROOT), "skip_verifier": True,
                                       "verifier_passed": True})
        self.assertTrue(all(result["gates"].values()))
        self.assertEqual(result["version"], "4.5.0")

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
        quality = enforce_customer_facing_quality({"quality_evidence": self.quality_evidence()})
        result = record_publication_actions({"repo_root": str(REPO_ROOT), "STEP-QUALITY": quality})
        self.assertEqual(result["mode"], "record-only")
        self.assertTrue(result["approval_required"])
        kinds = {action["kind"] for action in result["actions"]}
        self.assertEqual(kinds, {"vcs_push", "drive_update", "site_deploy"})

    def test_publication_is_blocked_without_quality_evidence(self) -> None:
        with self.assertRaises(ValidationError):
            record_publication_actions({"repo_root": str(REPO_ROOT)})

    def test_quality_gate_rejects_missing_proof_and_blockers(self) -> None:
        evidence = self.quality_evidence(
            deterministic_blockers=["fake-testimonial"],
            verified_viewports=["desktop"],
            fabricated_proof=True,
        )
        with self.assertRaises(ValidationError) as caught:
            enforce_customer_facing_quality({"quality_evidence": evidence})
        message = str(caught.exception)
        self.assertIn("deterministic blockers remain", message)
        self.assertIn("desktop and mobile evidence are required", message)
        self.assertIn("fabricated_proof must be false", message)

    def test_quality_gate_rejects_stale_or_nonisolated_review(self) -> None:
        evidence = self.quality_evidence(
            independent_review={
                "verdict": "PASS",
                "artifact_sha256": "b" * 64,
                "isolated": False,
                "fresh_context": False,
            }
        )
        with self.assertRaises(ValidationError) as caught:
            enforce_customer_facing_quality({"quality_evidence": evidence})
        self.assertIn("bound to a different artifact", str(caught.exception))
        self.assertIn("not fresh and isolated", str(caught.exception))


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
            "classify_change_criticality",
            "run_need_to_change_gate",
            "evaluate_release_gauntlet",
            "record_gauntlet_evidence",
            "review_test_suite_health",
            "verify_critical_path_hardening",
            *HANDLERS,
        ):
            self.assertIn(name, merged)


if __name__ == "__main__":
    unittest.main()
