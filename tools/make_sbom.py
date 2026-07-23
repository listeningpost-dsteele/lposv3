#!/usr/bin/env python3
"""Generate a CycloneDX 1.5 SBOM for the LPOS release (LPOS-11).

LPOS has zero runtime dependencies, so the SBOM is small and mostly proves that
fact in a machine-verifiable way: one root component (the lpos-os wheel with its
hash), the optional dev dependencies, and the derived-work attribution
(NOTICE-SKILLOPT.md). Run after tools/reseal.py; writes SBOM.json at the root.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def main() -> int:
    release = json.loads((ROOT / "RELEASE.json").read_text(encoding="utf-8"))
    version = release["version"]
    wheel = ROOT / "Packages" / release["wheel"]
    sbom = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "version": 1,
        "metadata": {
            "component": {
                "type": "application",
                "name": "lpos-os",
                "version": version,
                "supplier": {"name": "Listening Post / LPOS"},
                "licenses": [{"license": {"id": "MIT"}}],
                "hashes": [{"alg": "SHA-256", "content": sha256(wheel)}] if wheel.is_file() else [],
                "purl": f"pkg:pypi/lpos-os@{version}",
            },
            "properties": [
                {"name": "lpos:runtime_dependencies", "value": "none"},
                {"name": "lpos:python_requires", "value": release.get("python_requires", ">=3.11")},
                {"name": "lpos:derived_work_notice", "value": "NOTICE-SKILLOPT.md (Microsoft SkillOpt, MIT, reimplemented — not vendored)"},
            ],
        },
        "components": [
            {"type": "library", "name": "jsonschema", "version": ">=4.20",
             "scope": "optional",
             "description": "dev extra only; structural schema validation is built in and always on"},
            {"type": "library", "name": "pytest", "version": ">=8", "scope": "optional",
             "description": "dev extra only"},
        ],
        "dependencies": [{"ref": f"pkg:pypi/lpos-os@{version}", "dependsOn": []}],
    }
    (ROOT / "SBOM.json").write_text(json.dumps(sbom, indent=2) + "\n", encoding="utf-8")
    print(f"SBOM.json written for lpos-os {version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
