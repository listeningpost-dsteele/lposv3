"""Standing Operation step handlers for the Code Testing Guild.

Three Standing Operations are codified here:

* SO-027 Code Test Gauntlet -- classify criticality, run the Need-to-Change Gate,
  evaluate the criticality-weighted release gauntlet, and record the evidence packet.
* SO-028 Test Suite Health Review -- report flaky, slow, skipped, duplicate, and
  low-coverage findings over a supplied manifest and results set (or report cleanly
  that no results were supplied).
* SO-029 Critical Path Hardening -- verify the extra HIGH/CRITICAL gates are present
  before a high-risk release.

Every handler follows the StandingOperationRunner contract: it accepts the merged
context mapping and returns a JSON-safe mapping; a gate failure raises ValidationError
so the runner records an error result.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ..errors import ValidationError
from . import criticality as criticality_module
from . import evidence as evidence_module
from . import gauntlet as gauntlet_module
from . import manifest as manifest_module


def _dependency(context: Mapping[str, Any], step_id: str) -> Mapping[str, Any]:
    """Read a prior step's output from the merged context or the dependency map."""
    value = context.get(step_id)
    if isinstance(value, Mapping):
        return value
    deps = context.get("dependencies")
    if isinstance(deps, Mapping):
        inner = deps.get(step_id)
        if isinstance(inner, Mapping):
            return inner
    return {}


# --------------------------------------------------------------------------- SO-027


def classify_change_criticality(context: Mapping[str, Any]) -> Mapping[str, Any]:
    signals = context.get("signals")
    if not isinstance(signals, Mapping):
        signals = {}
    result = dict(criticality_module.classify(signals))
    result["change_id"] = context.get("change_id", "unspecified-change")
    return result


def run_need_to_change_gate(context: Mapping[str, Any]) -> Mapping[str, Any]:
    evidence = (
        context.get("need_to_change_evidence")
        or context.get("change_evidence")
        or {}
    )
    if not isinstance(evidence, Mapping):
        evidence = {}
    return dict(gauntlet_module.need_to_change_gate(evidence))


def evaluate_release_gauntlet(context: Mapping[str, Any]) -> Mapping[str, Any]:
    classify = _dependency(context, "STEP-CLASSIFY")
    level = classify.get("level") or context.get("level") or "STANDARD"

    need = _dependency(context, "STEP-NEED-TO-CHANGE")
    if need.get("result") == "NO_CHANGE_REQUIRED":
        return {
            "decision": "NO_CHANGE_REQUIRED",
            "level": level,
            "reason": need.get("reason", "no production change required"),
            "missing_gates": [],
            "failed_gates": [],
        }

    gate_results = context.get("gate_results")
    if not isinstance(gate_results, Mapping):
        gate_results = {}
    result = dict(gauntlet_module.evaluate_gauntlet(level, gate_results))
    if result["decision"] == "REJECT":
        raise ValidationError(
            "release gauntlet REJECT for "
            f"{context.get('change_id', 'change')}: " + "; ".join(result["reasons"])
        )
    return result


def record_gauntlet_evidence(context: Mapping[str, Any]) -> Mapping[str, Any]:
    classify = _dependency(context, "STEP-CLASSIFY")
    evaluate = _dependency(context, "STEP-EVALUATE")
    level = classify.get("level") or context.get("level") or "STANDARD"
    decision = evaluate.get("decision", "UNKNOWN")

    if decision == "NO_CHANGE_REQUIRED":
        return {
            "recorded": True,
            "release_recommendation": "NO_CHANGE_REQUIRED",
            "change_id": context.get("change_id", "unspecified-change"),
            "criticality": level,
        }

    packet = evidence_module.build_evidence_packet(
        change_id=context.get("change_id", "unspecified-change"),
        criticality=level,
        behavior_contract=context.get("behavior_contract"),
        frozen_acceptance_artifacts=context.get("frozen_acceptance_artifacts"),
        commands_executed=context.get("commands_executed"),
        pass_fail_results=context.get("pass_fail_results") or evaluate,
        coverage=context.get("coverage"),
        mutation=context.get("mutation"),
        architecture_fitness=context.get("architecture_fitness"),
        residual_risk=context.get("residual_risk"),
        rollback_method=context.get("rollback_method"),
        independent_reviewer=context.get("independent_reviewer"),
        implementer=context.get("implementer"),
        release_recommendation=decision,
    )
    return {"recorded": True, "evidence_packet": packet}


# --------------------------------------------------------------------------- SO-028


def review_test_suite_health(context: Mapping[str, Any]) -> Mapping[str, Any]:
    manifest = manifest_module.load_manifest(context.get("manifest"))
    commands = manifest_module.manifest_commands(manifest)
    results = context.get("results")
    if not isinstance(results, Mapping) or not results:
        return {
            "status": "no_results",
            "message": "no results supplied",
            "declared_commands": sorted(commands),
            "findings": [],
        }

    findings: list[dict[str, Any]] = []

    def _add(category: str, items: Any) -> None:
        if isinstance(items, (list, tuple)) and items:
            findings.append({"category": category, "count": len(items), "items": list(items)})

    _add("flaky", results.get("flaky"))
    _add("slow", results.get("slow"))
    _add("skipped", results.get("skipped"))
    _add("duplicate", results.get("duplicate"))
    _add("low_value", results.get("low_value"))
    _add("coverage_gap", results.get("coverage_gaps"))
    _add("mutation_survivor", results.get("mutation_survivors"))
    _add("broken_fixture", results.get("broken_fixtures"))
    _add("stale_snapshot", results.get("stale_snapshots"))
    _add("unreliable_dependency", results.get("unreliable_dependencies"))

    return {
        "status": "reviewed" if findings else "healthy",
        "declared_commands": sorted(commands),
        "finding_count": len(findings),
        "findings": findings,
    }


# --------------------------------------------------------------------------- SO-029


def verify_critical_path_hardening(context: Mapping[str, Any]) -> Mapping[str, Any]:
    level = context.get("level") or _dependency(context, "STEP-CLASSIFY").get("level") or "HIGH"
    resolved = gauntlet_module.normalize_level(level)
    if resolved not in {"HIGH", "CRITICAL"}:
        raise ValidationError(
            f"Critical Path Hardening applies to HIGH or CRITICAL releases, not {resolved}"
        )
    extra = gauntlet_module.extra_gates_for(resolved)
    gate_results = context.get("gate_results")
    if not isinstance(gate_results, Mapping):
        gate_results = {}

    missing = [
        gate
        for gate in extra
        if not (
            isinstance(gate_results.get(gate), Mapping)
            and gate_results[gate].get("ran")
            and gate_results[gate].get("passed")
            and not gate_results[gate].get("flaky")
        )
    ]
    if missing:
        raise ValidationError(
            f"critical-path hardening incomplete for {resolved}: missing or failing "
            "gates: " + ", ".join(missing)
        )
    return {
        "level": resolved,
        "hardened": True,
        "verified_gates": extra,
    }


HANDLERS: dict[str, Any] = {
    "classify_change_criticality": classify_change_criticality,
    "run_need_to_change_gate": run_need_to_change_gate,
    "evaluate_release_gauntlet": evaluate_release_gauntlet,
    "record_gauntlet_evidence": record_gauntlet_evidence,
    "review_test_suite_health": review_test_suite_health,
    "verify_critical_path_hardening": verify_critical_path_hardening,
}
