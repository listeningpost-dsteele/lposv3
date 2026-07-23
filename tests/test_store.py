from __future__ import annotations

import json
import os
import sqlite3
from contextlib import closing
import tempfile
import unittest
from pathlib import Path

from lpos_engine.canonical import new_id, text_digest, utc_now
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


@unittest.skipUnless(os.name == "posix", "POSIX file modes")
class StoreFileModeTests(unittest.TestCase):
    """LPOS-07: state files must not be group/other readable under any umask."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.old_umask = os.umask(0o022)

    def tearDown(self):
        os.umask(self.old_umask)
        self.temp.cleanup()

    def test_fresh_database_and_parent_dirs_are_restrictive_despite_umask(self):
        db = self.root / "state" / "nested" / "lpos.db"
        SQLiteStore(db)
        self.assertEqual(db.stat().st_mode & 0o777, 0o600)
        self.assertEqual(db.parent.stat().st_mode & 0o777, 0o700)
        self.assertEqual(db.parent.parent.stat().st_mode & 0o777, 0o700)

    def test_existing_world_readable_database_is_repaired_with_audit_event(self):
        db = self.root / "lpos.db"
        SQLiteStore(db)
        os.chmod(db, 0o644)
        store = SQLiteStore(db)
        self.assertEqual(db.stat().st_mode & 0o777, 0o600)
        events = store.list_events(stream_type="store")
        repairs = [e for e in events if e["event_type"] == "store.permissions_repaired"]
        self.assertEqual(len(repairs), 1)
        self.assertEqual(repairs[0]["payload"]["previous_mode"], "0644")
        self.assertEqual(repairs[0]["payload"]["repaired_mode"], "0600")
        self.assertTrue(store.verify_event_chain()["ok"])


class EventChainTests(unittest.TestCase):
    """LPOS-08: the audit event stream is hash-chained and verifiable."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = Path(self.temp.name) / "state.db"
        self.store = SQLiteStore(self.db)
        for index in range(3):
            self.store.create_task(
                TaskEnvelope(
                    task_id=f"TASK-{index}",
                    principal_instruction="Do it",
                    lead_guild="Engineering",
                    lead_specialist="PROFILE-ENGINEERING",
                    required_capabilities=("testing",),
                    material=False,
                    materiality_basis=("routine_internal_reversible",),
                )
            )

    def tearDown(self):
        self.temp.cleanup()

    def test_clean_chain_verifies_and_integrity_check_is_ok(self):
        result = self.store.verify_event_chain()
        self.assertTrue(result["ok"])
        self.assertEqual(result["events"], 3)
        self.assertIsNone(result["first_bad_id"])
        self.assertEqual(self.store.integrity_check(), "ok")
        report = self.store.integrity_report()
        self.assertTrue(report["ok"])
        self.assertEqual(report["pragma"], "ok")

    def test_dropped_trigger_and_payload_edit_are_detected(self):
        # Mirror the audit reproduction: the database owner drops the
        # append-only trigger and edits an event payload in place.
        target = self.store.list_events()[1]
        with closing(sqlite3.connect(self.db)) as conn:
            conn.execute("DROP TRIGGER events_no_update")
            conn.execute(
                "UPDATE events SET payload_json = ? WHERE sequence = ?",
                ('{"tampered":true}', target["sequence"]),
            )
            conn.commit()
        result = self.store.verify_event_chain()
        self.assertFalse(result["ok"])
        self.assertEqual(result["first_bad_id"], target["event_id"])
        self.assertNotEqual(self.store.integrity_check(), "ok")
        self.assertIn(target["event_id"], self.store.integrity_check())
        self.assertFalse(self.store.integrity_report()["ok"])

    def test_migration_applies_to_pre_chain_database_and_backfills(self):
        # Build a database exactly as the pre-chain schema left it: only the
        # initial migration applied and events written without chain links.
        legacy = Path(self.temp.name) / "legacy.db"
        initial_sql = (
            Path(__file__).resolve().parents[1]
            / "src" / "lpos_engine" / "sql" / "001_initial.sql"
        ).read_text(encoding="utf-8")
        with closing(sqlite3.connect(legacy)) as conn:
            conn.executescript(initial_sql)
            conn.execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations ("
                "migration_name TEXT PRIMARY KEY, checksum TEXT NOT NULL, applied_at TEXT NOT NULL)"
            )
            conn.execute(
                "INSERT INTO schema_migrations(migration_name, checksum, applied_at) VALUES (?, ?, ?)",
                ("001_initial.sql", text_digest(initial_sql), utc_now()),
            )
            for index in range(4):
                conn.execute(
                    "INSERT INTO events(event_id, stream_type, stream_id, event_type, payload_json, occurred_at) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (f"EVT-LEGACY{index}", "task", f"TASK-{index}", "task.created", "{}", utc_now()),
                )
            conn.commit()
        if os.name == "posix":
            # Pre-tighten the mode so this test isolates migration backfill
            # from the separate LPOS-07 permission-repair audit event.
            os.chmod(legacy, 0o600)

        store = SQLiteStore(legacy)
        names = [item["migration_name"] for item in store.list_migrations()]
        self.assertEqual(names, ["001_initial.sql", "002_event_chain.sql", "003_sentinel.sql"])
        result = store.verify_event_chain()
        self.assertTrue(result["ok"])
        self.assertEqual(result["events"], 4)
        with closing(sqlite3.connect(legacy)) as conn:
            linked = conn.execute("SELECT COUNT(*) FROM event_chain").fetchone()[0]
        self.assertEqual(linked, 4)

    def test_checkpoints_carry_hmac_tags_when_admin_key_is_configured(self):
        key_file = Path(self.temp.name) / "checkpoint.key"
        key_file.write_bytes(b"admin-held-checkpoint-key")
        keyed = SQLiteStore(self.db, checkpoint_key_path=key_file)
        checkpoint = keyed.write_checkpoint()
        self.assertIsNotNone(checkpoint)
        self.assertIsNotNone(checkpoint["hmac_tag"])
        result = keyed.verify_event_chain()
        self.assertTrue(result["ok"])
        self.assertEqual(result["checkpoints"]["verified"], 1)
        self.assertEqual(result["checkpoints"]["failed"], 0)
