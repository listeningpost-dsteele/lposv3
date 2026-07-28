from __future__ import annotations

import io
import json
import subprocess
import sys
import tarfile
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ReleasePortabilityTests(unittest.TestCase):
    def test_bundled_wheel_exactly_matches_package_source(self) -> None:
        release = json.loads((ROOT / "RELEASE.json").read_text(encoding="utf-8"))
        source_root = ROOT / "src" / "lpos_engine"
        source_files = {
            path.relative_to(ROOT / "src").as_posix(): path.read_bytes()
            for path in source_root.rglob("*")
            if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
        }
        with zipfile.ZipFile(ROOT / "Packages" / release["wheel"]) as wheel:
            wheel_files = {
                name: wheel.read(name)
                for name in wheel.namelist()
                if name.startswith("lpos_engine/") and not name.endswith("/")
            }
        self.assertEqual(set(wheel_files), set(source_files))
        self.assertEqual(wheel_files, source_files)

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
