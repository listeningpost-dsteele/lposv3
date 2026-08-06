"""Private COE API, dashboard, audit facade, and report surface.

The module deliberately renders persisted evidence. It never executes a gate as
part of an HTTP request and never constructs a successful release packet.
"""

from __future__ import annotations

import hmac
import json
import os
import re
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from .coe_contract import sortable_id, utc_now
from .coe_runtime import AuditOrchestrator, dashboard_summary, render_daily_report
from .coe_store import COEStore, default_state_root

API_PREFIX = "/api/v1/coe"
AUDIT_ID = re.compile(r"^audit-[0-9]{13}-[0-9a-f]{16}$")
OPPORTUNITY_ID = re.compile(r"^opportunity-[0-9]{13}-[0-9a-f]{16}$")


def run_audit(
    repo_root: Path,
    *,
    release_root: Path | None = None,
    state_root: Path | None = None,
    trigger: str = "manual",
    build_id: str | None = None,
    production: bool = False,
    configuration: dict[str, Any] | None = None,
    deterministic_command: list[str] | None = None,
    security_command: list[str] | None = None,
    dependency_audit_command: list[str] | None = None,
) -> dict[str, Any]:
    """Run a command-backed audit or return a fail-closed missing-input packet."""

    if release_root is None:
        return {
            "schema_version": 1,
            "audit_id": None,
            "generated_at": utc_now(),
            "status": "blocked",
            "ready_for_dan_approval": False,
            "decision_reason_codes": ["STAGED_RELEASE_REQUIRED"],
            "gates": [],
        }
    orchestrator = AuditOrchestrator(Path(repo_root), state_root)
    return orchestrator.run(
        release_root=Path(release_root),
        trigger=trigger,
        build_id=build_id or sortable_id("build"),
        production=production,
        configuration=configuration,
        deterministic_command=deterministic_command,
        security_command=security_command,
        dependency_audit_command=dependency_audit_command,
    )


def load_latest(state_root: Path | None = None) -> dict[str, Any] | None:
    return COEStore(state_root).latest_audit()


def render_report(audit_or_summary: dict[str, Any], *, state_root: Path | None = None) -> str:
    if "overall_health_score" in audit_or_summary:
        return render_daily_report(audit_or_summary)
    audit_id = audit_or_summary.get("audit_id")
    return render_daily_report(dashboard_summary(COEStore(state_root), str(audit_id) if audit_id else None))


def _html(summary: dict[str, Any]) -> str:
    labels = (
        ("Overall Health Score", "overall_health_score"),
        ("Engineering Score", "engineering_score"),
        ("Security Score", "security_score"),
        ("Efficiency Score", "efficiency_score"),
        ("Cost Score", "cost_score"),
        ("Documentation Score", "documentation_score"),
        ("Release Integrity", "release_integrity"),
        ("Scheduler Health", "scheduler_health"),
        ("Wake-Agent Efficiency", "wake_agent_efficiency"),
        ("Prompt Drift", "prompt_drift"),
        ("Technical Debt", "technical_debt"),
        ("Opportunity Backlog", "opportunity_backlog"),
        ("Release Readiness", "release_readiness"),
        ("Top Risks", "top_risks"),
        ("Pending Approvals", "pending_approvals"),
        ("Recent Improvements", "recent_improvements"),
        ("Audit History", "audit_history"),
        ("Current Release Status", "current_release_status"),
    )
    cards = []
    for label, key in labels:
        value = summary.get(key, {"status": "unknown", "reason": "measurement unavailable"})
        cards.append(
            '<section class="card"><h2>'
            + _escape(label)
            + "</h2><pre>"
            + _escape(json.dumps(value, indent=2, sort_keys=True))
            + "</pre></section>"
        )
    status = str(summary.get("release_readiness", "blocked"))
    return """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow"><title>LPOS COE</title>
<style>
:root{color-scheme:dark;--bg:#10120f;--panel:#191d18;--ink:#f3f0e7;--muted:#b4b8ad;--line:#394037;--accent:#f0d67a;--bad:#ff8c82}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace}
main{max-width:1200px;margin:auto;padding:32px 20px 64px}.eyebrow{color:var(--accent);text-transform:uppercase;letter-spacing:.14em}
h1{font:700 clamp(2rem,6vw,4.5rem)/.95 system-ui,sans-serif;margin:.3em 0}.meta{color:var(--muted);display:flex;gap:18px;flex-wrap:wrap}
.blocked{color:var(--bad)}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:14px;margin-top:28px}
.card{border:1px solid var(--line);background:var(--panel);padding:18px;min-width:0}.card h2{font:650 1rem system-ui,sans-serif;margin:0 0 12px}
pre{white-space:pre-wrap;overflow-wrap:anywhere;color:var(--muted);margin:0;font-size:.78rem}
</style></head><body><main><div class="eyebrow">Continuous Operational Excellence</div><h1>Evidence, not assertion.</h1>
<div class="meta"><span class="blocked">Release: """ + _escape(status) + """</span><span>Version: """ + _escape(str(summary.get("release_version") or "unknown")) + """</span>
<span>Audit: """ + _escape(str(summary.get("audit_id") or "unknown")) + """</span><span>Updated: """ + _escape(str(summary.get("generated_at") or "unknown")) + """</span></div>
<div class="grid">""" + "".join(cards) + """</div></main></body></html>"""


def _escape(value: str) -> str:
    return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;").replace("'", "&#39;")


class COEHandler(BaseHTTPRequestHandler):
    server_version = "LPOS-COE/4.7.0"

    @property
    def app(self) -> "COEServer":
        return self.server  # type: ignore[return-value]

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _authorized(self) -> bool:
        expected = self.app.operator_token
        header = self.headers.get("Authorization", "")
        supplied = header[7:] if header.startswith("Bearer ") else ""
        return bool(expected) and hmac.compare_digest(supplied, expected)

    def _headers(self, status: int, content_type: str, length: int) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(length))
        self.send_header("Cache-Control", "private, no-store, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; frame-ancestors 'none'")
        self.end_headers()

    def _json(self, status: int, payload: Any) -> None:
        body = (json.dumps(payload, sort_keys=True) + "\n").encode("utf-8")
        self._headers(status, "application/json; charset=utf-8", len(body))
        self.wfile.write(body)

    def _text(self, status: int, value: str, content_type: str = "text/plain; charset=utf-8") -> None:
        body = value.encode("utf-8")
        self._headers(status, content_type, len(body))
        self.wfile.write(body)

    def _authenticate(self) -> bool:
        if self._authorized():
            return True
        self._json(HTTPStatus.UNAUTHORIZED, {"error": "operator authentication required"})
        return False

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/ops/coe":
            self.send_response(HTTPStatus.FOUND)
            self.send_header("Location", "/dashboard/coe")
            self.send_header("Cache-Control", "private, no-store")
            self.end_headers()
            return
        if parsed.path not in {"/healthz"} and not self._authenticate():
            return
        if parsed.path == "/healthz":
            self._json(HTTPStatus.OK, {"status": "ok", "service": "lpos-coe"})
            return
        if parsed.path == "/dashboard/coe":
            query = parse_qs(parsed.query)
            audit_id = query.get("audit", [None])[0]
            summary = dashboard_summary(self.app.store, audit_id, public_base_url=self.app.public_base_url)
            self._text(HTTPStatus.OK, _html(summary), "text/html; charset=utf-8")
            return
        if parsed.path == f"{API_PREFIX}/summary":
            query = parse_qs(parsed.query)
            audit_id = query.get("audit", [None])[0]
            self._json(HTTPStatus.OK, dashboard_summary(self.app.store, audit_id, public_base_url=self.app.public_base_url))
            return
        if parsed.path == f"{API_PREFIX}/audits":
            query = parse_qs(parsed.query)
            limit = _bounded_int(query.get("limit", ["50"])[0], 1, 100)
            offset = _bounded_int(query.get("offset", ["0"])[0], 0, 100000)
            self._json(HTTPStatus.OK, {"items": self.app.store.audits(limit, offset), "limit": limit, "offset": offset})
            return
        match = re.fullmatch(r"/api/v1/coe/audits/([^/]+)", parsed.path)
        if match:
            audit_id = match.group(1)
            if not AUDIT_ID.fullmatch(audit_id):
                self._json(HTTPStatus.BAD_REQUEST, {"error": "invalid audit ID"})
                return
            audit = self.app.store.audit(audit_id)
            if not audit:
                self._json(HTTPStatus.NOT_FOUND, {"error": "audit not found"})
                return
            self._json(HTTPStatus.OK, {"audit": audit, "decision": self.app.store.decision(audit_id), "evidence": self.app.store.evidence(audit_id)})
            return
        if parsed.path == f"{API_PREFIX}/findings":
            self._json(HTTPStatus.OK, {"items": self.app.store.findings(limit=100)})
            return
        if parsed.path == f"{API_PREFIX}/opportunities":
            self._json(HTTPStatus.OK, {"items": self.app.store.opportunities(limit=100)})
            return
        if parsed.path == f"{API_PREFIX}/technical-debt":
            self._json(HTTPStatus.OK, {"items": self.app.store.technical_debt()})
            return
        if parsed.path == f"{API_PREFIX}/storage":
            self._json(HTTPStatus.OK, {"items": self.app.store.metrics(limit=1000)})
            return
        if parsed.path == f"{API_PREFIX}/scheduler":
            with self.app.store.engine.connection() as conn:
                jobs = [json.loads(row["job_json"]) for row in conn.execute("SELECT job_json FROM coe_scheduler_jobs ORDER BY job_id").fetchall()]
                wakes = [json.loads(row["decision_json"]) for row in conn.execute("SELECT decision_json FROM coe_wake_decisions ORDER BY created_at DESC LIMIT 100").fetchall()]
            self._json(HTTPStatus.OK, {"jobs": jobs, "wake_decisions": wakes})
            return
        if parsed.path == f"{API_PREFIX}/backups":
            with self.app.store.engine.connection() as conn:
                backups = [json.loads(row["backup_json"]) for row in conn.execute("SELECT backup_json FROM coe_backups ORDER BY created_at DESC LIMIT 100").fetchall()]
                restores = [json.loads(row["restore_json"]) for row in conn.execute("SELECT restore_json FROM coe_restore_tests ORDER BY completed_at DESC LIMIT 100").fetchall()]
            self._json(HTTPStatus.OK, {"backups": backups, "restore_tests": restores})
            return
        match = re.fullmatch(r"/api/v1/coe/reports/([^/]+)", parsed.path)
        if match:
            audit_id = match.group(1)
            if not AUDIT_ID.fullmatch(audit_id) or not self.app.store.audit(audit_id):
                self._json(HTTPStatus.NOT_FOUND, {"error": "report not found"})
                return
            self._text(HTTPStatus.OK, render_daily_report(dashboard_summary(self.app.store, audit_id, public_base_url=self.app.public_base_url)), "text/markdown; charset=utf-8")
            return
        if parsed.path == "/api/v1/operator/release-gate":
            decision = self.app.store.decision()
            self._json(HTTPStatus.OK, decision or {"schema_version": 1, "audit_id": None, "generated_at": utc_now(), "status": "blocked", "ready_for_dan_approval": False, "decision_reason_codes": ["DECISION_MISSING"], "gates": []})
            return
        self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if not self._authenticate():
            return
        match = re.fullmatch(r"/api/v1/coe/opportunities/([^/]+)/decision", parsed.path)
        if not match:
            self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})
            return
        opportunity_id = match.group(1)
        if not OPPORTUNITY_ID.fullmatch(opportunity_id):
            self._json(HTTPStatus.BAD_REQUEST, {"error": "invalid opportunity ID"})
            return
        try:
            length = min(int(self.headers.get("Content-Length", "0")), 16384)
            payload = json.loads(self.rfile.read(length))
        except (ValueError, json.JSONDecodeError):
            self._json(HTTPStatus.BAD_REQUEST, {"error": "invalid JSON"})
            return
        if not isinstance(payload, dict) or payload.get("decision") not in {"approved", "rejected", "deferred"} or not payload.get("actor"):
            self._json(HTTPStatus.BAD_REQUEST, {"error": "decision and actor are required"})
            return
        decision = self.app.store.record_operator_decision(opportunity_id, payload)
        self._json(HTTPStatus.CREATED, decision)


def _bounded_int(value: str, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except ValueError:
        return minimum
    return max(minimum, min(parsed, maximum))


class COEServer(ThreadingHTTPServer):
    def __init__(self, address: tuple[str, int], *, store: COEStore, operator_token: str, public_base_url: str) -> None:
        if not operator_token:
            raise ValueError("COE operator token is required")
        super().__init__(address, COEHandler)
        self.store = store
        self.operator_token = operator_token
        self.public_base_url = public_base_url.rstrip("/")


def serve(
    state_root: Path | None = None,
    *,
    host: str = "127.0.0.1",
    port: int = 8765,
    operator_token: str | None = None,
    public_base_url: str = "https://chip.listeningpost.ai",
) -> None:
    token = operator_token or os.environ.get("COE_OPERATOR_TOKEN", "")
    server = COEServer((host, port), store=COEStore(state_root or default_state_root()), operator_token=token, public_base_url=public_base_url)
    try:
        server.serve_forever()
    finally:
        server.server_close()