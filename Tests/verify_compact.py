from pathlib import Path
import zipfile, sys

root = Path(__file__).resolve().parents[1]
required = [
    root/"Source/LPOS-Full-Source-v2.0.zip",
    root/"Build/LPOS-Hermes-Compact-v3.0.zip",
    root/"Build/Hermes/LPOS-CORE.md",
    root/"Build/Hermes/CRAFT-STANDARDS.md",
    root/"Build/Hermes/GUILDS.md",
    root/"Build/Hermes/SPECIALISTS.md",
    root/"Build/Hermes/STANDING-OPERATIONS.md",
    root/"Build/Hermes/BENCHMARKS.md",
    root/"Build/Hermes/INSTALL-LPOS-COMPACT.md",
]
missing = [str(p.relative_to(root)) for p in required if not p.exists()]
if missing:
    print("Missing:", *missing, sep="\n- ")
    sys.exit(1)

count = sum(1 for p in root.rglob("*") if p.is_file())
print(f"PASS: compact repository contains {count} files.")
