from __future__ import annotations

import unittest

from lpos_engine.errors import InvalidTransitionError
from lpos_engine.materiality import MaterialityPolicy
from lpos_engine.models import MaterialitySignals, TaskStatus
from lpos_engine.state_machine import TaskStateMachine


class MaterialityTests(unittest.TestCase):
    def test_each_normative_signal_is_material(self):
        fields = (
            "external_or_irreversible",
            "changes_approved_artifact",
            "customer_or_public_facing",
            "legal_financial_security_privacy",
            "strategy_brand_or_taste",
            "modifies_long_lived_specification",
            "failure_cost_exceeds_review_cost",
            "uncertain",
        )
        for field in fields:
            with self.subTest(field=field):
                decision = MaterialityPolicy.evaluate(MaterialitySignals(**{field: True}))
                self.assertTrue(decision.material)
                self.assertTrue(decision.basis)

    def test_routine_internal_work_is_not_material(self):
        decision = MaterialityPolicy.evaluate(MaterialitySignals())
        self.assertFalse(decision.material)
        self.assertEqual(decision.basis, ("routine_internal_reversible",))

    def test_principal_can_designate_nonmaterial(self):
        decision = MaterialityPolicy.evaluate(
            MaterialitySignals(
                external_or_irreversible=True,
                explicit_principal_designation=False,
                designation_note="recorded decision",
            )
        )
        self.assertFalse(decision.material)
        self.assertIn("principal_designation", decision.basis[0])

    def test_principal_can_designate_material(self):
        decision = MaterialityPolicy.evaluate(
            MaterialitySignals(explicit_principal_designation=True)
        )
        self.assertTrue(decision.material)


class StateMachineTests(unittest.TestCase):
    def test_expected_happy_path(self):
        path = [
            TaskStatus.RECEIVED,
            TaskStatus.INTERPRETED,
            TaskStatus.PLANNED,
            TaskStatus.EXECUTING,
            TaskStatus.REVIEWING,
            TaskStatus.COMPLETED,
        ]
        for current, target in zip(path, path[1:]):
            TaskStateMachine.assert_transition(current, target)

    def test_routine_task_can_skip_contract_state(self):
        TaskStateMachine.assert_transition(TaskStatus.RECEIVED, TaskStatus.PLANNED)

    def test_correction_loop(self):
        TaskStateMachine.assert_transition(TaskStatus.REVIEWING, TaskStatus.CORRECTION_REQUIRED)
        TaskStateMachine.assert_transition(TaskStatus.CORRECTION_REQUIRED, TaskStatus.EXECUTING)

    def test_approval_loop(self):
        TaskStateMachine.assert_transition(TaskStatus.EXECUTING, TaskStatus.AWAITING_APPROVAL)
        TaskStateMachine.assert_transition(TaskStatus.AWAITING_APPROVAL, TaskStatus.EXECUTING)

    def test_terminal_task_cannot_reopen(self):
        with self.assertRaises(InvalidTransitionError):
            TaskStateMachine.assert_transition(TaskStatus.COMPLETED, TaskStatus.EXECUTING)

    def test_invalid_shortcut_rejected(self):
        with self.assertRaises(InvalidTransitionError):
            TaskStateMachine.assert_transition(TaskStatus.RECEIVED, TaskStatus.COMPLETED)
