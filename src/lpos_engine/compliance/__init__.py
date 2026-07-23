"""LPOS Control Readiness Monitor (SO-025).

Codifies the AICPA 2017 Trust Services Criteria (2022 points of focus) as
data and runs a register of machine-checkable readiness controls against the
release checkout and the Hermes runtime root. It is a SELF-ASSESSMENT: it
never emits "compliant" or "effective" as self-determined states (audit
finding LPOS-01) — a SOC 2 Type 2 conclusion is only ever issued by an
independent CPA. Evidence history is a hash-chained, truly append-only ledger
(finding LPOS-08); structural checks are honestly labeled and capped below
"operating" (finding LPOS-02). Remediations are staged to a test environment
only -- never the live system -- and a self-contained HTML report is published.

Public surface:

- :data:`HANDLERS` -- Standing Operation step handlers for SO-025
  (``inventory_compliance_controls``, ``audit_compliance_controls``,
  ``stage_compliance_remediation``, ``publish_compliance_report``), each with
  the repo's ``StepHandler`` signature ``(Mapping[str, Any]) -> Mapping[str, Any]``.
- ``python -m lpos_engine.compliance audit|report|status|verify`` -- CLI.
- :func:`verify_history` -- ledger integrity check for doctor wiring.

State lives under ``<hermes root>/compliance/``: ``history.jsonl``
(hash-chained append-only ledger; explicit ``compact_history`` checkpoints and
archives, never silent trimming), ``history.head.json`` (truncation-detection
sidecar), ``status.json`` (stable contract), ``report.html``,
``remediations.json``, and ``staging/<run_id>/<control_id>/`` for staged fixes.
Adoption of a staged fix is record-only and approval-gated, matching the
distribution's ``external_action_default: record-only``.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from . import audit as audit_module
from . import remediation as remediation_module
from . import report as report_module
from .audit import (
    MIN_OBSERVATION_DAYS,
    MIN_RUNS,
    MIN_RUNS_PER_CONTROL,
    OPERATING_THRESHOLD,
    AuditResult,
    compact_history,
    load_status,
    run_audit,
    verify_history,
)
from .controls import (
    CONTROLS,
    CONTROLS_BY_ID,
    NOT_EVIDENCED,
    Control,
    ControlResult,
    all_controls,
)
from .criteria import CRITERIA, FRAMEWORK, OBSERVATION_WINDOW_DAYS
from .remediation import Remediation, adoption_plan, build_and_stage_remediations, stage_remediation
from .report import generate_report, render_report

__all__ = [
    "AuditResult",
    "CONTROLS",
    "CONTROLS_BY_ID",
    "CRITERIA",
    "Control",
    "ControlResult",
    "FRAMEWORK",
    "HANDLERS",
    "MIN_OBSERVATION_DAYS",
    "MIN_RUNS",
    "MIN_RUNS_PER_CONTROL",
    "NOT_EVIDENCED",
    "OBSERVATION_WINDOW_DAYS",
    "OPERATING_THRESHOLD",
    "Remediation",
    "compact_history",
    "verify_history",
    "adoption_plan",
    "all_controls",
    "audit_compliance_controls",
    "build_and_stage_remediations",
    "generate_report",
    "inventory_compliance_controls",
    "load_status",
    "publish_compliance_report",
    "render_report",
    "run_audit",
    "stage_compliance_remediation",
    "stage_remediation",
]


def _repo_root(context: Mapping[str, Any]) -> Path:
    root = context.get("repo_root") or os.environ.get("LPOS_REPO_ROOT") or "."
    return Path(root).expanduser().resolve()


def _hermes_root(context: Mapping[str, Any]) -> Path:
    root = (
        context.get("hermes_root")
        or os.environ.get("LPOS_HERMES_ROOT")
        or (Path.home() / ".hermes")
    )
    return Path(root).expanduser()


# --------------------------------------------------------------------------- SO-025


def inventory_compliance_controls(context: Mapping[str, Any]) -> Mapping[str, Any]:
    """SO-025 STEP-INVENTORY: the codified framework and control catalog."""

    series_counts: dict[str, int] = {}
    for control in all_controls():
        series_counts[control.tsc_id] = series_counts.get(control.tsc_id, 0) + 1
    return {
        "framework": FRAMEWORK,
        "window_days": OBSERVATION_WINDOW_DAYS,
        "criteria_count": len(CRITERIA),
        "control_count": len(all_controls()),
        "series_counts": series_counts,
        "controls": [
            {
                "control_id": control.control_id,
                "tsc_id": control.tsc_id,
                "title": control.title,
                "category": control.category,
            }
            for control in all_controls()
        ],
    }


def audit_compliance_controls(context: Mapping[str, Any]) -> Mapping[str, Any]:
    """SO-025 STEP-AUDIT: run every control, persist history + status.json."""

    result = run_audit(_repo_root(context), _hermes_root(context))
    summary = result.status.get("summary", {})
    return {
        "generated_at": result.generated_at,
        "run_id": result.run_id,
        "overall": result.overall,
        "attestation": False,
        "issued_by_cpa": False,
        "self_assessment": True,
        "evidence_period_status": result.status.get("evidence_period_status"),
        "distinct_runs": result.status.get("distinct_runs"),
        "distinct_run_days": result.status.get("distinct_run_days"),
        "summary": dict(summary),
        "failing": sorted(result.failing),
        "status_path": result.status_path,
        "history_path": result.history_path,
    }


def stage_compliance_remediation(context: Mapping[str, Any]) -> Mapping[str, Any]:
    """SO-025 STEP-REMEDIATE: stage test-environment fixes for failing controls."""

    repo_root = _repo_root(context)
    hermes_root = _hermes_root(context)
    run_id = str(context.get("run_id") or f"RUN-{audit_module.utc_now_iso().replace(':', '')}")

    audit_step = context.get("STEP-AUDIT") or {}
    failing_ids = list(audit_step.get("failing") or [])
    status = load_status(hermes_root)
    evidence_by_id = {
        str(c.get("control_id")): str(c.get("evidence", ""))
        for c in status.get("controls", [])
    }
    if not failing_ids:
        failing_ids = [
            str(c.get("control_id"))
            for c in status.get("controls", [])
            if not c.get("passing")
        ]

    failing: list[tuple[Control, str]] = []
    for control_id in failing_ids:
        control = CONTROLS_BY_ID.get(control_id)
        if control is not None:
            failing.append((control, evidence_by_id.get(control_id, "control failing")))

    plan = build_and_stage_remediations(
        failing, repo_root=repo_root, hermes_root=hermes_root, run_id=run_id
    )
    audit_module._atomic_write_json(
        audit_module.compliance_dir(hermes_root) / "remediations.json", plan
    )
    return plan


def publish_compliance_report(context: Mapping[str, Any]) -> Mapping[str, Any]:
    """SO-025 STEP-REPORT: write the self-contained HTML compliance report."""

    hermes_root = _hermes_root(context)
    status = load_status(hermes_root)
    plan = context.get("STEP-REMEDIATE") or report_module._load_remediation_plan(hermes_root)
    entries = audit_module.load_history(hermes_root)
    out_path = audit_module.compliance_dir(hermes_root) / "report.html"
    generate_report(
        status,
        list(plan.get("remediations", []) or []),
        entries,
        out_path,
        adoption=plan.get("adoption"),
    )
    return {
        "report_path": str(out_path),
        "status_path": str(audit_module.status_path(hermes_root)),
        "overall": str(status.get("overall", "gaps")),
    }


#: Handler registration map for the orchestrator: register these with the
#: StandingOperationRunner alongside the existing handlers.
HANDLERS: dict[str, Any] = {
    "inventory_compliance_controls": inventory_compliance_controls,
    "audit_compliance_controls": audit_compliance_controls,
    "stage_compliance_remediation": stage_compliance_remediation,
    "publish_compliance_report": publish_compliance_report,
}
