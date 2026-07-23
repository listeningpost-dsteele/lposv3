"""Tests for the Hermes Project Dashboard module (lpos_engine.dashboard)."""

from __future__ import annotations

import json
import threading
import urllib.request
from datetime import timedelta
from pathlib import Path

import pytest

from lpos_engine.dashboard import scanner
from lpos_engine.dashboard.server import DashboardApp, DashboardError, DashboardServer, serve
from lpos_engine.dashboard.state import DashboardState, iso, parse_iso, state_path, utcnow


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def hermes_root(tmp_path: Path) -> Path:
    """A fake hermes root with projects across the standard scan roots."""
    root = tmp_path / "hermes"
    sessions = root / "sessions"
    ops = root / "standing-operations"
    projects = root / "projects"

    alpha = sessions / "alpha"
    alpha.mkdir(parents=True)
    (alpha / "project.json").write_text(
        json.dumps(
            {
                "name": "Alpha Report",
                "description": "Quarterly digest build",
                "agent": "scribe",
                "type": "active",
            }
        ),
        encoding="utf-8",
    )
    (alpha / "digest-final.md").write_text("done", encoding="utf-8")

    bare = ops / "nightly-sync"
    bare.mkdir(parents=True)
    (bare / "log.txt").write_text("ran", encoding="utf-8")

    research = projects / "deep-dive"
    research.mkdir(parents=True)
    (research / "project.json").write_text(
        json.dumps({"name": "Deep Dive", "type": "research", "agent": "analyst"}),
        encoding="utf-8",
    )

    # Broken metadata must not break the scan.
    broken = sessions / "broken-meta"
    broken.mkdir()
    (broken / "project.json").write_text("{not json", encoding="utf-8")

    # Extra root registered through dashboard/roots.json.
    extra_root = tmp_path / "extra-root"
    (extra_root / "side-quest").mkdir(parents=True)
    (root / "dashboard").mkdir(parents=True)
    (root / "dashboard" / "roots.json").write_text(
        json.dumps({"roots": [str(extra_root)]}), encoding="utf-8"
    )

    # Kanban board merged as projects; defensive about shape.
    kanban = root / "kanban"
    kanban.mkdir()
    (kanban / "board.json").write_text(
        json.dumps(
            {
                "cards": [
                    {"title": "Kanban Card One", "owner": "planner", "status": "research"},
                    "not-a-dict",
                ]
            }
        ),
        encoding="utf-8",
    )
    (kanban / "garbage.json").write_text("]]not json[[", encoding="utf-8")
    return root


def project_by_name(items: list[dict], name: str) -> dict:
    matches = [p for p in items if p["name"] == name]
    assert matches, f"project {name!r} not found in {[p['name'] for p in items]}"
    return matches[0]


# ---------------------------------------------------------------------------
# scanner
# ---------------------------------------------------------------------------


def test_scanner_finds_projects_across_roots(hermes_root: Path) -> None:
    items = scanner.scan_projects(hermes_root)
    names = {p["name"] for p in items}
    assert {"Alpha Report", "nightly-sync", "Deep Dive", "broken-meta", "side-quest"} <= names

    alpha = project_by_name(items, "Alpha Report")
    assert alpha["agent"] == "scribe"
    assert alpha["description"] == "Quarterly digest build"
    assert alpha["type"] == "active"
    assert alpha["last_activity"] > 0

    # Metadata-free folder falls back to folder name + mtime, type active.
    bare = project_by_name(items, "nightly-sync")
    assert bare["agent"] is None
    assert bare["type"] == "active"

    # Corrupt project.json falls back rather than raising.
    broken = project_by_name(items, "broken-meta")
    assert broken["type"] == "active"

    research = project_by_name(items, "Deep Dive")
    assert research["type"] == "research"


def test_scanner_merges_kanban_defensively(hermes_root: Path) -> None:
    items = scanner.scan_projects(hermes_root)
    card = project_by_name(items, "Kanban Card One")
    assert card["source"] == "kanban"
    assert card["agent"] == "planner"
    assert card["type"] == "research"
    # The unparseable kanban file contributes nothing and raises nothing.


def test_scanner_missing_root_is_empty(tmp_path: Path) -> None:
    assert scanner.scan_projects(tmp_path / "does-not-exist") == []


# ---------------------------------------------------------------------------
# state
# ---------------------------------------------------------------------------


def test_state_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "dashboard" / "state.json"
    state = DashboardState()
    wake = utcnow() + timedelta(days=1)
    state.snooze("proj-1", wake)
    state.archive("proj-2")
    state.move("proj-3", "research")
    state.save(path)

    loaded = DashboardState.load(path)
    assert loaded.projects == state.projects
    assert loaded.effective("proj-1")["bucket"] == "snoozed"
    assert loaded.effective("proj-2")["bucket"] == "archived"
    assert loaded.effective("proj-3")["bucket"] == "research"
    # Atomic write leaves no temp litter.
    assert [p.name for p in path.parent.iterdir()] == ["state.json"]


def test_snooze_wake_returns_to_previous_bucket_with_woke_flag() -> None:
    state = DashboardState()
    state.move("p", "research")
    state.snooze("p", utcnow() - timedelta(hours=1))  # already past wake time
    effective = state.effective("p")
    assert effective["bucket"] == "research"
    assert effective["woke"] is True

    # A future wake time keeps it snoozed, not woke.
    state.snooze("p", utcnow() + timedelta(hours=2))
    effective = state.effective("p")
    assert effective["bucket"] == "snoozed"
    assert effective["woke"] is False
    assert parse_iso(effective["snooze_until"]) is not None


def test_archive_and_restore() -> None:
    state = DashboardState()
    state.archive("p")
    archived = state.effective("p")
    assert archived["bucket"] == "archived"
    assert parse_iso(archived["archived_at"]) is not None

    state.restore("p", "research")
    assert state.effective("p")["bucket"] == "research"
    assert state.effective("p")["archived_at"] is None

    with pytest.raises(ValueError):
        state.restore("p", "archived")
    with pytest.raises(ValueError):
        state.move("p", "snoozed")


def test_corrupt_state_degrades_to_everything_active(hermes_root: Path) -> None:
    path = state_path(hermes_root)
    path.write_text('{"projects": ["truncated garba', encoding="utf-8")
    loaded = DashboardState.load(path)
    assert loaded.projects == {}
    assert loaded.effective("anything")["bucket"] == "active"

    # And the full app path survives it too.
    app = DashboardApp(root=hermes_root, opener=lambda cmd: None)
    result = app.projects()
    assert all(p["bucket"] in ("active", "research") for p in result["projects"])


def test_missing_state_is_everything_active(hermes_root: Path) -> None:
    app = DashboardApp(root=hermes_root, opener=lambda cmd: None)
    buckets = {p["name"]: p["bucket"] for p in app.projects()["projects"]}
    assert buckets["Alpha Report"] == "active"
    assert buckets["Deep Dive"] == "research"  # metadata type is the default bucket


# ---------------------------------------------------------------------------
# app-level API
# ---------------------------------------------------------------------------


def test_app_snooze_archive_restore_cycle(hermes_root: Path) -> None:
    app = DashboardApp(root=hermes_root, opener=lambda cmd: None)
    alpha = project_by_name(app.projects()["projects"], "Alpha Report")

    result = app.snooze(alpha["id"], iso(utcnow() + timedelta(days=3)))
    assert result["bucket"] == "snoozed"

    result = app.archive(alpha["id"])
    assert result["bucket"] == "archived"

    result = app.restore(alpha["id"], "research")
    assert result["bucket"] == "research"

    result = app.move(alpha["id"], "active")
    assert result["bucket"] == "active"

    with pytest.raises(DashboardError) as excinfo:
        app.snooze(alpha["id"], "definitely-not-a-date")
    assert excinfo.value.status == 400

    with pytest.raises(DashboardError) as excinfo:
        app.archive("no-such-project")
    assert excinfo.value.status == 404


def test_search_finds_projects_and_files(hermes_root: Path) -> None:
    app = DashboardApp(root=hermes_root, opener=lambda cmd: None)
    result = app.search("digest")
    file_names = [f["name"] for f in result["files"]]
    assert "digest-final.md" in file_names
    # "digest" appears in Alpha Report's description, so it matches as a project too.
    assert any(p["name"] == "Alpha Report" for p in result["projects"])

    result = app.search("Deep")
    assert any(p["name"] == "Deep Dive" for p in result["projects"])

    assert app.search("")["files"] == []


def test_api_open_rejects_paths_outside_root(hermes_root: Path, tmp_path: Path) -> None:
    launched: list[list[str]] = []
    app = DashboardApp(root=hermes_root, opener=launched.append)

    with pytest.raises(DashboardError) as excinfo:
        app.open_path(str(tmp_path))  # parent of the root, not inside it
    assert excinfo.value.status == 403

    with pytest.raises(DashboardError) as excinfo:
        app.open_path(str(hermes_root / ".." / "somewhere-else"))
    assert excinfo.value.status == 403
    assert launched == []

    result = app.open_path(str(hermes_root / "sessions" / "alpha"))
    assert result["ok"] is True
    assert launched and launched[0][-1].endswith("alpha")

    # A file target opens its containing folder.
    result = app.open_path(str(hermes_root / "sessions" / "alpha" / "digest-final.md"))
    assert result["opened"].endswith("alpha")


def test_health_reads_monitor_status(hermes_root: Path) -> None:
    app = DashboardApp(root=hermes_root, opener=lambda cmd: None)
    assert app.health() == {"health": None}
    monitor = hermes_root / "monitor"
    monitor.mkdir()
    (monitor / "status.json").write_text(json.dumps({"cpu": "ok"}), encoding="utf-8")
    assert app.health() == {"health": {"cpu": "ok"}}
    (monitor / "status.json").write_text("broken{", encoding="utf-8")
    assert app.health() == {"health": None}


# ---------------------------------------------------------------------------
# HTTP layer (real server on port 0)
# ---------------------------------------------------------------------------


@pytest.fixture()
def http_server(hermes_root: Path):
    launched: list[list[str]] = []
    server = serve(root=hermes_root, port=0, opener=launched.append)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        yield base, launched, server.token
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _get(url: str, token: str):
    request = urllib.request.Request(url, headers={"X-LPOS-Token": token})
    with urllib.request.urlopen(request, timeout=10) as response:
        return response.status, json.loads(response.read().decode("utf-8"))


def _post(url: str, payload: dict, token: str):
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "X-LPOS-Token": token},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read().decode("utf-8"))


def test_http_projects_and_ui(http_server) -> None:
    base, _, token = http_server
    status, data = _get(base + "/api/projects", token)
    assert status == 200
    assert {p["name"] for p in data["projects"]} >= {"Alpha Report", "Deep Dive"}
    with urllib.request.urlopen(base + "/", timeout=10) as response:
        html = response.read().decode("utf-8")
    assert response.headers.get_content_type() == "text/html"
    assert "Hermes" in html and "prefers-color-scheme" in html
    # The session token is injected server-side for the page's own fetches.
    assert token in html


def test_http_snooze_and_wake_flow(http_server) -> None:
    base, _, token = http_server
    _, listing = _get(base + "/api/projects", token)
    alpha = project_by_name(listing["projects"], "Alpha Report")

    status, result = _post(
        f"{base}/api/projects/{alpha['id']}/snooze",
        {"until": iso(utcnow() - timedelta(minutes=5))},
        token,
    )
    assert status == 200 and result["bucket"] == "active" and result["woke"] is True

    _, listing = _get(base + "/api/projects", token)
    alpha = project_by_name(listing["projects"], "Alpha Report")
    assert alpha["bucket"] == "active" and alpha["woke"] is True

    status, result = _post(f"{base}/api/projects/{alpha['id']}/archive", {}, token)
    assert status == 200 and result["bucket"] == "archived"
    status, result = _post(
        f"{base}/api/projects/{alpha['id']}/restore", {"bucket": "active"}, token
    )
    assert status == 200 and result["bucket"] == "active" and result["woke"] is False


def test_http_open_and_errors(http_server, hermes_root: Path) -> None:
    base, launched, token = http_server
    status, result = _post(base + "/api/open", {"path": "/etc"}, token)
    assert status == 403 and launched == []
    status, result = _post(
        base + "/api/open", {"path": str(hermes_root / "sessions" / "alpha")}, token
    )
    assert status == 200 and result["ok"] is True and launched

    status, result = _post(base + "/api/projects/nope/move", {"bucket": "active"}, token)
    assert status == 404
    status, _ = _get(base + "/api/health", token)
    assert status == 200

    status, data = _get(base + "/api/search?q=digest", token)
    assert status == 200
    assert any(f["name"] == "digest-final.md" for f in data["files"])
