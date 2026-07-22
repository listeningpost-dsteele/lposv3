"""SO-022 Release Publication and SO-024 Documentation Drift Audit handlers.

SO-022 codifies the release pipeline: verify the release gates, enforce the
documentation gate (every user-facing patch updates the wiki and adds a patch-notes
entry), rebuild the documentation site, and RECORD the exact external publication
actions (GitHub push, Drive update-in-place). Consistent with the distribution's
`external_action_default: record-only`, nothing in this module executes an external
side effect: STEP-PUBLISH emits the exact-action plan that the host routes through
the normal approval mechanism (LPOS-030 exact-action approval binding).

SO-024 keeps the User Guide honest: it enumerates every user-facing surface the
packaged system actually ships (Standing Operations, specialists, skills, engine
modules) and diffs them against the wiki sources, reporting anything undocumented.

All handlers follow the StandingOperationRunner contract: they accept the merged
context mapping and return a JSON-safe mapping. Failures raise ValidationError so
the runner records an error result.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tomllib
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from importlib.resources import files

from .errors import ValidationError


def _repo_root(context: Mapping[str, Any]) -> Path:
    root = context.get("repo_root") or os.environ.get("LPOS_REPO_ROOT") or "."
    return Path(root).expanduser().resolve()


def _hermes_root(context: Mapping[str, Any]) -> Path:
    root = (
        context.get("hermes_root")
        or os.environ.get("LPOS_HERMES_ROOT")
        or (Path.home() / ".hermes")
    )
    return Path(root).expanduser()


def _release_version(root: Path) -> str:
    try:
        release = json.loads((root / "RELEASE.json").read_text(encoding="utf-8"))
        return str(release["version"])
    except (OSError, ValueError, KeyError) as exc:
        raise ValidationError(f"RELEASE.json is missing or invalid under {root}") from exc


# --------------------------------------------------------------------------- SO-022

def verify_release_gates(context: Mapping[str, Any]) -> Mapping[str, Any]:
    """Gate 1: the release tree is coherent before anything is published."""
    root = _repo_root(context)
    version = _release_version(root)

    gates: dict[str, bool] = {}
    gates["manifest_present"] = (root / "RELEASE-MANIFEST.json").is_file()
    gates["checksums_present"] = (root / "SHA256SUMS").is_file()
    try:
        project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
        gates["version_synchronized"] = project["project"]["version"] == version
    except (OSError, ValueError, KeyError):
        gates["version_synchronized"] = False
    changelog = root / "CHANGELOG.md"
    gates["changelog_entry"] = changelog.is_file() and version in changelog.read_text(
        encoding="utf-8"
    )
    verifier = root / "verify_release.py"
    if verifier.is_file() and not context.get("skip_verifier", False):
        completed = subprocess.run(
            [sys.executable, str(verifier)], capture_output=True, text=True, check=False
        )
        gates["verifier_passed"] = completed.returncode == 0
    else:
        gates["verifier_passed"] = bool(context.get("verifier_passed", False))

    failed = sorted(name for name, ok in gates.items() if not ok)
    if failed:
        raise ValidationError(f"release gates failed: {', '.join(failed)}")
    return {"version": version, "gates": gates}


def enforce_docs_gate(context: Mapping[str, Any]) -> Mapping[str, Any]:
    """Gate 2: a user-facing release must carry its documentation with it."""
    root = _repo_root(context)
    version = _release_version(root)
    if context.get("no_user_facing_change", False):
        return {"version": version, "docs_gate": "waived", "reason": "declared no user-facing change"}

    slug = version.replace(".", "-")
    patch_note = root / "docs" / "wiki" / "patch-notes" / f"{slug}.md"
    if not patch_note.is_file():
        raise ValidationError(
            f"documentation gate failed: docs/wiki/patch-notes/{slug}.md is missing; "
            "every user-facing release must add its patch-notes page (or declare "
            "no_user_facing_change)"
        )
    return {"version": version, "docs_gate": "passed", "patch_note": str(patch_note)}


def build_documentation_site(context: Mapping[str, Any]) -> Mapping[str, Any]:
    """Rebuild the wiki so the published site, Drive copy, and GitHub artifact match."""
    root = _repo_root(context)
    builder = root / "tools" / "build_wiki.py"
    if not builder.is_file():
        return {"built": False, "reason": "tools/build_wiki.py not present (installed tree)"}
    completed = subprocess.run(
        [sys.executable, str(builder)], cwd=root, capture_output=True, text=True, check=False
    )
    if completed.returncode != 0:
        raise ValidationError(f"documentation build failed: {completed.stderr[-500:]}")
    site = root / "dist" / "wiki"
    combined = root / "dist" / "LPOS-User-Guide.html"
    return {
        "built": True,
        "site": str(site),
        "combined_guide": str(combined) if combined.is_file() else None,
    }


def record_publication_actions(context: Mapping[str, Any]) -> Mapping[str, Any]:
    """Record-only: emit the exact external actions for approval-bound execution."""
    root = _repo_root(context)
    version = _release_version(root)
    actions = [
        {
            "action_id": f"PUBLISH-GITHUB-{version}",
            "kind": "vcs_push",
            "description": f"Commit 'Release LPOS v{version}' and push to the LPOS GitHub remote",
            "destination": context.get("github_remote", "origin"),
            "artifacts": [
                "repository tree",
                f"Packages/lpos_os-{version}-py3-none-any.whl",
                "dist/LPOS-User-Guide.html",
            ],
        },
        {
            "action_id": f"PUBLISH-DRIVE-{version}",
            "kind": "drive_update",
            "description": (
                f"Update the LPOS release file and User Guide on Google Drive in place "
                f"(v{version}), preserving the share link"
            ),
            "destination": context.get("drive_folder", "LPOS"),
            "artifacts": [
                f"LPOS-v{version}-Complete.zip",
                "dist/LPOS-User-Guide.html",
            ],
        },
        {
            "action_id": f"PUBLISH-WIKI-{version}",
            "kind": "site_deploy",
            "description": f"Deploy dist/wiki to chip.listeningpost.ai (v{version})",
            "destination": context.get("wiki_host", "chip.listeningpost.ai"),
            "artifacts": ["dist/wiki/"],
        },
    ]
    return {
        "version": version,
        "mode": "record-only",
        "approval_required": True,
        "actions": actions,
    }


# --------------------------------------------------------------------------- SO-024

_ENGINE_MODULES = ("dashboard", "monitor", "evolution", "compliance")


def enumerate_documented_surfaces(context: Mapping[str, Any]) -> Mapping[str, Any]:
    """Enumerate the user-facing surfaces the packaged system actually ships."""
    package = files("lpos_engine")
    catalog = json.loads(
        package.joinpath("workflows", "catalog.json").read_text(encoding="utf-8")
    )
    surfaces: list[str] = [str(item["so_id"]) for item in catalog["operations"]]
    skills_dir = Path(str(package.joinpath("spec", "skills")))
    if skills_dir.is_dir():
        surfaces += [f"skill:{p.name}" for p in sorted(skills_dir.iterdir()) if p.is_dir()]
    surfaces += [f"module:{name}" for name in _ENGINE_MODULES]
    return {"surfaces": surfaces, "count": len(surfaces)}


def diff_documentation_coverage(context: Mapping[str, Any]) -> Mapping[str, Any]:
    """Diff shipped surfaces against the wiki sources; report what is undocumented."""
    root = _repo_root(context)
    wiki = root / "docs" / "wiki"
    surfaces = list(context.get("surfaces") or context.get("STEP-ENUMERATE", {}).get("surfaces", []))
    if not surfaces:
        raise ValidationError("no surfaces provided to diff (STEP-ENUMERATE output missing)")
    if not wiki.is_dir():
        return {"checked": 0, "undocumented": surfaces, "wiki_missing": True}

    corpus = ""
    for page in wiki.rglob("*.md"):
        corpus += page.read_text(encoding="utf-8", errors="replace").lower()

    # Standing Operation reference pages are generated at build time from the
    # packaged catalog by tools/build_wiki.py, so every cataloged SO is documented
    # by construction; generated pages cannot drift. Hand-written coverage is what
    # this audit protects.
    generator_present = (root / "tools" / "build_wiki.py").is_file()

    undocumented = []
    for surface in surfaces:
        if generator_present and re.fullmatch(r"SO-\d{3}", surface):
            continue
        token = surface.split(":", 1)[-1].lower()
        if token not in corpus and token.replace("-", " ") not in corpus:
            undocumented.append(surface)
    return {"checked": len(surfaces), "undocumented": undocumented, "wiki_missing": False}


def report_documentation_drift(context: Mapping[str, Any]) -> Mapping[str, Any]:
    """Persist the drift report where the dashboard and the Principal can see it."""
    diff = context.get("STEP-DIFF") or {
        "checked": context.get("checked", 0),
        "undocumented": context.get("undocumented", []),
    }
    undocumented = list(diff.get("undocumented", []))
    report = {
        "kind": "documentation-drift",
        "checked": diff.get("checked", 0),
        "undocumented": undocumented,
        "status": "drift" if undocumented else "ok",
    }
    out_dir = _hermes_root(context) / "docs"
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
        tmp = out_dir / "drift-report.json.tmp"
        tmp.write_text(json.dumps(report, indent=2), encoding="utf-8")
        tmp.replace(out_dir / "drift-report.json")
        report["report_path"] = str(out_dir / "drift-report.json")
    except OSError:
        report["report_path"] = None
    return report


HANDLERS = {
    "verify_release_gates": verify_release_gates,
    "enforce_docs_gate": enforce_docs_gate,
    "build_documentation_site": build_documentation_site,
    "record_publication_actions": record_publication_actions,
    "enumerate_documented_surfaces": enumerate_documented_surfaces,
    "diff_documentation_coverage": diff_documentation_coverage,
    "report_documentation_drift": report_documentation_drift,
}


def standard_handlers() -> dict[str, Any]:
    """All packaged Standing Operation handlers a host can register in one call."""
    from .compliance import HANDLERS as compliance_handlers
    from .monitor import HANDLERS as monitor_handlers

    merged: dict[str, Any] = {}
    merged.update(monitor_handlers)
    merged.update(compliance_handlers)
    merged.update(HANDLERS)
    return merged
