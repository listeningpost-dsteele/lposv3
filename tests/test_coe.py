from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

from lpos_engine.coe import run_audit
from lpos_engine.coe_contract import (
    GATE_IDS,
    ZERO_HASH,
    canonical_json,
    evidence_hash,
    redact,
    release_scope,
    sha256_bytes,
    sortable_id,
    validate_gate_evidence,
    verify_evidence_chain,
)
from lpos_engine.coe_gate import _secret_candidates
from lpos_engine.coe_runtime import GateRunner, ReleaseController, central_date, daily_idempotency_key, perform_backup_restore, wake_decision
from lpos_engine.coe_store import COEStore

RELEASE = {
    "product": "chip-service",
    "release_version": "4.5.0",
    "release_channel": "stable",
    "git_commit": "a" * 40,
    "build_id": "build-1",
    "artifact_sha256": "b" * 64,
}


def evidence(gate_id: str, audit_id: str, previous: str, status: str = "pass") -> dict:
    record = {
        "schema_version": 1,
        "evidence_id": sortable_id("evidence"),
        "audit_id": audit_id,
        "gate_id": gate_id,
        "gate_version": "1.0.0",
        "status": status,
        "started_at": "2026-07-28T12:00:00Z",
        "completed_at": "2026-07-28T12:00:01Z",
        "duration_ms": 1000,
        "executable": sys.executable,
        "arguments": ["-m", "test"],
        "exit_code": 0 if status == "pass" else 1,
        "signal": None,
        "release": RELEASE,
        "git_commit": RELEASE["git_commit"],
        "input_hashes": {},
        "checks": [{"check_id": "real-check", "status": "pass" if status == "pass" else "fail", "detail": "command ran"}],
        "stdout_sha256": sha256_bytes(b""),
        "stderr_sha256": sha256_bytes(b""),
        "stdout_excerpt": "",
        "stderr_excerpt": "",
        "artifacts": [],
        "previous_evidence_hash": previous,
        "source": "command",
    }
    record["evidence_hash"] = evidence_hash(record, previous)
    return record


def create_audit(store: COEStore, audit_id: str) -> None:
    store.create_audit(
        audit_id=audit_id,
        trigger="pre-release",
        local_date="2026-07-28",
        timezone_name="America/Chicago",
        idempotency_key=f"pre-release:{audit_id}",
        release_version="4.5.0",
        git_commit=RELEASE["git_commit"],
        artifact_sha256=RELEASE["artifact_sha256"],
        baseline_audit_id=None,
    )


def test_missing_staged_release_is_fail_closed(tmp_path: Path) -> None:
    result = run_audit(tmp_path, state_root=tmp_path / "state")
    assert result["status"] == "blocked"
    assert result["ready_for_dan_approval"] is False
    assert result["gates"] == []
    assert result["decision_reason_codes"] == ["STAGED_RELEASE_REQUIRED"]


def test_canonical_json_and_evidence_hash_are_stable() -> None:
    assert canonical_json({"b": 2, "a": 1}) == '{"a":1,"b":2}'
    first = evidence(GATE_IDS[0], "audit-1722168000000-0123456789abcdef", ZERO_HASH)
    validate_gate_evidence(first, expected_previous_hash=ZERO_HASH)
    assert len(first["evidence_hash"]) == 64


def test_evidence_hash_tampering_fails() -> None:
    record = evidence(GATE_IDS[0], "audit-1722168000000-0123456789abcdef", ZERO_HASH)
    record["checks"][0]["detail"] = "changed"
    with pytest.raises(ValueError, match="hash mismatch"):
        validate_gate_evidence(record)


def test_chain_requires_all_nine_gates() -> None:
    audit_id = "audit-1722168000000-0123456789abcdef"
    rows = []
    previous = ZERO_HASH
    for gate_id in GATE_IDS:
        row = evidence(gate_id, audit_id, previous)
        rows.append(row)
        previous = row["evidence_hash"]
    verify_evidence_chain(rows)
    with pytest.raises(ValueError, match="incomplete"):
        verify_evidence_chain(rows[:-1])


def test_sqlite_evidence_and_decisions_are_append_only(tmp_path: Path) -> None:
    store = COEStore(tmp_path)
    audit_id = sortable_id("audit")
    create_audit(store, audit_id)
    row = evidence(GATE_IDS[0], audit_id, ZERO_HASH)
    store.insert_evidence(row)
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        with store.engine.transaction() as conn:
            conn.execute("UPDATE coe_gate_evidence SET status='fail' WHERE evidence_id=?", (row["evidence_id"],))
    decision = {"audit_id": audit_id, "status": "blocked", "decision_hash": "c" * 64}
    store.insert_decision(audit_id, "blocked", decision["decision_hash"], decision)
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        with store.engine.transaction() as conn:
            conn.execute("DELETE FROM coe_release_decisions WHERE audit_id=?", (audit_id,))


def test_release_controller_blocks_missing_evidence(tmp_path: Path) -> None:
    store = COEStore(tmp_path)
    audit_id = sortable_id("audit")
    create_audit(store, audit_id)
    decision = ReleaseController(store).decide(audit_id, RELEASE)
    assert decision["status"] == "blocked"
    assert "GATE_MISSING" in decision["decision_reason_codes"]
    assert "DOCUMENTATION_PASSOFF_UNVERIFIED" in decision["decision_reason_codes"]


def test_gate_runner_rejects_zero_exit_without_evidence(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    store = COEStore(tmp_path)
    audit_id = sortable_id("audit")
    create_audit(store, audit_id)

    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(args[0], 0, stdout=b"ok", stderr=b"")

    monkeypatch.setattr("lpos_engine.coe_runtime.subprocess.run", fake_run)
    runner = GateRunner(store)
    with pytest.raises(ValueError, match="did not create"):
        runner.run(
            "deterministic-tests",
            {"audit_id": audit_id, "repo": str(tmp_path), "release": RELEASE},
        )


def test_redaction_covers_credentials_and_home_paths() -> None:
    value = "Authorization: Bearer abc123 password=secretsecretsecret /Users/dan/private"
    result = redact(value)
    assert "abc123" not in result
    assert "secretsecretsecret" not in result
    assert "/Users/dan" not in result
    assert result.count("[REDACTED]") >= 2


def test_daily_idempotency_and_dst_use_central_date() -> None:
    instant = datetime(2026, 11, 1, 6, 30, tzinfo=timezone.utc)
    assert central_date(instant) == "2026-11-01"
    assert daily_idempotency_key(instant) == "coe-daily:2026-11-01 America/Chicago"


def test_audit_lock_prevents_overlap(tmp_path: Path) -> None:
    store = COEStore(tmp_path)
    assert store.acquire_lock("coe-daily:2026-07-28 America/Chicago", "first", 60) is True
    assert store.acquire_lock("coe-daily:2026-07-28 America/Chicago", "second", 60) is False
    store.release_lock("coe-daily:2026-07-28 America/Chicago", "first")
    assert store.acquire_lock("coe-daily:2026-07-28 America/Chicago", "second", 60) is True


def test_backup_restore_is_real_isolated_and_hash_verified(tmp_path: Path) -> None:
    store = COEStore(tmp_path)
    audit_id = sortable_id("audit")
    create_audit(store, audit_id)
    result = perform_backup_restore(store, audit_id)
    assert result["status"] == "pass"
    assert result["hash_verified"] is True
    assert result["sqlite_integrity"] == "ok"
    assert result["sentinel_records"] == 1
    assert result["isolated"] is True


def test_wake_policy_defaults_to_no_model_call() -> None:
    decision = wake_decision(eligible=True, qualifying_input=False)
    assert decision == {
        "eligible": True,
        "wakeAgent": False,
        "reason_code": "NO_NEW_INPUT",
        "decision_source": "deterministic-policy",
        "model_invoked": False,
    }


def test_release_scope_rejects_invalid_artifact() -> None:
    with pytest.raises(ValueError, match="artifact"):
        release_scope({"product": "x", "release_version": "4.5.0", "release_channel": "stable", "git_commit": "a" * 40}, build_id="x", artifact_sha256="bad")


def test_secret_scan_rejects_credentials_without_flagging_environment_lookups(tmp_path: Path) -> None:
    candidate = tmp_path / "candidate.js"
    candidate.write_text('const password = "RealCredentialValue12345";\n', encoding="utf-8")
    assert _secret_candidates([tmp_path]) == [str(candidate)]
    candidate.write_text('const password = process.env.PASSWORD;\n', encoding="utf-8")
    assert _secret_candidates([tmp_path]) == []