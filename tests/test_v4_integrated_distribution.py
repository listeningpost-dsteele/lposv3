from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import tomllib
import unittest
from importlib.resources import files as resource_files
from pathlib import Path

import lpos_engine
from lpos_engine.context import SpecRepository
from lpos_engine.evals import catalog as benchmark_catalog
from lpos_engine.evals import load_all as load_all_benchmarks
from lpos_engine.evals import run_core_evaluations
from lpos_engine.routing import CapabilityRegistry
from lpos_engine.workflows import catalog, load_all


class IntegratedV4DistributionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path(__file__).resolve().parents[1]
        cls.package_root = cls.root / "src" / "lpos_engine"

    def test_release_version_is_synchronized(self) -> None:
        project = tomllib.loads((self.root / "pyproject.toml").read_text(encoding="utf-8"))
        registry = json.loads(
            (self.package_root / "config" / "default_registry.json").read_text(encoding="utf-8")
        )
        operation_catalog = json.loads(
            (self.package_root / "workflows" / "catalog.json").read_text(encoding="utf-8")
        )
        release = json.loads((self.root / "RELEASE.json").read_text(encoding="utf-8"))
        kernel = (self.package_root / "spec" / "CHIP-KERNEL.md").read_text(encoding="utf-8")

        versions = {
            project["project"]["version"],
            lpos_engine.__version__,
            registry["os_version"],
            operation_catalog["os_version"],
            release["version"],
        }
        self.assertEqual(versions, {"4.2.0"})
        self.assertIn("# Chip Kernel v4.2.0", kernel)
        self.assertEqual(release["distribution_type"], "integrated")

    def test_packaged_specification_is_the_runtime_default(self) -> None:
        repository = SpecRepository.packaged()
        kernel_ref, kernel = repository.load_kernel()
        self.assertIsNotNone(kernel_ref)
        self.assertTrue(str(kernel_ref).endswith("CHIP-KERNEL.md"))
        self.assertIn("Deterministic enforcement", kernel)
        self.assertIn("Persistence and audit", kernel)

        packaged = resource_files("lpos_engine.spec")
        expected = {
            "CHIP-KERNEL.md",
            "LPOS-CORE.md",
            "CRAFT-STANDARDS.md",
            "CRAFT-STANDARD-ROUTING.yaml",
            "GUILDS.md",
            "SPECIALISTS.md",
            "SPECIALIST-INDEX.md",
            "STANDING-OPERATIONS.md",
            "BENCHMARKS.md",
            "LEDGERS.md",
            "SCHEMAS.md",
            "ONBOARDING.md",
        }
        available = {item.name for item in packaged.iterdir()}
        self.assertTrue(expected.issubset(available))

    def test_all_33_specialists_are_canonical_and_routable(self) -> None:
        registry = CapabilityRegistry.default()
        expected_ids = tuple(f"SPECIALIST-{index:03d}" for index in range(1, 34))
        actual_ids = tuple(profile.specialist_id for profile in registry.profiles)
        self.assertEqual(actual_ids, expected_ids)
        self.assertTrue(all(profile.capabilities for profile in registry.profiles))
        self.assertTrue(all(profile.craft_standards for profile in registry.profiles))

    def test_all_22_standing_operations_are_executable_definitions(self) -> None:
        entries = catalog()
        workflows = load_all()
        expected_ids = tuple(f"SO-{index:03d}" for index in range(1, 23))
        self.assertEqual(tuple(item["so_id"] for item in entries), expected_ids)
        self.assertEqual(tuple(item.so_id for item in workflows), expected_ids)
        for workflow in workflows:
            with self.subTest(so_id=workflow.so_id):
                self.assertTrue(workflow.steps)
                step_ids = {step.step_id for step in workflow.steps}
                self.assertEqual(len(step_ids), len(workflow.steps))
                for step in workflow.steps:
                    self.assertTrue(set(step.depends_on).issubset(step_ids))
                    self.assertNotIn(step.step_id, step.depends_on)


    def test_fixed_benchmark_corpus_covers_every_runtime_component(self) -> None:
        entries = benchmark_catalog()
        fixtures = load_all_benchmarks()
        expected_ids = (
            *(f"BENCH-S{index:03d}" for index in range(1, 34)),
            *(f"BENCH-O{index:03d}" for index in range(1, 23)),
        )
        self.assertEqual(tuple(item["id"] for item in entries), expected_ids)
        self.assertEqual(tuple(item["id"] for item in fixtures), expected_ids)
        self.assertEqual(
            {item["component_id"] for item in fixtures if item["component_type"] == "specialist"},
            {f"SPECIALIST-{index:03d}" for index in range(1, 34)},
        )
        self.assertEqual(
            {item["component_id"] for item in fixtures if item["component_type"] == "standing_operation"},
            {f"SO-{index:03d}" for index in range(1, 23)},
        )
        for fixture in fixtures:
            with self.subTest(benchmark=fixture["id"]):
                self.assertTrue(fixture["inputs"])
                self.assertTrue(fixture["expected"])
                self.assertTrue(fixture["evaluation"]["assertions"])
                self.assertTrue(fixture["evidence"])

    def test_all_deterministic_core_benchmarks_pass(self) -> None:
        result = run_core_evaluations()
        self.assertEqual(result["total"], 55)
        self.assertEqual(result["passed"], 55)
        self.assertEqual(result["failed"], 0)

    def test_all_benchmark_fixtures_match_the_executable_schema(self) -> None:
        from jsonschema.validators import validator_for

        schema = json.loads(
            (self.root / "schemas" / "benchmark-definition.schema.json").read_text(encoding="utf-8")
        )
        validator = validator_for(schema)
        validator.check_schema(schema)
        for fixture in load_all_benchmarks():
            with self.subTest(benchmark=fixture["id"]):
                validator(schema).validate(fixture)

    def test_human_visible_and_packaged_assets_are_identical(self) -> None:
        root_schemas = sorted((self.root / "schemas").glob("*.schema.json"))
        packaged_schemas = sorted((self.package_root / "schemas").glob("*.schema.json"))
        self.assertEqual([item.name for item in root_schemas], [item.name for item in packaged_schemas])
        for root_path, package_path in zip(root_schemas, packaged_schemas, strict=True):
            with self.subTest(schema=root_path.name):
                self.assertEqual(root_path.read_bytes(), package_path.read_bytes())
        self.assertEqual(
            (self.root / "config" / "default_registry.json").read_bytes(),
            (self.package_root / "config" / "default_registry.json").read_bytes(),
        )

    def test_user_facing_distribution_has_no_split_release_framing(self) -> None:
        # Construct retired labels in pieces so this test does not introduce them
        # into the release text it is checking.
        prohibited = (
            "reference" + " engine",
            "Build" + "/Hermes",
            "LPOS " + "v3",
            "v3." + "3",
            "patch" + "-only",
            "source " + "overlay",
        )
        targets = [self.root / "README.md", self.root / "RELEASE.json", *sorted((self.root / "docs").glob("*.md"))]
        targets.extend(sorted((self.package_root / "spec").rglob("*.md")))
        for target in targets:
            text = target.read_text(encoding="utf-8").casefold()
            for marker in prohibited:
                with self.subTest(file=str(target.relative_to(self.root)), marker=marker):
                    self.assertNotIn(marker.casefold(), text)

    def test_doctor_reports_one_healthy_v4_system(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            env = dict(__import__("os").environ)
            env["PYTHONPATH"] = str(self.root / "src")
            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "lpos_engine",
                    "doctor",
                    "--db",
                    str(Path(directory) / "lpos.db"),
                ],
                cwd=self.root,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        report = json.loads(completed.stdout)
        self.assertEqual(report["name"], "LPOS")
        self.assertEqual(report["version"], "4.2.0")
        self.assertEqual(report["status"], "healthy")
        self.assertEqual(report["specialists"], 33)
        self.assertEqual(report["standing_operations"], 22)
        self.assertEqual(report["benchmarks"], 55)
        self.assertEqual(report["database"]["integrity"], "ok")

    def test_package_has_no_runtime_dependency_on_a_separate_spec_tree(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            env = dict(__import__("os").environ)
            env["PYTHONPATH"] = str(self.root / "src")
            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "lpos_engine",
                    "demo",
                    "--workspace",
                    directory,
                ],
                cwd=Path(directory),
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        result = json.loads(completed.stdout)
        self.assertEqual(result["os_version"], "4.2.0")
        self.assertEqual(result["completion_report"]["status"], "completed")
        self.assertEqual(result["external_action_mode"], "record-only")


if __name__ == "__main__":
    unittest.main()
