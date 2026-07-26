"""Code Testing Gauntlet Standard, expressed as executable data and gates.

The tier -> required-gate table is the Code Testing Gauntlet Standard rendered as
data (cumulative: STANDARD includes LIGHT, HIGH includes STANDARD, CRITICAL includes
HIGH). Two deterministic enforcement functions turn the standard's prose constraints
into checks a host can run:

* :func:`need_to_change_gate` -- the Need-to-Change Gate. A production change requires a
  reproduction, a demonstrated missing behavior, or an objective-constraint proof;
  absent all three the correct successful answer is ``NO_CHANGE_REQUIRED``.
* :func:`evaluate_gauntlet` -- the release decision. A required gate that did not RUN is
  a REJECT ("required command did not run"), a failing or flaky gate is a REJECT, and a
  green unit suite alone can never approve STANDARD or above.

Nothing here shells out or invents a command; it evaluates gate *results* supplied by the
host, which sources every command from the repository testing manifest.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

# Ordered, cumulative tiers.
TIER_ORDER: tuple[str, ...] = ("LIGHT", "STANDARD", "HIGH", "CRITICAL")

# Gates introduced at each tier (the standard, verbatim intent, as stable identifiers).
GATES_ADDED: dict[str, tuple[str, ...]] = {
    "LIGHT": (
        "need_to_change_gate",
        "format_or_syntax_check",
        "lint_or_static_check",
        "focused_unit_tests",
        "build_or_import_verification",
        "changed_behavior_smoke_test",
    ),
    "STANDARD": (
        "behavior_acceptance_criteria",
        "regression_test",
        "unit_test_stream",
        "integration_or_contract_test_stream",
        "type_check_when_available",
        "architecture_and_complexity_checks",
        "real_workflow_smoke_test",
    ),
    "HIGH": (
        "independent_acceptance_spec_review",
        "executable_acceptance_tests",
        "property_or_invariant_tests",
        "changed_code_mutation_testing",
        "security_tests",
        "performance_or_concurrency_checks",
        "manual_or_system_spot_check",
        "rollback_verification",
    ),
    "CRITICAL": (
        "principal_or_qualified_engineer_approval",
        "isolated_test_environment",
        "full_mutation_hardening_or_documented_exception",
        "staging_or_canary_validation",
        "restore_or_rollback_drill",
        "production_observability_and_incident_response_plan",
        "explicit_release_approval",
    ),
}

# Gates whose presence proves more than "the code executed without crashing".
# A green unit suite alone (only these unit-style gates) can never approve STANDARD+.
_UNIT_ONLY_GATES = frozenset(
    {
        "focused_unit_tests",
        "unit_test_stream",
        "build_or_import_verification",
    }
)

# Gates that demonstrate real behavior/regression coverage beyond unit execution.
_BEHAVIOR_GATES = frozenset(
    {
        "behavior_acceptance_criteria",
        "regression_test",
        "integration_or_contract_test_stream",
        "executable_acceptance_tests",
        "real_workflow_smoke_test",
    }
)


def normalize_level(level: Any) -> str:
    """Coerce an arbitrary value to a known tier; unknown -> STANDARD (total)."""
    text = str(level or "").strip().upper()
    return text if text in GATES_ADDED else "STANDARD"


def required_gates(level: Any) -> list[str]:
    """Cumulative list of gates required at ``level`` (deterministic, total)."""
    resolved = normalize_level(level)
    gates: list[str] = []
    for tier in TIER_ORDER:
        gates.extend(GATES_ADDED[tier])
        if tier == resolved:
            break
    return gates


def extra_gates_for(level: Any) -> list[str]:
    """The gates that a HIGH or CRITICAL change adds on top of STANDARD."""
    resolved = normalize_level(level)
    if resolved not in {"HIGH", "CRITICAL"}:
        return []
    gates: list[str] = list(GATES_ADDED["HIGH"])
    if resolved == "CRITICAL":
        gates.extend(GATES_ADDED["CRITICAL"])
    return gates


def need_to_change_gate(evidence: Mapping[str, Any] | None) -> dict[str, Any]:
    """The Need-to-Change Gate.

    A production change proceeds only with a reproduction, a demonstrated missing
    behavior, or a proof that an objective constraint blocks a required refactor.
    Absent all three, ``NO_CHANGE_REQUIRED`` is the correct successful result.
    """
    evidence = evidence or {}
    reproduction = bool(
        evidence.get("reproduction")
        or evidence.get("failing_behavior_test")
        or evidence.get("reproduced")
    )
    missing_behavior = bool(
        evidence.get("demonstrated_missing_behavior")
        or evidence.get("missing_behavior")
    )
    constraint = bool(
        evidence.get("objective_constraint_proof")
        or evidence.get("objective_constraint")
    )
    grounds = [
        name
        for name, present in (
            ("reproduction", reproduction),
            ("demonstrated_missing_behavior", missing_behavior),
            ("objective_constraint_proof", constraint),
        )
        if present
    ]
    if grounds:
        return {
            "result": "PROCEED",
            "reason": "change is justified by: " + ", ".join(grounds),
            "grounds": grounds,
        }
    return {
        "result": "NO_CHANGE_REQUIRED",
        "reason": (
            "no reproduction, demonstrated missing behavior, or objective-constraint "
            "proof was supplied; no production change is required when the behavior "
            "already works"
        ),
        "grounds": [],
    }


def _gate_ran(entry: Any) -> bool:
    return bool(isinstance(entry, Mapping) and entry.get("ran"))


def _gate_passed(entry: Any) -> bool:
    if not isinstance(entry, Mapping):
        return False
    if entry.get("flaky"):
        return False
    return bool(entry.get("passed"))


def evaluate_gauntlet(
    level: Any, gate_results: Mapping[str, Any] | None
) -> dict[str, Any]:
    """Return the release decision for ``level`` given executed gate results.

    ``gate_results`` maps a gate identifier to ``{"ran": bool, "passed": bool}``
    (an optional ``"flaky": true`` marks a passing-but-unreliable gate as failed).

    Enforcement (from the standard's mandatory constraints):

    * A required gate that did not RUN -> REJECT ("required command did not run").
    * A failing or flaky required gate -> REJECT.
    * A green unit suite alone can never PASS STANDARD, HIGH, or CRITICAL.
    """
    resolved = normalize_level(level)
    results = gate_results or {}
    required = required_gates(resolved)

    missing_gates = [gate for gate in required if not _gate_ran(results.get(gate))]
    failed_gates = [
        gate
        for gate in required
        if _gate_ran(results.get(gate)) and not _gate_passed(results.get(gate))
    ]

    reasons: list[str] = []
    for gate in missing_gates:
        reasons.append(f"required command did not run: {gate}")
    for gate in failed_gates:
        entry = results.get(gate)
        flaky = bool(isinstance(entry, Mapping) and entry.get("flaky"))
        reasons.append(
            f"required gate {'is flaky' if flaky else 'failed'}: {gate}"
        )

    # Green-unit-only guard for STANDARD+: even if (hypothetically) the required set
    # were satisfied, a run whose only executed+passed gates are unit-style cannot
    # approve STANDARD or above.
    green_unit_only = False
    if resolved != "LIGHT":
        ran_passed = {
            gate
            for gate, entry in results.items()
            if _gate_ran(entry) and _gate_passed(entry)
        }
        if ran_passed and ran_passed <= _UNIT_ONLY_GATES and not (ran_passed & _BEHAVIOR_GATES):
            green_unit_only = True
            reasons.append(
                "a green unit suite alone cannot approve STANDARD, HIGH, or CRITICAL "
                "changes"
            )

    decision = "PASS" if not missing_gates and not failed_gates and not green_unit_only else "REJECT"
    return {
        "decision": decision,
        "level": resolved,
        "required_gates": required,
        "missing_gates": missing_gates,
        "failed_gates": failed_gates,
        "green_unit_only": green_unit_only,
        "reasons": reasons,
    }


__all__ = [
    "TIER_ORDER",
    "GATES_ADDED",
    "normalize_level",
    "required_gates",
    "extra_gates_for",
    "need_to_change_gate",
    "evaluate_gauntlet",
]
