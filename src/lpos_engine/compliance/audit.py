"""Run the control catalog, keep evidence history, publish status.json.

This is a CONTROL READINESS MONITOR, not a certifier (audit finding LPOS-01).
It runs every control against the repo checkout and Hermes root, appends one
hash-chained JSON line per control result to ``<hermes>/compliance/history.jsonl``
(see :mod:`.ledger` — true append-only, tamper-evident, finding LPOS-08), and
atomically writes ``<hermes>/compliance/status.json``.

The status document never self-determines "compliant" or "effective". Every
audit execution gets a unique ``run_id``; one execution checking 21 controls
is ONE run. Readiness states:

- ``not_assessed`` — no runs at all;
- ``insufficient_evidence`` — runs exist but fewer than
  :data:`MIN_OBSERVATION_DAYS` distinct run days or :data:`MIN_RUNS` distinct
  runs are in the window;
- ``gaps`` — any control currently failing, regardless of history;
- ``ready_pending_attestation`` — all controls passing AND the evidence
  thresholds are met. A SOC 2 Type 2 conclusion is only ever issued by an
  independent CPA; ``attestation``/``issued_by_cpa`` are always false here.

Per-control verdicts: ``failing`` (current fail), ``insufficient_history``
(passing, but fewer than :data:`MIN_RUNS_PER_CONTROL` distinct runs or
:data:`MIN_OBSERVATION_DAYS` distinct run days in the window, or the pass
ratio is below :data:`OPERATING_THRESHOLD`), ``operating`` (passing, ratio
and thresholds met, outcome-assured check), and ``structural_evidence_only``
— the cap for structural (file-presence / string-search) checks, which can
never earn ``operating`` (finding LPOS-02).
"""

from __future__ import annotations

import json
import os
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from . import ledger
from .controls import NOT_EVIDENCED, Control, ControlResult, all_controls, run_control
from .criteria import FRAMEWORK, OBSERVATION_WINDOW_DAYS

#: Explicit compact() keeps at most this many lines in the active ledger.
HISTORY_LIMIT = 10_000
#: Minimum in-window pass ratio for an "operating" verdict.
OPERATING_THRESHOLD = 0.98
#: Minimum distinct UTC run days before evidence can count as sufficient.
MIN_OBSERVATION_DAYS = 30
#: Minimum distinct audit runs (run_ids) in the window, overall.
MIN_RUNS = 20
#: Minimum distinct runs per control before its history counts as sufficient.
MIN_RUNS_PER_CONTROL = 20

#: Verdict tiers, weakest first. Structural checks are capped one tier below
#: "operating" no matter how long their history is.
VERDICT_TIERS = ("failing", "insufficient_history", "structural_evidence_only", "operating")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def new_run_id(now_iso: str | None = None) -> str:
    """A unique id for one audit execution (one execution = ONE run)."""

    stamp = (now_iso or utc_now_iso()).replace(":", "").replace("+0000", "Z")
    return f"RUN-{stamp}-{uuid.uuid4().hex[:8]}"


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
    from ..store import secure_mkdir

    return secure_mkdir(Path(hermes_root).expanduser() / "compliance")


def history_path(hermes_root: Path) -> Path:
    return compliance_dir(hermes_root) / "history.jsonl"


def status_path(hermes_root: Path) -> Path:
    return compliance_dir(hermes_root) / "status.json"


def staging_dir(hermes_root: Path) -> Path:
    return compliance_dir(hermes_root) / "staging"


def _atomic_write_text(path: Path, text: str) -> None:
    from ..store import harden_file_mode, secure_create_file

    tmp = path.with_suffix(path.suffix + ".tmp")
    secure_create_file(tmp)  # LPOS-15: 0600 before content
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)
    harden_file_mode(path)


def _atomic_write_json(path: Path, payload: Any) -> None:
    _atomic_write_text(path, json.dumps(payload, indent=2) + "\n")


def load_history(hermes_root: Path) -> list[dict[str, Any]]:
    """Load history.jsonl tolerantly; malformed lines are skipped, not fatal.

    Tolerant loading serves reporting only — :func:`verify_history` is the
    integrity check and is NOT tolerant.
    """

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


def append_history(
    hermes_root: Path, new_entries: Sequence[Mapping[str, Any]]
) -> list[dict[str, Any]]:
    """True O(1) append to the hash-chained ledger; never read-modify-rewrite.

    Returns only the appended entries (with ``seq`` and ``chain`` assigned).
    Trimming is a separate, explicit :func:`compact_history` call.
    """

    return ledger.append_entries(history_path(hermes_root), new_entries)


def compact_history(hermes_root: Path, *, keep_last: int = HISTORY_LIMIT) -> dict[str, Any]:
    """Explicit compaction: checkpoint line + verbatim archive of the prefix."""

    return ledger.compact(
        history_path(hermes_root), keep_last=keep_last, now_iso=utc_now_iso()
    )


def verify_history(hermes_root: Path) -> dict[str, Any]:
    """Verify the evidence ledger chain: ``{ok, first_bad_seq, lines, gaps, reason}``.

    Detects edited, deleted, inserted, reordered, and truncated lines. This is
    the hook the orchestrator wires into doctor and the
    ``python -m lpos_engine.compliance verify`` subcommand.
    """

    return ledger.verify_history_file(history_path(hermes_root))


def _is_check_entry(entry: Mapping[str, Any]) -> bool:
    return entry.get("event", "check") == "check" and "passing" in entry


def _entry_run_key(entry: Mapping[str, Any]) -> str:
    """Distinct-run key: run_id when present, else the legacy timestamp."""

    run_id = entry.get("run_id")
    return str(run_id) if run_id else f"legacy-ts:{entry.get('ts', '')}"


def _entry_day(entry: Mapping[str, Any]) -> str | None:
    stamp = parse_iso(entry.get("ts"))
    return stamp.astimezone(timezone.utc).date().isoformat() if stamp else None


def window_entries(
    entries: Sequence[Mapping[str, Any]], *, now: datetime, window_days: int
) -> list[Mapping[str, Any]]:
    cutoff = now - timedelta(days=window_days)
    kept: list[Mapping[str, Any]] = []
    for entry in entries:
        if not _is_check_entry(entry):
            continue
        stamp = parse_iso(entry.get("ts"))
        if stamp is None or stamp < cutoff:
            continue
        kept.append(entry)
    return kept


def evidence_for(
    entries: Sequence[Mapping[str, Any]],
    control_id: str,
    *,
    now: datetime,
    window_days: int = OBSERVATION_WINDOW_DAYS,
    current_pass: bool,
    assurance: str = "outcome",
    structural_only: bool = False,
) -> dict[str, Any]:
    """Per-control operating-evidence stats and verdict over the window.

    Verdicts (never "effective" — that word is an auditor's, not ours):

    - ``failing`` — the current run fails, regardless of history;
    - ``insufficient_history`` — passing, but fewer than
      :data:`MIN_RUNS_PER_CONTROL` distinct runs or
      :data:`MIN_OBSERVATION_DAYS` distinct run days in the window, or the
      in-window pass ratio is below :data:`OPERATING_THRESHOLD`;
    - ``operating`` — passing, ratio >= threshold across sufficient distinct
      runs and days, and the check is outcome-assured;
    - ``structural_evidence_only`` — what a structural (file-presence /
      string-search) check earns instead of ``operating``: the artifact is
      present, which is structural evidence, not proof the control operates.
    """

    rows = 0
    passes = 0
    run_keys: set[str] = set()
    days: set[str] = set()
    for entry in window_entries(entries, now=now, window_days=window_days):
        if entry.get("control_id") != control_id:
            continue
        rows += 1
        if entry.get("passing"):
            passes += 1
        run_keys.add(_entry_run_key(entry))
        day = _entry_day(entry)
        if day:
            days.add(day)
    ratio = (passes / rows) if rows else 0.0
    distinct_runs = len(run_keys)
    distinct_run_days = len(days)

    if not current_pass:
        verdict = "failing"
    elif (
        distinct_runs < MIN_RUNS_PER_CONTROL
        or distinct_run_days < MIN_OBSERVATION_DAYS
        or ratio < OPERATING_THRESHOLD
    ):
        verdict = "insufficient_history"
    elif assurance != "outcome" or structural_only:
        verdict = "structural_evidence_only"
    else:
        verdict = "operating"
    return {
        "rows_in_window": rows,
        "passes_in_window": passes,
        "distinct_runs": distinct_runs,
        "distinct_run_days": distinct_run_days,
        "pass_ratio": round(ratio, 4),
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
    run_id: str = ""

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
    run_id: str | None = None,
) -> AuditResult:
    """Run one control-readiness pass and persist history + status.json.

    One execution is ONE run: every history line it appends carries the same
    unique ``run_id``, and ``distinct_runs`` counts run ids, never rows.
    """

    repo_root = Path(repo_root).expanduser().resolve()
    hermes_root = Path(hermes_root).expanduser()
    catalog = tuple(controls) if controls is not None else all_controls()
    now_iso = now or utc_now_iso()
    now_dt = parse_iso(now_iso) or datetime.now(timezone.utc)
    run_id = run_id or new_run_id(now_iso)

    results: dict[str, ControlResult] = {}
    new_lines: list[dict[str, Any]] = []
    for control in catalog:
        result = run_control(control, repo_root, hermes_root)
        results[control.control_id] = result
        new_lines.append(
            {
                "ts": now_iso,
                "run_id": run_id,
                "event": "check",
                "control_id": control.control_id,
                "passing": result.passing,
                "evidence": result.evidence,
            }
        )

    append_history(hermes_root, new_lines)
    entries = load_history(hermes_root)

    control_docs: list[dict[str, Any]] = []
    for control in catalog:
        result = results[control.control_id]
        evidence_stats = evidence_for(
            entries,
            control.control_id,
            now=now_dt,
            window_days=window_days,
            current_pass=result.passing,
            assurance=control.assurance,
            structural_only=bool(result.details.get("structural_only")),
        )
        control_docs.append(
            {
                "control_id": control.control_id,
                "tsc_id": control.tsc_id,
                "title": control.title,
                "category": control.category,
                "assurance": control.assurance,
                "control_objective": control.control_objective,
                "owner": control.owner,
                "frequency": control.frequency,
                "evidence_source": control.evidence_source,
                "passing": result.passing,
                "evidence": result.evidence,
                "details": result.details,
                **evidence_stats,
            }
        )

    in_window = window_entries(entries, now=now_dt, window_days=window_days)
    run_keys = {_entry_run_key(entry) for entry in in_window}
    day_keys = {day for entry in in_window if (day := _entry_day(entry))}
    stamps = [s for entry in in_window if (s := parse_iso(entry.get("ts")))]
    distinct_runs = len(run_keys)
    distinct_run_days = len(day_keys)
    days_of_history = (
        min(window_days, max(0, (now_dt - min(stamps)).days)) if stamps else 0
    )

    thresholds_met = (
        distinct_run_days >= MIN_OBSERVATION_DAYS and distinct_runs >= MIN_RUNS
    )
    if distinct_run_days >= window_days:
        evidence_period_status = "covers_window"
    elif thresholds_met:
        evidence_period_status = "partial"
    else:
        evidence_period_status = "insufficient"

    summary = {
        "total": len(control_docs),
        "passing": sum(1 for c in control_docs if c["passing"]),
        "failing": sum(1 for c in control_docs if not c["passing"]),
        "operating": sum(1 for c in control_docs if c["verdict"] == "operating"),
        "structural_evidence_only": sum(
            1 for c in control_docs if c["verdict"] == "structural_evidence_only"
        ),
        "insufficient_history": sum(
            1 for c in control_docs if c["verdict"] == "insufficient_history"
        ),
        "not_evidenced": len(NOT_EVIDENCED),
    }
    if distinct_runs == 0:
        overall = "not_assessed"
    elif summary["failing"] > 0:
        overall = "gaps"
    elif not thresholds_met:
        overall = "insufficient_evidence"
    else:
        overall = "ready_pending_attestation"

    status = {
        "generated_at": now_iso,
        "framework": FRAMEWORK,
        "assessment": "control_readiness_monitor",
        "attestation": False,
        "issued_by_cpa": False,
        "self_assessment": True,
        "evidence_period_status": evidence_period_status,
        "run_id": run_id,
        "distinct_runs": distinct_runs,
        "distinct_run_days": distinct_run_days,
        "days_of_history": days_of_history,
        "window_days": window_days,
        "thresholds": {
            "min_observation_days": MIN_OBSERVATION_DAYS,
            "min_runs": MIN_RUNS,
            "min_runs_per_control": MIN_RUNS_PER_CONTROL,
            "operating_ratio": OPERATING_THRESHOLD,
        },
        "overall": overall,
        "controls": control_docs,
        "not_evidenced": [dict(item) for item in NOT_EVIDENCED],
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
        run_id=run_id,
    )


def load_status(hermes_root: Path) -> dict[str, Any]:
    fallback = {
        "generated_at": None,
        "overall": "not_assessed",
        "attestation": False,
        "issued_by_cpa": False,
        "self_assessment": True,
        "evidence_period_status": "insufficient",
        "controls": [],
        "not_evidenced": [dict(item) for item in NOT_EVIDENCED],
        "summary": {},
    }
    try:
        value = json.loads(status_path(hermes_root).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return dict(fallback)
    if not isinstance(value, Mapping):
        return dict(fallback)
    return dict(value)
