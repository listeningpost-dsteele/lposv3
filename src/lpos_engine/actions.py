"""Plan/apply action service with approval and idempotency enforcement."""

from __future__ import annotations

from typing import Mapping, Sequence

from .adapters.base import AdapterRegistry
from .approvals import ApprovalService
from .canonical import new_id
from .errors import ActionExecutionError, ConcurrencyError, PolicyViolation
from .models import ActionPlan, ActionResult, ActionStatus, ApprovalRequest
from .store import SQLiteStore


class ActionService:
    def __init__(
        self,
        store: SQLiteStore,
        adapters: AdapterRegistry,
        approvals: ApprovalService,
    ) -> None:
        self.store = store
        self.adapters = adapters
        self.approvals = approvals

    def plan(
        self,
        *,
        task_id: str,
        kind: str,
        parameters: Mapping,
        external: bool,
        reversible: bool,
        idempotency_key: str,
        approval_required: bool | None = None,
        risk_tags: Sequence[str] = (),
        expires_at: str | None = None,
    ) -> tuple[ActionPlan, ApprovalRequest | None]:
        plan = ActionPlan.create(
            action_id=new_id("ACT"),
            task_id=task_id,
            kind=kind,
            parameters=parameters,
            external=external,
            reversible=reversible,
            approval_required=approval_required,
            idempotency_key=idempotency_key,
            risk_tags=risk_tags,
        )
        stored = self.store.create_action(plan)
        existing_state = self.store.get_action(stored.action_id)
        request = None
        if stored.approval_required and existing_state["status"] is ActionStatus.AWAITING_APPROVAL:
            request = self.store.get_approval_request_for_action(stored.action_id)
            if request is None:
                request = self.approvals.request(stored, expires_at=expires_at)
            elif expires_at is not None and request.expires_at != expires_at:
                raise ActionExecutionError(
                    "idempotent action retry attempted to change the approval expiry"
                )
        return stored, request

    def apply(self, action_id: str) -> ActionResult:
        state = self.store.get_action(action_id)
        plan: ActionPlan = state["plan"]
        status = state["status"]
        if status is ActionStatus.SUCCEEDED and state["result"] is not None:
            return state["result"]
        if status in {ActionStatus.FAILED, ActionStatus.CANCELLED}:
            raise PolicyViolation(
                f"action {action_id} is terminal ({status.value}); reconcile and create a new exact action"
            )
        if status is ActionStatus.EXECUTING:
            raise ConcurrencyError(
                f"action {action_id} is already executing; reconcile its outcome before retrying"
            )
        # Resolve the executor before consuming any Principal authority.  A
        # missing adapter is a configuration error, not an attempted action,
        # and must leave both the approval grant and action state untouched.
        adapter = self.adapters.get_action(plan.kind)
        grant = self.approvals.validate(plan)
        version = self.store.claim_action_execution(
            action_id,
            expected_version=state["version"],
            grant_id=grant.grant_id if grant is not None else None,
        )
        try:
            result = adapter.apply(plan)
            if result.action_id != plan.action_id:
                raise ActionExecutionError("action adapter returned a result for a different action")
            if not result.success:
                raise ActionExecutionError(result.error or "action adapter reported failure")
        except Exception as exc:
            failure = ActionResult(
                action_id=plan.action_id,
                success=False,
                output={},
                adapter=getattr(adapter, "name", "unknown"),
                error=f"{type(exc).__name__}: {exc}",
            )
            self.store.update_action(
                action_id,
                ActionStatus.FAILED,
                result=failure,
                expected_version=version,
            )
            if isinstance(exc, ActionExecutionError):
                raise
            raise ActionExecutionError(f"action {action_id} failed: {exc}") from exc
        self.store.update_action(
            action_id,
            ActionStatus.SUCCEEDED,
            result=result,
            expected_version=version,
        )
        return result
