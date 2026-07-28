"""Append-only SQLite persistence for COE audits and release evidence."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

from .coe_contract import ZERO_HASH, canonical_json, sortable_id, utc_now, validate_gate_evidence, verify_evidence_chain
from .store import SQLiteStore


def default_state_root() -> Path:
    import os

    configured = os.environ.get("COE_STATE_DIR") or os.environ.get("HERMES_STATE_DIR")
    base = Path(configured).expanduser() if configured else Path.home() / ".hermes" / "state"
    return (base / "chip-service" if base.name != "chip-service" else base).resolve()


class COEStore:
    """COE projection over the LPOS v4 transactional SQLite store."""

    def __init__(self, state_root: Path | None = None) -> None:
        self.state_root = Path(state_root or default_state_root()).expanduser().resolve()
        self.root = self.state_root / "coe"
        self.root.mkdir(parents=True, exist_ok=True)
        self.engine = SQLiteStore(self.root / "coe.db")

    def create_audit(
        self,
        *,
        audit_id: str,
        trigger: str,
        local_date: str,
        timezone_name: str,
        idempotency_key: str,
        release_version: str,
        git_commit: str,
        artifact_sha256: str,
        baseline_audit_id: str | None,
    ) -> dict[str, Any]:
        started_at = utc_now()
        payload = {
            "audit_id": audit_id,
            "trigger": trigger,
            "local_date": local_date,
            "timezone": timezone_name,
            "idempotency_key": idempotency_key,
            "release_version": release_version,
            "git_commit": git_commit,
            "artifact_sha256": artifact_sha256,
            "baseline_audit_id": baseline_audit_id,
            "status": "running",
            "started_at": started_at,
            "completed_at": None,
        }
        with self.engine.transaction() as conn:
            conn.execute(
                "INSERT INTO coe_audits(audit_id, trigger_name, local_date, timezone, idempotency_key, "
                "release_version, git_commit, artifact_sha256, baseline_audit_id, status, started_at, completed_at, audit_json) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    audit_id, trigger, local_date, timezone_name, idempotency_key, release_version, git_commit,
                    artifact_sha256, baseline_audit_id, "running", started_at, None, canonical_json(payload),
                ),
            )
        return payload

    def complete_audit(self, audit_id: str, status: str, payload: Mapping[str, Any]) -> None:
        if status not in {"pass", "blocked", "failed"}:
            raise ValueError("invalid terminal audit status")
        completed_at = utc_now()
        final = dict(payload)
        final["status"] = status
        final["completed_at"] = completed_at
        with self.engine.transaction() as conn:
            updated = conn.execute(
                "UPDATE coe_audits SET status=?, completed_at=?, audit_json=? WHERE audit_id=? AND status='running'",
                (status, completed_at, canonical_json(final), audit_id),
            ).rowcount
            if updated != 1:
                raise ValueError("audit is absent or already terminal")

    def latest_audit(self) -> dict[str, Any] | None:
        with self.engine.connection() as conn:
            row = conn.execute(
                "SELECT audit_json FROM coe_audits ORDER BY started_at DESC LIMIT 1"
            ).fetchone()
        return json.loads(row["audit_json"]) if row else None

    def audit(self, audit_id: str) -> dict[str, Any] | None:
        with self.engine.connection() as conn:
            row = conn.execute("SELECT audit_json FROM coe_audits WHERE audit_id=?", (audit_id,)).fetchone()
        return json.loads(row["audit_json"]) if row else None

    def audits(self, limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
        limit = max(1, min(int(limit), 100))
        offset = max(0, int(offset))
        with self.engine.connection() as conn:
            rows = conn.execute(
                "SELECT audit_json FROM coe_audits ORDER BY started_at DESC LIMIT ? OFFSET ?", (limit, offset)
            ).fetchall()
        return [json.loads(row["audit_json"]) for row in rows]

    def previous_evidence_hash(self, audit_id: str) -> str:
        with self.engine.connection() as conn:
            row = conn.execute(
                "SELECT evidence_hash FROM coe_gate_evidence WHERE audit_id=? ORDER BY rowid DESC LIMIT 1", (audit_id,)
            ).fetchone()
        return str(row["evidence_hash"]) if row else ZERO_HASH

    def insert_evidence(self, record: Mapping[str, Any]) -> None:
        expected = self.previous_evidence_hash(str(record.get("audit_id", "")))
        validate_gate_evidence(record, expected_previous_hash=expected)
        with self.engine.transaction() as conn:
            conn.execute(
                "INSERT INTO coe_gate_evidence(evidence_id,audit_id,gate_id,status,completed_at,previous_evidence_hash,evidence_hash,evidence_json) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (
                    record["evidence_id"], record["audit_id"], record["gate_id"], record["status"],
                    record["completed_at"], record["previous_evidence_hash"], record["evidence_hash"],
                    canonical_json(dict(record)),
                ),
            )

    def evidence(self, audit_id: str) -> list[dict[str, Any]]:
        with self.engine.connection() as conn:
            rows = conn.execute(
                "SELECT evidence_json FROM coe_gate_evidence WHERE audit_id=? ORDER BY rowid", (audit_id,)
            ).fetchall()
        return [json.loads(row["evidence_json"]) for row in rows]

    def verify_audit_chain(self, audit_id: str) -> list[dict[str, Any]]:
        records = self.evidence(audit_id)
        verify_evidence_chain(records)
        return records

    def insert_decision(self, audit_id: str, status: str, decision_hash: str, payload: Mapping[str, Any]) -> str:
        if status not in {"pass", "blocked"}:
            raise ValueError("invalid release decision status")
        decision_id = sortable_id("decision")
        with self.engine.transaction() as conn:
            conn.execute(
                "INSERT INTO coe_release_decisions(decision_id,audit_id,status,decision_hash,decision_json,created_at) "
                "VALUES (?,?,?,?,?,?)",
                (decision_id, audit_id, status, decision_hash, canonical_json(dict(payload)), utc_now()),
            )
        return decision_id

    def decision(self, audit_id: str | None = None) -> dict[str, Any] | None:
        query = "SELECT decision_json FROM coe_release_decisions"
        values: tuple[Any, ...] = ()
        if audit_id:
            query += " WHERE audit_id=?"
            values = (audit_id,)
        query += " ORDER BY created_at DESC LIMIT 1"
        with self.engine.connection() as conn:
            row = conn.execute(query, values).fetchone()
        return json.loads(row["decision_json"]) if row else None

    def insert_finding(self, audit_id: str, finding: Mapping[str, Any]) -> str:
        finding_id = str(finding.get("finding_id") or sortable_id("finding"))
        with self.engine.transaction() as conn:
            conn.execute(
                "INSERT INTO coe_findings(finding_id,audit_id,severity,status,owner,finding_json,created_at) VALUES (?,?,?,?,?,?,?)",
                (
                    finding_id, audit_id, finding.get("severity", "info"), finding.get("status", "open"),
                    finding.get("owner"), canonical_json(dict(finding)), utc_now(),
                ),
            )
        return finding_id

    def findings(self, *, status: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        query = "SELECT finding_json FROM coe_findings"
        values: list[Any] = []
        if status:
            query += " WHERE status=?"
            values.append(status)
        query += " ORDER BY created_at DESC LIMIT ?"
        values.append(max(1, min(limit, 200)))
        with self.engine.connection() as conn:
            rows = conn.execute(query, tuple(values)).fetchall()
        return [json.loads(row["finding_json"]) for row in rows]

    def insert_opportunity(self, audit_id: str, opportunity: Mapping[str, Any]) -> str:
        opportunity_id = str(opportunity.get("opportunity_id") or sortable_id("opportunity"))
        with self.engine.transaction() as conn:
            conn.execute(
                "INSERT INTO coe_opportunities(opportunity_id,audit_id,finding_id,status,owner,opportunity_json,created_at) VALUES (?,?,?,?,?,?,?)",
                (
                    opportunity_id, audit_id, opportunity.get("finding_id"), opportunity.get("status", "proposed"),
                    opportunity.get("owner"), canonical_json(dict(opportunity)), utc_now(),
                ),
            )
        return opportunity_id

    def opportunities(self, limit: int = 100) -> list[dict[str, Any]]:
        with self.engine.connection() as conn:
            rows = conn.execute(
                "SELECT opportunity_json FROM coe_opportunities ORDER BY created_at DESC LIMIT ?", (max(1, min(limit, 200)),)
            ).fetchall()
        return [json.loads(row["opportunity_json"]) for row in rows]

    def record_operator_decision(self, opportunity_id: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        decision_id = sortable_id("operator-decision")
        record = {
            "operator_decision_id": decision_id,
            "opportunity_id": opportunity_id,
            "decision": payload["decision"],
            "actor": payload["actor"],
            "reason": payload.get("reason"),
            "created_at": utc_now(),
        }
        with self.engine.transaction() as conn:
            exists = conn.execute(
                "SELECT 1 FROM coe_opportunities WHERE opportunity_id=?", (opportunity_id,)
            ).fetchone()
            if not exists:
                raise ValueError("opportunity does not exist")
            conn.execute(
                "INSERT INTO coe_operator_decisions(operator_decision_id,opportunity_id,decision,actor,decision_json,created_at) VALUES (?,?,?,?,?,?)",
                (
                    decision_id, opportunity_id, record["decision"], record["actor"],
                    canonical_json(record), record["created_at"],
                ),
            )
        return record

    def record_metric(self, audit_id: str, name: str, value: float | None, unit: str, status: str, detail: Mapping[str, Any]) -> str:
        metric_id = sortable_id("metric")
        with self.engine.transaction() as conn:
            conn.execute(
                "INSERT INTO coe_metrics(metric_id,audit_id,metric_name,metric_value,unit,status,metric_json,observed_at) VALUES (?,?,?,?,?,?,?,?)",
                (metric_id, audit_id, name, value, unit, status, canonical_json(dict(detail)), utc_now()),
            )
        return metric_id

    def metrics(self, name: str | None = None, limit: int = 365) -> list[dict[str, Any]]:
        query = "SELECT metric_name,metric_value,unit,status,metric_json,observed_at FROM coe_metrics"
        values: list[Any] = []
        if name:
            query += " WHERE metric_name=?"
            values.append(name)
        query += " ORDER BY observed_at DESC LIMIT ?"
        values.append(max(1, min(limit, 1000)))
        with self.engine.connection() as conn:
            rows = conn.execute(query, tuple(values)).fetchall()
        return [
            {
                "name": row["metric_name"], "value": row["metric_value"], "unit": row["unit"],
                "status": row["status"], "detail": json.loads(row["metric_json"]), "observed_at": row["observed_at"],
            }
            for row in rows
        ]

    def ensure_legacy_debt(self) -> None:
        payload = {
            "debt_id": "TD-LEGACY-LPOS-STATE",
            "title": "Import legacy lpos-state ledgers into v4 SQLite",
            "description": "Legacy records remain read-only; new silent runs may not write compatibility records",
            "owner": "LPOS Platform Operations",
            "reason": "Destructive legacy migration is outside the approved COE scope",
            "affected_components": ["/Users/dan/lpos-state", "LPOS v4 state"],
            "severity": "medium",
            "status": "accepted-temporary",
            "retirement_condition": "A separate validated and reversible import completes",
            "review_at": "2026-10-28T00:00:00Z",
            "migration_plan": "Inventory, export, verify, dry-run import, reconcile, and retain rollback",
            "verification_and_rollback": "Hash source ledgers and compare imported record counts before cutover",
        }
        with self.engine.transaction() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO coe_technical_debt(debt_id,status,owner,review_at,debt_json,created_at) VALUES (?,?,?,?,?,?)",
                (
                    payload["debt_id"], payload["status"], payload["owner"], payload["review_at"],
                    canonical_json(payload), utc_now(),
                ),
            )

    def technical_debt(self) -> list[dict[str, Any]]:
        with self.engine.connection() as conn:
            rows = conn.execute("SELECT debt_json FROM coe_technical_debt ORDER BY created_at DESC").fetchall()
        return [json.loads(row["debt_json"]) for row in rows]

    def acquire_lock(self, key: str, owner: str, ttl_seconds: int) -> bool:
        now = datetime.now(timezone.utc)
        expires = now + timedelta(seconds=ttl_seconds)
        now_text = now.isoformat().replace("+00:00", "Z")
        expires_text = expires.isoformat().replace("+00:00", "Z")
        with self.engine.transaction() as conn:
            stale = conn.execute("SELECT expires_at FROM coe_audit_locks WHERE idempotency_key=?", (key,)).fetchone()
            if stale and str(stale["expires_at"]) > now_text:
                return False
            conn.execute("DELETE FROM coe_audit_locks WHERE idempotency_key=?", (key,))
            conn.execute(
                "INSERT INTO coe_audit_locks(idempotency_key,owner,acquired_at,expires_at,heartbeat_at) VALUES (?,?,?,?,?)",
                (key, owner, now_text, expires_text, now_text),
            )
        return True

    def release_lock(self, key: str, owner: str) -> None:
        with self.engine.transaction() as conn:
            conn.execute("DELETE FROM coe_audit_locks WHERE idempotency_key=? AND owner=?", (key, owner))

    def record_delivery(self, audit_id: str, delivery: Mapping[str, Any]) -> str:
        delivery_id = str(delivery.get("delivery_id") or sortable_id("delivery"))
        with self.engine.transaction() as conn:
            conn.execute(
                "INSERT INTO coe_report_deliveries(delivery_id,audit_id,status,attempt_number,provider_message_id,report_hash,delivery_json,started_at,completed_at) VALUES (?,?,?,?,?,?,?,?,?)",
                (
                    delivery_id, audit_id, delivery["status"], int(delivery["attempt_number"]),
                    delivery.get("provider_message_id"), delivery["report_hash"], canonical_json(dict(delivery)),
                    delivery["started_at"], delivery.get("completed_at"),
                ),
            )
        return delivery_id

    def latest_delivery(self, audit_id: str) -> dict[str, Any] | None:
        with self.engine.connection() as conn:
            row = conn.execute(
                "SELECT delivery_json FROM coe_report_deliveries WHERE audit_id=? ORDER BY attempt_number DESC LIMIT 1",
                (audit_id,),
            ).fetchone()
        return json.loads(row["delivery_json"]) if row else None

    def documentation_passoff(self) -> list[dict[str, Any]]:
        with self.engine.connection() as conn:
            rows = conn.execute("SELECT passoff_json FROM coe_documentation_passoff ORDER BY surface").fetchall()
        return [json.loads(row["passoff_json"]) for row in rows]

    def insert_documentation_passoff(self, audit_id: str | None, payload: Mapping[str, Any]) -> str:
        passoff_id = str(payload.get("passoff_id") or sortable_id("passoff"))
        with self.engine.transaction() as conn:
            conn.execute(
                "INSERT INTO coe_documentation_passoff(passoff_id,audit_id,surface,status,reference,content_hash,verified_at,passoff_json) VALUES (?,?,?,?,?,?,?,?)",
                (
                    passoff_id, audit_id, payload["surface"], payload["status"], payload["reference"],
                    payload.get("content_hash"), payload.get("verified_at"), canonical_json(dict(payload)),
                ),
            )
        return passoff_id

    def integrity(self) -> dict[str, Any]:
        return self.engine.integrity_report()
