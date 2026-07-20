"""Ships with the OS: proves the evolution engine works and the LPOS fixture loader reads benchmarks."""
from __future__ import annotations

import os
import unittest
from pathlib import Path

from lpos_engine.evolution import Skill, evolve, gate_candidate, load_tasks, split_tasks
from lpos_engine.evolution.lpos_tasks import load_lpos_tasks

DATA = Path(__file__).resolve().parents[1] / "src" / "lpos_engine" / "evolution" / "data" / "cs001_tasks.json"


class EvolutionShipTests(unittest.TestCase):
    def test_cs001_example_domain_accepts_helpful_rejects_harmful(self):
        split = split_tasks(load_tasks(DATA))
        base = Skill("cs001-style").with_rules(["em_dash", "exclamation"])
        improved, report = evolve(base, split, edit_budget=4, min_support=2)
        self.assertTrue(report.accepted)
        self.assertGreater(report.candidate_test, report.baseline_test)
        harmful = improved.with_rules(list(improved.rules) + ["long_word_overbroad"])
        self.assertFalse(gate_candidate(improved, harmful, split).accepted)

    def test_lpos_fixtures_load_when_present(self):
        evals = os.environ.get("LPOS_EVALS_DIR")
        if not evals or not Path(evals).exists():
            self.skipTest("LPOS_EVALS_DIR not set to a fixtures directory")
        tasks = load_lpos_tasks(evals)
        self.assertEqual(len(tasks), 53)
        self.assertEqual({task["component_type"] for task in tasks}, {"specialist", "standing_operation"})
        self.assertTrue(all(task["evaluation"] for task in tasks))


if __name__ == "__main__":
    unittest.main()
