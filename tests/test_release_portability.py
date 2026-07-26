from __future__ import annotations

import io
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ReleasePortabilityTests(unittest.TestCase):
    def test_exact_committed_tree_verifies_after_clean_export(self) -> None:
        committed = subprocess.run(
            ["git", "diff", "--quiet", "HEAD", "--"],
            cwd=ROOT,
            check=False,
        )
        if committed.returncode != 0:
            self.skipTest("clean-export verification runs after the release candidate is committed")
        archive = subprocess.run(
            ["git", "archive", "--format=tar", "HEAD"],
            cwd=ROOT,
            capture_output=True,
            check=True,
        ).stdout
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with tarfile.open(fileobj=io.BytesIO(archive), mode="r:") as bundle:
                bundle.extractall(root, filter="data")
            self.assertFalse((root / ".git").exists())
            verified = subprocess.run(
                [sys.executable, "verify_release.py"],
                cwd=root,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(verified.returncode, 0, verified.stdout + verified.stderr)


if __name__ == "__main__":
    unittest.main()
