"""Offline tests for the connector health monitor (SO-023).

No network access anywhere: checks are injected via fake registries, alert
delivery via a recording fake transport, and retry delays via a fake sleep.
"""

from __future__ import annotations

import json
import time

import pytest

from lpos_engine.monitor import (
    HANDLERS,
    alert_connector_transitions,
    audit_connectors,
    discover_connector_inventory,
)
from lpos_engine.monitor import alert as alert_module
from lpos_engine.monitor import audit as audit_module
from lpos_engine.monitor import checks as checks_module
from lpos_engine.monitor import inventory as inventory_module
from lpos_engine.monitor.checks import CheckResult


class FakeTransport(alert_module.Transport):
    def __init__(self, fail: bool = False) -> None:
        self.sent: list[tuple[str, str, str]] = []
        self.fail = fail

    def send(self, subject: str, body: str, recipient: str) -> None:
        if self.fail:
            raise RuntimeError("smtp connection refused")
        self.sent.append((subject, body, recipient))


def _write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def _fake_hermes(tmp_path):
    root = tmp_path / "hermes"
    (root / "mcp-tokens").mkdir(parents=True)
    (root / "mcp-tokens" / "github.json").write_text("{}", encoding="utf-8")
    (root / "mcp-tokens" / "filesystem.json").write_text("{}", encoding="utf-8")
    (root / "gateway" / "slack-bridge").mkdir(parents=True)
    (root / "platforms" / "gmail").mkdir(parents=True)
    _write_json(
        root / "state" / "services.json",
        {
            "services": [
                {
                    "id": "svc:report-api",
                    "name": "Report API",
                    "kind": "self_built",
                    "check": {"type": "http_health", "url": "http://localhost:9999/health"},
                    "criticality": "informational",
                }
            ]
        },
    )
    _write_json(root / "profiles" / "owner.json", {"email": "owner@example.com"})
    return root


def _registry(fn):
    """A registry where every check type resolves to the same fake."""

    return {name: fn for name in checks_module.CHECKS}


def _no_sleep(_seconds):
    return None


# ---------------------------------------------------------------- discovery


def test_discovery_from_fake_hermes_root(tmp_path):
    root = _fake_hermes(tmp_path)
    entries = inventory_module.discover(root)
    ids = {e["id"] for e in entries}
    assert {
        "mcp:github",
        "mcp:filesystem",
        "gateway:slack-bridge",
        "platform:gmail",
        "svc:report-api",
    } <= ids
    by_id = {e["id"]: e for e in entries}
    assert by_id["mcp:github"]["kind"] == "vcs"  # name heuristic
    assert by_id["platform:gmail"]["kind"] == "email"
    assert by_id["gateway:slack-bridge"]["kind"] == "mcp"
    assert by_id["svc:report-api"]["kind"] == "self_built"
    assert by_id["svc:report-api"]["criticality"] == "informational"
    assert all(e["muted"] is False for e in entries)


def test_discovery_defensive_on_empty_root(tmp_path):
    assert inventory_module.discover(tmp_path / "nowhere") == []


def test_hermes_root_env(tmp_path, monkeypatch):
    monkeypatch.setenv("LPOS_HERMES_ROOT", str(tmp_path / "custom"))
    assert inventory_module.hermes_root() == tmp_path / "custom"


def test_merge_preserves_user_edits_and_mutes(tmp_path):
    root = _fake_hermes(tmp_path)
    inventory_module.refresh_inventory(root)
    # Owner edits: mute one connector, reclassify another, keep a retired one.
    entries = inventory_module.load_inventory(root)
    by_id = {e["id"]: e for e in entries}
    by_id["mcp:filesystem"]["muted"] = True
    by_id["mcp:github"]["criticality"] = "informational"
    by_id["mcp:github"]["name"] = "GitHub (primary)"
    entries.append({"id": "retired:old-api", "name": "Old API", "kind": "other"})
    inventory_module.save_inventory(entries, root)

    merged = inventory_module.refresh_inventory(root)
    by_id = {e["id"]: e for e in merged}
    assert by_id["mcp:filesystem"]["muted"] is True
    assert by_id["mcp:github"]["criticality"] == "informational"
    assert by_id["mcp:github"]["name"] == "GitHub (primary)"
    assert "retired:old-api" in by_id  # never silently dropped


# ------------------------------------------------------------------- checks


def test_retry_before_offline(tmp_path):
    calls = []
    sleeps = []

    def flaky(entry, timeout):
        calls.append(entry["id"])
        if len(calls) == 1:
            return CheckResult(ok=False, latency_ms=5, error="blip")
        return CheckResult(ok=True, latency_ms=5)

    entry = {"id": "x", "kind": "mcp", "check": {"type": "mcp_ping"}}
    result = checks_module.run_check(
        entry, registry=_registry(flaky), sleep=sleeps.append, retry_delay=5.0
    )
    assert result is not None and result.ok
    assert len(calls) == 2  # one retry happened before success
    assert sleeps == [5.0]  # short delay between attempts


def test_check_timeout_declares_offline(tmp_path):
    def hung(entry, timeout):
        time.sleep(0.5)
        return CheckResult(ok=True, latency_ms=1)

    entry = {"id": "slow", "kind": "mcp", "check": {"type": "mcp_ping"}}
    result = checks_module.run_check(
        entry, timeout=0.05, registry=_registry(hung), sleep=_no_sleep
    )
    assert result is not None
    assert not result.ok
    assert "timeout" in result.error


def test_unknown_kind_without_check_is_unknown_not_crash(tmp_path):
    entry = {"id": "mystery", "kind": "other", "check": {}}
    assert checks_module.run_check(entry, sleep=_no_sleep) is None


# -------------------------------------------------------------------- audit


def _run_audit(root, ok_map, now):
    """Run an audit where each connector's health comes from ok_map."""

    def fake(entry, timeout):
        healthy = ok_map.get(entry["id"], True)
        if healthy:
            return CheckResult(ok=True, latency_ms=3)
        return CheckResult(ok=False, latency_ms=3, error="connection refused")

    return audit_module.run_audit(
        root, registry=_registry(fake), sleep=_no_sleep, now=now
    )


def test_status_json_contract_shape(tmp_path):
    root = _fake_hermes(tmp_path)
    summary = _run_audit(root, {}, "2026-07-21T10:00:00+00:00")
    doc = json.loads((root / "monitor" / "status.json").read_text(encoding="utf-8"))
    assert set(doc) >= {"generated_at", "overall", "connectors"}
    assert doc["overall"] in ("ok", "degraded")
    assert doc["generated_at"] == "2026-07-21T10:00:00+00:00"
    assert doc["connectors"]
    for connector in doc["connectors"]:
        assert set(connector) >= {
            "id",
            "name",
            "kind",
            "status",
            "latency_ms",
            "error",
            "criticality",
            "last_ok",
            "down_since",
        }
        assert connector["status"] in ("ok", "offline", "unknown")
    assert summary["overall"] == "ok"


def test_audit_transitions_and_history(tmp_path):
    root = _fake_hermes(tmp_path)
    _run_audit(root, {}, "2026-07-21T10:00:00+00:00")
    down = _run_audit(root, {"mcp:github": False}, "2026-07-21T11:00:00+00:00")
    assert down["transitions"]["offline"] == ["mcp:github"]
    assert down["overall"] == "degraded"
    again = _run_audit(root, {"mcp:github": False}, "2026-07-21T12:00:00+00:00")
    assert again["transitions"]["offline"] == []  # already offline: no new transition
    doc = audit_module.load_status(root)
    github = next(c for c in doc["connectors"] if c["id"] == "mcp:github")
    assert github["down_since"] == "2026-07-21T11:00:00+00:00"
    back = _run_audit(root, {}, "2026-07-21T13:00:00+00:00")
    assert back["transitions"]["recovered"] == ["mcp:github"]
    state = json.loads((root / "monitor" / "state.json").read_text(encoding="utf-8"))
    assert len(state["connectors"]["mcp:github"]["history"]) == 4


def test_history_capped(tmp_path):
    root = tmp_path / "hermes"
    (root / "monitor").mkdir(parents=True)
    _write_json(
        root / "monitor" / "inventory.json",
        {"connectors": [{"id": "a", "kind": "mcp", "check": {"type": "mcp_ping"}}]},
    )
    state = {
        "connectors": {
            "a": {
                "status": "ok",
                "history": [{"ts": "t", "status": "ok", "latency_ms": 1, "error": ""}] * 500,
            }
        }
    }
    _write_json(root / "monitor" / "state.json", state)
    _run_audit(root, {}, "2026-07-21T10:00:00+00:00")
    saved = json.loads((root / "monitor" / "state.json").read_text(encoding="utf-8"))
    assert len(saved["connectors"]["a"]["history"]) == 500


def test_auth_expiry_warning(tmp_path):
    root = tmp_path / "hermes"
    (root / "monitor").mkdir(parents=True)
    _write_json(
        root / "monitor" / "inventory.json",
        {
            "connectors": [
                {
                    "id": "gh",
                    "kind": "vcs",
                    "check": {"type": "github_api"},
                    "auth_expires": "2026-07-24T00:00:00+00:00",
                }
            ]
        },
    )
    summary = _run_audit(root, {}, "2026-07-21T10:00:00+00:00")
    assert summary["warnings"] and summary["warnings"][0]["id"] == "gh"
    doc = audit_module.load_status(root)
    assert "auth_warning" in doc["connectors"][0]


def test_muted_entry_not_checked(tmp_path):
    root = tmp_path / "hermes"
    (root / "monitor").mkdir(parents=True)
    _write_json(
        root / "monitor" / "inventory.json",
        {"connectors": [{"id": "m", "kind": "mcp", "check": {"type": "mcp_ping"}, "muted": True}]},
    )
    summary = _run_audit(root, {"m": False}, "2026-07-21T10:00:00+00:00")
    assert summary["checked"] == 0
    assert summary["overall"] == "ok"  # muted offline never degrades or alerts


# ----------------------------------------------------------------- alerting


def test_offline_transition_sends_exactly_one_alert_and_one_recovery(tmp_path):
    root = _fake_hermes(tmp_path)
    transport = FakeTransport()
    _run_audit(root, {}, "2026-07-21T10:00:00+00:00")
    alert_module.run_alert_cycle(root, transport=transport, now="2026-07-21T10:00:05+00:00")
    assert transport.sent == []  # everything healthy: silence

    _run_audit(root, {"mcp:github": False}, "2026-07-21T11:00:00+00:00")
    alert_module.run_alert_cycle(root, transport=transport, now="2026-07-21T11:00:05+00:00")
    assert len(transport.sent) == 1
    subject, body, recipient = transport.sent[0]
    assert subject == "LPOS ALERT: GitHub (primary) offline (connection refused)" or subject.startswith(
        "LPOS ALERT: "
    )
    assert "connection refused" in body
    assert "2026-07-21T11:00:00+00:00" in body  # down since
    assert recipient == "owner@example.com"  # from profiles/owner.json

    # Still down an hour later: no repeat.
    _run_audit(root, {"mcp:github": False}, "2026-07-21T12:00:00+00:00")
    alert_module.run_alert_cycle(root, transport=transport, now="2026-07-21T12:00:05+00:00")
    assert len(transport.sent) == 1

    # Recovery: exactly one all-clear.
    _run_audit(root, {}, "2026-07-21T13:00:00+00:00")
    alert_module.run_alert_cycle(root, transport=transport, now="2026-07-21T13:00:05+00:00")
    assert len(transport.sent) == 2
    assert transport.sent[1][0].startswith("LPOS RECOVERED: ")

    # And silence again after recovery.
    _run_audit(root, {}, "2026-07-21T14:00:00+00:00")
    alert_module.run_alert_cycle(root, transport=transport, now="2026-07-21T14:00:05+00:00")
    assert len(transport.sent) == 2


def test_informational_entry_batches_into_daily_reminder_only(tmp_path):
    root = _fake_hermes(tmp_path)  # svc:report-api is informational
    transport = FakeTransport()
    _run_audit(root, {"svc:report-api": False}, "2026-07-21T10:00:00+00:00")
    alert_module.run_alert_cycle(root, transport=transport, now="2026-07-21T10:00:05+00:00")
    assert transport.sent == []  # informational: no immediate alert

    # 25 hours later, still down: daily reminder fires.
    _run_audit(root, {"svc:report-api": False}, "2026-07-22T11:00:00+00:00")
    alert_module.run_alert_cycle(root, transport=transport, now="2026-07-22T11:00:05+00:00")
    assert len(transport.sent) == 1
    assert transport.sent[0][0].startswith("LPOS REMINDER: ")

    # Another hour later: reminder does not repeat within 24h.
    _run_audit(root, {"svc:report-api": False}, "2026-07-22T12:00:00+00:00")
    alert_module.run_alert_cycle(root, transport=transport, now="2026-07-22T12:00:05+00:00")
    assert len(transport.sent) == 1


def test_alert_covers_everything_currently_down(tmp_path):
    root = _fake_hermes(tmp_path)
    transport = FakeTransport()
    _run_audit(
        root,
        {"mcp:github": False, "gateway:slack-bridge": False},
        "2026-07-21T10:00:00+00:00",
    )
    alert_module.run_alert_cycle(root, transport=transport, now="2026-07-21T10:00:05+00:00")
    assert len(transport.sent) == 1
    subject, body, _ = transport.sent[0]
    assert subject == "LPOS ALERT: 2 connectors offline"
    assert "mcp:github" in body and "gateway:slack-bridge" in body
    assert "likely fix" in body


def test_fallback_writes_alert_undelivered(tmp_path):
    root = _fake_hermes(tmp_path)
    _run_audit(root, {"mcp:github": False}, "2026-07-21T10:00:00+00:00")
    result = alert_module.run_alert_cycle(
        root, transport=FakeTransport(fail=True), now="2026-07-21T10:00:05+00:00"
    )
    assert result["attempted"] == 1
    assert result["delivered"] is False
    marker = root / "monitor" / "ALERT-UNDELIVERED.json"
    assert marker.exists()
    payload = json.loads(marker.read_text(encoding="utf-8"))
    assert payload["undelivered"] and "smtp connection refused" in payload["reason"]

    # The handler surfaces the failure as an exception (nonzero workflow result).
    with pytest.raises(RuntimeError):
        alert_connector_transitions({"hermes_root": str(root)})

    # Next cycle with a working transport retries (dedup state was not marked).
    transport = FakeTransport()
    alert_module.run_alert_cycle(root, transport=transport, now="2026-07-21T11:00:05+00:00")
    assert len(transport.sent) == 1
    assert not marker.exists()  # delivered cycle clears the loud marker


def test_no_transport_configured_counts_as_undelivered(tmp_path):
    root = _fake_hermes(tmp_path)
    _run_audit(root, {"mcp:github": False}, "2026-07-21T10:00:00+00:00")
    result = alert_module.run_alert_cycle(root, transport=None, now="2026-07-21T10:00:05+00:00")
    assert result["delivered"] is False
    assert (root / "monitor" / "ALERT-UNDELIVERED.json").exists()


def test_recipient_falls_back_to_env(tmp_path, monkeypatch):
    monkeypatch.setenv("LPOS_OWNER_EMAIL", "fallback@example.com")
    assert alert_module.resolve_recipient(tmp_path / "empty") == "fallback@example.com"


# ------------------------------------------------------------ SO-023 wiring


def test_handlers_mapping_and_workflow_definition(tmp_path):
    assert set(HANDLERS) == {
        "discover_connector_inventory",
        "audit_connectors",
        "alert_connector_transitions",
    }
    from importlib.resources import files

    raw = json.loads(
        files("lpos_engine.workflows").joinpath("SO-023.json").read_text(encoding="utf-8")
    )
    from lpos_engine.models import WorkflowDefinition

    definition = WorkflowDefinition.from_dict(raw)
    assert definition.so_id == "SO-023"
    assert [step.handler for step in definition.steps] == [
        "discover_connector_inventory",
        "audit_connectors",
        "alert_connector_transitions",
    ]
    assert all(step.handler in HANDLERS for step in definition.steps)


def test_handlers_run_end_to_end_with_freeze(tmp_path, monkeypatch):
    """Handlers return freeze_mapping-compatible mappings (runner contract)."""

    from lpos_engine.canonical import freeze_mapping

    root = _fake_hermes(tmp_path)
    context = {"hermes_root": str(root)}
    discovered = discover_connector_inventory(context)
    assert discovered["connector_count"] >= 5
    freeze_mapping(discovered)

    # Patch the default check path so the audit handler stays offline-safe.
    monkeypatch.setattr(
        checks_module,
        "CHECKS",
        _registry(lambda entry, timeout: CheckResult(ok=True, latency_ms=1)),
    )
    audited = audit_connectors(context)
    assert audited["overall"] == "ok"
    freeze_mapping(audited)

    result = alert_connector_transitions(context)  # nothing down: nothing attempted
    assert result["attempted"] == 0
    freeze_mapping(result)


def test_main_audit_cli_offline(tmp_path, monkeypatch, capsys):
    from lpos_engine.monitor.__main__ import main

    root = _fake_hermes(tmp_path)
    monkeypatch.setattr(
        checks_module,
        "CHECKS",
        _registry(lambda entry, timeout: CheckResult(ok=True, latency_ms=1)),
    )
    code = main(["--root", str(root), "audit", "--no-alert"])
    assert code == 0
    out = json.loads(capsys.readouterr().out)
    assert out["overall"] == "ok"
    assert (root / "monitor" / "status.json").exists()
