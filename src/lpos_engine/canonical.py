"""Canonical serialization, hashing, time, and identifier helpers."""

from __future__ import annotations

import dataclasses
import hashlib
import json
import re
import uuid
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

from .errors import ValidationError

_ID_RE = re.compile(r"^[A-Z][A-Z0-9_-]{1,63}$")


def utc_now() -> str:
    """Return a timezone-aware ISO-8601 timestamp with second precision."""

    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_timestamp(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, TypeError, ValueError) as exc:
        raise ValidationError(f"invalid ISO-8601 timestamp: {value!r}") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValidationError(f"timestamp must include a UTC offset: {value!r}")
    return parsed


def new_id(prefix: str) -> str:
    normalized = prefix.upper().rstrip("-")
    if not _ID_RE.fullmatch(normalized):
        raise ValidationError(f"invalid id prefix: {prefix!r}")
    return f"{normalized}-{uuid.uuid4().hex[:16].upper()}"


def jsonable(value: Any) -> Any:
    """Convert dataclasses and common immutable values to plain JSON values."""

    if dataclasses.is_dataclass(value):
        return {field.name: jsonable(getattr(value, field.name)) for field in dataclasses.fields(value)}
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Mapping):
        return {str(key): jsonable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [jsonable(item) for item in value]
    if isinstance(value, (set, frozenset)):
        # Set iteration order is deliberately unspecified.  Sort by each item's
        # canonical representation so digests remain stable across processes.
        converted = [jsonable(item) for item in value]
        return sorted(converted, key=lambda item: json.dumps(item, sort_keys=True, separators=(",", ":"), ensure_ascii=False))
    if isinstance(value, datetime):
        if value.tzinfo is None:
            raise ValidationError("naive datetime cannot be serialized")
        return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise ValidationError(f"value is not JSON serializable: {type(value).__name__}")


def canonical_json(value: Any) -> str:
    try:
        return json.dumps(
            jsonable(value),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"value cannot be represented as canonical JSON: {exc}") from exc


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def text_digest(value: str | bytes) -> str:
    raw = value if isinstance(value, bytes) else value.encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def require_text(name: str, value: str, *, max_length: int | None = None) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{name} must be a non-empty string")
    clean = value.strip()
    if max_length is not None and len(clean) > max_length:
        raise ValidationError(f"{name} exceeds {max_length} characters")
    return clean


def require_id(name: str, value: str) -> str:
    clean = require_text(name, value, max_length=128)
    if any(char.isspace() for char in clean):
        raise ValidationError(f"{name} may not contain whitespace")
    return clean


def normalize_token(value: str) -> str:
    value = require_text("token", value, max_length=128).lower()
    value = re.sub(r"[^a-z0-9]+", "_", value).strip("_")
    if not value:
        raise ValidationError("token contains no alphanumeric characters")
    return value


def _freeze_json(value: Any) -> Any:
    """Recursively freeze a JSON-compatible value.

    Frozen dataclasses are not sufficient when they contain ordinary dicts or
    lists: a caller could otherwise mutate an already-hashed action after its
    approval was recorded.  Mapping proxies and tuples make envelope contents
    immutable all the way down.
    """

    if isinstance(value, Mapping):
        frozen: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValidationError("JSON object keys must be strings")
            if key in frozen:
                raise ValidationError(f"duplicate JSON object key: {key!r}")
            frozen[key] = _freeze_json(item)
        return MappingProxyType(frozen)
    if isinstance(value, (tuple, list)):
        return tuple(_freeze_json(item) for item in value)
    if isinstance(value, (set, frozenset)):
        frozen_items = tuple(_freeze_json(item) for item in value)
        return tuple(sorted(frozen_items, key=canonical_json))
    if value is None or isinstance(value, (str, int, float, bool)):
        # canonical_json performs the final NaN/infinity validation.
        return value
    raise ValidationError(f"value is not JSON compatible: {type(value).__name__}")


def freeze_mapping(value: Mapping[str, Any] | None) -> Mapping[str, Any]:
    """Deep-copy, validate, and recursively freeze a JSON object."""

    frozen = _freeze_json(value or {})
    canonical_json(frozen)
    return frozen
