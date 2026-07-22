"""Pluggable connector health checks.

Every check is a callable ``(entry, timeout) -> CheckResult``.  Checks are
looked up first by the entry's explicit ``check.type`` and, failing that, by a
per-kind default.  A check that cannot even be attempted (missing host, url,
command, ...) raises :class:`CheckNotConfigured`, which the runner maps to the
``unknown`` status rather than ``offline``.

The module uses only the standard library and never imports anything at check
time that would require network access just to load.  Tests inject fake
registries and fake ``sleep`` callables, so nothing here is exercised against
the real network in CI.
"""

from __future__ import annotations

import os
import socket
import ssl
import subprocess
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from dataclasses import dataclass
from typing import Any

DEFAULT_TIMEOUT = 15.0
RETRY_DELAY = 5.0


class CheckNotConfigured(Exception):
    """The entry does not carry enough configuration to run its check."""


@dataclass(frozen=True, slots=True)
class CheckResult:
    ok: bool
    latency_ms: int
    error: str = ""


CheckFunction = Callable[[Mapping[str, Any], float], CheckResult]


def _spec(entry: Mapping[str, Any]) -> Mapping[str, Any]:
    check = entry.get("check")
    return check if isinstance(check, Mapping) else {}


def _require(spec: Mapping[str, Any], *names: str) -> list[Any]:
    values = []
    for name in names:
        value = spec.get(name)
        if value in (None, ""):
            raise CheckNotConfigured(f"check is missing required field: {name}")
        values.append(value)
    return values


def _result(started: float, ok: bool, error: str = "") -> CheckResult:
    return CheckResult(ok=ok, latency_ms=int((time.monotonic() - started) * 1000), error=error)


def _http_get(url: str, timeout: float, headers: Mapping[str, str] | None = None) -> CheckResult:
    started = time.monotonic()
    request = urllib.request.Request(url, headers=dict(headers or {}), method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
            status = getattr(response, "status", 200)
        if status < 400:
            return _result(started, True)
        return _result(started, False, f"HTTP {status}")
    except urllib.error.HTTPError as exc:
        return _result(started, False, f"HTTP {exc.code}: {exc.reason}")
    except Exception as exc:  # URLError, socket errors, ssl errors, ...
        return _result(started, False, f"{type(exc).__name__}: {exc}")


def check_http_health(entry: Mapping[str, Any], timeout: float) -> CheckResult:
    spec = _spec(entry)
    (url,) = _require(spec, "url")
    return _http_get(str(url), timeout)


def check_tcp(entry: Mapping[str, Any], timeout: float) -> CheckResult:
    spec = _spec(entry)
    host, port = _require(spec, "host", "port")
    started = time.monotonic()
    try:
        with socket.create_connection((str(host), int(port)), timeout=timeout):
            pass
        return _result(started, True)
    except Exception as exc:
        return _result(started, False, f"{type(exc).__name__}: {exc}")


def check_smtp(entry: Mapping[str, Any], timeout: float) -> CheckResult:
    import smtplib

    spec = _spec(entry)
    (host,) = _require(spec, "host")
    port = int(spec.get("port", 587))
    started = time.monotonic()
    try:
        with smtplib.SMTP(str(host), port, timeout=timeout) as client:
            if spec.get("starttls"):
                client.starttls(context=ssl.create_default_context())
            code, _ = client.noop()
        if 200 <= code < 400:
            return _result(started, True)
        return _result(started, False, f"SMTP NOOP returned {code}")
    except Exception as exc:
        return _result(started, False, f"{type(exc).__name__}: {exc}")


def check_imap(entry: Mapping[str, Any], timeout: float) -> CheckResult:
    import imaplib

    spec = _spec(entry)
    (host,) = _require(spec, "host")
    use_ssl = bool(spec.get("ssl", True))
    port = int(spec.get("port", 993 if use_ssl else 143))
    started = time.monotonic()
    try:
        if use_ssl:
            client = imaplib.IMAP4_SSL(
                str(host), port, timeout=timeout, ssl_context=ssl.create_default_context()
            )
        else:
            client = imaplib.IMAP4(str(host), port, timeout=timeout)
        try:
            client.noop()
        finally:
            try:
                client.logout()
            except Exception:
                pass
        return _result(started, True)
    except Exception as exc:
        return _result(started, False, f"{type(exc).__name__}: {exc}")


def _github_token(spec: Mapping[str, Any]) -> str:
    token_env = spec.get("token_env")
    if token_env:
        value = os.environ.get(str(token_env), "")
        if value:
            return value
    token_file = spec.get("token_file")
    if token_file:
        try:
            return open(os.path.expanduser(str(token_file)), encoding="utf-8").read().strip()
        except OSError:
            return ""
    return os.environ.get("GITHUB_TOKEN", "")


def check_github_api(entry: Mapping[str, Any], timeout: float) -> CheckResult:
    spec = _spec(entry)
    url = str(spec.get("url") or "https://api.github.com/rate_limit")
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "lpos-monitor"}
    token = _github_token(spec)
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return _http_get(url, timeout, headers=headers)


def check_mcp_ping(entry: Mapping[str, Any], timeout: float) -> CheckResult:
    spec = _spec(entry)
    if spec.get("url"):
        return _http_get(str(spec["url"]), timeout)
    if spec.get("host") and spec.get("port"):
        return check_tcp(entry, timeout)
    raise CheckNotConfigured("mcp_ping needs either url or host+port")


def check_command(entry: Mapping[str, Any], timeout: float) -> CheckResult:
    spec = _spec(entry)
    (command,) = _require(spec, "command")
    started = time.monotonic()
    try:
        completed = subprocess.run(  # noqa: S602
            command,
            shell=isinstance(command, str),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return _result(started, False, f"command timed out after {timeout:g}s")
    except Exception as exc:
        return _result(started, False, f"{type(exc).__name__}: {exc}")
    if completed.returncode == 0:
        return _result(started, True)
    detail = (completed.stderr or completed.stdout or "").strip().splitlines()
    tail = detail[-1] if detail else ""
    return _result(started, False, f"exit {completed.returncode}" + (f": {tail}" if tail else ""))


#: Registry mapping check type (or kind default) -> check callable.  Extend by
#: adding an entry here or passing a custom registry into :func:`run_check`.
CHECKS: dict[str, CheckFunction] = {
    "http_health": check_http_health,
    "tcp": check_tcp,
    "smtp": check_smtp,
    "imap": check_imap,
    "github_api": check_github_api,
    "mcp_ping": check_mcp_ping,
    "command": check_command,
}

#: Default check type per connector kind, used when the entry has no explicit
#: ``check.type``.
DEFAULT_CHECK_FOR_KIND: dict[str, str] = {
    "email": "smtp",
    "vcs": "github_api",
    "cloud": "http_health",
    "mcp": "mcp_ping",
    "self_built": "http_health",
}


def resolve_check(
    entry: Mapping[str, Any], registry: Mapping[str, CheckFunction] | None = None
) -> CheckFunction | None:
    """Return the check callable for an entry, or None if none applies."""

    reg = CHECKS if registry is None else registry
    spec = _spec(entry)
    check_type = spec.get("type")
    if check_type:
        return reg.get(str(check_type))
    default = DEFAULT_CHECK_FOR_KIND.get(str(entry.get("kind", "")))
    if default is None:
        return None
    return reg.get(default)


def _attempt(fn: CheckFunction, entry: Mapping[str, Any], timeout: float) -> CheckResult:
    """Run one check attempt, enforcing the timeout even on a hung callable."""

    started = time.monotonic()
    pool = ThreadPoolExecutor(max_workers=1)
    future = pool.submit(fn, entry, timeout)
    try:
        # Checks enforce their own socket-level timeouts; this outer bound is a
        # backstop against a hung callable, with a small proportional grace.
        value = future.result(timeout=timeout + min(1.0, timeout))
    except FutureTimeoutError:
        future.cancel()
        return CheckResult(ok=False, latency_ms=int(timeout * 1000), error=f"timeout after {timeout:g}s")
    except CheckNotConfigured:
        raise
    except Exception as exc:
        return _result(started, False, f"{type(exc).__name__}: {exc}")
    finally:
        pool.shutdown(wait=False, cancel_futures=True)
    if isinstance(value, CheckResult):
        return value
    if isinstance(value, bool):  # convenience for injected fakes
        return _result(started, value, "" if value else "check returned False")
    return _result(started, False, f"check returned unexpected value: {value!r}")


def run_check(
    entry: Mapping[str, Any],
    *,
    timeout: float = DEFAULT_TIMEOUT,
    retry_delay: float = RETRY_DELAY,
    retries: int = 1,
    registry: Mapping[str, CheckFunction] | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> CheckResult | None:
    """Run an entry's check with one retry before declaring it offline.

    Returns None when no check can be resolved or configured for the entry
    (status ``unknown``).  Never raises for a failing service.
    """

    fn = resolve_check(entry, registry)
    if fn is None:
        return None
    last: CheckResult | None = None
    for attempt in range(retries + 1):
        if attempt:
            sleep(retry_delay)
        try:
            last = _attempt(fn, entry, timeout)
        except CheckNotConfigured as exc:
            return None if attempt == 0 else CheckResult(False, 0, str(exc))
        if last.ok:
            return last
    return last


def run_checks(
    entries: list[Mapping[str, Any]],
    *,
    timeout: float = DEFAULT_TIMEOUT,
    retry_delay: float = RETRY_DELAY,
    registry: Mapping[str, CheckFunction] | None = None,
    sleep: Callable[[float], None] = time.sleep,
    max_workers: int = 8,
) -> dict[str, CheckResult | None]:
    """Run all entries' checks concurrently.  Returns {entry id: result}."""

    if not entries:
        return {}
    results: dict[str, CheckResult | None] = {}
    workers = max(1, min(max_workers, len(entries)))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(
                run_check,
                entry,
                timeout=timeout,
                retry_delay=retry_delay,
                registry=registry,
                sleep=sleep,
            ): str(entry.get("id", ""))
            for entry in entries
        }
        for future, entry_id in futures.items():
            try:
                results[entry_id] = future.result()
            except Exception as exc:  # defensive: a check must never sink the audit
                results[entry_id] = CheckResult(False, 0, f"{type(exc).__name__}: {exc}")
    return results
