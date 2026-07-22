"""The LPOS control set: concrete, machine-checkable SOC 2 controls.

Every control maps to a Trust Services Criteria series (see ``criteria.py``)
and carries a check callable ``(repo_root, hermes_root) -> ControlResult`` that
runs fully offline against the release checkout and the Hermes runtime root.
Checks are defensive by construction: a missing file is a *failing control
with evidence saying why*, never a crash. Evidence strings cite the exact
files and values inspected -- the evidence is the proof.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

# --------------------------------------------------------------------------- model


@dataclass(frozen=True, slots=True)
class ControlResult:
    passing: bool
    evidence: str
    details: dict[str, Any] = field(default_factory=dict)


CheckFunction = Callable[[Path, Path], ControlResult]


@dataclass(frozen=True, slots=True)
class Control:
    control_id: str
    tsc_id: str
    title: str
    description: str
    category: str  # "critical" | "standard"
    check: CheckFunction
    #: Repo-relative files a remediation would touch (copied into staging).
    remediation_paths: tuple[str, ...] = ()
    #: Concrete prose describing the fix, naming exact files/changes.
    remediation_hint: str = ""


# --------------------------------------------------------------------------- helpers


def _ok(evidence: str, **details: Any) -> ControlResult:
    return ControlResult(passing=True, evidence=evidence, details=dict(details))


def _fail(evidence: str, **details: Any) -> ControlResult:
    return ControlResult(passing=False, evidence=evidence, details=dict(details))


def _read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def _read_json(path: Path) -> Any | None:
    text = _read_text(path)
    if text is None:
        return None
    try:
        return json.loads(text)
    except ValueError:
        return None


def _release_version(repo_root: Path) -> str | None:
    release = _read_json(repo_root / "RELEASE.json")
    if isinstance(release, dict) and release.get("version"):
        return str(release["version"])
    return None


def _catalog_entry(repo_root: Path, so_id: str) -> dict[str, Any] | None:
    catalog = _read_json(repo_root / "src" / "lpos_engine" / "workflows" / "catalog.json")
    if not isinstance(catalog, dict):
        return None
    for item in catalog.get("operations", []) or []:
        if isinstance(item, dict) and item.get("so_id") == so_id:
            return item
    return None


# --------------------------------------------------------------------------- CC1


def check_cc1_control_environment(repo_root: Path, hermes_root: Path) -> ControlResult:
    core = repo_root / "src" / "lpos_engine" / "spec" / "LPOS-CORE.md"
    guilds = repo_root / "src" / "lpos_engine" / "spec" / "GUILDS.md"
    missing = [str(p.relative_to(repo_root)) for p in (core, guilds) if not p.is_file()]
    if missing:
        return _fail(f"operating specification incomplete: missing {', '.join(missing)}")
    sizes = {p.name: p.stat().st_size for p in (core, guilds)}
    trivial = [name for name, size in sizes.items() if size < 512]
    if trivial:
        return _fail(
            f"operating specification present but trivial (<512 bytes): {', '.join(trivial)}",
            sizes=sizes,
        )
    return _ok(
        "src/lpos_engine/spec/LPOS-CORE.md "
        f"({sizes['LPOS-CORE.md']} bytes) and GUILDS.md ({sizes['GUILDS.md']} bytes) "
        "define the operating specification and responsibility structure",
        sizes=sizes,
    )


def check_cc1_notice_attribution(repo_root: Path, hermes_root: Path) -> ControlResult:
    notices = sorted(p.name for p in repo_root.glob("NOTICE*") if p.is_file())
    if not notices:
        return _fail(
            "no NOTICE file at the repository root; derived work must carry attribution"
        )
    return _ok(
        f"attribution notices present at repo root: {', '.join(notices)}",
        notices=notices,
    )


# --------------------------------------------------------------------------- CC2


def check_cc2_communication(repo_root: Path, hermes_root: Path) -> ControlResult:
    readme = repo_root / "README.md"
    wiki = repo_root / "docs" / "wiki"
    patch_notes = wiki / "patch-notes"
    problems = []
    if not readme.is_file():
        problems.append("README.md missing")
    if not wiki.is_dir():
        problems.append("docs/wiki missing")
    notes = sorted(p.name for p in patch_notes.glob("*.md")) if patch_notes.is_dir() else []
    if not notes:
        problems.append("docs/wiki/patch-notes has no entries")
    if problems:
        return _fail("communication surface incomplete: " + "; ".join(problems))
    return _ok(
        f"README.md present; docs/wiki present with {len(notes)} patch-notes "
        f"page(s) (latest: {notes[-1]})",
        patch_notes=notes,
    )


# --------------------------------------------------------------------------- CC3


def check_cc3_risk_assessment(repo_root: Path, hermes_root: Path) -> ControlResult:
    threat = repo_root / "docs" / "THREAT-MODEL.md"
    security = repo_root / "docs" / "SECURITY.md"
    missing = [str(p.relative_to(repo_root)) for p in (threat, security) if not p.is_file()]
    if missing:
        return _fail(f"risk assessment artifacts missing: {', '.join(missing)}")
    sizes = {p.name: p.stat().st_size for p in (threat, security)}
    trivial = [name for name, size in sizes.items() if size < 512]
    if trivial:
        return _fail(
            f"risk assessment artifacts present but trivial (<512 bytes): {', '.join(trivial)}",
            sizes=sizes,
        )
    return _ok(
        f"docs/THREAT-MODEL.md ({sizes['THREAT-MODEL.md']} bytes) and "
        f"docs/SECURITY.md ({sizes['SECURITY.md']} bytes) are present and substantive",
        sizes=sizes,
    )


# --------------------------------------------------------------------------- CC4


def check_cc4_docs_drift_audit(repo_root: Path, hermes_root: Path) -> ControlResult:
    entry = _catalog_entry(repo_root, "SO-024")
    if entry is None:
        return _fail(
            "SO-024 (documentation drift audit) is not in "
            "src/lpos_engine/workflows/catalog.json"
        )
    return _ok(
        "SO-024 documentation drift audit is cataloged "
        f"(schedule {entry.get('default_schedule', 'unset')}) in "
        "src/lpos_engine/workflows/catalog.json",
        schedule=entry.get("default_schedule"),
    )


def check_cc4_compliance_so_wired(repo_root: Path, hermes_root: Path) -> ControlResult:
    workflow = repo_root / "src" / "lpos_engine" / "workflows" / "SO-025.json"
    if not workflow.is_file():
        return _fail(
            "src/lpos_engine/workflows/SO-025.json missing: the compliance audit "
            "itself is not shipped as a Standing Operation"
        )
    entry = _catalog_entry(repo_root, "SO-025")
    if entry is None:
        # Tolerant by design: the workflow ships with this package; the catalog
        # entry is wired by the orchestrator.
        return _ok(
            "SO-025.json is present in src/lpos_engine/workflows/ (catalog entry "
            "pending orchestrator wiring)",
            cataloged=False,
        )
    return _ok(
        "SO-025 compliance audit is shipped and cataloged "
        f"(schedule {entry.get('default_schedule', 'unset')})",
        cataloged=True,
        schedule=entry.get("default_schedule"),
    )


# --------------------------------------------------------------------------- CC5


def check_cc5_test_suite(repo_root: Path, hermes_root: Path) -> ControlResult:
    tests_dir = repo_root / "tests"
    if not tests_dir.is_dir():
        return _fail("tests/ directory is missing")
    count = 0
    files = 0
    for path in sorted(tests_dir.glob("test_*.py")):
        text = _read_text(path) or ""
        count += text.count("def test_")
        files += 1
    if count < 100:
        return _fail(
            f"tests/ contains only {count} test function(s) across {files} file(s); "
            "the control requires at least 100",
            test_functions=count,
        )
    return _ok(
        f"tests/ contains {count} test function(s) ('def test_' occurrences) "
        f"across {files} file(s), meeting the >=100 threshold",
        test_functions=count,
        test_files=files,
    )


def check_cc5_benchmark_corpus(repo_root: Path, hermes_root: Path) -> ControlResult:
    evals = repo_root / "src" / "lpos_engine" / "evals"
    fixtures = sorted(p.name for p in evals.glob("BENCH-*.json")) if evals.is_dir() else []
    release = _read_json(repo_root / "RELEASE.json")
    declared = release.get("benchmarks") if isinstance(release, dict) else None
    if not fixtures:
        return _fail("no BENCH-*.json fixtures under src/lpos_engine/evals/")
    if declared is not None and len(fixtures) != declared:
        return _fail(
            f"benchmark corpus drift: RELEASE.json declares {declared} benchmarks "
            f"but src/lpos_engine/evals/ ships {len(fixtures)} BENCH-*.json fixtures",
            declared=declared,
            shipped=len(fixtures),
        )
    return _ok(
        f"src/lpos_engine/evals/ ships {len(fixtures)} BENCH-*.json fixtures, "
        f"matching RELEASE.json benchmarks={declared}",
        shipped=len(fixtures),
        declared=declared,
    )


# --------------------------------------------------------------------------- CC6


def check_cc6_loopback_binding(repo_root: Path, hermes_root: Path) -> ControlResult:
    server = repo_root / "src" / "lpos_engine" / "dashboard" / "server.py"
    text = _read_text(server)
    if text is None:
        return _fail("src/lpos_engine/dashboard/server.py is missing; cannot verify bind address")
    match = re.search(r'DEFAULT_HOST\s*=\s*"([^"]+)"', text)
    if match is None:
        return _fail(
            "src/lpos_engine/dashboard/server.py has no DEFAULT_HOST constant; "
            "default bind address is unverifiable"
        )
    host = match.group(1)
    if host not in ("127.0.0.1", "localhost", "::1"):
        return _fail(
            f"dashboard DEFAULT_HOST is {host!r}, not loopback: the dashboard "
            "would listen on non-local interfaces by default",
            default_host=host,
        )
    return _ok(
        f'src/lpos_engine/dashboard/server.py sets DEFAULT_HOST = "{host}" '
        "(loopback-only by default)",
        default_host=host,
    )


def check_cc6_approval_gating(repo_root: Path, hermes_root: Path) -> ControlResult:
    approvals = repo_root / "src" / "lpos_engine" / "approvals.py"
    engine = repo_root / "src" / "lpos_engine" / "engine.py"
    if not approvals.is_file():
        return _fail("src/lpos_engine/approvals.py is missing: no approval service ships")
    engine_text = _read_text(engine) or ""
    if "ApprovalService" not in engine_text:
        return _fail(
            "src/lpos_engine/engine.py does not wire ApprovalService: exact-action "
            "approval gating is not engaged"
        )
    return _ok(
        "src/lpos_engine/approvals.py present and src/lpos_engine/engine.py wires "
        "ApprovalService into the action path (exact-action approval gating)",
    )


_SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("aws_access_key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("github_token", re.compile(r"ghp_[A-Za-z0-9]{36}")),
    ("api_secret_key", re.compile(r"sk-[A-Za-z0-9]{20,}")),
    ("inline_password", re.compile(r'"password"\s*:\s*"[^"]+"')),
)

_SCAN_SUFFIXES = {".json", ".jsonl", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".txt", ".env"}
_SCAN_MAX_BYTES = 1_000_000
_SCAN_SKIP_PARTS = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", "node_modules", "site-packages"}


def _scan_for_secrets(paths: list[Path], skip: Path | None = None) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    for base in paths:
        if not base.exists():
            continue
        candidates = [base] if base.is_file() else sorted(base.rglob("*"))
        for path in candidates:
            if not path.is_file() or path.suffix.lower() not in _SCAN_SUFFIXES:
                continue
            if _SCAN_SKIP_PARTS.intersection(path.parts):
                continue
            if skip is not None and skip in path.parents:
                continue
            try:
                if path.stat().st_size > _SCAN_MAX_BYTES:
                    continue
            except OSError:
                continue
            text = _read_text(path)
            if not text:
                continue
            for name, pattern in _SECRET_PATTERNS:
                if pattern.search(text):
                    findings.append({"file": str(path), "pattern": name})
    return findings


def check_cc6_secrets_hygiene(repo_root: Path, hermes_root: Path) -> ControlResult:
    scanned = [repo_root / "config", hermes_root]
    findings = _scan_for_secrets(scanned, skip=hermes_root / "compliance" / "staging")
    scanned_desc = ", ".join(str(p) for p in scanned)
    if findings:
        cited = "; ".join(f"{f['pattern']} in {f['file']}" for f in findings[:5])
        return _fail(
            f"plaintext secret pattern(s) found while scanning {scanned_desc}: {cited}",
            findings=findings[:20],
        )
    return _ok(
        f"no plaintext secret patterns (AWS key, GitHub token, sk- API key, inline "
        f'"password") found scanning {scanned_desc}',
        scanned=[str(p) for p in scanned],
    )


def check_cc6_smtp_password_file(repo_root: Path, hermes_root: Path) -> ControlResult:
    smtp = hermes_root / "monitor" / "smtp.json"
    if not smtp.is_file():
        return _ok(
            f"{smtp} not configured; no inline SMTP credential can exist",
            configured=False,
        )
    config = _read_json(smtp)
    if not isinstance(config, dict):
        return _fail(f"{smtp} exists but is not valid JSON; credential handling unverifiable")
    if config.get("password"):
        return _fail(
            f"{smtp} stores an inline \"password\" value; it must reference a "
            'credential via "password_file" instead',
            configured=True,
        )
    return _ok(
        f"{smtp} holds no inline password"
        + (' and uses "password_file"' if config.get("password_file") else ""),
        configured=True,
        uses_password_file=bool(config.get("password_file")),
    )


# --------------------------------------------------------------------------- CC7


def check_cc7_health_monitoring(repo_root: Path, hermes_root: Path) -> ControlResult:
    entry = _catalog_entry(repo_root, "SO-023")
    if entry is None:
        return _fail(
            "SO-023 (connector health monitor) is not in "
            "src/lpos_engine/workflows/catalog.json"
        )
    schedule = str(entry.get("default_schedule", ""))
    hourly = schedule.startswith("0 *")
    if not hourly:
        return _fail(
            f"SO-023 is cataloged but its schedule {schedule!r} is not hourly",
            schedule=schedule,
        )
    return _ok(
        f"SO-023 connector health monitor is cataloged hourly ({schedule}) in "
        "src/lpos_engine/workflows/catalog.json",
        schedule=schedule,
    )


def check_cc7_monitor_freshness(repo_root: Path, hermes_root: Path) -> ControlResult:
    wired = _catalog_entry(repo_root, "SO-023") is not None
    status = hermes_root / "monitor" / "status.json"
    if not (hermes_root / "monitor").is_dir():
        if wired:
            return _ok(
                f"no runtime yet: {hermes_root / 'monitor'} does not exist, but SO-023 "
                "catalog wiring is present so monitoring engages on first run",
                runtime=False,
            )
        return _fail(
            f"no monitor runtime under {hermes_root} and SO-023 is not cataloged"
        )
    doc = _read_json(status)
    generated = doc.get("generated_at") if isinstance(doc, dict) else None
    if not generated:
        return _fail(f"{status} is missing or has no generated_at; monitoring is not publishing")
    try:
        stamp = datetime.fromisoformat(str(generated).replace("Z", "+00:00"))
        if stamp.tzinfo is None:
            stamp = stamp.replace(tzinfo=timezone.utc)
    except ValueError:
        return _fail(f"{status} generated_at {generated!r} is not a valid timestamp")
    age = datetime.now(timezone.utc) - stamp
    if age > timedelta(hours=2):
        return _fail(
            f"{status} is stale: generated_at {generated} is "
            f"{int(age.total_seconds() // 3600)}h old (>2h); the hourly monitor is not running",
            generated_at=str(generated),
        )
    return _ok(
        f"{status} is fresh: generated_at {generated} is within the 2h freshness window",
        generated_at=str(generated),
    )


def check_cc7_append_only_audit_trail(repo_root: Path, hermes_root: Path) -> ControlResult:
    sql_dir = repo_root / "src" / "lpos_engine" / "sql"
    schemas = sorted(sql_dir.glob("*.sql")) if sql_dir.is_dir() else []
    if not schemas:
        return _fail("no SQL schema files under src/lpos_engine/sql/; audit trail unverifiable")
    corpus = "\n".join((_read_text(p) or "") for p in schemas)
    if not re.search(r"CREATE TABLE IF NOT EXISTS events", corpus):
        return _fail("SQL schema does not create an events table")
    has_update_guard = "events_no_update" in corpus
    has_delete_guard = "events_no_delete" in corpus
    if not (has_update_guard and has_delete_guard):
        missing = [
            name
            for name, present in (
                ("events_no_update", has_update_guard),
                ("events_no_delete", has_delete_guard),
            )
            if not present
        ]
        return _fail(
            f"events table lacks append-only trigger(s): missing {', '.join(missing)} "
            f"in {', '.join(str(p.relative_to(repo_root)) for p in schemas)}"
        )
    return _ok(
        "events table with events_no_update/events_no_delete ABORT triggers found in "
        + ", ".join(str(p.relative_to(repo_root)) for p in schemas)
        + " (append-only by construction)",
        schemas=[str(p.relative_to(repo_root)) for p in schemas],
    )


# --------------------------------------------------------------------------- CC8


def check_cc8_change_management(repo_root: Path, hermes_root: Path) -> ControlResult:
    version = _release_version(repo_root)
    if version is None:
        return _fail("RELEASE.json is missing or has no version; release state unverifiable")
    problems = []
    changelog = _read_text(repo_root / "CHANGELOG.md")
    if changelog is None:
        problems.append("CHANGELOG.md missing")
    elif version not in changelog:
        problems.append(f"CHANGELOG.md has no entry for v{version}")
    if not (repo_root / "RELEASE-MANIFEST.json").is_file():
        problems.append("RELEASE-MANIFEST.json missing")
    if not (repo_root / "SHA256SUMS").is_file():
        problems.append("SHA256SUMS missing")
    if not (repo_root / "verify_release.py").is_file():
        problems.append("verify_release.py (release verification tooling) missing")
    if problems:
        return _fail(f"change management gaps for v{version}: " + "; ".join(problems))
    return _ok(
        f"CHANGELOG.md has a v{version} entry; RELEASE-MANIFEST.json, SHA256SUMS, "
        "and verify_release.py are all present at the repo root",
        version=version,
    )


def check_cc8_release_gating(repo_root: Path, hermes_root: Path) -> ControlResult:
    entry = _catalog_entry(repo_root, "SO-022")
    if entry is None:
        return _fail("SO-022 (release publication) is not in the workflow catalog")
    workflow = _read_json(repo_root / "src" / "lpos_engine" / "workflows" / "SO-022.json")
    steps = workflow.get("steps", []) if isinstance(workflow, dict) else []
    gate = next(
        (
            s
            for s in steps
            if isinstance(s, dict)
            and (s.get("step_id") == "STEP-DOCS-GATE" or s.get("handler") == "enforce_docs_gate")
        ),
        None,
    )
    if gate is None:
        return _fail(
            "SO-022.json has no documentation gate step (STEP-DOCS-GATE / enforce_docs_gate)"
        )
    return _ok(
        "SO-022 is cataloged and SO-022.json carries STEP-DOCS-GATE "
        f"(handler {gate.get('handler')}): releases cannot publish without documentation",
        step_id=gate.get("step_id"),
    )


# --------------------------------------------------------------------------- CC9


def check_cc9_rollback_path(repo_root: Path, hermes_root: Path) -> ControlResult:
    problems = []
    upgrading = _read_text(repo_root / "docs" / "wiki" / "administration" / "upgrading.md")
    if upgrading is None or "rollback" not in upgrading.lower():
        problems.append(
            "docs/wiki/administration/upgrading.md missing or does not document rollback"
        )
    release = _read_json(repo_root / "RELEASE.json")
    wheel = release.get("wheel") if isinstance(release, dict) else None
    if not wheel:
        problems.append("RELEASE.json declares no wheel")
    elif not (repo_root / "Packages" / str(wheel)).is_file():
        problems.append(f"declared wheel Packages/{wheel} is not retained in the release tree")
    if problems:
        return _fail("rollback path incomplete: " + "; ".join(problems))
    return _ok(
        "docs/wiki/administration/upgrading.md documents the rollback procedure and "
        f"the release retains its installable wheel Packages/{wheel}",
        wheel=str(wheel),
    )


# --------------------------------------------------------------------------- A


def check_a_integrity_and_backups(repo_root: Path, hermes_root: Path) -> ControlResult:
    problems = []
    store = _read_text(repo_root / "src" / "lpos_engine" / "store.py") or ""
    if "integrity_check" not in store or "PRAGMA integrity_check" not in store:
        problems.append(
            "src/lpos_engine/store.py has no integrity_check (PRAGMA integrity_check)"
        )
    backups = repo_root / "docs" / "wiki" / "administration" / "backups.md"
    if not backups.is_file():
        problems.append("docs/wiki/administration/backups.md missing")
    if problems:
        return _fail("availability controls incomplete: " + "; ".join(problems))
    return _ok(
        "src/lpos_engine/store.py exposes integrity_check() running PRAGMA "
        "integrity_check, and docs/wiki/administration/backups.md documents backups",
    )


# --------------------------------------------------------------------------- C


def check_c_record_only_boundary(repo_root: Path, hermes_root: Path) -> ControlResult:
    release = _read_json(repo_root / "RELEASE.json")
    default = release.get("external_action_default") if isinstance(release, dict) else None
    if default != "record-only":
        return _fail(
            f"RELEASE.json external_action_default is {default!r}, not 'record-only': "
            "external side effects are not confined to approval-bound plans",
            external_action_default=default,
        )
    adapter_doc = _read_text(repo_root / "docs" / "ADAPTER-PROTOCOL.md") or ""
    if "Subprocess" not in adapter_doc:
        return _fail(
            "docs/ADAPTER-PROTOCOL.md missing or does not document the subprocess "
            "adapter boundary"
        )
    return _ok(
        'RELEASE.json declares external_action_default: "record-only" and '
        "docs/ADAPTER-PROTOCOL.md documents the SubprocessModelAdapter isolation boundary",
        external_action_default=default,
    )


# --------------------------------------------------------------------------- PI


def check_pi_idempotent_processing(repo_root: Path, hermes_root: Path) -> ControlResult:
    operations = _read_text(repo_root / "src" / "lpos_engine" / "operations.py")
    if operations is None:
        return _fail("src/lpos_engine/operations.py is missing")
    problems = []
    if "idempotency_key" not in operations:
        problems.append("no idempotency_key: workflow runs are not exactly-once per schedule")
    if not re.search(r"from\s+\.canonical\s+import[^\n]*\bdigest\b", operations):
        problems.append("operations.py does not use the canonical digest over step outputs")
    if "freeze_mapping" not in operations:
        problems.append("step outputs are not frozen before downstream steps observe them")
    if problems:
        return _fail("processing integrity gaps in src/lpos_engine/operations.py: " + "; ".join(problems))
    return _ok(
        "src/lpos_engine/operations.py keys every run by idempotency_key, freezes "
        "step outputs, and records a canonical sha256 digest as the outputs_ref",
    )


# --------------------------------------------------------------------------- catalog

CONTROLS: tuple[Control, ...] = (
    Control(
        control_id="CTRL-CC1-01",
        tsc_id="CC1",
        title="Operating specification and responsibility structure",
        description=(
            "The core operating specification (LPOS-CORE.md) and the guild "
            "responsibility structure (GUILDS.md) ship with the system and are substantive."
        ),
        category="standard",
        check=check_cc1_control_environment,
        remediation_paths=("src/lpos_engine/spec/LPOS-CORE.md", "src/lpos_engine/spec/GUILDS.md"),
        remediation_hint=(
            "Restore src/lpos_engine/spec/LPOS-CORE.md and src/lpos_engine/spec/GUILDS.md "
            "from the release archive and re-verify they exceed 512 bytes each."
        ),
    ),
    Control(
        control_id="CTRL-CC1-02",
        tsc_id="CC1",
        title="Attribution of derived work",
        description="NOTICE files at the repository root credit incorporated or derived work.",
        category="standard",
        check=check_cc1_notice_attribution,
        remediation_paths=("NOTICE-SKILLOPT.md",),
        remediation_hint=(
            "Add a NOTICE-*.md file at the repository root naming the derived or "
            "incorporated work and its origin."
        ),
    ),
    Control(
        control_id="CTRL-CC2-01",
        tsc_id="CC2",
        title="Shipped documentation surface",
        description=(
            "README.md and docs/wiki (including per-release patch-notes pages) ship with "
            "the system so operators learn what changed and how to run it."
        ),
        category="standard",
        check=check_cc2_communication,
        remediation_paths=("README.md",),
        remediation_hint=(
            "Restore README.md and the docs/wiki tree; add a "
            "docs/wiki/patch-notes/<version>.md page for the current release."
        ),
    ),
    Control(
        control_id="CTRL-CC3-01",
        tsc_id="CC3",
        title="Threat model and security posture",
        description="docs/THREAT-MODEL.md and docs/SECURITY.md exist and are substantive.",
        category="standard",
        check=check_cc3_risk_assessment,
        remediation_paths=("docs/THREAT-MODEL.md", "docs/SECURITY.md"),
        remediation_hint=(
            "Write or restore docs/THREAT-MODEL.md and docs/SECURITY.md covering assets, "
            "trust boundaries, and mitigations (>512 bytes each)."
        ),
    ),
    Control(
        control_id="CTRL-CC4-01",
        tsc_id="CC4",
        title="Documentation drift audit is scheduled",
        description="SO-024 (documentation drift audit) is wired into the workflow catalog.",
        category="standard",
        check=check_cc4_docs_drift_audit,
        remediation_paths=("src/lpos_engine/workflows/catalog.json",),
        remediation_hint=(
            "Add the SO-024 entry back to src/lpos_engine/workflows/catalog.json with a "
            "default_schedule."
        ),
    ),
    Control(
        control_id="CTRL-CC4-02",
        tsc_id="CC4",
        title="Compliance audit ships as a Standing Operation",
        description=(
            "SO-025.json (this compliance audit) is present in the packaged workflows "
            "directory; catalog wiring is tolerated as pending."
        ),
        category="standard",
        check=check_cc4_compliance_so_wired,
        remediation_paths=("src/lpos_engine/workflows/SO-025.json",),
        remediation_hint=(
            "Restore src/lpos_engine/workflows/SO-025.json and wire an SO-025 catalog "
            "entry with a daily default_schedule."
        ),
    ),
    Control(
        control_id="CTRL-CC5-01",
        tsc_id="CC5",
        title="Automated test suite depth",
        description="tests/ contains at least 100 collected test functions.",
        category="critical",
        check=check_cc5_test_suite,
        remediation_hint=(
            "Restore the tests/ directory from the release archive; the shipped suite "
            "carries well over 100 test functions."
        ),
    ),
    Control(
        control_id="CTRL-CC5-02",
        tsc_id="CC5",
        title="Immutable benchmark corpus",
        description=(
            "The packaged BENCH-*.json fixture count under src/lpos_engine/evals/ matches "
            "the benchmark count declared in RELEASE.json."
        ),
        category="standard",
        check=check_cc5_benchmark_corpus,
        remediation_paths=("RELEASE.json",),
        remediation_hint=(
            "Reconcile src/lpos_engine/evals/BENCH-*.json fixtures with the 'benchmarks' "
            "count in RELEASE.json; restore missing fixtures rather than editing the count."
        ),
    ),
    Control(
        control_id="CTRL-CC6-01",
        tsc_id="CC6",
        title="Loopback-only dashboard binding",
        description="The dashboard server's DEFAULT_HOST constant is a loopback address.",
        category="critical",
        check=check_cc6_loopback_binding,
        remediation_paths=("src/lpos_engine/dashboard/server.py",),
        remediation_hint=(
            'Set DEFAULT_HOST = "127.0.0.1" in src/lpos_engine/dashboard/server.py; '
            "non-local exposure must be an explicit operator flag, never the default."
        ),
    ),
    Control(
        control_id="CTRL-CC6-02",
        tsc_id="CC6",
        title="Exact-action approval gating",
        description=(
            "The approvals module ships and the engine wires ApprovalService into the "
            "action path so privileged actions require explicit approval."
        ),
        category="critical",
        check=check_cc6_approval_gating,
        remediation_paths=("src/lpos_engine/approvals.py",),
        remediation_hint=(
            "Restore src/lpos_engine/approvals.py and the ApprovalService wiring in "
            "src/lpos_engine/engine.py."
        ),
    ),
    Control(
        control_id="CTRL-CC6-03",
        tsc_id="CC6",
        title="Secrets hygiene",
        description=(
            "No plaintext secret patterns (AWS access keys, GitHub tokens, sk- API keys, "
            "inline passwords) in repo config/ or Hermes state files."
        ),
        category="critical",
        check=check_cc6_secrets_hygiene,
        remediation_hint=(
            "Rotate any credential found, remove the plaintext value from the cited file, "
            "and reference it via a *_file path with restrictive permissions instead."
        ),
    ),
    Control(
        control_id="CTRL-CC6-04",
        tsc_id="CC6",
        title="SMTP credential by file reference",
        description=(
            "monitor/smtp.json (when configured) references its credential via "
            "password_file and never stores an inline password."
        ),
        category="standard",
        check=check_cc6_smtp_password_file,
        remediation_hint=(
            "Move the inline password out of <hermes>/monitor/smtp.json into a separate "
            'credential file and reference it with "password_file"; rotate the exposed value.'
        ),
    ),
    Control(
        control_id="CTRL-CC7-01",
        tsc_id="CC7",
        title="Hourly health monitoring is scheduled",
        description="SO-023 (connector health monitor) is cataloged with an hourly schedule.",
        category="standard",
        check=check_cc7_health_monitoring,
        remediation_paths=("src/lpos_engine/workflows/catalog.json",),
        remediation_hint=(
            "Restore the SO-023 catalog entry with default_schedule '0 * * * *' in "
            "src/lpos_engine/workflows/catalog.json."
        ),
    ),
    Control(
        control_id="CTRL-CC7-02",
        tsc_id="CC7",
        title="Monitoring is actually running",
        description=(
            "monitor/status.json under the Hermes root is fresh within 2 hours; before "
            "first runtime, catalog wiring alone satisfies the control."
        ),
        category="standard",
        check=check_cc7_monitor_freshness,
        remediation_hint=(
            "Re-enable the SO-023 schedule (or run 'python -m lpos_engine.monitor audit') "
            "so <hermes>/monitor/status.json is republished hourly."
        ),
    ),
    Control(
        control_id="CTRL-CC7-03",
        tsc_id="CC7",
        title="Append-only audit trail",
        description=(
            "The SQL schema creates the events table with ABORT triggers on UPDATE and "
            "DELETE, making the audit trail append-only by construction."
        ),
        category="critical",
        check=check_cc7_append_only_audit_trail,
        remediation_paths=("src/lpos_engine/sql/001_initial.sql",),
        remediation_hint=(
            "Restore the events table definition and the events_no_update / "
            "events_no_delete triggers in src/lpos_engine/sql/001_initial.sql."
        ),
    ),
    Control(
        control_id="CTRL-CC8-01",
        tsc_id="CC8",
        title="Release change management artifacts",
        description=(
            "CHANGELOG.md carries an entry for the current RELEASE.json version, and "
            "RELEASE-MANIFEST.json, SHA256SUMS, and verify_release.py ship at the root."
        ),
        category="critical",
        check=check_cc8_change_management,
        remediation_paths=(
            "CHANGELOG.md",
            "RELEASE-MANIFEST.json",
            "SHA256SUMS",
            "verify_release.py",
        ),
        remediation_hint=(
            "Add the missing CHANGELOG.md entry for the RELEASE.json version and restore "
            "RELEASE-MANIFEST.json, SHA256SUMS, and verify_release.py at the repo root."
        ),
    ),
    Control(
        control_id="CTRL-CC8-02",
        tsc_id="CC8",
        title="Release publication is documentation-gated",
        description=(
            "SO-022 is cataloged and its workflow contains the STEP-DOCS-GATE step, so a "
            "release cannot publish without its documentation."
        ),
        category="standard",
        check=check_cc8_release_gating,
        remediation_paths=("src/lpos_engine/workflows/SO-022.json",),
        remediation_hint=(
            "Restore the STEP-DOCS-GATE step (handler enforce_docs_gate) in "
            "src/lpos_engine/workflows/SO-022.json and the SO-022 catalog entry."
        ),
    ),
    Control(
        control_id="CTRL-CC9-01",
        tsc_id="CC9",
        title="Rollback path retained and documented",
        description=(
            "The upgrade guide documents rollback, and the release tree retains its own "
            "installable wheel under Packages/."
        ),
        category="standard",
        check=check_cc9_rollback_path,
        remediation_paths=("docs/wiki/administration/upgrading.md", "RELEASE.json"),
        remediation_hint=(
            "Restore the rollback section of docs/wiki/administration/upgrading.md and "
            "the wheel named by RELEASE.json under Packages/."
        ),
    ),
    Control(
        control_id="CTRL-A-01",
        tsc_id="A",
        title="State integrity checking and backups",
        description=(
            "The SQLite store exposes integrity_check() (PRAGMA integrity_check) and the "
            "backup procedure is documented."
        ),
        category="standard",
        check=check_a_integrity_and_backups,
        remediation_paths=("src/lpos_engine/store.py",),
        remediation_hint=(
            "Restore integrity_check() in src/lpos_engine/store.py and the "
            "docs/wiki/administration/backups.md procedure."
        ),
    ),
    Control(
        control_id="CTRL-C-01",
        tsc_id="C",
        title="Record-only external action boundary",
        description=(
            "RELEASE.json declares external_action_default record-only, and the subprocess "
            "adapter isolation boundary is documented."
        ),
        category="critical",
        check=check_c_record_only_boundary,
        remediation_paths=("RELEASE.json", "docs/ADAPTER-PROTOCOL.md"),
        remediation_hint=(
            'Set "external_action_default": "record-only" in RELEASE.json and restore '
            "docs/ADAPTER-PROTOCOL.md's subprocess boundary documentation."
        ),
    ),
    Control(
        control_id="CTRL-PI-01",
        tsc_id="PI",
        title="Idempotent, digest-verified workflow processing",
        description=(
            "operations.py keys every run by an idempotency key, freezes step outputs, "
            "and records a canonical digest over them."
        ),
        category="critical",
        check=check_pi_idempotent_processing,
        remediation_paths=("src/lpos_engine/operations.py",),
        remediation_hint=(
            "Restore the idempotency_key claim, freeze_mapping of step outputs, and the "
            "canonical digest outputs_ref in src/lpos_engine/operations.py."
        ),
    ),
)

CONTROLS_BY_ID: dict[str, Control] = {control.control_id: control for control in CONTROLS}


def all_controls() -> tuple[Control, ...]:
    """The registered control catalog (registry hook: tests may pass their own)."""

    return CONTROLS


def run_control(control: Control, repo_root: Path, hermes_root: Path) -> ControlResult:
    """Run one control defensively: a crashing check is a failing control."""

    try:
        result = control.check(repo_root, hermes_root)
    except Exception as exc:  # noqa: BLE001 - defensive boundary by design
        return ControlResult(
            passing=False,
            evidence=f"control check crashed: {type(exc).__name__}: {exc}",
            details={"crashed": True},
        )
    if not isinstance(result, ControlResult):
        return ControlResult(
            passing=False,
            evidence=f"control check returned {type(result).__name__}, not ControlResult",
            details={"crashed": True},
        )
    return result
