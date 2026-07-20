"""Integrated LPOS v4 operating-system runtime."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from .actions import ActionService
from .adapters.base import AdapterRegistry
from .adapters.deterministic import (
    DeterministicModelAdapter,
    RecordingActionAdapter,
    SandboxedFileActionAdapter,
)
from .approvals import ApprovalService, IdentityVerifier
from .canonical import digest, new_id, utc_now
from .context import ContextCompiler, SpecRepository
from .errors import AdapterError, PolicyViolation
from .materiality import MaterialityPolicy
from .models import (
    ActionPlan,
    ActionResult,
    ApprovalGrant,
    ApprovalRequest,
    Artifact,
    ArtifactSpecification,
    CompletionReport,
    ConflictRecord,
    DecisionRecord,
    DecisionStatus,
    EvidenceRecord,
    EvidenceStatus,
    InterpretationContract,
    MaterialitySignals,
    MessageIdentity,
    ReviewDecision,
    ReviewResult,
    TaskEnvelope,
    TaskStatus,
)
from .policy import PolicyEngine
from .review import ReviewService
from .routing import CapabilityRegistry, CapabilityRouter
from .store import SQLiteStore


@dataclass(frozen=True, slots=True)
class RuntimeConfig:
    database_path: Path
    spec_root: Path | None = None
    verified_identities: Mapping[str, tuple[str, ...]] = field(default_factory=dict)
    max_context_chars: int = 160_000

    def __post_init__(self) -> None:
        object.__setattr__(self, "database_path", Path(self.database_path))
        if self.spec_root is not None:
            object.__setattr__(self, "spec_root", Path(self.spec_root))


class LPOSRuntime:
    """Deterministic control plane implementing the LPOS v4 specification."""

    def __init__(
        self,
        config: RuntimeConfig,
        *,
        adapters: AdapterRegistry,
        capability_registry: CapabilityRegistry | None = None,
    ) -> None:
        self.config = config
        self.store = SQLiteStore(config.database_path)
        self.adapters = adapters
        self.router = CapabilityRouter(capability_registry or CapabilityRegistry.default())
        self.spec_repository = (
            SpecRepository(config.spec_root) if config.spec_root is not None else SpecRepository.packaged()
        )
        self.context_compiler = ContextCompiler(
            self.spec_repository, max_chars=config.max_context_chars
        )
        self.identity_verifier = IdentityVerifier(config.verified_identities)
        self.approvals = ApprovalService(self.store, self.identity_verifier)
        self.actions = ActionService(self.store, self.adapters, self.approvals)
        self.reviews = ReviewService(self.store, self.adapters, self.context_compiler)
        self.policy = PolicyEngine(self.store)

    @classmethod
    def local(
        cls,
        config: RuntimeConfig,
        *,
        file_action_root: str | Path | None = None,
    ) -> "LPOSRuntime":
        """Create the safe local LPOS runtime with deterministic model and action adapters."""

        creator = DeterministicModelAdapter("local-creator", priority=10)
        reviewer = DeterministicModelAdapter(
            "local-reviewer",
            priority=5,
            supports_creation=False,
        )
        action_adapters = [RecordingActionAdapter()]
        if file_action_root is not None:
            action_adapters.append(SandboxedFileActionAdapter(file_action_root))
        return cls(
            config,
            adapters=AdapterRegistry(
                model_adapters=(creator, reviewer),
                action_adapters=action_adapters,
            ),
        )

    def submit_task(
        self,
        principal_instruction: str,
        *,
        required_capabilities: Iterable[str] = (),
        materiality_signals: MaterialitySignals | None = None,
        constraints: Mapping[str, Any] | None = None,
        preferred_model_class: str | None = None,
        deadline: str | None = None,
    ) -> TaskEnvelope:
        route = self.router.route(
            required_capabilities,
            preferred_model_class=preferred_model_class,
        )
        decision = MaterialityPolicy.evaluate(materiality_signals or MaterialitySignals())
        merged_constraints = dict(constraints or {})
        if route.missing_capabilities:
            merged_constraints["route_missing_capabilities"] = list(route.missing_capabilities)
        require_local = merged_constraints.get("privacy") == "local_only"
        creator = self.adapters.select_model(
            model_class=route.model_class,
            required_capabilities=route.required_capabilities,
            purpose="creation",
            require_local=require_local,
        )
        envelope = TaskEnvelope(
            task_id=new_id("TASK"),
            principal_instruction=principal_instruction,
            lead_guild=route.lead_guild,
            lead_specialist=route.lead_specialist,
            supporting_specialists=route.supporting_specialists,
            craft_standards=route.craft_standards,
            required_capabilities=route.required_capabilities,
            constraints=merged_constraints,
            material=decision.material,
            materiality_basis=decision.basis,
            model_class=route.model_class,
            deadline=deadline,
            creator_adapter=creator.name,
        )
        self.store.create_task(envelope)
        return envelope

    def record_interpretation(
        self,
        task_id: str,
        *,
        instruction_verbatim: str,
        interpretation: str,
        invariants: Sequence[str],
        conflicts: Sequence[ConflictRecord | Mapping[str, Any]] = (),
        verification_plan: Sequence[str],
        spec_ref: str | None,
    ) -> InterpretationContract:
        state = self.store.get_task(task_id)
        task: TaskEnvelope = state["envelope"]
        if state["status"] not in {
            TaskStatus.RECEIVED,
            TaskStatus.AWAITING_CLARIFICATION,
            TaskStatus.INTERPRETED,
            TaskStatus.CORRECTION_REQUIRED,
        }:
            raise PolicyViolation(
                f"InterpretationContract cannot change while task is {state['status'].value}"
            )
        if instruction_verbatim != task.principal_instruction:
            raise PolicyViolation(
                "InterpretationContract.instruction_verbatim must exactly match the Principal instruction"
            )
        converted = tuple(
            item if isinstance(item, ConflictRecord) else ConflictRecord.from_dict(item)
            for item in conflicts
        )
        contract = InterpretationContract(
            task_id=task_id,
            instruction_verbatim=instruction_verbatim,
            interpretation=interpretation,
            invariants=tuple(invariants),
            conflicts=converted,
            verification_plan=tuple(verification_plan),
            spec_ref=spec_ref,
        )
        self.store.save_interpretation(contract)
        if state["status"] in {TaskStatus.RECEIVED, TaskStatus.AWAITING_CLARIFICATION}:
            self.store.transition_task(
                task_id,
                TaskStatus.INTERPRETED,
                expected_version=state["version"],
                reason="InterpretationContract recorded",
            )
        return contract

    def record_artifact_spec(
        self,
        task_id: str,
        *,
        artifact_id: str | None = None,
        structural_decisions: Mapping[str, Any] | None = None,
        design_tokens: Mapping[str, Any] | None = None,
        invariants: Sequence[str] = (),
        approved_by: str | None = None,
        history: Sequence[str] = (),
    ) -> ArtifactSpecification:
        state = self.store.get_task(task_id)
        if state["status"] not in {
            TaskStatus.RECEIVED,
            TaskStatus.INTERPRETED,
            TaskStatus.PLANNED,
            TaskStatus.EXECUTING,
            TaskStatus.CORRECTION_REQUIRED,
        }:
            raise PolicyViolation(
                f"ArtifactSpecification cannot change while task is {state['status'].value}"
            )
        spec = ArtifactSpecification(
            artifact_id=artifact_id or new_id("ART"),
            structural_decisions=dict(structural_decisions or {}),
            design_tokens=dict(design_tokens or {}),
            invariants=tuple(invariants),
            approved_by=approved_by,
            history=tuple(history),
        )
        self.store.save_artifact_spec(task_id, spec)
        return spec

    def create_artifact(
        self,
        task_id: str,
        *,
        artifact_specification: ArtifactSpecification | None = None,
        baseline_ref: str | None = None,
        additional_components: Iterable[str] = (),
    ) -> Artifact:
        state = self.store.get_task(task_id)
        task: TaskEnvelope = state["envelope"]
        if artifact_specification is not None:
            self.store.save_artifact_spec(task_id, artifact_specification)
        spec = artifact_specification or self.store.get_latest_artifact_spec_for_task(task_id)
        if task.material and spec is None:
            raise PolicyViolation(
                "material work requires an ArtifactSpecification seeded before creation"
            )
        self.policy.assert_ready_to_execute(task)
        self._ensure_executing(task_id)
        interpretation = self.store.get_interpretation(task_id)
        context = self.context_compiler.compile_task(
            task=task,
            interpretation=interpretation,
            artifact_specification=spec,
            additional_components=additional_components,
        )
        self.store.save_context_bundle(context)
        adapter = self._select_creator(task)
        try:
            output = adapter.create_artifact(task, context)
        except AdapterError as primary_error:
            # Provider/model failures are not allowed to mutate task policy.
            # Re-evaluate the same capability, model-class, and locality
            # constraints once, excluding the failed adapter, and record the
            # substitution in the decision ledger.
            require_local = task.constraints.get("privacy") == "local_only"
            fallback = self.adapters.select_model(
                model_class=task.model_class,
                required_capabilities=task.required_capabilities,
                purpose="creation",
                exclude_names=(adapter.name,),
                require_local=require_local,
                allow_excluded_fallback=False,
            )
            self.record_decision(
                task.task_id,
                context=f"Creator adapter {adapter.name} failed during artifact creation.",
                decision=f"Retry creation once with fallback adapter {fallback.name}.",
                rationale=f"{type(primary_error).__name__}: {primary_error}",
                alternatives=("Suspend the task", "Retry the same provider outside this run"),
                consequences="The fallback receives the identical persisted creation context.",
                risks="Output characteristics may differ; material work still requires isolated review.",
                implementation_notes=(
                    "The failed adapter was excluded and all capability, model-class, and locality "
                    "constraints were re-evaluated before retry."
                ),
                owner="LPOS Engine",
            )
            adapter = fallback
            output = adapter.create_artifact(task, context)
        artifact = Artifact.create(
            artifact_id=spec.artifact_id if spec else new_id("ART"),
            task_id=task_id,
            media_type=output.media_type,
            content=output.content,
            baseline_ref=baseline_ref,
            context_bundle_id=context.bundle_id,
            context_bundle_hash=context.bundle_hash,
            interpretation_hash=digest(interpretation) if interpretation else None,
            artifact_spec_hash=digest(spec) if spec else None,
            verification_evidence=output.evidence,
            created_by_adapter=adapter.name,
        )
        self.store.save_artifact(artifact)
        return artifact

    def review_latest_artifact(
        self,
        task_id: str,
        *,
        intended_outcome: str,
        baseline: Mapping[str, Any] | None = None,
        auto_complete: bool = True,
        completion_summary: str | None = None,
    ) -> ReviewResult:
        state = self.store.get_task(task_id)
        task: TaskEnvelope = state["envelope"]
        artifact = self.store.get_latest_artifact(task_id)
        if artifact is None:
            raise PolicyViolation("cannot review a task with no artifact")
        interpretation = self.store.get_interpretation(task_id)
        if interpretation is None:
            raise PolicyViolation("review requires the InterpretationContract")
        spec = self.store.get_artifact_spec(artifact.artifact_id)
        if spec is None:
            raise PolicyViolation("review requires the ArtifactSpecification")
        if artifact.interpretation_hash and digest(interpretation) != artifact.interpretation_hash:
            raise PolicyViolation(
                "InterpretationContract changed after artifact creation; recreate the artifact before review"
            )
        if artifact.artifact_spec_hash and digest(spec) != artifact.artifact_spec_hash:
            raise PolicyViolation(
                "ArtifactSpecification changed after artifact creation; recreate the artifact before review"
            )
        if state["status"] is TaskStatus.EXECUTING:
            self.store.transition_task(
                task_id,
                TaskStatus.REVIEWING,
                expected_version=state["version"],
                reason="fresh independent review started",
            )
        elif state["status"] is not TaskStatus.REVIEWING:
            raise PolicyViolation(
                f"task must be executing or reviewing, not {state['status'].value}"
            )
        envelope = self.reviews.build_envelope(
            task=task,
            artifact=artifact,
            interpretation=interpretation,
            artifact_specification=spec,
            baseline=baseline or ({"ref": artifact.baseline_ref} if artifact.baseline_ref else None),
            verification_evidence=artifact.verification_evidence,
            intended_outcome=intended_outcome,
        )
        result = self.reviews.run(
            task=task,
            artifact=artifact,
            envelope=envelope,
            creator_adapter=artifact.created_by_adapter,
            creator_context_id=artifact.context_bundle_id,
        )
        current = self.store.get_task(task_id)
        if result.decision is ReviewDecision.REJECT:
            self.store.transition_task(
                task_id,
                TaskStatus.CORRECTION_REQUIRED,
                expected_version=current["version"],
                reason="independent review rejected artifact",
            )
        elif auto_complete:
            self.complete_task(
                task_id,
                result_summary=completion_summary or intended_outcome,
            )
        return result

    def complete_task(self, task_id: str, *, result_summary: str) -> CompletionReport:
        state = self.store.get_task(task_id)
        if state["status"] not in {TaskStatus.EXECUTING, TaskStatus.REVIEWING}:
            raise PolicyViolation(
                f"task cannot complete while it is {state['status'].value}"
            )
        task: TaskEnvelope = state["envelope"]
        artifact = self.store.get_latest_artifact(task_id)
        artifact_hash = artifact.content_hash if artifact else None
        self.policy.assert_can_complete(task, artifact_hash)

        completion_evidence = EvidenceRecord(
            id=new_id("EVID"),
            recommendation="Accept the completed LPOS task result.",
            owner=task.lead_specialist,
            expected_outcome=result_summary,
            baseline="Task received and interpreted under the recorded contract.",
            target="All deterministic completion policies pass.",
            observed=f"Task {task_id} passed completion policy checks.",
            confidence=1.0,
            measurement="State, review, action, and artifact-hash checks",
            fallback_used=(artifact.created_by_adapter != task.creator_adapter) if artifact else False,
            review_date=None,
            status=EvidenceStatus.VALIDATED,
        )
        evidence = self.store.list_evidence(task_id)
        decisions = self.store.list_decisions(task_id)
        actions = self.store.list_actions(task_id)
        review = self.store.get_latest_review(task_id, artifact_hash) if artifact_hash else None
        limitations: list[str] = []
        if review and review["creator_adapter"] == review["reviewer_adapter"]:
            limitations.append(
                "Review used the same model adapter as creation; context isolation was still enforced."
            )
        report = CompletionReport(
            task_id=task_id,
            status=TaskStatus.COMPLETED,
            result_summary=result_summary,
            artifact_id=artifact.artifact_id if artifact else None,
            artifact_hash=artifact_hash,
            material=task.material,
            review_decision=review["result"].decision if review else None,
            review_isolated=review["context_isolated"] if review else None,
            actions=tuple(
                {
                    "action_id": item["plan"].action_id,
                    "action_hash": item["plan"].action_hash,
                    "status": item["status"].value,
                }
                for item in actions
            ),
            evidence_ids=tuple(item.id for item in evidence) + (completion_evidence.id,),
            decision_ids=tuple(item.id for item in decisions),
            limitations=tuple(limitations),
        )
        self.store.finalize_task(
            report,
            expected_version=state["version"],
            completion_evidence=completion_evidence,
        )
        return report

    def plan_action(
        self,
        task_id: str,
        *,
        kind: str,
        parameters: Mapping[str, Any],
        external: bool,
        reversible: bool,
        idempotency_key: str,
        approval_required: bool | None = None,
        risk_tags: Sequence[str] = (),
        expires_at: str | None = None,
    ) -> tuple[ActionPlan, ApprovalRequest | None]:
        state_before = self.store.get_task(task_id)
        existing = self.store.get_action_by_idempotency_key(idempotency_key)
        retry_while_waiting = state_before["status"] is TaskStatus.AWAITING_APPROVAL
        if retry_while_waiting:
            if existing is None or existing["plan"].task_id != task_id:
                raise PolicyViolation(
                    "task is awaiting approval for another exact action; resolve it before planning more work"
                )
        else:
            self._ensure_executing(task_id)
        plan, request = self.actions.plan(
            task_id=task_id,
            kind=kind,
            parameters=parameters,
            external=external,
            reversible=reversible,
            idempotency_key=idempotency_key,
            approval_required=approval_required,
            risk_tags=risk_tags,
            expires_at=expires_at,
        )
        if request is not None:
            state = self.store.get_task(task_id)
            if state["status"] is TaskStatus.EXECUTING:
                self.store.transition_task(
                    task_id,
                    TaskStatus.AWAITING_APPROVAL,
                    expected_version=state["version"],
                    reason=f"exact action {plan.action_id} awaits Principal approval",
                )
            elif not (
                retry_while_waiting
                and state["status"] is TaskStatus.AWAITING_APPROVAL
                and existing is not None
                and existing["plan"].action_id == plan.action_id
            ):
                raise PolicyViolation(
                    f"cannot attach approval request while task is {state['status'].value}"
                )
        return plan, request

    def grant_action_approval(
        self,
        question_id: str,
        *,
        message_identity: MessageIdentity,
        verified_identity: str,
        granted_action: str | None = None,
        granted_at: str | None = None,
    ) -> ApprovalGrant:
        request = self.store.get_approval_request(question_id)
        return self.approvals.grant(
            request=request,
            message_identity=message_identity,
            verified_identity=verified_identity,
            granted_action=granted_action,
            granted_at=granted_at,
        )

    def apply_action(self, action_id: str) -> ActionResult:
        action = self.store.get_action(action_id)
        task_id = action["plan"].task_id
        try:
            result = self.actions.apply(action_id)
        except Exception:
            state = self.store.get_task(task_id)
            if state["status"] not in {
                TaskStatus.COMPLETED,
                TaskStatus.FAILED,
                TaskStatus.CANCELLED,
            }:
                self.store.transition_task(
                    task_id,
                    TaskStatus.FAILED,
                    expected_version=state["version"],
                    reason=f"action {action_id} failed",
                )
            raise
        state = self.store.get_task(task_id)
        if state["status"] is TaskStatus.AWAITING_APPROVAL:
            self.store.transition_task(
                task_id,
                TaskStatus.EXECUTING,
                expected_version=state["version"],
                reason=f"approved action {action_id} applied",
            )
        return result

    def record_decision(
        self,
        task_id: str,
        *,
        context: str,
        decision: str,
        rationale: str,
        alternatives: Sequence[str],
        consequences: str,
        risks: str,
        implementation_notes: str,
        references: Sequence[str] = (),
        owner: str = "Principal",
    ) -> DecisionRecord:
        self.store.get_task(task_id)
        record = DecisionRecord(
            id=new_id("DEC"),
            date=utc_now(),
            context=context,
            decision=decision,
            rationale=rationale,
            alternatives=tuple(alternatives),
            consequences=consequences,
            risks=risks,
            implementation_notes=implementation_notes,
            references=tuple(references),
            status=DecisionStatus.ACCEPTED,
            superseded_by=None,
            owner=owner,
        )
        self.store.save_decision(record, task_id=task_id)
        return record

    def _ensure_executing(self, task_id: str) -> None:
        state = self.store.get_task(task_id)
        task: TaskEnvelope = state["envelope"]
        self.policy.assert_ready_to_execute(task)
        status = state["status"]
        version = state["version"]
        if status is TaskStatus.RECEIVED:
            version = self.store.transition_task(
                task_id,
                TaskStatus.PLANNED,
                expected_version=version,
                reason="routine task planned",
            )
            status = TaskStatus.PLANNED
        elif status is TaskStatus.INTERPRETED:
            version = self.store.transition_task(
                task_id,
                TaskStatus.PLANNED,
                expected_version=version,
                reason="interpreted task planned",
            )
            status = TaskStatus.PLANNED
        if status is TaskStatus.PLANNED:
            self.store.transition_task(
                task_id,
                TaskStatus.EXECUTING,
                expected_version=version,
                reason="execution started",
            )
        elif status is TaskStatus.CORRECTION_REQUIRED:
            self.store.transition_task(
                task_id,
                TaskStatus.EXECUTING,
                expected_version=version,
                reason="correction cycle started",
            )
        elif status is not TaskStatus.EXECUTING:
            raise PolicyViolation(f"task cannot enter execution from {status.value}")

    def _select_creator(self, task: TaskEnvelope):
        require_local = task.constraints.get("privacy") == "local_only"
        if task.creator_adapter:
            try:
                adapter = self.adapters.get_model(task.creator_adapter)
                if require_local and not adapter.local:
                    raise AdapterError("configured creator is not local")
                if task.model_class not in adapter.model_classes or not adapter.supports_creation:
                    raise AdapterError("configured creator no longer supports the task model class")
                missing = set(task.required_capabilities) - set(adapter.capabilities)
                if missing:
                    raise AdapterError(
                        "configured creator no longer covers: " + ", ".join(sorted(missing))
                    )
                return adapter
            except AdapterError:
                pass
        fallback = self.adapters.select_model(
            model_class=task.model_class,
            required_capabilities=task.required_capabilities,
            purpose="creation",
            require_local=require_local,
        )
        if task.creator_adapter and fallback.name != task.creator_adapter:
            self.record_decision(
                task.task_id,
                context="Model adapter availability changed during execution.",
                decision=f"Use fallback adapter {fallback.name} instead of {task.creator_adapter}.",
                rationale="The configured creator adapter was unavailable or violated locality constraints.",
                alternatives=("Suspend the task",),
                consequences="Fallback use is visible in the decision and completion evidence.",
                risks="Output characteristics may differ; material work still requires review.",
                implementation_notes="Capability and model-class requirements were re-evaluated.",
                owner="LPOS Engine",
            )
        return fallback
