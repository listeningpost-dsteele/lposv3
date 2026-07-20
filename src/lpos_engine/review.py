"""Independent review orchestration with a canonical isolated envelope."""

from __future__ import annotations

from typing import Mapping, Sequence

from .adapters.base import AdapterRegistry
from .canonical import new_id
from .context import ContextCompiler
from .errors import ContextIsolationError
from .models import (
    Artifact,
    ArtifactSpecification,
    InterpretationContract,
    ReviewEnvelope,
    ReviewResult,
    TaskEnvelope,
)
from .store import SQLiteStore


class ReviewService:
    def __init__(
        self,
        store: SQLiteStore,
        adapters: AdapterRegistry,
        context_compiler: ContextCompiler,
    ) -> None:
        self.store = store
        self.adapters = adapters
        self.context_compiler = context_compiler

    @staticmethod
    def build_envelope(
        *,
        task: TaskEnvelope,
        artifact: Artifact,
        interpretation: InterpretationContract,
        artifact_specification: ArtifactSpecification,
        baseline: Mapping | None,
        verification_evidence: Sequence[str],
        intended_outcome: str,
    ) -> ReviewEnvelope:
        return ReviewEnvelope(
            brief=task.principal_instruction,
            baseline=dict(baseline) if baseline is not None else None,
            artifact=artifact.to_dict(),
            interpretation_contract=interpretation.to_dict(),
            artifact_specification=artifact_specification.to_dict(),
            mapped_craft_standards=task.craft_standards,
            verification_evidence=tuple(verification_evidence),
            intended_outcome=intended_outcome,
        )

    def run(
        self,
        *,
        task: TaskEnvelope,
        artifact: Artifact,
        envelope: ReviewEnvelope,
        creator_adapter: str | None,
        creator_context_id: str | None,
    ) -> ReviewResult:
        context = self.context_compiler.compile_review(envelope)
        self.store.save_context_bundle(context)
        if creator_context_id and creator_context_id == context.bundle_id:
            raise ContextIsolationError("review context reused the creator context id")
        reviewer = self.adapters.select_model(
            model_class="review",
            required_capabilities=("independent_review", "quality_assurance"),
            purpose="review",
            exclude_name=creator_adapter,
        )
        result = reviewer.review(envelope, context)
        isolation_token = f"fresh_context:{context.bundle_id}"
        if isolation_token not in result.isolation:
            raise ContextIsolationError(
                "review adapter did not attest to the exact fresh context bundle"
            )
        self.store.save_review(
            review_id=new_id("REV"),
            task_id=task.task_id,
            artifact=artifact,
            envelope=envelope,
            result=result,
            context_isolated=True,
            creator_adapter=creator_adapter,
            reviewer_adapter=reviewer.name,
            review_context_id=context.bundle_id,
        )
        return result
