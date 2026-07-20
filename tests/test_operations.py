from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from lpos_engine.errors import ConcurrencyError, ValidationError
from lpos_engine.models import OperationResult, WorkflowDefinition, WorkflowStep
from lpos_engine.operations import StandingOperationRunner
from lpos_engine.store import SQLiteStore


class OperationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = SQLiteStore(Path(self.temp.name) / "state.db")
        self.calls: list[str] = []

        def collect(ctx):
            self.calls.append("collect")
            return {"items": [1, 2]}

        def analyze(ctx):
            self.calls.append("analyze")
            return {"count": len(ctx["dependencies"]["STEP-COLLECT"]["items"])}

        self.runner = StandingOperationRunner(
            self.store,
            handlers={"collect": collect, "analyze": analyze},
        )
        self.workflow = WorkflowDefinition(
            so_id="SO-6",
            model_class="routine",
            steps=(
                WorkflowStep("STEP-COLLECT", "collect"),
                WorkflowStep("STEP-ANALYZE", "analyze", ("STEP-COLLECT",)),
            ),
        )

    def tearDown(self):
        self.temp.cleanup()

    def test_dag_executes_in_dependency_order(self):
        result = self.runner.run(self.workflow, scheduled_for="2026-07-20")
        self.assertEqual(self.calls, ["collect", "analyze"])
        self.assertEqual(result.run.result, OperationResult.OK)
        self.assertEqual(result.outputs["STEP-ANALYZE"]["count"], 2)

    def test_retry_is_idempotent_and_does_not_reexecute(self):
        first = self.runner.run(self.workflow, scheduled_for="2026-07-20")
        second = self.runner.run(self.workflow, scheduled_for="2026-07-20")
        self.assertEqual(first.run, second.run)
        self.assertEqual(self.calls, ["collect", "analyze"])

    def test_exactly_one_evidence_record_per_run(self):
        result = self.runner.run(self.workflow, scheduled_for="2026-07-20")
        evidence = self.store.list_evidence()
        self.assertEqual(len(evidence), 1)
        self.assertEqual(evidence[0].id, result.run.evidence_id)

    def test_error_is_explicit_and_still_records_evidence(self):
        def fail(ctx):
            raise RuntimeError("boom")

        runner = StandingOperationRunner(self.store, handlers={"fail": fail})
        workflow = WorkflowDefinition(
            so_id="SO-7",
            model_class="routine",
            steps=(WorkflowStep("STEP-FAIL", "fail"),),
        )
        result = runner.run(workflow, scheduled_for="2026-07-20")
        self.assertEqual(result.run.result, OperationResult.ERROR)
        self.assertIn("boom", result.outputs["__error__"]["error"])
        self.assertEqual(len(self.store.list_evidence()), 1)

    def test_continue_on_error_allows_following_step(self):
        def fail(ctx):
            raise RuntimeError("expected")

        def after(ctx):
            return {"continued": True}

        runner = StandingOperationRunner(self.store, handlers={"fail": fail, "after": after})
        workflow = WorkflowDefinition(
            so_id="SO-8",
            model_class="routine",
            steps=(
                WorkflowStep("STEP-FAIL", "fail", continue_on_error=True),
                WorkflowStep("STEP-AFTER", "after", ("STEP-FAIL",)),
            ),
        )
        result = runner.run(workflow, scheduled_for="2026-07-20")
        self.assertEqual(result.run.result, OperationResult.OK)
        self.assertTrue(result.outputs["STEP-AFTER"]["continued"])

    def test_missing_handler_becomes_error_run(self):
        runner = StandingOperationRunner(self.store, handlers={})
        workflow = WorkflowDefinition(
            so_id="SO-9",
            model_class="routine",
            steps=(WorkflowStep("STEP-X", "missing"),),
        )
        result = runner.run(workflow, scheduled_for="2026-07-20")
        self.assertEqual(result.run.result, OperationResult.ERROR)
        self.assertIn("no Standing Operation handler", result.outputs["__error__"]["error"])

    def test_unknown_dependency_rejected_at_definition(self):
        with self.assertRaises(ValidationError):
            WorkflowDefinition(
                so_id="SO-10",
                model_class="routine",
                steps=(WorkflowStep("STEP-A", "a", ("STEP-MISSING",)),),
            )

    def test_store_claim_prevents_concurrent_duplicate(self):
        self.store.claim_operation(
            so_id="SO-11",
            run_id="RUN-OTHER",
            idempotency_key="SO-11:2026-07-20",
        )
        workflow = WorkflowDefinition(
            so_id="SO-11",
            model_class="routine",
            steps=(WorkflowStep("STEP-X", "collect"),),
        )
        with self.assertRaises(ConcurrencyError):
            self.runner.run(workflow, scheduled_for="2026-07-20")
