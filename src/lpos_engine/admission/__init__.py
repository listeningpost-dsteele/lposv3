"""Behavioral admission test system for LPOS 4.7 Specialist candidates.

This package implements deterministic prepare, blind, score, and verify phases
for admitting active-candidate Specialists.  It is stdlib-first, provider-free,
and never silently activates a Specialist.
"""

from __future__ import annotations

from .harness import (
    AssignmentMap,
    BaselinePrompt,
    EvidenceRecord,
    ScoringJudgment,
    blind_packets,
    build_execution_matrix,
    prepare_suite,
    score_judgments,
    verify_admission_record,
    PASS_POLICY,
    PASS_POLICY_SHA256,
    BASELINE_PROMPT_SHA256,
    MINIMUM_REPETITIONS,
)
from .models import (
    AdmissionSuite,
    AdmissionCase,
    RUBRIC_DIMENSIONS,
    VALID_DISPOSITIONS,
)

__all__ = [
    "AdmissionCase",
    "AdmissionSuite",
    "AssignmentMap",
    "BaselinePrompt",
    "BASELINE_PROMPT_SHA256",
    "EvidenceRecord",
    "MINIMUM_REPETITIONS",
    "PASS_POLICY",
    "PASS_POLICY_SHA256",
    "RUBRIC_DIMENSIONS",
    "ScoringJudgment",
    "VALID_DISPOSITIONS",
    "blind_packets",
    "build_execution_matrix",
    "prepare_suite",
    "score_judgments",
    "verify_admission_record",
]
