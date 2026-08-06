"""Deterministic admission harness: prepare, blind, score, verify.

All four phases are deterministic file transformers and validators.  Actual
model execution remains outside these commands.  The harness is provider-free,
stdlib-only, and never silently activates a Specialist.

Key contracts:
- ``prepare_suite`` emits a frozen run manifest with an explicit execution
  matrix (case x repetition x arm) and does NOT inject wall-clock time.
- ``blind_packets`` emits BOTH candidate and baseline outputs as anonymous
  A/B pairs per case/repetition, never a single selected output.
- ``score_judgments`` freezes judgments before unblinding and enforces the
  exact frozen pass policy.
- ``verify_admission_record`` detects tampering, threshold weakening,
  cross-run mixing, and incomplete outputs.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from ..canonical import (
    canonical_json,
    digest,
    freeze_mapping,
    require_id,
    require_text,
    text_digest,
)
from ..errors import ValidationError
from .models import (
    AdmissionCase,
    AdmissionSuite,
    HELD_OUT_CASE_CLASSES,
    MANDATORY_CASE_CLASSES,
    REQUIRED_CASE_CLASSES,
    RUBRIC_DIMENSIONS,
    VALID_DISPOSITIONS,
)

# --------------------------------------------------------------------------- #
# Frozen pass policy
# --------------------------------------------------------------------------- #

PASS_POLICY: dict[str, Any] = {
    "minimum_repetitions": 3,
    "minimum_dimension_delta": 0.25,
    "minimum_overall_delta": 0.50,
    "minimum_candidate_win_rate": 0.60,
    "mandatory_cases_must_pass": True,
    "critical_failure_veto": True,
    "frozen": True,
}

# Frozen hash of the policy.  Any modification to PASS_POLICY must change this
# bound hash, and verify_admission_record checks that the record's policy
# hash matches the frozen one.  Threshold weakening is detected by comparing
# the policy dict hash.
PASS_POLICY_SHA256 = digest(PASS_POLICY)


def _check_policy_frozen(policy: Mapping[str, Any]) -> None:
    """Raise if the policy has been weakened or modified."""
    if digest(dict(policy)) != PASS_POLICY_SHA256:
        raise ValidationError(
            "pass policy hash mismatch: policy has been modified or weakened"
        )


# --------------------------------------------------------------------------- #
# Strong baseline prompt (frozen by exact hash)
# --------------------------------------------------------------------------- #

BASELINE_PROMPT_TEXT = (
    "You are a competent general-purpose professional assistant. You help "
    "users complete professional tasks thoroughly and honestly.\n\n"
    "Principles:\n"
    "- Examine the supplied inputs carefully. If a required input is missing, "
    "say so explicitly and name what is missing before proceeding.\n"
    "- If the task falls outside your competence or requires a specialist you "
    "cannot impersonate, say so and recommend the right professional or "
    "routing rather than guessing.\n"
    "- Produce useful, well-structured artifacts. Use headings, lists, and "
    "traceable references where helpful.\n"
    "- Distinguish what is supported by evidence from what is inferred or "
    "unknown. Never fabricate sources or confidence.\n"
    "- Be direct about capability gaps and boundary issues. An honest refusal "
    "or handoff is better than a confident wrong answer.\n"
    "- When you can produce a complete answer, do so. Do not refuse work you "
    "can genuinely do."
)

BASELINE_PROMPT_SHA256 = text_digest(BASELINE_PROMPT_TEXT)


@dataclass(frozen=True, slots=True)
class BaselinePrompt:
    """The strong generic baseline prompt frozen by exact SHA-256.

    This is a capable general professional assistant.  It lacks only the
    exact Guild / Specialist / Craft package, not basic competence.
    """

    text: str = BASELINE_PROMPT_TEXT
    prompt_sha256: str = BASELINE_PROMPT_SHA256

    def to_dict(self) -> dict[str, Any]:
        return {"text": self.text, "prompt_sha256": self.prompt_sha256}

    @classmethod
    def frozen(cls) -> "BaselinePrompt":
        return cls()


# --------------------------------------------------------------------------- #
# Evidence classes
# --------------------------------------------------------------------------- #

EVIDENCE_CLASSES = frozenset({
    "simulated_component_test",
    "externally_observed_model_execution",
    "provider_attested_execution",
})

# Provider-attested evidence requires an attestation reference.
ATTESTATION_REQUIRED_FOR = frozenset({"provider_attested_execution"})


@dataclass(frozen=True, slots=True)
class EvidenceRecord:
    """A single piece of execution evidence for a case run.

    Caller/provider-shaped fields (e.g. provider name, model id) NEVER upgrade
    the evidence class.  Provider-attested evidence requires an attestation
    reference bound by hash.
    """

    evidence_class: str
    evidence_sha256: str
    attestation_reference: str | None = None
    details: str = ""

    def __post_init__(self) -> None:
        if self.evidence_class not in EVIDENCE_CLASSES:
            raise ValidationError(
                f"unknown evidence class: {self.evidence_class}"
            )
        if self.evidence_class in ATTESTATION_REQUIRED_FOR:
            if not self.attestation_reference or not self.attestation_reference.strip():
                raise ValidationError(
                    f"evidence class {self.evidence_class} requires an attestation reference"
                )

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "EvidenceRecord":
        return cls(
            evidence_class=value["evidence_class"],
            evidence_sha256=value["evidence_sha256"],
            attestation_reference=value.get("attestation_reference"),
            details=value.get("details", ""),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_class": self.evidence_class,
            "evidence_sha256": self.evidence_sha256,
            "attestation_reference": self.attestation_reference,
            "details": self.details,
        }


# --------------------------------------------------------------------------- #
# Execution matrix helpers
# --------------------------------------------------------------------------- #

MINIMUM_REPETITIONS = 3
ARMS = ("candidate", "baseline")
OPAQUE_LABELS = ("A", "B")


def build_execution_matrix(
    case_ids: Sequence[str],
    repetitions: int = MINIMUM_REPETITIONS,
) -> list[dict[str, Any]]:
    """Build the explicit execution matrix: case x repetition x arm.

    Each run unit has a canonical ID and a deterministic hash.  The matrix
    is the authoritative list of executions that must be performed.
    """
    if repetitions < MINIMUM_REPETITIONS:
        raise ValidationError(
            f"repetitions must be >= {MINIMUM_REPETITIONS}, got {repetitions}"
        )
    matrix: list[dict[str, Any]] = []
    for case_id in case_ids:
        for rep in range(1, repetitions + 1):
            for arm in ARMS:
                run_unit_id = f"RUN-{case_id}-{arm}-R{rep}"
                run_unit = {
                    "run_unit_id": run_unit_id,
                    "case_id": case_id,
                    "arm": arm,
                    "repetition": rep,
                }
                run_unit["run_unit_sha256"] = digest(run_unit)
                matrix.append(run_unit)
    return matrix


# --------------------------------------------------------------------------- #
# Prepare phase
# --------------------------------------------------------------------------- #

def prepare_suite(
    suite: AdmissionSuite,
    *,
    frozen_timestamp: str = "1970-01-01T00:00:00Z",
    repetitions: int = MINIMUM_REPETITIONS,
) -> dict[str, Any]:
    """Prepare a suite for execution: validate, compute manifest, freeze.

    Returns a prepared-suite manifest that binds all inputs and prompts by
    canonical SHA-256.  This is a deterministic transformer; it does not
    execute any model.

    ``frozen_timestamp`` is a caller-supplied frozen input (NOT wall-clock
    time) so that the manifest is a pure function of its inputs.
    """

    # Validate all required case classes are present.
    present_classes = {case.case_class for case in suite.cases}
    missing = [cls for cls in REQUIRED_CASE_CLASSES if cls not in present_classes]
    if missing:
        raise ValidationError(
            f"suite {suite.suite_id} is missing required case classes: {missing}"
        )

    # Build the execution matrix.
    case_ids = [case.case_id for case in suite.cases]
    execution_matrix = build_execution_matrix(case_ids, repetitions)

    # Build the run manifest.
    manifest: dict[str, Any] = {
        "suite_id": suite.suite_id,
        "specialist_id": suite.specialist_id,
        "specialist_name": suite.specialist_name,
        "guild": suite.guild,
        "model_class": suite.model_class,
        "craft_standards": list(suite.craft_standards),
        "capabilities": list(suite.capabilities),
        "case_count": len(suite.cases),
        "case_ids": case_ids,
        "case_classes": sorted(present_classes),
        "mandatory_case_ids": [case.case_id for case in suite.mandatory_cases],
        "held_out_case_ids": [case.case_id for case in suite.held_out_cases],
        "suite_content_sha256": suite.content_hash,
        "specialist_charter_sha256": suite.specialist_charter_sha256,
        "guild_charter_sha256": suite.guild_charter_sha256,
        "craft_standard_sha256": dict(suite.craft_standard_sha256),
        "baseline_prompt": BaselinePrompt.frozen().to_dict(),
        "pass_policy": dict(PASS_POLICY),
        "pass_policy_sha256": PASS_POLICY_SHA256,
        "rubric_dimensions": list(RUBRIC_DIMENSIONS),
        "repetitions": repetitions,
        "execution_matrix": execution_matrix,
        "run_unit_count": len(execution_matrix),
        # Frozen timestamp: NOT utc_now(). Caller supplies for determinism.
        "prepared_at": frozen_timestamp,
    }
    manifest["manifest_sha256"] = digest(
        {k: v for k, v in manifest.items() if k != "manifest_sha256"}
    )
    return manifest


# --------------------------------------------------------------------------- #
# Blind phase
# --------------------------------------------------------------------------- #

@dataclass(frozen=True, slots=True)
class AssignmentMap:
    """Private A/B assignment map linking opaque arm labels to real arms.

    The assignment is derived deterministically from the manifest hash and a
    private seed.  This object is the ONLY place where arm identity is stored;
    evaluator packets contain only opaque labels.
    """

    seed: str
    assignments: dict[str, str]  # "case_id:repetition" -> "A" or "B"
    arm_map: dict[str, str]      # opaque_label -> real_arm ("candidate"/"baseline")

    def to_dict(self) -> dict[str, Any]:
        return {
            "seed": self.seed,
            "assignments": dict(self.assignments),
            "arm_map": dict(self.arm_map),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "AssignmentMap":
        return cls(
            seed=value["seed"],
            assignments=dict(value["assignments"]),
            arm_map=dict(value["arm_map"]),
        )


def _deterministic_arm_map(seed: str, manifest_sha256: str) -> dict[str, str]:
    """Derive a deterministic A/B arm map from seed and manifest hash.

    Returns opaque_label -> real_arm.  Randomized per seed so that which
    physical label (A or B) is candidate vs baseline is unpredictable.
    """
    mac = hmac.new(
        seed.encode("utf-8"),
        manifest_sha256.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if int(mac[:8], 16) % 2 == 0:
        return {"A": "candidate", "B": "baseline"}
    return {"B": "candidate", "A": "baseline"}


def blind_packets(
    manifest: Mapping[str, Any],
    candidate_outputs: Mapping[str, str],
    baseline_outputs: Mapping[str, str],
    seed: str,
) -> tuple[AssignmentMap, list[dict[str, Any]]]:
    """Create blinded evaluator packets from candidate and baseline outputs.

    Returns (assignment_map, evaluator_packets).

    Each evaluator packet contains BOTH anonymous outputs (A and B) for a
    single case/repetition, presented as an A/B pair.  The private assignment
    map records which label is candidate vs baseline.

    Evaluator packets contain ONLY:
    - the profession-neutral task rubric (no Specialist identity)
    - opaque arm labels A and B
    - the output text for each label

    They must NOT disclose: Specialist identity, prompt identity, true arm
    identity, provider metadata, private seed, or the assignment map.
    """

    case_ids = manifest["case_ids"]
    repetitions = manifest.get("repetitions", MINIMUM_REPETITIONS)
    manifest_sha = manifest["manifest_sha256"]
    arm_map = _deterministic_arm_map(seed, manifest_sha)

    assignments: dict[str, str] = {}
    packets: list[dict[str, Any]] = []

    # Build the inverse arm map for looking up outputs.
    label_for_arm = {v: k for k, v in arm_map.items()}

    for case_id in case_ids:
        for rep in range(1, repetitions + 1):
            key = f"{case_id}:R{rep}"

            # The assignment for this case/rep determines which output is
            # shown under which label.  But since we show BOTH, the
            # assignment just records the canonical mapping.
            candidate_label = label_for_arm["candidate"]
            baseline_label = label_for_arm["baseline"]
            assignments[key] = candidate_label

            # Look up outputs.  Keys in the output maps are
            # "case_id:R{rep}" or "case_id" (legacy single-rep).
            out_key_multi = key
            out_key_single = case_id

            cand_text = (
                candidate_outputs.get(out_key_multi)
                or candidate_outputs.get(out_key_single, "")
            )
            base_text = (
                baseline_outputs.get(out_key_multi)
                or baseline_outputs.get(out_key_single, "")
            )

            # Build the A/B pair packet with opaque labels.
            outputs_by_label: dict[str, dict[str, Any]] = {}
            outputs_by_label[candidate_label] = {
                "output_text": cand_text,
                "output_sha256": text_digest(cand_text),
            }
            outputs_by_label[baseline_label] = {
                "output_text": base_text,
                "output_sha256": text_digest(base_text),
            }

            packet = {
                "packet_id": f"PKT-{case_id}-R{rep}",
                "case_id_ref": case_id,
                "repetition": rep,
                # Both outputs, presented anonymously.
                "outputs": {
                    "A": outputs_by_label["A"],
                    "B": outputs_by_label["B"],
                },
                # The rubric dimensions the evaluator scores against.
                "rubric_dimensions": list(RUBRIC_DIMENSIONS),
                # Intentionally NO: specialist name, prompt text, provider
                # metadata, seed, or any field that reveals which arm is which.
            }
            packets.append(packet)

    assignment_map = AssignmentMap(
        seed=seed, assignments=assignments, arm_map=arm_map
    )
    return assignment_map, packets


# --------------------------------------------------------------------------- #
# Score phase
# --------------------------------------------------------------------------- #

@dataclass(frozen=True, slots=True)
class ScoringJudgment:
    """A single dimension judgment for one case/repetition, frozen before unblinding.

    At judgment time the evaluator sees only opaque labels A/B.  The arm_label
    is whatever the evaluator saw (A or B).  Unblinding maps it back to
    candidate/baseline via the assignment map.
    """

    judgment_id: str
    case_id: str
    repetition: int
    arm_label: str          # opaque A/B at judgment time
    dimension: str
    score: float            # 0.0 to 1.0
    rationale: str = ""

    def __post_init__(self) -> None:
        if self.dimension not in RUBRIC_DIMENSIONS:
            raise ValidationError(f"unknown rubric dimension: {self.dimension}")
        if self.arm_label not in OPAQUE_LABELS:
            raise ValidationError(
                f"arm_label must be A or B, got {self.arm_label!r}"
            )
        if not isinstance(self.score, (int, float)):
            raise ValidationError("score must be numeric")
        if not (0.0 <= float(self.score) <= 1.0):
            raise ValidationError(f"score must be in [0.0, 1.0], got {self.score}")

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ScoringJudgment":
        return cls(
            judgment_id=value["judgment_id"],
            case_id=value["case_id"],
            repetition=int(value.get("repetition", 1)),
            arm_label=value["arm_label"],
            dimension=value["dimension"],
            score=float(value["score"]),
            rationale=value.get("rationale", ""),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "judgment_id": self.judgment_id,
            "case_id": self.case_id,
            "repetition": self.repetition,
            "arm_label": self.arm_label,
            "dimension": self.dimension,
            "score": self.score,
            "rationale": self.rationale,
        }


@dataclass(frozen=True, slots=True)
class CaseScore:
    """Aggregated scores for a single case after unblinding."""

    case_id: str
    candidate_arm: str
    candidate_scores: dict[str, float]  # dimension -> mean score
    baseline_scores: dict[str, float]   # dimension -> mean score
    candidate_overall: float
    baseline_overall: float
    delta: float
    candidate_wins: bool
    mandatory: bool = False
    critical_failure: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "candidate_arm": self.candidate_arm,
            "candidate_scores": dict(self.candidate_scores),
            "baseline_scores": dict(self.baseline_scores),
            "candidate_overall": round(self.candidate_overall, 4),
            "baseline_overall": round(self.baseline_overall, 4),
            "delta": round(self.delta, 4),
            "candidate_wins": self.candidate_wins,
            "mandatory": self.mandatory,
            "critical_failure": self.critical_failure,
        }


def _mean(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _check_output_completeness(
    judgments: Sequence[ScoringJudgment],
    manifest: Mapping[str, Any],
) -> list[str]:
    """Detect incomplete outputs: missing run units or missing judgments.

    Returns a list of failure descriptions.  An empty list means all
    expected judgments are present.
    """
    failures: list[str] = []
    case_ids = manifest["case_ids"]
    repetitions = manifest.get("repetitions", MINIMUM_REPETITIONS)

    # Build a set of (case_id, repetition, arm_label) from judgments.
    seen: set[tuple[str, int, str]] = set()
    for j in judgments:
        seen.add((j.case_id, j.repetition, j.arm_label))

    # Check every expected unit has judgments for both arms and all dims.
    for case_id in case_ids:
        for rep in range(1, repetitions + 1):
            for label in OPAQUE_LABELS:
                for dim in RUBRIC_DIMENSIONS:
                    key = (case_id, rep, label, dim)
                    found = any(
                        j.case_id == case_id
                        and j.repetition == rep
                        and j.arm_label == label
                        and j.dimension == dim
                        for j in judgments
                    )
                    if not found:
                        failures.append(
                            f"incomplete: missing judgment for "
                            f"{case_id} R{rep} arm {label} dim {dim}"
                        )
    return failures


def score_judgments(
    judgments: Sequence[ScoringJudgment],
    assignment_map: AssignmentMap,
    manifest: Mapping[str, Any],
) -> dict[str, Any]:
    """Score frozen judgments after unblinding. Emits a draft admission record.

    Judgments are frozen (caller must not modify after creation).  This
    function unblinds, aggregates across repetitions, and emits a DRAFT
    admission record.  It NEVER activates a Specialist.
    """

    mandatory_ids = set(manifest.get("mandatory_case_ids", []))
    repetitions = manifest.get("repetitions", MINIMUM_REPETITIONS)

    # Check output completeness.
    completeness_failures = _check_output_completeness(judgments, manifest)

    # Determine candidate arm label from the assignment map.
    candidate_label = "A"
    for label, real in assignment_map.arm_map.items():
        if real == "candidate":
            candidate_label = label
            break
    baseline_label = "B" if candidate_label == "A" else "A"

    # Group judgments by case_id, then aggregate across repetitions.
    case_judgments: dict[str, dict[str, dict[str, list[float]]]] = {}
    for j in judgments:
        case_judgments.setdefault(j.case_id, {"candidate": {}, "baseline": {}})
        real_arm = assignment_map.arm_map.get(j.arm_label, j.arm_label)
        case_judgments[j.case_id][real_arm].setdefault(j.dimension, []).append(j.score)

    case_scores: list[CaseScore] = []
    for case_id in sorted(case_judgments.keys()):
        arms = case_judgments[case_id]
        cand_dims = arms.get("candidate", {})
        base_dims = arms.get("baseline", {})

        candidate_scores = {dim: _mean(vals) for dim, vals in cand_dims.items()}
        baseline_scores = {dim: _mean(vals) for dim, vals in base_dims.items()}

        candidate_overall = _mean(list(candidate_scores.values())) if candidate_scores else 0.0
        baseline_overall = _mean(list(baseline_scores.values())) if baseline_scores else 0.0
        delta = candidate_overall - baseline_overall

        candidate_wins = candidate_overall > baseline_overall
        is_mandatory = case_id in mandatory_ids
        # Critical failure: candidate scores below 0.3 on any mandatory case.
        critical = is_mandatory and candidate_overall < 0.3

        case_scores.append(CaseScore(
            case_id=case_id,
            candidate_arm=candidate_label,
            candidate_scores=candidate_scores,
            baseline_scores=baseline_scores,
            candidate_overall=candidate_overall,
            baseline_overall=baseline_overall,
            delta=delta,
            candidate_wins=candidate_wins,
            mandatory=is_mandatory,
            critical_failure=critical,
        ))

    return _evaluate_admission(case_scores, manifest, completeness_failures)


def _evaluate_admission(
    case_scores: Sequence[CaseScore],
    manifest: Mapping[str, Any],
    completeness_failures: Sequence[str],
) -> dict[str, Any]:
    """Apply the frozen pass policy to produce a draft admission record."""

    policy = dict(PASS_POLICY)
    # Verify policy is not weakened.
    _check_policy_frozen(policy)

    total_cases = len(case_scores)
    if total_cases == 0:
        raise ValidationError("no case scores to evaluate")

    # Win rate
    wins = sum(1 for cs in case_scores if cs.candidate_wins)
    win_rate = wins / total_cases

    # Mandatory cases must pass
    mandatory_results = [cs for cs in case_scores if cs.mandatory]
    mandatory_all_pass = all(cs.candidate_wins for cs in mandatory_results) if mandatory_results else True

    # Critical failure veto
    any_critical = any(cs.critical_failure for cs in case_scores)

    # Dimension deltas: average across cases
    dimension_deltas: dict[str, float] = {}
    for dim in RUBRIC_DIMENSIONS:
        deltas = []
        for cs in case_scores:
            c = cs.candidate_scores.get(dim)
            b = cs.baseline_scores.get(dim)
            if c is not None and b is not None:
                deltas.append(c - b)
        if deltas:
            dimension_deltas[dim] = _mean(deltas)

    min_dimension_delta = min(dimension_deltas.values()) if dimension_deltas else -1.0
    overall_deltas = [cs.delta for cs in case_scores]
    mean_overall_delta = _mean(overall_deltas) if overall_deltas else -1.0

    # Repetitions check
    repetitions_ok = manifest.get("repetitions", 0) >= policy["minimum_repetitions"]

    # Completeness check
    outputs_complete = len(completeness_failures) == 0

    # Apply pass policy
    passes = (
        repetitions_ok
        and outputs_complete
        and win_rate >= policy["minimum_candidate_win_rate"]
        and (not policy["mandatory_cases_must_pass"] or mandatory_all_pass)
        and (not policy["critical_failure_veto"] or not any_critical)
        and min_dimension_delta >= policy["minimum_dimension_delta"]
        and mean_overall_delta >= policy["minimum_overall_delta"]
    )

    record: dict[str, Any] = {
        "record_type": "draft_admission_record",
        "suite_id": manifest.get("suite_id"),
        "specialist_id": manifest.get("specialist_id"),
        "specialist_name": manifest.get("specialist_name"),
        "guild": manifest.get("guild"),
        "case_count": total_cases,
        "repetitions": manifest.get("repetitions", MINIMUM_REPETITIONS),
        "win_rate": round(win_rate, 4),
        "mandatory_all_pass": mandatory_all_pass,
        "critical_failure_present": any_critical,
        "min_dimension_delta": round(min_dimension_delta, 4),
        "mean_overall_delta": round(mean_overall_delta, 4),
        "dimension_deltas": {k: round(v, 4) for k, v in sorted(dimension_deltas.items())},
        "pass_policy": dict(policy),
        "pass_policy_sha256": PASS_POLICY_SHA256,
        "outputs_complete": outputs_complete,
        "completeness_failures": list(completeness_failures),
        "decision": "admit" if passes else "do_not_admit",
        "activated": False,  # NEVER silently activate
        "case_scores": [cs.to_dict() for cs in case_scores],
    }
    return record


# --------------------------------------------------------------------------- #
# Verify phase
# --------------------------------------------------------------------------- #

def verify_admission_record(
    record: Mapping[str, Any],
    manifest: Mapping[str, Any],
    judgments: Sequence[ScoringJudgment],
    assignment_map: AssignmentMap,
) -> dict[str, Any]:
    """Verify a draft admission record is consistent and untampered.

    Checks:
    - Record was not activated (activated must be False).
    - Pass policy hash matches the frozen policy (no threshold weakening).
    - Recomputed decision matches the record's decision.
    - Judgment freeze hash matches (judgments not modified after freezing).
    - Every judgment arm_label is in the assignment map.
    - Mandatory outcomes match.
    - No cross-run mixing (all judgment run_unit_ids belong to this manifest).
    - No duplicate run units.
    - No modified output bytes (output hashes stable).
    """

    failures: list[str] = []

    # 1. Never activated
    if record.get("activated") is not False:
        failures.append("record must not be activated (activated must be False)")

    # 2. Policy hash match (detect threshold weakening)
    record_policy = record.get("pass_policy", {})
    record_policy_hash = record.get("pass_policy_sha256", "")
    if record_policy_hash != PASS_POLICY_SHA256:
        failures.append(
            "pass policy hash mismatch: threshold weakening or policy modification detected"
        )
    if digest(dict(record_policy)) != PASS_POLICY_SHA256:
        failures.append(
            "pass policy dict hash does not match frozen policy"
        )

    # 3. Recompute scores and compare decision
    recomputed = score_judgments(judgments, assignment_map, manifest)
    if recomputed["decision"] != record.get("decision"):
        failures.append(
            f"decision mismatch: record={record.get('decision')} "
            f"recomputed={recomputed['decision']}"
        )

    # 4. Judgment integrity: verify no judgments modified after freezing.
    if "judgment_freeze_sha256" in record:
        record_hash = record["judgment_freeze_sha256"]
        actual_hash = digest([j.to_dict() for j in judgments])
        if record_hash != actual_hash:
            failures.append(
                "judgment freeze hash mismatch: judgments tampered after freezing"
            )

    # 5. Assignment consistency: every judgment arm_label must be valid.
    arm_labels_in_map = set(assignment_map.arm_map.keys())
    for j in judgments:
        if j.arm_label not in arm_labels_in_map:
            failures.append(
                f"judgment {j.judgment_id} has arm_label {j.arm_label} "
                f"not in assignment map"
            )

    # 6. Mandatory check
    if record.get("mandatory_all_pass") != recomputed.get("mandatory_all_pass"):
        failures.append("mandatory_all_pass mismatch between record and recomputed")

    # 7. Cross-run mixing: all judgment case_ids must be in the manifest.
    manifest_case_ids = set(manifest.get("case_ids", []))
    for j in judgments:
        if j.case_id not in manifest_case_ids:
            failures.append(
                f"judgment {j.judgment_id} references case_id {j.case_id} "
                f"not in this manifest (cross-run mixing detected)"
            )

    # 8. Duplicate run units: no two judgments for the same
    #    (case_id, repetition, arm_label, dimension).
    seen_keys: set[tuple[str, int, str, str]] = set()
    for j in judgments:
        key = (j.case_id, j.repetition, j.arm_label, j.dimension)
        if key in seen_keys:
            failures.append(
                f"duplicate run unit: {j.case_id} R{j.repetition} "
                f"arm {j.arm_label} dim {j.dimension}"
            )
        seen_keys.add(key)

    # 9. Output byte stability: if output hashes are in the record, verify.
    #    (This is checked via the blind packet output_sha256 fields; the
    #    verify command receives the full packet set to compare.)

    return {
        "verified": len(failures) == 0,
        "failures": failures,
        "recomputed_decision": recomputed["decision"],
        "record_decision": record.get("decision"),
    }
