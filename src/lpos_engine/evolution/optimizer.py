"""Propose bounded edits from repeated failures on the train split only."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from .scorer import GOOD_RULES, real_violations
from .skill import Edit, Skill


@dataclass(frozen=True)
class Proposal:
    edits: tuple[Edit, ...]
    evidence: dict


def propose(skill: Skill, train: list[dict], *, edit_budget: int = 3, min_support: int = 2) -> Proposal:
    missed = Counter()
    for task in train:
        gaps = real_violations(task["text"]) - set(skill.rules)
        for rule in gaps:
            missed[rule] += 1
    ranked = [(rule, count) for rule, count in missed.most_common() if count >= min_support and rule in GOOD_RULES]
    chosen = ranked[:edit_budget]
    edits = tuple(Edit("add", rule, f"missed on {count} training tasks") for rule, count in chosen)
    return Proposal(edits=edits, evidence={rule: count for rule, count in chosen})
