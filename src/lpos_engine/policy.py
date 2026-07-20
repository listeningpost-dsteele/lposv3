"""Constitutional policy guards enforced outside model prompts."""

from __future__ import annotations

from .errors import PolicyViolation
from .models import ActionStatus, ReviewDecision, TaskEnvelope
from .store import SQLiteStore


class PolicyEngine:
    def __init__(self, store: SQLiteStore) -> None:
        self.store = store

    def assert_ready_to_execute(self, task: TaskEnvelope) -> None:
        if task.material and self.store.get_interpretation(task.task_id) is None:
            raise PolicyViolation("material work cannot execute without an InterpretationContract")
        missing = tuple(task.constraints.get("route_missing_capabilities", ()))
        if missing:
            raise PolicyViolation(
                "task route lacks required capabilities: " + ", ".join(str(item) for item in missing)
            )

    def assert_can_complete(self, task: TaskEnvelope, artifact_hash: str | None) -> None:
        if task.material:
            if self.store.get_interpretation(task.task_id) is None:
                raise PolicyViolation("material task lacks an InterpretationContract")
            if not artifact_hash:
                raise PolicyViolation("material task lacks an artifact")
            review = self.store.get_latest_review(task.task_id, artifact_hash)
            if review is None:
                raise PolicyViolation("material artifact lacks independent review")
            if not review["context_isolated"]:
                raise PolicyViolation("material artifact review was not context-isolated")
            if review["result"].decision is not ReviewDecision.PASS:
                raise PolicyViolation("material artifact did not pass review")

        for action in self.store.list_actions(task.task_id):
            if action["status"] not in {ActionStatus.SUCCEEDED, ActionStatus.CANCELLED}:
                raise PolicyViolation(
                    f"task has unresolved action {action['plan'].action_id}: {action['status'].value}"
                )
