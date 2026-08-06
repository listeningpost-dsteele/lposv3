"""CLI entry point for `lpos admission` subcommands.

Provides four deterministic file transformers:
  prepare  - validate a suite and emit a frozen run manifest
  blind    - create blinded evaluator packets from outputs (A/B pairs)
  score    - score frozen judgments after unblinding
  verify   - verify a draft admission record
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from ..canonical import canonical_json, digest, text_digest
from ..errors import ValidationError
from .harness import (
    AssignmentMap,
    PASS_POLICY_SHA256,
    ScoringJudgment,
    blind_packets,
    prepare_suite,
    score_judgments,
    verify_admission_record,
)
from .models import AdmissionSuite


def _load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write_json(path: str | Path, value: Any) -> None:
    Path(path).write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _load_suite(path: str | Path) -> AdmissionSuite:
    data = _load_json(path)
    return AdmissionSuite.from_dict(data)


def cmd_prepare(args: argparse.Namespace) -> int:
    """Prepare a suite: validate and emit a frozen run manifest."""
    suite = _load_suite(args.suite)
    manifest = prepare_suite(
        suite,
        frozen_timestamp=args.frozen_timestamp,
        repetitions=args.repetitions,
    )
    output_path = args.output or Path(args.suite).with_suffix(".manifest.json")
    _write_json(output_path, manifest)
    print(canonical_json({
        "status": "prepared",
        "suite_id": manifest["suite_id"],
        "manifest_sha256": manifest["manifest_sha256"],
        "run_unit_count": manifest["run_unit_count"],
        "output": str(output_path),
    }))
    return 0


def cmd_blind(args: argparse.Namespace) -> int:
    """Create blinded evaluator packets from candidate and baseline outputs."""
    manifest = _load_json(args.manifest)
    candidate_outputs = _load_json(args.candidate_outputs)
    baseline_outputs = _load_json(args.baseline_outputs)

    assignment_map, packets = blind_packets(
        manifest,
        candidate_outputs,
        baseline_outputs,
        seed=args.seed,
    )

    _write_json(args.assignment_map, assignment_map.to_dict())
    _write_json(args.packets, {"packets": packets})

    print(canonical_json({
        "status": "blinded",
        "packet_count": len(packets),
        "assignment_map": str(args.assignment_map),
        "packets": str(args.packets),
    }))
    return 0


def cmd_score(args: argparse.Namespace) -> int:
    """Score frozen judgments after unblinding. Emits a draft admission record."""
    manifest = _load_json(args.manifest)
    judgments_data = _load_json(args.judgments)
    assignment_map = AssignmentMap.from_dict(_load_json(args.assignment_map))

    judgments = [ScoringJudgment.from_dict(j) for j in judgments_data["judgments"]]

    # Freeze judgments: compute and store the freeze hash BEFORE scoring.
    freeze_hash = digest([j.to_dict() for j in judgments])

    record = score_judgments(judgments, assignment_map, manifest)
    record["judgment_freeze_sha256"] = freeze_hash

    _write_json(args.output, record)
    print(canonical_json({
        "status": "scored",
        "decision": record["decision"],
        "activated": record["activated"],
        "outputs_complete": record["outputs_complete"],
        "output": str(args.output),
    }))
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    """Verify a draft admission record is consistent and untampered."""
    manifest = _load_json(args.manifest)
    record = _load_json(args.record)
    judgments_data = _load_json(args.judgments)
    assignment_map = AssignmentMap.from_dict(_load_json(args.assignment_map))

    judgments = [ScoringJudgment.from_dict(j) for j in judgments_data["judgments"]]

    result = verify_admission_record(record, manifest, judgments, assignment_map)
    _write_json(args.output, result)

    print(canonical_json({
        "status": "verified" if result["verified"] else "failed",
        "failures": result["failures"],
        "output": str(args.output),
    }))
    return 0 if result["verified"] else 1


def add_admission_parser(subparsers: argparse._SubParsersAction) -> None:
    """Add the `admission` subcommand and its four sub-actions."""

    admission = subparsers.add_parser(
        "admission",
        help="deterministic Specialist admission test harness (prepare, blind, score, verify)",
    )
    admission_sub = admission.add_subparsers(dest="admission_action", required=True)

    prepare = admission_sub.add_parser("prepare", help="validate a suite and emit a frozen run manifest")
    prepare.add_argument("--suite", required=True, type=Path, help="path to the admission suite JSON")
    prepare.add_argument("--output", type=Path, default=None, help="output manifest path")
    prepare.add_argument(
        "--frozen-timestamp",
        default="1970-01-01T00:00:00Z",
        help="caller-supplied frozen timestamp for deterministic output",
    )
    prepare.add_argument(
        "--repetitions",
        type=int,
        default=3,
        help="number of repetitions per case per arm (minimum 3)",
    )
    prepare.set_defaults(func=cmd_prepare)

    blind = admission_sub.add_parser("blind", help="create blinded evaluator packets")
    blind.add_argument("--manifest", required=True, type=Path, help="prepared manifest path")
    blind.add_argument("--candidate-outputs", required=True, type=Path, help="JSON map of case_id to candidate output")
    blind.add_argument("--baseline-outputs", required=True, type=Path, help="JSON map of case_id to baseline output")
    blind.add_argument("--seed", required=True, help="private blinding seed")
    blind.add_argument("--assignment-map", required=True, type=Path, help="output path for the private assignment map")
    blind.add_argument("--packets", required=True, type=Path, help="output path for evaluator packets")
    blind.set_defaults(func=cmd_blind)

    score = admission_sub.add_parser("score", help="score frozen judgments and emit a draft admission record")
    score.add_argument("--manifest", required=True, type=Path, help="prepared manifest path")
    score.add_argument("--judgments", required=True, type=Path, help="JSON of frozen scoring judgments")
    score.add_argument("--assignment-map", required=True, type=Path, help="private assignment map")
    score.add_argument("--output", required=True, type=Path, help="output draft admission record path")
    score.set_defaults(func=cmd_score)

    verify = admission_sub.add_parser("verify", help="verify a draft admission record")
    verify.add_argument("--manifest", required=True, type=Path, help="prepared manifest path")
    verify.add_argument("--record", required=True, type=Path, help="draft admission record")
    verify.add_argument("--judgments", required=True, type=Path, help="frozen scoring judgments")
    verify.add_argument("--assignment-map", required=True, type=Path, help="private assignment map")
    verify.add_argument("--output", required=True, type=Path, help="output verification result")
    verify.set_defaults(func=cmd_verify)
