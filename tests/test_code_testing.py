"""Tests for the executable Code Testing Guild (GUILD-040)."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from lpos_engine import publication
from lpos_engine.code_testing import (
    build_evidence_packet,
    classify,
    evaluate_gauntlet,
    extra_gates_for,
    load_commands,
    load_manifest,
    manifest_commands,
    need_to_change_gate,
    required_gates,
)
from lpos_engine.errors import ValidationError
from lpos_engine.operations import StandingOperationRunner
from lpos_engine.store import SQLiteStore
from lpos_engine.workflows import load as load_workflow


class CriticalityTests(unittest.TestCase):
    def test_destructive_is_critical(self) -> None:
        self.assertEqual(classify({"destructive": True})["level"], "CRITICAL")

    def test_secrets_and_financial_and_prod_infra_are_critical(self) -> None:
        self.assertEqual(classify({"secrets": True})["level"], "CRITICAL")
        self.assertEqual(classify({"financial_movement": True})["level"], "CRITICAL")
        self.assertEqual(classify({"production_infra": True})["level"], "CRITICAL")

    def test_irreversible_migration_is_critical_but_reversible_is_high(self) -> None:
        self.assertEqual(classify({"migration": True, "reversible": False})["level"], "CRITICAL")
        self.assertEqual(classify({"migration": True, "reversible": True})["level"], "HIGH")

    def test_auth_is_high(self) -> None:
        self.assertEqual(classify({"touches_auth": True})["level"], "HIGH")
        self.assertEqual(classify({"touches_permissions": True})["level"], "HIGH")
        self.assertEqual(classify({"customer_data": True})["level"], "HIGH")
        self.assertEqual(classify({"public_api": True})["level"], "HIGH")
        self.assertEqual(classify({"blast_radius": "broad"})["level"], "HIGH")

    def test_normal_business_logic_is_standard(self) -> None:
        self.assertEqual(classify({"blast_radius": "medium"})["level"], "STANDARD")
        self.assertEqual(classify({})["level"], "STANDARD")

    def test_trivial_internal_change_is_light(self) -> None:
        self.assertEqual(classify({"blast_radius": "small", "reversible": True})["level"], "LIGHT")

    def test_classify_is_total_and_never_raises(self) -> None:
        # Unknown/garbage signals default to STANDARD without raising.
        self.assertEqual(classify(None)["level"], "STANDARD")
        self.assertEqual(classify({"blast_radius": "??", "unknown": object()})["level"], "STANDARD")

    def test_record_carries_required_gates_and_authority(self) -> None:
        record = classify({"touches_auth": True})
        self.assertEqual(record["required_gates"], required_gates("HIGH"))
        self.assertTrue(record["review_authority"])
        self.assertTrue(record["evidence_required"])
        self.assertTrue(record["escalation_conditions"])


class NeedToChangeGateTests(unittest.TestCase):
    def test_no_reproduction_yields_no_change_required(self) -> None:
        result = need_to_change_gate({})
        self.assertEqual(result["result"], "NO_CHANGE_REQUIRED")

    def test_reproduction_proceeds(self) -> None:
        self.assertEqual(need_to_change_gate({"reproduction": True})["result"], "PROCEED")
        self.assertEqual(
            need_to_change_gate({"demonstrated_missing_behavior": True})["result"], "PROCEED"
        )
        self.assertEqual(
            need_to_change_gate({"objective_constraint_proof": True})["result"], "PROCEED"
        )


class GauntletTests(unittest.TestCase):
    def _all_pass(self, level: str) -> dict:
        return {gate: {"ran": True, "passed": True} for gate in required_gates(level)}

    def test_all_required_gates_pass(self) -> None:
        self.assertEqual(evaluate_gauntlet("STANDARD", self._all_pass("STANDARD"))["decision"], "PASS")

    def test_required_gate_that_did_not_run_is_reject(self) -> None:
        gates = self._all_pass("STANDARD")
        first = required_gates("STANDARD")[0]
        gates[first] = {"ran": False, "passed": False}
        result = evaluate_gauntlet("STANDARD", gates)
        self.assertEqual(result["decision"], "REJECT")
        self.assertIn(first, result["missing_gates"])
        self.assertTrue(any("required command did not run" in r for r in result["reasons"]))

    def test_failed_gate_is_reject(self) -> None:
        gates = self._all_pass("STANDARD")
        target = required_gates("STANDARD")[3]
        gates[target] = {"ran": True, "passed": False}
        result = evaluate_gauntlet("STANDARD", gates)
        self.assertEqual(result["decision"], "REJECT")
        self.assertIn(target, result["failed_gates"])

    def test_flaky_gate_is_reject(self) -> None:
        gates = self._all_pass("STANDARD")
        target = required_gates("STANDARD")[3]
        gates[target] = {"ran": True, "passed": True, "flaky": True}
        self.assertEqual(evaluate_gauntlet("STANDARD", gates)["decision"], "REJECT")

    def test_green_unit_only_cannot_pass_standard(self) -> None:
        gates = {
            "focused_unit_tests": {"ran": True, "passed": True},
            "unit_test_stream": {"ran": True, "passed": True},
        }
        result = evaluate_gauntlet("STANDARD", gates)
        self.assertEqual(result["decision"], "REJECT")

    def test_light_all_pass(self) -> None:
        self.assertEqual(evaluate_gauntlet("LIGHT", self._all_pass("LIGHT"))["decision"], "PASS")

    def test_unknown_level_defaults_to_standard(self) -> None:
        self.assertEqual(evaluate_gauntlet("???", self._all_pass("STANDARD"))["decision"], "PASS")


class EvidencePacketTests(unittest.TestCase):
    def test_self_review_is_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            build_evidence_packet(
                change_id="CHG-1",
                criticality="HIGH",
                independent_reviewer="alice",
                implementer="alice",
            )

    def test_independent_reviewer_is_accepted(self) -> None:
        packet = build_evidence_packet(
            change_id="CHG-1",
            criticality="HIGH",
            independent_reviewer="bob",
            implementer="alice",
            commands_executed=["pytest -q"],
        )
        self.assertEqual(packet["independent_reviewer"], "bob")
        self.assertEqual(packet["implementer"], "alice")
        self.assertEqual(packet["commands_executed"], ["pytest -q"])


class ManifestLoaderTests(unittest.TestCase):
    def test_missing_manifest_yields_no_commands(self) -> None:
        self.assertEqual(load_commands(None), {})
        self.assertEqual(load_commands("/nonexistent/testing-manifest.yml"), {})

    def test_never_invents_commands_from_empty_manifest(self) -> None:
        # An inline manifest whose commands are all empty declares no runnable commands.
        text = "commands:\n  unit: \"\"\n  lint: \"\"\n  build: \"\"\n"
        self.assertEqual(manifest_commands(load_manifest(text)), {})

    def test_declared_commands_are_returned_only_from_manifest(self) -> None:
        text = "commands:\n  unit: \"pytest -q\"\n  lint: ruff check .\n  build: \"\"\n"
        commands = manifest_commands(load_manifest(text))
        self.assertEqual(commands, {"unit": "pytest -q", "lint": "ruff check ."})

    def test_json_manifest_is_accepted(self) -> None:
        text = json.dumps({"commands": {"unit": "pytest", "type_check": "mypy", "smoke": ""}})
        commands = manifest_commands(load_manifest(text))
        self.assertEqual(commands, {"unit": "pytest", "type_check": "mypy"})


class StandingOperationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = SQLiteStore(Path(self.temp.name) / "state.db")
        self.runner = StandingOperationRunner(self.store, publication.standard_handlers())

    def test_so_027_runs_end_to_end_and_passes(self) -> None:
        gate_results = {gate: {"ran": True, "passed": True} for gate in required_gates("STANDARD")}
        context = {
            "change_id": "CHG-27",
            "signals": {"blast_radius": "medium"},
            "need_to_change_evidence": {"reproduction": True},
            "gate_results": gate_results,
            "independent_reviewer": "auditor",
            "implementer": "engineer",
            "commands_executed": ["pytest -q"],
        }
        execution = self.runner.run(
            load_workflow("SO-027"), scheduled_for="2030-01-01T00:00:00Z", initial_context=context
        )
        self.assertEqual(execution.run.result.value, "ok")
        self.assertEqual(execution.outputs["STEP-EVALUATE"]["decision"], "PASS")
        self.assertTrue(execution.outputs["STEP-RECORD"]["recorded"])

    def test_so_027_rejects_when_a_required_gate_did_not_run(self) -> None:
        context = {
            "change_id": "CHG-27b",
            "signals": {"touches_auth": True},
            "need_to_change_evidence": {"reproduction": True},
            "gate_results": {},
        }
        execution = self.runner.run(
            load_workflow("SO-027"), scheduled_for="2030-02-01T00:00:00Z", initial_context=context
        )
        self.assertEqual(execution.run.result.value, "error")

    def test_so_028_reports_cleanly_when_no_results_supplied(self) -> None:
        execution = self.runner.run(
            load_workflow("SO-028"), scheduled_for="2030-01-01T00:00:00Z", initial_context={}
        )
        self.assertEqual(execution.run.result.value, "ok")
        review = execution.outputs["STEP-REVIEW"]
        self.assertEqual(review["status"], "no_results")
        self.assertEqual(review["message"], "no results supplied")

    def test_so_028_reports_findings_over_supplied_results(self) -> None:
        context = {"results": {"flaky": ["test_a"], "coverage_gaps": ["module_x"]}}
        execution = self.runner.run(
            load_workflow("SO-028"), scheduled_for="2030-01-02T00:00:00Z", initial_context=context
        )
        self.assertEqual(execution.outputs["STEP-REVIEW"]["finding_count"], 2)

    def test_so_029_verifies_extra_gates_present(self) -> None:
        gate_results = {gate: {"ran": True, "passed": True} for gate in extra_gates_for("HIGH")}
        context = {"level": "HIGH", "gate_results": gate_results}
        execution = self.runner.run(
            load_workflow("SO-029"), scheduled_for="2030-01-01T00:00:00Z", initial_context=context
        )
        self.assertEqual(execution.run.result.value, "ok")
        self.assertTrue(execution.outputs["STEP-VERIFY"]["hardened"])

    def test_so_029_blocks_when_extra_gates_missing(self) -> None:
        context = {"level": "CRITICAL", "gate_results": {}}
        execution = self.runner.run(
            load_workflow("SO-029"), scheduled_for="2030-03-01T00:00:00Z", initial_context=context
        )
        self.assertEqual(execution.run.result.value, "error")


if __name__ == "__main__":
    unittest.main()
