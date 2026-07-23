"""Ships with the OS: proves the evolution engine works and the LPOS fixture
loader reads the operating system's own benchmarks.
"""
from __future__ import annotations

import os
import unittest
from pathlib import Path

from lpos_engine.evolution import Skill, load_tasks, split_tasks, evolve, gate_candidate
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
        # In the shipped package this points at lpos_engine/evals. The test is
        # skipped only when run outside a tree that carries the fixtures.
        evals = os.environ.get("LPOS_EVALS_DIR")
        if not evals or not Path(evals).exists():
            self.skipTest("LPOS_EVALS_DIR not set to a fixtures directory")
        tasks = load_lpos_tasks(evals)
        self.assertEqual(len(tasks), 55)
        self.assertEqual({t["component_type"] for t in tasks},
                         {"specialist", "standing_operation"})
        self.assertTrue(all(t["evaluation"] for t in tasks))


if __name__ == "__main__":
    unittest.main()
