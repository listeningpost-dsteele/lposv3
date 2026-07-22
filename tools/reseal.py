#!/usr/bin/env python3
"""Regenerate RELEASE-MANIFEST.json and SHA256SUMS over the release tree.

Uses the same immutable-file rules as verify_release.py, so a reseal followed by
verification is always self-consistent. Run from anywhere:

    python tools/reseal.py
"""

from __future__ import annotations

import datetime
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IGNORED_TOP_LEVEL = {".venv", "state", ".pytest_cache", "dist", "build"}
IGNORED_NAMES = {"RELEASE-MANIFEST.json", "SHA256SUMS"}


def sha256(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def main() -> int:
    release = json.loads((ROOT / "RELEASE.json").read_text(encoding="utf-8"))
    files: dict[str, str] = {}
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(ROOT)
        if relative.parts and relative.parts[0] in IGNORED_TOP_LEVEL:
            continue
        if "__pycache__" in relative.parts or path.suffix == ".pyc":
            continue
        if relative.name in IGNORED_NAMES:
            continue
        files[relative.as_posix()] = sha256(path)

    manifest = {
        "archive": release["archive"],
        "distribution_type": release["distribution_type"],
        "file_count": len(files),
        "files": files,
        "generated_at": datetime.datetime.now(datetime.UTC)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
        "hash_algorithm": "sha256",
        "name": release["name"],
        "version": release["version"],
    }
    (ROOT / "RELEASE-MANIFEST.json").write_text(
        json.dumps(manifest, indent=1, sort_keys=True) + "\n", encoding="utf-8"
    )
    checksums = "".join(f"{digest}  {name}\n" for name, digest in sorted(files.items()))
    checksums += f"{sha256(ROOT / 'RELEASE-MANIFEST.json')}  RELEASE-MANIFEST.json\n"
    (ROOT / "SHA256SUMS").write_text(checksums, encoding="utf-8")
    print(f"resealed {len(files)} files at version {release['version']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
