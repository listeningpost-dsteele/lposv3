"""Deterministic corpus validators for admission suites.

Validates exactly 103 suites, one per runtime Specialist, no duplicates,
all required case classes, valid adjacent-role targets, mapped Guild and
Craft Standards, exact source hashes, and no generic duplicated task text.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..canonical import text_digest
from ..context import SpecRepository
from ..routing import CapabilityRegistry
from .models import (
    AdmissionSuite,
    REQUIRED_CASE_CLASSES,
    MANDATORY_CASE_CLASSES,
    HELD_OUT_CASE_CLASSES,
)


def validate_corpus(suites: list[AdmissionSuite]) -> dict[str, Any]:
    """Validate the complete admission corpus.

    Returns a dict with 'valid' (bool) and 'errors' (list[str]).
    """

    errors: list[str] = []
    registry = CapabilityRegistry.default()
    repo = SpecRepository.packaged()

    # Build lookup maps from runtime.
    runtime_ids = {p.specialist_id for p in registry.profiles}
    runtime_map = {p.specialist_id: p for p in registry.profiles}
    guild_members: dict[str, list[str]] = {}
    for p in registry.profiles:
        guild_members.setdefault(p.guild, []).append(p.specialist_id)

    # 1. Exactly 103 suites.
    if len(suites) != 103:
        errors.append(f"expected exactly 103 suites, found {len(suites)}")

    # 2. One per runtime Specialist.
    suite_specialist_ids = [s.specialist_id for s in suites]
    if len(suite_specialist_ids) != len(set(suite_specialist_ids)):
        errors.append("duplicate specialist_id across suites")
    for sid in suite_specialist_ids:
        if sid not in runtime_ids:
            errors.append(f"suite references unknown specialist: {sid}")
    missing_specialists = runtime_ids - set(suite_specialist_ids)
    if missing_specialists:
        errors.append(f"missing suites for specialists: {sorted(missing_specialists)}")

    # 3. All required case classes present in every suite.
    for suite in suites:
        present = {c.case_class for c in suite.cases}
        missing = [cls for cls in REQUIRED_CASE_CLASSES if cls not in present]
        if missing:
            errors.append(
                f"suite {suite.suite_id} missing required case classes: {missing}"
            )

    # 4. Valid adjacent-role targets.
    for suite in suites:
        for adj in suite.adjacent_specialists:
            if adj == suite.specialist_id:
                errors.append(
                    f"suite {suite.suite_id} lists itself as adjacent"
                )
            elif adj not in runtime_ids:
                errors.append(
                    f"suite {suite.suite_id} has invalid adjacent specialist: {adj}"
                )
            else:
                # Adjacent must be in the same guild.
                adj_profile = runtime_map.get(adj)
                if adj_profile and adj_profile.guild != suite.guild:
                    errors.append(
                        f"suite {suite.suite_id} adjacent specialist {adj} "
                        f"is in a different guild ({adj_profile.guild} vs {suite.guild})"
                    )

    # 5. Mapped Guild and Craft Standards match runtime.
    for suite in suites:
        profile = runtime_map.get(suite.specialist_id)
        if profile:
            if suite.guild != profile.guild:
                errors.append(
                    f"suite {suite.suite_id} guild mismatch: "
                    f"{suite.guild} vs runtime {profile.guild}"
                )
            if set(suite.craft_standards) != set(profile.craft_standards):
                errors.append(
                    f"suite {suite.suite_id} craft standards mismatch: "
                    f"{sorted(suite.craft_standards)} vs runtime {sorted(profile.craft_standards)}"
                )

    # 6. Exact source hashes match current charter content.
    for suite in suites:
        _, charter_content = repo.load_component(suite.specialist_id)
        expected_sha = text_digest(charter_content)
        if suite.specialist_charter_sha256 != expected_sha:
            errors.append(
                f"suite {suite.suite_id} specialist charter hash mismatch "
                f"(expected {expected_sha[:12]}, got {suite.specialist_charter_sha256[:12]})"
            )

        _, guild_content = repo.load_component(suite.guild)
        expected_guild_sha = text_digest(guild_content)
        if suite.guild_charter_sha256 != expected_guild_sha:
            errors.append(
                f"suite {suite.suite_id} guild charter hash mismatch"
            )

        for cs_id in suite.craft_standards:
            _, cs_content = repo.load_component(cs_id)
            expected_cs_sha = text_digest(cs_content)
            actual_cs_sha = suite.craft_standard_sha256.get(cs_id, "")
            if actual_cs_sha != expected_cs_sha:
                errors.append(
                    f"suite {suite.suite_id} craft standard {cs_id} hash mismatch"
                )

    # 7. No generic duplicated task text across ALL suites.
    all_tasks: dict[str, str] = {}
    for suite in suites:
        for case in suite.cases:
            key = case.task.strip().lower()
            if key in all_tasks:
                errors.append(
                    f"duplicate task text between {all_tasks[key]} "
                    f"and {suite.suite_id} (case {case.case_id})"
                )
            all_tasks[key] = suite.suite_id

    # 8. Mandatory and held-out flags are correct.
    for suite in suites:
        for case in suite.cases:
            if case.case_class in MANDATORY_CASE_CLASSES and not case.mandatory:
                errors.append(
                    f"suite {suite.suite_id} case {case.case_id} "
                    f"({case.case_class}) must be mandatory"
                )
            if case.case_class in HELD_OUT_CASE_CLASSES and not case.held_out:
                errors.append(
                    f"suite {suite.suite_id} case {case.case_id} "
                    f"({case.case_class}) must be held_out"
                )

    # 9. Anti-template validation: no placeholder phrases, no identity-only tasks.
    from .generate import validate_against_templates, FORBIDDEN_PHRASES
    for suite in suites:
        violations = validate_against_templates(list(suite.cases))
        for v in violations:
            errors.append(f"anti-template: {suite.suite_id}: {v}")

    # 10. Every case must have a non-null expected_disposition.
    for suite in suites:
        for case in suite.cases:
            if not case.expected_disposition:
                errors.append(
                    f"suite {suite.suite_id} case {case.case_id} "
                    f"has null expected_disposition"
                )

    return {
        "valid": len(errors) == 0,
        "suite_count": len(suites),
        "errors": errors,
    }


def load_corpus_from_data(data_dir: Path | None = None) -> list[AdmissionSuite]:
    """Load all admission suites from the packaged data directory."""
    import json

    if data_dir is None:
        from importlib.resources import files
        data_root = files("lpos_engine.admission.data")
        suite_files = sorted(
            item for item in data_root.iterdir()
            if str(item.name).startswith("ADM-") and str(item.name).endswith(".json")
        )
        suites = []
        for item in suite_files:
            data = json.loads(item.read_text(encoding="utf-8"))
            suites.append(AdmissionSuite.from_dict(data))
        return suites

    suite_files = sorted(data_dir.glob("ADM-*.json"))
    suites = []
    for path in suite_files:
        data = json.loads(path.read_text(encoding="utf-8"))
        suites.append(AdmissionSuite.from_dict(data))
    return suites
