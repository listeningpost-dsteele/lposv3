"""Immutable records for the Sentinel Adversarial Assurance Guild.

Sentinel output is *untrusted by default*.  A :class:`SecurityAssessment` becomes
usable only when an independently produced :class:`SecurityAssessmentReview` binds
its exact hash, attests fresh-context isolation, and passes deterministic structural
verification.  Reports contain only redacted evidence and remediation guidance from a
trusted assessment.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from ..canonical import digest, freeze_mapping, parse_timestamp, require_id, require_text, utc_now
from ..errors import ValidationError
from ..models import ReviewDecision, ReviewEnvelope, ReviewResult, Serializable

SENTINEL_ORGANIZATION_ID = "GUILD-039"
SENTINEL_SPECIALIST_ID = "SPECIALIST-033"
SENTINEL_POLICY_VERSION = "2026.07.22.1"
SENTINEL_PRODUCER_ID = "sentinel-static-analyzer"

SEVERITIES = ("critical", "high", "medium", "low", "info")
SEVERITY_RANK = {value: index for index, value in enumerate(SEVERITIES)}
ASSESSMENT_SCOPES = ("artifact", "task_completion", "control_plane")
ASSESSMENT_MODES = ("passive", "isolated")
ASSESSMENT_STATUSES = ("clean", "findings", "error")
REPORT_STATES = ("attention_required", "assurance_failure")
REQUIRED_STRUCTURAL_CHECKS = frozenset(
    {
        "raw_output_untrusted",
        "policy_current",
        "all_rules_accounted_for",
        "producer_reviewer_separated",
        "fresh_context_attested",
        "envelope_hash_binding",
        "target_revision_present",
        "evidence_redacted",
        "findings_reproducible",
    }
)


def _text_tuple(name: str, values: Sequence[str], *, identifiers: bool = False) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)):
        raise ValidationError(f"{name} must be a sequence of strings")
    result: list[str] = []
    for item in tuple(values):
        value = require_id(name, item) if identifiers else require_text(name, item, max_length=20_000)
        if value not in result:
            result.append(value)
    return tuple(result)


def _sha256(name: str, value: str | None, *, optional: bool = False) -> str | None:
    if value is None and optional:
        return None
    if not isinstance(value, str) or len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
        raise ValidationError(f"{name} must be a lowercase SHA-256 digest")
    return value


@dataclass(frozen=True, slots=True)
class ActiveEngagementScope(Serializable):
    """Exact, non-secret scope for a separately authorized active security test.

    Creating this object does not authorize execution.  The scope hash must be bound
    to an ordinary LPOS :class:`ActionPlan` and independently verified
    :class:`ApprovalGrant` before any active probe may start.
    """

    engagement_id: str
    task_id: str
    target_owner: str
    targets: tuple[str, ...]
    excluded_assets: tuple[str, ...]
    allowed_methods: tuple[str, ...]
    isolated_environment: str
    network_boundary: str
    data_handling: str
    stop_conditions: tuple[str, ...]
    rollback_plan: str
    window_start: str
    window_end: str
    created_at: str = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        require_id("engagement_id", self.engagement_id)
        require_id("task_id", self.task_id)
        object.__setattr__(self, "target_owner", require_text("target_owner", self.target_owner, max_length=2_048))
        object.__setattr__(self, "targets", _text_tuple("engagement target", self.targets))
        object.__setattr__(self, "excluded_assets", _text_tuple("excluded asset", self.excluded_assets))
        allowed_methods = _text_tuple("allowed method", self.allowed_methods)
        prohibited = ("destructive", "persistence", "exfiltrat", "denial of service", "ransom", "wipe")
        if any(any(token in method.casefold() for token in prohibited) for method in allowed_methods):
            raise ValidationError("active engagement scope contains a prohibited destructive method")
        object.__setattr__(self, "allowed_methods", allowed_methods)
        if not self.targets or not self.excluded_assets or not self.allowed_methods:
            raise ValidationError("active engagement scope requires targets, exclusions, and allowed methods")
        environment = require_text("isolated_environment", self.isolated_environment, max_length=2_048)
        if environment.casefold() in {"production", "prod", "live", "none", "shared"}:
            raise ValidationError("active engagement requires a dedicated isolated environment")
        object.__setattr__(self, "isolated_environment", environment)
        boundary = require_text("network_boundary", self.network_boundary, max_length=2_048)
        if "deny" not in boundary.casefold() and "isolat" not in boundary.casefold():
            raise ValidationError("active engagement network boundary must be deny-by-default or isolated")
        object.__setattr__(self, "network_boundary", boundary)
        object.__setattr__(self, "data_handling", require_text("data_handling", self.data_handling, max_length=20_000))
        object.__setattr__(self, "stop_conditions", _text_tuple("stop condition", self.stop_conditions))
        if not self.stop_conditions:
            raise ValidationError("active engagement requires stop conditions")
        object.__setattr__(self, "rollback_plan", require_text("rollback_plan", self.rollback_plan, max_length=20_000))
        start = parse_timestamp(self.window_start)
        end = parse_timestamp(self.window_end)
        if end <= start:
            raise ValidationError("active engagement window_end must be after window_start")
        parse_timestamp(self.created_at)

    @property
    def scope_hash(self) -> str:
        return digest(self)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ActiveEngagementScope":
        data = dict(value)
        for name in ("targets", "excluded_assets", "allowed_methods", "stop_conditions"):
            data[name] = tuple(data.get(name, ()))
        return cls(**data)


@dataclass(frozen=True, slots=True)
class FindingEvidence(Serializable):
    """A privacy-preserving pointer to evidence inside an inspected target."""

    kind: str
    location: str
    redacted_excerpt: str
    evidence_hash: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "kind", require_text("evidence kind", self.kind, max_length=128).lower())
        object.__setattr__(self, "location", require_text("evidence location", self.location, max_length=2_048))
        object.__setattr__(
            self,
            "redacted_excerpt",
            require_text("redacted excerpt", self.redacted_excerpt, max_length=1_000),
        )
        _sha256("evidence_hash", self.evidence_hash)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "FindingEvidence":
        return cls(**dict(value))


@dataclass(frozen=True, slots=True)
class RemediationPlan(Serializable):
    summary: str
    steps: tuple[str, ...]
    verification: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "summary", require_text("remediation summary", self.summary, max_length=20_000))
        object.__setattr__(self, "steps", _text_tuple("remediation step", self.steps))
        object.__setattr__(self, "verification", _text_tuple("verification step", self.verification))
        if not self.steps or not self.verification:
            raise ValidationError("remediation requires implementation and verification steps")

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "RemediationPlan":
        data = dict(value)
        data["steps"] = tuple(data.get("steps", ()))
        data["verification"] = tuple(data.get("verification", ()))
        return cls(**data)


@dataclass(frozen=True, slots=True)
class SecurityFinding(Serializable):
    finding_id: str
    assessment_id: str
    task_id: str
    artifact_id: str | None
    artifact_hash: str | None
    rule_id: str
    severity: str
    category: str
    title: str
    description: str
    evidence: tuple[FindingEvidence, ...]
    remediation: RemediationPlan
    confidence: float
    blocking: bool
    fingerprint: str
    created_at: str = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        require_id("finding_id", self.finding_id)
        require_id("assessment_id", self.assessment_id)
        require_id("task_id", self.task_id)
        if self.artifact_id is not None:
            require_id("artifact_id", self.artifact_id)
        _sha256("artifact_hash", self.artifact_hash, optional=True)
        require_id("rule_id", self.rule_id)
        if self.severity not in SEVERITIES:
            raise ValidationError(f"unknown Sentinel severity: {self.severity}")
        object.__setattr__(self, "category", require_text("finding category", self.category, max_length=128).lower())
        object.__setattr__(self, "title", require_text("finding title", self.title, max_length=1_024))
        object.__setattr__(self, "description", require_text("finding description", self.description, max_length=20_000))
        if isinstance(self.evidence, (str, bytes)):
            raise ValidationError("finding evidence must be a sequence")
        evidence = tuple(self.evidence)
        if not evidence or any(not isinstance(item, FindingEvidence) for item in evidence):
            raise ValidationError("finding requires typed evidence")
        object.__setattr__(self, "evidence", evidence)
        if not isinstance(self.remediation, RemediationPlan):
            raise ValidationError("finding remediation must be a RemediationPlan")
        if isinstance(self.confidence, bool) or not isinstance(self.confidence, (int, float)):
            raise ValidationError("finding confidence must be numeric")
        if not 0 <= float(self.confidence) <= 1:
            raise ValidationError("finding confidence must be between 0 and 1")
        if not isinstance(self.blocking, bool):
            raise ValidationError("finding blocking must be boolean")
        expected = digest(
            {
                "task_id": self.task_id,
                "artifact_hash": self.artifact_hash,
                "rule_id": self.rule_id,
                "evidence_hashes": tuple(item.evidence_hash for item in evidence),
            }
        )
        if self.fingerprint != expected:
            raise ValidationError("finding fingerprint does not bind to its target and evidence")
        parse_timestamp(self.created_at)

    @classmethod
    def create(
        cls,
        *,
        finding_id: str,
        assessment_id: str,
        task_id: str,
        artifact_id: str | None,
        artifact_hash: str | None,
        rule_id: str,
        severity: str,
        category: str,
        title: str,
        description: str,
        evidence: Sequence[FindingEvidence],
        remediation: RemediationPlan,
        confidence: float,
        blocking: bool,
    ) -> "SecurityFinding":
        evidence_tuple = tuple(evidence)
        fingerprint = digest(
            {
                "task_id": task_id,
                "artifact_hash": artifact_hash,
                "rule_id": rule_id,
                "evidence_hashes": tuple(item.evidence_hash for item in evidence_tuple),
            }
        )
        return cls(
            finding_id=finding_id,
            assessment_id=assessment_id,
            task_id=task_id,
            artifact_id=artifact_id,
            artifact_hash=artifact_hash,
            rule_id=rule_id,
            severity=severity,
            category=category,
            title=title,
            description=description,
            evidence=evidence_tuple,
            remediation=remediation,
            confidence=confidence,
            blocking=blocking,
            fingerprint=fingerprint,
        )

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "SecurityFinding":
        data = dict(value)
        data["evidence"] = tuple(FindingEvidence.from_dict(item) for item in data.get("evidence", ()))
        data["remediation"] = RemediationPlan.from_dict(data["remediation"])
        return cls(**data)


@dataclass(frozen=True, slots=True)
class SecurityAssessment(Serializable):
    """Raw Sentinel output.  This record is never trusted on its own."""

    assessment_id: str
    task_id: str
    artifact_id: str | None
    artifact_hash: str | None
    scope: str
    mode: str
    trigger: str
    policy_version: str
    status: str
    checked_rules: tuple[str, ...]
    findings: tuple[SecurityFinding, ...]
    limitations: tuple[str, ...]
    isolated: bool
    producer_id: str = SENTINEL_PRODUCER_ID
    organization_id: str = SENTINEL_ORGANIZATION_ID
    specialist_id: str = SENTINEL_SPECIALIST_ID
    trust_state: str = "untrusted"
    started_at: str = field(default_factory=utc_now)
    completed_at: str = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        require_id("assessment_id", self.assessment_id)
        require_id("task_id", self.task_id)
        if self.artifact_id is not None:
            require_id("artifact_id", self.artifact_id)
        _sha256("artifact_hash", self.artifact_hash, optional=True)
        if self.scope not in ASSESSMENT_SCOPES:
            raise ValidationError(f"unknown assessment scope: {self.scope}")
        if self.mode not in ASSESSMENT_MODES:
            raise ValidationError(f"unknown assessment mode: {self.mode}")
        object.__setattr__(self, "trigger", require_text("assessment trigger", self.trigger, max_length=256).lower())
        object.__setattr__(self, "policy_version", require_text("policy_version", self.policy_version, max_length=128))
        if self.status not in ASSESSMENT_STATUSES:
            raise ValidationError(f"unknown assessment status: {self.status}")
        object.__setattr__(self, "checked_rules", _text_tuple("checked rule", self.checked_rules, identifiers=True))
        if isinstance(self.findings, (str, bytes)):
            raise ValidationError("assessment findings must be a sequence")
        findings = tuple(self.findings)
        if any(not isinstance(item, SecurityFinding) for item in findings):
            raise ValidationError("assessment findings must contain SecurityFinding values")
        for finding in findings:
            if finding.assessment_id != self.assessment_id or finding.task_id != self.task_id:
                raise ValidationError("assessment contains a finding for another assessment or task")
            if finding.artifact_hash != self.artifact_hash:
                raise ValidationError("assessment finding does not bind to the assessment artifact")
        object.__setattr__(self, "findings", findings)
        object.__setattr__(self, "limitations", _text_tuple("assessment limitation", self.limitations))
        if not isinstance(self.isolated, bool):
            raise ValidationError("assessment isolation flag must be boolean")
        if self.producer_id != SENTINEL_PRODUCER_ID:
            raise ValidationError("assessment producer is not the packaged Sentinel analyzer")
        if self.organization_id != SENTINEL_ORGANIZATION_ID:
            raise ValidationError("assessment organization is not the independent Sentinel Guild")
        if self.specialist_id != SENTINEL_SPECIALIST_ID:
            raise ValidationError("assessment specialist is not the Sentinel specialist")
        if self.trust_state != "untrusted":
            raise ValidationError("raw new-guild output must remain untrusted")
        if self.status == "clean" and findings:
            raise ValidationError("clean assessment may not contain findings")
        if self.status == "findings" and not findings:
            raise ValidationError("findings assessment must contain at least one finding")
        if self.status != "error" and not self.checked_rules:
            raise ValidationError("completed assessment must record checked rules")
        parse_timestamp(self.started_at)
        parse_timestamp(self.completed_at)
        if parse_timestamp(self.completed_at) < parse_timestamp(self.started_at):
            raise ValidationError("assessment completed before it started")

    @property
    def assessment_hash(self) -> str:
        return digest(self)

    @property
    def blocking_findings(self) -> tuple[SecurityFinding, ...]:
        return tuple(item for item in self.findings if item.blocking)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "SecurityAssessment":
        data = dict(value)
        data["checked_rules"] = tuple(data.get("checked_rules", ()))
        data["findings"] = tuple(SecurityFinding.from_dict(item) for item in data.get("findings", ()))
        data["limitations"] = tuple(data.get("limitations", ()))
        return cls(**data)


@dataclass(frozen=True, slots=True)
class SecurityAssessmentReview(Serializable):
    """Independent trust decision for one exact raw Sentinel assessment."""

    review_id: str
    assessment_id: str
    assessment_hash: str
    task_id: str
    artifact_hash: str | None
    envelope: ReviewEnvelope
    result: ReviewResult
    structural_checks: Mapping[str, bool]
    structural_failures: tuple[str, ...]
    context_isolated: bool
    producer_id: str
    reviewer_adapter: str
    review_context_id: str
    trusted: bool
    reviewed_at: str = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        require_id("review_id", self.review_id)
        require_id("assessment_id", self.assessment_id)
        _sha256("assessment_hash", self.assessment_hash)
        require_id("task_id", self.task_id)
        _sha256("artifact_hash", self.artifact_hash, optional=True)
        if not isinstance(self.envelope, ReviewEnvelope):
            raise ValidationError("Sentinel review requires a ReviewEnvelope")
        if not isinstance(self.result, ReviewResult):
            raise ValidationError("Sentinel review requires a ReviewResult")
        raw_checks = dict(self.structural_checks)
        if not raw_checks or any(not isinstance(name, str) or not isinstance(ok, bool) for name, ok in raw_checks.items()):
            raise ValidationError("Sentinel structural checks must be a non-empty boolean mapping")
        missing_checks = REQUIRED_STRUCTURAL_CHECKS - set(raw_checks)
        if missing_checks:
            raise ValidationError(
                f"Sentinel structural checks are incomplete: {sorted(missing_checks)}"
            )
        object.__setattr__(self, "structural_checks", freeze_mapping(raw_checks))
        structural_failures = _text_tuple("structural failure", self.structural_failures)
        expected_failures = tuple(name for name, passed in raw_checks.items() if not passed)
        if set(structural_failures) != set(expected_failures):
            raise ValidationError("Sentinel structural failure list does not match failed checks")
        object.__setattr__(self, "structural_failures", structural_failures)
        if not isinstance(self.context_isolated, bool):
            raise ValidationError("review context_isolated must be boolean")
        object.__setattr__(self, "producer_id", require_text("producer_id", self.producer_id, max_length=256))
        object.__setattr__(self, "reviewer_adapter", require_text("reviewer_adapter", self.reviewer_adapter, max_length=256))
        require_id("review_context_id", self.review_context_id)
        expected_isolation_token = f"fresh_context:{self.review_context_id}"
        if self.context_isolated != (expected_isolation_token in self.result.isolation):
            raise ValidationError("Sentinel review isolation does not bind the exact review context")
        if self.envelope.artifact.get("created_by_adapter") != self.producer_id:
            raise ValidationError("Sentinel review envelope producer does not match the assessment producer")
        if self.envelope.artifact.get("trust_state") != "untrusted":
            raise ValidationError("Sentinel review envelope must preserve the raw untrusted state")
        if self.envelope.artifact.get("task_id") != self.task_id:
            raise ValidationError("Sentinel review envelope does not bind the task")
        if not isinstance(self.trusted, bool):
            raise ValidationError("trusted must be boolean")
        expected_trusted = (
            self.result.decision is ReviewDecision.PASS
            and self.context_isolated
            and self.producer_id != self.reviewer_adapter
            and not self.structural_failures
            and all(raw_checks.values())
        )
        if self.trusted != expected_trusted:
            raise ValidationError("Sentinel trust decision is inconsistent with review evidence")
        if self.envelope.artifact.get("content_hash") != self.assessment_hash:
            raise ValidationError("Sentinel review envelope does not bind the assessment hash")
        parse_timestamp(self.reviewed_at)

    @property
    def review_hash(self) -> str:
        return digest(self)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "SecurityAssessmentReview":
        data = dict(value)
        data["envelope"] = ReviewEnvelope.from_dict(data["envelope"])
        data["result"] = ReviewResult.from_dict(data["result"])
        data["structural_failures"] = tuple(data.get("structural_failures", ()))
        return cls(**data)


@dataclass(frozen=True, slots=True)
class ReportFinding(Serializable):
    finding_id: str
    rule_id: str
    severity: str
    category: str
    confidence: float
    blocking: bool
    title: str
    description: str
    fingerprint: str
    evidence: tuple[FindingEvidence, ...]
    remediation_summary: str
    remediation_steps: tuple[str, ...]
    verification_steps: tuple[str, ...]

    def __post_init__(self) -> None:
        require_id("finding_id", self.finding_id)
        require_id("rule_id", self.rule_id)
        if self.severity not in SEVERITIES:
            raise ValidationError("invalid report finding severity")
        object.__setattr__(self, "category", require_text("report finding category", self.category, max_length=128).lower())
        if isinstance(self.confidence, bool) or not isinstance(self.confidence, (int, float)):
            raise ValidationError("report finding confidence must be numeric")
        if not 0 <= float(self.confidence) <= 1:
            raise ValidationError("report finding confidence must be between 0 and 1")
        if not isinstance(self.blocking, bool):
            raise ValidationError("report finding blocking must be boolean")
        object.__setattr__(self, "title", require_text("report finding title", self.title, max_length=1_024))
        object.__setattr__(self, "description", require_text("report finding description", self.description, max_length=20_000))
        _sha256("report finding fingerprint", self.fingerprint)
        if isinstance(self.evidence, (str, bytes)):
            raise ValidationError("report finding evidence must be a sequence")
        evidence = tuple(self.evidence)
        if not evidence or any(not isinstance(item, FindingEvidence) for item in evidence):
            raise ValidationError("report finding requires redacted typed evidence")
        object.__setattr__(self, "evidence", evidence)
        object.__setattr__(self, "remediation_summary", require_text("remediation summary", self.remediation_summary, max_length=20_000))
        object.__setattr__(self, "remediation_steps", _text_tuple("remediation step", self.remediation_steps))
        object.__setattr__(self, "verification_steps", _text_tuple("verification step", self.verification_steps))

    @classmethod
    def from_finding(cls, finding: SecurityFinding) -> "ReportFinding":
        return cls(
            finding_id=finding.finding_id,
            rule_id=finding.rule_id,
            severity=finding.severity,
            category=finding.category,
            confidence=finding.confidence,
            blocking=finding.blocking,
            title=finding.title,
            description=finding.description,
            fingerprint=finding.fingerprint,
            evidence=finding.evidence,
            remediation_summary=finding.remediation.summary,
            remediation_steps=finding.remediation.steps,
            verification_steps=finding.remediation.verification,
        )

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ReportFinding":
        data = dict(value)
        data["evidence"] = tuple(FindingEvidence.from_dict(item) for item in data.get("evidence", ()))
        for name in ("remediation_steps", "verification_steps"):
            data[name] = tuple(data.get(name, ()))
        return cls(**data)


@dataclass(frozen=True, slots=True)
class PrincipalSecurityReport(Serializable):
    report_id: str
    assessment_id: str
    assessment_hash: str
    review_id: str
    review_hash: str
    task_id: str
    artifact_id: str | None
    artifact_hash: str | None
    overall: str
    summary: str
    counts: Mapping[str, int]
    findings: tuple[ReportFinding, ...]
    destination: str = "principal_security_inbox"
    generated_at: str = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        require_id("report_id", self.report_id)
        require_id("assessment_id", self.assessment_id)
        _sha256("assessment_hash", self.assessment_hash)
        require_id("review_id", self.review_id)
        _sha256("review_hash", self.review_hash)
        require_id("task_id", self.task_id)
        if self.artifact_id is not None:
            require_id("artifact_id", self.artifact_id)
        _sha256("artifact_hash", self.artifact_hash, optional=True)
        if self.overall not in REPORT_STATES:
            raise ValidationError(f"unknown report overall state: {self.overall}")
        object.__setattr__(self, "summary", require_text("report summary", self.summary, max_length=20_000))
        raw_counts = dict(self.counts)
        for severity in SEVERITIES:
            value = raw_counts.get(severity, 0)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValidationError("report severity counts must be non-negative integers")
            raw_counts[severity] = value
        unknown = set(raw_counts) - set(SEVERITIES)
        if unknown:
            raise ValidationError(f"unknown severity count keys: {sorted(unknown)}")
        object.__setattr__(self, "counts", freeze_mapping(raw_counts))
        if isinstance(self.findings, (str, bytes)):
            raise ValidationError("report findings must be a sequence")
        findings = tuple(self.findings)
        if any(not isinstance(item, ReportFinding) for item in findings):
            raise ValidationError("report findings must contain ReportFinding values")
        object.__setattr__(self, "findings", findings)
        observed_counts = {severity: 0 for severity in SEVERITIES}
        for finding in findings:
            observed_counts[finding.severity] += 1
        if self.overall == "attention_required" and raw_counts != observed_counts:
            raise ValidationError("report severity counts do not match reviewed findings")
        if self.overall == "assurance_failure" and any(raw_counts.values()):
            raise ValidationError("assurance-failure reports may not count untrusted findings")
        if self.overall == "attention_required" and not findings:
            raise ValidationError("attention report requires reviewed findings")
        if self.overall == "assurance_failure" and findings:
            raise ValidationError("untrusted Sentinel output may not be presented as findings")
        if self.destination != "principal_security_inbox":
            raise ValidationError("Sentinel reports must target the Principal security inbox")
        parse_timestamp(self.generated_at)

    @property
    def report_hash(self) -> str:
        return digest(self)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "PrincipalSecurityReport":
        data = dict(value)
        data["findings"] = tuple(ReportFinding.from_dict(item) for item in data.get("findings", ()))
        return cls(**data)


@dataclass(frozen=True, slots=True)
class ReportAcknowledgement(Serializable):
    acknowledgement_id: str
    report_id: str
    acknowledged_by: str
    note: str
    acknowledged_at: str = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        require_id("acknowledgement_id", self.acknowledgement_id)
        require_id("report_id", self.report_id)
        acknowledged_by = require_text("acknowledged_by", self.acknowledged_by, max_length=2_048)
        if acknowledged_by.casefold() in {
            SENTINEL_ORGANIZATION_ID.casefold(),
            SENTINEL_SPECIALIST_ID.casefold(),
            SENTINEL_PRODUCER_ID.casefold(),
        }:
            raise ValidationError("Sentinel may not acknowledge its own report")
        object.__setattr__(self, "acknowledged_by", acknowledged_by)
        object.__setattr__(self, "note", require_text("acknowledgement note", self.note, max_length=20_000))
        parse_timestamp(self.acknowledged_at)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ReportAcknowledgement":
        return cls(**dict(value))


def severity_counts(findings: Sequence[SecurityFinding]) -> dict[str, int]:
    counts = {severity: 0 for severity in SEVERITIES}
    for finding in findings:
        counts[finding.severity] += 1
    return counts


def sort_findings(findings: Sequence[SecurityFinding]) -> tuple[SecurityFinding, ...]:
    return tuple(
        sorted(
            findings,
            key=lambda item: (SEVERITY_RANK[item.severity], not item.blocking, item.rule_id, item.fingerprint),
        )
    )
