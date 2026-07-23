"""Runtime-neutral JSON subprocess adapter for any configured model host.

Security note (LPOS-10): the hardening in this module is privilege
REDUCTION within the same operating-system account.  It is NOT an OS
sandbox and must not be described as an isolation boundary.  See the
class docstring for exactly what is and is not enforced.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import signal
import subprocess
import tempfile
import threading
import time
from collections.abc import Mapping, Sequence
from pathlib import Path

try:  # pragma: no cover - platform dependent
    import resource as _resource
except ImportError:  # pragma: no cover - non-POSIX platforms
    _resource = None

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

#: Environment keys copied from the parent when present.  Everything else in
#: the parent environment (credentials, tokens, cloud metadata hints, ...) is
#: withheld from the child unless explicitly configured via ``env`` or
#: ``inherit_env``.
_SAFE_ENV_KEYS = ("PATH", "HOME", "LANG", "LC_ALL", "TMPDIR", "PYTHONIOENCODING")

_READ_CHUNK_BYTES = 65536
_DEFAULT_MAX_STDERR_BYTES = 1_000_000

#: Config-tunable POSIX resource limits.  A value of ``None`` disables the
#: individual limit.  Defaults are deliberately generous so legitimate model
#: hosts keep working while runaway or hostile children stay bounded.
_RESOURCE_LIMIT_KEYS = (
    "cpu_seconds",
    "address_space_bytes",
    "file_size_bytes",
    "open_files",
    "processes",
)


def _default_resource_limits(timeout_seconds: int) -> dict[str, int | None]:
    return {
        "cpu_seconds": timeout_seconds + 30,
        "address_space_bytes": 4 * 1024**3,
        "file_size_bytes": 1024**3,
        "open_files": 256,
        "processes": 4096,
    }


class SubprocessModelAdapter:
    """Invoke a configured command with JSON on stdin and JSON on stdout.

    SECURITY BOUNDARY (LPOS-10) - this adapter is a privilege REDUCTION
    within the same operating-system account, not an OS sandbox:

    - The child runs as the same user as the LPOS engine.  It can read any
      file that account can read (including LPOS state and databases)
      unless the deployment restricts it externally.
    - Network egress is not constrained by this adapter.
    - The mitigations below reduce accidents and blast radius; they do not
      contain a malicious executable.

    Deployments that run untrusted or third-party model hosts MUST place
    the host in a container or a dedicated low-privilege account with an
    explicit filesystem view, no LPOS database access, and constrained
    network egress.  Capability and ``local`` declarations are policy
    inputs supplied by configuration, not self-attested security facts.

    What this adapter does enforce:

    - No shell.  The command is executed as argv with an absolute,
      optionally SHA-256-pinned executable path.
    - Minimal allowlisted environment: only PATH, HOME, LANG, LC_ALL,
      TMPDIR, PYTHONIOENCODING plus keys explicitly configured via ``env``
      (literal values) or ``inherit_env`` (names copied from the parent).
      Parent secrets are never inherited implicitly.
    - Explicit working directory: the configured ``cwd`` or a fresh
      temporary directory created per invocation.
    - stdout/stderr are streamed with hard byte caps enforced DURING
      reading, so peak memory stays bounded regardless of how much the
      child writes.  Breaching a cap or the timeout kills the child's
      entire process group (POSIX ``os.killpg``).
    - POSIX resource limits (CPU seconds, address space, file size, open
      files, process count) via ``resource.setrlimit`` where available.

    Platform caveats: process-group creation/kill and resource limits are
    POSIX-only.  On other platforms only the direct child process is
    killed and no resource limits are applied.
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
        max_stderr_bytes: int = _DEFAULT_MAX_STDERR_BYTES,
        available: bool = True,
        env: Mapping[str, str] | None = None,
        inherit_env: Sequence[str] = (),
        cwd: str | os.PathLike[str] | None = None,
        executable_sha256: str | None = None,
        resource_limits: Mapping[str, int | None] | None = None,
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
        if isinstance(max_stderr_bytes, bool) or not isinstance(max_stderr_bytes, int) or max_stderr_bytes <= 0:
            raise ValidationError("max_stderr_bytes must be a positive integer")

        extra_env: dict[str, str] = {}
        if env is not None:
            if not isinstance(env, Mapping):
                raise ValidationError("env must be a mapping of string keys to string values")
            for key, value in env.items():
                if not isinstance(key, str) or not key or "=" in key:
                    raise ValidationError("env keys must be non-empty strings without '='")
                if not isinstance(value, str):
                    raise ValidationError("env values must be strings")
                extra_env[key] = value
        if isinstance(inherit_env, (str, bytes)):
            raise ValidationError("inherit_env must be a sequence of environment variable names")
        inherited_names: tuple[str, ...] = tuple(inherit_env)
        for item in inherited_names:
            if not isinstance(item, str) or not item or "=" in item:
                raise ValidationError("inherit_env entries must be non-empty strings without '='")
        if cwd is not None and not isinstance(cwd, (str, os.PathLike)):
            raise ValidationError("cwd must be a path")
        if executable_sha256 is not None:
            if not isinstance(executable_sha256, str):
                raise ValidationError("executable_sha256 must be a 64-character hex string")
            normalized_digest = executable_sha256.strip().lower()
            if len(normalized_digest) != 64 or any(c not in "0123456789abcdef" for c in normalized_digest):
                raise ValidationError("executable_sha256 must be a 64-character hex string")
            executable_sha256 = normalized_digest
        limits = _default_resource_limits(timeout_seconds)
        if resource_limits is not None:
            if not isinstance(resource_limits, Mapping):
                raise ValidationError("resource_limits must be a mapping")
            for key, value in resource_limits.items():
                if key not in _RESOURCE_LIMIT_KEYS:
                    raise ValidationError(
                        f"unknown resource limit {key!r}; valid keys: {', '.join(_RESOURCE_LIMIT_KEYS)}"
                    )
                if value is not None and (isinstance(value, bool) or not isinstance(value, int) or value <= 0):
                    raise ValidationError(f"resource limit {key!r} must be a positive integer or None")
                limits[key] = value

        self.command = tuple(command)
        self.model_classes = declared_classes
        self.capabilities = normalized_capabilities
        self.supports_creation = supports_creation
        self.supports_review = supports_review
        self.local = local
        self.priority = priority
        self.timeout_seconds = timeout_seconds
        self.max_stdout_bytes = max_stdout_bytes
        self.max_stderr_bytes = max_stderr_bytes
        self.available = available
        self.extra_env = dict(extra_env)
        self.inherit_env = inherited_names
        self.cwd = Path(cwd) if cwd is not None else None
        self.executable_sha256 = executable_sha256
        self.resource_limits = limits
        #: Diagnostic: number of stdout bytes captured by the most recent
        #: invocation (never exceeds ``max_stdout_bytes``).
        self._last_stdout_bytes_captured = 0

    # -- child process construction helpers ---------------------------------

    def _resolved_executable(self) -> str:
        """Resolve command[0] to an absolute real path before exec."""
        executable = self.command[0]
        candidate = executable if os.path.isabs(executable) else shutil.which(executable)
        if candidate is None or not os.path.isfile(candidate):
            raise AdapterError(
                f"model-host adapter {self.name} could not run: executable not found: {executable!r}"
            )
        resolved = os.path.realpath(candidate)
        if not os.path.isfile(resolved):
            raise AdapterError(
                f"model-host adapter {self.name} could not run: executable not found: {executable!r}"
            )
        return resolved

    def _verify_executable(self, resolved: str) -> None:
        """Refuse to run when a pinned SHA-256 does not match the binary."""
        if self.executable_sha256 is None:
            return
        digest = hashlib.sha256()
        try:
            with open(resolved, "rb") as handle:
                for chunk in iter(lambda: handle.read(1 << 20), b""):
                    digest.update(chunk)
        except OSError as exc:
            raise AdapterError(
                f"model-host adapter {self.name} could not hash executable {resolved}: {exc}"
            ) from exc
        actual = digest.hexdigest()
        if actual != self.executable_sha256:
            raise AdapterError(
                f"model-host adapter {self.name} refused to run {resolved}: "
                f"sha256 {actual} does not match pinned {self.executable_sha256}"
            )

    def _child_environment(self) -> dict[str, str]:
        """Explicit allowlist environment; never the full parent environment."""
        child_env: dict[str, str] = {}
        for key in _SAFE_ENV_KEYS + self.inherit_env:
            value = os.environ.get(key)
            if value is not None:
                child_env[key] = value
        child_env.setdefault("PYTHONIOENCODING", "utf-8")
        child_env.update(self.extra_env)
        return child_env

    def _build_preexec_fn(self):
        """Return a preexec_fn applying rlimits, or None where unsupported."""
        if os.name != "posix" or _resource is None:
            return None
        res = _resource
        mapping = (
            ("cpu_seconds", getattr(res, "RLIMIT_CPU", None)),
            ("address_space_bytes", getattr(res, "RLIMIT_AS", None)),
            ("file_size_bytes", getattr(res, "RLIMIT_FSIZE", None)),
            ("open_files", getattr(res, "RLIMIT_NOFILE", None)),
            ("processes", getattr(res, "RLIMIT_NPROC", None)),
        )
        pairs = [
            (rlimit, self.resource_limits.get(key))
            for key, rlimit in mapping
            if rlimit is not None and self.resource_limits.get(key) is not None
        ]
        if not pairs:
            return None

        def _apply_limits() -> None:
            for rlimit, value in pairs:
                try:
                    _soft, hard = res.getrlimit(rlimit)
                    capped = value if hard == res.RLIM_INFINITY else min(value, hard)
                    res.setrlimit(rlimit, (capped, capped))
                except (OSError, ValueError):
                    # Never abort exec because one limit is unsupported here.
                    continue

        return _apply_limits

    @staticmethod
    def _terminate(proc: subprocess.Popen) -> None:
        """Kill the child's entire process group (POSIX) or the child."""
        try:
            if os.name == "posix" and hasattr(os, "killpg"):
                os.killpg(proc.pid, signal.SIGKILL)
            else:  # pragma: no cover - non-POSIX platforms
                proc.kill()
        except (ProcessLookupError, PermissionError, OSError):
            try:
                proc.kill()
            except OSError:
                pass

    def _communicate(
        self, proc: subprocess.Popen, input_bytes: bytes
    ) -> tuple[bytes, bytes, str]:
        """Stream stdin/stdout/stderr with hard caps enforced while reading.

        Returns ``(stdout, stderr, outcome)`` where outcome is one of
        ``completed``, ``stdout-limit``, ``stderr-limit``, ``timeout``.
        Peak buffered bytes never exceed the configured caps.
        """
        stdout_buf = bytearray()
        stderr_buf = bytearray()
        stdout_breach = threading.Event()
        stderr_breach = threading.Event()

        def _feed() -> None:
            try:
                proc.stdin.write(input_bytes)
                proc.stdin.close()
            except (BrokenPipeError, OSError):
                pass

        def _drain(stream, buf: bytearray, cap: int, breach: threading.Event) -> None:
            try:
                while True:
                    chunk = stream.read(_READ_CHUNK_BYTES)
                    if not chunk:
                        return
                    room = cap - len(buf)
                    if len(chunk) > room:
                        if room > 0:
                            buf.extend(chunk[:room])
                        breach.set()
                        return
                    buf.extend(chunk)
            except (OSError, ValueError):
                return

        feeder = threading.Thread(target=_feed, daemon=True)
        readers = (
            threading.Thread(
                target=_drain,
                args=(proc.stdout, stdout_buf, self.max_stdout_bytes, stdout_breach),
                daemon=True,
            ),
            threading.Thread(
                target=_drain,
                args=(proc.stderr, stderr_buf, self.max_stderr_bytes, stderr_breach),
                daemon=True,
            ),
        )
        feeder.start()
        for reader in readers:
            reader.start()

        deadline = time.monotonic() + self.timeout_seconds
        outcome = "completed"
        while True:
            if stdout_breach.is_set():
                outcome = "stdout-limit"
                break
            if stderr_breach.is_set():
                outcome = "stderr-limit"
                break
            readers_done = all(not reader.is_alive() for reader in readers)
            if readers_done and proc.poll() is not None:
                break
            if time.monotonic() >= deadline:
                outcome = "timeout"
                break
            time.sleep(0.01)

        if outcome != "completed":
            self._terminate(proc)
        for worker in (feeder, *readers):
            worker.join(timeout=5.0)
        try:
            proc.wait(timeout=10.0)
        except subprocess.TimeoutExpired:  # pragma: no cover - defensive
            proc.kill()
            proc.wait(timeout=5.0)
        finally:
            for stream in (proc.stdin, proc.stdout, proc.stderr):
                if stream is not None:
                    try:
                        stream.close()
                    except OSError:
                        pass
        return bytes(stdout_buf), bytes(stderr_buf), outcome

    # -- protocol ------------------------------------------------------------

    def _invoke(self, payload: dict) -> dict:
        executable = self._resolved_executable()
        self._verify_executable(executable)
        argv = (executable, *self.command[1:])
        child_env = self._child_environment()

        temp_cwd: str | None = None
        if self.cwd is not None:
            cwd = os.fspath(self.cwd)
            if not os.path.isdir(cwd):
                raise AdapterError(
                    f"model-host adapter {self.name} could not run: cwd does not exist: {cwd}"
                )
        else:
            temp_cwd = tempfile.mkdtemp(prefix="lpos-model-host-")
            cwd = temp_cwd

        popen_kwargs: dict = {}
        if os.name == "posix":
            popen_kwargs["start_new_session"] = True
            preexec_fn = self._build_preexec_fn()
            if preexec_fn is not None:
                popen_kwargs["preexec_fn"] = preexec_fn

        try:
            try:
                proc = subprocess.Popen(
                    argv,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    shell=False,
                    env=child_env,
                    cwd=cwd,
                    **popen_kwargs,
                )
            except OSError as exc:
                raise AdapterError(f"model-host adapter {self.name} could not run: {exc}") from exc
            input_bytes = canonical_json(payload).encode("utf-8")
            stdout_bytes, stderr_bytes, outcome = self._communicate(proc, input_bytes)
        finally:
            if temp_cwd is not None:
                shutil.rmtree(temp_cwd, ignore_errors=True)

        self._last_stdout_bytes_captured = len(stdout_bytes)
        if outcome == "stdout-limit":
            raise AdapterError(f"model-host adapter {self.name} exceeded stdout limit")
        if outcome == "stderr-limit":
            raise AdapterError(f"model-host adapter {self.name} exceeded stderr limit")
        if outcome == "timeout":
            raise AdapterError(
                f"model-host adapter {self.name} could not run: "
                f"timed out after {self.timeout_seconds} seconds"
            )
        if proc.returncode != 0:
            stderr_text = stderr_bytes.decode("utf-8", errors="replace")[-4000:].strip()
            raise AdapterError(
                f"model-host adapter {self.name} exited {proc.returncode}: {stderr_text or 'no stderr'}"
            )
        if len(stdout_bytes) > self.max_stdout_bytes:  # pragma: no cover - capped during read
            raise AdapterError(f"model-host adapter {self.name} exceeded stdout limit")
        try:
            value = json.loads(stdout_bytes.decode("utf-8", errors="replace"))
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
