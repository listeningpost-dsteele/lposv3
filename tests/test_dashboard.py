from __future__ import annotations

import json
import sqlite3
import tempfile
import time
import unittest
from pathlib import Path

from lpos_engine.dashboard import DEFAULT_PORT
from lpos_engine.dashboard.scanner import scan
from lpos_engine.dashboard.server import default_config, merged_state, read_meta, state_path, write_config, write_meta


class DashboardModuleTests(unittest.TestCase):
    def test_scanner_reads_kanban_tasks_and_workspace_deliverables(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace = root / "workspaces" / "alpha"
            workspace.mkdir(parents=True)
            (workspace / "report.md").write_text("done", encoding="utf-8")
            db = root / "kanban.db"
            con = sqlite3.connect(db)
            con.execute(
                "create table tasks (id text primary key, title text not null, body text, assignee text, status text not null, priority integer, created_by text, created_at integer not null, started_at integer, completed_at integer, workspace_kind text, workspace_path text, branch_name text, project_id text, claim_lock text, claim_expires integer, tenant text, result text, idempotency_key text, consecutive_failures integer, worker_pid integer, last_failure_error text, max_runtime_seconds integer, last_heartbeat_at integer, current_run_id integer, workflow_template_id text, current_step_key text, skills text, model_override text, max_retries integer, goal_mode integer, goal_max_turns integer, session_id text, block_kind text, block_recurrences integer)"
            )
            con.execute(
                "insert into tasks (id,title,body,assignee,status,created_at,workspace_path) values (?,?,?,?,?,?,?)",
                ("t_1", "Alpha Build", "Ship the dashboard", "Chip", "running", int(time.time()), str(workspace)),
            )
            con.commit()
            con.close()

            items = scan(str(root))
            self.assertEqual(items[0]["id"], "kanban:t_1")
            self.assertEqual(items[0]["name"], "Alpha Build")
            self.assertEqual(items[0]["bucket" if "bucket" in items[0] else "suggestedBucket"], "active")
            self.assertEqual(items[0]["files"][0]["name"], "report.md")

    def test_dashboard_state_survives_corrupt_or_missing_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as state_dir:
            root = Path(directory)
            project = root / "projects" / "research-alpha"
            project.mkdir(parents=True)
            (project / "project.json").write_text(json.dumps({"name": "Research Alpha", "type": "research"}), encoding="utf-8")
            (project / "brief.md").write_text("brief", encoding="utf-8")
            self.addCleanup(lambda: __import__("os").environ.pop("LPOS_DASHBOARD_STATE_ROOT", None))
            __import__("os").environ["LPOS_DASHBOARD_STATE_ROOT"] = state_dir
            config = default_config(str(root), DEFAULT_PORT, "tester")
            write_config(config)
            state_path().write_text("not json", encoding="utf-8")

            state = merged_state(config)
            self.assertEqual(state["projects"][0]["bucket"], "research")

    def test_expired_snooze_returns_to_previous_bucket(self) -> None:
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as state_dir:
            root = Path(directory)
            project = root / "projects" / "alpha"
            project.mkdir(parents=True)
            (project / "brief.md").write_text("brief", encoding="utf-8")
            self.addCleanup(lambda: __import__("os").environ.pop("LPOS_DASHBOARD_STATE_ROOT", None))
            __import__("os").environ["LPOS_DASHBOARD_STATE_ROOT"] = state_dir
            config = default_config(str(root), DEFAULT_PORT, "tester")
            write_config(config)
            write_meta({"schema_version": 1, "projects": {"projects:alpha": {"bucket": "snoozed", "prevBucket": "research", "snoozeUntil": 1}}})

            state = merged_state(config)
            self.assertEqual(state["projects"][0]["bucket"], "research")
            self.assertIsNotNone(state["projects"][0]["wokeAt"])
            self.assertEqual(read_meta()["projects"]["projects:alpha"]["bucket"], "research")


if __name__ == "__main__":
    unittest.main()
