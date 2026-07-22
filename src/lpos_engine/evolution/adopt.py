"""Staging-only adoption. This module cannot write a live skill by construction.

Every accepted proposal is written under a staging root as a rendered skill plus
a JSON report. Adoption into a real Hermes/LPOS skill is a separate, human-gated
step outside this pilot: this matches the review's rule that production skills
are never auto-adopted.
"""
from __future__ import annotations

import json
from pathlib import Path

from .skill import Skill

_FORBIDDEN = ("live", "production", ".hermes", "lpos-state")


class UnsafeAdoptionPath(Exception):
    pass


def stage_proposal(*, staging_root: str | Path, skill: Skill, report: dict) -> Path:
    root = Path(staging_root).resolve()
    lowered = str(root).lower()
    if any(tok in lowered for tok in _FORBIDDEN):
        raise UnsafeAdoptionPath(
            f"refusing to stage under a path that looks live/production: {root}"
        )
    dest = root / report["run_id"]
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "proposed-SKILL.md").write_text(skill.render())
    (dest / "report.json").write_text(json.dumps(report, indent=2))
    return dest
