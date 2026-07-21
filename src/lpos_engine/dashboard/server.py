"""Local HTTP service for the LPOS Hermes dashboard."""

from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
import time
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files as resource_files
from pathlib import Path
from typing import Any
from urllib.parse import unquote

from . import DEFAULT_PORT
from .scanner import hermes_root, scan

BUCKETS = {"active", "research", "snoozed", "archive"}


def dashboard_root() -> Path:
    return Path(os.environ.get("LPOS_DASHBOARD_STATE_ROOT", Path.home() / ".hermes" / "dashboard")).expanduser().resolve()


def config_path() -> Path:
    return dashboard_root() / "config.json"


def state_path() -> Path:
    return dashboard_root() / "state.json"


def pid_path() -> Path:
    return dashboard_root() / "dashboard.pid"


def default_config(hermes_root_value: str | None = None, port: int = DEFAULT_PORT, user: str | None = None) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "hermes_root": str(hermes_root(hermes_root_value)),
        "port": int(port),
        "host": "127.0.0.1",
        "user": user or os.environ.get("USER") or os.environ.get("USERNAME") or "local-user",
        "state_file": str(state_path()),
        "created_by": "LPOS dashboard onboarding",
    }


def load_config() -> dict[str, Any]:
    try:
        value = json.loads(config_path().read_text(encoding="utf-8"))
        if isinstance(value, dict):
            base = default_config()
            base.update(value)
            return base
    except (OSError, ValueError):
        pass
    return default_config()


def write_config(config: dict[str, Any]) -> None:
    dashboard_root().mkdir(parents=True, exist_ok=True)
    config_path().write_text(json.dumps(config, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_meta() -> dict[str, Any]:
    try:
        value = json.loads(state_path().read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def write_meta(value: dict[str, Any]) -> None:
    dashboard_root().mkdir(parents=True, exist_ok=True)
    state_path().write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def merged_state(config: dict[str, Any]) -> dict[str, Any]:
    meta = read_meta()
    projects_meta = meta.setdefault("projects", {})
    now = int(time.time() * 1000)
    dirty = False
    projects = []
    for project in scan(config.get("hermes_root")):
        item_meta = projects_meta.get(project["id"], {}) if isinstance(projects_meta.get(project["id"]), dict) else {}
        if item_meta.get("bucket") == "snoozed" and item_meta.get("snoozeUntil") and int(item_meta["snoozeUntil"]) <= now:
            item_meta["bucket"] = item_meta.get("prevBucket") or "active"
            item_meta["snoozeUntil"] = None
            item_meta["wokeAt"] = now
            projects_meta[project["id"]] = item_meta
            dirty = True
        bucket = item_meta.get("bucket") or project.get("suggestedBucket") or "active"
        if bucket not in BUCKETS:
            bucket = "active"
        project.update({
            "bucket": bucket,
            "snoozeUntil": item_meta.get("snoozeUntil"),
            "prevBucket": item_meta.get("prevBucket"),
            "archivedAt": item_meta.get("archivedAt"),
            "wokeAt": item_meta.get("wokeAt"),
        })
        projects.append(project)
    if dirty:
        write_meta(meta)
    return {
        "root": config["hermes_root"],
        "home": str(Path.home()),
        "platform": sys.platform,
        "config": {"port": config["port"], "stateFile": str(state_path()), "user": config.get("user")},
        "projects": projects,
    }


def open_path(target_value: str, root_value: str) -> bool:
    root = Path(root_value).expanduser().resolve()
    target = Path(target_value).expanduser().resolve()
    try:
        target.relative_to(root)
    except ValueError:
        return False
    if not target.exists():
        return False
    opener = "open" if sys.platform == "darwin" else "explorer" if sys.platform == "win32" else "xdg-open"
    subprocess.Popen([opener, str(target)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return True


class DashboardHandler(BaseHTTPRequestHandler):
    server_version = "LPOSDashboard/1.0"

    @property
    def config(self) -> dict[str, Any]:
        return self.server.config  # type: ignore[attr-defined]

    def _send(self, status: int, body: bytes | str, content_type: str = "application/json") -> None:
        payload = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)

    def _body_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        value = json.loads(raw.decode("utf-8") or "{}")
        if not isinstance(value, dict):
            raise ValueError("request body must be a JSON object")
        return value

    def do_GET(self) -> None:
        if self.path == "/api/state":
            self._send(HTTPStatus.OK, json.dumps(merged_state(self.config)))
            return
        rel = unquote(self.path.split("?", 1)[0])
        if rel == "/":
            rel = "/index.html"
        if ".." in Path(rel).parts:
            self._send(HTTPStatus.BAD_REQUEST, '{"error":"bad path"}')
            return
        public = resource_files("lpos_engine.dashboard.public")
        try:
            target = public.joinpath(rel.lstrip("/"))
            data = target.read_bytes()
        except (FileNotFoundError, IsADirectoryError, AttributeError):
            self._send(HTTPStatus.NOT_FOUND, '{"error":"not found"}')
            return
        content_type = "text/html; charset=utf-8" if rel.endswith(".html") else "text/plain; charset=utf-8"
        self._send(HTTPStatus.OK, data, content_type)

    def do_POST(self) -> None:
        try:
            body = self._body_json()
            if self.path == "/api/meta":
                project_id = str(body.get("id") or "")
                patch = body.get("patch") if isinstance(body.get("patch"), dict) else {}
                allowed = {"bucket", "snoozeUntil", "prevBucket", "archivedAt", "wokeAt"}
                clean = {key: value for key, value in patch.items() if key in allowed}
                if clean.get("bucket") and clean["bucket"] not in BUCKETS:
                    raise ValueError("invalid bucket")
                meta = read_meta()
                projects = meta.setdefault("projects", {})
                current = projects.get(project_id, {}) if isinstance(projects.get(project_id), dict) else {}
                current.update(clean)
                projects[project_id] = current
                write_meta(meta)
                self._send(HTTPStatus.OK, '{"ok":true}')
                return
            if self.path == "/api/open":
                ok = open_path(str(body.get("path") or ""), self.config["hermes_root"])
                self._send(HTTPStatus.OK if ok else HTTPStatus.BAD_REQUEST, json.dumps({"ok": ok}))
                return
            self._send(HTTPStatus.NOT_FOUND, '{"error":"not found"}')
        except Exception as exc:
            self._send(HTTPStatus.BAD_REQUEST, json.dumps({"error": str(exc)}))

    def log_message(self, fmt: str, *args: Any) -> None:
        sys.stderr.write("dashboard: " + fmt % args + "\n")


def serve(config: dict[str, Any]) -> None:
    dashboard_root().mkdir(parents=True, exist_ok=True)
    address = (str(config.get("host") or "127.0.0.1"), int(config.get("port") or DEFAULT_PORT))
    httpd = ThreadingHTTPServer(address, DashboardHandler)
    httpd.config = config  # type: ignore[attr-defined]
    pid_path().write_text(str(os.getpid()) + "\n", encoding="utf-8")
    print(json.dumps({"status": "running", "url": f"http://{address[0]}:{address[1]}", "hermes_root": config["hermes_root"], "state": str(state_path())}))
    try:
        httpd.serve_forever()
    finally:
        try:
            pid_path().unlink()
        except OSError:
            pass


def init_dashboard(args: argparse.Namespace) -> dict[str, Any]:
    config = default_config(args.hermes_root, args.port, args.user)
    existing = load_config() if config_path().is_file() else {}
    existing.update({k: v for k, v in config.items() if v is not None})
    write_config(existing)
    meta = read_meta()
    meta.setdefault("schema_version", 1)
    meta.setdefault("projects", {})
    write_meta(meta)
    return existing


def start_background(config: dict[str, Any], *, open_browser: bool) -> dict[str, Any]:
    command = [sys.executable, "-m", "lpos_engine", "dashboard", "serve"]
    log_path = dashboard_root() / "dashboard.log"
    with log_path.open("ab") as log:
        process = subprocess.Popen(command, stdout=log, stderr=log, cwd=str(Path.cwd()), start_new_session=True)
    pid_path().write_text(str(process.pid) + "\n", encoding="utf-8")
    url = f"http://{config.get('host', '127.0.0.1')}:{config.get('port', DEFAULT_PORT)}"
    if open_browser:
        webbrowser.open(url)
    return {"status": "started", "pid": process.pid, "url": url, "log": str(log_path)}


def status() -> dict[str, Any]:
    pid = None
    alive = False
    try:
        pid = int(pid_path().read_text(encoding="utf-8").strip())
        os.kill(pid, 0)
        alive = True
    except Exception:
        alive = False
    config = load_config()
    return {"configured": config_path().is_file(), "running": alive, "pid": pid, "url": f"http://{config.get('host', '127.0.0.1')}:{config.get('port', DEFAULT_PORT)}", "config": str(config_path()), "state": str(state_path())}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="lpos dashboard", description="LPOS Hermes Project Dashboard")
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init")
    init.add_argument("--hermes-root")
    init.add_argument("--port", type=int, default=DEFAULT_PORT)
    init.add_argument("--user")
    serve_parser = sub.add_parser("serve")
    serve_parser.add_argument("--hermes-root")
    serve_parser.add_argument("--port", type=int)
    start = sub.add_parser("start")
    start.add_argument("--open", action="store_true")
    status_parser = sub.add_parser("status")
    open_parser = sub.add_parser("open")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "init":
        print(json.dumps({"dashboard": init_dashboard(args)}, indent=2, sort_keys=True))
        return 0
    if args.command == "serve":
        config = load_config()
        if args.hermes_root:
            config["hermes_root"] = str(hermes_root(args.hermes_root))
        if args.port:
            config["port"] = args.port
        serve(config)
        return 0
    if args.command == "start":
        config = load_config()
        if not config_path().is_file():
            write_config(config)
        print(json.dumps(start_background(config, open_browser=args.open), indent=2, sort_keys=True))
        return 0
    if args.command == "status":
        print(json.dumps(status(), indent=2, sort_keys=True))
        return 0
    if args.command == "open":
        config = load_config()
        url = f"http://{config.get('host', '127.0.0.1')}:{config.get('port', DEFAULT_PORT)}"
        webbrowser.open(url)
        print(json.dumps({"url": url}, indent=2, sort_keys=True))
        return 0
    parser.error("unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
