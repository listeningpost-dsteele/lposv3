"""LPOS Connector Health Monitor (SO-023).

Discovers everything LPOS runs on, audits it hourly, publishes
``<hermes root>/monitor/status.json``, and emails the owner on
offline/recovery transitions.  Stdlib only; short-lived job, never a daemon.

Public surface:

- :data:`HANDLERS` — Standing Operation step handlers for SO-023
  (``discover_connector_inventory``, ``audit_connectors``,
  ``alert_connector_transitions``), each with the repo's ``StepHandler``
  signature ``(Mapping[str, Any]) -> Mapping[str, Any]``.
- ``python -m lpos_engine.monitor audit`` — on-demand CLI (see ``__main__``).
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from . import alert as alert_module
from . import approved as approved_module
from . import audit as audit_module
from . import inventory as inventory_module
from .alert import CommandTransport, SMTPTransport, Transport, run_alert_cycle
from .approved import approved_checks_path, load_approved_checks
from .audit import load_status, run_audit
from .checks import CHECKS, CheckNotConfigured, CheckResult, resolve_check, run_check, run_checks
from .inventory import discover, hermes_root, load_inventory, merge, refresh_inventory

__all__ = [
    "CHECKS",
    "CheckNotConfigured",
    "CheckResult",
    "CommandTransport",
    "HANDLERS",
    "SMTPTransport",
    "Transport",
    "approved_checks_path",
    "load_approved_checks",
    "alert_connector_transitions",
    "audit_connectors",
    "discover",
    "discover_connector_inventory",
    "hermes_root",
    "load_inventory",
    "load_status",
    "merge",
    "refresh_inventory",
    "resolve_check",
    "run_alert_cycle",
    "run_audit",
    "run_check",
    "run_checks",
]


def _root_from(context: Mapping[str, Any]) -> Path:
    value = context.get("hermes_root")
    return Path(str(value)).expanduser() if value else hermes_root()


def discover_connector_inventory(context: Mapping[str, Any]) -> Mapping[str, Any]:
    """SO-023 STEP-DISCOVER: refresh the connector inventory."""

    root = _root_from(context)
    repo_config = context.get("repo_config")
    entries = inventory_module.refresh_inventory(
        root, Path(str(repo_config)) if repo_config else None
    )
    return {
        "inventory_path": str(inventory_module.inventory_path(root)),
        "connector_count": len(entries),
        "connector_ids": [str(entry["id"]) for entry in entries],
        "muted": [str(entry["id"]) for entry in entries if entry.get("muted")],
    }


def audit_connectors(context: Mapping[str, Any]) -> Mapping[str, Any]:
    """SO-023 STEP-AUDIT: check every connector, persist state and status."""

    root = _root_from(context)
    summary = audit_module.run_audit(root, refresh=False)
    # run_audit returns plain JSON-compatible data; pass it through.
    return summary


def alert_connector_transitions(context: Mapping[str, Any]) -> Mapping[str, Any]:
    """SO-023 STEP-ALERT: send transition/recovery/reminder emails.

    Raises when messages were pending but could not be delivered, after the
    loud ALERT-UNDELIVERED.json fallback has been written — so the workflow
    run records the failure instead of swallowing it.
    """

    root = _root_from(context)
    result = alert_module.run_alert_cycle(root)
    if result["attempted"] and not result["delivered"]:
        raise RuntimeError(
            "alert delivery failed; see "
            + result.get("undelivered_path", str(alert_module.undelivered_path(root)))
        )
    return result


#: Handler registration map for the orchestrator: register these with the
#: StandingOperationRunner alongside the existing handlers.
HANDLERS: dict[str, Any] = {
    "discover_connector_inventory": discover_connector_inventory,
    "audit_connectors": audit_connectors,
    "alert_connector_transitions": alert_connector_transitions,
}
