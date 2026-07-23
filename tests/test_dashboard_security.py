"""Adversarial regression tests for audit findings LPOS-06 and LPOS-09.

These mirror the audit reproductions in
``evidence/reproduction-results.json -> dashboard.*``:

- ``unauthenticated_cross_origin_mutation``: unauthenticated / cross-origin /
  wrong-Host / text-plain requests must be rejected without state change and
  responses must carry hardening headers.
- ``scanner_root_escape``: symlinked project directories and absolute kanban
  card paths must not expose anything outside the approved roots.

Everything runs offline against a real server on port 0.
"""

from __future__ import annotations

import http.client
import json
import os
import socket
import stat
import threading
from pathlib import Path

import pytest

from lpos_engine.dashboard import scanner
from lpos_engine.dashboard.server import (
    MAX_BODY_BYTES,
    SECURITY_HEADERS,
    serve,
)

REQUIRED_HEADER_NAMES = [name for name, _ in SECURITY_HEADERS]


# ---------------------------------------------------------------------------
# fixtures and helpers
# ---------------------------------------------------------------------------


@pytest.fixture()
def hermes_root(tmp_path: Path) -> Path:
    """A minimal hermes root with one real project."""
    root = tmp_path / "hermes"
    demo = root / "projects" / "demo-project"
    demo.mkdir(parents=True)
    (demo / "project.json").write_text(
        json.dumps({"name": "Demo Project", "type": "active"}), encoding="utf-8"
    )
    (demo / "notes.md").write_text("inside", encoding="utf-8")
    return root


@pytest.fixture()
def http_server(hermes_root: Path):
    launched: list[list[str]] = []
    server = serve(root=hermes_root, port=0, opener=launched.append)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server, launched
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def request(
    server,
    method: str,
    path: str,
    *,
    token: str | None = None,
    headers: dict[str, str] | None = None,
    body: bytes | None = None,
):
    """Raw HTTP request with full control over Host/Origin/Content-Type."""
    port = server.server_address[1]
    all_headers: dict[str, str] = {"Host": f"127.0.0.1:{port}"}
    if token is not None:
        all_headers["X-LPOS-Token"] = token
    if body is not None:
        all_headers.setdefault("Content-Type", "application/json")
    if headers:
        all_headers.update(headers)
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    try:
        conn.request(method, path, body=body, headers=all_headers)
        response = conn.getresponse()
        raw = response.read()
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            payload = raw
        return response.status, payload, dict(response.getheaders())
    finally:
        conn.close()


def get_demo_id(server) -> str:
    status, data, _ = request(server, "GET", "/api/projects", token=server.token)
    assert status == 200
    matches = [p for p in data["projects"] if p["name"] == "Demo Project"]
    assert matches
    return matches[0]["id"]


def state_file(hermes_root: Path) -> Path:
    return hermes_root / "dashboard" / "state.json"


def assert_no_state_change(hermes_root: Path) -> None:
    # A fresh root has no state.json until a mutation succeeds.
    assert not state_file(hermes_root).exists()


# ---------------------------------------------------------------------------
# LPOS-06: authentication
# ---------------------------------------------------------------------------


def test_unauthenticated_get_projects_is_401_with_no_data(http_server, hermes_root):
    server, _ = http_server
    status, payload, _ = request(server, "GET", "/api/projects")
    assert status == 401
    assert isinstance(payload, dict) and "projects" not in payload
    assert "Demo Project" not in json.dumps(payload)


def test_unauthenticated_post_archive_is_401_and_state_unchanged(http_server, hermes_root):
    server, _ = http_server
    project_id = get_demo_id(server)
    status, payload, _ = request(
        server, "POST", f"/api/projects/{project_id}/archive", body=b"{}"
    )
    assert status == 401
    assert payload.get("ok") is not True
    assert_no_state_change(hermes_root)
    # Project is still active when queried with the real token.
    status, data, _ = request(server, "GET", "/api/projects", token=server.token)
    assert status == 200
    demo = [p for p in data["projects"] if p["id"] == project_id][0]
    assert demo["bucket"] == "active"


def test_wrong_token_is_401(http_server, hermes_root):
    server, _ = http_server
    status, _, _ = request(server, "GET", "/api/projects", token="A" * 43)
    assert status == 401
    status, _, _ = request(
        server,
        "GET",
        "/api/projects",
        headers={"Authorization": "Bearer definitely-not-the-token"},
    )
    assert status == 401
    # Bearer form with the right token works.
    status, _, _ = request(
        server,
        "GET",
        "/api/projects",
        headers={"Authorization": f"Bearer {server.token}"},
    )
    assert status == 200


def test_unauthenticated_search_and_health_are_401(http_server):
    server, _ = http_server
    for path in ("/api/search?q=notes", "/api/health"):
        status, _, _ = request(server, "GET", path)
        assert status == 401


# ---------------------------------------------------------------------------
# LPOS-06: Host and Origin boundaries
# ---------------------------------------------------------------------------


def test_attacker_host_header_is_400(http_server, hermes_root):
    server, _ = http_server
    port = server.server_address[1]
    status, _, _ = request(
        server,
        "GET",
        "/api/projects",
        token=server.token,
        headers={"Host": "attacker.example"},
    )
    assert status == 400
    # DNS-rebinding shape: right port, wrong name.
    status, _, _ = request(
        server,
        "POST",
        "/api/projects/x/archive",
        token=server.token,
        body=b"{}",
        headers={"Host": f"attacker.example:{port}"},
    )
    assert status == 400
    assert_no_state_change(hermes_root)
    # The UI shell itself also requires a valid Host.
    status, _, _ = request(server, "GET", "/", headers={"Host": "attacker.example"})
    assert status == 400
    # localhost alias with the right port is accepted.
    status, _, _ = request(
        server,
        "GET",
        "/api/projects",
        token=server.token,
        headers={"Host": f"localhost:{port}"},
    )
    assert status == 200


def test_foreign_origin_on_post_with_valid_token_is_403(http_server, hermes_root):
    server, _ = http_server
    project_id = get_demo_id(server)
    status, _, _ = request(
        server,
        "POST",
        f"/api/projects/{project_id}/archive",
        token=server.token,
        body=b"{}",
        headers={"Origin": "https://attacker.example"},
    )
    assert status == 403
    assert_no_state_change(hermes_root)
    # Same-origin POST is allowed.
    port = server.server_address[1]
    status, result, _ = request(
        server,
        "POST",
        f"/api/projects/{project_id}/archive",
        token=server.token,
        body=b"{}",
        headers={"Origin": f"http://127.0.0.1:{port}"},
    )
    assert status == 200 and result["bucket"] == "archived"


# ---------------------------------------------------------------------------
# LPOS-06: body and query limits
# ---------------------------------------------------------------------------


def test_text_plain_post_is_rejected(http_server, hermes_root):
    server, _ = http_server
    project_id = get_demo_id(server)
    status, _, _ = request(
        server,
        "POST",
        f"/api/projects/{project_id}/archive",
        token=server.token,
        body=b"{}",
        headers={"Content-Type": "text/plain"},
    )
    assert status == 415
    assert_no_state_change(hermes_root)


def test_oversized_body_is_413(http_server, hermes_root):
    server, _ = http_server
    port = server.server_address[1]
    # Announce a body over the cap; the server must reject on the header
    # without reading the body.
    with socket.create_connection(("127.0.0.1", port), timeout=10) as sock:
        sock.sendall(
            (
                "POST /api/projects/x/archive HTTP/1.1\r\n"
                f"Host: 127.0.0.1:{port}\r\n"
                f"X-LPOS-Token: {server.token}\r\n"
                "Content-Type: application/json\r\n"
                f"Content-Length: {MAX_BODY_BYTES + 1}\r\n"
                "\r\n"
            ).encode("ascii")
        )
        response = sock.recv(65536).decode("utf-8", "replace")
    assert response.startswith("HTTP/1.1 413")
    assert_no_state_change(hermes_root)


def test_oversized_query_string_is_rejected(http_server):
    server, _ = http_server
    status, _, _ = request(
        server, "GET", "/api/search?q=" + "a" * 4000, token=server.token
    )
    assert status == 414


# ---------------------------------------------------------------------------
# LPOS-06: headers, token file, loopback policy
# ---------------------------------------------------------------------------


def test_security_headers_on_ui_api_and_error_responses(http_server):
    server, _ = http_server
    for method, path, kwargs in (
        ("GET", "/", {}),
        ("GET", "/api/projects", {"token": server.token}),
        ("GET", "/api/projects", {}),  # 401 path
    ):
        _, _, headers = request(server, method, path, **kwargs)
        lowered = {k.lower(): v for k, v in headers.items()}
        for name in REQUIRED_HEADER_NAMES:
            assert name.lower() in lowered, f"{name} missing on {method} {path}"
        assert lowered["x-frame-options"] == "DENY"
        assert lowered["x-content-type-options"] == "nosniff"
        assert lowered["referrer-policy"] == "no-referrer"
        assert lowered["cache-control"] == "no-store"
        assert "default-src 'none'" in lowered["content-security-policy"]


def test_token_file_written_0600_and_matches(http_server, hermes_root):
    server, _ = http_server
    token_file = hermes_root / "dashboard" / "token"
    assert token_file.is_file()
    assert token_file.read_text(encoding="utf-8").strip() == server.token
    if os.name == "posix":
        mode = stat.S_IMODE(token_file.stat().st_mode)
        assert mode == 0o600


def test_ui_page_has_token_injected_without_requiring_auth(http_server, hermes_root):
    server, _ = http_server
    status, payload, _ = request(server, "GET", "/")
    assert status == 200
    assert server.token in payload.decode("utf-8")


def test_nonloopback_bind_refused_without_env_override(hermes_root, monkeypatch):
    monkeypatch.delenv("LPOS_DASHBOARD_ALLOW_NONLOOPBACK", raising=False)
    with pytest.raises(RuntimeError):
        serve(root=hermes_root, host="0.0.0.0", port=0)
    # With the explicit override the bind is allowed (and loudly warned about).
    monkeypatch.setenv("LPOS_DASHBOARD_ALLOW_NONLOOPBACK", "1")
    server = serve(root=hermes_root, host="0.0.0.0", port=0)
    server.server_close()


# ---------------------------------------------------------------------------
# LPOS-09: scanner containment
# ---------------------------------------------------------------------------


def _symlink_supported(tmp_path: Path) -> bool:
    try:
        (tmp_path / "_probe_link").symlink_to(tmp_path)
        return True
    except (OSError, NotImplementedError):
        return False


def test_symlinked_project_dir_outside_root_not_scanned_or_searched(
    hermes_root: Path, tmp_path: Path
):
    if not _symlink_supported(tmp_path):
        pytest.skip("symlinks unsupported on this platform")
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "AUDIT_OUTSIDE_MARKER.txt").write_text("secret", encoding="utf-8")
    (hermes_root / "projects" / "linked-external").symlink_to(outside)

    projects = scanner.scan_projects(hermes_root)
    assert all(p["name"] != "linked-external" for p in projects)
    assert all(
        not (p.get("path") or "").startswith(str(outside)) for p in projects
    )

    result = scanner.search(hermes_root, "AUDIT_OUTSIDE")
    assert result["files"] == []
    assert "AUDIT_OUTSIDE_MARKER" not in json.dumps(result)


def test_symlink_inside_project_not_followed_by_search(hermes_root: Path, tmp_path: Path):
    if not _symlink_supported(tmp_path):
        pytest.skip("symlinks unsupported on this platform")
    outside = tmp_path / "outside2"
    outside.mkdir()
    (outside / "MARKER_INNER.txt").write_text("secret", encoding="utf-8")
    (hermes_root / "projects" / "demo-project" / "escape").symlink_to(outside)

    result = scanner.search(hermes_root, "MARKER_INNER")
    assert result["files"] == []


def test_kanban_absolute_path_outside_root_is_dropped(hermes_root: Path, tmp_path: Path):
    outside = tmp_path / "kanban-outside"
    outside.mkdir()
    (outside / "LEAK_MARKER.txt").write_text("secret", encoding="utf-8")
    kanban = hermes_root / "kanban"
    kanban.mkdir()
    (kanban / "board.json").write_text(
        json.dumps(
            {
                "cards": [
                    {"title": "Escapee", "path": str(outside)},
                    {"title": "Contained", "path": "projects/demo-project"},
                ]
            }
        ),
        encoding="utf-8",
    )
    projects = scanner.scan_projects(hermes_root)
    escapee = [p for p in projects if p["name"] == "Escapee"][0]
    assert escapee["path"] is None
    assert escapee["note"] == "path outside approved roots"
    contained = [p for p in projects if p["name"] == "Contained"][0]
    assert contained["path"] is not None

    # The dropped path is never walked by search.
    result = scanner.search(hermes_root, "LEAK_MARKER")
    assert result["files"] == []


def test_open_path_rejects_symlink_escape(http_server, hermes_root, tmp_path):
    server, launched = http_server
    if not _symlink_supported(tmp_path):
        pytest.skip("symlinks unsupported on this platform")
    outside = tmp_path / "open-outside"
    outside.mkdir()
    link = hermes_root / "projects" / "demo-project" / "sneaky"
    link.symlink_to(outside)
    status, _, _ = request(
        server,
        "POST",
        "/api/open",
        token=server.token,
        body=json.dumps({"path": str(link)}).encode("utf-8"),
    )
    assert status == 403
    assert launched == []
