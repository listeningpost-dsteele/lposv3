#!/usr/bin/env python3
"""Minimal executable example for the SubprocessModelAdapter protocol.

This is deterministic demonstration code. It does not call a model provider.
"""

from __future__ import annotations

import json
import sys


def main() -> int:
    request = json.load(sys.stdin)
    operation = request.get("operation")
    if operation == "create_artifact":
        task = request["task"]
        context = request["context"]
        response = {
            "content": (
                "# Example model-host artifact\n\n"
                f"Task: {task['task_id']}\n\n"
                f"Instruction: {task['principal_instruction']}\n\n"
                f"Context: {context['bundle_id']}"
            ),
            "media_type": "text/markdown",
            "evidence": [f"context:{context['bundle_hash']}"],
            "assumptions": [],
            "adapter_metadata": {"host": "example", "deterministic": True},
        }
    elif operation == "review":
        context = request["context"]
        envelope = request["review_envelope"]
        response = {
            "decision": "PASS",
            "isolation": f"fresh_context:{context['bundle_id']}",
            "recomputed": "contract, artifact hash, and intended outcome",
            "contract_violations": [],
            "truth": ["The artifact hash and supplied envelope were recomputed."],
            "reasoning": ["No deterministic contradiction was found."],
            "craft": ["No deterministic craft marker failed."],
            "outcome": [f"Fit for: {envelope['intended_outcome']}"],
            "regressions": [],
            "required_corrections": [],
            "strengths_to_preserve": ["Preserve the reviewed artifact hash."],
            "evidence_reviewed": envelope.get("verification_evidence", []),
        }
    else:
        raise ValueError(f"unsupported operation: {operation!r}")
    json.dump(response, sys.stdout, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
