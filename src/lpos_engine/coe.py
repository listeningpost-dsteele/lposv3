"""Continuous Operational Excellence audits, reports, and local dashboard."""

from __future__ import annotations

import hashlib
import html
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 7374
SECRET_NAMES = {
    ".env",
    "auth.json",
    "credentials.json",
    "google_token.json",
    "token.json",
}
LEGACY_PATTERN = re.compile(r"\bLPOS\s+v(?:2|3)(?:\.\d+)*\b|Use LPOS v3|LPOS v3\.0\.3", re.IGNORECASE)
FREQUENT_MINUTES = re.compile(r"^\*/(\d+)\s")
WAKE_FALSE_PATTERN = re.compile(r"[\"']wakeAgent[\"']\s*:\s*(?:False|false)")
REQUIRED_DEBT_FIELDS = {"id", "owner", "rationale", "retirement_date", "migration_plan", "status"}


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def iso(moment: datetime | None = None) -> str:
    return (moment or utcnow()).isoformat(timespec="seconds").replace("+00:00", "Z")


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


def _json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        return default


def _tree_stats(root: Path, *, max_files: int = 250_000) -> dict[str, int]:
    files = 0
    bytes_total = 0
    if not root.exists():
        return {"files": 0, "bytes": 0}
    for path in root.rglob("*"):
        if files >= max_files:
            break
        try:
            if path.is_file() and not path.is_symlink():
                stat = path.stat()
                files += 1
                bytes_total += stat.st_size
        except OSError:
            continue
    return {"files": files, "bytes": bytes_total}


def _finding(domain: str, status: str, severity: str, summary: str, evidence: dict[str, Any]) -> dict[str, Any]:
    return {
        "domain": domain,
        "status": status,
        "severity": severity,
        "summary": summary,
        "evidence": evidence,
    }


def _release_integrity(repo: Path) -> dict[str, Any]:
    verifier = repo / "verify_release.py"
    if not verifier.is_file():
        return _finding("release_integrity", "fail", "critical", "Release verifier is missing", {"repo": str(repo)})
    completed = subprocess.run(
        [sys.executable, str(verifier)],
        cwd=repo,
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    detail = "\n".join(part.strip() for part in (completed.stdout, completed.stderr) if part.strip())
    return _finding(
        "release_integrity",
        "pass" if completed.returncode == 0 else "fail",
        "critical",
        "Immutable release verification passed" if completed.returncode == 0 else "Immutable release verification failed",
        {"returncode": completed.returncode, "detail": detail[-8000:]},
    )


def _backup_governance(hermes_root: Path) -> dict[str, Any]:
    roots = [hermes_root / "backups", hermes_root / "lpos" / "backups"]
    existing = [root for root in roots if root.exists()]
    totals = {"files": 0, "bytes": 0}
    nested: list[str] = []
    secrets: list[str] = []
    for root in existing:
        stats = _tree_stats(root)
        totals["files"] += stats["files"]
        totals["bytes"] += stats["bytes"]
        for path in root.rglob("*"):
            try:
                relative = path.relative_to(root)
            except ValueError:
                continue
            lowered = [part.lower() for part in relative.parts]
            if len(relative.parts) > 2 and any("backup" in part for part in lowered[1:-1]):
                nested.append(str(path))
            if path.is_file() and (path.name.lower() in SECRET_NAMES or "token" in path.name.lower()):
                secrets.append(str(path))
    invalid = bool(nested or secrets or totals["bytes"] > 5 * 1024**3 or totals["files"] > 100_000)
    status = "fail" if secrets else "warn" if invalid else "pass"
    severity = "critical" if secrets else "high" if invalid else "low"
    summary = "Backup governance passed" if status == "pass" else "Backup governance found unbounded, nested, or secret-bearing material"
    return _finding(
        "backup_governance",
        status,
        severity,
        summary,
        {
            "roots": [str(root) for root in existing],
            "files": totals["files"],
            "bytes": totals["bytes"],
            "nested_count": len(nested),
            "secret_file_count": len(secrets),
            "sample_nested": nested[:10],
            "sample_secret_files": secrets[:10],
            "limits": {"bytes": 5 * 1024**3, "files": 100_000},
        },
    )


def _jobs(hermes_root: Path) -> list[dict[str, Any]]:
    data = _json(hermes_root / "cron" / "jobs.json", {})
    rows = data.get("jobs", []) if isinstance(data, dict) else []
    return [row for row in rows if isinstance(row, dict)]


def _scheduler_governance(hermes_root: Path, jobs: list[dict[str, Any]]) -> dict[str, Any]:
    names: dict[str, list[str]] = {}
    orphan_scripts: list[str] = []
    fixtures: list[str] = []
    paused = 0
    for job in jobs:
        name = str(job.get("name", "")).strip()
        names.setdefault(name.lower(), []).append(str(job.get("id", "")))
        if not job.get("enabled", True):
            paused += 1
        if name.lower() in {"claim job", "paused job", "test job", "fixture job"}:
            fixtures.append(str(job.get("id", "")))
        script = job.get("script")
        if script and not (hermes_root / "scripts" / str(script)).is_file():
            orphan_scripts.append(f"{job.get('id')}:{script}")
    duplicates = {name: ids for name, ids in names.items() if name and len(ids) > 1}
    problems = len(duplicates) + len(orphan_scripts) + len(fixtures)
    return _finding(
        "scheduler_governance",
        "warn" if problems else "pass",
        "high" if fixtures or orphan_scripts else "medium" if duplicates else "low",
        "Scheduler contains duplicate, orphaned, or fixture jobs" if problems else "Scheduler governance passed",
        {
            "jobs": len(jobs),
            "paused": paused,
            "duplicates": duplicates,
            "orphan_scripts": orphan_scripts,
            "fixture_job_ids": fixtures,
        },
    )


def _frequent(job: dict[str, Any]) -> bool:
    schedule = str(job.get("schedule", ""))
    match = FREQUENT_MINUTES.match(schedule)
    if match:
        return int(match.group(1)) <= 30
    interval = re.search(r"every\s+(\d+)m", schedule, re.IGNORECASE)
    return bool(interval and int(interval.group(1)) <= 30)


def _wake_efficiency(hermes_root: Path, jobs: list[dict[str, Any]]) -> dict[str, Any]:
    frequent = [job for job in jobs if job.get("enabled", True) and _frequent(job)]
    ungated: list[str] = []
    gated: list[str] = []
    deterministic: list[str] = []
    for job in frequent:
        job_id = str(job.get("id", ""))
        if job.get("no_agent"):
            deterministic.append(job_id)
            continue
        script = job.get("script")
        source = ""
        if script:
            try:
                source = (hermes_root / "scripts" / str(script)).read_text(encoding="utf-8")
            except OSError:
                pass
        if WAKE_FALSE_PATTERN.search(source):
            gated.append(job_id)
        else:
            ungated.append(job_id)
    total = len(frequent)
    efficient = len(gated) + len(deterministic)
    score = 100 if total == 0 else round(100 * efficient / total)
    return _finding(
        "wake_agent_efficiency",
        "warn" if ungated else "pass",
        "high" if ungated else "low",
        "Frequent model jobs lack deterministic wake gates" if ungated else "Frequent scheduled work is deterministically gated",
        {
            "frequent_jobs": total,
            "deterministic_jobs": deterministic,
            "wake_gated_jobs": gated,
            "ungated_jobs": ungated,
            "efficiency_score": score,
        },
    )


def _prompt_drift(jobs: list[dict[str, Any]], current_version: str) -> dict[str, Any]:
    drift: list[dict[str, str]] = []
    for job in jobs:
        prompt = str(job.get("prompt", ""))
        match = LEGACY_PATTERN.search(prompt)
        if match:
            drift.append({"job_id": str(job.get("id", "")), "match": match.group(0)})
    return _finding(
        "prompt_drift",
        "warn" if drift else "pass",
        "medium" if drift else "low",
        "Legacy LPOS version guidance remains in scheduled prompts" if drift else "No obsolete LPOS prompt references detected",
        {"current_version": current_version, "drift": drift},
    )


def _mutable_immutable(repo: Path) -> dict[str, Any]:
    manifest = _json(repo / "RELEASE-MANIFEST.json", {})
    expected = set(manifest.get("files", {})) if isinstance(manifest, dict) else set()
    ignored = {".git", ".venv", "state", ".pytest_cache", "dist", "build"}
    mutable_suffixes = {".db", ".db-wal", ".db-shm", ".jsonl", ".log"}
    unlisted_mutable: list[str] = []
    for path in repo.rglob("*"):
        if not path.is_file() or path.is_symlink():
            continue
        relative = path.relative_to(repo)
        if relative.parts and relative.parts[0] in ignored:
            continue
        name = relative.as_posix()
        if name not in expected and any(path.name.endswith(suffix) for suffix in mutable_suffixes):
            unlisted_mutable.append(name)
    return _finding(
        "mutable_immutable_boundary",
        "fail" if unlisted_mutable else "pass",
        "critical" if unlisted_mutable else "low",
        "Mutable state exists inside the immutable release tree" if unlisted_mutable else "Mutable and immutable paths are separated",
        {"unlisted_mutable_files": unlisted_mutable},
    )


def _storage_efficiency(repo: Path, hermes_root: Path) -> dict[str, Any]:
    repo_stats = _tree_stats(repo)
    lpos_stats = _tree_stats(hermes_root / "lpos")
    cache_stats = _tree_stats(hermes_root / "cache")
    release_dirs = []
    lpos_root = hermes_root / "lpos"
    if lpos_root.is_dir():
        release_dirs = sorted(path.name for path in lpos_root.iterdir() if path.is_dir() and not path.is_symlink())
    warning = lpos_stats["bytes"] > 2 * 1024**3 or len(release_dirs) > 3
    return _finding(
        "storage_efficiency",
        "warn" if warning else "pass",
        "medium" if warning else "low",
        "Release or cache retention exceeds the operating target" if warning else "Storage retention is within the operating target",
        {
            "repository": repo_stats,
            "lpos_root": lpos_stats,
            "cache": cache_stats,
            "release_directories": release_dirs,
            "targets": {"lpos_bytes": 2 * 1024**3, "release_directories": 3},
        },
    )


def _technical_debt(state_root: Path, jobs: list[dict[str, Any]]) -> dict[str, Any]:
    path = state_root / "coe" / "technical-debt.json"
    data = _json(path, [])
    rows = data if isinstance(data, list) else []
    invalid = []
    overdue = []
    compatibility_jobs = [
        str(job.get("id", ""))
        for job in jobs
        if "compatibility" in str(job.get("prompt", "")).lower()
    ]
    today = utcnow().date().isoformat()
    for index, row in enumerate(rows):
        if not isinstance(row, dict) or not REQUIRED_DEBT_FIELDS.issubset(row):
            invalid.append(index)
            continue
        if str(row.get("status", "")).lower() not in {"retired", "closed"} and str(row.get("retirement_date", "")) < today:
            overdue.append(str(row.get("id")))
    undocumented = bool(compatibility_jobs and not rows)
    return _finding(
        "technical_debt_lifecycle",
        "warn" if invalid or overdue or undocumented else "pass",
        "medium" if invalid or overdue or undocumented else "low",
        "Technical debt records are invalid, overdue, or missing for a compatibility layer"
        if invalid or overdue or undocumented
        else "Technical debt lifecycle records are valid",
        {
            "path": str(path),
            "records": len(rows),
            "invalid_indexes": invalid,
            "overdue_ids": overdue,
            "compatibility_job_ids": compatibility_jobs,
            "undocumented_compatibility": undocumented,
        },
    )


def _documentation(repo: Path) -> dict[str, Any]:
    required = [
        "README.md",
        "CHANGELOG.md",
        "docs/ARCHITECTURE.md",
        "docs/TESTING.md",
        "docs/wiki/administration/cli-reference.md",
        "docs/wiki/administration/backups.md",
    ]
    missing = [name for name in required if not (repo / name).is_file()]
    return _finding(
        "documentation_audit",
        "fail" if missing else "pass",
        "high" if missing else "low",
        "Required operating documentation is missing" if missing else "Required operating documentation is present",
        {"required": required, "missing": missing},
    )


def _security(findings: list[dict[str, Any]]) -> dict[str, Any]:
    security_domains = {"release_integrity", "backup_governance", "mutable_immutable_boundary"}
    blockers = [item["domain"] for item in findings if item["domain"] in security_domains and item["status"] == "fail"]
    return _finding(
        "security_audit",
        "fail" if blockers else "pass",
        "critical" if blockers else "low",
        "Security-critical COE controls failed" if blockers else "Security-critical COE controls passed",
        {"blocking_domains": blockers},
    )


def _engineering(findings: list[dict[str, Any]]) -> dict[str, Any]:
    blockers = [item["domain"] for item in findings if item["status"] == "fail"]
    warnings = [item["domain"] for item in findings if item["status"] == "warn"]
    return _finding(
        "engineering_audit",
        "fail" if blockers else "warn" if warnings else "pass",
        "critical" if blockers else "medium" if warnings else "low",
        "Engineering controls require remediation" if blockers or warnings else "Engineering controls passed",
        {"blocking_domains": blockers, "warning_domains": warnings},
    )


def _opportunity(findings: list[dict[str, Any]]) -> dict[str, Any]:
    opportunities = [
        {"domain": item["domain"], "action": item["summary"]}
        for item in findings
        if item["status"] in {"warn", "fail"}
    ]
    return _finding(
        "opportunity_audit",
        "pass",
        "low",
        "Operational opportunities derived from current findings",
        {"opportunities": opportunities},
    )


def _score(items: list[dict[str, Any]]) -> int:
    score = 100
    for item in items:
        if item["status"] == "fail":
            score -= 30 if item["severity"] == "critical" else 20
        elif item["status"] == "warn":
            score -= 12 if item["severity"] in {"high", "critical"} else 7
    return max(0, score)


def _render_report(audit: dict[str, Any]) -> str:
    lines = [
        "# LPOS Continuous Operational Excellence Report",
        "",
        f"Audit ID: `{audit['audit_id']}`",
        f"Timestamp: {audit['generated_at']}",
        f"Release: {audit['release_version']}",
        f"Overall health: {audit['scores']['overall']} / 100",
        f"Release readiness: {'READY' if audit['release_ready'] else 'BLOCKED'}",
        f"Dashboard: {audit['dashboard_url']}",
        "",
        "## Findings",
        "",
    ]
    for item in audit["findings"]:
        lines.extend(
            [
                f"### {item['domain'].replace('_', ' ').title()}: {item['status'].upper()}",
                "",
                item["summary"],
                "",
                "```json",
                json.dumps(item["evidence"], indent=2, sort_keys=True),
                "```",
                "",
            ]
        )
    return "\n".join(lines)


def _render_email(audit: dict[str, Any]) -> str:
    critical = [item for item in audit["findings"] if item["status"] == "fail"]
    warnings = [item for item in audit["findings"] if item["status"] == "warn"]
    lines = [
        "Subject: LPOS Continuous Operational Excellence Report",
        "",
        "# Executive Summary",
        "",
        f"LPOS {audit['release_version']} is {'ready' if audit['release_ready'] else 'blocked'} with an overall health score of {audit['scores']['overall']}.",
        "",
        f"Dashboard: {audit['dashboard_url']}",
        f"Timestamp: {audit['generated_at']}",
        f"Latest audit ID: {audit['audit_id']}",
        "",
        "# Key Findings",
        "",
    ]
    if not critical and not warnings:
        lines.append("All COE audit domains passed.")
    for item in critical + warnings:
        lines.append(f"- {item['domain']}: {item['summary']}")
    lines.extend(
        [
            "",
            "# Critical Risks",
            "",
            *(f"- {risk}" for risk in audit["top_risks"]),
            "",
            "# Engineering Findings",
            "",
            f"Engineering score: {audit['scores']['engineering']} / 100",
            "",
            "# Code Review Summary",
            "",
            "The deterministic release verifier and evaluation suite are represented in the audit findings below. Independent human or agent review evidence remains a separate release artifact.",
            "",
            "# Bloat Findings",
            "",
            *(f"- {item['domain']}: {item['summary']}" for item in audit["findings"] if item["domain"] in {"backup_governance", "scheduler_governance", "wake_agent_efficiency", "prompt_drift", "storage_efficiency", "technical_debt_lifecycle"}),
            "",
            "# Recommendations",
            "",
            *(f"- {item['action']}" for item in audit["opportunity_backlog"]),
            "",
            "# Dashboard Link",
            "",
            audit["dashboard_url"],
            "",
            "# Full Appendix",
            "",
            _render_report(audit),
        ]
    )
    return "\n".join(lines)


def _render_dashboard(audit: dict[str, Any]) -> str:
    cards = []
    for label, value in audit["scores"].items():
        cards.append(f'<section class="score"><span>{html.escape(label.replace("_", " ").title())}</span><strong>{value}</strong></section>')
    rows = []
    for item in audit["findings"]:
        rows.append(
            "<tr>"
            f"<td>{html.escape(item['domain'].replace('_', ' ').title())}</td>"
            f"<td><span class=\"badge {html.escape(item['status'])}\">{html.escape(item['status'].upper())}</span></td>"
            f"<td>{html.escape(item['severity'].upper())}</td>"
            f"<td>{html.escape(item['summary'])}</td>"
            "</tr>"
        )
    readiness = "READY" if audit["release_ready"] else "BLOCKED"
    risks = "".join(f"<li>{html.escape(item)}</li>" for item in audit["top_risks"]) or "<li>None</li>"
    opportunities = "".join(
        f"<li><strong>{html.escape(item['domain'].replace('_', ' ').title())}</strong>: {html.escape(item['action'])}</li>"
        for item in audit["opportunity_backlog"]
    ) or "<li>None</li>"
    approvals = "".join(f"<li>{html.escape(str(item))}</li>" for item in audit["pending_approvals"]) or "<li>None</li>"
    improvements = "".join(f"<li>{html.escape(str(item))}</li>" for item in audit["recent_improvements"]) or "<li>None recorded</li>"
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>LPOS Operational Excellence</title>
<style>
:root{{--ink:#eaf2ff;--muted:#91a4bd;--panel:#111d2b;--line:#283a50;--accent:#5bd5c5;--danger:#ff6b7a;--warn:#f7c65c}}*{{box-sizing:border-box}}body{{margin:0;background:#08111d;color:var(--ink);font:15px/1.5 ui-sans-serif,system-ui;padding:32px}}main{{max-width:1200px;margin:auto}}header{{display:flex;justify-content:space-between;gap:24px;align-items:end;border-bottom:1px solid var(--line);padding-bottom:24px}}h1{{font-size:34px;margin:0}}h2{{font-size:18px}}p{{color:var(--muted)}}.ready{{font-size:28px;color:{'var(--accent)' if audit['release_ready'] else 'var(--danger)'}}}.scores,.details{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px;margin:24px 0}}.score,.detail{{background:var(--panel);border:1px solid var(--line);padding:16px}}.score span{{display:block;color:var(--muted);font-size:12px;text-transform:uppercase;letter-spacing:.08em}}.score strong{{font-size:28px}}table{{width:100%;border-collapse:collapse;background:var(--panel)}}th,td{{padding:12px;text-align:left;border-bottom:1px solid var(--line);vertical-align:top}}th{{color:var(--muted);font-size:12px;text-transform:uppercase}}.badge{{font-weight:700}}.pass{{color:var(--accent)}}.warn{{color:var(--warn)}}.fail{{color:var(--danger)}}code{{color:var(--accent)}}
</style></head><body><main><header><div><p>LPOS Continuous Operational Excellence</p><h1>Operational health and release readiness</h1><p>Release {html.escape(audit['release_version'])} · Audit <code>{html.escape(audit['audit_id'])}</code> · {html.escape(audit['generated_at'])}</p></div><strong class="ready">{readiness}</strong></header><div class="scores">{''.join(cards)}</div><table><thead><tr><th>Domain</th><th>Status</th><th>Severity</th><th>Finding</th></tr></thead><tbody>{''.join(rows)}</tbody></table><div class="details"><section class="detail"><h2>Top risks</h2><ul>{risks}</ul></section><section class="detail"><h2>Opportunity backlog</h2><ul>{opportunities}</ul></section><section class="detail"><h2>Pending approvals</h2><ul>{approvals}</ul></section><section class="detail"><h2>Recent improvements</h2><ul>{improvements}</ul></section><section class="detail"><h2>Audit history</h2><p>Append-only history is stored in <code>coe/history.jsonl</code>. Latest audit: <code>{html.escape(audit['audit_id'])}</code>.</p></section><section class="detail"><h2>Current release status</h2><p>{html.escape(audit['current_release_status'].upper())}</p></section></div></main></body></html>"""


def run_audit(
    repo: Path,
    hermes_root: Path,
    state_root: Path,
    dashboard_url: str,
    *,
    include_evaluations: bool = False,
) -> dict[str, Any]:
    repo = Path(repo).resolve()
    hermes_root = Path(hermes_root).expanduser().resolve()
    state_root = Path(state_root).expanduser().resolve()
    release = _json(repo / "RELEASE.json", {})
    version = str(release.get("version", "unknown")) if isinstance(release, dict) else "unknown"
    jobs = _jobs(hermes_root)
    core_findings = [
        _release_integrity(repo),
        _backup_governance(hermes_root),
        _scheduler_governance(hermes_root, jobs),
        _wake_efficiency(hermes_root, jobs),
        _prompt_drift(jobs, version),
        _mutable_immutable(repo),
        _storage_efficiency(repo, hermes_root),
        _technical_debt(state_root, jobs),
        _documentation(repo),
    ]
    if include_evaluations:
        from .evals import run_core_evaluations

        evaluations = run_core_evaluations()
        core_findings.append(
            _finding(
                "deterministic_evaluations",
                "pass" if evaluations["failed"] == 0 else "fail",
                "critical",
                "Deterministic evaluation suite passed" if evaluations["failed"] == 0 else "Deterministic evaluation suite failed",
                {
                    "passed": evaluations["passed"],
                    "failed": evaluations["failed"],
                    "total": evaluations["total"],
                },
            )
        )
    findings = core_findings + [_security(core_findings), _engineering(core_findings), _opportunity(core_findings)]
    domain_scores = {item["domain"]: _score([item]) for item in findings}
    scores = {
        "overall": _score(core_findings),
        "engineering": domain_scores["engineering_audit"],
        "security": domain_scores["security_audit"],
        "efficiency": round((domain_scores["wake_agent_efficiency"] + domain_scores["storage_efficiency"]) / 2),
        "cost": domain_scores["wake_agent_efficiency"],
        "documentation": domain_scores["documentation_audit"],
    }
    critical = [item for item in core_findings if item["status"] == "fail" and item["severity"] == "critical"]
    payload: dict[str, Any] = {
        "schema_version": 1,
        "generated_at": iso(),
        "release_version": version,
        "repo": str(repo),
        "hermes_root": str(hermes_root),
        "state_root": str(state_root),
        "dashboard_url": dashboard_url,
        "scores": scores,
        "release_ready": not critical,
        "release_blockers": [item["domain"] for item in critical],
        "findings": findings,
        "top_risks": [item["summary"] for item in findings if item["status"] in {"warn", "fail"}][:10],
        "pending_approvals": [],
        "recent_improvements": [],
        "opportunity_backlog": next(item["evidence"]["opportunities"] for item in findings if item["domain"] == "opportunity_audit"),
        "current_release_status": "ready" if not critical else "blocked",
    }
    signature = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    payload["audit_id"] = "COE-" + hashlib.sha256(signature).hexdigest()[:16].upper()
    coe_root = state_root / "coe"
    _atomic_write(coe_root / "latest.json", json.dumps(payload, indent=2, sort_keys=True) + "\n")
    history = coe_root / "history.jsonl"
    history.parent.mkdir(parents=True, exist_ok=True)
    with history.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n")
    _atomic_write(coe_root / "report.md", _render_report(payload) + "\n")
    _atomic_write(coe_root / "daily-email.md", _render_email(payload) + "\n")
    _atomic_write(coe_root / "dashboard.html", _render_dashboard(payload))
    return payload


def load_latest(state_root: Path) -> dict[str, Any]:
    data = _json(Path(state_root).expanduser().resolve() / "coe" / "latest.json", {})
    return data if isinstance(data, dict) else {}


def serve(state_root: Path, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> None:
    if host not in {"127.0.0.1", "localhost", "::1"} and os.environ.get("LPOS_COE_ALLOW_NONLOOPBACK") != "1":
        raise ValueError("COE dashboard refuses non-loopback binding without LPOS_COE_ALLOW_NONLOOPBACK=1")
    root = Path(state_root).expanduser().resolve() / "coe"

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            if self.path in {"/", "/dashboard/coe"}:
                path = root / "dashboard.html"
                body = path.read_bytes() if path.is_file() else b"COE audit has not run."
                content_type = "text/html; charset=utf-8"
                status = 200 if path.is_file() else 503
            elif self.path == "/api/coe":
                path = root / "latest.json"
                body = path.read_bytes() if path.is_file() else b"{}"
                content_type = "application/json; charset=utf-8"
                status = 200 if path.is_file() else 503
            else:
                body = b"Not found"
                content_type = "text/plain; charset=utf-8"
                status = 404
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Referrer-Policy", "no-referrer")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: Any) -> None:
            return

    server = ThreadingHTTPServer((host, port), Handler)
    print(f"LPOS COE dashboard: http://{host}:{port}/dashboard/coe", flush=True)
    server.serve_forever()
