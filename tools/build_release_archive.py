#!/usr/bin/env python3
"""Build the complete LPOS release ZIP from the exact committed tree."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    release = json.loads((ROOT / "RELEASE.json").read_text(encoding="utf-8"))
    archive_name = str(release["archive"])
    version = str(release["version"])
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    if status.strip():
        raise SystemExit("release archive requires a clean committed tree")
    output = ROOT / "dist" / archive_name
    output.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "git",
            "archive",
            "--format=zip",
            f"--prefix=LPOS-v{version}/",
            f"--output={output}",
            "HEAD",
        ],
        cwd=ROOT,
        check=True,
    )
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
