"""Validation gate: accept a candidate skill only if it beats the current one
on held-out tasks.

Behaviourally identical to Microsoft SkillOpt's ``skillopt.evaluation.gate``
(MIT-licensed reference implementation, github.com/microsoft/SkillOpt). We
reimplement rather than depend so the LPOS pilot stays self-contained and can be
audited against LPOS's own standards. The gate is the point of the whole system:
a plausible edit that does not measurably improve the held-out score is rejected.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GateResult:
    action: str
    accepted: bool
    current_score: float
    candidate_score: float
    reason: str


def evaluate_gate(*, current_score: float, candidate_score: float, min_gain: float = 0.0) -> GateResult:
    """Strictly-better gate. A tie is a rejection: an edit must earn its place.

    min_gain lets the caller demand a margin so noise-sized wins do not accumulate
    as instruction bloat.
    """
    if candidate_score > current_score + min_gain:
        return GateResult(
            "accept_new_best",
            True,
            current_score,
            candidate_score,
            f"candidate {candidate_score:.4f} beat current {current_score:.4f} "
            f"by more than min_gain {min_gain:.4f}",
        )
    return GateResult(
        "reject",
        False,
        current_score,
        candidate_score,
        f"candidate {candidate_score:.4f} did not beat current {current_score:.4f} + min_gain {min_gain:.4f}",
    )
