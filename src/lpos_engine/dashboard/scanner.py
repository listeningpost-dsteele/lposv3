"""Filesystem and Hermes state scanner for the LPOS dashboard."""

from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Iterable

IGNORE_NAMES = {".git", "node_modules", "__pycache__", ".pytest_cache", ".venv", "dist", "build"}
DELIVERABLE_SUFFIXES = {".md", ".txt", ".pdf", ".docx", ".xlsx", ".csv", ".json", ".html", ".png", ".jpg", ".jpeg", ".webp", ".mp4"}


@dataclass
class DashboardItem:
    id: str
    name: str
    desc: str
    agents: list[str]
    source: str
    suggested_bucket: str
    path: str
    mtime: float
    file_count: int
    files: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["suggestedBucket"] = data.pop("suggested_bucket")
        data["fileCount"] = data.pop("file_count")
        return data


def hermes_root(value: str | None = None) -> Path:
    if value:
        return Path(os.path.expanduser(value)).resolve()
    return (Path.home() / ".hermes").resolve()


def _safe_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def _walk_files(root: Path, *, depth: int = 3, limit: int = 800) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []

    def walk(path: Path, level: int) -> None:
        if level > depth or len(found) >= limit:
            return
        try:
            entries = sorted(path.iterdir(), key=lambda p: p.name.casefold())
        except OSError:
            return
        for entry in entries:
            if entry.name.startswith(".") or entry.name in IGNORE_NAMES:
                continue
            try:
                if entry.is_dir():
                    walk(entry, level + 1)
                elif entry.is_file():
                    stat = entry.stat()
                    found.append({"path": str(entry), "name": entry.name, "mtime": stat.st_mtime * 1000, "size": stat.st_size})
            except OSError:
                continue
    walk(root, 0)
    found.sort(key=lambda item: item["mtime"], reverse=True)
    return found


def _key_files(path: Path) -> tuple[list[dict[str, Any]], float, int]:
    files = _walk_files(path)
    if files:
        mtime = max(item["mtime"] for item in files)
    else:
        try:
            mtime = path.stat().st_mtime * 1000
        except OSError:
            mtime = 0
    key = []
    for item in files:
        suffix = Path(item["path"]).suffix.lower()
        if suffix and suffix not in DELIVERABLE_SUFFIXES:
            continue
        try:
            rel = str(Path(item["path"]).relative_to(path))
        except ValueError:
            rel = item["name"]
        key.append({
            "name": rel,
            "path": item["path"],
            "mtime": item["mtime"],
            "kind": (suffix.lstrip(".") or "file")[:4].upper(),
        })
        if len(key) >= 8:
            break
    return key, mtime, len(files)


def _read_description(path: Path) -> str:
    info = _safe_json(path / "project.json")
    if isinstance(info.get("description"), str):
        return info["description"][:260]
    for name in ("README.md", "readme.md", "README.txt"):
        try:
            text = (path / name).read_text(encoding="utf-8")
        except OSError:
            continue
        blocks = [line.strip() for line in text.split("\n\n") if line.strip() and not line.lstrip().startswith("#")]
        if blocks:
            return " ".join(blocks[0].split())[:260]
    return ""


def _title(value: str) -> str:
    return " ".join(part.capitalize() for part in value.replace("_", " ").replace("-", " ").split())


def _item_from_directory(path: Path, source: str, default_bucket: str = "active") -> DashboardItem | None:
    if not path.exists() or not path.is_dir():
        return None
    info = _safe_json(path / "project.json")
    key, mtime, count = _key_files(path)
    agents = info.get("agents") if isinstance(info.get("agents"), list) else None
    if agents is None and isinstance(info.get("agent"), str):
        agents = [info["agent"]]
    return DashboardItem(
        id=f"{source}:{path.name}",
        name=str(info.get("name") or _title(path.name)),
        desc=_read_description(path),
        agents=[str(a) for a in (agents or [])],
        source=source,
        suggested_bucket=str(info.get("type") or default_bucket if str(info.get("type") or default_bucket) in {"active", "research"} else default_bucket),
        path=str(path),
        mtime=mtime,
        file_count=count,
        files=key,
    )


def _scan_directory_roots(root: Path) -> list[DashboardItem]:
    items: list[DashboardItem] = []
    candidate_roots = [root / "projects", root / "guilds", root / "standing-operations", root / "specialists", root / "lpos-runtime"]
    for base in candidate_roots:
        if not base.is_dir():
            continue
        for child in sorted(base.iterdir(), key=lambda p: p.name.casefold()):
            if child.name.startswith(".") or child.name in IGNORE_NAMES or not child.is_dir():
                continue
            item = _item_from_directory(child, base.name, "research" if base.name in {"guilds", "specialists"} else "active")
            if item:
                items.append(item)
    return items


def _scan_kanban(root: Path) -> list[DashboardItem]:
    db = root / "kanban.db"
    if not db.is_file():
        return []
    try:
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        con.row_factory = sqlite3.Row
        rows = list(con.execute("select * from tasks order by coalesce(started_at, created_at) desc limit 200"))
    except sqlite3.Error:
        return []
    finally:
        try:
            con.close()
        except Exception:
            pass
    items: list[DashboardItem] = []
    for row in rows:
        data = dict(row)
        path_value = data.get("workspace_path") or str(root / "kanban")
        path = Path(path_value).expanduser()
        if not path.exists():
            path = root / "kanban"
        key, mtime, count = _key_files(path) if path.is_dir() else ([], float(data.get("created_at") or 0) * 1000, 0)
        started = data.get("started_at") or data.get("created_at") or 0
        mtime = max(mtime, float(started) * 1000)
        status = str(data.get("status") or "active").lower()
        bucket = "archive" if status in {"done", "completed", "released"} else "active"
        assignee = data.get("assignee") or data.get("created_by") or "Hermes"
        body = " ".join(str(data.get("body") or "").split())[:260]
        items.append(DashboardItem(
            id=f"kanban:{data.get('id')}",
            name=str(data.get("title") or data.get("id")),
            desc=body,
            agents=[str(assignee)] if assignee else [],
            source="kanban",
            suggested_bucket=bucket,
            path=str(path),
            mtime=mtime,
            file_count=count,
            files=key,
        ))
    return items


def _scan_sessions(root: Path) -> list[DashboardItem]:
    sessions = root / "sessions"
    if not sessions.is_dir():
        return []
    dumps = sorted(sessions.glob("request_dump*.json"), key=lambda p: p.stat().st_mtime if p.exists() else 0, reverse=True)[:80]
    grouped: dict[str, list[Path]] = {}
    for dump in dumps:
        parts = dump.name.split("_")
        key = "_".join(parts[:4]) if len(parts) >= 4 else dump.stem
        grouped.setdefault(key, []).append(dump)
    items: list[DashboardItem] = []
    for key, paths in grouped.items():
        latest = max(paths, key=lambda p: p.stat().st_mtime)
        meta = _safe_json(latest)
        title = meta.get("title") or meta.get("session_title") or key.replace("request_dump_", "Session ")
        path = latest.parent
        mtime = latest.stat().st_mtime * 1000
        files = [{"name": p.name, "path": str(p), "mtime": p.stat().st_mtime * 1000, "kind": "JSON"} for p in paths[:8]]
        items.append(DashboardItem(
            id=f"session:{key}",
            name=str(title),
            desc="Recent Hermes session activity and request dumps.",
            agents=["Hermes"],
            source="sessions",
            suggested_bucket="research",
            path=str(path),
            mtime=mtime,
            file_count=len(paths),
            files=files,
        ))
    return items


def scan(root_value: str | None = None) -> list[dict[str, Any]]:
    root = hermes_root(root_value)
    items: list[DashboardItem] = []
    items.extend(_scan_kanban(root))
    items.extend(_scan_directory_roots(root))
    items.extend(_scan_sessions(root))
    seen: set[str] = set()
    result = []
    for item in sorted(items, key=lambda it: it.mtime, reverse=True):
        if item.id in seen:
            continue
        seen.add(item.id)
        result.append(item.to_dict())
    return result
