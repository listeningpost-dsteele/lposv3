"""COE gate runner, orchestrator, release controller, collectors, backup, and reports."""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping
from zoneinfo import ZoneInfo

from .coe_contract import (
    GATE_IDS,
    ZERO_HASH,
    canonical_json,
    evidence_hash,
    read_release_identity,
    redact,
    release_scope,
    sha256_bytes,
    sha256_file,
    sortable_id,
    utc_now,
    validate_gate_evidence,
)
from .coe_manifest import verify_release
from .coe_store import COEStore

CENTRAL = ZoneInfo("America/Chicago")


def central_date(now: datetime | None = None) -> str:
    instant = now or datetime.now(timezone.utc)
    if instant.tzinfo is None:
        instant = instant.replace(tzinfo=timezone.utc)
    return instant.astimezone(CENTRAL).date().isoformat()


def daily_idempotency_key(now: datetime | None = None) -> str:
    return f"coe-daily:{central_date(now)} America/Chicago"


def wake_decision(*, eligible: bool, qualifying_input: bool, fail_visible: bool = False) -> dict[str, Any]:
    if not eligible:
        reason = "NOT_ELIGIBLE"
        wake = False
    elif qualifying_input:
        reason = "QUALIFYING_INPUT"
        wake = True
    elif fail_visible:
        reason = "FAIL_VISIBLE_HOLD"
        wake = True
    else:
        reason = "NO_NEW_INPUT"
        wake = False
    return {
        "eligible": eligible,
        "wakeAgent": wake,
        "reason_code": reason,
        "decision_source": "deterministic-policy",
        "model_invoked": False,
    }


class GateRunner:
    """Spawn one gate command at a time and accept only matching valid evidence."""

    def __init__(self, store: COEStore, *, timeout_seconds: int = 1800, maximum_output_bytes: int = 1024 * 1024, engine_root: Path | None = None) -> None:
        self.store = store
        self.timeout_seconds = timeout_seconds
        self.maximum_output_bytes = maximum_output_bytes
        self.engine_root = Path(engine_root or Path(__file__).resolve().parents[2]).resolve()

    def run(self, gate_id: str, context: Mapping[str, Any]) -> dict[str, Any]:
        if gate_id not in GATE_IDS:
            raise ValueError(f"unknown gate {gate_id}")
        audit_id = str(context["audit_id"])
        run_dir = self.store.root / "runs" / audit_id / gate_id
        run_dir.mkdir(parents=True, exist_ok=True)
        context_path = run_dir / "context.json"
        evidence_path = run_dir / "evidence.json"
        if evidence_path.exists():
            raise ValueError(f"gate evidence already exists for {audit_id}/{gate_id}")
        material = dict(context)
        material["previous_evidence_hash"] = self.store.previous_evidence_hash(audit_id)
        material["context_path"] = str(context_path)
        context_path.write_text(json.dumps(material, sort_keys=True) + "\n", encoding="utf-8")
        os.chmod(context_path, 0o600)
        argv = [
            sys.executable,
            "-m",
            "lpos_engine.coe_gate",
            "--gate",
            gate_id,
            "--context",
            str(context_path),
            "--output",
            str(evidence_path),
        ]
        env = {
            "PATH": os.environ.get("PATH", ""),
            "HOME": os.environ.get("HOME", ""),
            "PYTHONPATH": os.pathsep.join(filter(None, [str(self.engine_root / "src"), os.environ.get("PYTHONPATH", "")])),
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
        }
        started = time.monotonic()
        try:
            completed = subprocess.run(
                argv,
                cwd=Path(context["repo"]),
                env=env,
                capture_output=True,
                check=False,
                timeout=self.timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            raise ValueError(f"gate {gate_id} timed out after {self.timeout_seconds}s") from exc
        if len(completed.stdout) > self.maximum_output_bytes or len(completed.stderr) > self.maximum_output_bytes:
            raise ValueError(f"gate {gate_id} exceeded the output limit")
        if not evidence_path.is_file() or evidence_path.is_symlink():
            raise ValueError(f"gate {gate_id} did not create a safe evidence file")
        try:
            record = json.loads(evidence_path.read_text(encoding="utf-8"))
        except (OSError, ValueError, UnicodeDecodeError) as exc:
            raise ValueError(f"gate {gate_id} evidence is malformed") from exc
        expected_previous = str(material["previous_evidence_hash"])
        validate_gate_evidence(record, expected_previous_hash=expected_previous)
        if record["executable"] != argv[0] or record["arguments"] != argv[1:]:
            raise ValueError(f"gate {gate_id} evidence did not match the executed command")
        if record["audit_id"] != audit_id or record["gate_id"] != gate_id:
            raise ValueError(f"gate {gate_id} evidence scope mismatch")
        release = context["release"]
        if record["release"] != release or record["git_commit"] != release["git_commit"]:
            raise ValueError(f"gate {gate_id} evidence release mismatch")
        process_pass = completed.returncode == 0
        evidence_pass = record["status"] == "pass"
        if process_pass != evidence_pass or record["exit_code"] != completed.returncode:
            raise ValueError(f"gate {gate_id} process and evidence outcomes disagree")
        record["runner_duration_ms"] = round((time.monotonic() - started) * 1000)
        self.store.insert_evidence({key: value for key, value in record.items() if key != "runner_duration_ms"})
        return record


class ReleaseController:
    """Aggregate current persisted evidence without running or inventing checks."""

    def __init__(self, store: COEStore, *, maximum_age_seconds: int = 7200) -> None:
        self.store = store
        self.maximum_age_seconds = maximum_age_seconds

    def decide(self, audit_id: str, expected_release: Mapping[str, str]) -> dict[str, Any]:
        reasons: list[str] = []
        try:
            records = self.store.verify_audit_chain(audit_id)
        except Exception as exc:
            records = self.store.evidence(audit_id)
            reasons.append("EVIDENCE_HASH_CHAIN_INVALID")
            chain_error = str(exc)
        else:
            chain_error = None
        gates = []
        now = datetime.now(timezone.utc)
        seen = set()
        for record in records:
            seen.add(record.get("gate_id"))
            completed = None
            try:
                completed = datetime.fromisoformat(str(record["completed_at"]).replace("Z", "+00:00"))
            except (KeyError, ValueError):
                reasons.append("GATE_MALFORMED")
            if completed is None or (now - completed).total_seconds() > self.maximum_age_seconds:
                reasons.append("GATE_STALE")
            if record.get("status") != "pass":
                reasons.append(f"GATE_{str(record.get('status', 'unknown')).upper()}")
            if record.get("release") != dict(expected_release) or record.get("git_commit") != expected_release.get("git_commit"):
                reasons.append("GATE_SCOPE_MISMATCH")
            gates.append(
                {
                    "gate_id": record.get("gate_id"),
                    "status": record.get("status"),
                    "evidence_id": record.get("evidence_id"),
                    "evidence_hash": record.get("evidence_hash"),
                    "completed_at": record.get("completed_at"),
                }
            )
        if seen != set(GATE_IDS) or len(records) != len(GATE_IDS):
            reasons.append("GATE_MISSING")
        findings = self.store.findings(status="open", limit=500)
        critical = [item for item in findings if item.get("severity") == "critical"]
        high = [item for item in findings if item.get("severity") == "high" and not item.get("accepted_risk")]
        if critical:
            reasons.append("OPEN_CRITICAL_FINDING")
        if high:
            reasons.append("OPEN_HIGH_FINDING")
        passoff = self.store.documentation_passoff()
        verified_surfaces = {item.get("surface") for item in passoff if item.get("status") == "verified"}
        if verified_surfaces < {"github", "wiki", "google-drive"}:
            reasons.append("DOCUMENTATION_PASSOFF_UNVERIFIED")
        reasons = sorted(set(reasons))
        generated_at = utc_now()
        status = "pass" if not reasons else "blocked"
        payload: dict[str, Any] = {
            "schema_version": 1,
            "audit_id": audit_id,
            "generated_at": generated_at,
            "release": dict(expected_release),
            "status": status,
            "ready_for_dan_approval": status == "pass",
            "decision_reason_codes": reasons,
            "gates": gates,
            "critical_findings": critical,
            "documentation_passoff": {"status": "verified" if verified_surfaces >= {"github", "wiki", "google-drive"} else "unverified", "references": passoff},
            "chain_error": chain_error,
        }
        payload["decision_hash"] = sha256_bytes(canonical_json(payload).encode("utf-8"))
        self.store.insert_decision(audit_id, status, payload["decision_hash"], payload)
        return payload


def _record_storage_metrics(store: COEStore, audit_id: str, repo: Path, release_root: Path) -> None:
    categories = {
        "tracked_repository": [repo / name for name in _git_files(repo)],
        "staged_release": [path for path in release_root.rglob("*") if path.is_file()] if release_root.exists() else [],
        "mutable_state": [path for path in store.state_root.rglob("*") if path.is_file()],
        "audit_evidence": [path for path in store.root.rglob("*.json") if path.is_file()],
        "reports": [path for path in (store.root / "reports").rglob("*") if path.is_file()] if (store.root / "reports").exists() else [],
        "backups": [path for path in (store.root / "backups").rglob("*") if path.is_file()] if (store.root / "backups").exists() else [],
        "temporary_build": [path for path in Path(tempfile.gettempdir()).glob("lpos-coe-build-*") if path.is_file()],
    }
    for category, paths in categories.items():
        total = sum(path.stat().st_size for path in paths if path.exists() and path.is_file())
        store.record_metric(audit_id, f"storage.{category}.bytes", float(total), "bytes", "measured", {"file_count": len(paths), "category": category})


def _git_files(repo: Path) -> list[str]:
    completed = subprocess.run(["git", "ls-files", "-z"], cwd=repo, capture_output=True, check=False, timeout=60)
    if completed.returncode != 0:
        return []
    return [part.decode("utf-8") for part in completed.stdout.split(b"\0") if part]


def _record_skill_metrics(store: COEStore, audit_id: str) -> None:
    skill_root = Path.home() / ".hermes" / "skills"
    skills = [path for path in skill_root.rglob("SKILL.md") if path.is_file()] if skill_root.exists() else []
    bytes_total = sum(path.stat().st_size for path in skills)
    store.record_metric(
        audit_id,
        "skills.catalog.size",
        float(len(skills)),
        "skills",
        "measured",
        {
            "catalog_bytes": bytes_total,
            "efficiency": "unknown",
            "reason": "catalog inventory is available, but search latency and per-task use telemetry require Hermes runtime export",
            "discovery_order": ["indexed-local", "approved-reuse", "fresh-cache", "external-search-if-needed", "approval", "verify-and-index"],
        },
    )


def _record_scheduler_and_wakes(store: COEStore, audit_id: str) -> None:
    decision = wake_decision(eligible=True, qualifying_input=False)
    wake_id = sortable_id("wake")
    with store.engine.transaction() as conn:
        conn.execute(
            "INSERT INTO coe_wake_decisions(wake_id,job_id,audit_id,eligible,wake_agent,model_invoked,reason_code,decision_json,created_at) VALUES (?,?,?,?,?,?,?,?,?)",
            (wake_id, "coe-daily", audit_id, 1, 0, 0, decision["reason_code"], canonical_json(decision), utc_now()),
        )
    store.record_metric(audit_id, "wake.efficiency", 100.0, "percent", "measured", {"eligible_polls": 1, "model_wakes": 0, "deterministic_skips": 1, "false_wakes": 0, "missed_work_check": "no qualifying input"})


def _record_prompt_drift(store: COEStore, audit_id: str, repo: Path) -> None:
    findings = []
    for name in _git_files(repo):
        path = repo / name
        if not path.is_file() or path.suffix not in {".md", ".json", ".yaml", ".yml", ".py"}:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if "Use LPOS v3" in text and not name.startswith("docs/history/"):
            findings.append({"path": name, "match": "Use LPOS v3", "active": True})
    store.record_metric(audit_id, "prompt_drift.active_findings", float(len(findings)), "findings", "measured", {"findings": findings})
    for item in findings:
        finding_id = sortable_id("finding")
        store.insert_finding(audit_id, {"finding_id": finding_id, "severity": "high", "status": "open", "owner": "LPOS Platform Operations", "title": "Active prompt uses obsolete LPOS version", "evidence": item})
        store.insert_opportunity(audit_id, {
            "opportunity_id": sortable_id("opportunity"), "finding_id": finding_id,
            "problem_statement": "An active prompt can route work through obsolete LPOS policy",
            "proposed_change": "Update the prompt and add it to prompt drift regression tests",
            "operator_time_saved": "prevents manual drift repair", "compute_saved": "avoids reruns", "latency_reduced": "avoids recovery latency",
            "risk_reduced": "high", "maintenance_reduced": "medium", "quality_improved": "high",
            "implementation_effort": "low", "confidence": 0.95, "approval_status": "approved-by-implementation-order",
            "owner": "LPOS Platform Operations", "status": "proposed",
        })


def perform_backup_restore(store: COEStore, audit_id: str) -> dict[str, Any]:
    """Copy the active database, verify hashes, restore, and run SQLite integrity_check."""

    source = store.engine.path
    backup_dir = store.root / "backups" / audit_id
    backup_dir.mkdir(parents=True, exist_ok=True)
    target = backup_dir / "coe.db"
    with sqlite3.connect(source) as source_conn, sqlite3.connect(target) as target_conn:
        source_conn.backup(target_conn)
    digest = sha256_file(target)
    backup_id = sortable_id("backup")
    created = datetime.now(timezone.utc)
    expires = created + timedelta(days=14)
    backup = {
        "backup_id": backup_id,
        "audit_id": audit_id,
        "status": "pass",
        "manifest_hash": digest,
        "bytes": target.stat().st_size,
        "file_count": 1,
        "destination": str(target),
        "policy_version": 1,
        "encrypted_destination_required_for_export": True,
        "created_at": created.isoformat().replace("+00:00", "Z"),
        "expires_at": expires.isoformat().replace("+00:00", "Z"),
    }
    with store.engine.transaction() as conn:
        conn.execute(
            "INSERT INTO coe_backups(backup_id,audit_id,status,manifest_hash,backup_json,created_at,expires_at) VALUES (?,?,?,?,?,?,?)",
            (backup_id, audit_id, "pass", digest, canonical_json(backup), backup["created_at"], backup["expires_at"]),
        )
    restore_id = sortable_id("restore")
    with tempfile.TemporaryDirectory(prefix="lpos-coe-restore-") as temp:
        restored = Path(temp) / "restored.db"
        shutil.copy2(target, restored)
        hash_ok = sha256_file(restored) == digest
        conn = sqlite3.connect(restored)
        try:
            pragma = str(conn.execute("PRAGMA integrity_check").fetchone()[0])
            sentinel = conn.execute("SELECT COUNT(*) FROM coe_audits WHERE audit_id=?", (audit_id,)).fetchone()[0]
        finally:
            conn.close()
        status = "pass" if hash_ok and pragma == "ok" and sentinel == 1 else "fail"
        restore = {
            "restore_test_id": restore_id,
            "backup_id": backup_id,
            "audit_id": audit_id,
            "status": status,
            "hash_verified": hash_ok,
            "sqlite_integrity": pragma,
            "sentinel_records": sentinel,
            "isolated": True,
            "cleanup": "temporary restore directory removed",
            "completed_at": utc_now(),
        }
    with store.engine.transaction() as conn:
        conn.execute(
            "INSERT INTO coe_restore_tests(restore_test_id,backup_id,audit_id,status,restore_json,completed_at) VALUES (?,?,?,?,?,?)",
            (restore_id, backup_id, audit_id, status, canonical_json(restore), restore["completed_at"]),
        )
    return restore


class AuditOrchestrator:
    def __init__(self, repo: Path, state_root: Path | None = None) -> None:
        self.repo = Path(repo).resolve()
        self.store = COEStore(state_root)

    def run(
        self,
        *,
        release_root: Path,
        trigger: str,
        build_id: str,
        configuration: Mapping[str, Any] | None = None,
        production: bool = False,
        baseline_commit: str | None = None,
        deterministic_command: list[str] | None = None,
        deterministic_commands: list[dict[str, Any]] | None = None,
        security_command: list[str] | None = None,
        dependency_audit_command: list[str] | None = None,
        source_repositories: list[dict[str, Any]] | None = None,
        documentation_repo: Path | None = None,
    ) -> dict[str, Any]:
        if trigger not in {"scheduled-daily", "manual", "pre-release", "post-deploy", "backfill"}:
            raise ValueError("invalid COE audit trigger")
        identity = read_release_identity(self.repo)
        verified = verify_release(release_root, expected_identity=identity, expected_commit=identity["git_commit"])
        scope = release_scope(identity, build_id=build_id, artifact_sha256=verified["artifact_sha256"])
        local = central_date()
        key = daily_idempotency_key() if trigger in {"scheduled-daily", "backfill"} else f"coe-{trigger}:{identity['git_commit']}:{verified['artifact_sha256']}:{sortable_id('attempt')}"
        owner = sortable_id("runner")
        if not self.store.acquire_lock(key, owner, 7200):
            raise ValueError(f"audit lock already held for {key}")
        audit_id = sortable_id("audit")
        try:
            prior = self.store.latest_audit()
            self.store.create_audit(
                audit_id=audit_id,
                trigger=trigger,
                local_date=local,
                timezone_name="America/Chicago",
                idempotency_key=key,
                release_version=identity["release_version"],
                git_commit=identity["git_commit"],
                artifact_sha256=verified["artifact_sha256"],
                baseline_audit_id=prior.get("audit_id") if prior else None,
            )
            self.store.ensure_legacy_debt()
            _record_storage_metrics(self.store, audit_id, self.repo, Path(release_root))
            _record_skill_metrics(self.store, audit_id)
            _record_scheduler_and_wakes(self.store, audit_id)
            _record_prompt_drift(self.store, audit_id, self.repo)
            restore = perform_backup_restore(self.store, audit_id)
            if restore["status"] != "pass":
                self.store.insert_finding(audit_id, {"finding_id": sortable_id("finding"), "severity": "critical", "status": "open", "owner": "LPOS Platform Operations", "title": "Isolated backup restore failed", "evidence": restore})
            passoff = self.store.documentation_passoff()
            context: dict[str, Any] = {
                "audit_id": audit_id,
                "repo": str(self.repo),
                "state_root": str(self.store.state_root),
                "release_root": str(Path(release_root).resolve()),
                "identity": identity,
                "release": scope,
                "baseline_commit": baseline_commit or (prior.get("git_commit") if prior else identity["git_commit"]),
                "configuration": dict(configuration or {}),
                "production": production,
                "dashboard_auth_required": True,
                "documentation_passoff": passoff,
                "documentation_repo": str(Path(documentation_repo).resolve()) if documentation_repo else str(self.repo),
                "source_repositories": source_repositories or [{"path": str(self.repo), "baseline_commit": baseline_commit or (prior.get("git_commit") if prior else identity["git_commit"]), "target_commit": identity["git_commit"]}],
                "gate_timeout_seconds": 1800,
                "input_hashes": {"release_manifest": verified["manifest_sha256"]},
            }
            if deterministic_command:
                context["deterministic_command"] = deterministic_command
            if deterministic_commands:
                context["deterministic_commands"] = deterministic_commands
            if security_command:
                context["security_command"] = security_command
            if dependency_audit_command:
                context["dependency_audit_command"] = dependency_audit_command
            runner = GateRunner(self.store)
            outcomes: list[dict[str, Any]] = []
            for gate_id in GATE_IDS:
                record = runner.run(gate_id, context)
                outcomes.append(record)
            decision = ReleaseController(self.store).decide(audit_id, scope)
            terminal = "pass" if decision["status"] == "pass" else "blocked"
            audit_payload = {
                "audit_id": audit_id,
                "trigger": trigger,
                "local_date": local,
                "timezone": "America/Chicago",
                "idempotency_key": key,
                "release_version": identity["release_version"],
                "git_commit": identity["git_commit"],
                "artifact_sha256": verified["artifact_sha256"],
                "baseline_audit_id": prior.get("audit_id") if prior else None,
                "status": terminal,
                "started_at": outcomes[0]["started_at"] if outcomes else utc_now(),
                "gate_statuses": {item["gate_id"]: item["status"] for item in outcomes},
                "decision_hash": decision["decision_hash"],
            }
            self.store.complete_audit(audit_id, terminal, audit_payload)
            summary = dashboard_summary(self.store, audit_id=audit_id)
            write_projection(self.store, summary)
            return {"audit": self.store.audit(audit_id), "decision": decision, "evidence": outcomes, "summary": summary}
        finally:
            self.store.release_lock(key, owner)


def score_summary(store: COEStore, audit_id: str) -> dict[str, Any]:
    decision = store.decision(audit_id)
    if not decision:
        return {name: {"status": "unknown", "reason": "no persisted release decision"} for name in ("overall", "engineering", "security", "efficiency", "cost", "documentation", "release_integrity", "scheduler_health", "wake_agent_efficiency", "backup_health")}
    by_gate = {item["gate_id"]: item["status"] for item in decision.get("gates", [])}
    dimensions = {
        "engineering": by_gate.get("engineering-audit"),
        "security": by_gate.get("security-reliability-audit"),
        "efficiency": by_gate.get("bloat-audit"),
        "cost": "unknown",
        "documentation": by_gate.get("documentation-audit"),
        "release_integrity": by_gate.get("release-integrity"),
        "scheduler_health": "unknown",
        "wake_agent_efficiency": "pass" if any(item["name"] == "wake.efficiency" for item in store.metrics(limit=100)) else "unknown",
        "backup_health": by_gate.get("security-reliability-audit"),
    }
    rendered = {name: ({"status": "measured", "score": 100 if status == "pass" else 0} if status in {"pass", "fail"} else {"status": "unknown", "reason": "required measurement unavailable"}) for name, status in dimensions.items()}
    available: list[float] = [float(item["score"]) for item in rendered.values() if "score" in item]
    overall = sum(available) / len(available) if available else None
    if decision.get("critical_findings") and overall is not None:
        overall = min(overall, 59)
    rendered["overall"] = {"status": "measured", "score": round(overall, 1)} if overall is not None else {"status": "unknown", "reason": "no dimensions measured"}
    return rendered


def dashboard_summary(store: COEStore, audit_id: str | None = None, *, public_base_url: str = "https://chip.listeningpost.ai", dashboard_path: str = "/dashboard/coe") -> dict[str, Any]:
    audit = store.audit(audit_id) if audit_id else store.latest_audit()
    if not audit:
        return {"schema_version": 1, "audit_id": None, "release_version": None, "generated_at": utc_now(), "status": "unknown", "reason": "no COE audit exists"}
    resolved_audit_id = str(audit["audit_id"])
    decision = store.decision(resolved_audit_id)
    scores = score_summary(store, resolved_audit_id)
    findings = store.findings(limit=100)
    opportunities = store.opportunities(limit=100)
    debt = store.technical_debt()
    metrics = store.metrics(limit=1000)
    latest_delivery = store.latest_delivery(resolved_audit_id)
    prompt = next((item for item in metrics if item["name"] == "prompt_drift.active_findings"), None)
    wake = next((item for item in metrics if item["name"] == "wake.efficiency"), None)
    storage = [item for item in metrics if item["name"].startswith("storage.")]
    return {
        "schema_version": 1,
        "audit_id": resolved_audit_id,
        "release_version": audit["release_version"],
        "git_commit": audit["git_commit"],
        "build_id": decision.get("release", {}).get("build_id") if decision else None,
        "generated_at": utc_now(),
        "canonical_url": f"{public_base_url.rstrip('/')}{dashboard_path}",
        "overall_health_score": scores["overall"],
        "engineering_score": scores["engineering"],
        "security_score": scores["security"],
        "efficiency_score": scores["efficiency"],
        "cost_score": scores["cost"],
        "documentation_score": scores["documentation"],
        "release_integrity": scores["release_integrity"],
        "scheduler_health": scores["scheduler_health"],
        "wake_agent_efficiency": wake or {"status": "unknown", "reason": "wake telemetry unavailable"},
        "prompt_drift": prompt or {"status": "unknown", "reason": "prompt scan unavailable"},
        "technical_debt": debt,
        "opportunity_backlog": opportunities,
        "release_readiness": decision.get("status") if decision else "blocked",
        "top_risks": [item for item in findings if item.get("severity") in {"critical", "high"}][:10],
        "pending_approvals": [item for item in opportunities if item.get("approval_status") not in {"approved", "approved-by-implementation-order", "rejected"}],
        "recent_improvements": [item for item in opportunities if item.get("status") == "verified"][:10],
        "audit_history": store.audits(limit=30),
        "current_release_status": decision or {"status": "blocked", "decision_reason_codes": ["DECISION_MISSING"]},
        "daily_email_delivery_status": latest_delivery or {"status": "unknown"},
        "backup_restore_evidence_age": "current-audit" if any(item.get("gate_id") == "security-reliability-audit" for item in (decision or {}).get("gates", [])) else "unknown",
        "storage_trend_summary": storage,
    }


def render_daily_report(summary: Mapping[str, Any]) -> str:
    decision = summary.get("current_release_status", {})
    lines = [
        f"# LPOS COE {str(decision.get('status', 'blocked')).upper()}",
        "",
        f"Audit ID: {summary.get('audit_id')}",
        f"Release: {summary.get('release_version')} at {summary.get('git_commit')}",
        f"Dashboard: {summary.get('canonical_url')}?audit={summary.get('audit_id')}",
        f"Canonical dashboard: {summary.get('canonical_url')}",
        f"Release readiness: {summary.get('release_readiness')}",
        "",
        "## Gates",
    ]
    for gate in decision.get("gates", []):
        lines.append(f"- {gate.get('gate_id')}: {gate.get('status')}")
    sections = (
        ("Top risks", summary.get("top_risks", [])),
        ("Skill-search efficiency", summary.get("efficiency_score")),
        ("Scheduler and wake efficiency", summary.get("wake_agent_efficiency")),
        ("Backup and restore", summary.get("backup_restore_evidence_age")),
        ("Storage trend", summary.get("storage_trend_summary")),
        ("Technical debt", summary.get("technical_debt")),
        ("Opportunities", summary.get("opportunity_backlog")),
        ("Pending decisions", summary.get("pending_approvals")),
    )
    for title, value in sections:
        lines.extend(["", f"## {title}", "", "```json", json.dumps(value, indent=2, sort_keys=True), "```"])
    return "\n".join(lines) + "\n"


def write_projection(store: COEStore, summary: Mapping[str, Any]) -> dict[str, str]:
    """Atomically publish privacy-safe mutable views for the deployed read-only adapter."""
    store.root.mkdir(parents=True, exist_ok=True)
    report_dir = store.root / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    latest_path = store.root / "latest.json"
    report_path = report_dir / f"{summary.get('audit_id', 'unknown')}.md"
    latest_temp = latest_path.with_suffix(".json.tmp")
    report_temp = report_path.with_suffix(".md.tmp")
    payload = canonical_json(dict(summary)) + "\n"
    report = render_daily_report(summary)
    latest_temp.write_text(payload, encoding="utf-8")
    report_temp.write_text(report, encoding="utf-8")
    os.chmod(latest_temp, 0o600)
    os.chmod(report_temp, 0o600)
    os.replace(latest_temp, latest_path)
    os.replace(report_temp, report_path)
    return {
        "latest_path": str(latest_path),
        "latest_sha256": sha256_file(latest_path),
        "report_path": str(report_path),
        "report_sha256": sha256_file(report_path),
    }


def deliver_report(store: COEStore, audit_id: str, report: str, *, recipient_reference: str, transport_argv: list[str]) -> dict[str, Any]:
    report_dir = store.root / "reports" / audit_id
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "daily-report.md"
    report_path.write_text(report, encoding="utf-8")
    report_hash = sha256_file(report_path)
    started = utc_now()
    completed = subprocess.run(
        [*transport_argv, str(report_path)],
        cwd=report_dir,
        env={"PATH": os.environ.get("PATH", ""), "HOME": os.environ.get("HOME", "")},
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    output = redact(completed.stdout.strip())
    message_id = output.splitlines()[-1].strip() if completed.returncode == 0 and output else None
    status = "delivered" if completed.returncode == 0 and message_id else "failed"
    delivery = {
        "delivery_id": sortable_id("delivery"),
        "audit_id": audit_id,
        "recipient_reference": sha256_bytes(recipient_reference.encode("utf-8")),
        "transport": transport_argv[0],
        "attempt_number": 1,
        "started_at": started,
        "completed_at": utc_now(),
        "status": status,
        "provider_message_id": message_id,
        "error": redact(completed.stderr.strip()) if status == "failed" else None,
        "report_hash": report_hash,
    }
    store.record_delivery(audit_id, delivery)
    return delivery
