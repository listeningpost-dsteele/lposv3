"""Complete staged-release construction and fail-closed verification."""

from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

from .coe_contract import canonical_json, read_release_identity, sha256_bytes, sha256_file, utc_now

MANIFEST_NAME = "release-manifest.json"
TOOL_VERSION = "lpos-release-manifest/1.0.0"
FORBIDDEN_PARTS = {
    ".git", ".terraform", "node_modules", "__pycache__", ".pytest_cache", "state", "reports",
    "backups", "cache", ".venv", "dist", "build", "status", "runtime-state",
}
FORBIDDEN_SUFFIXES = {".db", ".db-wal", ".db-shm", ".log", ".jsonl", ".tmp", ".pyc"}
FORBIDDEN_NAMES = {".env", "credentials.json", "token.json", "auth.json", "cookies.json"}


def _safe_relative(value: str) -> PurePosixPath:
    if not value or "\\" in value:
        raise ValueError(f"unsafe release path: {value!r}")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or "." in path.parts:
        raise ValueError(f"unsafe release path: {value!r}")
    if value != path.as_posix():
        raise ValueError(f"noncanonical release path: {value!r}")
    return path


def _is_mutable_path(path: PurePosixPath) -> bool:
    lowered = tuple(part.lower() for part in path.parts)
    return bool(
        set(lowered) & FORBIDDEN_PARTS
        or path.name.lower() in FORBIDDEN_NAMES
        or any(path.name.lower().endswith(suffix) for suffix in FORBIDDEN_SUFFIXES)
    )


def _regular_files(root: Path, *, include_manifest: bool = False) -> list[Path]:
    result: list[Path] = []
    for candidate in root.rglob("*"):
        relative = candidate.relative_to(root)
        if candidate.is_symlink():
            raise ValueError(f"symlink is not allowed in release: {relative.as_posix()}")
        if candidate.is_file():
            if not include_manifest and relative.as_posix() == MANIFEST_NAME:
                continue
            result.append(candidate)
    return sorted(result, key=lambda item: item.relative_to(root).as_posix().encode("utf-8"))


def _file_record(root: Path, path: Path) -> dict[str, Any]:
    relative = path.relative_to(root).as_posix()
    safe = _safe_relative(relative)
    if _is_mutable_path(safe):
        raise ValueError(f"mutable or forbidden path inside release: {relative}")
    info = path.stat()
    if not stat.S_ISREG(info.st_mode):
        raise ValueError(f"release entry is not a regular file: {relative}")
    return {
        "path": relative,
        "sha256": sha256_file(path),
        "size": info.st_size,
        "mode": stat.S_IMODE(info.st_mode),
        "type": "file",
    }


def artifact_sha256(release: dict[str, Any], source_commit: str, build_id: str, files: list[dict[str, Any]]) -> str:
    material = {"release": release, "source_commit": source_commit, "build_id": build_id, "files": files}
    return sha256_bytes(canonical_json(material).encode("utf-8"))


def generate_manifest(release_root: Path, *, release: dict[str, Any], source_commit: str, build_id: str) -> dict[str, Any]:
    release_root = Path(release_root).resolve()
    if not release_root.is_dir():
        raise ValueError("release root is not a directory")
    files = [_file_record(release_root, path) for path in _regular_files(release_root)]
    if not files:
        raise ValueError("release contains no files")
    normalized = [item["path"].casefold() for item in files]
    if len(normalized) != len(set(normalized)):
        raise ValueError("release contains case-colliding paths")
    manifest = {
        "schema_version": 1,
        "release": {
            "schema_version": 1,
            "product": release["product"],
            "release_version": release["release_version"],
            "release_channel": release["release_channel"],
            "lpos_version": release["lpos_version"],
        },
        "source_commit": source_commit,
        "build_id": build_id,
        "generation_tool_version": TOOL_VERSION,
        "created_at": utc_now(),
        "files": files,
        "artifact_sha256": artifact_sha256(
            {
                "schema_version": 1,
                "product": release["product"],
                "release_version": release["release_version"],
                "release_channel": release["release_channel"],
                "lpos_version": release["lpos_version"],
            },
            source_commit,
            build_id,
            files,
        ),
    }
    target = release_root / MANIFEST_NAME
    target.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def verify_release(release_root: Path, *, expected_identity: dict[str, str] | None = None, expected_commit: str | None = None) -> dict[str, Any]:
    release_root = Path(release_root).resolve()
    manifest_path = release_root / MANIFEST_NAME
    if not manifest_path.is_file() or manifest_path.is_symlink():
        raise ValueError("release-manifest.json is missing or unsafe")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError) as exc:
        raise ValueError(f"release manifest is invalid: {exc}") from exc
    if not isinstance(manifest, dict):
        raise ValueError("release manifest must be an object")
    required = {"schema_version", "release", "source_commit", "build_id", "generation_tool_version", "created_at", "files", "artifact_sha256"}
    if set(manifest) != required or manifest.get("schema_version") != 1:
        raise ValueError("release manifest field set is invalid")
    rows = manifest.get("files")
    if not isinstance(rows, list) or not rows:
        raise ValueError("release manifest has no file records")
    listed: dict[str, dict[str, Any]] = {}
    folded: set[str] = set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"path", "sha256", "size", "mode", "type"}:
            raise ValueError("release manifest file record is invalid")
        path = _safe_relative(str(row["path"]))
        name = path.as_posix()
        if name in listed or name.casefold() in folded:
            raise ValueError(f"duplicate or case-colliding manifest path: {name}")
        if _is_mutable_path(path):
            raise ValueError(f"mutable path is listed in release manifest: {name}")
        if row["type"] != "file":
            raise ValueError(f"unsupported release file type: {name}")
        listed[name] = row
        folded.add(name.casefold())

    actual_paths = {path.relative_to(release_root).as_posix(): path for path in _regular_files(release_root)}
    missing = sorted(set(listed) - set(actual_paths))
    unlisted = sorted(set(actual_paths) - set(listed))
    if missing:
        raise ValueError(f"missing release files: {missing}")
    if unlisted:
        raise ValueError(f"unlisted release files: {unlisted}")
    for name, row in listed.items():
        path = actual_paths[name]
        info = path.stat()
        if info.st_size != row["size"]:
            raise ValueError(f"release file size mismatch: {name}")
        if stat.S_IMODE(info.st_mode) != row["mode"]:
            raise ValueError(f"release file mode mismatch: {name}")
        if sha256_file(path) != row["sha256"]:
            raise ValueError(f"release file hash mismatch: {name}")

    release = manifest.get("release")
    if not isinstance(release, dict):
        raise ValueError("manifest release identity is invalid")
    if expected_identity is not None:
        for field in ("product", "release_version", "release_channel", "lpos_version"):
            if release.get(field) != expected_identity.get(field):
                raise ValueError(f"manifest release identity mismatch: {field}")
    if expected_commit is not None and manifest.get("source_commit") != expected_commit:
        raise ValueError("manifest source commit mismatch")
    calculated = artifact_sha256(release, str(manifest["source_commit"]), str(manifest["build_id"]), rows)
    if calculated != manifest.get("artifact_sha256"):
        raise ValueError("release artifact identity mismatch")
    try:
        from importlib.resources import files as resource_files
        import jsonschema  # type: ignore

        schema = json.loads(resource_files("lpos_engine.schemas").joinpath("release-manifest.schema.json").read_text())
        jsonschema.validate(manifest, schema, format_checker=jsonschema.FormatChecker())
    except ImportError:
        pass
    return {
        "status": "pass",
        "manifest_sha256": sha256_file(manifest_path),
        "artifact_sha256": calculated,
        "file_count": len(rows),
        "total_bytes": sum(int(row["size"]) for row in rows),
        "source_commit": manifest["source_commit"],
        "build_id": manifest["build_id"],
        "release": release,
    }


def _tracked_files(repo: Path) -> list[str]:
    completed = subprocess.run(
        ["git", "ls-files", "-z"], cwd=repo, capture_output=True, check=False, timeout=60
    )
    if completed.returncode != 0:
        raise ValueError("tracked-file inventory failed")
    return [item.decode("utf-8") for item in completed.stdout.split(b"\0") if item]


def stage_release(repo: Path, destination: Path, *, build_id: str, require_clean: bool = True, excludes: Iterable[str] = ()) -> dict[str, Any]:
    repo = Path(repo).resolve()
    destination = Path(destination).resolve()
    identity = read_release_identity(repo, require_clean=require_clean)
    if destination == repo or repo in destination.parents:
        raise ValueError("staged release must be outside the source tree")
    if destination.exists() and any(destination.iterdir()):
        raise ValueError("staged release destination is not empty")
    destination.mkdir(parents=True, exist_ok=True)
    excluded = set(excludes)
    for relative in _tracked_files(repo):
        path = _safe_relative(relative)
        if relative in excluded or _is_mutable_path(path):
            continue
        source = repo / relative
        if source.is_symlink():
            raise ValueError(f"tracked symlink is not allowed: {relative}")
        if not source.is_file():
            raise ValueError(f"tracked release input is missing: {relative}")
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    return generate_manifest(destination, release=identity, source_commit=identity["git_commit"], build_id=build_id)
