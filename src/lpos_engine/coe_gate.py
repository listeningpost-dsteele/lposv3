"""Independent command entry point for the nine mandatory COE release gates."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import py_compile
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .coe_contract import (
    GATE_IDS,
    canonical_json,
    evidence_hash,
    redact,
    sha256_bytes,
    sha256_file,
    sortable_id,
    utc_now,
)
from .coe_manifest import verify_release
from .coe_store import COEStore

Check = dict[str, Any]


def _check(check_id: str, status: str, detail: str, **evidence: Any) -> Check:
    return {"check_id": check_id, "status": status, "detail": detail, **evidence}


def _run(argv: list[str], cwd: Path, timeout: int = 1200, maximum_bytes: int = 1024 * 1024) -> dict[str, Any]:
    started = time.monotonic()
    try:
        completed = subprocess.run(
            argv,
            cwd=cwd,
            env={
                "PATH": os.environ.get("PATH", ""),
                "HOME": os.environ.get("HOME", ""),
                "PYTHONPATH": os.environ.get("PYTHONPATH", ""),
                "LANG": "C.UTF-8",
                "LC_ALL": "C.UTF-8",
            },
            capture_output=True,
            check=False,
            timeout=timeout,
        )
        stdout = completed.stdout[:maximum_bytes]
        stderr = completed.stderr[:maximum_bytes]
        return {
            "argv": argv,
            "returncode": completed.returncode,
            "signal": None,
            "duration_ms": round((time.monotonic() - started) * 1000),
            "stdout": stdout,
            "stderr": stderr,
            "stdout_truncated": len(completed.stdout) > maximum_bytes,
            "stderr_truncated": len(completed.stderr) > maximum_bytes,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "argv": argv,
            "returncode": None,
            "signal": "timeout",
            "duration_ms": round((time.monotonic() - started) * 1000),
            "stdout": (exc.stdout or b"")[:maximum_bytes],
            "stderr": (exc.stderr or b"")[:maximum_bytes],
            "stdout_truncated": False,
            "stderr_truncated": False,
        }
    except OSError as exc:
        return {
            "argv": argv,
            "returncode": None,
            "signal": "spawn_error",
            "duration_ms": round((time.monotonic() - started) * 1000),
            "stdout": b"",
            "stderr": str(exc).encode("utf-8"),
            "stdout_truncated": False,
            "stderr_truncated": False,
        }


def _deterministic(context: dict[str, Any]) -> tuple[list[Check], list[dict[str, str]], bytes, bytes]:
    configured = context.get("deterministic_commands")
    commands = configured or [{"name": "deterministic-suite", "command": context.get("deterministic_command") or [sys.executable, "-m", "pytest", "-q"], "cwd": context["repo"]}]
    checks: list[Check] = []
    stdout = b""
    stderr = b""
    for index, item in enumerate(commands):
        if not isinstance(item, dict):
            return [_check("command-contract", "fail", "deterministic command entry is invalid")], [], b"", b""
        command = item.get("command")
        if not isinstance(command, list) or not command or not all(isinstance(part, str) for part in command):
            return [_check("command-contract", "fail", "deterministic command is invalid")], [], b"", b""
        result = _run(command, Path(item.get("cwd", context["repo"])), timeout=int(context.get("gate_timeout_seconds", 1800)))
        passed = result["returncode"] == 0 and result["signal"] is None
        checks.append(_check(str(item.get("name", f"deterministic-suite-{index + 1}")), "pass" if passed else "fail", "deterministic suite completed successfully" if passed else "deterministic suite failed or timed out", returncode=result["returncode"], signal=result["signal"], duration_ms=result["duration_ms"], output_truncated=result["stdout_truncated"] or result["stderr_truncated"]))
        stdout += result["stdout"]
        stderr += result["stderr"]
    return checks, [], stdout, stderr


def _application_verifier(context: dict[str, Any]) -> tuple[list[Check], list[dict[str, str]], bytes, bytes]:
    try:
        result = verify_release(
            Path(context["release_root"]),
            expected_identity=context["identity"],
            expected_commit=context["release"]["git_commit"],
        )
    except Exception as exc:
        return [_check("immutable-release", "fail", f"release verification failed: {exc}")], [], b"", str(exc).encode()
    manifest = Path(context["release_root"]) / "release-manifest.json"
    artifacts = [{"path": str(manifest), "sha256": sha256_file(manifest)}]
    verification_detail = {key: value for key, value in result.items() if key != "status"}
    return [
        _check(
            "immutable-release",
            "pass",
            "all staged release files, metadata, paths, modes, and hashes verified",
            **verification_detail,
        )
    ], artifacts, canonical_json(result).encode(), b""


def _doctor(context: dict[str, Any]) -> tuple[list[Check], list[dict[str, str]], bytes, bytes]:
    repo = Path(context["repo"]).resolve()
    release_root = Path(context["release_root"]).resolve()
    state_root = Path(context["state_root"]).resolve()
    checks: list[Check] = []
    checks.append(_check("state-outside-release", "pass" if release_root not in state_root.parents and state_root != release_root else "fail", "state root is outside the immutable release" if release_root not in state_root.parents and state_root != release_root else "state root overlaps immutable release", state_root=str(state_root)))
    config = context.get("configuration", {})
    production = bool(context.get("production"))
    required = ["COE_ENABLED", "COE_SCHEDULE_ENABLED", "COE_DASHBOARD_ENABLED", "COE_EMAIL_ENABLED"]
    missing_flags = [name for name in required if production and str(config.get(name, "")).lower() != "true"]
    required_values = ["COE_TIMEZONE", "COE_CRON", "COE_STATE_DIR", "PUBLIC_BASE_URL", "COE_DASHBOARD_PATH"]
    missing_values = [name for name in required_values if production and not config.get(name)]
    checks.append(_check("required-configuration", "fail" if missing_flags or missing_values else "pass", "production COE configuration is complete" if not missing_flags and not missing_values else "production COE configuration is missing or disabled", missing_flags=missing_flags, missing_values=missing_values))
    checks.append(_check("schedule-contract", "pass" if config.get("COE_TIMEZONE", "America/Chicago") == "America/Chicago" and config.get("COE_CRON", "0 3 * * *") == "0 3 * * *" else "fail", "daily schedule is 03:00 America/Chicago"))
    try:
        store = COEStore(state_root)
        integrity = store.integrity()
        healthy = bool(integrity.get("ok"))
    except Exception as exc:
        integrity = {"error": str(exc)}
        healthy = False
    checks.append(_check("sqlite-integrity", "pass" if healthy else "fail", "SQLite and audit chains are healthy" if healthy else "SQLite or audit-chain integrity failed", result=integrity))
    try:
        verified = verify_release(release_root, expected_identity=context["identity"], expected_commit=context["release"]["git_commit"])
        checks.append(_check("installed-release-integrity", "pass", "installed release tree verified", artifact_sha256=verified["artifact_sha256"]))
    except Exception as exc:
        checks.append(_check("installed-release-integrity", "fail", f"installed release verification failed: {exc}"))
    writable = state_root.exists() and os.access(state_root, os.W_OK)
    source_readonly = not os.access(release_root / "release-manifest.json", os.W_OK) if context.get("require_readonly_release") else True
    checks.append(_check("path-access", "pass" if writable and source_readonly else "fail", "state is writable and release access policy is satisfied", state_writable=writable, release_readonly=source_readonly))
    dashboard_path = str(config.get("COE_DASHBOARD_PATH", "/dashboard/coe"))
    checks.append(_check("dashboard-auth-route", "pass" if dashboard_path == "/dashboard/coe" and bool(context.get("dashboard_auth_required", True)) else "fail", "dashboard route and authentication policy are configured"))
    email_ok = not production or (bool(config.get("COE_REPORT_RECIPIENT")) and bool(config.get("COE_EMAIL_TRANSPORT")))
    checks.append(_check("email-transport", "pass" if email_ok else "fail", "email transport is configured without exposing credentials" if email_ok else "email recipient or transport is unavailable"))
    return checks, [], canonical_json({"repo": str(repo), "state": str(state_root)}).encode(), b""


def _engineering(context: dict[str, Any]) -> tuple[list[Check], list[dict[str, str]], bytes, bytes]:
    sources = context.get("source_repositories") or [{"path": context["repo"], "baseline_commit": context.get("baseline_commit"), "target_commit": context["release"]["git_commit"]}]
    changed: list[dict[str, str]] = []
    inventory_failures: list[dict[str, str]] = []
    stdout = b""
    stderr = b""
    for source in sources:
        repo = Path(source["path"])
        baseline = str(source.get("baseline_commit") or source["target_commit"])
        target = str(source["target_commit"])
        diff = _run(["git", "diff", "--name-status", "--find-renames", f"{baseline}..{target}"], repo, timeout=120)
        stdout += diff["stdout"]
        stderr += diff["stderr"]
        if diff["returncode"] != 0:
            inventory_failures.append({"repository": str(repo), "target": target})
            continue
        for line in diff["stdout"].decode("utf-8", "replace").splitlines():
            parts = line.split("\t")
            if len(parts) >= 2:
                changed.append({"repository": str(repo), "status": parts[0], "path": parts[-1]})
    checks = [_check("change-inventory", "pass" if not inventory_failures else "fail", "every changed file is enumerated" if not inventory_failures else "one or more changed-file inventories failed", changed=changed, failures=inventory_failures)]
    compile_failures: list[str] = []
    oversized: list[str] = []
    for item in changed:
        path = Path(item["repository"]) / item["path"]
        if not path.is_file() or path.suffix != ".py":
            continue
        try:
            py_compile.compile(str(path), doraise=True)
        except py_compile.PyCompileError as exc:
            compile_failures.append(f"{item['path']}: {exc.msg}")
        try:
            lines = len(path.read_text(encoding="utf-8").splitlines())
            if lines > 1200:
                oversized.append(f"{item['path']}:{lines}")
        except OSError:
            compile_failures.append(f"{item['path']}: unreadable")
    checks.append(_check("changed-python-syntax", "pass" if not compile_failures else "fail", "changed Python files compile" if not compile_failures else "changed Python files do not compile", failures=compile_failures))
    checks.append(_check("changed-file-maintainability", "pass", "changed implementation file size was measured; oversized files remain recorded as noncritical findings", oversized=oversized))
    source_writes = [item["path"] for item in changed if item["path"].startswith(("state/", "status/", "reports/", "backups/")) and item["status"] != "D"]
    checks.append(_check("immutable-write-scan", "pass" if not source_writes else "fail", "change set does not add mutable release-tree state" if not source_writes else "change set includes mutable release-tree state", paths=source_writes))
    return checks, [], stdout, stderr


def _secret_candidates(roots: list[Path]) -> list[str]:
    findings: list[str] = []
    assignment = re.compile(r"(?i)(api[_-]?key|password|client[_-]?secret|authorization)\s*[:=]\s*[\"']([^\"']{16,})[\"']")
    private_key = "-----BEGIN "
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or path.is_symlink() or path.stat().st_size > 5 * 1024 * 1024:
                continue
            if set(path.parts) & {".git", ".venv", "node_modules", "__pycache__"}:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            for line in text.splitlines():
                lowered = line.lower()
                if any(marker in lowered for marker in ("fixture", "example", "placeholder", "secure-value", "[redacted]")):
                    continue
                match = assignment.search(line)
                value = match.group(2).lower() if match else ""
                known_fixture = any(marker in value for marker in ("test", "fixture", "example", "placeholder", "redacted", "process.env", "${"))
                if (match and not known_fixture) or private_key in line:
                    findings.append(str(path))
                    break
    return findings[:100]


def _security(context: dict[str, Any]) -> tuple[list[Check], list[dict[str, str]], bytes, bytes]:
    repo = Path(context["repo"])
    roots = [Path(item["path"]) for item in context.get("source_repositories", [{"path": context["repo"]}])]
    roots.extend([Path(context["release_root"]), Path(context["state_root"]) / "coe" / "reports"])
    leaked = _secret_candidates(roots)
    checks = [_check("secret-scan", "pass" if not leaked else "fail", "tracked source, release, evidence, and reports contain no credential patterns" if not leaked else "credential-like material was detected", paths=leaked)]
    auth_command = context.get("security_command")
    stdout = b""
    stderr = b""
    if auth_command:
        result = _run(list(auth_command), repo, timeout=int(context.get("gate_timeout_seconds", 1800)))
        stdout, stderr = result["stdout"], result["stderr"]
        checks.append(_check("security-test-command", "pass" if result["returncode"] == 0 else "fail", "security and reliability tests passed" if result["returncode"] == 0 else "security and reliability tests failed", returncode=result["returncode"], signal=result["signal"]))
    else:
        checks.append(_check("security-test-command", "unknown", "no authenticated dashboard, isolation, failure-injection, or logging test command was supplied"))
    store = COEStore(Path(context["state_root"]))
    with store.engine.connection() as conn:
        restore = conn.execute("SELECT status,completed_at FROM coe_restore_tests ORDER BY completed_at DESC LIMIT 1").fetchone()
    fresh = False
    if restore and restore["status"] == "pass":
        try:
            age = datetime.now(timezone.utc) - datetime.fromisoformat(str(restore["completed_at"]).replace("Z", "+00:00"))
            fresh = age.days <= 7
        except ValueError:
            fresh = False
    checks.append(_check("backup-restore-evidence", "pass" if fresh else "fail", "a real isolated restore passed within policy age" if fresh else "fresh real restore evidence is absent"))
    dependency_command = context.get("dependency_audit_command")
    if dependency_command:
        result = _run(list(dependency_command), repo, timeout=600)
        checks.append(_check("dependency-audit", "pass" if result["returncode"] == 0 else "fail", "dependency audit passed" if result["returncode"] == 0 else "dependency audit failed or was unavailable", returncode=result["returncode"], signal=result["signal"]))
        stdout += result["stdout"]
        stderr += result["stderr"]
    else:
        checks.append(_check("dependency-audit", "unknown", "no pinned dependency audit command was supplied"))
    return checks, [], stdout, stderr


def _documentation(context: dict[str, Any]) -> tuple[list[Check], list[dict[str, str]], bytes, bytes]:
    repo = Path(context.get("documentation_repo", context["repo"]))
    required = [
        "docs/architecture/coe/README.md", "docs/architecture/coe/DATA_MODEL.md",
        "docs/architecture/coe/RELEASE_ASSURANCE.md", "docs/architecture/coe/OPERATIONS.md",
        "docs/architecture/coe/DASHBOARD.md", "docs/architecture/coe/SECURITY.md",
        "docs/passoff/LPOS-v4.5.0-COE.md", "docs/COE-BLOAT-CLOSEOUT-ADDENDUM.md",
        "docs/ARCHITECTURE.md", "docs/TESTING.md", "CHANGELOG.md",
    ]
    missing = [name for name in required if not (repo / name).is_file()]
    checks = [_check("repository-documentation", "pass" if not missing else "fail", "required COE repository documentation is present" if not missing else "required COE documentation is missing", missing=missing)]
    application_repo = Path(context["repo"])
    application_required = ["docs/architecture/coe/README.md", "docs/architecture/coe/OPERATIONS.md", "docs/architecture/coe/DASHBOARD-SECURITY.md", "docs/passoff/LPOS-v4.5.0-COE.md"]
    application_missing = [name for name in application_required if not (application_repo / name).is_file()]
    checks.append(_check("application-documentation", "pass" if not application_missing else "fail", "deployed service COE documentation is present" if not application_missing else "deployed service COE documentation is missing", missing=application_missing))
    version_drift: list[str] = []
    for name in required:
        path = repo / name
        if path.is_file() and "4.5.0" not in path.read_text(encoding="utf-8", errors="replace") and name.startswith(("docs/architecture/coe", "docs/passoff")):
            version_drift.append(name)
    checks.append(_check("documentation-version", "pass" if not version_drift else "fail", "COE documentation names the authoritative release" if not version_drift else "COE documentation release identity drifted", paths=version_drift))
    passoff = context.get("documentation_passoff", [])
    required_surfaces = {"github", "wiki", "google-drive"}
    verified = {
        str(item.get("surface"))
        for item in passoff
        if isinstance(item, dict) and item.get("status") == "verified" and item.get("reference") and item.get("verified_at")
    }
    absent = sorted(required_surfaces - verified)
    checks.append(_check("external-passoff", "pass" if not absent else "fail", "GitHub, wiki, and Google Drive pass-off references were verified" if not absent else "external documentation pass-off is incomplete", missing_surfaces=absent))
    obsolete: list[str] = []
    for path in repo.rglob("*.md"):
        relative = path.relative_to(repo).as_posix()
        if relative.startswith("docs/history/") or relative == "docs/implementation/COE-IMPLEMENTATION-ORDER.md":
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if "Use LPOS v3" in text:
            obsolete.append(relative)
    checks.append(_check("obsolete-guidance", "pass" if not obsolete else "fail", "active documentation contains no obsolete LPOS v3 instructions" if not obsolete else "active documentation contains obsolete LPOS guidance", paths=obsolete))
    return checks, [], canonical_json({"required": required, "passoff": passoff}).encode(), b""


def _tree_stats(root: Path) -> tuple[int, int]:
    count = total = 0
    if not root.exists():
        return count, total
    for path in root.rglob("*"):
        if path.is_file() and not path.is_symlink():
            count += 1
            total += path.stat().st_size
    return count, total


def _bloat(context: dict[str, Any]) -> tuple[list[Check], list[dict[str, str]], bytes, bytes]:
    repo = Path(context["repo"])
    release_root = Path(context["release_root"])
    state_root = Path(context["state_root"])
    tracked = _run(["git", "ls-files", "-z"], repo, timeout=60)
    tracked_names = [item.decode("utf-8") for item in tracked["stdout"].split(b"\0") if item]
    tracked_bytes = sum((repo / name).stat().st_size for name in tracked_names if (repo / name).is_file())
    status = _run(["git", "status", "--porcelain=v2", "--untracked-files=all"], repo, timeout=60)
    dirty = status["returncode"] != 0 or bool(status["stdout"].strip())
    checks = [_check("clean-source-context", "pass" if not dirty else "fail", "source context is clean" if not dirty else "source context contains unapproved changes", source_status=redact(status["stdout"].decode("utf-8", "replace")[:8192]))]
    release_count, release_bytes = _tree_stats(release_root)
    state_count, state_bytes = _tree_stats(state_root)
    checks.append(_check("storage-inventory", "pass", "repository, release, and mutable-state storage were measured", tracked_files=len(tracked_names), tracked_bytes=tracked_bytes, release_files=release_count, release_bytes=release_bytes, state_files=state_count, state_bytes=state_bytes))
    hashes: dict[tuple[int, str], list[str]] = defaultdict(list)
    for name in tracked_names:
        path = repo / name
        if path.is_file() and path.stat().st_size:
            hashes[(path.stat().st_size, sha256_file(path))].append(name)
    duplicates = [names for names in hashes.values() if len(names) > 1]
    duplicate_bytes = sum((repo / names[0]).stat().st_size * (len(names) - 1) for names in duplicates)
    checks.append(_check("duplicate-content", "pass", "duplicate content was measured without classifying generated mirrors as defects", groups=duplicates[:50], duplicate_bytes=duplicate_bytes))
    nested_backups = [str(path) for path in state_root.rglob("*") if path.is_dir() and "backup" in path.name.lower() and any("backup" in part.lower() for part in path.relative_to(state_root).parts[:-1])]
    checks.append(_check("nested-backups", "pass" if not nested_backups else "fail", "no nested backup roots were found" if not nested_backups else "nested backup roots were detected", paths=nested_backups[:50]))
    return checks, [], tracked["stdout"] + status["stdout"], tracked["stderr"] + status["stderr"]


def _opportunity(context: dict[str, Any]) -> tuple[list[Check], list[dict[str, str]], bytes, bytes]:
    store = COEStore(Path(context["state_root"]))
    findings = store.findings(limit=500)
    opportunities = store.opportunities(limit=500)
    mapped = {item.get("finding_id") for item in opportunities if item.get("owner") and item.get("status")}
    orphaned = [item.get("finding_id") for item in findings if item.get("severity") in {"critical", "high"} and item.get("status") == "open" and item.get("finding_id") not in mapped and not item.get("accepted_risk")]
    required_fields = {"problem_statement", "proposed_change", "operator_time_saved", "compute_saved", "latency_reduced", "risk_reduced", "maintenance_reduced", "quality_improved", "implementation_effort", "confidence", "approval_status", "owner"}
    invalid = [item.get("opportunity_id") for item in opportunities if not required_fields.issubset(item)]
    checks = [
        _check("critical-finding-coverage", "pass" if not orphaned else "fail", "every critical or high finding has an owned opportunity or accepted-risk decision" if not orphaned else "critical or high findings are orphaned", finding_ids=orphaned),
        _check("opportunity-contract", "pass" if not invalid else "fail", "opportunities include value, effort, confidence, owner, and decision fields" if not invalid else "opportunity records are incomplete", opportunity_ids=invalid),
    ]
    return checks, [], canonical_json({"findings": findings, "opportunities": opportunities}).encode(), b""


def _release_integrity(context: dict[str, Any]) -> tuple[list[Check], list[dict[str, str]], bytes, bytes]:
    store = COEStore(Path(context["state_root"]))
    prior = store.evidence(context["audit_id"])
    expected = list(GATE_IDS[:-1])
    checks: list[Check] = []
    actual = [item.get("gate_id") for item in prior]
    checks.append(_check("prior-gate-set", "pass" if actual == expected else "fail", "the eight prerequisite gate records are complete and ordered" if actual == expected else "prerequisite gate evidence is incomplete or unordered", actual=actual))
    failed = [item.get("gate_id") for item in prior if item.get("status") != "pass"]
    checks.append(_check("prior-gate-status", "pass" if not failed else "fail", "all eight prerequisite gates passed" if not failed else "one or more prerequisite gates did not pass", gates=failed))
    try:
        previous = "0" * 64
        for item in prior:
            from .coe_contract import validate_gate_evidence

            validate_gate_evidence(item, expected_previous_hash=previous)
            previous = item["evidence_hash"]
        chain_ok = actual == expected
        detail = "prerequisite evidence hash chain verified" if chain_ok else "prerequisite chain is incomplete"
    except Exception as exc:
        chain_ok = False
        detail = f"prerequisite evidence chain failed: {exc}"
    checks.append(_check("evidence-chain", "pass" if chain_ok else "fail", detail))
    try:
        verified = verify_release(Path(context["release_root"]), expected_identity=context["identity"], expected_commit=context["release"]["git_commit"])
        exact = verified["artifact_sha256"] == context["release"]["artifact_sha256"]
    except Exception as exc:
        verified = {"error": str(exc)}
        exact = False
    checks.append(_check("artifact-provenance", "pass" if exact else "fail", "the exact staged artifact matches release scope" if exact else "artifact provenance mismatch", result=verified))
    passoff = context.get("documentation_passoff", [])
    docs_ok = {item.get("surface") for item in passoff if item.get("status") == "verified"} >= {"github", "wiki", "google-drive"}
    checks.append(_check("documentation-provenance", "pass" if docs_ok else "fail", "documentation pass-off is verified" if docs_ok else "documentation pass-off is not verified"))
    return checks, [], canonical_json({"prior_evidence_hashes": [item.get("evidence_hash") for item in prior]}).encode(), b""


GATES: dict[str, Callable[[dict[str, Any]], tuple[list[Check], list[dict[str, str]], bytes, bytes]]] = {
    "deterministic-tests": _deterministic,
    "application-release-verifier": _application_verifier,
    "doctor": _doctor,
    "engineering-audit": _engineering,
    "security-reliability-audit": _security,
    "documentation-audit": _documentation,
    "bloat-audit": _bloat,
    "opportunity-audit": _opportunity,
    "release-integrity": _release_integrity,
}


def execute_gate(gate_id: str, context: dict[str, Any], output_path: Path) -> dict[str, Any]:
    if gate_id not in GATES:
        raise ValueError(f"unknown gate: {gate_id}")
    started_at = utc_now()
    started = time.monotonic()
    checks: list[Check]
    artifacts: list[dict[str, str]]
    stdout: bytes
    stderr: bytes
    try:
        checks, artifacts, stdout, stderr = GATES[gate_id](context)
        statuses = {item["status"] for item in checks}
        status = "pass" if statuses == {"pass"} else "fail"
    except Exception as exc:
        checks = [_check("gate-execution", "error", f"gate raised a controlled error: {exc}")]
        artifacts = []
        stdout = b""
        stderr = str(exc).encode("utf-8")
        status = "error"
    completed_at = utc_now()
    arguments = ["-m", "lpos_engine.coe_gate", "--gate", gate_id, "--context", str(context.get("context_path", "[provided]")), "--output", str(output_path)]
    record: dict[str, Any] = {
        "schema_version": 1,
        "evidence_id": sortable_id("evidence"),
        "audit_id": context["audit_id"],
        "gate_id": gate_id,
        "gate_version": "1.0.0",
        "status": status,
        "started_at": started_at,
        "completed_at": completed_at,
        "duration_ms": round((time.monotonic() - started) * 1000),
        "executable": sys.executable,
        "arguments": arguments,
        "exit_code": 0 if status == "pass" else 1,
        "signal": None,
        "release": context["release"],
        "git_commit": context["release"]["git_commit"],
        "input_hashes": dict(context.get("input_hashes", {})),
        "checks": checks,
        "stdout_sha256": sha256_bytes(stdout),
        "stderr_sha256": sha256_bytes(stderr),
        "stdout_excerpt": redact(stdout.decode("utf-8", "replace")[-8192:]),
        "stderr_excerpt": redact(stderr.decode("utf-8", "replace")[-8192:]),
        "artifacts": artifacts,
        "previous_evidence_hash": context["previous_evidence_hash"],
        "source": "command",
    }
    record["evidence_hash"] = evidence_hash(record, record["previous_evidence_hash"])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return record


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run one independent LPOS COE gate")
    parser.add_argument("--gate", required=True, choices=GATE_IDS)
    parser.add_argument("--context", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        context = json.loads(args.context.read_text(encoding="utf-8"))
        if not isinstance(context, dict):
            raise ValueError("gate context must be an object")
        context["context_path"] = str(args.context)
        record = execute_gate(args.gate, context, args.output)
    except Exception as exc:
        print(redact(str(exc)), file=sys.stderr)
        return 2
    print(json.dumps({"gate_id": args.gate, "status": record["status"], "evidence_id": record["evidence_id"]}, sort_keys=True))
    return 0 if record["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
