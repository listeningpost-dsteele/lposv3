"""LPOS Code Testing Guild: the executable criticality-weighted test gauntlet.

This package is the executable core of the Code Testing Guild. It codifies the Code
Testing Gauntlet Standard so the operating system enforces it deterministically rather
than by prompt instruction alone:

* :func:`classify` -- deterministic, total criticality classification.
* :mod:`gauntlet` -- the tier -> required-gate table, the Need-to-Change Gate, and the
  release-decision evaluator (a required gate that did not run, or a failing/flaky gate,
  is a REJECT; a green unit suite alone cannot approve STANDARD+).
* :func:`build_evidence_packet` -- the release evidence packet with the independence
  rule (a producer cannot audit its own release).
* :mod:`manifest` -- a tolerant, dependency-free manifest loader that never invents a
  build, test, lint, or type-check command.
* :data:`HANDLERS` -- Standing Operation step handlers for SO-027, SO-028, and SO-029.
"""

from __future__ import annotations

from .criticality import classify
from .evidence import build_evidence_packet
from .gauntlet import (
    GATES_ADDED,
    TIER_ORDER,
    evaluate_gauntlet,
    extra_gates_for,
    need_to_change_gate,
    normalize_level,
    required_gates,
)
from .handlers import HANDLERS
from .manifest import load_commands, load_manifest, manifest_commands, parse_manifest

__all__ = [
    "classify",
    "build_evidence_packet",
    "GATES_ADDED",
    "TIER_ORDER",
    "evaluate_gauntlet",
    "extra_gates_for",
    "need_to_change_gate",
    "normalize_level",
    "required_gates",
    "HANDLERS",
    "load_commands",
    "load_manifest",
    "manifest_commands",
    "parse_manifest",
]
