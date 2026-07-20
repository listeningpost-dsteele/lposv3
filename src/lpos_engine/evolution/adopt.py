"""Staging-only adoption. This module cannot write a live skill by construction."""
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
    if any(token in lowered for token in _FORBIDDEN):
        raise UnsafeAdoptionPath(f"refusing to stage under a path that looks live/production: {root}")
    dest = root / report["run_id"]
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "proposed-SKILL.md").write_text(skill.render(), encoding="utf-8")
    (dest / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return dest
