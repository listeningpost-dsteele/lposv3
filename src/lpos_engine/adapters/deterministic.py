"""Safe deterministic adapters used by tests and local demonstrations."""

from __future__ import annotations

import os
import tempfile
import threading
from pathlib import Path
from typing import Callable

from ..canonical import text_digest, utc_now
from ..errors import ActionExecutionError, ValidationError
from ..models import (
    ActionPlan,
    ActionResult,
    ContextBundle,
    ModelOutput,
    ReviewDecision,
    ReviewEnvelope,
    ReviewResult,
    TaskEnvelope,
)


class DeterministicModelAdapter:
    """Predictable creator/reviewer; never presented as a production model."""

    def __init__(
        self,
        name: str,
        *,
        model_classes: frozenset[str] = frozenset({"executive", "routine", "review", "local"}),
        capabilities: frozenset[str] = frozenset(
            {
                "attack_surface_analysis",
                "automation",
                "baseline_preservation",
                "blocker_resolution",
                "brief_writing",
                "budgeting",
                "clarity_improvement",
                "code_generation",
                "code_review",
                "communication_context",
                "competitive_intelligence",
                "competitor_research",
                "confidence_assessment",
                "contract_analysis",
                "corrective_action",
                "customer_communication",
                "cost_analysis",
                "customer_insights",
                "customer_research",
                "data_analysis",
                "data_modeling",
                "data_quality",
                "debugging",
                "decision_analysis",
                "decision_communication",
                "decision_support",
                "demand_analysis",
                "dependency_management",
                "dependency_tracking",
                "developer_communication",
                "documentation",
                "editing",
                "evidence_management",
                "evidence_synthesis",
                "execution_planning",
                "executive_communication",
                "executive_coordination",
                "fact_checking",
                "failure_injection",
                "financial_analysis",
                "follow_up_planning",
                "forecasting",
                "incident_diagnosis",
                "incident_response",
                "independent_review",
                "independence_analysis",
                "initiative_management",
                "innovation_research",
                "integration",
                "integration_architecture",
                "interaction_design",
                "least_privilege",
                "legal_analysis",
                "legal_risk",
                "literature_review",
                "market_positioning",
                "market_research",
                "meaning_preservation",
                "measurement",
                "metrics",
                "mitigation_planning",
                "needs_analysis",
                "objectives",
                "observability",
                "operational_coordination",
                "operations",
                "outcome_definition",
                "outcome_evaluation",
                "packaging",
                "planning",
                "policy_audit",
                "policy_interpretation",
                "portfolio_tracking",
                "pricing",
                "prioritization",
                "privacy_engineering",
                "process_improvement",
                "product_design",
                "product_management",
                "product_strategy",
                "quality_assurance",
                "recency_analysis",
                "recommendations",
                "regression_detection",
                "relationship_analysis",
                "reliability_engineering",
                "requirements",
                "research",
                "revenue_analysis",
                "risk_analysis",
                "risk_triage",
                "roi_analysis",
                "root_cause_analysis",
                "scenario_analysis",
                "scenario_planning",
                "scheduling",
                "security_architecture",
                "security_review",
                "segmentation",
                "software_architecture",
                "software_implementation",
                "source_evaluation",
                "source_validation",
                "stakeholder_analysis",
                "state_tracking",
                "strategic_planning",
                "strategy",
                "system_design",
                "technical_writing",
                "technology_research",
                "technology_scouting",
                "test_design",
                "testing",
                "threat_mitigation",
                "threat_modeling",
                "tradeoff_analysis",
                "trend_analysis",
                "unit_economics",
                "visual_design",
                "weak_signal_detection",
                "web_design",
                "workflow_coordination",
                "workflow_design",
                "writing",
                "writing_review",
            }
        ),
        artifact_factory: Callable[[TaskEnvelope, ContextBundle], str] | None = None,
        reject_markers: tuple[str, ...] = ("[[REJECT]]",),
        local: bool = True,
        priority: int = 100,
        supports_creation: bool = True,
        supports_review: bool = True,
        available: bool = True,
    ) -> None:
        self.name = name
        self.model_classes = model_classes
        self.capabilities = capabilities
        self.artifact_factory = artifact_factory
        self.reject_markers = reject_markers
        self.local = local
        self.priority = priority
        self.supports_creation = supports_creation
        self.supports_review = supports_review
        self.available = available
        self.last_creation_context: ContextBundle | None = None
        self.last_review_context: ContextBundle | None = None

    def create_artifact(self, task: TaskEnvelope, context: ContextBundle) -> ModelOutput:
        self.last_creation_context = context
        content = (
            self.artifact_factory(task, context)
            if self.artifact_factory
            else (
                f"# LPOS Artifact\n\n"
                f"Task: {task.task_id}\n\n"
                f"Instruction: {task.principal_instruction}\n\n"
                f"Generated under context bundle `{context.bundle_id}`."
            )
        )
        return ModelOutput(
            content=content,
            evidence=(f"context:{context.bundle_hash}",),
            adapter_metadata={"adapter": self.name, "deterministic": True},
        )

    def review(self, envelope: ReviewEnvelope, context: ContextBundle) -> ReviewResult:
        self.last_review_context = context
        artifact_content = str(envelope.artifact.get("content", ""))
        found = tuple(marker for marker in self.reject_markers if marker in artifact_content)
        if found:
            return ReviewResult(
                decision=ReviewDecision.REJECT,
                isolation=f"fresh_context:{context.bundle_id}",
                recomputed="contract, artifact hash, and deterministic rejection markers",
                contract_violations=("Artifact contains a configured rejection marker.",),
                required_corrections=tuple(f"Remove or resolve marker {marker}" for marker in found),
                evidence_reviewed=envelope.verification_evidence,
            )
        return ReviewResult(
            decision=ReviewDecision.PASS,
            isolation=f"fresh_context:{context.bundle_id}",
            recomputed="contract alignment, artifact hash, and supplied verification evidence",
            truth=("No deterministic truth failure detected.",),
            reasoning=("Artifact is consistent with the supplied review envelope.",),
            craft=("No deterministic craft regression detected.",),
            outcome=("Artifact is fit for the stated intended outcome in this isolated deterministic review.",),
            strengths_to_preserve=("Preserve the reviewed artifact hash.",),
            evidence_reviewed=envelope.verification_evidence,
        )


class RecordingActionAdapter:
    """Records exact actions without causing an external side effect."""

    def __init__(self, name: str = "recording-actions", kinds: frozenset[str] | None = None) -> None:
        self.name = name
        self.kinds = kinds or frozenset({"external_send", "deploy", "purchase", "delete"})
        self.applied: list[ActionPlan] = []
        self._lock = threading.Lock()

    def apply(self, plan: ActionPlan) -> ActionResult:
        with self._lock:
            self.applied.append(plan)
        return ActionResult(
            action_id=plan.action_id,
            success=True,
            output={"recorded": True, "action_hash": plan.action_hash},
            adapter=self.name,
        )


class SandboxedFileActionAdapter:
    """Atomic local file writes confined to one configured root."""

    name = "sandboxed-files"
    kinds = frozenset({"filesystem_write"})

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _resolve(self, relative: str) -> Path:
        supplied = Path(relative)
        if supplied.is_absolute():
            raise ActionExecutionError("file action requires a relative path")
        candidate = (self.root / supplied).resolve()
        try:
            candidate.relative_to(self.root)
        except ValueError as exc:
            raise ActionExecutionError("file action attempted path traversal") from exc
        return candidate

    def apply(self, plan: ActionPlan) -> ActionResult:
        relative = plan.parameters.get("path")
        content = plan.parameters.get("content")
        if not isinstance(relative, str) or not isinstance(content, str):
            raise ValidationError("filesystem_write requires string path and content")
        target = self._resolve(relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        expected = plan.parameters.get("expected_sha256")
        allow_overwrite = plan.parameters.get("allow_overwrite", False)
        if not isinstance(allow_overwrite, bool):
            raise ValidationError("filesystem_write allow_overwrite must be boolean")
        if expected is not None and (
            not isinstance(expected, str)
            or len(expected) != 64
            or any(char not in "0123456789abcdef" for char in expected)
        ):
            raise ValidationError("filesystem_write expected_sha256 must be a lowercase SHA-256 digest")
        if target.exists():
            observed = text_digest(target.read_bytes())
            if expected is not None and observed != expected:
                raise ActionExecutionError(
                    f"baseline checksum mismatch for {relative}: expected {expected}, observed {observed}"
                )
            if expected is None and not allow_overwrite:
                raise ActionExecutionError(
                    f"refusing to overwrite {relative} without expected_sha256 or allow_overwrite=true"
                )
        elif expected is not None:
            raise ActionExecutionError(
                f"baseline checksum was supplied but {relative} does not exist"
            )

        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{target.name}.", suffix=".tmp", dir=target.parent
        )
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_name, target)
            try:
                directory_fd = os.open(target.parent, os.O_RDONLY)
            except OSError:
                directory_fd = None
            if directory_fd is not None:
                try:
                    os.fsync(directory_fd)
                finally:
                    os.close(directory_fd)
        finally:
            try:
                os.unlink(temporary_name)
            except FileNotFoundError:
                pass
        return ActionResult(
            action_id=plan.action_id,
            success=True,
            output={
                "path": str(target),
                "sha256": text_digest(content),
                "bytes": len(content.encode("utf-8")),
                "executed_at": utc_now(),
            },
            adapter=self.name,
        )
