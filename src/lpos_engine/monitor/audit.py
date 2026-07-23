"""The hourly connector audit: check everything, record state, publish status.

Short-lived job semantics: :func:`run_audit` wakes, refreshes the inventory,
runs every non-muted check concurrently (15 s timeout, one retry after 5 s),
appends results to per-connector history in ``state.json`` (capped at 500
entries per connector), writes ``status.json`` atomically, and returns a
summary including ok->offline / offline->ok transitions and any credentials
expiring within 7 days.  Alert delivery is a separate step (see ``alert.py``).
"""

from __future__ import annotations

import json
import os
import time
from collections.abc import Callable, Mapping
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from . import checks as checks_module
from . import inventory as inventory_module
from .checks import CheckFunction, CheckResult
from .inventory import hermes_root, monitor_dir

HISTORY_LIMIT = 500
AUTH_EXPIRY_WARNING_DAYS = 7


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def state_path(root: Path | None = None) -> Path:
    return monitor_dir(root) / "state.json"


def status_path(root: Path | None = None) -> Path:
    return monitor_dir(root) / "status.json"


def _atomic_write_json(path: Path, payload: Any) -> None:
    from ..store import harden_file_mode, secure_create_file

    tmp = path.with_suffix(path.suffix + ".tmp")
    secure_create_file(tmp)  # 0600 before any content is written (LPOS-15)
    tmp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)
    harden_file_mode(path)


def _load_state(root: Path | None) -> dict[str, Any]:
    try:
        value = json.loads(state_path(root).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"connectors": {}}
    if not isinstance(value, Mapping) or not isinstance(value.get("connectors"), Mapping):
        return {"connectors": {}}
    return {"connectors": {str(k): dict(v) for k, v in value["connectors"].items() if isinstance(v, Mapping)}}


def _auth_warning(entry: Mapping[str, Any], now: datetime) -> str | None:
    expiry = parse_iso(entry.get("auth_expires"))
    if expiry is None:
        return None
    remaining = expiry - now
    if remaining <= timedelta(days=AUTH_EXPIRY_WARNING_DAYS):
        if remaining.total_seconds() <= 0:
            return f"credential expired at {entry['auth_expires']}"
        days = max(0, remaining.days)
        return f"credential expires in {days}d ({entry['auth_expires']})"
    return None


def run_audit(
    root: Path | None = None,
    *,
    timeout: float = checks_module.DEFAULT_TIMEOUT,
    retry_delay: float = checks_module.RETRY_DELAY,
    registry: Mapping[str, CheckFunction] | None = None,
    sleep: Callable[[float], None] = time.sleep,
    now: str | None = None,
    refresh: bool = True,
    repo_config: Path | None = None,
) -> dict[str, Any]:
    """Run one full audit pass and persist state.json + status.json."""

    base = Path(root) if root is not None else hermes_root()
    now_iso = now or utc_now_iso()
    now_dt = parse_iso(now_iso) or datetime.now(timezone.utc)

    if refresh:
        inventory = inventory_module.refresh_inventory(base, repo_config)
    else:
        inventory = inventory_module.load_inventory(base)

    state = _load_state(base)
    active = [entry for entry in inventory if not entry.get("muted")]
    results: dict[str, CheckResult | None] = checks_module.run_checks(
        active,
        timeout=timeout,
        retry_delay=retry_delay,
        registry=registry,
        sleep=sleep,
        root=base,
    )

    connectors: list[dict[str, Any]] = []
    transitions: dict[str, list[str]] = {"offline": [], "recovered": []}
    warnings: list[dict[str, str]] = []

    for entry in inventory:
        entry_id = str(entry["id"])
        previous = state["connectors"].get(entry_id, {})
        muted = bool(entry.get("muted"))

        if muted:
            status, latency_ms, error = "unknown", None, "muted"
        else:
            result = results.get(entry_id)
            if result is None:
                status, latency_ms, error = "unknown", None, "no check configured for this connector"
            elif getattr(result, "unknown", False):
                # Refused before any execution (e.g. unapproved check
                # definition, LPOS-03): unknown, never ok, never offline.
                status, latency_ms, error = "unknown", None, result.error
            elif result.ok:
                status, latency_ms, error = "ok", result.latency_ms, ""
            else:
                status, latency_ms, error = "offline", result.latency_ms, result.error

        last_ok = previous.get("last_ok")
        down_since = previous.get("down_since")
        previous_status = previous.get("status")
        if status == "ok":
            last_ok = now_iso
            if previous_status == "offline":
                transitions["recovered"].append(entry_id)
            down_since = None
        elif status == "offline":
            if previous_status != "offline":
                down_since = now_iso
                transitions["offline"].append(entry_id)
            elif not down_since:
                down_since = now_iso

        warning = _auth_warning(entry, now_dt)
        if warning:
            warnings.append({"id": entry_id, "warning": warning})

        connector = {
            "id": entry_id,
            "name": str(entry.get("name", entry_id)),
            "kind": str(entry.get("kind", "other")),
            "status": status,
            "latency_ms": latency_ms,
            "error": error,
            "criticality": str(entry.get("criticality", "critical")),
            "last_ok": last_ok,
            "down_since": down_since,
        }
        if muted:
            connector["muted"] = True
        if warning:
            connector["auth_warning"] = warning
        if entry.get("unapproved_check"):
            connector["unapproved_check"] = True
        connectors.append(connector)

        history = previous.get("history")
        history = list(history) if isinstance(history, list) else []
        history.append({"ts": now_iso, "status": status, "latency_ms": latency_ms, "error": error})
        state["connectors"][entry_id] = {
            "status": status,
            "last_ok": last_ok,
            "down_since": down_since,
            "history": history[-HISTORY_LIMIT:],
        }

    overall = (
        "degraded"
        if any(c["status"] == "offline" and not c.get("muted") for c in connectors)
        else "ok"
    )
    status_doc = {"generated_at": now_iso, "overall": overall, "connectors": connectors}

    _atomic_write_json(state_path(base), state)
    _atomic_write_json(status_path(base), status_doc)

    return {
        "root": str(base),
        "generated_at": now_iso,
        "overall": overall,
        "checked": len(active),
        "total": len(inventory),
        "offline": [c["id"] for c in connectors if c["status"] == "offline"],
        "unknown": [c["id"] for c in connectors if c["status"] == "unknown"],
        "transitions": transitions,
        "warnings": warnings,
        "status_path": str(status_path(base)),
    }


def load_status(root: Path | None = None) -> dict[str, Any]:
    try:
        value = json.loads(status_path(root).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"generated_at": None, "overall": "ok", "connectors": []}
    if not isinstance(value, Mapping):
        return {"generated_at": None, "overall": "ok", "connectors": []}
    return dict(value)
