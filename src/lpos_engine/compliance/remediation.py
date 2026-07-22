"""Staging-only remediation. This module cannot write into the live system.

For every failing control it builds a :class:`Remediation` -- the problem, a
concrete proposed fix naming exact files, and a TEST ENVIRONMENT copy of the
affected files staged under ``<hermes>/compliance/staging/<run_id>/<control_id>/``
alongside a ``REMEDIATION.md`` and a ``validation.json``.

Adoption is NEVER performed here. Matching the distribution's
``external_action_default: record-only`` and the evolution pilot's staging rule
(``evolution/adopt.py``), the output is a record-only adoption plan whose
exact actions flow through the normal Principal approval mechanism before
anything touches the main system. Staging refuses (``ValidationError``) any
destination that resolves inside the repository checkout, outside the
compliance staging directory, or onto a path that looks live/production.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..errors import ValidationError
from . import audit as audit_module
from .controls import Control, run_control

_FORBIDDEN = ("live", "production")


@dataclass(frozen=True, slots=True)
class Remediation:
    control_id: str
    problem: str
    proposed_fix: str
    staged_paths: tuple[str, ...] = ()
    staged_dir: str = ""
    validation: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "control_id": self.control_id,
            "problem": self.problem,
            "proposed_fix": self.proposed_fix,
            "staged_paths": list(self.staged_paths),
            "staged_dir": self.staged_dir,
            "validation": dict(self.validation),
        }


def _guard_staging_dir(dest: Path, repo_root: Path, hermes_root: Path) -> Path:
    """Refuse any staging destination that could touch the live system."""

    staging_root = audit_module.staging_dir(hermes_root).resolve()
    resolved = dest.resolve()
    repo = Path(repo_root).expanduser().resolve()
    lowered = str(resolved).lower()
    if any(token in lowered for token in _FORBIDDEN):
        raise ValidationError(
            f"refusing to stage under a path that looks live/production: {resolved}"
        )
    if resolved == repo or repo in resolved.parents:
        raise ValidationError(
            f"refusing to stage inside the repository checkout: {resolved} is under {repo}"
        )
    if resolved != staging_root and staging_root not in resolved.parents:
        raise ValidationError(
            f"staging destination {resolved} is not under the compliance staging "
            f"directory {staging_root}"
        )
    return resolved


def stage_remediation(
    control: Control,
    evidence: str,
    *,
    repo_root: Path,
    hermes_root: Path,
    run_id: str,
) -> Remediation:
    """Stage a TEST ENVIRONMENT remediation for one failing control."""

    repo_root = Path(repo_root).expanduser()
    hermes_root = Path(hermes_root).expanduser()
    dest = audit_module.staging_dir(hermes_root) / run_id / control.control_id
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.mkdir(parents=True, exist_ok=True)
    resolved = _guard_staging_dir(dest, repo_root, hermes_root)

    proposed_fix = control.remediation_hint or (
        f"Investigate and correct the condition described by the evidence: {evidence}"
    )

    staged: list[str] = []
    missing_sources: list[str] = []
    for rel in control.remediation_paths:
        source = repo_root / rel
        if not source.is_file():
            missing_sources.append(rel)
            continue
        target = resolved / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        staged.append(str(target))

    # Cheap offline validation: where the staged copy mirrors the repo-relative
    # layout, re-run the control check against the staged copy directory. The
    # staged copy is a snapshot of the CURRENT (failing) state, so this records
    # the pre-fix baseline; the fix is proven when the same check flips to
    # passing against the edited staged copy. Anything else is honestly "not
    # validated".
    validation: dict[str, Any] = {
        "proving_test": (
            f"Apply the described change to the staged copy, then run the "
            f"{control.control_id} check with repo_root pointed at the staged copy "
            f"directory ({resolved}) and expect passing=True."
        ),
        "validated": False,
        "note": "not validated: staging holds a snapshot; the fix has not been applied yet",
    }
    if staged and not missing_sources:
        baseline = run_control(control, resolved, hermes_root)
        validation["staged_copy_baseline"] = {
            "passing": baseline.passing,
            "evidence": baseline.evidence,
        }
        copies_ok = all(
            (resolved / rel).read_bytes() == (repo_root / rel).read_bytes()
            for rel in control.remediation_paths
        )
        validation["staged_copy_integrity"] = (
            "byte-identical to source" if copies_ok else "copy mismatch"
        )
    elif missing_sources:
        validation["note"] = (
            "not validated: source file(s) missing, nothing to copy: "
            + ", ".join(missing_sources)
        )

    remediation = Remediation(
        control_id=control.control_id,
        problem=evidence,
        proposed_fix=proposed_fix,
        staged_paths=tuple(staged),
        staged_dir=str(dest),
        validation=validation,
    )

    (resolved / "REMEDIATION.md").write_text(
        "\n".join(
            [
                f"# Remediation for {control.control_id} — {control.title}",
                "",
                "**TEST ENVIRONMENT copy — this directory is staging, not the live system.**",
                "",
                f"- TSC criterion: {control.tsc_id}",
                f"- Category: {control.category}",
                f"- Run: {run_id}",
                "",
                "## Problem",
                "",
                evidence,
                "",
                "## Proposed fix",
                "",
                proposed_fix,
                "",
                "## Staged files",
                "",
                *(
                    [f"- `{path}`" for path in staged]
                    or ["- (no file-based fix; see proposed fix above)"]
                ),
                "",
                "## Adoption",
                "",
                "Adoption is record-only and approval-gated: the exact-action plan in the "
                "run output must be approved by the Principal before any staged file "
                "moves into the main system.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (resolved / "validation.json").write_text(
        json.dumps(validation, indent=2) + "\n", encoding="utf-8"
    )
    return remediation


def adoption_plan(
    remediations: list[Remediation], *, repo_root: Path, run_id: str
) -> dict[str, Any]:
    """Record-only adoption plan: exact actions for the approval flow."""

    actions = []
    for remediation in remediations:
        actions.append(
            {
                "action_id": f"ADOPT-{remediation.control_id}-{run_id}",
                "description": (
                    f"Apply the staged remediation for {remediation.control_id} to the "
                    f"main system after Principal approval: {remediation.proposed_fix}"
                ),
                "staged_path": remediation.staged_dir,
                "target_path": str(Path(repo_root).expanduser()),
            }
        )
    return {"mode": "record-only", "approval_required": True, "actions": actions}


def build_and_stage_remediations(
    failing: list[tuple[Control, str]],
    *,
    repo_root: Path,
    hermes_root: Path,
    run_id: str,
) -> dict[str, Any]:
    """Stage remediations for the failing controls; return the JSON-safe plan.

    Returns ``{"remediations": [], "adoption": "none"}`` when nothing fails.
    Every staged remediation is also recorded as a ``remediation_staged`` event
    in the compliance history so the audit log shows it.
    """

    if not failing:
        return {"remediations": [], "adoption": "none", "run_id": run_id}

    now_iso = audit_module.utc_now_iso()
    remediations = [
        stage_remediation(
            control, evidence, repo_root=repo_root, hermes_root=hermes_root, run_id=run_id
        )
        for control, evidence in failing
    ]
    audit_module.append_history(
        hermes_root,
        [
            {
                "ts": now_iso,
                "event": "remediation_staged",
                "control_id": remediation.control_id,
                "evidence": f"remediation staged (test environment): {remediation.staged_dir}",
            }
            for remediation in remediations
        ],
    )
    return {
        "remediations": [remediation.to_dict() for remediation in remediations],
        "adoption": adoption_plan(remediations, repo_root=repo_root, run_id=run_id),
        "run_id": run_id,
    }
