"""Dashboard state: bucket overrides, snooze timers, and archive records.

All metadata lives in one JSON file, ``<hermes-root>/dashboard/state.json``.
Corrupt or missing state degrades to "everything Active" — never a crash.
Writes are atomic (temp file plus ``os.replace``) so a crash mid-write can
never leave a torn file behind.
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BUCKETS = ("active", "research", "snoozed", "archived")
WORKING_BUCKETS = ("active", "research")

STATE_VERSION = 1


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def iso(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def parse_iso(value: Any) -> datetime | None:
    """Parse an ISO 8601 timestamp; naive values are assumed UTC. None on failure."""
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    if text.endswith(("Z", "z")):
        text = text[:-1] + "+00:00"
    try:
        moment = datetime.fromisoformat(text)
    except ValueError:
        return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc)


def state_path(root: Path) -> Path:
    return root / "dashboard" / "state.json"


class DashboardState:
    """In-memory view of the persisted dashboard metadata."""

    def __init__(self, data: dict[str, Any] | None = None) -> None:
        if not isinstance(data, dict):
            data = {}
        projects = data.get("projects")
        if not isinstance(projects, dict):
            projects = {}
        self.projects: dict[str, dict[str, Any]] = {
            key: dict(value) for key, value in projects.items() if isinstance(value, dict)
        }

    # -- persistence ------------------------------------------------------

    @classmethod
    def load(cls, path: Path) -> "DashboardState":
        """Load state; any failure (missing, corrupt, wrong shape) yields empty state."""
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, ValueError, UnicodeDecodeError):
            return cls()
        return cls(data if isinstance(data, dict) else None)

    def save(self, path: Path) -> None:
        """Atomically persist state via a temp file and ``os.replace``."""
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(
            {"version": STATE_VERSION, "projects": self.projects},
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        fd, tmp_name = tempfile.mkstemp(
            prefix=target.name + ".", suffix=".tmp", dir=str(target.parent)
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(payload + "\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp_name, target)
        except BaseException:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
            raise

    # -- mutations --------------------------------------------------------

    def _record(self, project_id: str) -> dict[str, Any]:
        record = self.projects.setdefault(project_id, {})
        return record

    def move(self, project_id: str, bucket: str, default_bucket: str = "active") -> None:
        """Explicitly place a project in a bucket, clearing snooze metadata."""
        if bucket not in BUCKETS or bucket == "snoozed":
            raise ValueError(f"invalid bucket: {bucket!r}")
        record = self._record(project_id)
        record.pop("snooze_until", None)
        record.pop("snoozed_from", None)
        if bucket == "archived":
            record["archived_at"] = iso(utcnow())
        else:
            record.pop("archived_at", None)
        record["bucket"] = bucket
        record["updated_at"] = iso(utcnow())

    def snooze(self, project_id: str, until: datetime, default_bucket: str = "active") -> None:
        record = self._record(project_id)
        current = self.effective(project_id, default_bucket)["bucket"]
        if current in WORKING_BUCKETS:
            record["snoozed_from"] = current
        elif record.get("snoozed_from") not in WORKING_BUCKETS:
            record["snoozed_from"] = default_bucket if default_bucket in WORKING_BUCKETS else "active"
        record["bucket"] = "snoozed"
        record["snooze_until"] = iso(until)
        record.pop("archived_at", None)
        record["updated_at"] = iso(utcnow())

    def archive(self, project_id: str) -> None:
        self.move(project_id, "archived")

    def restore(self, project_id: str, bucket: str = "active") -> None:
        if bucket not in WORKING_BUCKETS:
            raise ValueError(f"restore bucket must be one of {WORKING_BUCKETS}, got {bucket!r}")
        self.move(project_id, bucket)

    # -- queries ----------------------------------------------------------

    def effective(
        self,
        project_id: str,
        default_bucket: str = "active",
        now: datetime | None = None,
    ) -> dict[str, Any]:
        """Compute the effective bucket after snooze-wake logic.

        A snoozed item whose wake time has passed returns to its previous
        bucket with ``woke=True``.  The state file is not mutated on read.
        """
        if default_bucket not in WORKING_BUCKETS:
            default_bucket = "active"
        moment = now or utcnow()
        record = self.projects.get(project_id)
        result: dict[str, Any] = {
            "bucket": default_bucket,
            "woke": False,
            "snooze_until": None,
            "archived_at": None,
        }
        if not isinstance(record, dict):
            return result
        bucket = record.get("bucket")
        if bucket not in BUCKETS:
            return result
        if bucket == "snoozed":
            until = parse_iso(record.get("snooze_until"))
            previous = record.get("snoozed_from")
            if previous not in WORKING_BUCKETS:
                previous = default_bucket
            if until is None or until <= moment:
                result["bucket"] = previous
                result["woke"] = True
                result["snooze_until"] = record.get("snooze_until")
            else:
                result["bucket"] = "snoozed"
                result["snooze_until"] = record.get("snooze_until")
            return result
        if bucket == "archived":
            result["bucket"] = "archived"
            archived_at = record.get("archived_at")
            result["archived_at"] = archived_at if isinstance(archived_at, str) else None
            return result
        result["bucket"] = bucket
        return result
