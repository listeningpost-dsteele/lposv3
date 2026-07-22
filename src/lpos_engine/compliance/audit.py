"""Run the control catalog, keep Type 2 history, publish status.json.

Short-lived job semantics, mirroring the connector monitor: :func:`run_audit`
runs every control against the repo checkout and Hermes root, appends one JSON
line per control result to ``<hermes>/compliance/history.jsonl`` (capped at
:data:`HISTORY_LIMIT` lines, oldest trimmed), computes per-control Type 2
operating effectiveness over the observation window, and atomically writes
``<hermes>/compliance/status.json`` with a stable contract::

    {
      "generated_at": "...", "framework": "SOC 2 Type 2 (TSC 2017, 2022 POF)",
      "window_days": 90, "overall": "compliant" | "gaps",
      "controls": [...], "summary": {...}
    }
"""

from __future__ import annotations

import json
import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .controls import Control, ControlResult, all_controls, run_control
from .criteria import FRAMEWORK, OBSERVATION_WINDOW_DAYS

HISTORY_LIMIT = 10_000
EFFECTIVENESS_THRESHOLD = 0.98


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


def compliance_dir(hermes_root: Path) -> Path:
    return Path(hermes_root).expanduser() / "compliance"


def history_path(hermes_root: Path) -> Path:
    return compliance_dir(hermes_root) / "history.jsonl"


def status_path(hermes_root: Path) -> Path:
    return compliance_dir(hermes_root) / "status.json"


def staging_dir(hermes_root: Path) -> Path:
    return compliance_dir(hermes_root) / "staging"


def _atomic_write_text(path: Path, text: str) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def _atomic_write_json(path: Path, payload: Any) -> None:
    _atomic_write_text(path, json.dumps(payload, indent=2) + "\n")


def load_history(hermes_root: Path) -> list[dict[str, Any]]:
    """Load history.jsonl tolerantly; malformed lines are skipped, not fatal."""

    entries: list[dict[str, Any]] = []
    try:
        text = history_path(hermes_root).read_text(encoding="utf-8")
    except OSError:
        return entries
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            value = json.loads(line)
        except ValueError:
            continue
        if isinstance(value, Mapping):
            entries.append(dict(value))
    return entries


def append_history(hermes_root: Path, new_entries: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Append entries to history.jsonl, trimming to the newest HISTORY_LIMIT lines."""

    entries = load_history(hermes_root)
    entries.extend(dict(entry) for entry in new_entries)
    entries = entries[-HISTORY_LIMIT:]
    path = history_path(hermes_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write_text(path, "".join(json.dumps(entry) + "\n" for entry in entries))
    return entries


def _is_check_entry(entry: Mapping[str, Any]) -> bool:
    return entry.get("event", "check") == "check" and "passing" in entry


def effectiveness_for(
    entries: Sequence[Mapping[str, Any]],
    control_id: str,
    *,
    now: datetime,
    window_days: int = OBSERVATION_WINDOW_DAYS,
    current_pass: bool,
) -> dict[str, Any]:
    """Type 2 operating effectiveness for one control over the window.

    Verdicts: "effective" when the in-window pass ratio is >= 0.98 AND the
    current run passes; "ineffective" when the current run fails; otherwise
    "not yet demonstrated" (currently passing, but the window has not shown a
    sustained >=0.98 pass rate).
    """

    cutoff = now - timedelta(days=window_days)
    runs = 0
    passes = 0
    for entry in entries:
        if entry.get("control_id") != control_id or not _is_check_entry(entry):
            continue
        stamp = parse_iso(entry.get("ts"))
        if stamp is None or stamp < cutoff:
            continue
        runs += 1
        if entry.get("passing"):
            passes += 1
    ratio = (passes / runs) if runs else 0.0
    if not current_pass:
        verdict = "ineffective"
    elif ratio >= EFFECTIVENESS_THRESHOLD:
        verdict = "effective"
    else:
        verdict = "not yet demonstrated"
    return {
        "runs_in_window": runs,
        "passes_in_window": passes,
        "effectiveness": round(ratio, 4),
        "verdict": verdict,
    }


@dataclass(frozen=True, slots=True)
class AuditResult:
    generated_at: str
    overall: str
    status: dict[str, Any]
    results: dict[str, ControlResult] = field(default_factory=dict)
    status_path: str = ""
    history_path: str = ""

    @property
    def failing(self) -> list[str]:
        return [cid for cid, result in self.results.items() if not result.passing]


def run_audit(
    repo_root: Path,
    hermes_root: Path,
    *,
    controls: Sequence[Control] | None = None,
    now: str | None = None,
    window_days: int = OBSERVATION_WINDOW_DAYS,
) -> AuditResult:
    """Run one full compliance audit pass and persist history + status.json."""

    repo_root = Path(repo_root).expanduser().resolve()
    hermes_root = Path(hermes_root).expanduser()
    catalog = tuple(controls) if controls is not None else all_controls()
    now_iso = now or utc_now_iso()
    now_dt = parse_iso(now_iso) or datetime.now(timezone.utc)

    results: dict[str, ControlResult] = {}
    new_lines: list[dict[str, Any]] = []
    for control in catalog:
        result = run_control(control, repo_root, hermes_root)
        results[control.control_id] = result
        new_lines.append(
            {
                "ts": now_iso,
                "event": "check",
                "control_id": control.control_id,
                "passing": result.passing,
                "evidence": result.evidence,
            }
        )

    entries = append_history(hermes_root, new_lines)

    control_docs: list[dict[str, Any]] = []
    for control in catalog:
        result = results[control.control_id]
        effectiveness = effectiveness_for(
            entries,
            control.control_id,
            now=now_dt,
            window_days=window_days,
            current_pass=result.passing,
        )
        control_docs.append(
            {
                "control_id": control.control_id,
                "tsc_id": control.tsc_id,
                "title": control.title,
                "category": control.category,
                "passing": result.passing,
                "evidence": result.evidence,
                "details": result.details,
                **effectiveness,
            }
        )

    check_stamps = [
        parse_iso(entry.get("ts"))
        for entry in entries
        if _is_check_entry(entry)
    ]
    check_stamps = [stamp for stamp in check_stamps if stamp is not None]
    in_window = [s for s in check_stamps if s >= now_dt - timedelta(days=window_days)]
    days_of_history = (
        min(window_days, max(0, (now_dt - min(in_window)).days)) if in_window else 0
    )

    summary = {
        "total": len(control_docs),
        "passing": sum(1 for c in control_docs if c["passing"]),
        "failing": sum(1 for c in control_docs if not c["passing"]),
        "effective": sum(1 for c in control_docs if c["verdict"] == "effective"),
        "not_yet_demonstrated": sum(
            1 for c in control_docs if c["verdict"] == "not yet demonstrated"
        ),
        "ineffective": sum(1 for c in control_docs if c["verdict"] == "ineffective"),
    }
    overall = "compliant" if summary["failing"] == 0 else "gaps"
    status = {
        "generated_at": now_iso,
        "framework": FRAMEWORK,
        "window_days": window_days,
        "overall": overall,
        "coverage": {
            "days_of_history": days_of_history,
            "runs_in_window": len(in_window),
        },
        "controls": control_docs,
        "summary": summary,
    }

    path = status_path(hermes_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write_json(path, status)

    return AuditResult(
        generated_at=now_iso,
        overall=overall,
        status=status,
        results=results,
        status_path=str(path),
        history_path=str(history_path(hermes_root)),
    )


def load_status(hermes_root: Path) -> dict[str, Any]:
    try:
        value = json.loads(status_path(hermes_root).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"generated_at": None, "overall": "gaps", "controls": [], "summary": {}}
    if not isinstance(value, Mapping):
        return {"generated_at": None, "overall": "gaps", "controls": [], "summary": {}}
    return dict(value)
