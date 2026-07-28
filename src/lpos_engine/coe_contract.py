"""Strict COE identity, evidence, hashing, and redaction contracts."""

from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import subprocess
import time
import tomllib
from datetime import datetime, timezone
from importlib.resources import files as resource_files
from pathlib import Path
from typing import Any, Mapping, Sequence

GATE_IDS = (
    "deterministic-tests",
    "application-release-verifier",
    "doctor",
    "engineering-audit",
    "security-reliability-audit",
    "documentation-audit",
    "bloat-audit",
    "opportunity-audit",
    "release-integrity",
)
ZERO_HASH = "0" * 64
HEX_40 = re.compile(r"^[0-9a-f]{40}$")
HEX_64 = re.compile(r"^[0-9a-f]{64}$")
VERSION = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
SECRET_PATTERNS = (
    re.compile(r"(?i)(authorization\s*[:=]\s*)(?:bearer\s+)?[^\s,;]+"),
    re.compile(r"(?i)((?:api[_-]?key|token|password|client[_-]?secret|cookie)\s*[:=]\s*)[^\s,;]+"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.DOTALL),
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def sortable_id(prefix: str) -> str:
    """Return a lexically sortable, collision-resistant identifier."""

    millis = int(time.time() * 1000)
    return f"{prefix}-{millis:013d}-{secrets.token_hex(8)}"


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def redact(value: str, extra_patterns: tuple[re.Pattern[str], ...] = ()) -> str:
    redacted = value
    for pattern in SECRET_PATTERNS + extra_patterns:
        redacted = pattern.sub(lambda match: (match.group(1) if match.lastindex else "") + "[REDACTED]", redacted)
    redacted = re.sub(r"/Users/[^/\s]+", "[REDACTED_HOME]", redacted)
    return redacted


def _read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def git_commit(repo: Path) -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True, check=False, timeout=30
    )
    value = completed.stdout.strip()
    if completed.returncode != 0 or not HEX_40.fullmatch(value):
        raise ValueError("current Git commit is unavailable or invalid")
    return value


def git_is_clean(repo: Path) -> bool:
    completed = subprocess.run(
        ["git", "status", "--porcelain=v2", "--untracked-files=all"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    return completed.returncode == 0 and not completed.stdout.strip()


def read_release_identity(repo: Path, *, require_clean: bool = False) -> dict[str, str]:
    """Read the authoritative identity and reject drift in required mirrors."""

    repo = Path(repo).resolve()
    authoritative = _read_json(repo / "release" / "release.json")
    required = {"schema_version", "product", "release_version", "release_channel", "lpos_version"}
    if set(authoritative) != required or authoritative.get("schema_version") != 1:
        raise ValueError("release/release.json has an invalid field set")
    for field in ("release_version", "lpos_version"):
        if not VERSION.fullmatch(str(authoritative[field])):
            raise ValueError(f"invalid {field}")
    if authoritative["release_version"] != authoritative["lpos_version"]:
        raise ValueError("release_version and lpos_version differ")

    if (repo / "pyproject.toml").is_file():
        root_release = _read_json(repo / "RELEASE.json")
        pyproject = tomllib.loads((repo / "pyproject.toml").read_text(encoding="utf-8"))
        init_text = (repo / "src" / "lpos_engine" / "__init__.py").read_text(encoding="utf-8")
        match = re.search(r'^__version__\s*=\s*["\']([^"\']+)["\']', init_text, re.MULTILINE)
        mirrors = {
            "RELEASE.json": str(root_release.get("version")),
            "pyproject.toml": str(pyproject.get("project", {}).get("version")),
            "lpos_engine.__version__": match.group(1) if match else "missing",
        }
    elif (repo / "package.json").is_file():
        package = _read_json(repo / "package.json")
        mirrors = {"package.json": str(package.get("version"))}
    else:
        raise ValueError("no supported release identity mirrors were found")
    expected = str(authoritative["release_version"])
    drift = {name: value for name, value in mirrors.items() if value != expected}
    if drift:
        raise ValueError(f"release identity drift: {canonical_json(drift)}")
    if require_clean and not git_is_clean(repo):
        raise ValueError("source tree is not clean")
    return {
        "product": str(authoritative["product"]),
        "release_version": expected,
        "release_channel": str(authoritative["release_channel"]),
        "lpos_version": str(authoritative["lpos_version"]),
        "git_commit": git_commit(repo),
    }


def release_scope(identity: Mapping[str, str], *, build_id: str, artifact_sha256: str) -> dict[str, str]:
    if not HEX_40.fullmatch(str(identity.get("git_commit", ""))):
        raise ValueError("release scope requires a full Git commit")
    if not HEX_64.fullmatch(artifact_sha256):
        raise ValueError("release scope requires a SHA-256 artifact identity")
    return {
        "product": str(identity["product"]),
        "release_version": str(identity["release_version"]),
        "release_channel": str(identity["release_channel"]),
        "git_commit": str(identity["git_commit"]),
        "build_id": build_id,
        "artifact_sha256": artifact_sha256,
    }


def evidence_hash(record_without_hash: Mapping[str, Any], previous_hash: str) -> str:
    if not HEX_64.fullmatch(previous_hash):
        raise ValueError("previous evidence hash is invalid")
    return sha256_bytes((canonical_json(dict(record_without_hash)) + previous_hash).encode("utf-8"))


def validate_gate_evidence(record: Mapping[str, Any], *, expected_previous_hash: str | None = None) -> None:
    required = {
        "schema_version", "evidence_id", "audit_id", "gate_id", "gate_version", "status",
        "started_at", "completed_at", "duration_ms", "executable", "arguments", "exit_code", "signal",
        "release", "git_commit", "input_hashes", "checks", "stdout_sha256", "stderr_sha256",
        "stdout_excerpt", "stderr_excerpt", "artifacts", "previous_evidence_hash", "evidence_hash", "source",
    }
    if set(record) != required:
        raise ValueError(f"gate evidence field mismatch: {sorted(set(record) ^ required)}")
    if record["schema_version"] != 1 or record["gate_id"] not in GATE_IDS:
        raise ValueError("gate evidence identity is invalid")
    if record["status"] not in {"pass", "fail", "error", "skipped"} or record["source"] != "command":
        raise ValueError("gate evidence status or source is invalid")
    if isinstance(record["duration_ms"], bool) or not isinstance(record["duration_ms"], int) or record["duration_ms"] < 0:
        raise ValueError("gate duration is invalid")
    if not isinstance(record["arguments"], list) or not all(isinstance(item, str) for item in record["arguments"]):
        raise ValueError("gate arguments are invalid")
    if not isinstance(record["checks"], list) or not record["checks"]:
        raise ValueError("gate checks are missing")
    for check in record["checks"]:
        if not isinstance(check, dict) or check.get("status") not in {"pass", "fail", "error", "unknown"}:
            raise ValueError("gate check is invalid")
    if not HEX_40.fullmatch(str(record["git_commit"])):
        raise ValueError("gate Git commit is invalid")
    for field in ("stdout_sha256", "stderr_sha256", "previous_evidence_hash", "evidence_hash"):
        if not HEX_64.fullmatch(str(record[field])):
            raise ValueError(f"gate {field} is invalid")
    if expected_previous_hash is not None and record["previous_evidence_hash"] != expected_previous_hash:
        raise ValueError("gate evidence chain predecessor mismatch")
    material = dict(record)
    claimed = str(material.pop("evidence_hash"))
    if evidence_hash(material, str(record["previous_evidence_hash"])) != claimed:
        raise ValueError("gate evidence hash mismatch")
    scope = record["release"]
    if not isinstance(scope, dict) or scope.get("git_commit") != record["git_commit"]:
        raise ValueError("gate release scope does not match Git commit")
    if not HEX_64.fullmatch(str(scope.get("artifact_sha256", ""))):
        raise ValueError("gate release scope artifact is invalid")
    try:
        schema = json.loads(resource_files("lpos_engine.schemas").joinpath("coe-gate-evidence.schema.json").read_text())
        import jsonschema  # type: ignore

        jsonschema.validate(dict(record), schema, format_checker=jsonschema.FormatChecker())
    except ImportError:
        pass


def verify_evidence_chain(records: Sequence[Mapping[str, Any]]) -> None:
    previous = ZERO_HASH
    seen: set[str] = set()
    for expected_gate, record in zip(GATE_IDS, records, strict=False):
        if record.get("gate_id") != expected_gate:
            raise ValueError(f"gate order mismatch: expected {expected_gate}")
        evidence_id = str(record.get("evidence_id"))
        if evidence_id in seen:
            raise ValueError("duplicate evidence ID")
        validate_gate_evidence(record, expected_previous_hash=previous)
        previous = str(record["evidence_hash"])
        seen.add(evidence_id)
    if len(records) != len(GATE_IDS):
        raise ValueError("evidence chain is incomplete")


def load_json_resource(package: str, name: str) -> dict[str, Any]:
    data = json.loads(resource_files(package).joinpath(name).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{name} is not a JSON object")
    return data
