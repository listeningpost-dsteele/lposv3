"""Specialist-led managed execution through a tool-capable Hermes CLI child."""

from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Mapping, Sequence

from .canonical import canonical_json, digest, new_id, normalize_token, require_id, require_text, text_digest, utc_now
from .context import ContextCompiler, SpecRepository
from .errors import ValidationError
from .models import ArtifactSpecification, InterpretationContract, TaskEnvelope
from .routing import CapabilityRegistry, SpecialistProfile
from .store import secure_mkdir


class RiskTier(str, Enum):
    READ_ONLY = "read-only"
    LOCAL_IMPLEMENTATION = "local-implementation"
    CONSEQUENTIAL = "consequential"


class ManagedStatus(str, Enum):
    PREFLIGHT = "preflight"
    EXECUTING = "executing"
    REVIEWING = "reviewing"
    CORRECTING = "correcting"
    COMPLETED = "completed"
    CAPABILITY_GAP = "capability_gap"
    FAILED = "failed"


_ALLOWED_TOOLSETS = {
    RiskTier.READ_ONLY: frozenset({"file", "web", "session_search", "skills"}),
    RiskTier.LOCAL_IMPLEMENTATION: frozenset({"file", "terminal", "code_execution", "todo", "skills"}),
    RiskTier.CONSEQUENTIAL: frozenset(
        {"file", "terminal", "code_execution", "todo", "skills", "web", "browser", "computer_use"}
    ),
}


def _sha256_file(path: Path) -> str:
    value = __import__("hashlib").sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            value.update(chunk)
    return value.hexdigest()


def _write_json(path: Path, value: Any) -> None:
    secure_mkdir(path.parent)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    if os.name == "posix":
        os.chmod(path, 0o600)


def _resolve_inside(root: Path, relative: str, *, field_name: str) -> Path:
    candidate = Path(relative)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValidationError(f"{field_name} must be a relative path without '..'")
    resolved = (root / candidate).resolve()
    if resolved != root and root not in resolved.parents:
        raise ValidationError(f"{field_name} escapes the managed workdir")
    return resolved


def source_snapshot(workdir: Path, *, excluded: Sequence[Path] = ()) -> dict[str, Any]:
    """Return a canonical hash over exact source bytes, excluding managed evidence."""
    excluded_resolved = tuple(path.resolve() for path in excluded)
    files: dict[str, str] = {}
    for path in sorted(workdir.rglob("*")):
        if not path.is_file() or ".git" in path.relative_to(workdir).parts:
            continue
        resolved = path.resolve()
        if any(resolved == item or item in resolved.parents for item in excluded_resolved):
            continue
        relative = path.relative_to(workdir).as_posix()
        files[relative] = _sha256_file(path)
    return {"sha256": digest(files), "file_count": len(files), "files": files}


@dataclass(frozen=True, slots=True)
class CheckEvidence:
    argv: tuple[str, ...]
    returncode: int
    stdout_sha256: str
    stderr_sha256: str
    passed: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "argv": list(self.argv),
            "returncode": self.returncode,
            "stdout_sha256": self.stdout_sha256,
            "stderr_sha256": self.stderr_sha256,
            "passed": self.passed,
        }


@dataclass(frozen=True, slots=True)
class ContributionReceipt:
    schema: str
    run_id: str
    specialist_id: str
    status: str
    artifact_path: str
    artifact_sha256: str
    summary: str
    capability_gap: tuple[str, ...] = ()
    evidence: tuple[str, ...] = ()

    @classmethod
    def from_path(cls, path: Path) -> "ContributionReceipt":
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise ValidationError(f"contribution receipt is missing or invalid: {path}") from exc
        receipt = cls(
            schema=value.get("schema", ""),
            run_id=value.get("run_id", ""),
            specialist_id=value.get("specialist_id", ""),
            status=value.get("status", ""),
            artifact_path=value.get("artifact_path", ""),
            artifact_sha256=value.get("artifact_sha256", ""),
            summary=value.get("summary", ""),
            capability_gap=tuple(value.get("capability_gap", ())),
            evidence=tuple(value.get("evidence", ())),
        )
        if receipt.schema != "lpos.managed-contribution.v1":
            raise ValidationError("contribution receipt has the wrong schema")
        require_id("run_id", receipt.run_id)
        require_id("specialist_id", receipt.specialist_id)
        require_text("summary", receipt.summary, max_length=20_000)
        if receipt.status not in {"completed", "capability_gap", "failed"}:
            raise ValidationError("contribution receipt has an invalid status")
        if receipt.status == "capability_gap" and not receipt.capability_gap:
            raise ValidationError("capability_gap receipt must identify missing capabilities")
        return receipt


@dataclass(frozen=True, slots=True)
class ReviewReceipt:
    schema: str
    run_id: str
    reviewer_id: str
    decision: str
    artifact_sha256: str
    source_sha256: str
    corrections: tuple[str, ...]
    evidence_reviewed: tuple[str, ...]
    summary: str

    @classmethod
    def from_path(cls, path: Path) -> "ReviewReceipt":
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise ValidationError(f"review receipt is missing or invalid: {path}") from exc
        receipt = cls(
            schema=value.get("schema", ""),
            run_id=value.get("run_id", ""),
            reviewer_id=value.get("reviewer_id", ""),
            decision=value.get("decision", ""),
            artifact_sha256=value.get("artifact_sha256", ""),
            source_sha256=value.get("source_sha256", ""),
            corrections=tuple(value.get("corrections", ())),
            evidence_reviewed=tuple(value.get("evidence_reviewed", ())),
            summary=value.get("summary", ""),
        )
        if receipt.schema != "lpos.managed-review.v1":
            raise ValidationError("review receipt has the wrong schema")
        if receipt.decision not in {"PASS", "REJECT"}:
            raise ValidationError("review receipt decision must be PASS or REJECT")
        if receipt.decision == "REJECT" and not receipt.corrections:
            raise ValidationError("REJECT review must include consolidated corrections")
        require_text("review summary", receipt.summary, max_length=20_000)
        return receipt


@dataclass(slots=True)
class ManagedRunRequest:
    instruction: str
    workdir: Path
    specialist_id: str
    reviewer_id: str
    artifact_path: str
    required_capabilities: tuple[str, ...]
    toolsets: tuple[str, ...]
    checks: tuple[str, ...]
    risk_tier: RiskTier = RiskTier.LOCAL_IMPLEMENTATION
    state_root: Path | None = None
    hermes_command: str = "hermes"
    expected_repo: Path | None = None
    expected_head: str | None = None
    authorize_consequential: bool = False
    timeout_seconds: int = 1800
    max_corrections: int = 2
    preserved_receipts: tuple[Path, ...] = ()

    def __post_init__(self) -> None:
        self.workdir = self.workdir.expanduser().resolve()
        _resolve_inside(self.workdir, self.artifact_path, field_name="artifact_path")
        self.state_root = (self.state_root or self.workdir / ".lpos-managed").expanduser().resolve()
        self.specialist_id = require_id("specialist_id", self.specialist_id)
        self.reviewer_id = require_id("reviewer_id", self.reviewer_id)
        self.instruction = require_text("instruction", self.instruction, max_length=200_000)
        self.required_capabilities = tuple(dict.fromkeys(normalize_token(item) for item in self.required_capabilities))
        self.toolsets = tuple(dict.fromkeys(normalize_token(item) for item in self.toolsets))
        if self.specialist_id == self.reviewer_id:
            raise ValidationError("reviewer must be a different specialist")
        if not 0 <= self.max_corrections <= 2:
            raise ValidationError("max_corrections must be between 0 and 2")
        if self.risk_tier is RiskTier.CONSEQUENTIAL and not self.authorize_consequential:
            raise ValidationError("consequential managed execution requires separate explicit authorization")
        disallowed = set(self.toolsets) - _ALLOWED_TOOLSETS[self.risk_tier]
        if disallowed:
            raise ValidationError(
                f"toolsets are not allowed for risk tier {self.risk_tier.value}: {', '.join(sorted(disallowed))}"
            )


class ManagedExecution:
    """Bounded creator, independent review, and consolidated correction workflow."""

    def __init__(self, request: ManagedRunRequest, *, registry: CapabilityRegistry | None = None) -> None:
        self.request = request
        self.registry = registry or CapabilityRegistry.default()
        self.run_id = new_id("MRUN")
        assert request.state_root is not None
        self.run_root = request.state_root / self.run_id
        self.evidence_dir = self.run_root / "evidence"
        self.receipt_path = self.run_root / "contribution.json"
        self.review_path = self.run_root / "review.json"
        self.state_path = self.run_root / "state.json"
        self.contract_path = self.run_root / "contract.json"
        self.events: list[dict[str, Any]] = []

    def _profile(self, specialist_id: str) -> SpecialistProfile:
        matches = [item for item in self.registry.profiles if item.specialist_id == specialist_id]
        if not matches:
            raise ValidationError(f"exact specialist is not active: {specialist_id}")
        return matches[0]

    def _event(self, event_type: str, **payload: Any) -> None:
        event = {"sequence": len(self.events) + 1, "at": utc_now(), "type": event_type, "payload": payload}
        event["event_hash"] = digest({"previous": self.events[-1]["event_hash"] if self.events else "GENESIS", **event})
        self.events.append(event)
        self._persist(ManagedStatus(payload.get("status", ManagedStatus.PREFLIGHT.value)))

    def _persist(self, status: ManagedStatus, **extra: Any) -> None:
        value = {
            "schema": "lpos.managed-run.v1",
            "run_id": self.run_id,
            "status": status.value,
            "risk_tier": self.request.risk_tier.value,
            "workdir": str(self.request.workdir),
            "specialist_id": self.request.specialist_id,
            "reviewer_id": self.request.reviewer_id,
            "max_corrections": self.request.max_corrections,
            "events": self.events,
            "completion_latch": status is ManagedStatus.COMPLETED,
            **extra,
        }
        _write_json(self.state_path, value)

    def preflight(self) -> dict[str, Any]:
        gaps: list[str] = []
        workdir = self.request.workdir
        if not workdir.is_dir():
            gaps.append("workdir_missing")
        executable = shutil.which(self.request.hermes_command)
        if executable is None:
            gaps.append("hermes_cli_missing")
        git_root = None
        head = None
        if workdir.is_dir():
            completed = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"], cwd=workdir, capture_output=True, text=True, check=False
            )
            if completed.returncode != 0:
                gaps.append("git_repository_missing")
            else:
                git_root = Path(completed.stdout.strip()).resolve()
                if git_root != workdir:
                    gaps.append("workdir_not_repository_root")
                head_result = subprocess.run(
                    ["git", "rev-parse", "HEAD"], cwd=workdir, capture_output=True, text=True, check=False
                )
                if head_result.returncode == 0:
                    head = head_result.stdout.strip()
        if self.request.expected_repo and git_root != self.request.expected_repo.expanduser().resolve():
            gaps.append("repository_identity_mismatch")
        if self.request.expected_head and head != self.request.expected_head:
            gaps.append("head_mismatch")
        creator = self._profile(self.request.specialist_id)
        reviewer = self._profile(self.request.reviewer_id)
        missing = set(self.request.required_capabilities) - creator.capabilities
        gaps.extend(f"specialist_capability:{item}" for item in sorted(missing))
        if creator.specialist_id == reviewer.specialist_id:
            gaps.append("reviewer_not_independent")
        preserved = []
        for path in self.request.preserved_receipts:
            target = path.expanduser().resolve()
            if not target.is_file():
                gaps.append(f"preserved_receipt_missing:{target}")
            else:
                preserved.append({"path": str(target), "sha256": _sha256_file(target)})
        evidence = {
            "workdir": str(workdir),
            "git_root": str(git_root) if git_root else None,
            "head": head,
            "hermes_executable": executable,
            "requested_toolsets": list(self.request.toolsets),
            "required_capabilities": list(self.request.required_capabilities),
            "preserved_receipts": preserved,
            "gaps": gaps,
        }
        _write_json(self.evidence_dir / "preflight.json", evidence)
        if gaps:
            self._persist(ManagedStatus.CAPABILITY_GAP, capability_gap=gaps, preflight=evidence)
        return evidence

    def _compile_contract(self) -> dict[str, Any]:
        profile = self._profile(self.request.specialist_id)
        task = TaskEnvelope(
            task_id=self.run_id,
            principal_instruction=self.request.instruction,
            lead_guild=profile.guild,
            lead_specialist=profile.specialist_id,
            craft_standards=profile.craft_standards,
            required_capabilities=self.request.required_capabilities,
            constraints={
                "workdir": str(self.request.workdir),
                "artifact_path": self.request.artifact_path,
                "risk_tier": self.request.risk_tier.value,
                "external_actions_authorized": self.request.authorize_consequential,
            },
            material=self.request.risk_tier is not RiskTier.READ_ONLY,
            materiality_basis=("managed_local_implementation",) if self.request.risk_tier is not RiskTier.READ_ONLY else (),
            model_class=profile.model_class,
            creator_adapter="hermes-cli-managed-execution",
        )
        interpretation = InterpretationContract(
            task_id=self.run_id,
            instruction_verbatim=self.request.instruction,
            interpretation="Produce the requested artifact in the exact repository through the routed specialist role.",
            invariants=(
                "Work only inside the exact managed workdir.",
                "Do not substitute another specialist or return work to the parent.",
                "Do not perform external or consequential actions unless the risk tier separately authorizes them.",
                "Write the concrete artifact and machine-readable contribution receipt before reporting completion.",
            ),
            conflicts=(),
            verification_plan=(
                "Run the configured deterministic checks.",
                "Bind review to exact source and artifact SHA-256 hashes.",
                "Require a different specialist in a fresh context to pass the final candidate.",
            ),
            spec_ref="LPOS-v4.8.0:managed-execution",
        )
        artifact_spec = ArtifactSpecification(
            artifact_id=f"ART-{self.run_id.split('-', 1)[1]}",
            structural_decisions={"artifact_path": self.request.artifact_path},
            invariants=("The artifact path remains inside the exact workdir.",),
        )
        context = ContextCompiler(SpecRepository.packaged()).compile_task(
            task=task, interpretation=interpretation, artifact_specification=artifact_spec
        )
        if context.missing_components:
            raise ValidationError("managed creation context has missing components: " + ", ".join(context.missing_components))
        contract = {
            "schema": "lpos.managed-contract.v1",
            "run_id": self.run_id,
            "task": task.to_dict(),
            "interpretation": interpretation.to_dict(),
            "artifact_specification": artifact_spec.to_dict(),
            "context": context.to_dict(),
            "receipt_path": str(self.receipt_path),
        }
        _write_json(self.contract_path, contract)
        return contract

    def _run_hermes(self, prompt: str, *, phase: str) -> subprocess.CompletedProcess[str]:
        argv = [self.request.hermes_command, "chat", "-q", prompt, "-Q", "--source", "lpos-managed"]
        if self.request.toolsets:
            argv.extend(["--toolsets", ",".join(self.request.toolsets)])
        if self.request.risk_tier is not RiskTier.READ_ONLY:
            argv.append("--yolo")
        completed = subprocess.run(
            argv,
            cwd=self.request.workdir,
            capture_output=True,
            text=True,
            timeout=self.request.timeout_seconds,
            check=False,
        )
        _write_json(
            self.evidence_dir / f"{phase}-process.json",
            {
                "argv": argv[:2] + ["<compiled-contract>"] + argv[3:],
                "returncode": completed.returncode,
                "stdout_sha256": text_digest(completed.stdout),
                "stderr_sha256": text_digest(completed.stderr),
                "stdout_tail": completed.stdout[-4000:],
                "stderr_tail": completed.stderr[-4000:],
            },
        )
        return completed

    def _creator_prompt(self, contract: Mapping[str, Any], corrections: Sequence[str] = ()) -> str:
        correction_text = canonical_json(list(corrections)) if corrections else "[]"
        return (
            "You are the exact LPOS specialist named in the compiled contract below. Execute the task with the available tools. "
            "Work only in the current exact workdir. Do not delegate, substitute roles, publish, deploy, email, or perform any external action. "
            f"Create the concrete artifact at {self.request.artifact_path}. After the artifact exists, calculate its exact SHA-256 and write "
            f"{self.receipt_path} as JSON with schema lpos.managed-contribution.v1, run_id {self.run_id}, specialist_id "
            f"{self.request.specialist_id}, status completed or capability_gap or failed, artifact_path exactly "
            f"{json.dumps(self.request.artifact_path)} as the configured relative path, artifact_sha256, summary, capability_gap array, "
            "and evidence array. artifact_path must be that exact relative string; never use an absolute, canonical, or workspace-prefixed path. "
            "evidence must match the contribution schema: a JSON array whose items are non-empty strings. "
            "A capability gap is terminal. Do not ask the parent or another specialist to replace you. "
            f"Consolidated corrections from the independent reviewer: {correction_text}\n\nCOMPILED CONTRACT:\n{canonical_json(contract)}"
        )

    def _validate_contribution(self) -> ContributionReceipt:
        receipt = ContributionReceipt.from_path(self.receipt_path)
        if receipt.run_id != self.run_id or receipt.specialist_id != self.request.specialist_id:
            raise ValidationError("contribution receipt identity does not match managed run")
        if receipt.artifact_path != self.request.artifact_path:
            raise ValidationError(
                f"contribution receipt artifact_path must equal the exact configured relative path: {self.request.artifact_path}"
            )
        artifact = _resolve_inside(self.request.workdir, receipt.artifact_path, field_name="artifact_path")
        expected = _resolve_inside(self.request.workdir, self.request.artifact_path, field_name="artifact_path")
        if artifact != expected:
            raise ValidationError("contribution receipt names an unexpected artifact")
        if receipt.status == "completed":
            if not artifact.is_file():
                raise ValidationError("completed contribution receipt has no concrete artifact")
            if _sha256_file(artifact) != receipt.artifact_sha256:
                raise ValidationError("contribution receipt artifact hash does not match")
        return receipt

    def _run_checks(self, cycle: int) -> tuple[CheckEvidence, ...]:
        results: list[CheckEvidence] = []
        for index, command in enumerate(self.request.checks, start=1):
            argv = tuple(shlex.split(command))
            if not argv:
                raise ValidationError("deterministic check may not be empty")
            completed = subprocess.run(
                argv, cwd=self.request.workdir, capture_output=True, text=True, timeout=self.request.timeout_seconds, check=False
            )
            evidence = CheckEvidence(
                argv=argv,
                returncode=completed.returncode,
                stdout_sha256=text_digest(completed.stdout),
                stderr_sha256=text_digest(completed.stderr),
                passed=completed.returncode == 0,
            )
            results.append(evidence)
            _write_json(
                self.evidence_dir / f"cycle-{cycle}-check-{index}.json",
                {**evidence.to_dict(), "stdout_tail": completed.stdout[-8000:], "stderr_tail": completed.stderr[-8000:]},
            )
        return tuple(results)

    def _review_prompt(
        self, *, artifact_sha256: str, source_sha256: str, checks: Sequence[CheckEvidence], cycle: int
    ) -> str:
        repository = SpecRepository.packaged()
        reviewer_ref, reviewer_charter = repository.load_component(self.request.reviewer_id)
        if not reviewer_ref:
            raise ValidationError("reviewer charter is unavailable")
        review_envelope = {
            "run_id": self.run_id,
            "instruction": self.request.instruction,
            "creator_specialist": self.request.specialist_id,
            "reviewer_specialist": self.request.reviewer_id,
            "artifact_path": self.request.artifact_path,
            "artifact_sha256": artifact_sha256,
            "source_sha256": source_sha256,
            "checks": [item.to_dict() for item in checks],
            "cycle": cycle,
            "excluded": ["creation conversation", "creator private reasoning", "creator self-assessment"],
        }
        return (
            "You are the different LPOS specialist identified below. Perform one exhaustive fresh-context review of the exact current workdir. "
            "Do not modify any source or artifact file. Inspect the artifact, relevant source, and deterministic evidence. Recompute the supplied "
            "artifact and source hashes using the same repository state. Consolidate every blocking correction into one review. "
            f"Write only the machine-readable review receipt at {self.review_path} with schema lpos.managed-review.v1, run_id {self.run_id}, "
            f"reviewer_id {self.request.reviewer_id}, decision PASS or REJECT, artifact_sha256, source_sha256, corrections array, "
            "evidence_reviewed array, and summary. Do not perform external actions.\n\n"
            f"REVIEWER CHARTER ({reviewer_ref}):\n{reviewer_charter}\n\nREVIEW ENVELOPE:\n{canonical_json(review_envelope)}"
        )

    def run(self) -> dict[str, Any]:
        secure_mkdir(self.evidence_dir)
        assert self.request.state_root is not None
        self._persist(ManagedStatus.PREFLIGHT)
        preflight = self.preflight()
        if preflight["gaps"]:
            return json.loads(self.state_path.read_text(encoding="utf-8"))
        contract = self._compile_contract()
        corrections: tuple[str, ...] = ()
        final_checks: tuple[CheckEvidence, ...] = ()
        final_source: dict[str, Any] | None = None
        final_receipt: ContributionReceipt | None = None
        final_review: ReviewReceipt | None = None
        cycle = 0
        for cycle in range(self.request.max_corrections + 1):
            status = ManagedStatus.EXECUTING if cycle == 0 else ManagedStatus.CORRECTING
            self._persist(status, correction_cycle=cycle)
            completed = self._run_hermes(self._creator_prompt(contract, corrections), phase=f"cycle-{cycle}-creator")
            if completed.returncode != 0:
                self._persist(ManagedStatus.FAILED, failure="creator_process_failed", correction_cycle=cycle)
                return json.loads(self.state_path.read_text(encoding="utf-8"))
            try:
                final_receipt = self._validate_contribution()
            except ValidationError as exc:
                diagnostic = str(exc)
                corrections = (f"Correct the invalid contribution receipt: {diagnostic}",)
                if cycle >= self.request.max_corrections:
                    self._persist(
                        ManagedStatus.FAILED,
                        failure="contribution_receipt_invalid",
                        diagnostic=diagnostic,
                        correction_cycle=cycle,
                    )
                    return json.loads(self.state_path.read_text(encoding="utf-8"))
                continue
            if final_receipt.status == "capability_gap":
                self._persist(
                    ManagedStatus.CAPABILITY_GAP,
                    capability_gap=list(final_receipt.capability_gap),
                    contribution={
                        "schema": final_receipt.schema,
                        "run_id": final_receipt.run_id,
                        "specialist_id": final_receipt.specialist_id,
                        "status": final_receipt.status,
                        "artifact_path": final_receipt.artifact_path,
                        "artifact_sha256": final_receipt.artifact_sha256,
                        "summary": final_receipt.summary,
                        "capability_gap": list(final_receipt.capability_gap),
                        "evidence": list(final_receipt.evidence),
                    },
                    correction_cycle=cycle,
                )
                return json.loads(self.state_path.read_text(encoding="utf-8"))
            if final_receipt.status != "completed":
                self._persist(ManagedStatus.FAILED, failure="creator_reported_failed", correction_cycle=cycle)
                return json.loads(self.state_path.read_text(encoding="utf-8"))
            final_checks = self._run_checks(cycle)
            if any(not item.passed for item in final_checks):
                corrections = tuple(
                    f"Deterministic check failed: {' '.join(item.argv)}" for item in final_checks if not item.passed
                )
                if cycle >= self.request.max_corrections:
                    self._persist(ManagedStatus.FAILED, failure="deterministic_checks_failed", correction_cycle=cycle)
                    return json.loads(self.state_path.read_text(encoding="utf-8"))
                continue
            final_source = source_snapshot(self.request.workdir, excluded=(self.request.state_root,))
            artifact_sha = final_receipt.artifact_sha256
            self._persist(ManagedStatus.REVIEWING, correction_cycle=cycle)
            self.review_path.unlink(missing_ok=True)
            review_process = self._run_hermes(
                self._review_prompt(
                    artifact_sha256=artifact_sha,
                    source_sha256=final_source["sha256"],
                    checks=final_checks,
                    cycle=cycle,
                ),
                phase=f"cycle-{cycle}-review",
            )
            if review_process.returncode != 0:
                self._persist(ManagedStatus.FAILED, failure="review_process_failed", correction_cycle=cycle)
                return json.loads(self.state_path.read_text(encoding="utf-8"))
            final_review = ReviewReceipt.from_path(self.review_path)
            if final_review.run_id != self.run_id or final_review.reviewer_id != self.request.reviewer_id:
                raise ValidationError("review receipt identity does not match managed run")
            if final_review.reviewer_id == final_receipt.specialist_id:
                raise ValidationError("creator cannot review its own contribution")
            current_source = source_snapshot(self.request.workdir, excluded=(self.request.state_root,))
            if current_source["sha256"] != final_source["sha256"]:
                raise ValidationError("source changed during read-only review")
            if final_review.source_sha256 != final_source["sha256"] or final_review.artifact_sha256 != artifact_sha:
                raise ValidationError("review is not bound to the exact source and artifact hashes")
            if final_review.decision == "PASS":
                break
            corrections = final_review.corrections
            if cycle >= self.request.max_corrections:
                self._persist(ManagedStatus.FAILED, failure="correction_limit_reached", correction_cycle=cycle)
                return json.loads(self.state_path.read_text(encoding="utf-8"))
        if final_receipt is None or final_review is None or final_source is None or final_review.decision != "PASS":
            raise ValidationError("managed execution reached an invalid terminal state")
        result = {
            "correction_cycles": cycle,
            "artifact": {
                "path": final_receipt.artifact_path,
                "sha256": final_receipt.artifact_sha256,
            },
            "source": final_source,
            "checks": [item.to_dict() for item in final_checks],
            "review": {
                "reviewer_id": final_review.reviewer_id,
                "decision": final_review.decision,
                "summary": final_review.summary,
                "source_sha256": final_review.source_sha256,
                "artifact_sha256": final_review.artifact_sha256,
            },
        }
        self._persist(ManagedStatus.COMPLETED, **result)
        return json.loads(self.state_path.read_text(encoding="utf-8"))
