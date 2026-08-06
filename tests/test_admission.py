"""Comprehensive provider-free tests for the LPOS 4.7 admission system.

Tests cover:
- Corpus quality (anti-template, concrete scenarios, dispositions)
- Strong baseline (frozen hash, not crippled)
- True A/B blind packets (both outputs, no leakage)
- Execution matrix (repetitions >= 3, case x rep x arm)
- Deterministic prepare (frozen timestamp, no utc_now)
- Scoring and pass policy enforcement
- Tamper detection (threshold weakening, cross-run mixing, duplicates)
- Synthetic end-to-end pass and fail flows
- Corpus integrity (103 suites, all required classes, hash binding)
"""

from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from lpos_engine.admission.generate import (
    FORBIDDEN_PHRASES,
    generate_all_suites,
    generate_suite,
    validate_against_templates,
)
from lpos_engine.admission.harness import (
    AssignmentMap,
    BASELINE_PROMPT_SHA256,
    BaselinePrompt,
    MINIMUM_REPETITIONS,
    PASS_POLICY,
    PASS_POLICY_SHA256,
    ScoringJudgment,
    blind_packets,
    build_execution_matrix,
    prepare_suite,
    score_judgments,
    verify_admission_record,
)
from lpos_engine.admission.models import (
    AdmissionCase,
    AdmissionSuite,
    REQUIRED_CASE_CLASSES,
    RUBRIC_DIMENSIONS,
    VALID_DISPOSITIONS,
)
from lpos_engine.admission.validate import validate_corpus
from lpos_engine.canonical import digest, text_digest
from lpos_engine.context import SpecRepository
from lpos_engine.errors import ValidationError
from lpos_engine.routing import CapabilityRegistry


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------

def _make_minimal_suite(
    suite_id: str = "ADM-TEST",
    specialist_id: str = "SPECIALIST-TEST",
    expected_disposition: str = "acceptance",
) -> AdmissionSuite:
    """Build a minimal valid suite for unit tests."""
    cases = []
    disp_map = {
        "representative_positive": "acceptance",
        "positive_routing": "acceptance",
        "negative_routing": "handoff",
        "adjacent_role_confusion": "handoff",
        "missing_input": "missing_input",
        "capability_gap": "capability_gap",
        "authority_boundary": "refusal",
        "weak_output_completion_honesty": "rejection",
    }
    for i, cls in enumerate(REQUIRED_CASE_CLASSES):
        cases.append(AdmissionCase(
            case_id=f"{suite_id}-C{i}",
            case_class=cls,
            task=f"Concrete test task number {i} for the {cls} scenario with enough detail to pass validation",
            expected_behavior=f"Expected behavior for {cls}",
            expected_disposition=disp_map.get(cls, expected_disposition),
            mandatory=cls != "representative_positive" and cls != "positive_routing",
            held_out=cls in ("adjacent_role_confusion", "capability_gap", "weak_output_completion_honesty"),
        ))
    return AdmissionSuite(
        suite_id=suite_id,
        specialist_id=specialist_id,
        specialist_name="Test Specialist",
        guild="GUILD-TEST",
        craft_standards=("CS-TEST-001",),
        capabilities=("test_capability",),
        model_class="executive",
        adjacent_specialists=("SPECIALIST-ADJ",),
        cases=tuple(cases),
        specialist_charter_sha256="a" * 64,
        guild_charter_sha256="b" * 64,
        craft_standard_sha256={"CS-TEST-001": "c" * 64},
    )


def _generate_synthetic_judgments(
    suite: AdmissionSuite,
    assignment_map: AssignmentMap,
    repetitions: int,
    candidate_score: float = 0.85,
    baseline_score: float = 0.35,
) -> list[ScoringJudgment]:
    """Generate complete synthetic judgments for all cases/reps/dims."""
    judgments = []
    jid = 0
    label_for_arm = {v: k for k, v in assignment_map.arm_map.items()}
    cand_label = label_for_arm["candidate"]
    base_label = label_for_arm["baseline"]
    for case in suite.cases:
        for rep in range(1, repetitions + 1):
            for dim in RUBRIC_DIMENSIONS:
                jid += 1
                judgments.append(ScoringJudgment(
                    judgment_id=f"J{jid}",
                    case_id=case.case_id,
                    repetition=rep,
                    arm_label=cand_label,
                    dimension=dim,
                    score=candidate_score,
                ))
                jid += 1
                judgments.append(ScoringJudgment(
                    judgment_id=f"J{jid}",
                    case_id=case.case_id,
                    repetition=rep,
                    arm_label=base_label,
                    dimension=dim,
                    score=baseline_score,
                ))
    return judgments


# ---------------------------------------------------------------------------
# A. Corpus quality tests
# ---------------------------------------------------------------------------

class CorpusQualityTests(unittest.TestCase):
    """Tests that the generated corpus has concrete, profession-specific tasks."""

    @classmethod
    def setUpClass(cls):
        cls.registry = CapabilityRegistry.default()
        cls.repo = SpecRepository.packaged()
        cls.suites = generate_all_suites()

    def test_generates_exactly_103_suites(self):
        self.assertEqual(len(self.suites), 103)

    def test_every_suite_has_eight_required_classes(self):
        for suite in self.suites:
            present = {c.case_class for c in suite.cases}
            missing = [cls for cls in REQUIRED_CASE_CLASSES if cls not in present]
            self.assertEqual(missing, [], f"{suite.suite_id} missing: {missing}")

    def test_every_case_has_non_null_expected_disposition(self):
        for suite in self.suites:
            for case in suite.cases:
                self.assertIsNotNone(
                    case.expected_disposition,
                    f"{case.case_id} has null expected_disposition",
                )
                self.assertIn(
                    case.expected_disposition,
                    VALID_DISPOSITIONS,
                    f"{case.case_id} has invalid disposition {case.expected_disposition}",
                )

    def test_no_forbidden_placeholder_phrases_in_any_task(self):
        for suite in self.suites:
            for case in suite.cases:
                task_lower = case.task.lower()
                for phrase in FORBIDDEN_PHRASES:
                    self.assertNotIn(
                        phrase,
                        task_lower,
                        f"{case.case_id} task contains forbidden phrase '{phrase}': {case.task[:80]}",
                    )

    def test_no_task_is_identity_only_or_meta_prompt(self):
        """Tasks must not merely repeat role identity or ask about charter prose."""
        for suite in self.suites:
            for case in suite.cases:
                # The task must not be just "Analyze the request '<identity>'"
                self.assertNotIn(
                    "analyze the request '",
                    case.task.lower(),
                    f"{case.case_id} is a meta-prompt about identity: {case.task[:80]}",
                )

    def test_tasks_are_substantive(self):
        """Every task must have enough profession-specific detail."""
        for suite in self.suites:
            for case in suite.cases:
                self.assertGreaterEqual(
                    len(case.task.strip()),
                    60,
                    f"{case.case_id} task too short: {case.task}",
                )

    def test_adjacent_role_cases_present_real_ambiguity(self):
        """Adjacent-role cases must name both specialists and a concrete boundary."""
        for suite in self.suites:
            adj_cases = [c for c in suite.cases if c.case_class == "adjacent_role_confusion"]
            for case in adj_cases:
                # Must mention "either" (the ambiguity) and a concrete trigger
                self.assertIn("either", case.task.lower())
                # Must not just repeat identity text
                self.assertNotIn("professional identity", case.task.lower())

    def test_corpus_passes_full_validation(self):
        """The generated corpus must pass validate_corpus."""
        result = validate_corpus(self.suites)
        self.assertTrue(
            result["valid"],
            f"Corpus validation failed: {result['errors'][:5]}",
        )

    def test_source_hashes_match_current_charters(self):
        """Every suite's charter hashes must match current charter content."""
        for suite in self.suites:
            _, charter = self.repo.load_component(suite.specialist_id)
            expected = text_digest(charter)
            self.assertEqual(
                suite.specialist_charter_sha256,
                expected,
                f"{suite.suite_id} charter hash mismatch",
            )


# ---------------------------------------------------------------------------
# B. Strong baseline tests
# ---------------------------------------------------------------------------

class StrongBaselineTests(unittest.TestCase):

    def test_baseline_prompt_is_frozen_by_hash(self):
        bp = BaselinePrompt.frozen()
        self.assertEqual(bp.prompt_sha256, BASELINE_PROMPT_SHA256)

    def test_baseline_is_not_crippled(self):
        """The baseline must NOT say 'do not declare capability gaps' or 'do not route'."""
        text = BaselinePrompt.frozen().text.lower()
        self.assertNotIn("do not declare capability gaps", text)
        self.assertNotIn("do not route", text)
        self.assertNotIn("do not route to specialists", text)

    def test_baseline_is_evidence_aware_and_honest(self):
        text = BaselinePrompt.frozen().text.lower()
        self.assertIn("missing", text)
        self.assertIn("evidence", text)
        self.assertIn("honest", text)
        self.assertIn("capability gap", text)
        self.assertIn("routing", text)

    def test_baseline_can_produce_structured_artifacts(self):
        text = BaselinePrompt.frozen().text.lower()
        self.assertIn("structured", text)
        self.assertIn("artifact", text)


# ---------------------------------------------------------------------------
# C. True A/B, repetitions, and hash binding tests
# ---------------------------------------------------------------------------

class BlindPacketTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.suite = _make_minimal_suite()
        cls.manifest = prepare_suite(cls.suite, frozen_timestamp="2026-01-01T00:00:00Z")
        cls.candidate_outputs = {}
        cls.baseline_outputs = {}
        for case in cls.suite.cases:
            for rep in range(1, 4):
                key = f"{case.case_id}:R{rep}"
                cls.candidate_outputs[key] = f"Candidate output for {key}"
                cls.baseline_outputs[key] = f"Baseline output for {key}"

    def test_packets_contain_both_a_and_b_outputs(self):
        """Each packet must present BOTH candidate and baseline as anonymous A/B."""
        seed = "test-seed"
        amap, packets = blind_packets(self.manifest, self.candidate_outputs, self.baseline_outputs, seed)
        self.assertEqual(len(packets), 8 * 3)  # 8 cases * 3 reps
        for pkt in packets:
            self.assertIn("A", pkt["outputs"])
            self.assertIn("B", pkt["outputs"])
            # Each output must have text and hash
            for label in ("A", "B"):
                self.assertIn("output_text", pkt["outputs"][label])
                self.assertIn("output_sha256", pkt["outputs"][label])

    def test_packets_do_not_leak_specialist_identity(self):
        seed = "test-seed"
        amap, packets = blind_packets(self.manifest, self.candidate_outputs, self.baseline_outputs, seed)
        for pkt in packets:
            pkt_str = json.dumps(pkt)
            # Must not contain specialist name or specialist id
            self.assertNotIn("Test Specialist", pkt_str)
            self.assertNotIn("SPECIALIST-TEST", pkt_str)
            # Must not contain the private seed
            self.assertNotIn(seed, pkt_str)
            # Must not contain provider/prompt metadata fields
            self.assertNotIn("provider", pkt_str.lower())
            self.assertNotIn("prompt_text", pkt_str.lower())
            self.assertNotIn("specialist_name", pkt_str.lower())
            # Must not contain arm identity labels as field names
            for key in pkt:
                self.assertNotIn("candidate", key.lower())
                self.assertNotIn("baseline", key.lower())
            for out_key in pkt.get("outputs", {}):
                self.assertIn(out_key, ("A", "B"))

    def test_assignment_map_records_true_arm_mapping(self):
        seed = "test-seed"
        amap, packets = blind_packets(self.manifest, self.candidate_outputs, self.baseline_outputs, seed)
        self.assertIn(amap.arm_map["A"], ("candidate", "baseline"))
        self.assertIn(amap.arm_map["B"], ("candidate", "baseline"))
        self.assertNotEqual(amap.arm_map["A"], amap.arm_map["B"])

    def test_blinding_is_deterministic_for_same_seed(self):
        seed = "test-seed"
        amap1, packets1 = blind_packets(self.manifest, self.candidate_outputs, self.baseline_outputs, seed)
        amap2, packets2 = blind_packets(self.manifest, self.candidate_outputs, self.baseline_outputs, seed)
        self.assertEqual(amap1.arm_map, amap2.arm_map)
        self.assertEqual(len(packets1), len(packets2))


class ExecutionMatrixTests(unittest.TestCase):

    def test_matrix_has_minimum_3_repetitions(self):
        matrix = build_execution_matrix(["C1", "C2"], repetitions=3)
        # 2 cases * 3 reps * 2 arms = 12
        self.assertEqual(len(matrix), 12)

    def test_matrix_rejects_below_minimum_repetitions(self):
        with self.assertRaises(ValidationError):
            build_execution_matrix(["C1"], repetitions=2)

    def test_every_run_unit_has_canonical_id_and_hash(self):
        matrix = build_execution_matrix(["C1"], repetitions=3)
        for unit in matrix:
            self.assertIn("run_unit_id", unit)
            self.assertIn("run_unit_sha256", unit)
            self.assertTrue(unit["run_unit_id"].startswith("RUN-"))

    def test_matrix_covers_all_case_rep_arm_combinations(self):
        matrix = build_execution_matrix(["C1", "C2"], repetitions=3)
        combos = {(u["case_id"], u["repetition"], u["arm"]) for u in matrix}
        expected = set()
        for case in ("C1", "C2"):
            for rep in range(1, 4):
                for arm in ("candidate", "baseline"):
                    expected.add((case, rep, arm))
        self.assertEqual(combos, expected)


class DeterministicPrepareTests(unittest.TestCase):

    def test_prepare_does_not_use_wall_clock_time(self):
        """The manifest must use the caller-supplied frozen timestamp, not utc_now."""
        suite = _make_minimal_suite()
        manifest1 = prepare_suite(suite, frozen_timestamp="2026-01-01T00:00:00Z")
        manifest2 = prepare_suite(suite, frozen_timestamp="2026-01-01T00:00:00Z")
        self.assertEqual(manifest1["manifest_sha256"], manifest2["manifest_sha256"])
        self.assertEqual(manifest1["prepared_at"], "2026-01-01T00:00:00Z")

    def test_prepare_is_deterministic(self):
        suite = _make_minimal_suite()
        m1 = prepare_suite(suite, frozen_timestamp="2026-01-01T00:00:00Z")
        m2 = prepare_suite(suite, frozen_timestamp="2026-01-01T00:00:00Z")
        self.assertEqual(m1["manifest_sha256"], m2["manifest_sha256"])

    def test_prepare_binds_baseline_prompt_hash(self):
        suite = _make_minimal_suite()
        manifest = prepare_suite(suite, frozen_timestamp="2026-01-01T00:00:00Z")
        self.assertEqual(
            manifest["baseline_prompt"]["prompt_sha256"],
            BASELINE_PROMPT_SHA256,
        )

    def test_prepare_binds_pass_policy_hash(self):
        suite = _make_minimal_suite()
        manifest = prepare_suite(suite, frozen_timestamp="2026-01-01T00:00:00Z")
        self.assertEqual(manifest["pass_policy_sha256"], PASS_POLICY_SHA256)

    def test_prepare_includes_execution_matrix(self):
        suite = _make_minimal_suite()
        manifest = prepare_suite(suite, frozen_timestamp="2026-01-01T00:00:00Z")
        self.assertIn("execution_matrix", manifest)
        self.assertEqual(manifest["run_unit_count"], 8 * 3 * 2)


# ---------------------------------------------------------------------------
# D. Scoring and verification tests
# ---------------------------------------------------------------------------

class ScoringTests(unittest.TestCase):

    def setUp(self):
        self.suite = _make_minimal_suite()
        self.manifest = prepare_suite(self.suite, frozen_timestamp="2026-01-01T00:00:00Z")
        self.candidate_outputs = {}
        self.baseline_outputs = {}
        for case in self.suite.cases:
            for rep in range(1, 4):
                key = f"{case.case_id}:R{rep}"
                self.candidate_outputs[key] = f"Candidate {key}"
                self.baseline_outputs[key] = f"Baseline {key}"
        self.amap, _ = blind_packets(
            self.manifest, self.candidate_outputs, self.baseline_outputs, "seed"
        )

    def test_candidate_win_produces_admit(self):
        judgments = _generate_synthetic_judgments(
            self.suite, self.amap, 3, candidate_score=0.95, baseline_score=0.30
        )
        record = score_judgments(judgments, self.amap, self.manifest)
        self.assertEqual(record["decision"], "admit")
        self.assertFalse(record["activated"])

    def test_candidate_loss_produces_do_not_admit(self):
        judgments = _generate_synthetic_judgments(
            self.suite, self.amap, 3, candidate_score=0.30, baseline_score=0.85
        )
        record = score_judgments(judgments, self.amap, self.manifest)
        self.assertEqual(record["decision"], "do_not_admit")

    def test_critical_failure_on_mandatory_case_vetoes(self):
        """Candidate scoring below 0.3 on a mandatory case vetoes admission."""
        judgments = _generate_synthetic_judgments(
            self.suite, self.amap, 3, candidate_score=0.95, baseline_score=0.30
        )
        # Sabotage one mandatory case: candidate scores 0.2
        label_for_arm = {v: k for k, v in self.amap.arm_map.items()}
        cand_label = label_for_arm["candidate"]
        for j in judgments:
            if j.case_id == self.suite.cases[2].case_id and j.arm_label == cand_label:
                object.__setattr__(j, "score", 0.2)
        record = score_judgments(judgments, self.amap, self.manifest)
        self.assertTrue(record["critical_failure_present"])
        self.assertEqual(record["decision"], "do_not_admit")

    def test_incomplete_outputs_fail(self):
        """Missing judgments for some case/rep/dim must flag incomplete."""
        judgments = _generate_synthetic_judgments(
            self.suite, self.amap, 3, candidate_score=0.95, baseline_score=0.30
        )
        # Remove some judgments to create incompleteness
        judgments = judgments[:-5]
        record = score_judgments(judgments, self.amap, self.manifest)
        self.assertFalse(record["outputs_complete"])
        self.assertGreater(len(record["completeness_failures"]), 0)

    def test_record_never_activates(self):
        judgments = _generate_synthetic_judgments(
            self.suite, self.amap, 3, candidate_score=0.95, baseline_score=0.30
        )
        record = score_judgments(judgments, self.amap, self.manifest)
        self.assertFalse(record["activated"])


class VerifyTests(unittest.TestCase):

    def setUp(self):
        self.suite = _make_minimal_suite()
        self.manifest = prepare_suite(self.suite, frozen_timestamp="2026-01-01T00:00:00Z")
        self.candidate_outputs = {}
        self.baseline_outputs = {}
        for case in self.suite.cases:
            for rep in range(1, 4):
                key = f"{case.case_id}:R{rep}"
                self.candidate_outputs[key] = f"Candidate {key}"
                self.baseline_outputs[key] = f"Baseline {key}"
        self.amap, _ = blind_packets(
            self.manifest, self.candidate_outputs, self.baseline_outputs, "seed"
        )
        self.judgments = _generate_synthetic_judgments(
            self.suite, self.amap, 3, candidate_score=0.95, baseline_score=0.30
        )
        freeze_hash = digest([j.to_dict() for j in self.judgments])
        self.record = score_judgments(self.judgments, self.amap, self.manifest)
        self.record["judgment_freeze_sha256"] = freeze_hash

    def test_valid_record_passes_verification(self):
        result = verify_admission_record(self.record, self.manifest, self.judgments, self.amap)
        self.assertTrue(result["verified"])
        self.assertEqual(result["failures"], [])

    def test_activated_record_fails_verification(self):
        tampered = dict(self.record)
        tampered["activated"] = True
        result = verify_admission_record(tampered, self.manifest, self.judgments, self.amap)
        self.assertFalse(result["verified"])

    def test_threshold_weakening_fails_verification(self):
        """Modifying the pass policy to weaken thresholds must fail."""
        tampered = json.loads(json.dumps(self.record))
        tampered["pass_policy"]["minimum_overall_delta"] = 0.01
        tampered["pass_policy_sha256"] = digest(tampered["pass_policy"])
        result = verify_admission_record(tampered, self.manifest, self.judgments, self.amap)
        self.assertFalse(result["verified"])
        self.assertTrue(any("policy" in f.lower() for f in result["failures"]))

    def test_policy_hash_mismatch_fails_verification(self):
        tampered = json.loads(json.dumps(self.record))
        tampered["pass_policy_sha256"] = "0" * 64
        result = verify_admission_record(tampered, self.manifest, self.judgments, self.amap)
        self.assertFalse(result["verified"])

    def test_judgment_tampering_fails_verification(self):
        """Modifying judgments after freezing must be detected."""
        tampered_judgments = list(self.judgments)
        object.__setattr__(tampered_judgments[0], "score", 0.01)
        result = verify_admission_record(self.record, self.manifest, tampered_judgments, self.amap)
        self.assertFalse(result["verified"])
        self.assertTrue(any("tampered" in f.lower() or "freeze" in f.lower() for f in result["failures"]))

    def test_cross_run_mixing_detected(self):
        """Judgments referencing case_ids not in the manifest must fail."""
        foreign_judgment = ScoringJudgment(
            judgment_id="FOREIGN",
            case_id="ADM-FOREIGN-C0",
            repetition=1,
            arm_label="A",
            dimension="method_fidelity",
            score=0.5,
        )
        all_judgments = list(self.judgments) + [foreign_judgment]
        result = verify_admission_record(self.record, self.manifest, all_judgments, self.amap)
        self.assertFalse(result["verified"])
        self.assertTrue(any("cross-run" in f.lower() for f in result["failures"]))

    def test_duplicate_run_units_detected(self):
        """Duplicate judgments for the same case/rep/arm/dim must fail."""
        dup = ScoringJudgment(
            judgment_id="DUP",
            case_id=self.judgments[0].case_id,
            repetition=self.judgments[0].repetition,
            arm_label=self.judgments[0].arm_label,
            dimension=self.judgments[0].dimension,
            score=0.5,
        )
        all_judgments = list(self.judgments) + [dup]
        result = verify_admission_record(self.record, self.manifest, all_judgments, self.amap)
        self.assertFalse(result["verified"])
        self.assertTrue(any("duplicate" in f.lower() for f in result["failures"]))


# ---------------------------------------------------------------------------
# E. Synthetic end-to-end pass/fail flow
# ---------------------------------------------------------------------------

class SyntheticEndToEndTests(unittest.TestCase):

    def test_e2e_pass_flow(self):
        """A complete prepare -> blind -> score -> verify flow that should ADMIT."""
        suite = _make_minimal_suite("ADM-E2E-PASS")
        manifest = prepare_suite(suite, frozen_timestamp="2026-01-01T00:00:00Z")

        candidate_outputs = {}
        baseline_outputs = {}
        for case in suite.cases:
            for rep in range(1, 4):
                key = f"{case.case_id}:R{rep}"
                candidate_outputs[key] = f"High-quality candidate work for {key}"
                baseline_outputs[key] = f"Basic baseline work for {key}"

        amap, packets = blind_packets(manifest, candidate_outputs, baseline_outputs, "e2e-seed")
        self.assertEqual(len(packets), 8 * 3)

        judgments = _generate_synthetic_judgments(
            suite, amap, 3, candidate_score=0.95, baseline_score=0.25
        )
        freeze_hash = digest([j.to_dict() for j in judgments])
        record = score_judgments(judgments, amap, manifest)
        record["judgment_freeze_sha256"] = freeze_hash

        self.assertEqual(record["decision"], "admit")
        self.assertFalse(record["activated"])
        self.assertTrue(record["outputs_complete"])

        result = verify_admission_record(record, manifest, judgments, amap)
        self.assertTrue(result["verified"])

    def test_e2e_fail_flow(self):
        """A complete flow where the candidate loses should NOT admit."""
        suite = _make_minimal_suite("ADM-E2E-FAIL")
        manifest = prepare_suite(suite, frozen_timestamp="2026-01-01T00:00:00Z")

        candidate_outputs = {}
        baseline_outputs = {}
        for case in suite.cases:
            for rep in range(1, 4):
                key = f"{case.case_id}:R{rep}"
                candidate_outputs[key] = f"Poor candidate work for {key}"
                baseline_outputs[key] = f"Good baseline work for {key}"

        amap, packets = blind_packets(manifest, candidate_outputs, baseline_outputs, "e2e-seed")

        judgments = _generate_synthetic_judgments(
            suite, amap, 3, candidate_score=0.30, baseline_score=0.85
        )
        freeze_hash = digest([j.to_dict() for j in judgments])
        record = score_judgments(judgments, amap, manifest)
        record["judgment_freeze_sha256"] = freeze_hash

        self.assertEqual(record["decision"], "do_not_admit")

        result = verify_admission_record(record, manifest, judgments, amap)
        self.assertTrue(result["verified"])


# ---------------------------------------------------------------------------
# F. Model validation tests
# ---------------------------------------------------------------------------

class ModelValidationTests(unittest.TestCase):

    def test_case_rejects_null_expected_disposition(self):
        with self.assertRaises(ValidationError):
            AdmissionCase(
                case_id="TEST-C0",
                case_class="representative_positive",
                task="A concrete test task with enough detail to be valid for testing",
                expected_behavior="Expected",
                expected_disposition=None,
            )

    def test_case_rejects_invalid_disposition(self):
        with self.assertRaises(ValidationError):
            AdmissionCase(
                case_id="TEST-C0",
                case_class="representative_positive",
                task="A concrete test task with enough detail to be valid for testing",
                expected_behavior="Expected",
                expected_disposition="bogus_disposition",
            )

    def test_case_accepts_valid_disposition(self):
        for disp in VALID_DISPOSITIONS:
            case = AdmissionCase(
                case_id=f"TEST-{disp[:4]}",
                case_class="representative_positive",
                task="A concrete test task with enough detail to be valid for testing",
                expected_behavior="Expected",
                expected_disposition=disp,
            )
            self.assertEqual(case.expected_disposition, disp)

    def test_suite_rejects_missing_required_case_class(self):
        """A suite missing one of the 8 required classes must fail."""
        cases = []
        for cls in REQUIRED_CASE_CLASSES[:-1]:  # skip last
            cases.append(AdmissionCase(
                case_id=f"ADM-S-C{len(cases)}",
                case_class=cls,
                task=f"Task for {cls} number {len(cases)} with enough detail",
                expected_behavior="Expected",
                expected_disposition="acceptance",
            ))
        with self.assertRaises(ValidationError):
            AdmissionSuite(
                suite_id="ADM-S",
                specialist_id="SPECIALIST-S",
                specialist_name="S",
                guild="GUILD-S",
                craft_standards=("CS-1",),
                capabilities=("cap",),
                model_class="executive",
                adjacent_specialists=("SPECIALIST-A",),
                cases=tuple(cases),
                specialist_charter_sha256="a" * 64,
                guild_charter_sha256="b" * 64,
                craft_standard_sha256={"CS-1": "c" * 64},
            )


# ---------------------------------------------------------------------------
# G. Anti-template validator tests
# ---------------------------------------------------------------------------

class AntiTemplateValidatorTests(unittest.TestCase):

    def test_rejects_placeholder_phrase(self):
        case = AdmissionCase(
            case_id="TEST-AT-0",
            case_class="representative_positive",
            task="Apply the required method and deliver the required artifact for this Specialist",
            expected_behavior="Expected",
            expected_disposition="acceptance",
        )
        violations = validate_against_templates([case])
        self.assertTrue(len(violations) >= 3)  # 3 forbidden phrases

    def test_rejects_short_task(self):
        case = AdmissionCase(
            case_id="TEST-AT-1",
            case_class="representative_positive",
            task="Do the task.",
            expected_behavior="Expected",
            expected_disposition="acceptance",
        )
        violations = validate_against_templates([case])
        self.assertTrue(any("too short" in v for v in violations))

    def test_rejects_meta_prompt(self):
        case = AdmissionCase(
            case_id="TEST-AT-2",
            case_class="adjacent_role_confusion",
            task="Analyze the request 'You are a senior analyst' and determine which specialist owns it based on identity",
            expected_behavior="Expected",
            expected_disposition="handoff",
        )
        violations = validate_against_templates([case])
        self.assertTrue(any("meta-prompt" in v for v in violations))

    def test_accepts_concrete_task(self):
        case = AdmissionCase(
            case_id="TEST-AT-3",
            case_class="representative_positive",
            task="A decision owner asks the specialist to evaluate three competing vendor proposals for a cloud migration, comparing cost, risk, and timeline.",
            expected_behavior="Expected",
            expected_disposition="acceptance",
        )
        violations = validate_against_templates([case])
        self.assertEqual(violations, [])


# --------------------------------------------------------------------------- #
# H. Evidence class and attestation controls
# --------------------------------------------------------------------------- #

class EvidenceControlTests(unittest.TestCase):

    def test_unknown_evidence_class_rejected(self):
        """Caller cannot invent an evidence class outside the frozen set."""
        from lpos_engine.admission.harness import EvidenceRecord
        with self.assertRaises(ValidationError):
            EvidenceRecord(
                evidence_class="caller_self_attested",
                evidence_sha256="a" * 64,
            )

    def test_provider_attested_requires_attestation_reference(self):
        """Provider-attested evidence must carry a non-empty attestation reference."""
        from lpos_engine.admission.harness import EvidenceRecord
        # Missing reference -> fail
        with self.assertRaises(ValidationError):
            EvidenceRecord(
                evidence_class="provider_attested_execution",
                evidence_sha256="a" * 64,
            )
        # Empty/whitespace reference -> fail
        with self.assertRaises(ValidationError):
            EvidenceRecord(
                evidence_class="provider_attested_execution",
                evidence_sha256="a" * 64,
                attestation_reference="   ",
            )

    def test_valid_attestation_reference_accepted(self):
        from lpos_engine.admission.harness import EvidenceRecord
        ev = EvidenceRecord(
            evidence_class="provider_attested_execution",
            evidence_sha256="a" * 64,
            attestation_reference="attestation-abc123",
        )
        self.assertEqual(ev.attestation_reference, "attestation-abc123")

    def test_simulated_component_test_accepted_without_attestation(self):
        from lpos_engine.admission.harness import EvidenceRecord
        ev = EvidenceRecord(
            evidence_class="simulated_component_test",
            evidence_sha256="b" * 64,
        )
        self.assertIsNone(ev.attestation_reference)

    def test_evidence_class_not_upgradable_by_details_field(self):
        """The details field cannot smuggle a different evidence class."""
        from lpos_engine.admission.harness import EvidenceRecord
        ev = EvidenceRecord(
            evidence_class="simulated_component_test",
            evidence_sha256="c" * 64,
            details="this is really provider_attested_execution",
        )
        # The actual class remains what was declared, not what details says.
        self.assertEqual(ev.evidence_class, "simulated_component_test")


# --------------------------------------------------------------------------- #
# I. Duplicate suite and mandatory-case enforcement
# --------------------------------------------------------------------------- #

class DuplicateAndMandatoryTests(unittest.TestCase):

    def test_corpus_has_no_duplicate_specialist_suites(self):
        """No two suites may target the same specialist_id."""
        from lpos_engine.admission.validate import load_corpus_from_data
        suites = load_corpus_from_data()
        ids = [s.specialist_id for s in suites]
        self.assertEqual(len(ids), len(set(ids)),
                         "duplicate specialist_id found in corpus")

    def test_corpus_has_no_duplicate_suite_ids(self):
        from lpos_engine.admission.validate import load_corpus_from_data
        suites = load_corpus_from_data()
        ids = [s.suite_id for s in suites]
        self.assertEqual(len(ids), len(set(ids)))

    def test_every_mandatory_case_is_marked_mandatory(self):
        """Cases in mandatory classes must have mandatory=True."""
        from lpos_engine.admission.models import MANDATORY_CASE_CLASSES
        from lpos_engine.admission.validate import load_corpus_from_data
        suites = load_corpus_from_data()
        for suite in suites:
            for case in suite.cases:
                if case.case_class in MANDATORY_CASE_CLASSES:
                    self.assertTrue(
                        case.mandatory,
                        f"{suite.suite_id} {case.case_id} "
                        f"({case.case_class}) must be mandatory",
                    )

    def test_every_held_out_case_is_marked_held_out(self):
        from lpos_engine.admission.models import HELD_OUT_CASE_CLASSES
        from lpos_engine.admission.validate import load_corpus_from_data
        suites = load_corpus_from_data()
        for suite in suites:
            for case in suite.cases:
                if case.case_class in HELD_OUT_CASE_CLASSES:
                    self.assertTrue(
                        case.held_out,
                        f"{suite.suite_id} {case.case_id} "
                        f"({case.case_class}) must be held_out",
                    )


# --------------------------------------------------------------------------- #
# J. Replay and tampered-output rejection
# --------------------------------------------------------------------------- #

class ReplayAndTamperTests(unittest.TestCase):

    def setUp(self):
        self.suite = _make_minimal_suite("ADM-REPLAY")
        self.manifest = prepare_suite(self.suite, frozen_timestamp="2026-01-01T00:00:00Z")
        self.candidate_outputs = {}
        self.baseline_outputs = {}
        for case in self.suite.cases:
            for rep in range(1, 4):
                key = f"{case.case_id}:R{rep}"
                self.candidate_outputs[key] = f"Candidate {key}"
                self.baseline_outputs[key] = f"Baseline {key}"
        self.amap, self.packets = blind_packets(
            self.manifest, self.candidate_outputs, self.baseline_outputs, "replay-seed"
        )

    def test_incomplete_outputs_flagged_in_record(self):
        """A record with missing judgments must have outputs_complete=False."""
        judgments = _generate_synthetic_judgments(
            self.suite, self.amap, 3, candidate_score=0.95, baseline_score=0.30
        )
        # Drop a chunk of judgments
        record = score_judgments(judgments[:-10], self.amap, self.manifest)
        self.assertFalse(record["outputs_complete"])
        self.assertGreater(len(record["completeness_failures"]), 0)
        self.assertEqual(record["decision"], "do_not_admit")

    def test_replayed_judgments_detected_as_duplicates(self):
        """Replaying the same judgment twice must be caught by verify."""
        judgments = _generate_synthetic_judgments(
            self.suite, self.amap, 3, candidate_score=0.95, baseline_score=0.30
        )
        freeze_hash = digest([j.to_dict() for j in judgments])
        record = score_judgments(judgments, self.amap, self.manifest)
        record["judgment_freeze_sha256"] = freeze_hash

        # Replay: duplicate the first judgment
        replayed = list(judgments) + [judgments[0]]
        result = verify_admission_record(record, self.manifest, replayed, self.amap)
        self.assertFalse(result["verified"])
        self.assertTrue(any("duplicate" in f.lower() for f in result["failures"]))


# --------------------------------------------------------------------------- #
# K. Adjacent-role confusion plausibility (cross-Guild spot checks)
# --------------------------------------------------------------------------- #

class AdjacentRolePlausibilityTests(unittest.TestCase):

    def test_adjacent_trigger_belongs_to_named_adjacent(self):
        """The confusion trigger must be drawn from the adjacent specialist's
        own invocation criteria, not blindly assigned from the subject's
        do-not-invoke list."""
        import re as _re
        from lpos_engine.admission.validate import load_corpus_from_data
        from lpos_engine.context import SpecRepository
        from lpos_engine.routing import CapabilityRegistry

        repo = SpecRepository.packaged()
        registry = CapabilityRegistry.default()
        invoke_map = {}
        for p in registry.profiles:
            _, charter = repo.load_component(p.specialist_id)
            # Extract invoke_when items (both heading variants)
            items = []
            for heading in ("Invoke this role when", "Invoke when"):
                section_match = _re.search(
                    rf"##\s+{_re.escape(heading)}\s*\n(.*?)(?=\n##\s+|\Z)",
                    charter, _re.DOTALL,
                )
                if section_match:
                    for line in section_match.group(1).split("\n"):
                        line = line.strip()
                        if line.startswith("- "):
                            items.append(line[2:].strip().rstrip(";").rstrip(".").strip())
                    break  # use the first matching heading
            invoke_map[p.specialist_id] = items

        suites = load_corpus_from_data()
        bad = []
        for suite in suites:
            adj_case = None
            for c in suite.cases:
                if c.case_class == "adjacent_role_confusion":
                    adj_case = c
                    break
            if not adj_case or not suite.adjacent_specialists:
                continue
            adj_id = suite.adjacent_specialists[0]
            adj_invoke = invoke_map.get(adj_id, [])

            # Extract trigger from the task
            m = _re.search(r':\s*"([^"]+)"', adj_case.task)
            trigger = m.group(1).lower().strip() if m else ""

            # Must overlap with at least one adjacent invoke_when item
            found = False
            for item in adj_invoke:
                item_lower = item.lower()
                t_words = set(trigger.split())
                i_words = set(item_lower.split())
                if t_words and i_words:
                    overlap = len(t_words & i_words) / max(len(t_words), len(i_words))
                    if overlap > 0.3 or trigger in item_lower:
                        found = True
                        break
            if not found:
                bad.append((suite.suite_id, adj_id, trigger[:60]))

        self.assertEqual(bad, [],
                         f"{len(bad)} suites have implausible adjacent triggers: "
                         f"{bad[:5]}")


if __name__ == "__main__":
    unittest.main()
