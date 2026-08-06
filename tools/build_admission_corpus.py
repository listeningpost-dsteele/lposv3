#!/usr/bin/env python3
"""Generate all 103 admission suites and write them as packaged data.

Usage:
    python tools/build_admission_corpus.py

This is a deterministic generator. Running it multiple times against the
same charter inputs produces identical suites with identical hashes.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from lpos_engine.admission.generate import generate_all_suites


def main() -> int:
    suites = generate_all_suites()
    output_dir = ROOT / "src" / "lpos_engine" / "admission" / "data"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Track all task texts across ALL suites to detect generic duplication.
    all_tasks: dict[str, str] = {}  # task_text_lower -> suite_id

    suite_summaries = []
    for suite in suites:
        output_path = output_dir / f"{suite.suite_id}.json"
        data = suite.to_dict()
        output_path.write_text(
            json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        # Check for cross-suite task duplication.
        for case in suite.cases:
            task_key = case.task.strip().lower()
            if task_key in all_tasks:
                print(
                    f"WARNING: duplicate task text between {all_tasks[task_key]} "
                    f"and {suite.suite_id} (case {case.case_id})",
                    file=sys.stderr,
                )
            all_tasks[task_key] = suite.suite_id

        suite_summaries.append({
            "suite_id": suite.suite_id,
            "specialist_id": suite.specialist_id,
            "specialist_name": suite.specialist_name,
            "guild": suite.guild,
            "case_count": len(suite.cases),
            "content_sha256": suite.content_hash,
        })

    # Write index.
    index = {
        "suite_count": len(suites),
        "specialist_count": len(suites),
        "suites": sorted(suite_summaries, key=lambda s: s["suite_id"]),
    }
    index_path = output_dir / "index.json"
    index_path.write_text(
        json.dumps(index, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(f"Generated {len(suites)} admission suites in {output_dir}")
    print(f"Index: {index_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
