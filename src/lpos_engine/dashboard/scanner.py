"""Forgiving filesystem scanner for Hermes project directories.

The scanner is a separate layer from the UI and the HTTP server.  It reads
whatever metadata Hermes already writes (``project.json`` per project folder,
``kanban/*.json`` boards) and falls back gracefully to folder name plus mtime
when metadata is absent or malformed.  It never raises for a broken file: a
project that exists on disk always appears in the dashboard.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any, Iterable

ENV_ROOT = "LPOS_HERMES_ROOT"
DEFAULT_ROOT_NAME = ".hermes"

#: Directory names under the hermes root that are scanned for projects.
STANDARD_ROOT_NAMES = ("sessions", "standing-operations", "projects")

#: Directory names that are never descended into while indexing files.
_SKIP_DIR_NAMES = {
    ".git",
    ".hg",
    ".svn",
    "__pycache__",
    "node_modules",
    ".venv",
    "venv",
}

_PROJECT_TYPES = ("active", "research")

_SEARCH_MAX_FILES = 100
_SEARCH_MAX_DEPTH = 4
_SEARCH_MAX_ENTRIES = 5000


def hermes_root(override: str | os.PathLike[str] | None = None) -> Path:
    """Resolve the Hermes root: explicit override, env var, or ``~/.hermes``."""
    if override is not None:
        return Path(override).expanduser()
    env = os.environ.get(ENV_ROOT, "").strip()
    if env:
        return Path(env).expanduser()
    return Path.home() / DEFAULT_ROOT_NAME


def _read_json(path: Path) -> Any:
    """Read a JSON file, returning ``None`` on any failure."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        return None


def project_roots(root: Path) -> list[Path]:
    """The directories scanned for projects: standard names plus roots.json extras."""
    roots: list[Path] = [root / name for name in STANDARD_ROOT_NAMES]
    extra = _read_json(root / "dashboard" / "roots.json")
    entries: list[Any] = []
    if isinstance(extra, list):
        entries = extra
    elif isinstance(extra, dict):
        candidate = extra.get("roots")
        if isinstance(candidate, list):
            entries = candidate
    for item in entries:
        if not isinstance(item, str) or not item.strip():
            continue
        path = Path(item.strip()).expanduser()
        if not path.is_absolute():
            path = root / path
        roots.append(path)
    seen: set[str] = set()
    unique: list[Path] = []
    for candidate_path in roots:
        key = str(candidate_path)
        if key not in seen:
            seen.add(key)
            unique.append(candidate_path)
    return unique


def _resolve_strict(path: Path) -> Path | None:
    """Resolve ``path`` following symlinks, requiring it to exist. None on failure."""
    try:
        return Path(path).resolve(strict=True)
    except (OSError, RuntimeError):
        return None


def approved_roots(root: Path | None = None) -> list[Path]:
    """The resolved, existing approved scan roots (LPOS-09).

    Standard roots plus ``roots.json`` extras; every entry must exist and
    resolve cleanly (symlinks followed) or it is dropped.  The resolved form
    is the approved boundary used for containment checks.
    """
    base = hermes_root(root)
    resolved: list[Path] = []
    seen: set[str] = set()
    for candidate in project_roots(base):
        target = _resolve_strict(candidate)
        if target is None or not target.is_dir():
            continue
        key = str(target)
        if key not in seen:
            seen.add(key)
            resolved.append(target)
    return resolved


def containment_roots(root: Path | None = None) -> list[Path]:
    """Resolved roots that any scanned, searched, or opened path must stay
    inside: the hermes root itself plus every approved extra root (LPOS-09)."""
    base = hermes_root(root)
    roots: list[Path] = []
    base_resolved = _resolve_strict(base)
    if base_resolved is not None:
        roots.append(base_resolved)
    for extra in approved_roots(base):
        if not any(extra.is_relative_to(existing) for existing in roots):
            roots.append(extra)
    return roots


def is_contained(resolved: Path, roots: Iterable[Path]) -> bool:
    """Whether an already-resolved path lies inside one of the resolved roots."""
    return any(resolved.is_relative_to(root) for root in roots)


def _slug(text: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9._-]+", "-", text.strip()).strip("-").lower()
    return cleaned[:40] or "project"


def _make_id(name: str, key: str) -> str:
    digest = hashlib.sha1(key.encode("utf-8", "replace")).hexdigest()[:8]
    return f"{_slug(name)}-{digest}"


def _dir_last_activity(path: Path) -> float:
    """Best-effort last activity: newest mtime among the dir and its children."""
    try:
        newest = path.stat().st_mtime
    except OSError:
        return 0.0
    try:
        with os.scandir(path) as entries:
            for index, entry in enumerate(entries):
                if index >= 200:
                    break
                try:
                    newest = max(newest, entry.stat(follow_symlinks=False).st_mtime)
                except OSError:
                    continue
    except OSError:
        pass
    return newest


def _friendly_path(path: Path) -> str:
    text = str(path)
    home = str(Path.home())
    if home and text.startswith(home):
        return "~" + text[len(home) :]
    return text


def _scan_folder_project(folder: Path, root_name: str) -> dict[str, Any]:
    meta = _read_json(folder / "project.json")
    if not isinstance(meta, dict):
        meta = {}
    name = meta.get("name")
    if not isinstance(name, str) or not name.strip():
        name = folder.name
    description = meta.get("description")
    if not isinstance(description, str):
        description = ""
    agent = meta.get("agent")
    if not isinstance(agent, str) or not agent.strip():
        agent = None
    project_type = meta.get("type")
    if project_type not in _PROJECT_TYPES:
        project_type = "active"
    return {
        "id": _make_id(name, str(folder)),
        "name": name.strip(),
        "path": str(folder),
        "friendly_path": _friendly_path(folder),
        "description": description.strip(),
        "agent": agent,
        "type": project_type,
        "last_activity": _dir_last_activity(folder),
        "source": "scan",
        "root": root_name,
    }


def _kanban_items(data: Any) -> list[dict[str, Any]]:
    """Extract card-like dicts from an arbitrary kanban JSON shape."""
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        for key in ("cards", "items", "projects", "tasks", "columns"):
            value = data.get(key)
            if isinstance(value, list):
                found = [item for item in value if isinstance(item, dict)]
                # Columns may nest cards one level deeper.
                nested: list[dict[str, Any]] = []
                for item in found:
                    inner = item.get("cards") or item.get("items")
                    if isinstance(inner, list):
                        nested.extend(x for x in inner if isinstance(x, dict))
                return nested or found
        return [data]
    return []


def _scan_kanban(root: Path, containment: list[Path] | None = None) -> list[dict[str, Any]]:
    if containment is None:
        containment = containment_roots(root)
    kanban_dir = root / "kanban"
    if not kanban_dir.is_dir():
        return []
    projects: list[dict[str, Any]] = []
    try:
        files = sorted(kanban_dir.glob("*.json"))
    except OSError:
        return []
    for file in files:
        data = _read_json(file)
        try:
            file_mtime = file.stat().st_mtime
        except OSError:
            file_mtime = 0.0
        for index, item in enumerate(_kanban_items(data)):
            name = None
            for key in ("name", "title", "id"):
                value = item.get(key)
                if isinstance(value, str) and value.strip():
                    name = value.strip()
                    break
            if name is None:
                name = f"{file.stem} card {index + 1}"
            description = item.get("description")
            if not isinstance(description, str):
                description = ""
            agent = None
            for key in ("agent", "owner", "assignee"):
                value = item.get(key)
                if isinstance(value, str) and value.strip():
                    agent = value.strip()
                    break
            project_type = item.get("type")
            if project_type not in _PROJECT_TYPES:
                status = item.get("status")
                project_type = "research" if status == "research" else "active"
            raw_path = item.get("path")
            note = None
            card_path: Path | None
            if isinstance(raw_path, str) and raw_path.strip():
                candidate = Path(raw_path.strip()).expanduser()
                if not candidate.is_absolute():
                    candidate = root / candidate
                # LPOS-09: resolve (following symlinks) and require containment
                # inside an approved root; otherwise drop the path but keep the
                # card metadata.
                try:
                    resolved = candidate.resolve()
                except (OSError, RuntimeError):
                    resolved = None
                if resolved is not None and is_contained(resolved, containment):
                    card_path = resolved
                else:
                    card_path = None
                    note = "path outside approved roots"
            else:
                card_path = file
            projects.append(
                {
                    "id": _make_id(name, f"{file}#{index}#{name}"),
                    "name": name,
                    "path": str(card_path) if card_path is not None else None,
                    "friendly_path": _friendly_path(card_path) if card_path is not None else None,
                    "description": description.strip(),
                    "agent": agent,
                    "type": project_type,
                    "last_activity": file_mtime,
                    "source": "kanban",
                    "root": "kanban",
                    **({"note": note} if note else {}),
                }
            )
    return projects


def scan_projects(root: Path | None = None) -> list[dict[str, Any]]:
    """Scan the hermes root and return every discoverable project.

    Never raises for unreadable or malformed content; missing roots simply
    contribute nothing.
    """
    base = hermes_root(root)
    projects: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for scan_root in project_roots(base):
        # LPOS-09: the configured root itself must exist and resolve cleanly;
        # its resolved form is the approved boundary.
        resolved_root = _resolve_strict(scan_root)
        if resolved_root is None or not resolved_root.is_dir():
            continue
        try:
            entries = sorted(resolved_root.iterdir(), key=lambda p: p.name)
        except OSError:
            continue
        for entry in entries:
            if entry.name.startswith("."):
                continue
            try:
                # LPOS-09: never treat a symlinked directory as a project.
                if entry.is_symlink() or not entry.is_dir():
                    continue
            except OSError:
                continue
            resolved_entry = _resolve_strict(entry)
            if resolved_entry is None or not resolved_entry.is_relative_to(resolved_root):
                continue
            project = _scan_folder_project(resolved_entry, resolved_root.name)
            if project["id"] in seen_ids:
                continue
            seen_ids.add(project["id"])
            projects.append(project)
    for project in _scan_kanban(base):
        if project["id"] in seen_ids:
            continue
        seen_ids.add(project["id"])
        projects.append(project)
    return projects


def search(root: Path | None, query: str, projects: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Match ``query`` against project names and file names across all roots."""
    base = hermes_root(root)
    needle = query.strip().lower()
    if projects is None:
        projects = scan_projects(base)
    if not needle:
        return {"query": query, "projects": [], "files": []}
    matched_projects = [
        project
        for project in projects
        if needle in project["name"].lower() or needle in project["description"].lower()
    ]
    files: list[dict[str, Any]] = []
    visited = 0
    containment = containment_roots(base)
    for project in projects:
        raw_project_path = project.get("path")
        if not raw_project_path:
            continue
        project_path = Path(raw_project_path)
        # LPOS-09: only walk real directories that resolve inside an approved
        # root; never start a walk at a symlink.
        try:
            if project_path.is_symlink():
                continue
        except OSError:
            continue
        resolved_project = _resolve_strict(project_path)
        if (
            resolved_project is None
            or not resolved_project.is_dir()
            or not is_contained(resolved_project, containment)
        ):
            continue
        base_depth = len(resolved_project.parts)
        # followlinks=False (the default) so directory symlinks are not
        # descended; they are additionally pruned from dirnames below.
        for dirpath, dirnames, filenames in os.walk(resolved_project, followlinks=False):
            depth = len(Path(dirpath).parts) - base_depth
            dirnames[:] = [
                d
                for d in dirnames
                if not d.startswith(".")
                and d not in _SKIP_DIR_NAMES
                and depth < _SEARCH_MAX_DEPTH
                and not os.path.islink(os.path.join(dirpath, d))
            ]
            for filename in filenames:
                visited += 1
                if visited > _SEARCH_MAX_ENTRIES or len(files) >= _SEARCH_MAX_FILES:
                    break
                if filename.startswith("."):
                    continue
                if needle in filename.lower():
                    full = Path(dirpath) / filename
                    files.append(
                        {
                            "name": filename,
                            "path": str(full),
                            "friendly_path": _friendly_path(full),
                            "project_id": project["id"],
                            "project_name": project["name"],
                        }
                    )
            if visited > _SEARCH_MAX_ENTRIES or len(files) >= _SEARCH_MAX_FILES:
                break
        if len(files) >= _SEARCH_MAX_FILES:
            break
    return {"query": query, "projects": matched_projects, "files": files}
