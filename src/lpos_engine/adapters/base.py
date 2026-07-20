"""Adapter protocols and deterministic adapter selection."""

from __future__ import annotations

from typing import Any, Iterable, Mapping, Protocol, runtime_checkable

from ..canonical import normalize_token, require_text
from ..errors import AdapterError, ValidationError
from ..models import (
    ActionPlan,
    ActionResult,
    ContextBundle,
    MODEL_CLASSES,
    ModelOutput,
    ReviewEnvelope,
    ReviewResult,
    TaskEnvelope,
)


@runtime_checkable
class ModelAdapter(Protocol):
    name: str
    model_classes: frozenset[str]
    capabilities: frozenset[str]
    supports_creation: bool
    supports_review: bool
    local: bool
    priority: int
    available: bool

    def create_artifact(self, task: TaskEnvelope, context: ContextBundle) -> ModelOutput:
        ...

    def review(self, envelope: ReviewEnvelope, context: ContextBundle) -> ReviewResult:
        ...


@runtime_checkable
class ActionAdapter(Protocol):
    name: str
    kinds: frozenset[str]

    def apply(self, plan: ActionPlan) -> ActionResult:
        ...


class AdapterRegistry:
    def __init__(
        self,
        *,
        model_adapters: Iterable[ModelAdapter] = (),
        action_adapters: Iterable[ActionAdapter] = (),
    ) -> None:
        self._models: dict[str, ModelAdapter] = {}
        self._actions: dict[str, ActionAdapter] = {}
        for adapter in model_adapters:
            self.register_model(adapter)
        for adapter in action_adapters:
            self.register_action(adapter)

    def register_model(self, adapter: ModelAdapter) -> None:
        try:
            raw_name = adapter.name
            raw_classes = adapter.model_classes
            raw_capabilities = adapter.capabilities
            flags = {
                "supports_creation": adapter.supports_creation,
                "supports_review": adapter.supports_review,
                "local": adapter.local,
                "available": adapter.available,
            }
            priority = adapter.priority
        except AttributeError as exc:
            raise ValidationError("model adapter is missing required metadata") from exc

        name = require_text("adapter name", raw_name, max_length=128)
        if raw_name != name:
            raise ValidationError("adapter name may not contain surrounding whitespace")
        if name in self._models:
            raise ValidationError(f"duplicate model adapter: {name}")
        if isinstance(raw_classes, (str, bytes)):
            raise ValidationError(f"adapter {name} model_classes must be a collection")
        try:
            declared_classes = frozenset(raw_classes)
        except TypeError as exc:
            raise ValidationError(f"adapter {name} model_classes must be a collection") from exc
        if not declared_classes or not declared_classes <= MODEL_CLASSES:
            raise ValidationError(f"adapter {name} declares invalid model classes")
        if isinstance(raw_capabilities, (str, bytes)):
            raise ValidationError(f"adapter {name} capabilities must be a collection")
        try:
            declared_capabilities = frozenset(raw_capabilities)
            normalized_capabilities = frozenset(
                normalize_token(item) for item in declared_capabilities
            )
        except (TypeError, ValidationError) as exc:
            raise ValidationError(f"adapter {name} declares invalid capabilities") from exc
        if declared_capabilities != normalized_capabilities:
            raise ValidationError(
                f"adapter {name} capabilities must use normalized tokens"
            )
        for field_name, field_value in flags.items():
            if not isinstance(field_value, bool):
                raise ValidationError(f"adapter {name} {field_name} must be boolean")
        if isinstance(priority, bool) or not isinstance(priority, int) or priority < 0:
            raise ValidationError(
                f"adapter {name} priority must be a non-negative integer"
            )
        if not callable(getattr(adapter, "create_artifact", None)):
            raise ValidationError(f"adapter {name} is missing create_artifact()")
        if not callable(getattr(adapter, "review", None)):
            raise ValidationError(f"adapter {name} is missing review()")
        self._models[name] = adapter

    def register_action(self, adapter: ActionAdapter) -> None:
        try:
            raw_name = adapter.name
            raw_kinds = adapter.kinds
        except AttributeError as exc:
            raise ValidationError("action adapter is missing required metadata") from exc
        name = require_text("adapter name", raw_name, max_length=128)
        if raw_name != name:
            raise ValidationError("adapter name may not contain surrounding whitespace")
        if name in {item.name for item in self._actions.values()}:
            raise ValidationError(f"duplicate action adapter: {name}")
        if isinstance(raw_kinds, (str, bytes)):
            raise ValidationError(f"action adapter {name} kinds must be a collection")
        try:
            kinds = tuple(raw_kinds)
        except TypeError as exc:
            raise ValidationError(f"action adapter {name} kinds must be a collection") from exc
        if not kinds:
            raise ValidationError(f"action adapter {name} must declare at least one kind")
        if not callable(getattr(adapter, "apply", None)):
            raise ValidationError(f"action adapter {name} is missing apply()")
        normalized_kinds: list[str] = []
        for kind in kinds:
            normalized = normalize_token(kind)
            if normalized in normalized_kinds:
                raise ValidationError(
                    f"action adapter {name} declares duplicate normalized kind: {normalized}"
                )
            if normalized in self._actions:
                raise ValidationError(f"action kind already registered: {normalized}")
            normalized_kinds.append(normalized)
        for normalized in normalized_kinds:
            self._actions[normalized] = adapter

    def select_model(
        self,
        *,
        model_class: str,
        required_capabilities: Iterable[str],
        purpose: str,
        exclude_name: str | None = None,
        exclude_names: Iterable[str] = (),
        require_local: bool = False,
        allow_partial: bool = False,
        allow_excluded_fallback: bool = True,
    ) -> ModelAdapter:
        if model_class not in MODEL_CLASSES:
            raise ValidationError(f"unknown model class: {model_class}")
        if purpose not in {"creation", "review"}:
            raise ValidationError(f"unknown model purpose: {purpose}")
        required = {normalize_token(item) for item in required_capabilities}
        excluded = {require_text("excluded adapter name", item, max_length=128) for item in exclude_names}
        if exclude_name is not None:
            excluded.add(require_text("excluded adapter name", exclude_name, max_length=128))
        candidates: list[ModelAdapter] = []
        for adapter in self._models.values():
            if not adapter.available or model_class not in adapter.model_classes:
                continue
            if adapter.name in excluded:
                continue
            if require_local and not adapter.local:
                continue
            if purpose == "creation" and not adapter.supports_creation:
                continue
            if purpose == "review" and not adapter.supports_review:
                continue
            candidates.append(adapter)
        if not candidates and excluded and allow_excluded_fallback:
            # LPOS prefers a different reviewer but permits the same model when
            # only one is available, provided the context itself is isolated.
            return self.select_model(
                model_class=model_class,
                required_capabilities=required,
                purpose=purpose,
                exclude_name=None,
                exclude_names=(),
                require_local=require_local,
                allow_partial=allow_partial,
                allow_excluded_fallback=False,
            )
        if not candidates:
            raise AdapterError(
                f"no available {purpose} adapter for model class {model_class!r}"
            )
        complete = [adapter for adapter in candidates if required <= adapter.capabilities]
        if not complete and not allow_partial:
            nearest = min(
                candidates,
                key=lambda adapter: (
                    len(required - adapter.capabilities),
                    adapter.priority,
                    adapter.name,
                ),
            )
            missing = ", ".join(sorted(required - nearest.capabilities))
            raise AdapterError(
                f"no available {purpose} adapter fully covers the required capabilities; "
                f"nearest adapter {nearest.name!r} is missing: {missing}"
            )
        pool = complete or candidates
        return min(
            pool,
            key=lambda adapter: (
                0 if required <= adapter.capabilities else 1,
                len(required - adapter.capabilities),
                adapter.priority,
                adapter.name,
            ),
        )

    def get_model(self, name: str) -> ModelAdapter:
        try:
            adapter = self._models[name]
        except KeyError as exc:
            raise AdapterError(f"model adapter not registered: {name}") from exc
        if not adapter.available:
            raise AdapterError(f"model adapter is unavailable: {name}")
        return adapter

    def get_action(self, kind: str) -> ActionAdapter:
        normalized = normalize_token(kind)
        try:
            return self._actions[normalized]
        except KeyError as exc:
            raise AdapterError(f"no action adapter registered for {normalized!r}") from exc

    @property
    def model_names(self) -> tuple[str, ...]:
        return tuple(sorted(self._models))
