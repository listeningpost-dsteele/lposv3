"""The evolution loop: baseline, propose on train, gate on validation, report on
test, stage only if accepted. No live writes anywhere in this module.
"""
from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass

from .gate import evaluate_gate
from .optimizer import propose
from .scorer import score_skill
from .skill import Skill, apply_edits
from .tasks import Split, assert_no_leakage


@dataclass
class RunReport:
    run_id: str
    skill_name: str
    baseline_val: float
    candidate_val: float
    baseline_test: float
    candidate_test: float
    accepted: bool
    gate_reason: str
    applied_edits: list
    proposal_evidence: dict


def _run_id(skill: Skill, split: Split) -> str:
    ids = "".join(sorted(t["id"] for t in split.train + split.val + split.test))
    seed = f"{skill.name}:{','.join(skill.rules)}:{ids}"
    return "RUN-" + hashlib.sha256(seed.encode()).hexdigest()[:12]


def evolve(skill: Skill, split: Split, *, edit_budget: int = 3,
           min_support: int = 2, min_gain: float = 0.0) -> tuple[Skill, RunReport]:
    assert_no_leakage(split)  # a run on a leaking split is invalid, not just wrong

    baseline_val = score_skill(skill.rules, split.val)
    baseline_test = score_skill(skill.rules, split.test)

    proposal = propose(skill, split.train, edit_budget=edit_budget, min_support=min_support)
    candidate = apply_edits(skill, proposal.edits)
    candidate_val = score_skill(candidate.rules, split.val)

    gate = evaluate_gate(current_score=baseline_val,
                         candidate_score=candidate_val, min_gain=min_gain)

    accepted_skill = candidate if gate.accepted else skill
    report = RunReport(
        run_id=_run_id(skill, split),
        skill_name=skill.name,
        baseline_val=round(baseline_val, 4),
        candidate_val=round(candidate_val, 4),
        baseline_test=round(baseline_test, 4),
        candidate_test=round(score_skill(accepted_skill.rules, split.test), 4),
        accepted=gate.accepted,
        gate_reason=gate.reason,
        applied_edits=[asdict_edit(e) for e in (proposal.edits if gate.accepted else ())],
        proposal_evidence=proposal.evidence,
    )
    return accepted_skill, report


def asdict_edit(edit) -> dict:
    return {"op": edit.op, "rule": edit.rule, "rationale": edit.rationale}


def gate_candidate(skill: Skill, candidate: Skill, split: Split, *,
                   min_gain: float = 0.0):
    """Gate an externally-supplied candidate (used to test harmful edits)."""
    assert_no_leakage(split)
    base = score_skill(skill.rules, split.val)
    cand = score_skill(candidate.rules, split.val)
    return evaluate_gate(current_score=base, candidate_score=cand, min_gain=min_gain)
