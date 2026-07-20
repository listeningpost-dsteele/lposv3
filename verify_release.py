#!/usr/bin/env python3
"""Verify the complete LPOS v4 release before installation."""

from __future__ import annotations

import hashlib
import json
import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent
IGNORED_TOP_LEVEL = {".git", ".venv", "state", ".pytest_cache", "dist", "build"}
IGNORED_NAMES = {".gitignore", "RELEASE-MANIFEST.json", "SHA256SUMS"}


def sha256(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def relative_files() -> set[str]:
    result: set[str] = set()
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(ROOT)
        if relative.parts and relative.parts[0] in IGNORED_TOP_LEVEL:
            continue
        if "__pycache__" in relative.parts or path.suffix == ".pyc":
            continue
        if any(part.endswith(".egg-info") for part in relative.parts):
            continue
        if relative.name in IGNORED_NAMES:
            continue
        result.add(relative.as_posix())
    return result


def fail(message: str, failures: list[str]) -> None:
    failures.append(message)


def main() -> int:
    failures: list[str] = []
    manifest_path = ROOT / "RELEASE-MANIFEST.json"
    release_path = ROOT / "RELEASE.json"
    if not manifest_path.is_file():
        print("ERROR: RELEASE-MANIFEST.json is missing.", file=sys.stderr)
        return 1
    if not release_path.is_file():
        print("ERROR: RELEASE.json is missing.", file=sys.stderr)
        return 1

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        release = json.loads(release_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(f"ERROR: release metadata is invalid: {exc}", file=sys.stderr)
        return 1

    checksum_path = ROOT / "SHA256SUMS"
    if not checksum_path.is_file():
        fail("SHA256SUMS is missing", failures)
    else:
        checksum_entries: dict[str, str] = {}
        for line_number, raw in enumerate(checksum_path.read_text(encoding="utf-8").splitlines(), start=1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            try:
                expected_checksum, relative_checksum_path = line.split("  ", 1)
            except ValueError:
                fail(f"SHA256SUMS line {line_number} is malformed", failures)
                continue
            candidate = Path(relative_checksum_path)
            if candidate.is_absolute() or ".." in candidate.parts:
                fail(f"unsafe SHA256SUMS path: {relative_checksum_path}", failures)
                continue
            checksum_entries[relative_checksum_path] = expected_checksum
        manifest_checksum = checksum_entries.get("RELEASE-MANIFEST.json")
        if manifest_checksum != sha256(manifest_path):
            fail("SHA256SUMS does not match RELEASE-MANIFEST.json", failures)

    expected_files = manifest.get("files")
    if not isinstance(expected_files, dict) or not expected_files:
        fail("release manifest has no file hash map", failures)
        expected_files = {}

    for relative, expected_hash in sorted(expected_files.items()):
        candidate = Path(relative)
        if candidate.is_absolute() or ".." in candidate.parts:
            fail(f"unsafe manifest path: {relative}", failures)
            continue
        target = ROOT / candidate
        if not target.is_file():
            fail(f"missing immutable file: {relative}", failures)
            continue
        actual = sha256(target)
        if actual != expected_hash:
            fail(f"hash mismatch: {relative}", failures)
        if checksum_path.is_file() and checksum_entries.get(relative) != expected_hash:
            fail(f"SHA256SUMS and release manifest disagree: {relative}", failures)

    listed = set(expected_files)
    actual_files = relative_files()
    for relative in sorted(actual_files - listed):
        fail(f"unlisted immutable file: {relative}", failures)
    for relative in sorted(listed - actual_files):
        fail(f"manifest entry is not an immutable file: {relative}", failures)

    try:
        project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        project_version = project["project"]["version"]
        package_init = (ROOT / "src" / "lpos_engine" / "__init__.py").read_text(encoding="utf-8")
        match = re.search(r'^__version__\s*=\s*["\']([^"\']+)["\']', package_init, re.MULTILINE)
        package_version = match.group(1) if match else None
        registry_root = json.loads((ROOT / "config" / "default_registry.json").read_text(encoding="utf-8"))
        registry_package = json.loads(
            (ROOT / "src" / "lpos_engine" / "config" / "default_registry.json").read_text(encoding="utf-8")
        )
        workflow_catalog = json.loads(
            (ROOT / "src" / "lpos_engine" / "workflows" / "catalog.json").read_text(encoding="utf-8")
        )
    except (OSError, ValueError, KeyError, TypeError) as exc:
        fail(f"integrated metadata could not be parsed: {exc}", failures)
    else:
        versions = {
            str(release.get("version")),
            str(manifest.get("version")),
            str(project_version),
            str(package_version),
            str(registry_root.get("os_version")),
            str(registry_package.get("os_version")),
            str(workflow_catalog.get("os_version")),
        }
        if versions != {"4.1.0"}:
            fail(f"version fields are not synchronized: {sorted(versions)}", failures)
        if release.get("distribution_type") != "integrated":
            fail("RELEASE.json does not declare an integrated distribution", failures)
        if registry_root != registry_package:
            fail("root and packaged capability registries differ", failures)

        specialists = registry_package.get("specialists", [])
        specialist_ids = [item.get("specialist_id") for item in specialists if isinstance(item, dict)]
        expected_specialists = [f"SPECIALIST-{number:03d}" for number in range(1, 33)]
        if specialist_ids != expected_specialists:
            fail("capability registry does not contain canonical SPECIALIST-001 through SPECIALIST-032", failures)

        operations = workflow_catalog.get("operations", [])
        operation_ids = [item.get("so_id") for item in operations if isinstance(item, dict)]
        expected_operations = [f"SO-{number:03d}" for number in range(1, 22)]
        if operation_ids != expected_operations:
            fail("workflow catalog does not contain canonical SO-001 through SO-021", failures)
        for item in operations:
            if not isinstance(item, dict):
                fail("workflow catalog contains a non-object entry", failures)
                continue
            workflow_name = item.get("workflow")
            target = ROOT / "src" / "lpos_engine" / "workflows" / str(workflow_name)
            try:
                workflow = json.loads(target.read_text(encoding="utf-8"))
            except (OSError, ValueError) as exc:
                fail(f"invalid workflow {workflow_name}: {exc}", failures)
                continue
            if workflow.get("so_id") != item.get("so_id"):
                fail(f"workflow identity mismatch: {workflow_name}", failures)
            if not workflow.get("steps"):
                fail(f"workflow has no executable steps: {workflow_name}", failures)

    root_schema_dir = ROOT / "schemas"
    package_schema_dir = ROOT / "src" / "lpos_engine" / "schemas"
    root_schema_names = sorted(path.name for path in root_schema_dir.glob("*.schema.json"))
    package_schema_names = sorted(path.name for path in package_schema_dir.glob("*.schema.json"))
    if root_schema_names != package_schema_names or len(root_schema_names) != 17:
        fail("root and packaged schema sets are not the same 17 schemas", failures)
    else:
        for name in root_schema_names:
            root_path = root_schema_dir / name
            package_path = package_schema_dir / name
            if root_path.read_bytes() != package_path.read_bytes():
                fail(f"root and packaged schema differ: {name}", failures)
            try:
                json.loads(root_path.read_text(encoding="utf-8"))
            except ValueError as exc:
                fail(f"schema is not valid JSON: {name}: {exc}", failures)

    benchmark_root = ROOT / "src" / "lpos_engine" / "evals"
    try:
        benchmark_catalog = json.loads((benchmark_root / "catalog.json").read_text(encoding="utf-8"))
        benchmark_entries = benchmark_catalog["benchmarks"]
    except (OSError, ValueError, KeyError, TypeError) as exc:
        fail(f"benchmark catalog is missing or invalid: {exc}", failures)
        benchmark_entries = []
    expected_benchmark_ids = [
        *(f"BENCH-S{number:03d}" for number in range(1, 33)),
        *(f"BENCH-O{number:03d}" for number in range(1, 22)),
    ]
    actual_benchmark_ids = [item.get("id") for item in benchmark_entries if isinstance(item, dict)]
    if actual_benchmark_ids != expected_benchmark_ids:
        fail("benchmark catalog does not contain 32 specialist and 21 Standing Operation fixtures", failures)
    for item in benchmark_entries:
        if not isinstance(item, dict):
            fail("benchmark catalog contains a non-object entry", failures)
            continue
        fixture_name = item.get("fixture")
        target = benchmark_root / str(fixture_name)
        try:
            benchmark = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            fail(f"invalid benchmark fixture {fixture_name}: {exc}", failures)
            continue
        required = {
            "id", "component_type", "component_id", "objective", "fixture_version",
            "scenario", "inputs", "expected", "success_criteria", "failure_criteria",
            "evaluation", "evidence",
        }
        if required - set(benchmark):
            fail(f"benchmark fixture is incomplete: {fixture_name}", failures)
        if benchmark.get("id") != item.get("id"):
            fail(f"benchmark identity mismatch: {fixture_name}", failures)

    kernel = ROOT / "src" / "lpos_engine" / "spec" / "CHIP-KERNEL.md"
    if not kernel.is_file() or "# Chip Kernel v4.1.0" not in kernel.read_text(encoding="utf-8"):
        fail("the packaged v4 kernel is missing or has the wrong version", failures)

    wheel_name = release.get("wheel")
    if not isinstance(wheel_name, str) or not (ROOT / "Packages" / wheel_name).is_file():
        fail("the offline LPOS v4 wheel named by RELEASE.json is missing", failures)

    # User-facing release text must describe one v4 system rather than a layered historical bundle.
    retired_markers = (
        "reference" + " engine",
        "Build" + "/Hermes",
        "LPOS " + "v3",
        "v3." + "3",
        "patch" + "-only",
        "source " + "overlay",
    )
    text_targets = [ROOT / "README.md", ROOT / "RELEASE.json", *sorted((ROOT / "docs").glob("*.md"))]
    text_targets.extend(sorted((ROOT / "src" / "lpos_engine" / "spec").rglob("*.md")))
    for target in text_targets:
        text = target.read_text(encoding="utf-8").casefold()
        for marker in retired_markers:
            if marker.casefold() in text:
                fail(f"retired split-release framing appears in {target.relative_to(ROOT)}", failures)

    if failures:
        print("LPOS v4 release verification FAILED:", file=sys.stderr)
        for item in failures:
            print(f"  - {item}", file=sys.stderr)
        return 1

    print(
        "LPOS v4 release verification passed: "
        f"{len(expected_files)} immutable files, 32 specialists, 21 Standing Operations, 53 benchmarks, 17 schemas."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
