"""Localhost-only stdlib HTTP server and JSON API for the Hermes dashboard.

The API surface:

- ``GET  /``                              the single-page UI
- ``GET  /api/projects``                  all projects with computed buckets
- ``POST /api/projects/<id>/snooze``      body ``{"until": "<ISO 8601>"}``
- ``POST /api/projects/<id>/archive``
- ``POST /api/projects/<id>/restore``     body ``{"bucket": "active"|"research"}``
- ``POST /api/projects/<id>/move``        body ``{"bucket": ...}``
- ``POST /api/open``                      body ``{"path": ...}`` (inside hermes root only)
- ``GET  /api/search?q=``                 project-name and file-name search
- ``GET  /api/health``                    contents of ``<root>/monitor/status.json`` or null

Application logic lives on :class:`DashboardApp` so tests can drive it without
sockets; the request handler is a thin shim.
"""

from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable
from urllib.parse import parse_qs, unquote, urlsplit

from . import scanner, state as state_mod
from .state import DashboardState, WORKING_BUCKETS, iso, parse_iso, utcnow
from .ui import PAGE_HTML

DEFAULT_PORT = 7373
DEFAULT_HOST = "127.0.0.1"


class DashboardError(Exception):
    """An API-level error carrying an HTTP status code."""

    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


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
            root_resolved = self.root.resolve()
        except OSError as exc:
            raise DashboardError(400, f"unresolvable path: {exc}") from exc
        if not resolved.is_relative_to(root_resolved):
            raise DashboardError(403, "refusing to open a path outside the hermes root")
        if not resolved.exists():
            raise DashboardError(404, "path does not exist")
        target = resolved if resolved.is_dir() else resolved.parent
        command = open_folder_command(str(target))
        try:
            self.opener(command)
        except OSError as exc:
            raise DashboardError(500, f"could not launch file manager: {exc}") from exc
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

    def _send_json(self, status: int, payload: Any) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, html: str) -> None:
        body = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self) -> dict[str, Any]:
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = 0
        if length <= 0:
            return {}
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
        except Exception as exc:  # never let a request kill the server
            self._send_json(500, {"error": f"{type(exc).__name__}: {exc}"})

    def do_GET(self) -> None:  # noqa: N802
        url = urlsplit(self.path)
        path = url.path
        if path == "/" or path == "/index.html":
            self._send_html(PAGE_HTML)
        elif path == "/api/projects":
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
        parts = [unquote(part) for part in url.path.strip("/").split("/")]
        try:
            body = self._read_body()
        except DashboardError as exc:
            self._send_json(exc.status, {"error": exc.message})
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


class DashboardServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, app: DashboardApp, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT):
        super().__init__((host, port), DashboardHandler)
        self.app = app
        self.verbose = False


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
    server = serve(root=args.root, host=args.host, port=args.port)
    server.verbose = args.verbose
    bound_host, bound_port = server.server_address[0], server.server_address[1]
    print(
        json.dumps(
            {
                "dashboard": f"http://{bound_host}:{bound_port}/",
                "hermes_root": str(server.app.root),
                "state": str(server.app.state_file),
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
