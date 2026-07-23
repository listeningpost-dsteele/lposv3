"""On-demand CLI for the LPOS control readiness monitor (SO-025).

Usage:

    python -m lpos_engine.compliance audit    # run every control, update status.json
    python -m lpos_engine.compliance report   # stage fixes for failures + write report.html
    python -m lpos_engine.compliance status   # print current status.json
    python -m lpos_engine.compliance verify   # verify the hash-chained evidence ledger

Options: ``--root`` for the Hermes root (default $LPOS_HERMES_ROOT or
~/.hermes), ``--repo`` for the release checkout (default $LPOS_REPO_ROOT or
the current directory).

Exit codes: 0 = command completed (even with gaps -- cron must not flap);
1 = verify found ledger tampering; 2 = status requested but no audit has
ever run.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from . import (
    audit_compliance_controls,
    publish_compliance_report,
    stage_compliance_remediation,
)
from .audit import load_status, status_path, verify_history


def _print(value) -> None:
    print(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False))


def _context(args: argparse.Namespace) -> dict[str, str]:
    context: dict[str, str] = {}
    if args.repo:
        context["repo_root"] = str(Path(args.repo).expanduser())
    if args.root:
        context["hermes_root"] = str(Path(args.root).expanduser())
    return context


def cmd_audit(args: argparse.Namespace) -> int:
    _print(dict(audit_compliance_controls(_context(args))))
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    context = _context(args)
    plan = stage_compliance_remediation(context)
    published = publish_compliance_report({**context, "STEP-REMEDIATE": plan})
    _print({"remediation": dict(plan), "report": dict(published)})
    return 0


def _root(args: argparse.Namespace) -> Path:
    context = _context(args)
    return Path(
        context.get("hermes_root")
        or os.environ.get("LPOS_HERMES_ROOT")
        or (Path.home() / ".hermes")
    ).expanduser()


def cmd_status(args: argparse.Namespace) -> int:
    root = _root(args)
    if not status_path(root).is_file():
        print(f"no compliance status at {status_path(root)}; run audit first", file=sys.stderr)
        return 2
    _print(load_status(root))
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    result = verify_history(_root(args))
    _print(result)
    return 0 if result.get("ok") else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m lpos_engine.compliance",
        description="LPOS control readiness monitor (self-assessment, not an attestation)",
    )
    parser.add_argument("--root", help="Hermes root (default: $LPOS_HERMES_ROOT or ~/.hermes)")
    parser.add_argument("--repo", help="release checkout (default: $LPOS_REPO_ROOT or .)")
    sub = parser.add_subparsers(dest="command", required=True)

    audit_cmd = sub.add_parser("audit", help="run every control and update status.json")
    audit_cmd.set_defaults(func=cmd_audit)

    report_cmd = sub.add_parser(
        "report", help="stage remediations for current failures and write report.html"
    )
    report_cmd.set_defaults(func=cmd_report)

    status_cmd = sub.add_parser("status", help="print the current status.json")
    status_cmd.set_defaults(func=cmd_status)

    verify_cmd = sub.add_parser(
        "verify",
        help="verify the hash-chained evidence ledger (exit 1 on tampering)",
    )
    verify_cmd.set_defaults(func=cmd_verify)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
