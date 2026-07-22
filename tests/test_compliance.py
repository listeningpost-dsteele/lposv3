"""SO-025 SOC 2 Type 2 compliance engine tests (fully offline, repo untouched)."""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from lpos_engine.compliance import (
    CONTROLS,
    HANDLERS,
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
    "window_days",
    "overall",
    "controls",
    "summary",
}


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
    )


def _passing_control(control_id: str = "CTRL-TEST-02") -> Control:
    return Control(
        control_id=control_id,
        tsc_id="CC5",
        title="Always-passing test control",
        description="Always passes, for effectiveness math.",
        category="standard",
        check=lambda repo, hermes: ControlResult(passing=True, evidence="ok"),
    )


class FullAuditTests(unittest.TestCase):
    def test_full_audit_runs_and_this_repo_passes_the_release_tree_controls(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            hermes = Path(directory)
            result = run_audit(REPO_ROOT, hermes)

            self.assertTrue(STATUS_CONTRACT_KEYS <= set(result.status))
            self.assertEqual(
                result.status["framework"], "SOC 2 Type 2 (TSC 2017, 2022 POF)"
            )
            self.assertIn(result.status["overall"], ("compliant", "gaps"))

            # The written status.json matches the returned contract.
            written = json.loads((hermes / "compliance" / "status.json").read_text())
            self.assertEqual(written, result.status)

            # History: one check line per control, all JSON.
            lines = (hermes / "compliance" / "history.jsonl").read_text().splitlines()
            self.assertEqual(len(lines), len(CONTROLS))
            for line in lines:
                entry = json.loads(line)
                self.assertIn("ts", entry)
                self.assertIn("control_id", entry)
                self.assertIn("passing", entry)
                self.assertIn("evidence", entry)

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
                "CTRL-CC8-01",
                "CTRL-CC8-02",
                "CTRL-CC9-01",
                "CTRL-C-01",
                "CTRL-PI-01",
            ):
                self.assertTrue(
                    by_id[control_id]["passing"],
                    f"{control_id} should pass on this checkout: {by_id[control_id]['evidence']}",
                )
            self.assertEqual(result.status["overall"], "compliant")

    def test_missing_files_fail_the_control_without_crashing(self) -> None:
        with tempfile.TemporaryDirectory() as empty_repo, tempfile.TemporaryDirectory() as hermes:
            result = run_audit(Path(empty_repo), Path(hermes))
            self.assertEqual(result.overall, "gaps")
            # Every failing control carries evidence saying why.
            for control in result.status["controls"]:
                if not control["passing"]:
                    self.assertTrue(control["evidence"])

    def test_history_is_capped_at_the_limit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            hermes = Path(directory)
            seed = [
                {"ts": "2026-01-01T00:00:00+00:00", "event": "check",
                 "control_id": f"CTRL-SEED-{i}", "passing": True, "evidence": "seed"}
                for i in range(audit_module.HISTORY_LIMIT + 25)
            ]
            entries = audit_module.append_history(hermes, seed)
            self.assertEqual(len(entries), audit_module.HISTORY_LIMIT)
            # Oldest trimmed: the first 25 seeds are gone.
            self.assertEqual(entries[0]["control_id"], "CTRL-SEED-25")


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

            # The staging event lands in the audit history.
            events = [
                json.loads(line)
                for line in (hermes / "compliance" / "history.jsonl").read_text().splitlines()
            ]
            self.assertTrue(
                any(e.get("event") == "remediation_staged" for e in events)
            )
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


class EffectivenessTests(unittest.TestCase):
    def _seed(self, hermes: Path, control_id: str, passes: int, fails: int,
              *, days_ago: float = 1.0) -> None:
        base = datetime.now(timezone.utc) - timedelta(days=days_ago)
        entries = []
        for i in range(passes + fails):
            entries.append(
                {
                    "ts": (base + timedelta(minutes=i)).isoformat(),
                    "event": "check",
                    "control_id": control_id,
                    "passing": i < passes,
                    "evidence": "seed",
                }
            )
        audit_module.append_history(hermes, entries)

    def test_ratio_at_the_098_boundary_is_effective(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            hermes = Path(directory)
            control = _passing_control()
            self._seed(hermes, control.control_id, passes=97, fails=2)
            result = run_audit(REPO_ROOT, hermes, controls=[control])
            doc = result.status["controls"][0]
            self.assertEqual(doc["runs_in_window"], 100)
            self.assertEqual(doc["passes_in_window"], 98)
            self.assertAlmostEqual(doc["effectiveness"], 0.98)
            self.assertEqual(doc["verdict"], "effective")

    def test_ratio_below_the_boundary_is_not_yet_demonstrated(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            hermes = Path(directory)
            control = _passing_control()
            self._seed(hermes, control.control_id, passes=97, fails=3)
            result = run_audit(REPO_ROOT, hermes, controls=[control])
            doc = result.status["controls"][0]
            self.assertEqual(doc["runs_in_window"], 101)
            self.assertEqual(doc["passes_in_window"], 98)
            self.assertLess(doc["effectiveness"], 0.98)
            self.assertEqual(doc["verdict"], "not yet demonstrated")

    def test_a_currently_failing_control_is_ineffective_regardless_of_history(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            hermes = Path(directory)
            control = _failing_control("CTRL-TEST-03", paths=())
            self._seed(hermes, control.control_id, passes=500, fails=0)
            result = run_audit(REPO_ROOT, hermes, controls=[control])
            doc = result.status["controls"][0]
            self.assertEqual(doc["verdict"], "ineffective")

    def test_entries_outside_the_observation_window_are_excluded(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            hermes = Path(directory)
            control = _passing_control()
            self._seed(hermes, control.control_id, passes=0, fails=50, days_ago=200.0)
            result = run_audit(REPO_ROOT, hermes, controls=[control])
            doc = result.status["controls"][0]
            self.assertEqual(doc["runs_in_window"], 1)  # only the current run
            self.assertEqual(doc["verdict"], "effective")


class ReportTests(unittest.TestCase):
    def _status(self) -> dict:
        return {
            "generated_at": "2026-07-22T00:00:00+00:00",
            "framework": "SOC 2 Type 2 (TSC 2017, 2022 POF)",
            "window_days": 90,
            "overall": "gaps",
            "coverage": {"days_of_history": 12, "runs_in_window": 40},
            "controls": [
                {
                    "control_id": "CTRL-CC8-01",
                    "tsc_id": "CC8",
                    "title": "Release change management artifacts",
                    "category": "critical",
                    "passing": False,
                    "evidence": 'broken by <script>alert("x")</script> & "quotes"',
                    "runs_in_window": 10,
                    "passes_in_window": 4,
                    "effectiveness": 0.4,
                    "verdict": "ineffective",
                },
                {
                    "control_id": "CTRL-PI-01",
                    "tsc_id": "PI",
                    "title": "Idempotent processing",
                    "category": "critical",
                    "passing": True,
                    "evidence": "ok",
                    "runs_in_window": 10,
                    "passes_in_window": 10,
                    "effectiveness": 1.0,
                    "verdict": "effective",
                },
            ],
            "summary": {
                "total": 2, "passing": 1, "failing": 1,
                "effective": 1, "not_yet_demonstrated": 0, "ineffective": 1,
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
            {"ts": "2026-07-22T00:00:00+00:00", "event": "check",
             "control_id": "CTRL-CC8-01", "passing": False, "evidence": "e < f"},
            {"ts": "2026-07-22T00:01:00+00:00", "event": "remediation_staged",
             "control_id": "CTRL-CC8-01", "evidence": "staged"},
        ]
        html = render_report(
            self._status(), remediations, log,
            adoption={"mode": "record-only", "approval_required": True, "actions": []},
        )

        for marker in (
            '<section id="status"', '<section id="problems"', '<section id="fixes"',
            '<section id="audit-log"', '<section id="matrix"',
            "The Problems", "The Fixes", "Audit Log", "Control Matrix",
            "GAPS FOUND", "awaiting approval", "not validated",
        ):
            self.assertIn(marker, html)

        # Basic well-formedness: balanced document and section tags.
        self.assertEqual(html.count("<html"), 1)
        self.assertEqual(html.count("</html>"), 1)
        self.assertEqual(html.count("<section"), html.count("</section>"))
        self.assertEqual(html.count("<table"), html.count("</table>"))

        # User strings never break out of tags.
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)
        self.assertIn("&lt;entry&gt;", html)

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
            self.assertEqual(audit_out["overall"], "compliant")
            remediate = execution.outputs["STEP-REMEDIATE"]
            self.assertEqual(list(remediate["remediations"]), [])
            self.assertEqual(remediate["adoption"], "none")
            report_out = execution.outputs["STEP-REPORT"]
            self.assertTrue(Path(report_out["report_path"]).is_file())
            html = Path(report_out["report_path"]).read_text(encoding="utf-8")
            self.assertIn("COMPLIANT", html)
            self.assertIn('<section id="matrix"', html)


if __name__ == "__main__":
    unittest.main()
