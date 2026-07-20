"""Task lifecycle and transition guards."""

from __future__ import annotations

from .errors import InvalidTransitionError
from .models import ActionStatus, TaskStatus


class TaskStateMachine:
    TERMINAL = frozenset({TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED})

    ALLOWED: dict[TaskStatus, frozenset[TaskStatus]] = {
        TaskStatus.RECEIVED: frozenset(
            {
                TaskStatus.INTERPRETED,
                TaskStatus.PLANNED,
                TaskStatus.AWAITING_CLARIFICATION,
                TaskStatus.CANCELLED,
                TaskStatus.FAILED,
            }
        ),
        TaskStatus.INTERPRETED: frozenset(
            {
                TaskStatus.PLANNED,
                TaskStatus.AWAITING_CLARIFICATION,
                TaskStatus.CANCELLED,
                TaskStatus.FAILED,
            }
        ),
        TaskStatus.PLANNED: frozenset(
            {
                TaskStatus.EXECUTING,
                TaskStatus.AWAITING_APPROVAL,
                TaskStatus.AWAITING_CLARIFICATION,
                TaskStatus.CANCELLED,
                TaskStatus.FAILED,
            }
        ),
        TaskStatus.AWAITING_CLARIFICATION: frozenset(
            {
                TaskStatus.INTERPRETED,
                TaskStatus.PLANNED,
                TaskStatus.CANCELLED,
                TaskStatus.FAILED,
            }
        ),
        TaskStatus.AWAITING_APPROVAL: frozenset(
            {
                TaskStatus.EXECUTING,
                TaskStatus.CANCELLED,
                TaskStatus.FAILED,
                TaskStatus.SUSPENDED,
            }
        ),
        TaskStatus.EXECUTING: frozenset(
            {
                TaskStatus.REVIEWING,
                TaskStatus.COMPLETED,
                TaskStatus.AWAITING_APPROVAL,
                TaskStatus.SUSPENDED,
                TaskStatus.FAILED,
                TaskStatus.CANCELLED,
            }
        ),
        TaskStatus.REVIEWING: frozenset(
            {
                TaskStatus.COMPLETED,
                TaskStatus.CORRECTION_REQUIRED,
                TaskStatus.FAILED,
                TaskStatus.CANCELLED,
            }
        ),
        TaskStatus.CORRECTION_REQUIRED: frozenset(
            {
                TaskStatus.EXECUTING,
                TaskStatus.CANCELLED,
                TaskStatus.FAILED,
            }
        ),
        TaskStatus.SUSPENDED: frozenset(
            {
                TaskStatus.EXECUTING,
                TaskStatus.AWAITING_APPROVAL,
                TaskStatus.CANCELLED,
                TaskStatus.FAILED,
            }
        ),
        TaskStatus.COMPLETED: frozenset(),
        TaskStatus.FAILED: frozenset(),
        TaskStatus.CANCELLED: frozenset(),
    }

    @classmethod
    def assert_transition(cls, current: TaskStatus | str, target: TaskStatus | str) -> None:
        current_status = TaskStatus(current)
        target_status = TaskStatus(target)
        if target_status not in cls.ALLOWED[current_status]:
            allowed = ", ".join(item.value for item in sorted(cls.ALLOWED[current_status], key=lambda x: x.value))
            raise InvalidTransitionError(
                f"task transition {current_status.value!r} -> {target_status.value!r} is not allowed; "
                f"allowed: {allowed or 'none'}"
            )


class ActionStateMachine:
    """Lifecycle guard for exact actions.

    Failed, cancelled, and successful actions are terminal.  A failed external
    action must be reconciled and replanned rather than silently retried with an
    already-consumed approval.
    """

    TERMINAL = frozenset({ActionStatus.SUCCEEDED, ActionStatus.FAILED, ActionStatus.CANCELLED})

    ALLOWED: dict[ActionStatus, frozenset[ActionStatus]] = {
        ActionStatus.PLANNED: frozenset({ActionStatus.EXECUTING, ActionStatus.CANCELLED}),
        ActionStatus.AWAITING_APPROVAL: frozenset({ActionStatus.APPROVED, ActionStatus.CANCELLED}),
        ActionStatus.APPROVED: frozenset({ActionStatus.EXECUTING, ActionStatus.CANCELLED}),
        ActionStatus.EXECUTING: frozenset({ActionStatus.SUCCEEDED, ActionStatus.FAILED}),
        ActionStatus.SUCCEEDED: frozenset(),
        ActionStatus.FAILED: frozenset(),
        ActionStatus.CANCELLED: frozenset(),
    }

    @classmethod
    def assert_transition(cls, current: ActionStatus | str, target: ActionStatus | str) -> None:
        current_status = ActionStatus(current)
        target_status = ActionStatus(target)
        if target_status not in cls.ALLOWED[current_status]:
            allowed = ", ".join(
                item.value for item in sorted(cls.ALLOWED[current_status], key=lambda item: item.value)
            )
            raise InvalidTransitionError(
                f"action transition {current_status.value!r} -> {target_status.value!r} is not allowed; "
                f"allowed: {allowed or 'none'}"
            )
