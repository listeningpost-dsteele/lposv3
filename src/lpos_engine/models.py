"""Typed runtime envelopes for LPOS v4.

These classes are the executable form of the operating specification and reject
malformed state before it reaches storage or an adapter.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Sequence

from .canonical import (
    canonical_json,
    digest,
    freeze_mapping,
    normalize_token,
    parse_timestamp,
    require_id,
    require_text,
    text_digest,
    utc_now,
)
from .errors import ValidationError

MODEL_CLASSES = frozenset({"executive", "routine", "review", "local"})
REVIEW_EXCLUSIONS = (
    "creation_conversation",
    "creator_private_reasoning",
    "creator_self_assessment",
)


def _text_tuple(
    name: str,
    values: Sequence[str],
    *,
    normalize: bool = False,
    identifiers: bool = False,
    unique: bool = False,
    max_length: int = 200_000,
) -> tuple[str, ...]:
    """Validate a string sequence and return an immutable tuple.

    ``str`` is deliberately rejected as a sequence to prevent accidental
    character-by-character envelopes.
    """

    if isinstance(values, (str, bytes)):
        raise ValidationError(f"{name} must be a sequence of strings, not a string")
    try:
        supplied = tuple(values)
    except TypeError as exc:
        raise ValidationError(f"{name} must be a sequence of strings") from exc
    result: list[str] = []
    for item in supplied:
        if not isinstance(item, str):
            raise ValidationError(f"{name} must contain only strings")
        if normalize:
            clean = normalize_token(item)
        elif identifiers:
            clean = require_id(name, item)
        else:
            clean = require_text(name, item, max_length=max_length)
        if not unique or clean not in result:
            result.append(clean)
    return tuple(result)


def _require_bool(name: str, value: Any) -> bool:
    if not isinstance(value, bool):
        raise ValidationError(f"{name} must be boolean")
    return value


class TaskStatus(str, Enum):
    RECEIVED = "received"
    INTERPRETED = "interpreted"
    PLANNED = "planned"
    AWAITING_CLARIFICATION = "awaiting_clarification"
    AWAITING_APPROVAL = "awaiting_approval"
    EXECUTING = "executing"
    REVIEWING = "reviewing"
    CORRECTION_REQUIRED = "correction_required"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SUSPENDED = "suspended"


class ActionStatus(str, Enum):
    PLANNED = "planned"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    EXECUTING = "executing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ReviewDecision(str, Enum):
    PASS = "PASS"
    REJECT = "REJECT"


class EvidenceStatus(str, Enum):
    PROPOSED = "Proposed"
    ACTIVE = "Active"
    MEASURED = "Measured"
    VALIDATED = "Validated"
    REFUTED = "Refuted"
    INCONCLUSIVE = "Inconclusive"


class DecisionStatus(str, Enum):
    ACCEPTED = "Accepted"
    SUPERSEDED = "Superseded"


class OperationResult(str, Enum):
    OK = "ok"
    SILENT = "silent"
    ERROR = "error"


class Serializable:
    def to_dict(self) -> dict[str, Any]:
        import dataclasses

        if not dataclasses.is_dataclass(self):
            raise TypeError("Serializable must be mixed into a dataclass")
        from .canonical import jsonable

        return jsonable(self)


@dataclass(frozen=True, slots=True)
class MaterialitySignals(Serializable):
    external_or_irreversible: bool = False
    changes_approved_artifact: bool = False
    customer_or_public_facing: bool = False
    legal_financial_security_privacy: bool = False
    strategy_brand_or_taste: bool = False
    modifies_long_lived_specification: bool = False
    failure_cost_exceeds_review_cost: bool = False
    uncertain: bool = False
    explicit_principal_designation: bool | None = None
    designation_note: str | None = None

    def __post_init__(self) -> None:
        for name in (
            "external_or_irreversible",
            "changes_approved_artifact",
            "customer_or_public_facing",
            "legal_financial_security_privacy",
            "strategy_brand_or_taste",
            "modifies_long_lived_specification",
            "failure_cost_exceeds_review_cost",
            "uncertain",
        ):
            _require_bool(name, getattr(self, name))
        if self.explicit_principal_designation is not None:
            _require_bool("explicit_principal_designation", self.explicit_principal_designation)
        if self.designation_note is not None:
            require_text("designation_note", self.designation_note, max_length=20_000)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any] | None) -> "MaterialitySignals":
        data = dict(value or {})
        allowed = {field.name for field in __import__("dataclasses").fields(cls)}
        unknown = set(data) - allowed
        if unknown:
            raise ValidationError(f"unknown materiality signals: {sorted(unknown)}")
        return cls(**data)


@dataclass(frozen=True, slots=True)
class MaterialityDecision(Serializable):
    material: bool
    basis: tuple[str, ...]
    decided_at: str = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        _require_bool("material", self.material)
        object.__setattr__(self, "basis", _text_tuple("materiality basis", self.basis, unique=True))
        parse_timestamp(self.decided_at)
        if self.material and not self.basis:
            raise ValidationError("material task must record a materiality basis")


@dataclass(frozen=True, slots=True)
class RouteDecision(Serializable):
    lead_guild: str
    lead_specialist: str
    supporting_specialists: tuple[str, ...]
    craft_standards: tuple[str, ...]
    model_class: str
    required_capabilities: tuple[str, ...]
    covered_capabilities: tuple[str, ...]
    missing_capabilities: tuple[str, ...]
    substitutions: tuple[str, ...] = ()
    trace: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        require_text("lead_guild", self.lead_guild)
        require_id("lead_specialist", self.lead_specialist)
        object.__setattr__(self, "supporting_specialists", _text_tuple("supporting_specialists", self.supporting_specialists, identifiers=True, unique=True))
        object.__setattr__(self, "craft_standards", _text_tuple("craft_standards", self.craft_standards, identifiers=True, unique=True))
        object.__setattr__(self, "required_capabilities", _text_tuple("required_capabilities", self.required_capabilities, normalize=True, unique=True))
        object.__setattr__(self, "covered_capabilities", _text_tuple("covered_capabilities", self.covered_capabilities, normalize=True, unique=True))
        object.__setattr__(self, "missing_capabilities", _text_tuple("missing_capabilities", self.missing_capabilities, normalize=True, unique=True))
        object.__setattr__(self, "substitutions", _text_tuple("substitutions", self.substitutions))
        object.__setattr__(self, "trace", _text_tuple("trace", self.trace))
        if self.model_class not in MODEL_CLASSES:
            raise ValidationError(f"unknown model class: {self.model_class}")


@dataclass(frozen=True, slots=True)
class TaskEnvelope(Serializable):
    task_id: str
    principal_instruction: str
    lead_guild: str
    lead_specialist: str
    supporting_specialists: tuple[str, ...] = ()
    craft_standards: tuple[str, ...] = ()
    required_capabilities: tuple[str, ...] = ()
    constraints: Mapping[str, Any] = field(default_factory=dict)
    material: bool = False
    materiality_basis: tuple[str, ...] = ()
    model_class: str = "routine"
    deadline: str | None = None
    created_at: str = field(default_factory=utc_now)
    creator_adapter: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "task_id", require_id("task_id", self.task_id))
        object.__setattr__(
            self,
            "principal_instruction",
            require_text("principal_instruction", self.principal_instruction, max_length=200_000),
        )
        object.__setattr__(self, "lead_guild", require_text("lead_guild", self.lead_guild))
        object.__setattr__(self, "lead_specialist", require_id("lead_specialist", self.lead_specialist))
        object.__setattr__(
            self,
            "required_capabilities",
            _text_tuple("required_capabilities", self.required_capabilities, normalize=True, unique=True),
        )
        object.__setattr__(self, "supporting_specialists", _text_tuple("supporting_specialists", self.supporting_specialists, identifiers=True, unique=True))
        object.__setattr__(self, "craft_standards", _text_tuple("craft_standards", self.craft_standards, identifiers=True, unique=True))
        object.__setattr__(self, "materiality_basis", _text_tuple("materiality_basis", self.materiality_basis, unique=True))
        object.__setattr__(self, "constraints", freeze_mapping(self.constraints))
        _require_bool("material", self.material)
        if self.model_class not in MODEL_CLASSES:
            raise ValidationError(f"unknown model class: {self.model_class}")
        if self.material and not self.materiality_basis:
            raise ValidationError("material task requires materiality_basis")
        if self.deadline is not None:
            parse_timestamp(self.deadline)
        parse_timestamp(self.created_at)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "TaskEnvelope":
        data = dict(value)
        for key in (
            "supporting_specialists",
            "craft_standards",
            "required_capabilities",
            "materiality_basis",
        ):
            data[key] = tuple(data.get(key, ()))
        return cls(**data)


@dataclass(frozen=True, slots=True)
class ConflictRecord(Serializable):
    levels: tuple[str, ...]
    description: str
    resolution: str
    question_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "levels", _text_tuple("conflict levels", self.levels, unique=True))
        if len(self.levels) < 2:
            raise ValidationError("conflict must identify at least two precedence levels")
        require_text("description", self.description)
        if self.resolution not in {"asked", "precedence", "principal_override"}:
            raise ValidationError(f"invalid conflict resolution: {self.resolution}")
        if self.resolution == "asked" and not self.question_id:
            raise ValidationError("asked conflict requires question_id")

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ConflictRecord":
        data = dict(value)
        data["levels"] = tuple(data.get("levels", ()))
        return cls(**data)


@dataclass(frozen=True, slots=True)
class InterpretationContract(Serializable):
    task_id: str
    instruction_verbatim: str
    interpretation: str
    invariants: tuple[str, ...]
    conflicts: tuple[ConflictRecord, ...]
    verification_plan: tuple[str, ...]
    spec_ref: str | None
    created_at: str = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        require_id("task_id", self.task_id)
        require_text("instruction_verbatim", self.instruction_verbatim, max_length=200_000)
        require_text("interpretation", self.interpretation, max_length=200_000)
        object.__setattr__(self, "invariants", _text_tuple("contract invariant", self.invariants))
        if isinstance(self.conflicts, (str, bytes)):
            raise ValidationError("conflicts must be a sequence of ConflictRecord values")
        conflicts = tuple(self.conflicts)
        if any(not isinstance(item, ConflictRecord) for item in conflicts):
            raise ValidationError("conflicts must contain only ConflictRecord values")
        object.__setattr__(self, "conflicts", conflicts)
        object.__setattr__(self, "verification_plan", _text_tuple("verification plan item", self.verification_plan))
        if not self.verification_plan:
            raise ValidationError("interpretation contract requires a verification plan")
        for item in (*self.invariants, *self.verification_plan):
            require_text("contract item", item, max_length=20_000)
        parse_timestamp(self.created_at)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "InterpretationContract":
        data = dict(value)
        data["invariants"] = tuple(data.get("invariants", ()))
        data["verification_plan"] = tuple(data.get("verification_plan", ()))
        data["conflicts"] = tuple(ConflictRecord.from_dict(item) for item in data.get("conflicts", ()))
        return cls(**data)


@dataclass(frozen=True, slots=True)
class ArtifactSpecification(Serializable):
    artifact_id: str
    structural_decisions: Mapping[str, Any] = field(default_factory=dict)
    design_tokens: Mapping[str, Any] = field(default_factory=dict)
    invariants: tuple[str, ...] = ()
    approved_by: str | None = None
    updated_at: str = field(default_factory=utc_now)
    history: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        require_id("artifact_id", self.artifact_id)
        object.__setattr__(self, "structural_decisions", freeze_mapping(self.structural_decisions))
        object.__setattr__(self, "design_tokens", freeze_mapping(self.design_tokens))
        object.__setattr__(self, "invariants", _text_tuple("artifact invariant", self.invariants))
        object.__setattr__(self, "history", _text_tuple("artifact history", self.history))
        if self.approved_by is not None:
            require_text("approved_by", self.approved_by, max_length=2_048)
        parse_timestamp(self.updated_at)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ArtifactSpecification":
        data = dict(value)
        data["invariants"] = tuple(data.get("invariants", ()))
        data["history"] = tuple(data.get("history", ()))
        return cls(**data)


@dataclass(frozen=True, slots=True)
class Artifact(Serializable):
    artifact_id: str
    task_id: str
    media_type: str
    content: str
    content_hash: str
    baseline_ref: str | None = None
    context_bundle_id: str | None = None
    context_bundle_hash: str | None = None
    interpretation_hash: str | None = None
    artifact_spec_hash: str | None = None
    verification_evidence: tuple[str, ...] = ()
    created_at: str = field(default_factory=utc_now)
    created_by_adapter: str | None = None

    def __post_init__(self) -> None:
        require_id("artifact_id", self.artifact_id)
        require_id("task_id", self.task_id)
        require_text("media_type", self.media_type)
        if not isinstance(self.content, str):
            raise ValidationError("artifact content must be text in LPOS v4 core")
        if text_digest(self.content) != self.content_hash:
            raise ValidationError("artifact content_hash does not match content")
        object.__setattr__(self, "verification_evidence", _text_tuple("verification evidence", self.verification_evidence))
        if self.baseline_ref is not None:
            require_text("baseline_ref", self.baseline_ref, max_length=20_000)
        if self.created_by_adapter is not None:
            require_text("created_by_adapter", self.created_by_adapter, max_length=256)
        if bool(self.context_bundle_id) != bool(self.context_bundle_hash):
            raise ValidationError(
                "context_bundle_id and context_bundle_hash must be supplied together"
            )
        if self.context_bundle_id:
            require_id("context_bundle_id", self.context_bundle_id)
        for name, value in (
            ("context_bundle_hash", self.context_bundle_hash),
            ("interpretation_hash", self.interpretation_hash),
            ("artifact_spec_hash", self.artifact_spec_hash),
        ):
            if value and (
                len(value) != 64
                or any(char not in "0123456789abcdef" for char in value)
            ):
                raise ValidationError(f"{name} must be a lowercase SHA-256 digest")
        parse_timestamp(self.created_at)

    @classmethod
    def create(
        cls,
        *,
        artifact_id: str,
        task_id: str,
        media_type: str,
        content: str,
        baseline_ref: str | None = None,
        context_bundle_id: str | None = None,
        context_bundle_hash: str | None = None,
        interpretation_hash: str | None = None,
        artifact_spec_hash: str | None = None,
        verification_evidence: Sequence[str] = (),
        created_by_adapter: str | None = None,
    ) -> "Artifact":
        return cls(
            artifact_id=artifact_id,
            task_id=task_id,
            media_type=media_type,
            content=content,
            content_hash=text_digest(content),
            baseline_ref=baseline_ref,
            context_bundle_id=context_bundle_id,
            context_bundle_hash=context_bundle_hash,
            interpretation_hash=interpretation_hash,
            artifact_spec_hash=artifact_spec_hash,
            verification_evidence=tuple(verification_evidence),
            created_by_adapter=created_by_adapter,
        )

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "Artifact":
        data = dict(value)
        data["verification_evidence"] = tuple(data.get("verification_evidence", ()))
        return cls(**data)


@dataclass(frozen=True, slots=True)
class ContextBundle(Serializable):
    bundle_id: str
    task_id: str
    purpose: str
    content: str
    loaded_components: tuple[str, ...]
    missing_components: tuple[str, ...]
    excluded: tuple[str, ...]
    token_estimate: int
    bundle_hash: str
    created_at: str = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        require_id("bundle_id", self.bundle_id)
        require_id("task_id", self.task_id)
        require_text("purpose", self.purpose)
        object.__setattr__(self, "loaded_components", _text_tuple("loaded component", self.loaded_components))
        object.__setattr__(self, "missing_components", _text_tuple("missing component", self.missing_components))
        object.__setattr__(self, "excluded", _text_tuple("excluded context item", self.excluded))
        if not isinstance(self.token_estimate, int) or isinstance(self.token_estimate, bool):
            raise ValidationError("token_estimate must be an integer")
        if self.token_estimate < 0:
            raise ValidationError("token_estimate may not be negative")
        if text_digest(self.content) != self.bundle_hash:
            raise ValidationError("context bundle hash does not match content")
        parse_timestamp(self.created_at)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ContextBundle":
        data = dict(value)
        for key in ("loaded_components", "missing_components", "excluded"):
            data[key] = tuple(data.get(key, ()))
        return cls(**data)


@dataclass(frozen=True, slots=True)
class ModelOutput(Serializable):
    content: str
    media_type: str = "text/markdown"
    evidence: tuple[str, ...] = ()
    assumptions: tuple[str, ...] = ()
    adapter_metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.content, str) or not self.content.strip():
            raise ValidationError("model output content may not be empty")
        require_text("media_type", self.media_type)
        object.__setattr__(self, "evidence", _text_tuple("model evidence", self.evidence))
        object.__setattr__(self, "assumptions", _text_tuple("model assumption", self.assumptions))
        object.__setattr__(self, "adapter_metadata", freeze_mapping(self.adapter_metadata))

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ModelOutput":
        data = dict(value)
        data["evidence"] = tuple(data.get("evidence", ()))
        data["assumptions"] = tuple(data.get("assumptions", ()))
        return cls(**data)


@dataclass(frozen=True, slots=True)
class ReviewEnvelope(Serializable):
    brief: str
    baseline: Mapping[str, Any] | None
    artifact: Mapping[str, Any]
    interpretation_contract: Mapping[str, Any]
    artifact_specification: Mapping[str, Any]
    mapped_craft_standards: tuple[str, ...]
    verification_evidence: tuple[str, ...]
    intended_outcome: str
    excluded_always: tuple[str, ...] = REVIEW_EXCLUSIONS

    def __post_init__(self) -> None:
        require_text("brief", self.brief, max_length=200_000)
        require_text("intended_outcome", self.intended_outcome, max_length=200_000)
        object.__setattr__(self, "mapped_craft_standards", _text_tuple("mapped craft standard", self.mapped_craft_standards, identifiers=True, unique=True))
        object.__setattr__(self, "verification_evidence", _text_tuple("review evidence", self.verification_evidence))
        object.__setattr__(self, "excluded_always", _text_tuple("review exclusion", self.excluded_always))
        if self.excluded_always != REVIEW_EXCLUSIONS:
            raise ValidationError("review envelope exclusions are immutable")
        object.__setattr__(self, "artifact", freeze_mapping(self.artifact))
        object.__setattr__(
            self,
            "interpretation_contract",
            freeze_mapping(self.interpretation_contract),
        )
        object.__setattr__(
            self,
            "artifact_specification",
            freeze_mapping(self.artifact_specification),
        )
        if self.baseline is not None:
            object.__setattr__(self, "baseline", freeze_mapping(self.baseline))

    @property
    def envelope_hash(self) -> str:
        return digest(self.to_dict())

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ReviewEnvelope":
        data = dict(value)
        data["mapped_craft_standards"] = tuple(data.get("mapped_craft_standards", ()))
        data["verification_evidence"] = tuple(data.get("verification_evidence", ()))
        data["excluded_always"] = tuple(data.get("excluded_always", REVIEW_EXCLUSIONS))
        return cls(**data)


@dataclass(frozen=True, slots=True)
class ReviewResult(Serializable):
    decision: ReviewDecision
    isolation: str
    recomputed: str
    contract_violations: tuple[str, ...] = ()
    truth: tuple[str, ...] = ()
    reasoning: tuple[str, ...] = ()
    craft: tuple[str, ...] = ()
    outcome: tuple[str, ...] = ()
    regressions: tuple[str, ...] = ()
    required_corrections: tuple[str, ...] = ()
    strengths_to_preserve: tuple[str, ...] = ()
    evidence_reviewed: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.decision, ReviewDecision):
            object.__setattr__(self, "decision", ReviewDecision(self.decision))
        require_text("isolation", self.isolation)
        require_text("recomputed", self.recomputed)
        for name in (
            "contract_violations",
            "truth",
            "reasoning",
            "craft",
            "outcome",
            "regressions",
            "required_corrections",
            "strengths_to_preserve",
            "evidence_reviewed",
        ):
            object.__setattr__(self, name, _text_tuple(name, getattr(self, name)))
        if self.decision is ReviewDecision.REJECT and not (
            self.required_corrections or self.contract_violations or self.regressions
        ):
            raise ValidationError("rejected review must explain a correction or violation")

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ReviewResult":
        data = dict(value)
        data["decision"] = ReviewDecision(data["decision"])
        for key in (
            "contract_violations",
            "truth",
            "reasoning",
            "craft",
            "outcome",
            "regressions",
            "required_corrections",
            "strengths_to_preserve",
            "evidence_reviewed",
        ):
            data[key] = tuple(data.get(key, ()))
        return cls(**data)


@dataclass(frozen=True, slots=True)
class MessageIdentity(Serializable):
    channel: str
    provider: str
    message_id: str
    thread_id: str | None
    sender: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "channel", normalize_token(self.channel))
        object.__setattr__(self, "provider", normalize_token(self.provider))
        require_text("message_id", self.message_id, max_length=1024)
        require_text("sender", self.sender, max_length=2048)

    @property
    def replay_key(self) -> str:
        return digest(
            {
                "channel": self.channel,
                "provider": self.provider,
                "message_id": self.message_id,
            }
        )

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "MessageIdentity":
        return cls(**dict(value))


@dataclass(frozen=True, slots=True)
class ActionPlan(Serializable):
    action_id: str
    task_id: str
    kind: str
    parameters: Mapping[str, Any]
    external: bool
    reversible: bool
    approval_required: bool
    exact_action: str
    action_hash: str
    idempotency_key: str
    risk_tags: tuple[str, ...] = ()
    created_at: str = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        require_id("action_id", self.action_id)
        require_id("task_id", self.task_id)
        object.__setattr__(self, "kind", normalize_token(self.kind))
        object.__setattr__(self, "parameters", freeze_mapping(self.parameters))
        _require_bool("external", self.external)
        _require_bool("reversible", self.reversible)
        _require_bool("approval_required", self.approval_required)
        object.__setattr__(self, "risk_tags", _text_tuple("risk tag", self.risk_tags, normalize=True, unique=True))
        require_text("idempotency_key", self.idempotency_key, max_length=1024)
        # The exact action deliberately excludes the database identity.  This lets
        # a retry reconstruct the same logical action with a fresh candidate ID
        # while the idempotency key resolves it to the original stored action.
        expected = {
            "task_id": self.task_id,
            "kind": self.kind,
            "parameters": self.parameters,
            "external": self.external,
            "reversible": self.reversible,
            "idempotency_key": self.idempotency_key,
        }
        if canonical_json(expected) != self.exact_action:
            raise ValidationError("exact_action is not the canonical action payload")
        if digest(expected) != self.action_hash:
            raise ValidationError("action_hash does not bind to exact_action")
        if (self.external or not self.reversible) and not self.approval_required:
            raise ValidationError("external or irreversible actions must require approval")
        parse_timestamp(self.created_at)

    @classmethod
    def create(
        cls,
        *,
        action_id: str,
        task_id: str,
        kind: str,
        parameters: Mapping[str, Any],
        external: bool,
        reversible: bool,
        idempotency_key: str,
        approval_required: bool | None = None,
        risk_tags: Sequence[str] = (),
    ) -> "ActionPlan":
        normalized_kind = normalize_token(kind)
        exact = {
            "task_id": task_id,
            "kind": normalized_kind,
            "parameters": freeze_mapping(parameters),
            "external": bool(external),
            "reversible": bool(reversible),
            "idempotency_key": require_text("idempotency_key", idempotency_key),
        }
        requires = (external or not reversible) if approval_required is None else approval_required
        return cls(
            action_id=action_id,
            task_id=task_id,
            kind=normalized_kind,
            parameters=exact["parameters"],
            external=external,
            reversible=reversible,
            approval_required=requires,
            exact_action=canonical_json(exact),
            action_hash=digest(exact),
            idempotency_key=idempotency_key,
            risk_tags=tuple(dict.fromkeys(normalize_token(item) for item in risk_tags)),
        )

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ActionPlan":
        data = dict(value)
        data["risk_tags"] = tuple(data.get("risk_tags", ()))
        return cls(**data)


@dataclass(frozen=True, slots=True)
class ApprovalRequest(Serializable):
    question_id: str
    task_id: str
    action_id: str
    kind: str
    exact_action: str
    action_hash: str
    options: tuple[str, ...]
    recommended: str | None
    expires_policy: str
    created_at: str = field(default_factory=utc_now)
    expires_at: str | None = None

    def __post_init__(self) -> None:
        require_id("question_id", self.question_id)
        require_id("task_id", self.task_id)
        require_id("action_id", self.action_id)
        if self.kind not in {"consent", "clarification", "approval"}:
            raise ValidationError(f"invalid approval request kind: {self.kind}")
        require_text("exact_action", self.exact_action, max_length=1_000_000)
        object.__setattr__(self, "options", _text_tuple("approval option", self.options, unique=True))
        if self.recommended is not None:
            require_text("recommended", self.recommended, max_length=20_000)
        if self.action_hash != text_digest(self.exact_action):
            # ActionPlan hashes the parsed canonical payload.  For a canonical JSON
            # string these values are equal; checking this prevents altered text.
            try:
                import json

                if digest(json.loads(self.exact_action)) != self.action_hash:
                    raise ValidationError("approval request action hash mismatch")
            except (ValueError, TypeError) as exc:
                raise ValidationError("approval request exact_action is invalid JSON") from exc
        if not self.options:
            raise ValidationError("approval request requires explicit options")
        if self.expires_policy not in {"hold", "timestamp"}:
            raise ValidationError("expires_policy must be hold or timestamp")
        if self.expires_policy == "timestamp" and not self.expires_at:
            raise ValidationError("timestamp expiry requires expires_at")
        if self.expires_at:
            parse_timestamp(self.expires_at)
        parse_timestamp(self.created_at)

    @classmethod
    def from_plan(
        cls,
        plan: ActionPlan,
        *,
        question_id: str,
        expires_at: str | None = None,
    ) -> "ApprovalRequest":
        return cls(
            question_id=question_id,
            task_id=plan.task_id,
            action_id=plan.action_id,
            kind="approval",
            exact_action=plan.exact_action,
            action_hash=plan.action_hash,
            options=("Approve exact action", "Reject", "Ask a question"),
            recommended=None,
            expires_policy="timestamp" if expires_at else "hold",
            expires_at=expires_at,
        )

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ApprovalRequest":
        data = dict(value)
        data["options"] = tuple(data.get("options", ()))
        return cls(**data)


@dataclass(frozen=True, slots=True)
class ApprovalGrant(Serializable):
    grant_id: str
    question_id: str
    task_id: str
    action_id: str
    granted_action: str
    action_hash: str
    channel: str
    message_identity: MessageIdentity
    verified_identity: str
    granted_at: str = field(default_factory=utc_now)
    expires_at: str | None = None

    def __post_init__(self) -> None:
        require_id("grant_id", self.grant_id)
        require_id("question_id", self.question_id)
        require_id("task_id", self.task_id)
        require_id("action_id", self.action_id)
        object.__setattr__(self, "channel", normalize_token(self.channel))
        require_text("granted_action", self.granted_action, max_length=1_000_000)
        require_text("verified_identity", self.verified_identity, max_length=2048)
        if self.channel != self.message_identity.channel:
            raise ValidationError("grant channel does not match message identity")
        try:
            import json

            if digest(json.loads(self.granted_action)) != self.action_hash:
                raise ValidationError("approval grant action hash mismatch")
        except (ValueError, TypeError) as exc:
            raise ValidationError("granted_action is invalid JSON") from exc
        parse_timestamp(self.granted_at)
        if self.expires_at:
            parse_timestamp(self.expires_at)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ApprovalGrant":
        data = dict(value)
        data["message_identity"] = MessageIdentity.from_dict(data["message_identity"])
        return cls(**data)


@dataclass(frozen=True, slots=True)
class ActionResult(Serializable):
    action_id: str
    success: bool
    output: Mapping[str, Any]
    executed_at: str = field(default_factory=utc_now)
    adapter: str = "unknown"
    error: str | None = None

    def __post_init__(self) -> None:
        require_id("action_id", self.action_id)
        _require_bool("success", self.success)
        object.__setattr__(self, "output", freeze_mapping(self.output))
        require_text("adapter", self.adapter, max_length=256)
        if self.success and self.error:
            raise ValidationError("successful action may not include an error")
        if not self.success and not self.error:
            raise ValidationError("failed action requires an error")
        parse_timestamp(self.executed_at)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ActionResult":
        return cls(**dict(value))


@dataclass(frozen=True, slots=True)
class EvidenceRecord(Serializable):
    id: str
    recommendation: str
    owner: str
    expected_outcome: str
    baseline: str
    target: str
    observed: str
    confidence: float
    measurement: str
    fallback_used: bool
    review_date: str | None
    status: EvidenceStatus

    def __post_init__(self) -> None:
        require_id("evidence id", self.id)
        for name in (
            "recommendation",
            "owner",
            "expected_outcome",
            "baseline",
            "target",
            "observed",
            "measurement",
        ):
            require_text(name, getattr(self, name), max_length=200_000)
        if isinstance(self.confidence, bool) or not isinstance(self.confidence, (int, float)):
            raise ValidationError("confidence must be numeric")
        if not 0 <= self.confidence <= 1:
            raise ValidationError("confidence must be between 0 and 1")
        _require_bool("fallback_used", self.fallback_used)
        if not isinstance(self.status, EvidenceStatus):
            object.__setattr__(self, "status", EvidenceStatus(self.status))
        if self.review_date:
            parse_timestamp(self.review_date)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "EvidenceRecord":
        data = dict(value)
        data["status"] = EvidenceStatus(data["status"])
        return cls(**data)


@dataclass(frozen=True, slots=True)
class DecisionRecord(Serializable):
    id: str
    date: str
    context: str
    decision: str
    rationale: str
    alternatives: tuple[str, ...]
    consequences: str
    risks: str
    implementation_notes: str
    references: tuple[str, ...]
    status: DecisionStatus
    superseded_by: str | None
    owner: str

    def __post_init__(self) -> None:
        require_id("decision id", self.id)
        parse_timestamp(self.date)
        for name in (
            "context",
            "decision",
            "rationale",
            "consequences",
            "risks",
            "implementation_notes",
            "owner",
        ):
            require_text(name, getattr(self, name), max_length=200_000)
        object.__setattr__(self, "alternatives", _text_tuple("decision alternative", self.alternatives))
        object.__setattr__(self, "references", _text_tuple("decision reference", self.references))
        if not isinstance(self.status, DecisionStatus):
            object.__setattr__(self, "status", DecisionStatus(self.status))
        if self.status is DecisionStatus.SUPERSEDED and not self.superseded_by:
            raise ValidationError("superseded decision requires superseded_by")

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "DecisionRecord":
        data = dict(value)
        data["alternatives"] = tuple(data.get("alternatives", ()))
        data["references"] = tuple(data.get("references", ()))
        data["status"] = DecisionStatus(data["status"])
        return cls(**data)


@dataclass(frozen=True, slots=True)
class StandingOperationRun(Serializable):
    so_id: str
    run_id: str
    idempotency_key: str
    started_at: str
    finished_at: str
    result: OperationResult
    outputs_ref: str
    evidence_id: str
    fallback_used: bool
    model_class: str

    def __post_init__(self) -> None:
        require_id("so_id", self.so_id)
        require_id("run_id", self.run_id)
        require_text("idempotency_key", self.idempotency_key)
        require_text("outputs_ref", self.outputs_ref, max_length=20_000)
        require_id("evidence_id", self.evidence_id)
        _require_bool("fallback_used", self.fallback_used)
        parse_timestamp(self.started_at)
        parse_timestamp(self.finished_at)
        if not isinstance(self.result, OperationResult):
            object.__setattr__(self, "result", OperationResult(self.result))
        if self.model_class not in MODEL_CLASSES:
            raise ValidationError(f"unknown model class: {self.model_class}")

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "StandingOperationRun":
        data = dict(value)
        data["result"] = OperationResult(data["result"])
        return cls(**data)


@dataclass(frozen=True, slots=True)
class WorkflowStep(Serializable):
    step_id: str
    handler: str
    depends_on: tuple[str, ...] = ()
    continue_on_error: bool = False

    def __post_init__(self) -> None:
        require_id("step_id", self.step_id)
        object.__setattr__(self, "handler", normalize_token(self.handler))
        object.__setattr__(self, "depends_on", _text_tuple("step dependency", self.depends_on, identifiers=True, unique=True))
        _require_bool("continue_on_error", self.continue_on_error)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "WorkflowStep":
        data = dict(value)
        data["depends_on"] = tuple(data.get("depends_on", ()))
        return cls(**data)


@dataclass(frozen=True, slots=True)
class WorkflowDefinition(Serializable):
    so_id: str
    model_class: str
    steps: tuple[WorkflowStep, ...]

    def __post_init__(self) -> None:
        require_id("so_id", self.so_id)
        if isinstance(self.steps, (str, bytes)):
            raise ValidationError("workflow steps must be a sequence of WorkflowStep values")
        steps = tuple(self.steps)
        if any(not isinstance(step, WorkflowStep) for step in steps):
            raise ValidationError("workflow steps must contain only WorkflowStep values")
        object.__setattr__(self, "steps", steps)
        if self.model_class not in MODEL_CLASSES:
            raise ValidationError(f"unknown model class: {self.model_class}")
        if not self.steps:
            raise ValidationError("workflow requires at least one step")
        ids = [step.step_id for step in self.steps]
        if len(ids) != len(set(ids)):
            raise ValidationError("workflow step ids must be unique")
        known = set(ids)
        for step in self.steps:
            missing = set(step.depends_on) - known
            if missing:
                raise ValidationError(f"step {step.step_id} has unknown dependencies: {sorted(missing)}")
        self._assert_acyclic()

    def _assert_acyclic(self) -> None:
        graph = {step.step_id: set(step.depends_on) for step in self.steps}
        remaining = set(graph)
        resolved: set[str] = set()
        while remaining:
            ready = {item for item in remaining if graph[item] <= resolved}
            if not ready:
                raise ValidationError("workflow dependency graph contains a cycle")
            resolved |= ready
            remaining -= ready

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "WorkflowDefinition":
        data = dict(value)
        data["steps"] = tuple(WorkflowStep.from_dict(item) for item in data.get("steps", ()))
        return cls(**data)


@dataclass(frozen=True, slots=True)
class CompletionReport(Serializable):
    task_id: str
    status: TaskStatus
    result_summary: str
    artifact_id: str | None
    artifact_hash: str | None
    material: bool
    review_decision: ReviewDecision | None
    review_isolated: bool | None
    actions: tuple[Mapping[str, Any], ...]
    evidence_ids: tuple[str, ...]
    decision_ids: tuple[str, ...]
    limitations: tuple[str, ...]
    completed_at: str = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        require_id("task_id", self.task_id)
        if not isinstance(self.status, TaskStatus):
            object.__setattr__(self, "status", TaskStatus(self.status))
        if self.status is not TaskStatus.COMPLETED:
            raise ValidationError("completion report requires completed task status")
        require_text("result_summary", self.result_summary, max_length=200_000)
        _require_bool("material", self.material)
        if self.review_isolated is not None:
            _require_bool("review_isolated", self.review_isolated)
        if isinstance(self.actions, (str, bytes)):
            raise ValidationError("completion actions must be a sequence of mappings")
        actions = tuple(freeze_mapping(item) for item in self.actions)
        object.__setattr__(self, "actions", actions)
        object.__setattr__(self, "evidence_ids", _text_tuple("evidence id", self.evidence_ids, identifiers=True, unique=True))
        object.__setattr__(self, "decision_ids", _text_tuple("decision id", self.decision_ids, identifiers=True, unique=True))
        object.__setattr__(self, "limitations", _text_tuple("limitation", self.limitations))
        if self.artifact_id is not None:
            require_id("artifact_id", self.artifact_id)
        if self.artifact_hash is not None and (len(self.artifact_hash) != 64 or any(char not in "0123456789abcdef" for char in self.artifact_hash)):
            raise ValidationError("artifact_hash must be a lowercase SHA-256 digest")
        if self.review_decision is not None and not isinstance(self.review_decision, ReviewDecision):
            object.__setattr__(self, "review_decision", ReviewDecision(self.review_decision))
        parse_timestamp(self.completed_at)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "CompletionReport":
        data = dict(value)
        data["status"] = TaskStatus(data["status"])
        if data.get("review_decision") is not None:
            data["review_decision"] = ReviewDecision(data["review_decision"])
        for key in ("actions", "evidence_ids", "decision_ids", "limitations"):
            data[key] = tuple(data.get(key, ()))
        return cls(**data)
