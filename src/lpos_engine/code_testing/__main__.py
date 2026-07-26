"""CLI: ``python -m lpos_engine.code_testing classify|gauntlet``.

Reads a JSON document from a ``--file`` path or from stdin and prints the result as
indented JSON. ``classify`` expects a signals object (or ``{"signals": {...}}``);
``gauntlet`` expects ``{"level": ..., "gate_results": {...}}`` and optionally
``{"need_to_change_evidence": {...}}``.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from . import classify, evaluate_gauntlet, need_to_change_gate


def _load(path: str | None) -> Any:
    text = sys.stdin.read() if not path or path == "-" else open(path, encoding="utf-8").read()
    if not text.strip():
        return {}
    return json.loads(text)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m lpos_engine.code_testing")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("classify", "gauntlet"):
        p = sub.add_parser(name)
        p.add_argument("--file", "-f", default=None, help="JSON input file (default: stdin)")
    args = parser.parse_args(argv)

    try:
        document = _load(args.file)
    except (OSError, ValueError) as exc:
        print(json.dumps({"error": type(exc).__name__, "message": str(exc)}), file=sys.stderr)
        return 1

    if args.command == "classify":
        signals = document.get("signals") if isinstance(document, dict) and "signals" in document else document
        result: Any = classify(signals if isinstance(signals, dict) else {})
    else:  # gauntlet
        document = document if isinstance(document, dict) else {}
        level = document.get("level", "STANDARD")
        gate_results = document.get("gate_results") or {}
        result = {
            "need_to_change": need_to_change_gate(document.get("need_to_change_evidence") or {}),
            "gauntlet": evaluate_gauntlet(level, gate_results),
        }

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
