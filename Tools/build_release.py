#!/usr/bin/env python3
"""Deterministic release builder.

Builds Build/LPOS-Hermes-Compact-v3.3.zip from Build/Hermes with fixed
timestamps (reproducible bytes), then writes MANIFEST.json with the version
and a sha256 for every repository file.

Usage: build_release.py <version> [--check]
--check rebuilds the zip in memory and fails if it differs from the committed
zip or if any manifest hash is stale.
"""
import hashlib, io, json, sys, zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
H = ROOT / "Build/Hermes"
ZIP = ROOT / "Build/LPOS-Hermes-Compact-v3.3.zip"
TOP = "LPOS-Hermes-Compact-v3.3"
STAMP = (2026, 1, 1, 0, 0, 0)

def build_zip_bytes():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(H.rglob("*")):
            if p.is_file():
                zi = zipfile.ZipInfo(f"{TOP}/{p.relative_to(H)}", STAMP)
                zi.external_attr = 0o644 << 16
                z.writestr(zi, p.read_bytes(), zipfile.ZIP_DEFLATED)
    return buf.getvalue()

def manifest(version):
    files = sorted(str(p.relative_to(ROOT)) for p in ROOT.rglob("*")
                   if p.is_file() and ".git" not in p.parts
                   and p.name != "MANIFEST.json")
    return {"name": "Listening Post Operating System Compact Repository",
            "version": version, "file_count": len(files) + 1,
            "sha256": {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest()
                       for f in files}}

def main():
    version = sys.argv[1]
    data = build_zip_bytes()
    if "--check" in sys.argv:
        ok = ZIP.exists() and ZIP.read_bytes() == data
        if not ok:
            print("FAIL: committed zip differs from deterministic rebuild")
            sys.exit(1)
        want = manifest(version)["sha256"]
        have = json.loads((ROOT / "MANIFEST.json").read_text()).get("sha256", {})
        if want != have:
            diff = {k for k in set(want) | set(have) if want.get(k) != have.get(k)}
            print("FAIL: manifest hashes stale for:", *sorted(diff)[:10], sep="\n- ")
            sys.exit(1)
        print("OK: zip reproducible and manifest hashes current")
        return
    ZIP.write_bytes(data)
    (ROOT / "MANIFEST.json").write_text(json.dumps(manifest(version), indent=1) + "\n")
    print(f"built {ZIP.name} ({len(data)} bytes) and MANIFEST.json v{version}")

if __name__ == "__main__":
    main()
