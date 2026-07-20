"""Load LPOS benchmark fixtures as skill-evolution task records."""
from __future__ import annotations

import glob
import json
from pathlib import Path


def load_lpos_tasks(evals_dir: str | Path) -> list[dict]:
    tasks: list[dict] = []
    for fixture in sorted(glob.glob(str(Path(evals_dir) / "BENCH-*.json"))):
        data = json.loads(Path(fixture).read_text(encoding="utf-8"))
        tasks.append(
            {
                "id": data["id"],
                "component": data.get("component_id"),
                "component_type": data.get("component_type"),
                "objective": data.get("objective", ""),
                "inputs": data.get("inputs", {}),
                "expected": data.get("expected", {}),
                "success_criteria": data.get("success_criteria", []),
                "failure_criteria": data.get("failure_criteria", []),
                "evaluation": data.get("evaluation", {}),
            }
        )
    ids = [task["id"] for task in tasks]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate benchmark ids: fixture identity must be unique")
    if not tasks:
        raise ValueError(f"no BENCH-*.json fixtures under {evals_dir}")
    return tasks
