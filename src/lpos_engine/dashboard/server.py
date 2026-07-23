"""Localhost-only stdlib HTTP server and JSON API for the Hermes dashboard.

The API surface:

- ``GET  /``                              the single-page UI (token injected)
- ``GET  /api/projects``                  all projects with computed buckets
- ``POST /api/projects/<id>/snooze``      body ``{"until": "<ISO 8601>"}``
- ``POST /api/projects/<id>/archive``
- ``POST /api/projects/<id>/restore``     body ``{"bucket": "active"|"research"}``
- ``POST /api/projects/<id>/move``        body ``{"bucket": ...}``
- ``POST /api/open``                      body ``{"path": ...}`` (inside approved roots only)
- ``GET  /api/search?q=``                 project-name and file-name search
- ``GET  /api/health``                    contents of ``<root>/monitor/status.json`` or null

Security model (LPOS-06):

- Every ``/api`` route — GET and POST — requires the per-run session token,
  sent as ``Authorization: Bearer <token>`` or ``X-LPOS-Token``.  The token is
  generated at server start and written to ``<root>/dashboard/token`` (0600,
  atomic).  ``GET /`` serves the UI with the token injected server-side.
- Every request must carry a Host header matching the bound host:port
  (loopback aliases accepted when bound to loopback) or it is rejected with
  400 — this defeats DNS rebinding.
- State-changing requests with a foreign Origin header are rejected with 403;
  header-based auth already makes cross-site form posts unauthenticatable.
- POST bodies must be ``application/json`` and at most 1 MB; query strings are
  length-capped.
- Binding to a non-loopback host is refused unless
  ``LPOS_DASHBOARD_ALLOW_NONLOOPBACK=1`` is set, and then loudly warned about.
- Hardening headers are attached to every response; 500s carry a generic body.

Application logic lives on :class:`DashboardApp` so tests can drive it without
sockets; the request handler is a thin shim.
"""

from __future__ import annotations

import argparse
import hmac
import ipaddress
import json
import os
import platform
import secrets
import subprocess
import sys
import tempfile
import traceback
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable
from urllib.parse import parse_qs, unquote, urlsplit

from . import scanner, state as state_mod
from .state import DashboardState, WORKING_BUCKETS, iso, parse_iso, utcnow
from .ui import PAGE_HTML, TOKEN_PLACEHOLDER

DEFAULT_PORT = 7373
DEFAULT_HOST = "127.0.0.1"

#: Maximum accepted POST body, in bytes (LPOS-06).
MAX_BODY_BYTES = 1_000_000

#: Maximum accepted query-string length, in characters (LPOS-06).
MAX_QUERY_LENGTH = 2048

#: Environment override that permits a non-loopback bind (LPOS-06).
NONLOOPBACK_ENV = "LPOS_DASHBOARD_ALLOW_NONLOOPBACK"

#: File under ``<root>/dashboard/`` holding the current session token.
TOKEN_FILE_NAME = "token"

#: Hardening headers attached to every response (LPOS-06).
SECURITY_HEADERS: tuple[tuple[str, str], ...] = (
    (
        "Content-Security-Policy",
        "default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; "
        "connect-src 'self'; img-src 'self' data:",
    ),
    ("X-Frame-Options", "DENY"),
    ("X-Content-Type-Options", "nosniff"),
    ("Referrer-Policy", "no-referrer"),
    ("Cache-Control", "no-store"),
)


class DashboardError(Exception):
    """An API-level error carrying an HTTP status code."""

    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


def is_loopback_host(host: str) -> bool:
    """Whether a bind/host string refers to the loopback interface."""
    bare = host.strip().strip("[]").lower()
    if bare == "localhost":
        return True
    try:
        return ipaddress.ip_address(bare).is_loopback
    except ValueError:
        return False


def render_page(token: str) -> str:
    """The UI page with the session token injected into the inline script."""
    return PAGE_HTML.replace(TOKEN_PLACEHOLDER, token)


def _write_token_file(path: Path, token: str) -> None:
    """Atomically write the token file with 0600 permissions."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    try:
        if hasattr(os, "fchmod"):
            os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(token + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def open_folder_command(path: str) -> list[str]:
    """The platform-detected command that opens ``path`` in the file manager."""
    system = platform.system()
    if system == "Darwin":
        return ["open", path]
    if system == "Windows":
        return ["explorer", path]
    return ["xdg-open", path]


def _default_opener(command: list[str]) -> None:
    subprocess.Popen(
        command,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
    )


class DashboardApp:
    """All dashboard behavior, independent of the HTTP transport."""

    def __init__(
        self,
        root: Path | None = None,
        opener: Callable[[list[str]], None] | None = None,
    ) -> None:
        self.root = scanner.hermes_root(root)
        self.state_file = state_mod.state_path(self.root)
        self.opener = opener or _default_opener

    # -- helpers ----------------------------------------------------------

    def _load_state(self) -> DashboardState:
        return DashboardState.load(self.state_file)

    def _annotated_projects(self, now: datetime | None = None) -> list[dict[str, Any]]:
        state = self._load_state()
        moment = now or utcnow()
        projects = scanner.scan_projects(self.root)
        for project in projects:
            effective = state.effective(project["id"], project.get("type", "active"), moment)
            project.update(effective)
        return projects

    def _require_known(self, project_id: str) -> None:
        known = {project["id"] for project in scanner.scan_projects(self.root)}
        if project_id not in known:
            raise DashboardError(404, f"unknown project: {project_id}")

    def _default_bucket(self, project_id: str) -> str:
        for project in scanner.scan_projects(self.root):
            if project["id"] == project_id:
                return project.get("type", "active")
        return "active"

    def _mutate(self, project_id: str, fn: Callable[[DashboardState], None]) -> dict[str, Any]:
        self._require_known(project_id)
        state = self._load_state()
        fn(state)
        state.save(self.state_file)
        effective = state.effective(project_id, self._default_bucket(project_id))
        return {"ok": True, "id": project_id, **effective}

    # -- API operations ---------------------------------------------------

    def projects(self, now: datetime | None = None) -> dict[str, Any]:
        return {
            "root": str(self.root),
            "generated_at": iso(now or utcnow()),
            "projects": self._annotated_projects(now),
        }

    def snooze(self, project_id: str, until_raw: Any) -> dict[str, Any]:
        until = parse_iso(until_raw)
        if until is None:
            raise DashboardError(400, "snooze requires an ISO 8601 'until' timestamp")
        default = self._default_bucket(project_id)
        return self._mutate(project_id, lambda s: s.snooze(project_id, until, default))

    def archive(self, project_id: str) -> dict[str, Any]:
        return self._mutate(project_id, lambda s: s.archive(project_id))

    def restore(self, project_id: str, bucket: Any) -> dict[str, Any]:
        target = bucket if isinstance(bucket, str) and bucket else "active"
        if target not in WORKING_BUCKETS:
            raise DashboardError(400, f"restore bucket must be one of {list(WORKING_BUCKETS)}")
        return self._mutate(project_id, lambda s: s.restore(project_id, target))

    def move(self, project_id: str, bucket: Any) -> dict[str, Any]:
        if not isinstance(bucket, str) or bucket not in ("active", "research", "archived"):
            raise DashboardError(400, "move bucket must be active, research, or archived")
        return self._mutate(project_id, lambda s: s.move(project_id, bucket))

    def open_path(self, raw_path: Any) -> dict[str, Any]:
        if not isinstance(raw_path, str) or not raw_path.strip():
            raise DashboardError(400, "open requires a 'path'")
        candidate = Path(raw_path.strip()).expanduser()
        try:
            resolved = candidate.resolve()
        except (OSError, RuntimeError) as exc:
            raise DashboardError(400, "unresolvable path") from exc
        # LPOS-09: resolve symlinks first, then require containment inside an
        # approved root before anything is handed to the OS opener.
        allowed = scanner.containment_roots(self.root)
        if not allowed or not scanner.is_contained(resolved, allowed):
            raise DashboardError(403, "refusing to open a path outside the approved roots")
        if not resolved.exists():
            raise DashboardError(404, "path does not exist")
        target = resolved if resolved.is_dir() else resolved.parent
        command = open_folder_command(str(target))
        try:
            self.opener(command)
        except OSError as exc:
            raise DashboardError(500, "could not launch file manager") from exc
        return {"ok": True, "opened": str(target), "command": command}

    def search(self, query: str) -> dict[str, Any]:
        result = scanner.search(self.root, query, projects=self._annotated_projects())
        return result

    def health(self) -> dict[str, Any]:
        status = self.root / "monitor" / "status.json"
        data = None
        if status.is_file():
            try:
                loaded = json.loads(status.read_text(encoding="utf-8"))
            except (OSError, ValueError, UnicodeDecodeError):
                loaded = None
            if isinstance(loaded, dict):
                data = loaded
        return {"health": data}


class DashboardHandler(BaseHTTPRequestHandler):
    """Thin HTTP shim over :class:`DashboardApp`."""

    server_version = "LPOSDashboard/1.0"
    protocol_version = "HTTP/1.1"

    @property
    def app(self) -> DashboardApp:
        return self.server.app  # type: ignore[attr-defined]

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        if getattr(self.server, "verbose", False):
            super().log_message(format, *args)

    # -- responses --------------------------------------------------------

    def _send_security_headers(self) -> None:
        for name, value in SECURITY_HEADERS:
            self.send_header(name, value)

    def _send_json(self, status: int, payload: Any) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._send_security_headers()
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, html: str) -> None:
        body = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._send_security_headers()
        self.end_headers()
        self.wfile.write(body)

    def _reject(self, status: int, message: str) -> None:
        # The request body (if any) is not read on rejection, so the
        # connection cannot be safely reused.
        self.close_connection = True
        self._send_json(status, {"error": message})

    # -- security gates (LPOS-06) -----------------------------------------

    def _host_ok(self) -> bool:
        host = (self.headers.get("Host") or "").strip().lower()
        return host in getattr(self.server, "allowed_hosts", set())

    def _token_ok(self) -> bool:
        expected = getattr(self.server, "token", None)
        if not expected:
            return False
        supplied = self.headers.get("X-LPOS-Token")
        if supplied is None:
            authorization = self.headers.get("Authorization") or ""
            if authorization.startswith("Bearer "):
                supplied = authorization[len("Bearer ") :].strip()
        if not supplied:
            return False
        return hmac.compare_digest(supplied.encode("utf-8"), expected.encode("utf-8"))

    def _origin_ok(self) -> bool:
        origin = self.headers.get("Origin")
        if origin is None:
            return True
        return origin.strip().lower() in getattr(self.server, "allowed_origins", set())

    def _common_checks(self, url) -> bool:
        """Checks applied to every request. False means already rejected."""
        if len(url.query) > MAX_QUERY_LENGTH:
            self._reject(414, "query string too long")
            return False
        if not self._host_ok():
            self._reject(400, "invalid Host header")
            return False
        return True

    def _api_checks(self) -> bool:
        """Auth check for every /api route. False means already rejected."""
        if not self._token_ok():
            self._reject(401, "missing or invalid dashboard token")
            return False
        return True

    def _post_checks(self) -> bool:
        """Extra gates for state-changing requests. False means rejected."""
        if not self._origin_ok():
            self._reject(403, "cross-origin request rejected")
            return False
        content_type = (self.headers.get("Content-Type") or "").split(";")[0].strip().lower()
        if content_type != "application/json":
            self._reject(415, "Content-Type must be application/json")
            return False
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            self._reject(400, "invalid Content-Length")
            return False
        if length > MAX_BODY_BYTES:
            self._reject(413, "request body too large")
            return False
        return True

    # -- request plumbing --------------------------------------------------

    def _read_body(self) -> dict[str, Any]:
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = 0
        if length <= 0:
            return {}
        if length > MAX_BODY_BYTES:
            raise DashboardError(413, "request body too large")
        raw = self.rfile.read(length)
        try:
            data = json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            raise DashboardError(400, "request body must be JSON")
        return data if isinstance(data, dict) else {}

    def _dispatch(self, handler: Callable[[], Any]) -> None:
        try:
            self._send_json(200, handler())
        except DashboardError as exc:
            self._send_json(exc.status, {"error": exc.message})
        except BrokenPipeError:
            pass
        except Exception:  # never let a request kill the server, never leak internals
            if getattr(self.server, "verbose", False):
                traceback.print_exc(file=sys.stderr)
            try:
                self._send_json(500, {"error": "internal server error"})
            except (BrokenPipeError, OSError):
                pass

    def do_GET(self) -> None:  # noqa: N802
        url = urlsplit(self.path)
        if not self._common_checks(url):
            return
        path = url.path
        if path == "/" or path == "/index.html":
            self._send_html(render_page(getattr(self.server, "token", "")))
            return
        if path.startswith("/api/") and not self._api_checks():
            return
        if path == "/api/projects":
            self._dispatch(self.app.projects)
        elif path == "/api/search":
            query = parse_qs(url.query).get("q", [""])[0]
            self._dispatch(lambda: self.app.search(query))
        elif path == "/api/health":
            self._dispatch(self.app.health)
        else:
            self._send_json(404, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        url = urlsplit(self.path)
        if not self._common_checks(url):
            return
        if not self._api_checks():
            return
        if not self._post_checks():
            return
        parts = [unquote(part) for part in url.path.strip("/").split("/")]
        try:
            body = self._read_body()
        except DashboardError as exc:
            self._reject(exc.status, exc.message)
            return
        if parts == ["api", "open"]:
            self._dispatch(lambda: self.app.open_path(body.get("path")))
            return
        if len(parts) == 4 and parts[0] == "api" and parts[1] == "projects":
            project_id, action = parts[2], parts[3]
            if action == "snooze":
                self._dispatch(lambda: self.app.snooze(project_id, body.get("until")))
            elif action == "archive":
                self._dispatch(lambda: self.app.archive(project_id))
            elif action == "restore":
                self._dispatch(lambda: self.app.restore(project_id, body.get("bucket")))
            elif action == "move":
                self._dispatch(lambda: self.app.move(project_id, body.get("bucket")))
            else:
                self._send_json(404, {"error": f"unknown action: {action}"})
            return
        self._send_json(404, {"error": "not found"})


def _allowed_hosts(bind_host: str, port: int) -> set[str]:
    """Host header values accepted for this bind (lowercase ``host:port``)."""
    names = {"localhost", "127.0.0.1", "[::1]"}
    bare = bind_host.strip().lower()
    if bare and not is_loopback_host(bare) and bare not in ("0.0.0.0", "::", "[::]"):
        names.add(f"[{bare.strip('[]')}]" if ":" in bare.strip("[]") else bare)
    return {f"{name}:{port}" for name in names}


class DashboardServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, app: DashboardApp, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT):
        if not is_loopback_host(host):
            if os.environ.get(NONLOOPBACK_ENV) != "1":
                raise RuntimeError(
                    f"refusing to bind non-loopback host {host!r}: the dashboard is "
                    "localhost-only. Set LPOS_DASHBOARD_ALLOW_NONLOOPBACK=1 to override, "
                    "and put a hardened reverse proxy with TLS and authentication in "
                    "front of it (see docs/DASHBOARD.md)."
                )
            print(
                "=" * 72
                + f"\nWARNING: dashboard binding non-loopback host {host!r}.\n"
                "Every client that can reach this port can read project metadata and\n"
                "mutate dashboard state if it obtains the session token. Remote use\n"
                "REQUIRES a hardened reverse proxy providing TLS and authentication.\n"
                + "=" * 72,
                file=sys.stderr,
            )
        super().__init__((host, port), DashboardHandler)
        self.app = app
        self.verbose = False
        # LPOS-06: per-run high-entropy session token, persisted 0600 for
        # local tooling (curl etc.) to read.
        self.token = secrets.token_urlsafe(32)
        self.token_file = self.app.root / "dashboard" / TOKEN_FILE_NAME
        _write_token_file(self.token_file, self.token)
        bound_port = self.server_address[1]
        self.allowed_hosts = _allowed_hosts(host, bound_port)
        self.allowed_origins = {f"http://{h}" for h in self.allowed_hosts}


def serve(
    root: Path | None = None,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    opener: Callable[[list[str]], None] | None = None,
) -> DashboardServer:
    """Build a ready-to-run server bound to localhost. Call ``serve_forever`` on it."""
    return DashboardServer(DashboardApp(root=root, opener=opener), host=host, port=port)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="lpos dashboard",
        description="Hermes Project Dashboard: local project status on a localhost port",
    )
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="port (default 7373)")
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Hermes root (default: $LPOS_HERMES_ROOT or ~/.hermes)",
    )
    parser.add_argument("--host", default=DEFAULT_HOST, help="bind address (default 127.0.0.1)")
    parser.add_argument("--verbose", action="store_true", help="log requests to stderr")
    args = parser.parse_args(argv)
    try:
        server = serve(root=args.root, host=args.host, port=args.port)
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    server.verbose = args.verbose
    bound_host, bound_port = server.server_address[0], server.server_address[1]
    print(
        json.dumps(
            {
                "dashboard": f"http://{bound_host}:{bound_port}/",
                "hermes_root": str(server.app.root),
                "state": str(server.app.state_file),
                "token_file": str(server.token_file),
            },
            indent=2,
        ),
        file=sys.stderr,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0
