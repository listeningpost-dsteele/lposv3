"""Task records and a leak-proof train/validation/test split.

Held-out integrity is the difference between a real gate and a fake one. Splits
are assigned by a stable hash of the task id, so a task lands in exactly one
split and re-runs are deterministic. `assert_no_leakage` is called by the
harness and the tests; if it ever raises, the gate's held-out score is
meaningless and the run must stop.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Split:
    train: list[dict]
    val: list[dict]
    test: list[dict]


def _bucket(task_id: str) -> int:
    h = hashlib.sha256(task_id.encode()).hexdigest()
    return int(h[:8], 16) % 100


def load_tasks(path: str | Path) -> list[dict]:
    data = json.loads(Path(path).read_text())
    ids = [t["id"] for t in data]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate task ids: task identity must be unique")
    return data


def split_tasks(tasks: list[dict]) -> Split:
    train, val, test = [], [], []
    for t in tasks:
        b = _bucket(t["id"])
        (train if b < 60 else val if b < 80 else test).append(t)
    s = Split(train, val, test)
    assert_no_leakage(s)
    return s


def assert_no_leakage(split: Split) -> None:
    tr = {t["id"] for t in split.train}
    va = {t["id"] for t in split.val}
    te = {t["id"] for t in split.test}
    if tr & va or tr & te or va & te:
        raise AssertionError("held-out leakage: a task appears in more than one split")
    if not split.val or not split.test:
        raise AssertionError("validation and test splits must be non-empty")
