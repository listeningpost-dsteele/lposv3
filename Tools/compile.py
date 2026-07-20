#!/usr/bin/env python3
"""Deterministic LPOS compiler: Source/v3 -> Build/Hermes.

Architecture is the source of truth (LPOS-020); Build/Hermes is generated.
Usage:
  python3 Tools/compile.py            # write Build/Hermes from Source/v3
  python3 Tools/compile.py --check    # verify Build/Hermes == compile(Source/v3)
"""
import json, sys, hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "Source/v3"
OUT = ROOT / "Build/Hermes"
SEP = "\n---\n\n## Source: "

def compile_book(book, spec):
    d = SRC / spec["dir"]
    parts = [(d / "_header.md").read_text()]
    for e in spec["entries"]:
        parts.append(f"`{e['source']}`\n\n" + (d / e["file"]).read_text())
    return SEP.join(parts)

def build():
    manifest = json.loads((SRC / "BOOKS.json").read_text())
    out = {}
    for book, spec in manifest["books"].items():
        out[book] = compile_book(book, spec)
    for s in manifest["standalone"]:
        out[s] = (SRC / "standalone" / s).read_text()
    return out

def main():
    out = build()
    if "--check" in sys.argv:
        bad = []
        for rel, text in out.items():
            p = OUT / rel
            if not p.exists() or p.read_text() != text:
                bad.append(rel)
        if bad:
            print("MISMATCH: compiled output differs from Build/Hermes for:",
                  *bad, sep="\n- "); sys.exit(1)
        print(f"OK: compile(Source/v3) == Build/Hermes ({len(out)} files, byte-exact)")
        return
    for rel, text in out.items():
        p = OUT / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    print(f"wrote {len(out)} files to Build/Hermes")

if __name__ == "__main__":
    main()
