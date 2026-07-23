#!/usr/bin/env python3
"""Offline installer for the complete LPOS v4 distribution."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

MINIMUM_PYTHON = (3, 11)


def run(command: list[str], *, cwd: Path) -> None:
    print("\n> " + " ".join(str(part) for part in command), flush=True)
    subprocess.run(command, cwd=cwd, check=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Install the complete LPOS v4 distribution offline.")
    parser.add_argument(
        "--skip-demo",
        action="store_true",
        help="Install and initialize LPOS without running the record-only verification flow.",
    )
    parser.add_argument(
        "--reset-environment",
        action="store_true",
        help="Delete and recreate the local .venv before installation.",
    )
    return parser.parse_args()


def venv_python(venv_root: Path) -> Path:
    if sys.platform == "win32":
        return venv_root / "Scripts" / "python.exe"
    return venv_root / "bin" / "python"


def main() -> int:
    args = parse_args()
    if sys.version_info < MINIMUM_PYTHON:
        required = ".".join(str(part) for part in MINIMUM_PYTHON)
        current = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        print(f"ERROR: Python {required}+ is required; found {current}.", file=sys.stderr)
        return 2

    root = Path(__file__).resolve().parent
    try:
        release = json.loads((root / "RELEASE.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(f"ERROR: RELEASE.json is missing or invalid: {exc}", file=sys.stderr)
        return 2

    wheel_name = release.get("wheel")
    if not isinstance(wheel_name, str):
        print("ERROR: RELEASE.json does not name the bundled wheel.", file=sys.stderr)
        return 2
    wheel = root / "Packages" / wheel_name
    venv_root = root / ".venv"
    state_root = root / "state"

    run([sys.executable, str(root / "verify_release.py")], cwd=root)

    if args.reset_environment and venv_root.exists():
        print("\nRemoving the existing local Python environment...", flush=True)
        shutil.rmtree(venv_root)

    if not venv_root.exists():
        print("\nCreating the local LPOS Python environment...", flush=True)
        run([sys.executable, "-m", "venv", str(venv_root)], cwd=root)
    else:
        print("\nUsing the existing .venv directory.", flush=True)

    python = venv_python(venv_root)
    if not python.is_file():
        print(f"ERROR: virtual-environment Python was not created at {python}.", file=sys.stderr)
        return 2

    run(
        [
            str(python),
            "-m",
            "pip",
            "install",
            "--no-index",
            "--force-reinstall",
            str(wheel),
        ],
        cwd=root,
    )
    run([str(python), "-m", "pip", "check"], cwd=root)
    run([str(python), "-m", "lpos_engine", "version"], cwd=root)
    run([str(python), "-m", "lpos_engine", "validate-schemas"], cwd=root)

    state_root.mkdir(parents=True, exist_ok=True)
    database = state_root / "lpos.db"
    run([str(python), "-m", "lpos_engine", "init", "--db", str(database)], cwd=root)
    run([str(python), "-m", "lpos_engine", "doctor", "--db", str(database)], cwd=root)

    verification_status = "skipped"
    if not args.skip_demo:
        verification_workspace = state_root / "verification"
        if verification_workspace.exists():
            shutil.rmtree(verification_workspace)
        run(
            [
                str(python),
                "-m",
                "lpos_engine",
                "demo",
                "--workspace",
                str(verification_workspace),
            ],
            cwd=root,
        )
        verification_status = "passed"

    installation = {
        "name": release["name"],
        "version": release["version"],
        "distribution_type": release["distribution_type"],
        "installed_at": datetime.now(timezone.utc).isoformat(),
        "python": sys.version.split()[0],
        "database": str(database.relative_to(root)),
        "verification": verification_status,
        "external_action_default": release["external_action_default"],
    }
    (state_root / "INSTALLATION.json").write_text(
        json.dumps(installation, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print("\nLPOS v4.3.0 installation completed successfully.")
    print(f"  Operating system: {root}")
    print(f"  Transactional state: {database}")
    print(f"  Verification flow: {verification_status}")
    print(f"  External actions: {release['external_action_default']} by default")
    if sys.platform == "win32":
        command = r".venv\Scripts\lpos.exe doctor --db state\lpos.db"
    else:
        command = ".venv/bin/lpos doctor --db state/lpos.db"
    print(f"\nRun this health check at any time:\n  {command}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as exc:
        print(f"\nERROR: installation command failed with exit code {exc.returncode}.", file=sys.stderr)
        raise SystemExit(exc.returncode) from exc
