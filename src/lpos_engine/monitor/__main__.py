"""On-demand CLI for the connector health monitor.

Usage:

    python -m lpos_engine.monitor audit      # discover + audit + alert
    python -m lpos_engine.monitor audit --no-alert
    python -m lpos_engine.monitor discover   # refresh inventory only
    python -m lpos_engine.monitor status     # print current status.json

Exit codes: 0 = audit completed (even if degraded — cron must not flap);
2 = alerts were pending but could not be delivered (ALERT-UNDELIVERED.json
written).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import alert as alert_module
from . import audit as audit_module
from . import inventory as inventory_module


def _print(value) -> None:
    print(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False))


def _root(args: argparse.Namespace) -> Path | None:
    return Path(args.root).expanduser() if args.root else None


def cmd_audit(args: argparse.Namespace) -> int:
    root = _root(args)
    summary = audit_module.run_audit(root, timeout=args.timeout)
    if args.no_alert:
        _print(summary)
        return 0
    alert_result = alert_module.run_alert_cycle(root)
    _print({"audit": summary, "alerts": alert_result})
    if alert_result["attempted"] and not alert_result["delivered"]:
        print(
            "ALERT DELIVERY FAILED — see "
            + alert_result.get("undelivered_path", str(alert_module.undelivered_path(root))),
            file=sys.stderr,
        )
        return 2
    return 0


def cmd_discover(args: argparse.Namespace) -> int:
    root = _root(args)
    entries = inventory_module.refresh_inventory(root)
    _print(
        {
            "inventory_path": str(inventory_module.inventory_path(root)),
            "connectors": entries,
        }
    )
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    _print(audit_module.load_status(_root(args)))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m lpos_engine.monitor",
        description="LPOS connector health monitor",
    )
    parser.add_argument("--root", help="Hermes root (default: $LPOS_HERMES_ROOT or ~/.hermes)")
    sub = parser.add_subparsers(dest="command", required=True)

    audit_cmd = sub.add_parser("audit", help="run a full audit and send any due alerts")
    audit_cmd.add_argument("--no-alert", action="store_true", help="audit only; skip alerting")
    audit_cmd.add_argument("--timeout", type=float, default=15.0, help="per-check timeout seconds")
    audit_cmd.set_defaults(func=cmd_audit)

    discover_cmd = sub.add_parser("discover", help="refresh and print the connector inventory")
    discover_cmd.set_defaults(func=cmd_discover)

    status_cmd = sub.add_parser("status", help="print the current status.json")
    status_cmd.set_defaults(func=cmd_status)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
