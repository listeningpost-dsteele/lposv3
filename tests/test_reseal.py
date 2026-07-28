from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


def test_reseal_refuses_uncommitted_release_inputs(tmp_path: Path) -> None:
    root = tmp_path / "release"
    (root / "tools").mkdir(parents=True)
    shutil.copy2(Path(__file__).resolve().parents[1] / "tools" / "reseal.py", root / "tools" / "reseal.py")
    (root / "payload.txt").write_text("committed\n", encoding="utf-8")
    (root / "RELEASE.json").write_text(
        json.dumps({"archive": "fixture.zip", "distribution_type": "fixture", "name": "fixture", "version": "1"}) + "\n",
        encoding="utf-8",
    )
    _git(root, "init")
    _git(root, "config", "user.email", "fixture@example.invalid")
    _git(root, "config", "user.name", "Fixture")
    _git(root, "add", ".")
    _git(root, "commit", "-m", "fixture")

    (root / "payload.txt").write_text("dirty\n", encoding="utf-8")
    blocked = subprocess.run([sys.executable, "tools/reseal.py"], cwd=root, capture_output=True, text=True)
    assert blocked.returncode != 0
    assert "refusing to reseal with uncommitted release inputs" in blocked.stderr

    _git(root, "restore", "payload.txt")
    release = json.loads((root / "RELEASE.json").read_text(encoding="utf-8"))
    release["version"] = "1.0.1"
    (root / "RELEASE.json").write_text(json.dumps(release) + "\n", encoding="utf-8")
    allowed = subprocess.run([sys.executable, "tools/reseal.py"], cwd=root, capture_output=True, text=True)
    assert allowed.returncode == 0, allowed.stderr
    assert (root / "RELEASE-MANIFEST.json").is_file()
    assert (root / "SHA256SUMS").is_file()
