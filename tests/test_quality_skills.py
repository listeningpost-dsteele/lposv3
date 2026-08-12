from __future__ import annotations

import json
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "src" / "lpos_engine" / "spec" / "skills"


class QualitySkillContractTests(unittest.TestCase):
    def test_writing_and_design_quality_skills_are_packaged(self) -> None:
        anti = (SKILLS / "anti-slop-editor" / "SKILL.md").read_text(encoding="utf-8")
        design = (SKILLS / "design-anti-slop-reviewer" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("Zero em dashes", anti)
        self.assertIn("Deterministic blockers", design)
        self.assertIn("desktop and mobile", design)
        self.assertIn("fabricated customer proof", design)

    def test_cs002_requires_both_gates_without_ceremony_router(self) -> None:
        standards = (ROOT / "src" / "lpos_engine" / "spec" / "CRAFT-STANDARDS.md").read_text(encoding="utf-8")
        self.assertIn("zero deterministic blockers", standards)
        self.assertIn("placeholder or fabricated proof", standards)
        for removed in (
            "quality-router",
            "system-auditor",
            "test-evidence-auditor",
            "acceptance-spec-reviewer",
        ):
            self.assertFalse(
                (SKILLS / removed / "SKILL.md").exists(),
                f"{removed} was removed as ceremony in 4.8.1",
            )

    def test_release_metadata_points_to_versioned_quality_release(self) -> None:
        release = json.loads((ROOT / "RELEASE.json").read_text(encoding="utf-8"))
        self.assertEqual(release["version"], "4.8.2")
        self.assertEqual(release["archive"], "LPOS-v4.8.2-Complete.zip")
        self.assertEqual(release["wheel"], "lpos_os-4.8.2-py3-none-any.whl")

    def test_built_wheel_contains_design_skill_and_reference(self) -> None:
        release = json.loads((ROOT / "RELEASE.json").read_text(encoding="utf-8"))
        wheel = ROOT / "Packages" / release["wheel"]
        self.assertTrue(wheel.is_file(), "versioned release wheel is missing")
        with zipfile.ZipFile(wheel) as archive:
            names = set(archive.namelist())
        self.assertIn("lpos_engine/spec/skills/design-anti-slop-reviewer/SKILL.md", names)
        self.assertIn(
            "lpos_engine/spec/skills/design-anti-slop-reviewer/references/paid-agent-runtime-integration.md",
            names,
        )


if __name__ == "__main__":
    unittest.main()
