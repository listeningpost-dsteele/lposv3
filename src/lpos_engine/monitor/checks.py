"""Pluggable connector health checks.

Every check is a callable ``(entry, timeout) -> CheckResult``.  Checks are
looked up first by the entry's explicit ``check.type`` and, failing that, by a
per-kind default.  A check that cannot even be attempted (missing host, url,
command, ...) raises :class:`CheckNotConfigured`, which the runner maps to the
``unknown`` status rather than ``offline``.

Security boundary (audit findings LPOS-03 / LPOS-04):

- :func:`run_check` resolves every entry through
  :mod:`lpos_engine.monitor.approved` first.  Executable checks only run from
  admin-approved templates; entries carrying their own executable definition
  are reported ``unknown`` with evidence ``unapproved check definition``.
- ``command`` checks never use a shell: argv lists only, absolute executable
  path restricted to /usr, /bin, /sbin, /opt or ``<root>/monitor/approved/``,
  minimal environment, new session with process-group kill on timeout, and
  output capped at 64 KiB.
- All URL/host checks validate scheme and the *resolved* addresses: loopback,
  link-local, multicast, unspecified, private ranges, and the metadata host
  are refused unless the admin template sets ``private_network_approved``.
  HTTP redirects are always refused.
- The GitHub token is only ever attached to ``https://api.github.com``; a
  ``token_file`` must resolve (symlinks followed) inside
  ``<root>/monitor/secrets/``; token values are redacted from error strings.

The module uses only the standard library and never imports anything at check
time that would require network access just to load.  Tests inject fake
registries and fake ``sleep`` callables, so nothing here is exercised against
the real network in CI.
"""

from __future__ import annotations

import ipaddress
import os
import signal
import socket
import ssl
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Mapping
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import approved as approved_module
from .inventory import hermes_root

DEFAULT_TIMEOUT = 15.0
RETRY_DELAY = 5.0

#: Hard cap on captured stdout/stderr of command checks (LPOS-03).
OUTPUT_CAP_BYTES = 64 * 1024

#: Prefixes an approved command-check executable may resolve into, plus the
#: per-root ``<root>/monitor/approved/`` directory (see :func:`_exec_allowed`).
EXEC_PREFIXES = ("/usr", "/bin", "/sbin", "/opt")

#: The only origin ever allowed to receive the GitHub token (LPOS-04).
GITHUB_ORIGIN = ("https", "api.github.com", 443)

_REDIRECT_CODES = (301, 302, 303, 307, 308)


class CheckNotConfigured(Exception):
    """The entry does not carry enough configuration to run its check."""


@dataclass(frozen=True, slots=True)
class CheckResult:
    ok: bool
    latency_ms: int
    error: str = ""
    #: When True the runner reports status ``unknown`` (with ``error`` as the
    #: evidence string) instead of ``offline`` — used for refused/unapproved
    #: definitions that were never attempted.
    unknown: bool = False


CheckFunction = Callable[[Mapping[str, Any], float], CheckResult]


def _spec(entry: Mapping[str, Any]) -> Mapping[str, Any]:
    check = entry.get("check")
    return check if isinstance(check, Mapping) else {}


def _spec_root(spec: Mapping[str, Any]) -> Path:
    value = spec.get("_hermes_root")
    return Path(str(value)) if value else hermes_root()


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


def _redact(text: str, secret: str) -> str:
    """Never echo credential material in errors, state, status, or alerts."""

    if secret and secret in text:
        return text.replace(secret, "[REDACTED]")
    return text


# --------------------------------------------------------------- egress policy


def _blocked_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    return (
        ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_unspecified
        or ip.is_private
        or ip.is_reserved
        or str(ip) == "169.254.169.254"
    )


def _validate_host(host: str, *, allow_private: bool) -> str | None:
    """Resolve ``host`` and refuse blocked address ranges (LPOS-04 SSRF).

    Returns an error string, or None when the host may be contacted.
    ``allow_private`` is only ever True for admin-approved templates that set
    ``private_network_approved`` in approved-checks.json.
    """

    if allow_private:
        return None
    try:
        infos = socket.getaddrinfo(str(host), None, type=socket.SOCK_STREAM)
    except OSError:
        return f"DNS resolution failed for {host}"
    if not infos:
        return f"DNS resolution failed for {host}"
    for info in infos:
        address = str(info[4][0]).split("%", 1)[0]
        try:
            ip = ipaddress.ip_address(address)
        except ValueError:
            return f"refused: unparseable resolved address for {host}"
        if _blocked_ip(ip):
            return f"refused: {host} resolves to a blocked address range ({ip})"
    return None


def _validate_url(url: str, *, allow_private: bool) -> str | None:
    try:
        parsed = urllib.parse.urlsplit(url)
    except ValueError:
        return "refused: unparseable URL"
    if parsed.scheme not in ("http", "https"):
        return f"refused: scheme {parsed.scheme or '(none)'!s} not allowed"
    if "@" in parsed.netloc:
        return "refused: userinfo in URL"
    if not parsed.hostname:
        return "refused: URL has no host"
    try:
        parsed.port  # noqa: B018 - property access validates the port
    except ValueError:
        return "refused: invalid port in URL"
    return _validate_host(parsed.hostname, allow_private=allow_private)


def _allow_private(spec: Mapping[str, Any]) -> bool:
    # Only survives resolve_execution_entry when set by an approved template.
    return bool(spec.get("private_network_approved"))


class _RefuseRedirects(urllib.request.HTTPRedirectHandler):
    """Redirects are never followed; the 3xx surfaces as an HTTPError."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D102
        return None


_OPENER = urllib.request.build_opener(_RefuseRedirects())


def _urlopen(request: urllib.request.Request, timeout: float):
    """Single egress point for HTTP checks; tests monkeypatch this."""

    return _OPENER.open(request, timeout=timeout)  # noqa: S310


def _http_get(
    url: str,
    timeout: float,
    headers: Mapping[str, str] | None = None,
    *,
    allow_private: bool = False,
) -> CheckResult:
    started = time.monotonic()
    refusal = _validate_url(url, allow_private=allow_private)
    if refusal:
        return _result(started, False, refusal)
    request = urllib.request.Request(url, headers=dict(headers or {}), method="GET")
    try:
        with _urlopen(request, timeout) as response:
            status = getattr(response, "status", 200)
        if status in _REDIRECT_CODES:
            return _result(started, False, "redirect refused")
        if status < 400:
            return _result(started, True)
        return _result(started, False, f"HTTP {status}")
    except urllib.error.HTTPError as exc:
        if exc.code in _REDIRECT_CODES:
            return _result(started, False, "redirect refused")
        return _result(started, False, f"HTTP {exc.code}: {exc.reason}")
    except Exception as exc:  # URLError, socket errors, ssl errors, ...
        return _result(started, False, f"{type(exc).__name__}: {exc}")


def check_http_health(entry: Mapping[str, Any], timeout: float) -> CheckResult:
    spec = _spec(entry)
    (url,) = _require(spec, "url")
    return _http_get(str(url), timeout, allow_private=_allow_private(spec))


def check_tcp(entry: Mapping[str, Any], timeout: float) -> CheckResult:
    spec = _spec(entry)
    host, port = _require(spec, "host", "port")
    started = time.monotonic()
    refusal = _validate_host(str(host), allow_private=_allow_private(spec))
    if refusal:
        return _result(started, False, refusal)
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
    refusal = _validate_host(str(host), allow_private=_allow_private(spec))
    if refusal:
        return _result(started, False, refusal)
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
    refusal = _validate_host(str(host), allow_private=_allow_private(spec))
    if refusal:
        return _result(started, False, refusal)
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


# ------------------------------------------------------------------ github_api


def secrets_dir(root: Path | None = None) -> Path:
    """The only directory ``token_file`` may resolve into (LPOS-04)."""

    base = Path(root) if root is not None else hermes_root()
    return base / "monitor" / "secrets"


class _TokenRefused(Exception):
    """token_file is outside the approved secrets directory."""


def _github_token(spec: Mapping[str, Any]) -> str:
    """Resolve the GitHub token from env or the approved secrets directory.

    Raises :class:`_TokenRefused` — before any network activity — when a
    configured ``token_file`` does not resolve (symlinks followed) inside
    ``<root>/monitor/secrets/``.
    """

    token_env = spec.get("token_env")
    if token_env:
        value = os.environ.get(str(token_env), "")
        if value:
            return value
    token_file = spec.get("token_file")
    if token_file:
        allowed = os.path.realpath(secrets_dir(_spec_root(spec)))
        candidate = os.path.realpath(os.path.expanduser(str(token_file)))
        if os.path.commonpath([allowed, candidate]) != allowed or candidate == allowed:
            raise _TokenRefused(
                "refused: token_file must resolve inside <hermes>/monitor/secrets/"
            )
        try:
            return open(candidate, encoding="utf-8").read().strip()
        except OSError:
            return ""
    return os.environ.get("GITHUB_TOKEN", "")


def _is_github_origin(url: str) -> bool:
    try:
        parsed = urllib.parse.urlsplit(url)
        port = parsed.port
    except ValueError:
        return False
    scheme, host, default_port = GITHUB_ORIGIN
    return (
        parsed.scheme == scheme
        and parsed.hostname == host
        and (port is None or port == default_port)
        and "@" not in parsed.netloc
    )


def check_github_api(entry: Mapping[str, Any], timeout: float) -> CheckResult:
    spec = _spec(entry)
    url = str(spec.get("url") or "https://api.github.com/rate_limit")
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "lpos-monitor"}
    started = time.monotonic()
    try:
        token = _github_token(spec)
    except _TokenRefused as exc:
        return _result(started, False, str(exc))
    if token:
        # The credential is bound to the GitHub API origin: never attach it to
        # any other scheme/host/port, and fail loudly instead of degrading to
        # an unauthenticated probe of an attacker-chosen URL.
        if not _is_github_origin(url):
            return _result(started, False, "refused: token bound to api.github.com")
        headers["Authorization"] = f"Bearer {token}"
    result = _http_get(url, timeout, headers=headers, allow_private=False)
    if token and token in result.error:
        result = CheckResult(
            ok=result.ok,
            latency_ms=result.latency_ms,
            error=_redact(result.error, token),
            unknown=result.unknown,
        )
    return result


def check_mcp_ping(entry: Mapping[str, Any], timeout: float) -> CheckResult:
    spec = _spec(entry)
    if spec.get("url"):
        return _http_get(str(spec["url"]), timeout, allow_private=_allow_private(spec))
    if spec.get("host") and spec.get("port"):
        return check_tcp(entry, timeout)
    raise CheckNotConfigured("mcp_ping needs either url or host+port")


# --------------------------------------------------------------- command check


def approved_exec_dir(root: Path | None = None) -> Path:
    """Admin-owned directory for custom check executables."""

    base = Path(root) if root is not None else hermes_root()
    return base / "monitor" / "approved"


def _exec_allowed(executable: str, root: Path) -> str | None:
    """Validate the executable path policy; return an error string or None."""

    if not os.path.isabs(executable):
        return "refused: command executable must be an absolute path"
    if not os.path.isfile(executable):
        return "refused: command executable does not exist"
    real = os.path.realpath(executable)
    allowed_roots = [os.path.realpath(prefix) for prefix in EXEC_PREFIXES]
    allowed_roots.append(os.path.realpath(approved_exec_dir(root)))
    for prefix in allowed_roots:
        try:
            if os.path.commonpath([prefix, real]) == prefix:
                return None
        except ValueError:
            continue
    return "refused: command executable resolves outside the allowed directories"


def _cap(text: str) -> str:
    return text if len(text) <= OUTPUT_CAP_BYTES else text[:OUTPUT_CAP_BYTES]


def check_command(entry: Mapping[str, Any], timeout: float) -> CheckResult:
    """Run an admin-approved argv command.  Never a shell (LPOS-03).

    Only reachable through an approved template (``_approved`` marker set by
    :func:`lpos_engine.monitor.approved.resolve_execution_entry`); shell
    strings are refused unconditionally.
    """

    spec = _spec(entry)
    started = time.monotonic()
    if not spec.get("_approved"):
        raise CheckNotConfigured("command checks require an approved template")
    argv = spec.get("argv", spec.get("command"))
    if isinstance(argv, str):
        return _result(started, False, "refused: shell command strings are not supported")
    if (
        not isinstance(argv, list)
        or not argv
        or not all(isinstance(item, str) for item in argv)
    ):
        raise CheckNotConfigured("command check needs argv: a non-empty list of strings")
    refusal = _exec_allowed(argv[0], _spec_root(spec))
    if refusal:
        return _result(started, False, refusal)
    env = {
        "PATH": "/usr/bin:/bin",
        "LANG": os.environ.get("LANG", "C.UTF-8"),
    }
    try:
        process = subprocess.Popen(  # noqa: S603 - argv list, no shell, vetted path
            argv,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            start_new_session=True,
        )
    except Exception as exc:
        return _result(started, False, f"{type(exc).__name__}: {exc}")
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        try:  # kill the whole session/process group, not just the child
            os.killpg(process.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError, OSError):
            process.kill()
        try:
            process.communicate(timeout=5)
        except Exception:
            pass
        return _result(started, False, f"command timed out after {timeout:g}s")
    stdout, stderr = _cap(stdout or ""), _cap(stderr or "")
    if process.returncode == 0:
        return _result(started, True)
    detail = (stderr or stdout).strip().splitlines()
    tail = detail[-1] if detail else ""
    return _result(
        started, False, f"exit {process.returncode}" + (f": {tail[:200]}" if tail else "")
    )


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
    root: Path | None = None,
) -> CheckResult | None:
    """Run an entry's check with one retry before declaring it offline.

    Every entry passes through the approval boundary first
    (:func:`lpos_engine.monitor.approved.resolve_execution_entry`): entries
    carrying unapproved executable definitions return a ``CheckResult`` with
    ``unknown=True`` and are never attempted.  Returns None when no check can
    be resolved or configured for the entry (status ``unknown``).  Never
    raises for a failing service.
    """

    effective, refusal = approved_module.resolve_execution_entry(entry, root)
    if refusal is not None or effective is None:
        return CheckResult(ok=False, latency_ms=0, error=refusal or "", unknown=True)
    fn = resolve_check(effective, registry)
    if fn is None:
        return None
    last: CheckResult | None = None
    for attempt in range(retries + 1):
        if attempt:
            sleep(retry_delay)
        try:
            last = _attempt(fn, effective, timeout)
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
    root: Path | None = None,
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
                root=root,
            ): str(entry.get("id", ""))
            for entry in entries
        }
        for future, entry_id in futures.items():
            try:
                results[entry_id] = future.result()
            except Exception as exc:  # defensive: a check must never sink the audit
                results[entry_id] = CheckResult(False, 0, f"{type(exc).__name__}: {exc}")
    return results
