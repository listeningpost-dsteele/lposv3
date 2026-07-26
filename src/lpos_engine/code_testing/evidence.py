"""Release evidence packet construction with independent-reviewer enforcement.

:func:`build_evidence_packet` assembles the evidence packet defined by the Code Testing
Gauntlet Standard. It enforces the independence rule that mirrors Sentinel: a producer
cannot audit its own release, so the independent reviewer may not be the implementer.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from ..errors import ValidationError


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, (str, bytes)):
        return [value]
    if isinstance(value, Sequence):
        return list(value)
    return [value]


def build_evidence_packet(
    *,
    change_id: str,
    criticality: str,
    behavior_contract: Any = None,
    frozen_acceptance_artifacts: Any = None,
    commands_executed: Any = None,
    pass_fail_results: Any = None,
    coverage: Any = None,
    mutation: Any = None,
    architecture_fitness: Any = None,
    residual_risk: Any = None,
    rollback_method: Any = None,
    independent_reviewer: str | None = None,
    implementer: str | None = None,
    release_recommendation: str | None = None,
) -> dict[str, Any]:
    """Build the release evidence packet.

    Raises :class:`ValidationError` when the independent reviewer is the implementer:
    a producer cannot audit its own release.
    """
    reviewer = (independent_reviewer or "").strip()
    producer = (implementer or "").strip()
    if reviewer and producer and reviewer.casefold() == producer.casefold():
        raise ValidationError(
            "a producer cannot audit its own release: the independent reviewer "
            f"({reviewer!r}) must not be the implementer"
        )

    packet: dict[str, Any] = {
        "change_id": str(change_id),
        "criticality": str(criticality),
        "behavior_contract": behavior_contract,
        "frozen_acceptance_artifacts": _as_list(frozen_acceptance_artifacts),
        "commands_executed": _as_list(commands_executed),
        "pass_fail_results": dict(pass_fail_results)
        if isinstance(pass_fail_results, Mapping)
        else _as_list(pass_fail_results),
        "coverage": coverage,
        "mutation": mutation,
        "architecture_fitness": architecture_fitness,
        "residual_risk": residual_risk if residual_risk is not None else "none recorded",
        "rollback_method": rollback_method,
        "independent_reviewer": reviewer or None,
        "implementer": producer or None,
        "release_recommendation": release_recommendation,
    }
    return packet


__all__ = ["build_evidence_packet"]
