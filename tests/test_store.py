from __future__ import annotations

import json
import sqlite3
from contextlib import closing
import tempfile
import unittest
from pathlib import Path

from lpos_engine.canonical import new_id
from lpos_engine.errors import ConcurrencyError
from lpos_engine.models import (
    ActionPlan,
    Artifact,
    InterpretationContract,
    MaterialitySignals,
    TaskEnvelope,
    TaskStatus,
)
from lpos_engine.store import SQLiteStore


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = Path(self.temp.name) / "state.db"
        self.store = SQLiteStore(self.db)
        self.task = TaskEnvelope(
            task_id="TASK-1",
            principal_instruction="Do it",
            lead_guild="Engineering",
            lead_specialist="PROFILE-ENGINEERING",
            required_capabilities=("testing",),
            material=False,
            materiality_basis=("routine_internal_reversible",),
        )
        self.store.create_task(self.task)

    def tearDown(self):
        self.temp.cleanup()

    def test_create_and_get_task(self):
        state = self.store.get_task("TASK-1")
        self.assertEqual(state["envelope"], self.task)
        self.assertEqual(state["status"], TaskStatus.RECEIVED)
        self.assertEqual(state["version"], 0)

    def test_duplicate_task_rejected(self):
        with self.assertRaises(ConcurrencyError):
            self.store.create_task(self.task)

    def test_optimistic_concurrency(self):
        version = self.store.transition_task("TASK-1", TaskStatus.PLANNED, expected_version=0)
        self.assertEqual(version, 1)
        with self.assertRaises(ConcurrencyError):
            self.store.transition_task("TASK-1", TaskStatus.EXECUTING, expected_version=0)

    def test_events_are_append_only_at_database_layer(self):
        with closing(sqlite3.connect(self.db)) as conn:
            with self.assertRaises(sqlite3.DatabaseError):
                conn.execute("UPDATE events SET event_type = 'tampered'")
            with self.assertRaises(sqlite3.DatabaseError):
                conn.execute("DELETE FROM events")

    def test_interpretation_versions_and_latest(self):
        contract = InterpretationContract(
            task_id="TASK-1",
            instruction_verbatim="Do it",
            interpretation="Do exactly it",
            invariants=(),
            conflicts=(),
            verification_plan=("test",),
            spec_ref=None,
        )
        self.assertEqual(self.store.save_interpretation(contract), 1)
        changed = InterpretationContract.from_dict(
            {**contract.to_dict(), "interpretation": "Do only it"}
        )
        self.assertEqual(self.store.save_interpretation(changed), 2)
        self.assertEqual(self.store.get_interpretation("TASK-1"), changed)
        events = self.store.list_events(stream_id="TASK-1")
        self.assertEqual(sum(e["event_type"] == "interpretation.recorded" for e in events), 2)

    def test_artifact_insert_is_idempotent_for_same_hash(self):
        artifact = Artifact.create(
            artifact_id="ART-1",
            task_id="TASK-1",
            media_type="text/plain",
            content="same",
        )
        self.store.save_artifact(artifact)
        self.store.save_artifact(artifact)
        events = self.store.list_events(stream_type="artifact")
        self.assertEqual(len(events), 1)

    def test_action_idempotency_key_binds_one_exact_action(self):
        first = ActionPlan.create(
            action_id="ACT-1",
            task_id="TASK-1",
            kind="filesystem_write",
            parameters={"path": "a", "content": "x"},
            external=False,
            reversible=True,
            idempotency_key="same-key",
        )
        self.store.create_action(first)
        second_same = ActionPlan.create(
            action_id="ACT-2",
            task_id="TASK-1",
            kind="filesystem_write",
            parameters={"path": "a", "content": "x"},
            external=False,
            reversible=True,
            idempotency_key="same-key",
        )
        stored = self.store.create_action(second_same)
        self.assertEqual(stored.action_id, first.action_id)
        self.assertEqual(stored.action_hash, first.action_hash)
        action_events = self.store.list_events(stream_type="action")
        self.assertEqual(len(action_events), 1)

    def test_export_jsonl_contains_valid_events(self):
        out = self.store.export_jsonl(Path(self.temp.name) / "events.jsonl")
        lines = out.read_text(encoding="utf-8").splitlines()
        self.assertTrue(lines)
        self.assertEqual(json.loads(lines[0])["event_type"], "task.created")

    def test_operation_claim_rejects_concurrent_owner(self):
        self.store.claim_operation(so_id="SO-1", run_id="RUN-1", idempotency_key="SO-1:date")
        with self.assertRaises(ConcurrencyError):
            self.store.claim_operation(so_id="SO-1", run_id="RUN-2", idempotency_key="SO-1:date")
