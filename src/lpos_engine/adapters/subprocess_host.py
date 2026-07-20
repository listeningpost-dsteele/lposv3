"""Runtime-neutral JSON subprocess adapter for any configured model host."""

from __future__ import annotations

import json
import subprocess
from collections.abc import Sequence

from ..canonical import canonical_json, normalize_token, require_text
from ..errors import AdapterError, ValidationError
from ..models import (
    MODEL_CLASSES,
    ContextBundle,
    ModelOutput,
    ReviewEnvelope,
    ReviewResult,
    TaskEnvelope,
)


class SubprocessModelAdapter:
    """Invoke a configured command with JSON on stdin and JSON on stdout.

    No shell is used.  The command owns provider credentials and model-specific
    behavior; the LPOS engine only sends the compiled context and validates the
    returned envelope.
    """

    def __init__(
        self,
        name: str,
        command: Sequence[str],
        *,
        model_classes: frozenset[str],
        capabilities: frozenset[str],
        supports_creation: bool = True,
        supports_review: bool = True,
        local: bool = False,
        priority: int = 50,
        timeout_seconds: int = 180,
        max_stdout_bytes: int = 10_000_000,
        available: bool = True,
    ) -> None:
        self.name = require_text("adapter name", name, max_length=128)
        if isinstance(command, (str, bytes)) or not command:
            raise ValidationError("model-host command must be a non-empty sequence of strings")
        if any(not isinstance(part, str) or not part for part in command):
            raise ValidationError("model-host command must be a non-empty sequence of strings")
        declared_classes = frozenset(model_classes)
        if not declared_classes or not declared_classes <= MODEL_CLASSES:
            raise ValidationError("model-host adapter declares invalid model classes")
        if isinstance(capabilities, (str, bytes)):
            raise ValidationError("model-host capabilities must be a collection of tokens")
        normalized_capabilities = frozenset(normalize_token(item) for item in capabilities)
        for field_name, field_value in (
            ("supports_creation", supports_creation),
            ("supports_review", supports_review),
            ("local", local),
            ("available", available),
        ):
            if not isinstance(field_value, bool):
                raise ValidationError(f"{field_name} must be boolean")
        if isinstance(priority, bool) or not isinstance(priority, int) or priority < 0:
            raise ValidationError("priority must be a non-negative integer")
        if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, int) or timeout_seconds <= 0:
            raise ValidationError("timeout_seconds must be a positive integer")
        if isinstance(max_stdout_bytes, bool) or not isinstance(max_stdout_bytes, int) or max_stdout_bytes <= 0:
            raise ValidationError("max_stdout_bytes must be a positive integer")

        self.command = tuple(command)
        self.model_classes = declared_classes
        self.capabilities = normalized_capabilities
        self.supports_creation = supports_creation
        self.supports_review = supports_review
        self.local = local
        self.priority = priority
        self.timeout_seconds = timeout_seconds
        self.max_stdout_bytes = max_stdout_bytes
        self.available = available

    def _invoke(self, payload: dict) -> dict:
        try:
            completed = subprocess.run(
                self.command,
                input=canonical_json(payload),
                text=True,
                capture_output=True,
                timeout=self.timeout_seconds,
                check=False,
                shell=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise AdapterError(f"model-host adapter {self.name} could not run: {exc}") from exc
        if completed.returncode != 0:
            stderr = completed.stderr[-4000:].strip()
            raise AdapterError(
                f"model-host adapter {self.name} exited {completed.returncode}: {stderr or 'no stderr'}"
            )
        if len(completed.stdout.encode("utf-8")) > self.max_stdout_bytes:
            raise AdapterError(f"model-host adapter {self.name} exceeded stdout limit")
        try:
            value = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise AdapterError(f"model-host adapter {self.name} returned invalid JSON") from exc
        if not isinstance(value, dict):
            raise AdapterError(f"model-host adapter {self.name} must return a JSON object")
        return value

    def create_artifact(self, task: TaskEnvelope, context: ContextBundle) -> ModelOutput:
        result = self._invoke(
            {
                "operation": "create_artifact",
                "task": task.to_dict(),
                "context": context.to_dict(),
            }
        )
        return ModelOutput.from_dict(result)

    def review(self, envelope: ReviewEnvelope, context: ContextBundle) -> ReviewResult:
        result = self._invoke(
            {
                "operation": "review",
                "review_envelope": envelope.to_dict(),
                "context": context.to_dict(),
            }
        )
        return ReviewResult.from_dict(result)
