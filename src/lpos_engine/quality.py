"""Deterministic customer-facing quality gate.

The gate validates evidence, binds independent review to the exact artifact hash,
and rejects publication when required proof is missing or any blocker remains.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from .errors import ValidationError

REQUIRED_SKILLS = frozenset({"anti-slop-editor", "design-anti-slop-reviewer"})
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def _require_true(evidence: Mapping[str, Any], name: str, failures: list[str]) -> None:
    if evidence.get(name) is not True:
        failures.append(f"{name} must be true")


def evaluate_customer_facing_quality(evidence: Mapping[str, Any]) -> Mapping[str, Any]:
    """Return a deterministic pass record or raise ValidationError."""
    failures: list[str] = []
    artifact_id = evidence.get("artifact_id")
    artifact_hash = evidence.get("artifact_sha256")
    artifact_kind = evidence.get("artifact_kind")

    if not isinstance(artifact_id, str) or not artifact_id.strip():
        failures.append("artifact_id is required")
    if not isinstance(artifact_hash, str) or not SHA256_PATTERN.fullmatch(artifact_hash):
        failures.append("artifact_sha256 must be a lowercase SHA-256 digest")
    if artifact_kind not in {"text", "visual", "customer-facing-release"}:
        failures.append("artifact_kind is invalid")

    loaded = evidence.get("required_skills_loaded")
    if not isinstance(loaded, list) or not REQUIRED_SKILLS.issubset(set(loaded)):
        failures.append("required quality skills are missing")

    blockers = evidence.get("deterministic_blockers")
    if not isinstance(blockers, list):
        failures.append("deterministic_blockers must be a list")
    elif blockers:
        failures.append("deterministic blockers remain")

    _require_true(evidence, "writing_lint_passed", failures)
    if evidence.get("fabricated_proof") is not False:
        failures.append("fabricated_proof must be false")
    unsupported = evidence.get("unsupported_claims")
    if not isinstance(unsupported, list) or unsupported:
        failures.append("unsupported claims remain or were not reported")

    if artifact_kind in {"visual", "customer-facing-release"}:
        viewports = evidence.get("verified_viewports")
        if not isinstance(viewports, list) or not {"desktop", "mobile"}.issubset(set(viewports)):
            failures.append("desktop and mobile evidence are required")
        for field in (
            "accessibility_passed",
            "interactions_verified",
            "named_pattern_review_passed",
        ):
            _require_true(evidence, field, failures)

    review = evidence.get("independent_review")
    if not isinstance(review, Mapping):
        failures.append("independent_review is required")
    else:
        if review.get("verdict") != "PASS":
            failures.append("independent review did not pass")
        if review.get("artifact_sha256") != artifact_hash:
            failures.append("independent review is bound to a different artifact")
        if review.get("isolated") is not True or review.get("fresh_context") is not True:
            failures.append("independent review was not fresh and isolated")

    if failures:
        raise ValidationError("customer-facing quality gate failed: " + "; ".join(sorted(failures)))
    return {
        "status": "passed",
        "artifact_id": artifact_id,
        "artifact_sha256": artifact_hash,
        "artifact_kind": artifact_kind,
        "blocker_count": 0,
        "required_skills": sorted(REQUIRED_SKILLS),
    }


def enforce_customer_facing_quality(context: Mapping[str, Any]) -> Mapping[str, Any]:
    """Standing Operation handler for the exact evidence packet in context."""
    evidence = context.get("quality_evidence")
    if not isinstance(evidence, Mapping):
        raise ValidationError("quality_evidence is required before publication")
    return evaluate_customer_facing_quality(evidence)