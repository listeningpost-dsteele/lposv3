"""Sentinel orchestration and the constitutional no-self-trust gate."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Sequence

from ..adapters.base import AdapterRegistry
from ..canonical import canonical_json, new_id, parse_timestamp, text_digest, utc_now
from ..context import ContextCompiler
from ..errors import ContextIsolationError, NotFoundError, PolicyViolation, ValidationError
from ..models import (
    ActionPlan,
    ActionStatus,
    ApprovalGrant,
    Artifact,
    ReviewDecision,
    ReviewEnvelope,
    ReviewResult,
)
from ..store import SQLiteStore
from .models import (
    ActiveEngagementScope,
    PrincipalSecurityReport,
    ReportAcknowledgement,
    ReportFinding,
    SecurityAssessment,
    SecurityAssessmentReview,
    SENTINEL_ORGANIZATION_ID,
    SENTINEL_POLICY_VERSION,
    SENTINEL_PRODUCER_ID,
    SENTINEL_SPECIALIST_ID,
    SEVERITIES,
    severity_counts,
)
from .rules import RULE_IDS, SentinelScanner, finding_signatures, redact_excerpt


if TYPE_CHECKING:
    from ..approvals import ApprovalService


@dataclass(frozen=True, slots=True)
class SentinelPolicy:
    """Deterministic boundaries for the independent security organization."""

    enabled: bool = True
    require_trusted_review: bool = True
    blocking_severities: tuple[str, ...] = ("critical", "high")
    passive_only: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.enabled, bool):
            raise ValidationError("Sentinel enabled must be boolean")
        if not isinstance(self.require_trusted_review, bool):
            raise ValidationError("Sentinel require_trusted_review must be boolean")
        if self.enabled and not self.require_trusted_review:
            raise ValidationError(
                "enabled Sentinel may not bypass independent adversarial review"
            )
        if not isinstance(self.passive_only, bool):
            raise ValidationError("Sentinel passive_only must be boolean")
        supplied = tuple(dict.fromkeys(self.blocking_severities))
        if not supplied or any(item not in SEVERITIES for item in supplied):
            raise ValidationError("Sentinel blocking severities are invalid")
        object.__setattr__(self, "blocking_severities", supplied)


class SentinelService:
    """Continuously scan Chip artifacts, then distrust and review Sentinel itself.

    The static scanner is a producer, not an authority.  Its raw assessment is
    immutable and marked untrusted.  The exact assessment hash is passed through the
    same fresh-context independent review mechanism used for material LPOS work, plus
    a deterministic re-scan.  Only a passing combined review can create a finding
    report or permit the assessment to influence task completion.
    """

    def __init__(
        self,
        store: SQLiteStore,
        adapters: AdapterRegistry,
        context_compiler: ContextCompiler,
        *,
        policy: SentinelPolicy | None = None,
        approval_service: ApprovalService | None = None,
    ) -> None:
        self.store = store
        self.adapters = adapters
        self.context_compiler = context_compiler
        self.policy = policy or SentinelPolicy()
        self.approval_service = approval_service
        self.scanner = SentinelScanner(blocking_severities=self.policy.blocking_severities)

    def assess_artifact(
        self,
        artifact: Artifact,
        *,
        trigger: str = "artifact_created",
    ) -> SecurityAssessment:
        if not self.policy.enabled:
            raise PolicyViolation("Sentinel is disabled")
        mode = "passive" if self.policy.passive_only else "isolated"
        assessment = self.scanner.scan_artifact(artifact, trigger=trigger, mode=mode)
        return self.store.save_sentinel_assessment(assessment)

    def _build_review_envelope(self, assessment: SecurityAssessment) -> ReviewEnvelope:
        serialized = canonical_json(assessment)
        return ReviewEnvelope(
            brief=(
                "Independently adversarially review the raw Sentinel assessment. "
                "Do not trust it because it came from a security guild. Recompute its target binding, "
                "finding support, severity, remediation safety, omissions, and regressions."
            ),
            baseline={
                "sentinel_policy_version": SENTINEL_POLICY_VERSION,
                "constitutional_rule": "new_guild_output_is_untrusted_until_independent_review",
            },
            artifact={
                "artifact_id": assessment.assessment_id,
                "task_id": assessment.task_id,
                "media_type": "application/vnd.lpos.sentinel-assessment+json",
                "content": serialized,
                "content_hash": assessment.assessment_hash,
                "created_by_adapter": assessment.producer_id,
                "trust_state": assessment.trust_state,
            },
            interpretation_contract={
                "task_id": assessment.task_id,
                "instruction_verbatim": "Continuously adversarially test Chip-created work and report remediations.",
                "interpretation": (
                    "Review this exact raw assessment without creator context; no Sentinel conclusion is authoritative "
                    "until both independent review and deterministic verification pass."
                ),
                "invariants": [
                    "No guild may approve or close its own work.",
                    "No unreviewed finding may block, authorize, publish, or be presented as fact.",
                    "Evidence remains redacted and bound to immutable hashes.",
                ],
            },
            artifact_specification={
                "artifact_id": assessment.assessment_id,
                "invariants": [
                    "Exact assessment and target hashes are preserved.",
                    "All packaged Sentinel rules are accounted for.",
                    "Remediation is non-destructive and separately authorized before execution.",
                ],
            },
            mapped_craft_standards=("CS-003", "CS-008", "CS-009"),
            verification_evidence=(
                f"assessment_hash:{assessment.assessment_hash}",
                f"artifact_hash:{assessment.artifact_hash}",
                "checked_rules:" + ",".join(assessment.checked_rules),
                "producer_trust_state:untrusted",
            ),
            intended_outcome=(
                "A fresh-context, independently reviewed, reproducible security assessment whose exact findings "
                "and remediation guidance are safe to present to the Principal."
            ),
        )

    def _structural_verification(
        self,
        assessment: SecurityAssessment,
        envelope: ReviewEnvelope,
        artifact: Artifact | None,
        *,
        reviewer_adapter: str,
        context_isolated: bool,
    ) -> tuple[dict[str, bool], tuple[str, ...]]:
        checks: dict[str, bool] = {}
        checks["raw_output_untrusted"] = assessment.trust_state == "untrusted"
        checks["policy_current"] = assessment.policy_version == SENTINEL_POLICY_VERSION
        checks["all_rules_accounted_for"] = tuple(assessment.checked_rules) == tuple(RULE_IDS)
        checks["producer_reviewer_separated"] = reviewer_adapter != assessment.producer_id
        checks["fresh_context_attested"] = context_isolated
        checks["envelope_hash_binding"] = (
            envelope.artifact.get("content_hash") == assessment.assessment_hash
            and text_digest(str(envelope.artifact.get("content", ""))) == assessment.assessment_hash
        )
        checks["target_revision_present"] = (
            artifact is not None
            and artifact.task_id == assessment.task_id
            and artifact.artifact_id == assessment.artifact_id
            and artifact.content_hash == assessment.artifact_hash
        )
        checks["evidence_redacted"] = all(
            redact_excerpt(evidence.redacted_excerpt) == evidence.redacted_excerpt
            for finding in assessment.findings
            for evidence in finding.evidence
        )

        if artifact is None:
            checks["findings_reproducible"] = False
        else:
            reproduced = self.scanner.scan_artifact(
                artifact,
                assessment_id=assessment.assessment_id,
                trigger=assessment.trigger,
                mode=assessment.mode,
            )
            checks["findings_reproducible"] = (
                reproduced.status == assessment.status
                and finding_signatures(reproduced) == finding_signatures(assessment)
            )

        failures = tuple(name for name, passed in checks.items() if not passed)
        return checks, failures

    def review_assessment(self, assessment: SecurityAssessment) -> SecurityAssessmentReview:
        existing = self.store.get_sentinel_review_for_assessment(assessment.assessment_id)
        if existing is not None:
            return existing

        envelope = self._build_review_envelope(assessment)
        context = self.context_compiler.compile_review(envelope)
        self.store.save_context_bundle(context)
        reviewer_name = "sentinel-review-unavailable"
        context_isolated = False

        try:
            reviewer = self.adapters.select_model(
                model_class="review",
                required_capabilities=("independent_review", "quality_assurance"),
                purpose="review",
                exclude_name=assessment.producer_id,
                allow_excluded_fallback=False,
            )
            reviewer_name = reviewer.name
            result = reviewer.review(envelope, context)
            isolation_token = f"fresh_context:{context.bundle_id}"
            context_isolated = isolation_token in result.isolation
            if not context_isolated:
                raise ContextIsolationError(
                    "Sentinel reviewer did not attest to the exact fresh review context"
                )
        except Exception as exc:
            # A failed review attempt is persisted as an untrusted assurance failure;
            # it never converts the guild's raw claims into findings.
            context_isolated = False
            result = ReviewResult(
                decision=ReviewDecision.REJECT,
                isolation=f"review_failed:{context.bundle_id}",
                recomputed="Independent Sentinel review could not be completed.",
                contract_violations=(f"{type(exc).__name__}: {exc}",),
                required_corrections=(
                    "Restore an independent review adapter and rerun this exact assessment hash.",
                ),
                evidence_reviewed=(f"assessment_hash:{assessment.assessment_hash}",),
            )

        artifact = (
            self.store.get_artifact_revision(assessment.task_id, assessment.artifact_hash)
            if assessment.artifact_hash is not None
            else None
        )
        checks, failures = self._structural_verification(
            assessment,
            envelope,
            artifact,
            reviewer_adapter=reviewer_name,
            context_isolated=context_isolated,
        )
        trusted = (
            result.decision is ReviewDecision.PASS
            and context_isolated
            and not failures
            and reviewer_name != assessment.producer_id
        )
        review = SecurityAssessmentReview(
            review_id=new_id("SREV"),
            assessment_id=assessment.assessment_id,
            assessment_hash=assessment.assessment_hash,
            task_id=assessment.task_id,
            artifact_hash=assessment.artifact_hash,
            envelope=envelope,
            result=result,
            structural_checks=checks,
            structural_failures=failures,
            context_isolated=context_isolated,
            producer_id=assessment.producer_id,
            reviewer_adapter=reviewer_name,
            review_context_id=context.bundle_id,
            trusted=trusted,
        )
        return self.store.save_sentinel_review(review)

    def _create_report(
        self,
        assessment: SecurityAssessment,
        review: SecurityAssessmentReview,
    ) -> PrincipalSecurityReport | None:
        existing = self.store.get_sentinel_report_for_review(review.review_id)
        if existing is not None:
            return existing

        if review.trusted and not assessment.findings:
            return None
        if review.trusted:
            report_findings = tuple(ReportFinding.from_finding(item) for item in assessment.findings)
            counts = severity_counts(assessment.findings)
            blocking = sum(1 for item in assessment.findings if item.blocking)
            summary = (
                f"Sentinel found {len(assessment.findings)} independently reviewed security issue(s) "
                f"in task {assessment.task_id}; {blocking} block completion. Each item includes remediation "
                "and verification steps. Sentinel cannot apply or close its own remediation."
            )
            overall = "attention_required"
        else:
            report_findings = ()
            counts = {severity: 0 for severity in SEVERITIES}
            reasons = list(review.structural_failures)
            reasons.extend(review.result.contract_violations)
            detail = "; ".join(reasons[:5]) or "independent review rejected the assessment"
            summary = (
                "Sentinel produced an assessment, but LPOS rejected it as untrusted. No Sentinel finding is "
                f"being presented as fact and the assessment cannot affect completion. Review detail: {detail}"
            )
            overall = "assurance_failure"

        report = PrincipalSecurityReport(
            report_id=new_id("SREPORT"),
            assessment_id=assessment.assessment_id,
            assessment_hash=assessment.assessment_hash,
            review_id=review.review_id,
            review_hash=review.review_hash,
            task_id=assessment.task_id,
            artifact_id=assessment.artifact_id,
            artifact_hash=assessment.artifact_hash,
            overall=overall,
            summary=summary,
            counts=counts,
            findings=report_findings,
        )
        return self.store.save_sentinel_report(report)

    def assess_and_review(
        self,
        artifact: Artifact,
        *,
        trigger: str = "artifact_created",
    ) -> tuple[SecurityAssessment, SecurityAssessmentReview, PrincipalSecurityReport | None]:
        assessment = self.store.get_latest_sentinel_assessment(artifact.task_id, artifact.content_hash)
        if not (
            assessment is not None
            and assessment.policy_version == SENTINEL_POLICY_VERSION
            and assessment.trigger == trigger
        ):
            assessment = self.assess_artifact(artifact, trigger=trigger)
        review = self.review_assessment(assessment)
        report = self._create_report(assessment, review)
        return assessment, review, report

    def scan_latest(
        self,
        task_id: str,
        *,
        trigger: str = "manual",
    ) -> tuple[SecurityAssessment, SecurityAssessmentReview, PrincipalSecurityReport | None]:
        artifact = self.store.get_latest_artifact(task_id)
        if artifact is None:
            raise PolicyViolation("Sentinel cannot scan a task with no artifact")
        return self.assess_and_review(artifact, trigger=trigger)

    def run_pending(self) -> tuple[dict[str, str | int | bool], ...]:
        results: list[dict[str, str | int | bool]] = []
        for artifact in self.store.list_artifacts_without_sentinel_assessment(
            policy_version=SENTINEL_POLICY_VERSION
        ):
            assessment, review, report = self.assess_and_review(
                artifact,
                trigger="standing_operation",
            )
            results.append(
                {
                    "task_id": artifact.task_id,
                    "artifact_hash": artifact.content_hash,
                    "assessment_id": assessment.assessment_id,
                    "trusted": review.trusted,
                    "findings": len(assessment.findings) if review.trusted else 0,
                    "report_id": report.report_id if report else "",
                }
            )
        return tuple(results)

    def assert_can_complete(self, task_id: str, artifact_hash: str | None) -> None:
        if not self.policy.enabled or artifact_hash is None:
            return
        assessment = self.store.get_latest_sentinel_assessment(task_id, artifact_hash)
        if assessment is None or assessment.policy_version != SENTINEL_POLICY_VERSION:
            raise PolicyViolation(
                "completion blocked: exact artifact revision lacks a current Sentinel assessment"
            )
        review = self.store.get_sentinel_review_for_assessment(assessment.assessment_id)
        if review is None or not review.trusted:
            raise PolicyViolation(
                "completion blocked: Sentinel output has not passed independent adversarial review"
            )
        blockers = tuple(item for item in assessment.findings if item.blocking)
        if blockers:
            ids = ", ".join(item.finding_id for item in blockers)
            raise PolicyViolation(
                f"completion blocked by {len(blockers)} independently reviewed Sentinel finding(s): {ids}"
            )

    def assert_active_engagement_authorized(
        self,
        scope: ActiveEngagementScope,
        *,
        plan: ActionPlan | None,
        grant: ApprovalGrant | None,
        checked_at: str | None = None,
    ) -> str:
        """Fail closed unless an active test is bound to exact ordinary approval.

        This method is only an authorization gate; Sentinel ships no live exploit
        runner.  A separately isolated executor must call it immediately before each
        active engagement and retain the returned scope hash in its evidence.
        """

        if self.policy.passive_only:
            raise PolicyViolation(
                "active penetration testing is disabled; use passive Sentinel monitoring "
                "or a separately configured isolated engagement"
            )
        if not isinstance(scope, ActiveEngagementScope):
            raise ValidationError("active engagement requires a typed scope")
        if not isinstance(plan, ActionPlan):
            raise PolicyViolation(
                "active penetration testing requires a separate exact-action plan and verified Principal approval"
            )
        if self.approval_service is None:
            raise PolicyViolation(
                "active penetration testing requires the ordinary persisted LPOS approval service"
            )

        try:
            action_state = self.store.get_action(plan.action_id)
        except NotFoundError as exc:
            raise PolicyViolation(
                "active engagement action is not present in the ordinary LPOS action ledger"
            ) from exc
        stored_plan = action_state["plan"]
        if stored_plan.to_dict() != plan.to_dict():
            raise PolicyViolation("active engagement plan does not match the persisted exact action")
        if action_state["status"] is not ActionStatus.APPROVED:
            raise PolicyViolation("active engagement action is not in the approved state")

        observed_at = checked_at or utc_now()
        persisted_grant = self.approval_service.validate(stored_plan, now=observed_at)
        if persisted_grant is None:
            raise PolicyViolation("active engagement lacks a persisted approval grant")
        if grant is not None and (
            not isinstance(grant, ApprovalGrant)
            or grant.to_dict() != persisted_grant.to_dict()
        ):
            raise PolicyViolation("supplied active engagement grant differs from the persisted grant")
        grant = persisted_grant
        plan = stored_plan

        if plan.kind != "sentinel_active_penetration_test":
            raise PolicyViolation("active engagement approval is for a different action kind")
        if plan.task_id != scope.task_id or grant.task_id != scope.task_id:
            raise PolicyViolation("active engagement approval does not bind the scoped task")
        if not plan.external or plan.reversible or not plan.approval_required:
            raise PolicyViolation("active penetration testing must be external, irreversible, and approval-bound")
        parameters = dict(plan.parameters)
        if (
            parameters.get("engagement_id") != scope.engagement_id
            or parameters.get("engagement_scope_hash") != scope.scope_hash
            or parameters.get("isolated_environment") != scope.isolated_environment
        ):
            raise PolicyViolation("active engagement action does not bind the exact isolated scope")
        if (
            grant.action_id != plan.action_id
            or grant.action_hash != plan.action_hash
            or grant.granted_action != plan.exact_action
        ):
            raise PolicyViolation("active engagement grant does not bind the exact action")
        if grant.verified_identity.casefold() in {
            SENTINEL_ORGANIZATION_ID.casefold(),
            SENTINEL_SPECIALIST_ID.casefold(),
            SENTINEL_PRODUCER_ID.casefold(),
        }:
            raise PolicyViolation("Sentinel may not approve its own active engagement")
        now = parse_timestamp(observed_at)
        if not (parse_timestamp(scope.window_start) <= now <= parse_timestamp(scope.window_end)):
            raise PolicyViolation("active engagement is outside its approved time window")
        return scope.scope_hash

    def acknowledge_report(
        self,
        report_id: str,
        *,
        acknowledged_by: str,
        note: str,
    ) -> ReportAcknowledgement:
        acknowledgement = ReportAcknowledgement(
            acknowledgement_id=new_id("SACK"),
            report_id=report_id,
            acknowledged_by=acknowledged_by,
            note=note,
        )
        return self.store.acknowledge_sentinel_report(acknowledgement)
