"""Load LPOS benchmark fixtures as skill-evolution task records (Phase 3).

Turns the operating system's own 55 fixed fixtures (one per specialist, one per
Standing Operation) into task records the evolution loop can score. The
deterministic dimensions (schema validity, required sections, route correctness)
are scorable offline; the full behavioural score requires a live agent rollout
under a candidate skill, which is the integration point wired by the host
adapter. This module does the real, testable half: it loads every fixture and
exposes its assertions, so the scorer has ground truth to work against.
"""
from __future__ import annotations

import glob
import json
from pathlib import Path


def load_lpos_tasks(evals_dir: str | Path) -> list[dict]:
    tasks: list[dict] = []
    for f in sorted(glob.glob(str(Path(evals_dir) / "BENCH-*.json"))):
        d = json.loads(Path(f).read_text())
        tasks.append({
            "id": d["id"],
            "component": d.get("component_id"),
            "component_type": d.get("component_type"),
            "objective": d.get("objective", ""),
            "inputs": d.get("inputs", {}),
            "expected": d.get("expected", {}),
            "success_criteria": d.get("success_criteria", []),
            "failure_criteria": d.get("failure_criteria", []),
            "evaluation": d.get("evaluation", {}),
        })
    ids = [t["id"] for t in tasks]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate benchmark ids: fixture identity must be unique")
    if not tasks:
        raise ValueError(f"no BENCH-*.json fixtures under {evals_dir}")
    return tasks
