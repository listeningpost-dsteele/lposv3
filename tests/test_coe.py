from __future__ import annotations

import json
from pathlib import Path

from lpos_engine.coe import load_latest, run_audit


def _repo(tmp_path: Path, *, verifier_exit: int = 0) -> Path:
    repo = tmp_path / "release"
    repo.mkdir()
    (repo / "RELEASE.json").write_text('{"version":"4.5.0"}\n', encoding="utf-8")
    (repo / "RELEASE-MANIFEST.json").write_text('{"files":{}}\n', encoding="utf-8")
    (repo / "verify_release.py").write_text(
        f"import sys\nprint('fixture verifier')\nsys.exit({verifier_exit})\n",
        encoding="utf-8",
    )
    for relative in (
        "README.md",
        "CHANGELOG.md",
        "docs/ARCHITECTURE.md",
        "docs/TESTING.md",
        "docs/wiki/administration/cli-reference.md",
        "docs/wiki/administration/backups.md",
    ):
        target = repo / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("fixture\n", encoding="utf-8")
    return repo


def test_audit_writes_dashboard_report_email_and_history(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    hermes = tmp_path / "hermes"
    (hermes / "cron").mkdir(parents=True)
    (hermes / "cron" / "jobs.json").write_text('{"jobs":[]}\n', encoding="utf-8")
    state = tmp_path / "state"

    result = run_audit(repo, hermes, state, "http://127.0.0.1:7374/dashboard/coe")

    assert result["release_ready"] is True
    assert result["release_version"] == "4.5.0"
    assert result["audit_id"].startswith("COE-")
    assert load_latest(state)["audit_id"] == result["audit_id"]
    assert "Operational health and release readiness" in (state / "coe" / "dashboard.html").read_text()
    assert "Subject: LPOS Continuous Operational Excellence Report" in (state / "coe" / "daily-email.md").read_text()
    assert len((state / "coe" / "history.jsonl").read_text().splitlines()) == 1
    assert result["audit_history"][-1]["audit_id"] == result["audit_id"]
    second = run_audit(repo, hermes, state, "http://127.0.0.1:7374/dashboard/coe")
    assert len((state / "coe" / "history.jsonl").read_text().splitlines()) == 2
    assert [item["audit_id"] for item in second["audit_history"]][-2:] == [result["audit_id"], second["audit_id"]]
    assert result["audit_id"] in (state / "coe" / "dashboard.html").read_text()


def test_mutable_database_inside_release_blocks_readiness(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    (repo / "state").mkdir()
    (repo / "state" / "lpos.db").write_bytes(b"mutable")
    result = run_audit(repo, tmp_path / "hermes", tmp_path / "state", "http://127.0.0.1:7374/dashboard/coe")
    assert result["release_ready"] is False
    assert "mutable_immutable_boundary" in result["release_blockers"]


def test_failed_release_verifier_blocks_release(tmp_path: Path) -> None:
    repo = _repo(tmp_path, verifier_exit=4)
    hermes = tmp_path / "hermes"
    state = tmp_path / "state"

    result = run_audit(repo, hermes, state, "http://127.0.0.1:7374/dashboard/coe")

    assert result["release_ready"] is False
    assert "release_integrity" in result["release_blockers"]


def test_scheduler_prompt_and_wake_agent_findings_are_evidence_based(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    hermes = tmp_path / "hermes"
    (hermes / "cron").mkdir(parents=True)
    jobs = {
        "jobs": [
            {
                "id": "legacy",
                "name": "Daily Check",
                "enabled": True,
                "schedule": "*/10 * * * *",
                "prompt": "Use LPOS v3 from the current workdir.",
            },
            {
                "id": "duplicate",
                "name": "Daily Check",
                "enabled": True,
                "schedule": "0 8 * * *",
                "prompt": "Current release only.",
            },
            {
                "id": "fixture",
                "name": "claim job",
                "enabled": True,
                "schedule": "0 9 * * *",
                "prompt": "fixture",
            },
        ]
    }
    (hermes / "cron" / "jobs.json").write_text(json.dumps(jobs), encoding="utf-8")

    result = run_audit(repo, hermes, tmp_path / "state", "http://127.0.0.1:7374/dashboard/coe")
    by_domain = {item["domain"]: item for item in result["findings"]}

    assert by_domain["scheduler_governance"]["status"] == "warn"
    assert by_domain["scheduler_governance"]["evidence"]["fixture_job_ids"] == ["fixture"]
    assert by_domain["prompt_drift"]["evidence"]["drift"] == [{"job_id": "legacy", "match": "Use LPOS v3"}]
    assert by_domain["wake_agent_efficiency"]["evidence"]["ungated_jobs"] == ["legacy"]


def test_release_gate_records_deterministic_evaluations(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    result = run_audit(
        repo,
        tmp_path / "hermes",
        tmp_path / "state",
        "http://127.0.0.1:7374/dashboard/coe",
        include_evaluations=True,
    )
    evaluation = next(item for item in result["findings"] if item["domain"] == "deterministic_evaluations")
    assert evaluation["status"] == "pass"
    assert evaluation["evidence"] == {"passed": 70, "failed": 0, "total": 70}


def test_compatibility_job_requires_technical_debt_record(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    hermes = tmp_path / "hermes"
    (hermes / "cron").mkdir(parents=True)
    (hermes / "cron" / "jobs.json").write_text(
        json.dumps({"jobs": [{"id": "compat", "name": "Reader", "prompt": "Read the compatibility ledger"}]}),
        encoding="utf-8",
    )
    result = run_audit(repo, hermes, tmp_path / "state", "http://127.0.0.1:7374/dashboard/coe")
    debt_result = next(item for item in result["findings"] if item["domain"] == "technical_debt_lifecycle")
    assert debt_result["status"] == "warn"
    assert debt_result["evidence"]["undocumented_compatibility"] is True


def test_valid_technical_debt_record_passes(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    hermes = tmp_path / "hermes"
    state = tmp_path / "state"
    debt = state / "coe" / "technical-debt.json"
    debt.parent.mkdir(parents=True)
    debt.write_text(
        json.dumps(
            [
                {
                    "id": "TD-001",
                    "owner": "Platform",
                    "rationale": "Temporary compatibility boundary",
                    "retirement_date": "2099-01-01",
                    "migration_plan": "Import then remove",
                    "status": "open",
                }
            ]
        ),
        encoding="utf-8",
    )

    result = run_audit(repo, hermes, state, "http://127.0.0.1:7374/dashboard/coe")
    debt_result = next(item for item in result["findings"] if item["domain"] == "technical_debt_lifecycle")
    assert debt_result["status"] == "pass"
