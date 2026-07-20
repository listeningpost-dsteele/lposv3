"""Fixed, repeatable LPOS v4 benchmark fixtures and deterministic core evaluator."""

from __future__ import annotations

import json
from importlib.resources import files
from typing import Any

from ..errors import ValidationError
from ..routing import CapabilityRegistry, CapabilityRouter
from ..workflows import load as load_workflow

_REQUIRED_FIELDS = {
    "id",
    "component_type",
    "component_id",
    "objective",
    "fixture_version",
    "scenario",
    "inputs",
    "expected",
    "success_criteria",
    "failure_criteria",
    "evaluation",
    "evidence",
}


def catalog() -> tuple[dict[str, Any], ...]:
    try:
        value = json.loads(files(__package__).joinpath("catalog.json").read_text(encoding="utf-8"))
        entries = value["benchmarks"]
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise ValidationError("packaged benchmark catalog is missing or invalid") from exc
    if not isinstance(entries, list):
        raise ValidationError("benchmark catalog entries must be a list")
    return tuple(dict(item) for item in entries)


def load(benchmark_id: str) -> dict[str, Any]:
    names = {item["id"]: item["fixture"] for item in catalog()}
    try:
        filename = names[benchmark_id]
    except KeyError as exc:
        raise ValidationError(f"unknown benchmark: {benchmark_id}") from exc
    try:
        value = json.loads(files(__package__).joinpath(filename).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValidationError(f"benchmark {benchmark_id} is missing or invalid") from exc
    if not isinstance(value, dict):
        raise ValidationError(f"benchmark {benchmark_id} must be an object")
    missing = _REQUIRED_FIELDS - set(value)
    if missing:
        raise ValidationError(f"benchmark {benchmark_id} is missing fields: {sorted(missing)}")
    if value["id"] != benchmark_id:
        raise ValidationError(f"benchmark identity mismatch for {benchmark_id}")
    if value["component_type"] not in {"specialist", "standing_operation"}:
        raise ValidationError(f"benchmark {benchmark_id} has an unknown component type")
    if not isinstance(value["inputs"], dict) or not isinstance(value["expected"], dict):
        raise ValidationError(f"benchmark {benchmark_id} inputs and expected values must be objects")
    return value


def load_all() -> tuple[dict[str, Any], ...]:
    return tuple(load(item["id"]) for item in catalog())


def run_core_evaluations() -> dict[str, Any]:
    """Evaluate deterministic routing and workflow contracts against all fixed fixtures.

    This deliberately does not pretend to score a remote model's prose or judgment.
    Deployment adapters can consume the same fixtures for model-quality evaluation.
    """

    router = CapabilityRouter(CapabilityRegistry.default())
    results: list[dict[str, Any]] = []
    for benchmark in load_all():
        assertions: list[dict[str, Any]] = []
        if benchmark["component_type"] == "specialist":
            inputs = benchmark["inputs"]
            expected = benchmark["expected"]
            route = router.route(
                inputs["required_capabilities"],
                preferred_model_class=inputs.get("preferred_model_class"),
            )
            checks = {
                "lead_specialist": route.lead_specialist == expected["lead_specialist"],
                "model_class": route.model_class == expected["model_class"],
                "no_missing_capabilities": not route.missing_capabilities,
                "craft_standards_present": bool(route.craft_standards),
            }
        else:
            expected = benchmark["expected"]
            workflow = load_workflow(benchmark["component_id"])
            checks = {
                "workflow_identity": workflow.so_id == expected["so_id"],
                "model_class": workflow.model_class == expected["model_class"],
                "minimum_steps": len(workflow.steps) >= int(expected["minimum_steps"]),
                "unique_step_ids": len({step.step_id for step in workflow.steps}) == len(workflow.steps),
            }
        for name, passed in checks.items():
            assertions.append({"name": name, "passed": bool(passed)})
        results.append(
            {
                "id": benchmark["id"],
                "component_id": benchmark["component_id"],
                "status": "PASS" if all(item["passed"] for item in assertions) else "FAIL",
                "assertions": assertions,
            }
        )
    passed = sum(item["status"] == "PASS" for item in results)
    return {
        "os_version": "4.1.0",
        "evaluation_type": "deterministic_core",
        "total": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "results": results,
    }


__all__ = ["catalog", "load", "load_all", "run_core_evaluations"]
