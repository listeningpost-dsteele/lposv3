"""Lazy, deterministic context compilation from the integrated LPOS v4 specification."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

from .canonical import canonical_json, new_id, text_digest
from .errors import ContextIsolationError, ValidationError
from .models import (
    ArtifactSpecification,
    ContextBundle,
    InterpretationContract,
    REVIEW_EXCLUSIONS,
    ReviewEnvelope,
    TaskEnvelope,
)

_COMPONENT_FILES = {
    "SPECIALIST-": "SPECIALISTS.md",
    "CS-": "CRAFT-STANDARDS.md",
    "SO-": "STANDING-OPERATIONS.md",
    "LPOS-": "LPOS-CORE.md",
    "BENCH-": "BENCHMARKS.md",
}


class SpecRepository:
    """Read only requested sections from the canonical LPOS v4 specification."""

    def __init__(self, root: str | Path | None) -> None:
        self.root = Path(root).resolve() if root else None

    @classmethod
    def packaged(cls) -> "SpecRepository":
        """Load the specification shipped inside the installed LPOS v4 package."""
        from importlib.resources import files

        repository = cls(None)
        repository.root = files("lpos_engine.spec")
        return repository

    def load_kernel(self) -> tuple[str | None, str]:
        if self.root is None:
            return None, ""
        path = self.root / "CHIP-KERNEL.md"
        if not path.is_file():
            return None, ""
        return str(path), path.read_text(encoding="utf-8")

    def load_component(self, component_id: str) -> tuple[str | None, str]:
        if self.root is None:
            return None, ""
        filename = next(
            (filename for prefix, filename in _COMPONENT_FILES.items() if component_id.startswith(prefix)),
            None,
        )
        if filename is None:
            return None, ""
        path = self.root / filename
        if not path.is_file():
            return None, ""
        text = path.read_text(encoding="utf-8")
        section = self.extract_markdown_section(text, component_id)
        return (f"{path}#{component_id}", section) if section else (None, "")

    def load_reviewer_skill(self) -> tuple[str | None, str]:
        if self.root is not None:
            path = self.root / "skills" / "independent-reviewer" / "SKILL.md"
            if path.is_file():
                return str(path), path.read_text(encoding="utf-8")
        return (
            "builtin:independent-reviewer",
            "# Independent reviewer\n"
            "Evaluate only the supplied ReviewEnvelope. Recompute intent, truth, reasoning, craft, "
            "outcome, and regressions. Return a ReviewResult. Do not infer creator reasoning.",
        )

    @staticmethod
    def extract_markdown_section(text: str, component_id: str) -> str:
        lines = text.splitlines()
        start = None
        level = None
        heading_re = re.compile(r"^(#{1,6})\s+.*(?:^|\b)" + re.escape(component_id) + r"(?:\b|$)")
        for index, line in enumerate(lines):
            match = heading_re.search(line)
            if match:
                start = index
                level = len(match.group(1))
                break
        if start is None or level is None:
            return ""
        end = len(lines)
        for index in range(start + 1, len(lines)):
            match = re.match(r"^(#{1,6})\s+", lines[index])
            if match and len(match.group(1)) <= level:
                end = index
                break
        return "\n".join(lines[start:end]).strip()


class ContextCompiler:
    def __init__(self, spec_repository: SpecRepository, *, max_chars: int = 160_000) -> None:
        if max_chars < 1_000:
            raise ValidationError("context max_chars is unreasonably small")
        self.spec_repository = spec_repository
        self.max_chars = max_chars

    def compile_task(
        self,
        *,
        task: TaskEnvelope,
        interpretation: InterpretationContract | None,
        artifact_specification: ArtifactSpecification | None,
        additional_components: Iterable[str] = (),
    ) -> ContextBundle:
        loaded: list[str] = []
        missing: list[str] = []
        sections: list[str] = []

        kernel_ref, kernel = self.spec_repository.load_kernel()
        if kernel_ref:
            loaded.append(kernel_ref)
            sections.append("# Kernel\n" + kernel)
        else:
            missing.append("CHIP-KERNEL.md")

        component_ids = tuple(
            dict.fromkeys(
                (
                    task.lead_specialist,
                    *task.supporting_specialists,
                    *task.craft_standards,
                    *additional_components,
                )
            )
        )
        for component_id in component_ids:
            ref, section = self.spec_repository.load_component(component_id)
            if ref:
                loaded.append(ref)
                sections.append(f"# Loaded component: {component_id}\n{section}")
            else:
                missing.append(component_id)

        structured = {
            "task_envelope": task.to_dict(),
            "interpretation_contract": interpretation.to_dict() if interpretation else None,
            "artifact_specification": artifact_specification.to_dict() if artifact_specification else None,
        }
        content = (
            "# LPOS Creation Context\n\n"
            "## Structured runtime state\n"
            "```json\n"
            + canonical_json(structured)
            + "\n```\n\n"
            + "\n\n".join(sections)
        )
        if len(content) > self.max_chars:
            raise ValidationError(
                f"compiled creation context exceeds {self.max_chars} characters; split the task or reduce components"
            )
        return ContextBundle(
            bundle_id=new_id("CTX"),
            task_id=task.task_id,
            purpose="creation",
            content=content,
            loaded_components=tuple(loaded),
            missing_components=tuple(missing),
            excluded=(),
            token_estimate=(len(content) + 3) // 4,
            bundle_hash=text_digest(content),
        )

    def compile_review(self, envelope: ReviewEnvelope) -> ContextBundle:
        skill_ref, skill = self.spec_repository.load_reviewer_skill()
        task_id = str(envelope.interpretation_contract.get("task_id") or envelope.artifact.get("task_id"))
        if not task_id or task_id == "None":
            raise ContextIsolationError("review envelope does not identify its task")
        content = (
            "# LPOS Independent Review Context\n\n"
            "This context is fresh. It contains only the reviewer instruction and the canonical ReviewEnvelope.\n\n"
            "## Reviewer instruction\n"
            + skill
            + "\n\n## ReviewEnvelope\n```json\n"
            + canonical_json(envelope)
            + "\n```\n"
        )
        if len(content) > self.max_chars:
            raise ValidationError(
                f"compiled review context exceeds {self.max_chars} characters; externalize the artifact by immutable ref"
            )
        bundle = ContextBundle(
            bundle_id=new_id("RCTX"),
            task_id=task_id,
            purpose="review",
            content=content,
            loaded_components=(skill_ref,) if skill_ref else (),
            missing_components=() if skill_ref else ("independent-reviewer/SKILL.md",),
            excluded=REVIEW_EXCLUSIONS,
            token_estimate=(len(content) + 3) // 4,
            bundle_hash=text_digest(content),
        )
        self.assert_review_isolated(bundle)
        return bundle

    @staticmethod
    def assert_review_isolated(bundle: ContextBundle) -> None:
        if bundle.purpose != "review":
            raise ContextIsolationError("review must use a review-purpose context")
        if tuple(bundle.excluded) != REVIEW_EXCLUSIONS:
            raise ContextIsolationError("review context does not declare all mandatory exclusions")
        if "# LPOS Creation Context" in bundle.content:
            raise ContextIsolationError("creation context leaked into review context")
