"""Dataclass models for admission suites and cases.

These follow the existing LPOS conventions: frozen dataclasses with slots,
canonical validation via require_text/require_id, and from_dict/to_dict
serialization that round-trips through canonical_json.

A suite binds every case to a concrete, profession-specific scenario derived
from the Specialist's charter, and every case carries a non-null
expected_disposition drawn from the charter's authority section.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from ..canonical import (
    canonical_json,
    digest,
    freeze_mapping,
    require_id,
    require_text,
    text_digest,
)
from ..errors import ValidationError

# The seven required rubric dimensions, frozen in order.
RUBRIC_DIMENSIONS: tuple[str, ...] = (
    "method_fidelity",
    "boundary_recognition",
    "routing_precision",
    "artifact_quality",
    "evidence_discipline",
    "capability_gap_declaration",
    "completion_honesty",
)

# Case classes required at minimum in every suite.
REQUIRED_CASE_CLASSES: tuple[str, ...] = (
    "representative_positive",
    "positive_routing",
    "negative_routing",
    "adjacent_role_confusion",
    "missing_input",
    "capability_gap",
    "authority_boundary",
    "weak_output_completion_honesty",
)

# Cases that must always pass (no tolerance for failure).
MANDATORY_CASE_CLASSES: tuple[str, ...] = (
    "negative_routing",
    "adjacent_role_confusion",
    "missing_input",
    "capability_gap",
    "authority_boundary",
    "weak_output_completion_honesty",
)

# Cases held out from the candidate's known context.
HELD_OUT_CASE_CLASSES: tuple[str, ...] = (
    "adjacent_role_confusion",
    "capability_gap",
    "weak_output_completion_honesty",
)

# Valid case class labels (REQUIRED plus optional held-out variants).
VALID_CASE_CLASSES: frozenset[str] = frozenset(
    REQUIRED_CASE_CLASSES + (
        "representative_positive_extended",
        "positive_routing_extended",
    )
)

# Canonical disposition values that every expected_disposition must draw from.
# These are the categories the admission contract binds, not the
# profession-specific disposition CODES (those live in the task text).
VALID_DISPOSITIONS: frozenset[str] = frozenset({
    "acceptance",
    "refusal",
    "handoff",
    "capability_gap",
    "missing_input",
    "rejection",
})


@dataclass(frozen=True, slots=True)
class AdmissionCase:
    """A single behavioral admission test case for a Specialist candidate.

    ``task`` is a concrete, profession-specific work scenario (never a
    meta-prompt or template fill).  ``expected_disposition`` binds the
    acceptance/refusal/handoff/capability-gap/missing-input/rejection
    expectation and is never null.
    """

    case_id: str
    case_class: str
    task: str
    expected_behavior: str
    expected_disposition: str
    mandatory: bool = False
    held_out: bool = False

    def __post_init__(self) -> None:
        require_id("case_id", self.case_id)
        require_text("case_class", self.case_class)
        if self.case_class not in VALID_CASE_CLASSES:
            raise ValidationError(
                f"unknown case class: {self.case_class}"
            )
        require_text("task", self.task)
        require_text("expected_behavior", self.expected_behavior)
        if not self.expected_disposition:
            raise ValidationError(
                f"case {self.case_id}: expected_disposition must not be null"
            )
        if self.expected_disposition not in VALID_DISPOSITIONS:
            raise ValidationError(
                f"case {self.case_id}: expected_disposition "
                f"{self.expected_disposition!r} is not one of "
                f"{sorted(VALID_DISPOSITIONS)}"
            )

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "AdmissionCase":
        return cls(
            case_id=require_id("case_id", value["case_id"]),
            case_class=value["case_class"],
            task=value["task"],
            expected_behavior=value["expected_behavior"],
            expected_disposition=value["expected_disposition"],
            mandatory=bool(value.get("mandatory", False)),
            held_out=bool(value.get("held_out", False)),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "case_class": self.case_class,
            "task": self.task,
            "expected_behavior": self.expected_behavior,
            "expected_disposition": self.expected_disposition,
            "mandatory": self.mandatory,
            "held_out": self.held_out,
        }


@dataclass(frozen=True, slots=True)
class AdmissionSuite:
    """A complete admission suite for one Specialist candidate.

    Every suite is derived from the Specialist's charter, Guild charter,
    and mapped Craft Standards.  Suites are frozen by canonical hash and
    bound to exact source hashes.
    """

    suite_id: str
    specialist_id: str
    specialist_name: str
    guild: str
    craft_standards: tuple[str, ...]
    capabilities: tuple[str, ...]
    model_class: str
    adjacent_specialists: tuple[str, ...]
    cases: tuple[AdmissionCase, ...]
    # Source binding: exact hashes of the charter content at suite generation time.
    specialist_charter_sha256: str
    guild_charter_sha256: str
    craft_standard_sha256: dict[str, str]
    suite_version: str = "1.0.0"

    def __post_init__(self) -> None:
        require_id("suite_id", self.suite_id)
        require_id("specialist_id", self.specialist_id)
        require_text("specialist_name", self.specialist_name)
        require_text("guild", self.guild)
        if not self.craft_standards:
            raise ValidationError(f"{self.suite_id} has no craft standards")
        if not self.capabilities:
            raise ValidationError(f"{self.suite_id} has no capabilities")
        if not self.cases:
            raise ValidationError(f"{self.suite_id} has no cases")
        # Ensure case IDs are unique within suite.
        case_ids = [case.case_id for case in self.cases]
        if len(case_ids) != len(set(case_ids)):
            raise ValidationError(f"{self.suite_id} has duplicate case IDs")
        # Ensure no duplicate task text within suite.
        tasks = [case.task.strip().lower() for case in self.cases]
        if len(tasks) != len(set(tasks)):
            raise ValidationError(f"{self.suite_id} has duplicate task text")
        # Ensure all 8 required case classes present.
        present = {c.case_class for c in self.cases}
        missing = [cls for cls in REQUIRED_CASE_CLASSES if cls not in present]
        if missing:
            raise ValidationError(
                f"{self.suite_id} missing required case classes: {missing}"
            )

    @property
    def content_hash(self) -> str:
        """Canonical SHA-256 of the suite's serializable content."""
        return digest(self._hash_payload())

    def _hash_payload(self) -> dict[str, Any]:
        """Return the suite content without the computed hash field."""
        return {
            "suite_id": self.suite_id,
            "specialist_id": self.specialist_id,
            "specialist_name": self.specialist_name,
            "guild": self.guild,
            "craft_standards": list(self.craft_standards),
            "capabilities": list(self.capabilities),
            "model_class": self.model_class,
            "adjacent_specialists": list(self.adjacent_specialists),
            "cases": [case.to_dict() for case in self.cases],
            "specialist_charter_sha256": self.specialist_charter_sha256,
            "guild_charter_sha256": self.guild_charter_sha256,
            "craft_standard_sha256": dict(self.craft_standard_sha256),
            "suite_version": self.suite_version,
        }

    @property
    def mandatory_cases(self) -> tuple[AdmissionCase, ...]:
        return tuple(case for case in self.cases if case.mandatory)

    @property
    def held_out_cases(self) -> tuple[AdmissionCase, ...]:
        return tuple(case for case in self.cases if case.held_out)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "AdmissionSuite":
        cases = tuple(AdmissionCase.from_dict(item) for item in value["cases"])
        craft_standard_hashes = dict(value.get("craft_standard_sha256", {}))
        return cls(
            suite_id=value["suite_id"],
            specialist_id=value["specialist_id"],
            specialist_name=value["specialist_name"],
            guild=value["guild"],
            craft_standards=tuple(value["craft_standards"]),
            capabilities=tuple(value["capabilities"]),
            model_class=value["model_class"],
            adjacent_specialists=tuple(value.get("adjacent_specialists", ())),
            cases=cases,
            specialist_charter_sha256=value["specialist_charter_sha256"],
            guild_charter_sha256=value["guild_charter_sha256"],
            craft_standard_sha256=craft_standard_hashes,
            suite_version=value.get("suite_version", "1.0.0"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "suite_id": self.suite_id,
            "specialist_id": self.specialist_id,
            "specialist_name": self.specialist_name,
            "guild": self.guild,
            "craft_standards": list(self.craft_standards),
            "capabilities": list(self.capabilities),
            "model_class": self.model_class,
            "adjacent_specialists": list(self.adjacent_specialists),
            "cases": [case.to_dict() for case in self.cases],
            "specialist_charter_sha256": self.specialist_charter_sha256,
            "guild_charter_sha256": self.guild_charter_sha256,
            "craft_standard_sha256": dict(self.craft_standard_sha256),
            "suite_version": self.suite_version,
            "content_sha256": self.content_hash,
        }
