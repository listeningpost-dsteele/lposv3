"""SO-025 control readiness monitor tests (fully offline, repo untouched).

Contract under test (audit findings LPOS-01/LPOS-02): the monitor is a
self-assessment that never emits "compliant" or "effective"; a fresh run is
insufficient evidence, never green; one execution over 21 controls is ONE run.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from lpos_engine.compliance import (
    CONTROLS,
    HANDLERS,
    MIN_OBSERVATION_DAYS,
    MIN_RUNS,
    Control,
    ControlResult,
    build_and_stage_remediations,
    run_audit,
    stage_remediation,
)
from lpos_engine.compliance import audit as audit_module
from lpos_engine.compliance.report import render_report
from lpos_engine.errors import ValidationError
from lpos_engine.models import OperationResult, WorkflowDefinition
from lpos_engine.operations import StandingOperationRunner
from lpos_engine.store import SQLiteStore

REPO_ROOT = Path(__file__).resolve().parents[1]

STATUS_CONTRACT_KEYS = {
    "generated_at",
    "framework",
    "assessment",
    "attestation",
    "issued_by_cpa",
    "self_assessment",
    "evidence_period_status",
    "run_id",
    "distinct_runs",
    "distinct_run_days",
    "days_of_history",
    "window_days",
    "thresholds",
    "overall",
    "controls",
    "not_evidenced",
    "summary",
}

#: Substrings that must NEVER appear as self-determined states. "effective"
#: also catches "effectiveness"; matched case-insensitively.
FORBIDDEN_WORDS = ("compliant", "effective")


def _assert_no_self_certification(test: unittest.TestCase, text: str) -> None:
    lowered = text.lower()
    for word in FORBIDDEN_WORDS:
        test.assertNotIn(word, lowered, f"self-certifying word {word!r} found")


def _snapshot_repo() -> dict[str, tuple[int, int]]:
    """(mtime_ns, size) for every repo file, ignoring bytecode caches."""

    snapshot: dict[str, tuple[int, int]] = {}
    for path in REPO_ROOT.rglob("*"):
        if "__pycache__" in path.parts or path.suffix == ".pyc":
            continue
        if path.is_file():
            stat = path.stat()
            snapshot[str(path.relative_to(REPO_ROOT))] = (stat.st_mtime_ns, stat.st_size)
    return snapshot


def _failing_control(control_id: str = "CTRL-TEST-01", paths: tuple[str, ...] = ("CHANGELOG.md",)) -> Control:
    return Control(
        control_id=control_id,
        tsc_id="CC8",
        title="Deliberately failing test control",
        description="Always fails, for staging tests.",
        category="standard",
        check=lambda repo, hermes: ControlResult(
            passing=False, evidence="injected failure for the test"
        ),
        remediation_paths=paths,
        remediation_hint="Fix CHANGELOG.md as described.",
        assurance="outcome",
    )


def _passing_control(control_id: str = "CTRL-TEST-02", assurance: str = "outcome") -> Control:
    return Control(
        control_id=control_id,
        tsc_id="CC5",
        title="Always-passing test control",
        description="Always passes, for evidence math.",
        category="standard",
        check=lambda repo, hermes: ControlResult(passing=True, evidence="ok"),
        assurance=assurance,
    )


def _seed_runs(
    hermes: Path,
    control_id: str,
    *,
    runs: int,
    days: int,
    fails: int = 0,
) -> None:
    """Seed `runs` distinct run_ids spread over `days` distinct UTC days."""

    base = datetime.now(timezone.utc).replace(microsecond=0)
    entries = []
    for i in range(runs):
        day = (i % days) + 1  # never today: run_audit adds today itself
        stamp = base - timedelta(days=day, minutes=i)
        entries.append(
            {
                "ts": stamp.isoformat(),
                "run_id": f"RUN-SEED-{i:04d}",
                "event": "check",
                "control_id": control_id,
                "passing": i >= fails,
                "evidence": "seed",
            }
        )
    audit_module.append_history(hermes, entries)


class FullAuditTests(unittest.TestCase):
    def test_full_audit_contract_and_release_tree_controls(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            hermes = Path(directory)
            result = run_audit(REPO_ROOT, hermes)

            self.assertTrue(STATUS_CONTRACT_KEYS <= set(result.status))
            self.assertEqual(
                result.status["framework"], "SOC 2 Type 2 (TSC 2017, 2022 POF)"
            )
            # LPOS-01: machine-readable honesty fields.
            self.assertIs(result.status["attestation"], False)
            self.assertIs(result.status["issued_by_cpa"], False)
            self.assertIs(result.status["self_assessment"], True)
            self.assertIn(
                result.status["overall"],
                ("not_assessed", "insufficient_evidence", "gaps", "ready_pending_attestation"),
            )
            # A fresh run can NEVER be ready: zero-day history is insufficient.
            self.assertIn(result.status["overall"], ("insufficient_evidence", "gaps"))
            self.assertEqual(result.status["evidence_period_status"], "insufficient")

            # The written status.json matches the returned contract and never
            # self-certifies.
            written_text = (hermes / "compliance" / "status.json").read_text()
            self.assertEqual(json.loads(written_text), result.status)
            _assert_no_self_certification(self, written_text)

            # History: one hash-chained line per control, all carrying run_id.
            lines = (hermes / "compliance" / "history.jsonl").read_text().splitlines()
            self.assertEqual(len(lines), len(CONTROLS))
            for line in lines:
                entry = json.loads(line)
                for key in ("ts", "run_id", "control_id", "passing", "evidence", "seq", "chain"):
                    self.assertIn(key, entry)
                self.assertEqual(entry["run_id"], result.run_id)

            # The release-tree controls pass on this checkout.
            by_id = {c["control_id"]: c for c in result.status["controls"]}
            for control_id in (
                "CTRL-CC1-01",
                "CTRL-CC2-01",
                "CTRL-CC3-01",
                "CTRL-CC5-01",
                "CTRL-CC5-02",
                "CTRL-CC6-01",
                "CTRL-CC7-03",
                "CTRL-CC8-02",
                "CTRL-CC9-01",
                "CTRL-C-01",
                "CTRL-PI-01",
            ):
                self.assertTrue(
                    by_id[control_id]["passing"],
                    f"{control_id} should pass on this checkout: {by_id[control_id]['evidence']}",
                )
            # Every control carries its register row (LPOS-02).
            for control in result.status["controls"]:
                self.assertIn(control["assurance"], ("outcome", "structural", "organizational"))
                self.assertTrue(control["control_objective"])
                self.assertEqual(control["owner"], "Principal")
                self.assertEqual(control["frequency"], "daily")
                self.assertTrue(control["evidence_source"])

    def test_one_execution_of_all_controls_is_one_run(self) -> None:
        """LPOS-01 closure: 21 controls checked in one execution = ONE run."""

        with tempfile.TemporaryDirectory() as directory:
            hermes = Path(directory)
            result = run_audit(REPO_ROOT, hermes)
            self.assertEqual(result.status["distinct_runs"], 1)
            self.assertEqual(result.status["distinct_run_days"], 1)
            self.assertEqual(result.status["days_of_history"], 0)
            for control in result.status["controls"]:
                self.assertEqual(control["distinct_runs"], 1)

    def test_fresh_run_with_all_passing_controls_is_insufficient_evidence(self) -> None:
        """LPOS-01 closure: zero-day, one-run history cannot look green."""

        with tempfile.TemporaryDirectory() as directory:
            hermes = Path(directory)
            result = run_audit(REPO_ROOT, hermes, controls=[_passing_control()])
            self.assertEqual(result.overall, "insufficient_evidence")
            self.assertEqual(result.status["controls"][0]["verdict"], "insufficient_history")

    def test_missing_status_reads_as_not_assessed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            status = audit_module.load_status(Path(directory))
            self.assertEqual(status["overall"], "not_assessed")
            self.assertIs(status["attestation"], False)
            self.assertIs(status["self_assessment"], True)

    def test_any_current_failure_is_gaps_regardless_of_history(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            hermes = Path(directory)
            control = _failing_control("CTRL-TEST-03", paths=())
            _seed_runs(hermes, control.control_id, runs=60, days=45)
            result = run_audit(REPO_ROOT, hermes, controls=[control])
            self.assertEqual(result.overall, "gaps")
            self.assertEqual(result.status["controls"][0]["verdict"], "failing")

    def test_sustained_history_reaches_ready_pending_attestation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            hermes = Path(directory)
            control = _passing_control()
            _seed_runs(hermes, control.control_id, runs=45, days=45)
            result = run_audit(REPO_ROOT, hermes, controls=[control])
            self.assertGreaterEqual(result.status["distinct_run_days"], MIN_OBSERVATION_DAYS)
            self.assertGreaterEqual(result.status["distinct_runs"], MIN_RUNS)
            self.assertEqual(result.overall, "ready_pending_attestation")
            self.assertEqual(result.status["controls"][0]["verdict"], "operating")
            # Even at readiness, honesty fields stay false.
            self.assertIs(result.status["attestation"], False)
            self.assertIs(result.status["issued_by_cpa"], False)

    def test_missing_files_fail_the_control_without_crashing(self) -> None:
        with tempfile.TemporaryDirectory() as empty_repo, tempfile.TemporaryDirectory() as hermes:
            result = run_audit(Path(empty_repo), Path(hermes))
            self.assertEqual(result.overall, "gaps")
            for control in result.status["controls"]:
                if not control["passing"]:
                    self.assertTrue(control["evidence"])

    def test_not_evidenced_organizational_criteria_are_emitted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = run_audit(REPO_ROOT, Path(directory), controls=[_passing_control()])
            items = result.status["not_evidenced"]
            self.assertGreaterEqual(len(items), 8)
            tsc_ids = {item["tsc_id"] for item in items}
            for series in ("CC1", "CC9", "A", "P"):
                self.assertIn(series, tsc_ids)
            for item in items:
                self.assertEqual(
                    item["basis"], "requires organizational evidence — not machine-checkable"
                )


class StructuralCapTests(unittest.TestCase):
    def test_structural_control_never_exceeds_structural_evidence_only(self) -> None:
        """LPOS-02: a passing structural check is capped below "operating"."""

        with tempfile.TemporaryDirectory() as directory:
            hermes = Path(directory)
            control = _passing_control("CTRL-TEST-STRUCT", assurance="structural")
            _seed_runs(hermes, control.control_id, runs=60, days=45)
            result = run_audit(REPO_ROOT, hermes, controls=[control])
            self.assertEqual(
                result.status["controls"][0]["verdict"], "structural_evidence_only"
            )

    def test_shipped_structural_controls_are_labeled_structural(self) -> None:
        by_id = {c.control_id: c for c in CONTROLS}
        for control_id in (
            "CTRL-CC5-01",  # def test_ counter + recorded report (does not run the suite)
            "CTRL-CC6-01",  # DEFAULT_HOST string read
            "CTRL-CC6-02",  # approvals-file presence
            "CTRL-CC2-01",  # docs presence
            "CTRL-CC3-01",  # docs presence
        ):
            self.assertEqual(by_id[control_id].assurance, "structural", control_id)
        for control_id in ("CTRL-CC7-02", "CTRL-CC8-01", "CTRL-CC6-03"):
            self.assertEqual(by_id[control_id].assurance, "outcome", control_id)

    def test_monitor_freshness_catalog_only_is_structural_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            hermes = Path(directory)  # no monitor runtime exists
            result = run_audit(
                REPO_ROOT,
                hermes,
                controls=[c for c in CONTROLS if c.control_id == "CTRL-CC7-02"],
            )
            doc = result.status["controls"][0]
            self.assertTrue(doc["passing"])
            self.assertTrue(doc["details"].get("structural_only"))

    def test_monitor_freshness_stale_runtime_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            hermes = Path(directory)
            monitor = hermes / "monitor"
            monitor.mkdir()
            stale = (datetime.now(timezone.utc) - timedelta(hours=5)).isoformat()
            (monitor / "status.json").write_text(json.dumps({"generated_at": stale}))
            result = run_audit(
                REPO_ROOT,
                hermes,
                controls=[c for c in CONTROLS if c.control_id == "CTRL-CC7-02"],
            )
            self.assertFalse(result.status["controls"][0]["passing"])

    def test_release_integrity_spot_check_detects_a_tampered_sampled_file(self) -> None:
        """LPOS-02: deleting/altering the operating artifact fails the check."""

        import shutil

        with tempfile.TemporaryDirectory() as repo_copy, tempfile.TemporaryDirectory() as hermes:
            copy = Path(repo_copy)
            for rel in (
                "RELEASE.json",
                "CHANGELOG.md",
                "RELEASE-MANIFEST.json",
                "SHA256SUMS",
                "verify_release.py",
            ):
                shutil.copyfile(REPO_ROOT / rel, copy / rel)
            manifest = json.loads((copy / "RELEASE-MANIFEST.json").read_text())
            version = json.loads((copy / "RELEASE.json").read_text())["version"]
            import random as random_module

            sample = random_module.Random(f"lpos-release-integrity-{version}").sample(
                sorted(manifest["files"]), 5
            )
            for rel in sample:
                target = copy / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                source = REPO_ROOT / rel
                if source.is_file():
                    shutil.copyfile(source, target)
            # Tamper with one sampled file.
            tampered = copy / sample[0]
            tampered.write_bytes(tampered.read_bytes() + b"\n# tampered\n")
            result = run_audit(
                copy,
                Path(hermes),
                controls=[c for c in CONTROLS if c.control_id == "CTRL-CC8-01"],
            )
            doc = result.status["controls"][0]
            self.assertFalse(doc["passing"])
            self.assertIn("spot-check failed", doc["evidence"])


class RemediationTests(unittest.TestCase):
    def test_failing_control_produces_a_staged_remediation_and_record_only_plan(self) -> None:
        before = _snapshot_repo()
        with tempfile.TemporaryDirectory() as directory:
            hermes = Path(directory)
            control = _failing_control()
            result = run_audit(REPO_ROOT, hermes, controls=[control])
            self.assertEqual(result.overall, "gaps")

            plan = build_and_stage_remediations(
                [(control, "injected failure for the test")],
                repo_root=REPO_ROOT,
                hermes_root=hermes,
                run_id="RUN-TEST",
            )
            self.assertEqual(len(plan["remediations"]), 1)
            remediation = plan["remediations"][0]
            staged_dir = Path(remediation["staged_dir"])
            self.assertTrue(
                staged_dir.is_relative_to(hermes / "compliance" / "staging" / "RUN-TEST")
            )
            self.assertTrue((staged_dir / "REMEDIATION.md").is_file())
            self.assertTrue((staged_dir / "validation.json").is_file())
            self.assertTrue((staged_dir / "CHANGELOG.md").is_file())
            self.assertEqual(
                (staged_dir / "CHANGELOG.md").read_bytes(),
                (REPO_ROOT / "CHANGELOG.md").read_bytes(),
            )

            validation = json.loads((staged_dir / "validation.json").read_text())
            self.assertFalse(validation["validated"])  # honest: fix not applied yet
            self.assertIn("proving_test", validation)

            adoption = plan["adoption"]
            self.assertEqual(adoption["mode"], "record-only")
            self.assertTrue(adoption["approval_required"])
            self.assertEqual(
                adoption["actions"][0]["action_id"], "ADOPT-CTRL-TEST-01-RUN-TEST"
            )
            self.assertEqual(adoption["actions"][0]["staged_path"], str(staged_dir))

            # The staging event lands in the audit history with its run id.
            events = [
                json.loads(line)
                for line in (hermes / "compliance" / "history.jsonl").read_text().splitlines()
            ]
            staged_events = [e for e in events if e.get("event") == "remediation_staged"]
            self.assertTrue(staged_events)
            self.assertEqual(staged_events[0]["run_id"], "RUN-TEST")
        self.assertEqual(before, _snapshot_repo(), "remediation must not touch the repo")

    def test_nothing_failing_returns_the_empty_plan(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            plan = build_and_stage_remediations(
                [], repo_root=REPO_ROOT, hermes_root=Path(directory), run_id="RUN-EMPTY"
            )
            self.assertEqual(plan["remediations"], [])
            self.assertEqual(plan["adoption"], "none")

    def test_staging_refuses_a_path_inside_the_repo_root(self) -> None:
        control = _failing_control()
        with self.assertRaises(ValidationError):
            stage_remediation(
                control,
                "evidence",
                repo_root=REPO_ROOT,
                hermes_root=REPO_ROOT / "build" / "hermes-in-repo",
                run_id="RUN-BAD",
            )
        self.assertFalse((REPO_ROOT / "build" / "hermes-in-repo" / "compliance" / "staging"
                          / "RUN-BAD" / control.control_id / "REMEDIATION.md").exists())

    def test_staging_refuses_a_live_or_production_looking_path(self) -> None:
        control = _failing_control()
        with tempfile.TemporaryDirectory() as directory:
            for token in ("production-state", "live-system"):
                with self.assertRaises(ValidationError):
                    stage_remediation(
                        control,
                        "evidence",
                        repo_root=REPO_ROOT,
                        hermes_root=Path(directory) / token,
                        run_id="RUN-BAD",
                    )


class EvidenceMathTests(unittest.TestCase):
    def test_ratio_at_the_098_boundary_is_operating(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            hermes = Path(directory)
            control = _passing_control()
            # 99 seeded runs over 45 days: 2 fails -> with the current passing
            # run, 98/100 = exactly 0.98.
            _seed_runs(hermes, control.control_id, runs=99, days=45, fails=2)
            result = run_audit(REPO_ROOT, hermes, controls=[control])
            doc = result.status["controls"][0]
            self.assertEqual(doc["rows_in_window"], 100)
            self.assertEqual(doc["passes_in_window"], 98)
            self.assertAlmostEqual(doc["pass_ratio"], 0.98)
            self.assertEqual(doc["verdict"], "operating")

    def test_ratio_below_the_boundary_is_insufficient_history(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            hermes = Path(directory)
            control = _passing_control()
            _seed_runs(hermes, control.control_id, runs=100, days=45, fails=3)
            result = run_audit(REPO_ROOT, hermes, controls=[control])
            doc = result.status["controls"][0]
            self.assertLess(doc["pass_ratio"], 0.98)
            self.assertEqual(doc["verdict"], "insufficient_history")

    def test_entries_outside_the_observation_window_are_excluded(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            hermes = Path(directory)
            control = _passing_control()
            base = datetime.now(timezone.utc) - timedelta(days=200)
            audit_module.append_history(
                hermes,
                [
                    {
                        "ts": (base + timedelta(minutes=i)).isoformat(),
                        "run_id": f"RUN-OLD-{i}",
                        "event": "check",
                        "control_id": control.control_id,
                        "passing": False,
                        "evidence": "old",
                    }
                    for i in range(50)
                ],
            )
            result = run_audit(REPO_ROOT, hermes, controls=[control])
            doc = result.status["controls"][0]
            self.assertEqual(doc["rows_in_window"], 1)  # only the current run
            self.assertEqual(doc["distinct_runs"], 1)
            self.assertEqual(doc["verdict"], "insufficient_history")


class ReportTests(unittest.TestCase):
    def _status(self) -> dict:
        return {
            "generated_at": "2026-07-22T00:00:00+00:00",
            "framework": "SOC 2 Type 2 (TSC 2017, 2022 POF)",
            "assessment": "control_readiness_monitor",
            "attestation": False,
            "issued_by_cpa": False,
            "self_assessment": True,
            "evidence_period_status": "insufficient",
            "run_id": "RUN-TEST",
            "distinct_runs": 12,
            "distinct_run_days": 12,
            "days_of_history": 12,
            "window_days": 90,
            "overall": "gaps",
            "controls": [
                {
                    "control_id": "CTRL-CC8-01",
                    "tsc_id": "CC8",
                    "title": "Release change management artifacts",
                    "category": "critical",
                    "assurance": "outcome",
                    "control_objective": "Release integrity verifies.",
                    "owner": "Principal",
                    "frequency": "daily",
                    "evidence_source": "manifest",
                    "passing": False,
                    "evidence": 'broken by <script>alert("x")</script> & "quotes"',
                    "rows_in_window": 10,
                    "passes_in_window": 4,
                    "distinct_runs": 10,
                    "distinct_run_days": 10,
                    "pass_ratio": 0.4,
                    "verdict": "failing",
                },
                {
                    "control_id": "CTRL-PI-01",
                    "tsc_id": "PI",
                    "title": "Idempotent processing",
                    "category": "critical",
                    "assurance": "structural",
                    "control_objective": "Processing is idempotent.",
                    "owner": "Principal",
                    "frequency": "daily",
                    "evidence_source": "operations.py",
                    "passing": True,
                    "evidence": "ok",
                    "rows_in_window": 10,
                    "passes_in_window": 10,
                    "distinct_runs": 10,
                    "distinct_run_days": 10,
                    "pass_ratio": 1.0,
                    "verdict": "insufficient_history",
                },
            ],
            "not_evidenced": [
                {
                    "id": "ORG-CC1-01",
                    "tsc_id": "CC1",
                    "requirement": "Governance oversight operating",
                    "basis": "requires organizational evidence — not machine-checkable",
                }
            ],
            "summary": {
                "total": 2, "passing": 1, "failing": 1,
                "operating": 0, "structural_evidence_only": 0,
                "insufficient_history": 1, "not_evidenced": 1,
            },
        }

    def test_report_contains_all_sections_and_is_well_formed(self) -> None:
        remediations = [
            {
                "control_id": "CTRL-CC8-01",
                "problem": "evidence",
                "proposed_fix": "Restore CHANGELOG.md <entry>",
                "staged_paths": ["/tmp/x/CHANGELOG.md"],
                "staged_dir": "/tmp/x",
                "validation": {"validated": False, "note": "not validated"},
            }
        ]
        log = [
            {"ts": "2026-07-22T00:00:00+00:00", "run_id": "RUN-TEST", "event": "check",
             "control_id": "CTRL-CC8-01", "passing": False, "evidence": "e < f"},
            {"ts": "2026-07-22T00:01:00+00:00", "run_id": "RUN-TEST",
             "event": "remediation_staged",
             "control_id": "CTRL-CC8-01", "evidence": "staged"},
        ]
        html = render_report(
            self._status(), remediations, log,
            adoption={"mode": "record-only", "approval_required": True, "actions": []},
        )

        for marker in (
            '<section id="status"', '<section id="problems"',
            '<section id="not-evidenced"', '<section id="fixes"',
            '<section id="audit-log"', '<section id="matrix"',
            "LPOS Control Readiness Report", "self-assessment",
            "issued by an independent CPA",
            "Requires Organizational Evidence",
            "requires organizational evidence — not machine-checkable",
            "The Problems", "The Fixes", "Audit Log", "Control Matrix",
            "GAPS FOUND", "awaiting approval", "not validated",
        ):
            self.assertIn(marker, html)

        _assert_no_self_certification(self, html)

        # Basic well-formedness: balanced document and section tags.
        self.assertEqual(html.count("<html"), 1)
        self.assertEqual(html.count("</html>"), 1)
        self.assertEqual(html.count("<section"), html.count("</section>"))
        self.assertEqual(html.count("<table"), html.count("</table>"))

        # User strings never break out of tags.
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)
        self.assertIn("&lt;entry&gt;", html)

    def test_zero_day_fresh_status_reads_not_assessed_not_green(self) -> None:
        """LPOS-01: a fresh page must visibly read NOT ASSESSED, never green."""

        status = self._status()
        status.update(
            overall="not_assessed",
            distinct_runs=0,
            distinct_run_days=0,
            days_of_history=0,
            controls=[],
            summary={},
        )
        html = render_report(status, [], [])
        self.assertIn("NOT ASSESSED", html)
        self.assertIn("0 of 90 observation days", html)
        self.assertIn("insufficient operating evidence", html)
        _assert_no_self_certification(self, html)

    def test_insufficient_evidence_hero(self) -> None:
        status = self._status()
        status.update(overall="insufficient_evidence", distinct_run_days=1, distinct_runs=1)
        html = render_report(status, [], [])
        self.assertIn("INSUFFICIENT EVIDENCE", html)
        self.assertIn("1 of 90 observation days", html)

    def test_audit_log_display_is_capped_at_200(self) -> None:
        log = [
            {"ts": f"2026-07-{(i % 28) + 1:02}T00:00:00+00:00", "event": "check",
             "control_id": f"CTRL-N-{i}", "passing": True, "evidence": "e"}
            for i in range(350)
        ]
        html = render_report(self._status(), [], log)
        self.assertNotIn("CTRL-N-149", html)
        self.assertIn("CTRL-N-150", html)
        self.assertIn("CTRL-N-349", html)


class StandingOperationTests(unittest.TestCase):
    def test_so_025_runs_end_to_end_through_the_runner(self) -> None:
        workflow = WorkflowDefinition.from_dict(
            json.loads(
                (REPO_ROOT / "src" / "lpos_engine" / "workflows" / "SO-025.json").read_text()
            )
        )
        self.assertEqual(workflow.so_id, "SO-025")
        self.assertEqual(workflow.model_class, "routine")

        with tempfile.TemporaryDirectory() as directory:
            hermes = Path(directory)
            store = SQLiteStore(hermes / "state.db")
            runner = StandingOperationRunner(store, handlers=HANDLERS)
            execution = runner.run(
                workflow,
                scheduled_for="2026-07-22T06:00",
                initial_context={
                    "repo_root": str(REPO_ROOT),
                    "hermes_root": str(hermes),
                },
            )
            self.assertEqual(execution.run.result, OperationResult.OK)
            for step_id in ("STEP-INVENTORY", "STEP-AUDIT", "STEP-REMEDIATE", "STEP-REPORT"):
                self.assertIn(step_id, execution.outputs)

            inventory = execution.outputs["STEP-INVENTORY"]
            self.assertEqual(inventory["control_count"], len(CONTROLS))
            audit_out = execution.outputs["STEP-AUDIT"]
            # A first execution can never be green (LPOS-01).
            self.assertIn(audit_out["overall"], ("insufficient_evidence", "gaps"))
            self.assertIs(audit_out["attestation"], False)
            self.assertIs(audit_out["issued_by_cpa"], False)
            self.assertIs(audit_out["self_assessment"], True)
            self.assertEqual(audit_out["distinct_runs"], 1)
            if not audit_out["failing"]:
                remediate = execution.outputs["STEP-REMEDIATE"]
                self.assertEqual(list(remediate["remediations"]), [])
                self.assertEqual(remediate["adoption"], "none")
            report_out = execution.outputs["STEP-REPORT"]
            self.assertTrue(Path(report_out["report_path"]).is_file())
            html = Path(report_out["report_path"]).read_text(encoding="utf-8")
            self.assertIn("LPOS Control Readiness Report", html)
            self.assertTrue(
                "INSUFFICIENT EVIDENCE" in html or "GAPS FOUND" in html,
                "fresh report must not read green",
            )
            self.assertIn('<section id="matrix"', html)
            _assert_no_self_certification(self, html)


if __name__ == "__main__":
    unittest.main()
