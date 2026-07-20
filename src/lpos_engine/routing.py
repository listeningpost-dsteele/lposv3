"""Capability-first routing with guilds retained as the governance view."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

from .canonical import normalize_token, require_id, require_text
from .errors import ValidationError
from .models import MODEL_CLASSES, RouteDecision


@dataclass(frozen=True, slots=True)
class SpecialistProfile:
    specialist_id: str
    name: str
    guild: str
    capabilities: frozenset[str]
    craft_standards: tuple[str, ...]
    model_class: str
    priority: int = 100

    def __post_init__(self) -> None:
        require_id("specialist_id", self.specialist_id)
        require_text("name", self.name)
        require_text("guild", self.guild)
        if not self.capabilities:
            raise ValidationError(f"{self.specialist_id} has no capabilities")
        if self.model_class not in MODEL_CLASSES:
            raise ValidationError(f"unknown model class: {self.model_class}")

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "SpecialistProfile":
        data = dict(value)
        data["capabilities"] = frozenset(normalize_token(item) for item in data.get("capabilities", ()))
        data["craft_standards"] = tuple(data.get("craft_standards", ()))
        return cls(**data)


class CapabilityRegistry:
    def __init__(self, profiles: Iterable[SpecialistProfile]) -> None:
        self.profiles = tuple(profiles)
        if not self.profiles:
            raise ValidationError("capability registry may not be empty")
        ids = [profile.specialist_id for profile in self.profiles]
        if len(ids) != len(set(ids)):
            raise ValidationError("duplicate specialist profile id")

    @classmethod
    def from_json(cls, path: str | Path) -> "CapabilityRegistry":
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(SpecialistProfile.from_dict(item) for item in raw["specialists"])

    @classmethod
    def default(cls) -> "CapabilityRegistry":
        from importlib.resources import files

        try:
            resource = files("lpos_engine.config").joinpath("default_registry.json")
            raw = json.loads(resource.read_text(encoding="utf-8"))
            profiles = raw["specialists"]
        except (FileNotFoundError, ModuleNotFoundError, OSError, ValueError, KeyError, TypeError) as exc:
            raise ValidationError("packaged capability registry is missing or invalid") from exc
        return cls(SpecialistProfile.from_dict(item) for item in profiles)


class CapabilityRouter:
    """Choose the smallest set of profiles that covers the requested capabilities."""

    def __init__(self, registry: CapabilityRegistry) -> None:
        self.registry = registry

    def route(
        self,
        required_capabilities: Iterable[str],
        *,
        preferred_model_class: str | None = None,
    ) -> RouteDecision:
        required = tuple(dict.fromkeys(normalize_token(item) for item in required_capabilities))
        if not required:
            required = ("executive_coordination",)
        required_set = set(required)

        # First prefer a single complete profile.  Extra-capability count is a
        # specialization penalty; priority is an explicit tie-breaker.
        complete = [profile for profile in self.registry.profiles if required_set <= profile.capabilities]
        if complete:
            lead = min(
                complete,
                key=lambda profile: (
                    len(profile.capabilities - required_set),
                    profile.priority,
                    profile.specialist_id,
                ),
            )
            selected = [lead]
        else:
            selected = self._greedy_cover(required_set)
            lead = selected[0]

        covered = set().union(*(profile.capabilities for profile in selected))
        missing = required_set - covered
        standards = tuple(
            dict.fromkeys(standard for profile in selected for standard in profile.craft_standards)
        )
        model_class = preferred_model_class or lead.model_class
        if model_class not in MODEL_CLASSES:
            raise ValidationError(f"unknown model class: {model_class}")
        substitutions = ()
        if missing:
            substitutions = (
                "No profile fully covers: " + ", ".join(sorted(missing)) + "; Principal escalation required",
            )

        trace = (
            f"required={','.join(required)}",
            "selected=" + ",".join(profile.specialist_id for profile in selected),
            f"coverage={len(required_set - missing)}/{len(required_set)}",
        )
        return RouteDecision(
            lead_guild=lead.guild,
            lead_specialist=lead.specialist_id,
            supporting_specialists=tuple(profile.specialist_id for profile in selected[1:]),
            craft_standards=standards,
            model_class=model_class,
            required_capabilities=required,
            covered_capabilities=tuple(sorted(required_set - missing)),
            missing_capabilities=tuple(sorted(missing)),
            substitutions=substitutions,
            trace=trace,
        )

    def _greedy_cover(self, required: set[str]) -> list[SpecialistProfile]:
        uncovered = set(required)
        remaining = list(self.registry.profiles)
        selected: list[SpecialistProfile] = []
        while uncovered and remaining:
            candidate = max(
                remaining,
                key=lambda profile: (
                    len(profile.capabilities & uncovered),
                    -profile.priority,
                    -len(profile.capabilities),
                    profile.specialist_id,
                ),
            )
            gain = candidate.capabilities & uncovered
            if not gain:
                break
            selected.append(candidate)
            uncovered -= gain
            remaining.remove(candidate)
        if not selected:
            # The executive profile is guaranteed in the default registry, but a
            # custom registry may not contain one.  Choose deterministically.
            selected.append(min(self.registry.profiles, key=lambda profile: (profile.priority, profile.specialist_id)))
        # Lead is the profile with the greatest original coverage, not merely the
        # first accidental registry order.
        selected.sort(
            key=lambda profile: (
                -len(profile.capabilities & required),
                profile.priority,
                profile.specialist_id,
            )
        )
        return selected

