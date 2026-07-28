from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from lpos_engine.cli import _release_integrity


class ReleaseIntegrityDoctorTests(unittest.TestCase):
    def test_explicit_missing_release_root_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = _release_integrity(Path(tmp))
        self.assertEqual(result["status"], "failed")
        self.assertIn("verify_release.py is missing", result["detail"])

    def test_verifier_pass_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "verify_release.py").write_text("print('verified')\n", encoding="utf-8")
            result = _release_integrity(root)
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["returncode"], 0)
        self.assertIn("verified", result["detail"])

    def test_verifier_failure_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "verify_release.py").write_text("raise SystemExit(7)\n", encoding="utf-8")
            result = _release_integrity(root)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["returncode"], 7)

    def test_no_detected_release_is_not_applicable(self):
        with tempfile.TemporaryDirectory() as prefix_tmp, tempfile.TemporaryDirectory() as cwd_tmp:
            with patch("lpos_engine.cli.sys.prefix", prefix_tmp), patch("lpos_engine.cli.Path.cwd", return_value=Path(cwd_tmp)):
                result = _release_integrity()
        self.assertEqual(result["status"], "not_applicable")


if __name__ == "__main__":
    unittest.main()
