"""LPOS-15: monitor/compliance state files must be created 0600, not world-readable.

Mirrors the audit reproduction: under umask 022 the earlier build wrote
monitor/*.json and compliance/*.jsonl world-readable (0644). These regressions
run real audit writes and assert the files are group/other-tight, and that
audit_state_permissions() flags a deliberately-widened file.
"""

from __future__ import annotations

import json
import os
import stat
import tempfile
import unittest
from pathlib import Path

from lpos_engine.store import audit_state_permissions


def _mode(path: Path) -> int:
    return stat.S_IMODE(os.stat(path).st_mode)


@unittest.skipUnless(os.name == "posix", "POSIX file modes")
class StatePermissionTests(unittest.TestCase):
    def setUp(self) -> None:
        self._umask = os.umask(0o022)  # the audit's umask

    def tearDown(self) -> None:
        os.umask(self._umask)

    def test_monitor_and_compliance_state_created_0600(self) -> None:
        from lpos_engine.compliance.audit import run_audit as compliance_audit
        from lpos_engine.monitor.audit import run_audit as monitor_audit

        with tempfile.TemporaryDirectory() as directory:
            hermes = Path(directory) / "hermes"
            os.environ["LPOS_HERMES_ROOT"] = str(hermes)
            try:
                monitor_audit(hermes)
                compliance_audit(Path.cwd(), hermes)
            finally:
                os.environ.pop("LPOS_HERMES_ROOT", None)

            for rel in ("monitor/status.json", "monitor/state.json",
                        "compliance/status.json", "compliance/history.jsonl"):
                path = hermes / rel
                if path.is_file():
                    self.assertEqual(_mode(path) & 0o077, 0, f"{rel} is group/other readable")

            report = audit_state_permissions(hermes)
            self.assertEqual(report["status"], "ok", report)

    def test_audit_flags_a_widened_state_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            hermes = Path(directory) / "hermes"
            (hermes / "monitor").mkdir(parents=True)
            widened = hermes / "monitor" / "status.json"
            widened.write_text(json.dumps({"overall": "ok"}))
            os.chmod(widened, 0o644)
            report = audit_state_permissions(hermes)
            self.assertEqual(report["status"], "insecure")
            self.assertTrue(any(f["path"].endswith("status.json") for f in report["insecure_files"]))


if __name__ == "__main__":
    unittest.main()
