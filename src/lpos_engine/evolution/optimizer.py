"""Propose bounded edits from repeated failures on the TRAIN split only.

The optimizer never sees validation or test. It looks at which real violations
the current skill misses across training tasks, and proposes adding the rules
that would catch the most-repeated misses, up to the edit budget. "Repeated,
not anecdotal" is enforced by `min_support`: a fix must be justified by more than
one failing task before it is proposed.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from .scorer import GOOD_RULES, real_violations
from .skill import Edit, Skill


@dataclass(frozen=True)
class Proposal:
    edits: tuple[Edit, ...]
    evidence: dict          # rule -> number of training tasks that motivated it


def propose(skill: Skill, train: list[dict], *, edit_budget: int = 3,
            min_support: int = 2) -> Proposal:
    missed = Counter()
    for task in train:
        gaps = real_violations(task["text"]) - set(skill.rules)
        for rule in gaps:
            missed[rule] += 1
    ranked = [(r, n) for r, n in missed.most_common() if n >= min_support and r in GOOD_RULES]
    chosen = ranked[:edit_budget]
    edits = tuple(
        Edit("add", r, f"missed on {n} training tasks") for r, n in chosen
    )
    return Proposal(edits=edits, evidence={r: n for r, n in chosen})
