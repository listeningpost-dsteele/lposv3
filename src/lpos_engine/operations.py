"""Executable, idempotent Standing Operation workflows."""

from __future__ import annotations

import traceback
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from .canonical import digest, freeze_mapping, new_id, utc_now
from .errors import AdapterError, ConcurrencyError, ValidationError
from .models import (
    EvidenceRecord,
    EvidenceStatus,
    OperationResult,
    StandingOperationRun,
    WorkflowDefinition,
)
from .store import SQLiteStore

StepHandler = Callable[[Mapping[str, Any]], Mapping[str, Any]]


@dataclass(frozen=True, slots=True)
class WorkflowExecution:
    run: StandingOperationRun
    outputs: Mapping[str, Mapping[str, Any]]


class StandingOperationRunner:
    def __init__(self, store: SQLiteStore, handlers: Mapping[str, StepHandler]) -> None:
        self.store = store
        self.handlers = dict(handlers)

    def run(
        self,
        workflow: WorkflowDefinition,
        *,
        scheduled_for: str,
        initial_context: Mapping[str, Any] | None = None,
        fallback_used: bool = False,
        lease_seconds: int = 900,
    ) -> WorkflowExecution:
        idempotency_key = f"{workflow.so_id}:{scheduled_for}"
        existing = self.store.get_operation_run_by_key(idempotency_key)
        if existing is not None:
            return WorkflowExecution(run=existing, outputs={})

        run_id = new_id("RUN")
        self.store.claim_operation(
            so_id=workflow.so_id,
            run_id=run_id,
            idempotency_key=idempotency_key,
            lease_seconds=lease_seconds,
        )
        started = utc_now()
        outputs: dict[str, Mapping[str, Any]] = {}
        context: dict[str, Any] = dict(initial_context or {})
        result = OperationResult.OK
        error_text = ""

        try:
            remaining = {step.step_id: step for step in workflow.steps}
            while remaining:
                ready = [
                    step
                    for step in remaining.values()
                    if all(dependency in outputs for dependency in step.depends_on)
                ]
                if not ready:
                    raise ValidationError("workflow cannot make progress")
                for step in sorted(ready, key=lambda item: item.step_id):
                    handler = self.handlers.get(step.handler)
                    if handler is None:
                        raise AdapterError(f"no Standing Operation handler registered: {step.handler}")
                    step_context = {
                        **context,
                        "so_id": workflow.so_id,
                        "run_id": run_id,
                        "scheduled_for": scheduled_for,
                        "dependencies": {item: outputs[item] for item in step.depends_on},
                    }
                    try:
                        value = handler(step_context)
                        if not isinstance(value, Mapping):
                            raise AdapterError(f"handler {step.handler} returned a non-mapping")
                        # Validate and freeze before another step can observe the
                        # output.  This prevents an adapter from smuggling a
                        # mutable or non-JSON object into the evidence digest.
                        frozen_value = freeze_mapping(value)
                        outputs[step.step_id] = frozen_value
                        context[step.step_id] = frozen_value
                    except Exception as exc:
                        if not step.continue_on_error:
                            raise
                        outputs[step.step_id] = freeze_mapping(
                            {
                                "error": f"{type(exc).__name__}: {exc}",
                                "continued": True,
                            }
                        )
                    del remaining[step.step_id]
            if not any(outputs.values()):
                result = OperationResult.SILENT
        except Exception as exc:
            result = OperationResult.ERROR
            error_text = f"{type(exc).__name__}: {exc}"
            outputs["__error__"] = freeze_mapping(
                {
                    "error": error_text,
                    "traceback": "".join(
                        traceback.format_exception_only(type(exc), exc)
                    ).strip(),
                }
            )

        finished = utc_now()
        output_hash = digest(outputs)
        evidence = EvidenceRecord(
            id=new_id("EVID"),
            recommendation=f"Standing Operation {workflow.so_id} execution record",
            owner="LPOS Engine",
            expected_outcome="Workflow executes once for the scheduled idempotency key.",
            baseline=f"scheduled_for={scheduled_for}",
            target="All required steps complete or an explicit diagnostic is recorded.",
            observed=(error_text or f"{len(outputs)} step outputs; sha256={output_hash}"),
            confidence=1.0,
            measurement="Deterministic workflow state and output digest",
            fallback_used=fallback_used,
            review_date=None,
            status=EvidenceStatus.MEASURED,
        )
        run = StandingOperationRun(
            so_id=workflow.so_id,
            run_id=run_id,
            idempotency_key=idempotency_key,
            started_at=started,
            finished_at=finished,
            result=result,
            outputs_ref=f"sha256:{output_hash}",
            evidence_id=evidence.id,
            fallback_used=fallback_used,
            model_class=workflow.model_class,
        )
        persisted = self.store.save_operation_run(run, evidence=evidence)
        return WorkflowExecution(run=persisted, outputs=freeze_mapping(outputs))
