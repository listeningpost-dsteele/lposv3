"""Task records and a leak-proof train/validation/test split."""
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
    digest = hashlib.sha256(task_id.encode()).hexdigest()
    return int(digest[:8], 16) % 100


def load_tasks(path: str | Path) -> list[dict]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    ids = [task["id"] for task in data]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate task ids: task identity must be unique")
    return data


def split_tasks(tasks: list[dict]) -> Split:
    train: list[dict] = []
    val: list[dict] = []
    test: list[dict] = []
    for task in tasks:
        bucket = _bucket(task["id"])
        (train if bucket < 60 else val if bucket < 80 else test).append(task)
    split = Split(train, val, test)
    assert_no_leakage(split)
    return split


def assert_no_leakage(split: Split) -> None:
    train_ids = {task["id"] for task in split.train}
    val_ids = {task["id"] for task in split.val}
    test_ids = {task["id"] for task in split.test}
    if train_ids & val_ids or train_ids & test_ids or val_ids & test_ids:
        raise AssertionError("held-out leakage: a task appears in more than one split")
    if not split.val or not split.test:
        raise AssertionError("validation and test splits must be non-empty")
