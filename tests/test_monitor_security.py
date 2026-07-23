"""Adversarial regressions for monitor security findings LPOS-03 and LPOS-04.

Every test is fully offline: no real network and no real credential leaves the
process.  Fake resolvers (monkeypatched ``socket.getaddrinfo``), a fake
``urlopen`` that records requests, and marker-file payloads mirror the audit's
own reproduction (``evidence/reproduce_findings.py`` -> ``monitor_repro``).

The findings:

- LPOS-03: agent-registered service definitions must never execute a shell
  string or an arbitrary argv; only admin-approved templates run, argv-only.
- LPOS-04: connector credentials are bound to the GitHub API origin, token
  files must live in the approved secrets dir, and all URL/host checks refuse
  loopback/private/metadata addresses and redirects unless approved.
"""

from __future__ import annotations

import json
import os
import socket

import pytest

from lpos_engine.monitor import approved as approved_module
from lpos_engine.monitor import audit as audit_module
from lpos_engine.monitor import checks as checks_module
from lpos_engine.monitor import inventory as inventory_module
from lpos_engine.monitor.alert import CommandTransport


def _write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def _no_sleep(_seconds):
    return None


# ============================================================ LPOS-03: command


def test_agent_registered_shell_string_never_executes(tmp_path):
    """Mirror the audit: a registered shell-string payload must not run."""

    root = tmp_path / "hermes"
    marker = tmp_path / "agent-registered-shell-marker.txt"
    _write_json(
        root / "state" / "services.json",
        {
            "services": [
                {
                    "id": "agent-owned-service",
                    "name": "Agent-owned service",
                    "kind": "self_built",
                    "criticality": "critical",
                    "check": {
                        "type": "command",
                        "command": f"printf pwned > {marker}",
                    },
                }
            ]
        },
    )
    summary = audit_module.run_audit(root, timeout=2, retry_delay=0, sleep=_no_sleep)

    assert not marker.exists()  # the payload never ran
    doc = audit_module.load_status(root)
    svc = next(c for c in doc["connectors"] if c["id"] == "agent-owned-service")
    assert svc["status"] == "unknown"
    assert svc["error"] == "unapproved check definition"
    assert svc.get("unapproved_check") is True
    assert "agent-owned-service" in summary["unknown"]
    assert summary["overall"] == "ok"  # unapproved != offline


def test_agent_argv_form_not_executed_without_approved_template(tmp_path):
    """Even an argv (non-shell) agent definition is refused without approval."""

    root = tmp_path / "hermes"
    marker = tmp_path / "argv-marker.txt"
    _write_json(
        root / "state" / "services.json",
        {
            "services": [
                {
                    "id": "svc:argv",
                    "kind": "self_built",
                    "check": {"type": "command", "argv": ["/usr/bin/touch", str(marker)]},
                }
            ]
        },
    )
    audit_module.run_audit(root, timeout=2, retry_delay=0, sleep=_no_sleep)
    assert not marker.exists()
    doc = audit_module.load_status(root)
    svc = next(c for c in doc["connectors"] if c["id"] == "svc:argv")
    assert svc["status"] == "unknown"
    assert svc["error"] == "unapproved check definition"


def test_approved_template_with_parameters_executes_argv_only(tmp_path):
    """An admin template runs argv-only and fills declared placeholders."""

    root = tmp_path / "hermes"
    marker = tmp_path / "approved-marker.txt"
    _write_json(
        root / "monitor" / "approved-checks.json",
        {
            "checks": {
                "make-marker": {
                    "type": "command",
                    "argv": ["/usr/bin/touch", "{path}"],
                    "parameters": ["path"],
                    "description": "touch a file (admin approved)",
                }
            }
        },
    )
    _write_json(
        root / "state" / "services.json",
        {
            "services": [
                {
                    "id": "svc:approved",
                    "kind": "self_built",
                    "check": {"check_id": "make-marker", "params": {"path": str(marker)}},
                }
            ]
        },
    )
    audit_module.run_audit(root, timeout=5, retry_delay=0, sleep=_no_sleep)
    assert marker.exists()  # approved template executed
    doc = audit_module.load_status(root)
    svc = next(c for c in doc["connectors"] if c["id"] == "svc:approved")
    assert svc["status"] == "ok"


def test_shell_metacharacters_in_parameters_are_inert(tmp_path):
    """A shell metacharacter payload in a param is a literal argv element."""

    root = tmp_path / "hermes"
    sentinel = tmp_path / "injected.txt"
    payload = f"; touch {sentinel}"
    _write_json(
        root / "monitor" / "approved-checks.json",
        {
            "checks": {
                "echo-arg": {
                    "type": "command",
                    "argv": ["/bin/echo", "{msg}"],
                    "parameters": ["msg"],
                }
            }
        },
    )
    _write_json(
        root / "state" / "services.json",
        {
            "services": [
                {
                    "id": "svc:inject",
                    "kind": "self_built",
                    "check": {"check_id": "echo-arg", "params": {"msg": payload}},
                }
            ]
        },
    )
    audit_module.run_audit(root, timeout=5, retry_delay=0, sleep=_no_sleep)
    assert not sentinel.exists()  # no shell interpreted the metacharacters
    doc = audit_module.load_status(root)
    svc = next(c for c in doc["connectors"] if c["id"] == "svc:inject")
    assert svc["status"] == "ok"  # echo exits 0; the ; was a literal arg


def test_command_check_refuses_direct_shell_string(tmp_path):
    """check_command never honours a shell string, even if marked approved."""

    marker = tmp_path / "direct.txt"
    entry = {
        "id": "d",
        "check": {"_approved": True, "command": f"printf x > {marker}", "type": "command"},
    }
    result = checks_module.check_command(entry, timeout=2)
    assert not marker.exists()
    assert not result.ok
    assert "shell command strings are not supported" in result.error


def test_command_executable_outside_allowed_dirs_refused(tmp_path):
    """An absolute executable outside /usr,/bin,/sbin,/opt,approved is refused."""

    fake = tmp_path / "evil.sh"
    fake.write_text("#!/bin/sh\ntrue\n", encoding="utf-8")
    os.chmod(fake, 0o755)
    entry = {
        "id": "e",
        "check": {"_approved": True, "type": "command", "argv": [str(fake)]},
    }
    result = checks_module.check_command(entry, timeout=2)
    assert not result.ok
    assert "outside the allowed directories" in result.error


def test_command_relative_executable_refused():
    entry = {"id": "r", "check": {"_approved": True, "type": "command", "argv": ["touch", "x"]}}
    result = checks_module.check_command(entry, timeout=2)
    assert not result.ok
    assert "absolute path" in result.error


def test_command_timeout_kills_process_group(tmp_path):
    entry = {
        "id": "slow",
        "check": {"_approved": True, "type": "command", "argv": ["/bin/sleep", "30"]},
    }
    result = checks_module.check_command(entry, timeout=0.3)
    assert not result.ok
    assert "timed out" in result.error


def test_command_transport_argv_only():
    """CommandTransport refuses shell strings at construction (LPOS-03)."""

    with pytest.raises(TypeError):
        CommandTransport("sendmail -t")
    transport = CommandTransport(["/bin/cat"])
    assert transport.command == ["/bin/cat"]


# ============================================================= LPOS-04: egress


class _RecordingOpener:
    """Fake urlopen that records the request and never touches the network."""

    def __init__(self):
        self.requests = []

    def __call__(self, request, timeout):
        self.requests.append(request)

        class _Resp:
            status = 200

            def __enter__(self_inner):
                return self_inner

            def __exit__(self_inner, *exc):
                return False

        return _Resp()


def _github_secret_file(root, value="AUDIT-CANARY-SECRET"):
    secrets = root / "monitor" / "secrets"
    secrets.mkdir(parents=True, exist_ok=True)
    token_file = secrets / "github-token.txt"
    token_file.write_text(value, encoding="utf-8")
    os.chmod(token_file, 0o600)
    return token_file


def test_token_not_sent_to_non_github_origin(tmp_path, monkeypatch):
    """The canary token is never attached to an attacker-chosen URL."""

    root = tmp_path / "hermes"
    token_file = _github_secret_file(root)
    recorder = _RecordingOpener()
    monkeypatch.setattr(checks_module, "_urlopen", recorder)

    effective, refusal = approved_module.resolve_execution_entry(
        {
            "id": "canary-vcs",
            "kind": "vcs",
            "check": {
                "type": "github_api",
                "url": "http://attacker.example/capture",
                "token_file": str(token_file),
            },
        },
        root,
    )
    assert refusal is None
    result = checks_module.check_github_api(effective, timeout=2)
    assert not result.ok
    assert result.error == "refused: token bound to api.github.com"
    assert recorder.requests == []  # never dialed out with the token


def test_token_attached_only_for_github_origin(tmp_path, monkeypatch):
    root = tmp_path / "hermes"
    token_file = _github_secret_file(root)
    recorder = _RecordingOpener()
    monkeypatch.setattr(checks_module, "_urlopen", recorder)

    effective, _ = approved_module.resolve_execution_entry(
        {
            "id": "gh",
            "kind": "vcs",
            "check": {"type": "github_api", "token_file": str(token_file)},
        },
        root,
    )
    result = checks_module.check_github_api(effective, timeout=2)
    assert result.ok
    assert len(recorder.requests) == 1
    assert recorder.requests[0].get_header("Authorization") == "Bearer AUDIT-CANARY-SECRET"


def test_token_file_outside_secrets_dir_rejected_before_network(tmp_path, monkeypatch):
    root = tmp_path / "hermes"
    (root / "monitor" / "secrets").mkdir(parents=True)
    outside = tmp_path / "elsewhere" / "token.txt"
    outside.parent.mkdir(parents=True)
    outside.write_text("SECRET", encoding="utf-8")
    recorder = _RecordingOpener()
    monkeypatch.setattr(checks_module, "_urlopen", recorder)

    effective, _ = approved_module.resolve_execution_entry(
        {"id": "gh", "kind": "vcs", "check": {"type": "github_api", "token_file": str(outside)}},
        root,
    )
    result = checks_module.check_github_api(effective, timeout=2)
    assert not result.ok
    assert "must resolve inside" in result.error
    assert recorder.requests == []


def test_symlinked_token_file_rejected(tmp_path, monkeypatch):
    root = tmp_path / "hermes"
    secrets = root / "monitor" / "secrets"
    secrets.mkdir(parents=True)
    real = tmp_path / "outside-secret.txt"
    real.write_text("SECRET", encoding="utf-8")
    link = secrets / "token.txt"
    os.symlink(real, link)
    recorder = _RecordingOpener()
    monkeypatch.setattr(checks_module, "_urlopen", recorder)

    effective, _ = approved_module.resolve_execution_entry(
        {"id": "gh", "kind": "vcs", "check": {"type": "github_api", "token_file": str(link)}},
        root,
    )
    result = checks_module.check_github_api(effective, timeout=2)
    assert not result.ok
    assert "must resolve inside" in result.error
    assert recorder.requests == []


def test_token_redacted_from_errors(tmp_path, monkeypatch):
    """A token value never appears in error strings (redaction)."""

    root = tmp_path / "hermes"
    token_file = _github_secret_file(root, "SUPER-SECRET-TOKEN")

    def _boom(request, timeout):
        raise OSError("connection to SUPER-SECRET-TOKEN failed")

    monkeypatch.setattr(checks_module, "_urlopen", _boom)
    effective, _ = approved_module.resolve_execution_entry(
        {"id": "gh", "kind": "vcs", "check": {"type": "github_api", "token_file": str(token_file)}},
        root,
    )
    result = checks_module.check_github_api(effective, timeout=2)
    assert "SUPER-SECRET-TOKEN" not in result.error
    assert "[REDACTED]" in result.error


def _fake_resolver(mapping):
    def _getaddrinfo(host, *args, **kwargs):
        ip = mapping.get(host, "140.82.112.10")  # default: public TEST-NET-3
        return [(socket.AF_INET, socket.SOCK_STREAM, 0, "", (ip, 0))]

    return _getaddrinfo


@pytest.mark.parametrize(
    "ip",
    [
        "127.0.0.1",  # loopback
        "169.254.169.254",  # cloud metadata
        "169.254.1.1",  # link-local
        "10.1.2.3",  # private /8
        "172.16.0.5",  # private /12
        "192.168.1.1",  # private /16
        "0.0.0.0",  # unspecified
        "224.0.0.1",  # multicast
    ],
)
def test_agent_url_private_and_metadata_addresses_refused(tmp_path, monkeypatch, ip):
    monkeypatch.setattr(socket, "getaddrinfo", _fake_resolver({"internal.example": ip}))
    entry = {"id": "u", "kind": "self_built", "check": {"type": "http_health", "url": "http://internal.example/x"}}
    effective, _ = approved_module.resolve_execution_entry(entry, tmp_path / "hermes")
    result = checks_module.check_http_health(effective, timeout=2)
    assert not result.ok
    assert "refused" in result.error


def test_ipv6_loopback_and_ula_refused(tmp_path, monkeypatch):
    def _getaddrinfo(host, *args, **kwargs):
        return [(socket.AF_INET6, socket.SOCK_STREAM, 0, "", ("fc00::1", 0, 0, 0))]

    monkeypatch.setattr(socket, "getaddrinfo", _getaddrinfo)
    entry = {"id": "u6", "kind": "self_built", "check": {"type": "http_health", "url": "http://internal6.example/x"}}
    effective, _ = approved_module.resolve_execution_entry(entry, tmp_path / "hermes")
    result = checks_module.check_http_health(effective, timeout=2)
    assert not result.ok
    assert "refused" in result.error


def test_approved_template_may_reach_localhost(tmp_path, monkeypatch):
    """A template with private_network_approved reaches localhost; agent cannot."""

    root = tmp_path / "hermes"
    _write_json(
        root / "monitor" / "approved-checks.json",
        {
            "checks": {
                "local": {
                    "type": "http_health",
                    "url": "http://127.0.0.1:{port}/health",
                    "parameters": ["port"],
                    "private_network_approved": True,
                }
            }
        },
    )
    recorder = _RecordingOpener()
    monkeypatch.setattr(checks_module, "_urlopen", recorder)
    monkeypatch.setattr(socket, "getaddrinfo", _fake_resolver({"127.0.0.1": "127.0.0.1"}))

    effective, refusal = approved_module.resolve_execution_entry(
        {
            "id": "svc:local",
            "kind": "self_built",
            "check": {"check_id": "local", "params": {"port": 8080}},
        },
        root,
    )
    assert refusal is None
    result = checks_module.check_http_health(effective, timeout=2)
    assert result.ok
    assert len(recorder.requests) == 1


def test_agent_cannot_self_grant_private_network(tmp_path, monkeypatch):
    """An inline private_network_approved flag from agent state is stripped."""

    monkeypatch.setattr(socket, "getaddrinfo", _fake_resolver({"127.0.0.1": "127.0.0.1"}))
    entry = {
        "id": "u",
        "kind": "self_built",
        "check": {"type": "http_health", "url": "http://127.0.0.1/x", "private_network_approved": True},
    }
    effective, _ = approved_module.resolve_execution_entry(entry, tmp_path / "hermes")
    assert "private_network_approved" not in effective["check"]
    result = checks_module.check_http_health(effective, timeout=2)
    assert not result.ok
    assert "refused" in result.error


def test_redirect_refused(tmp_path, monkeypatch):
    root = tmp_path / "hermes"
    import urllib.error

    def _redirecting(request, timeout):
        raise urllib.error.HTTPError(request.full_url, 302, "Found", {}, None)

    monkeypatch.setattr(checks_module, "_urlopen", _redirecting)
    monkeypatch.setattr(socket, "getaddrinfo", _fake_resolver({"ok.example": "140.82.112.5"}))
    entry = {"id": "r", "kind": "self_built", "check": {"type": "http_health", "url": "http://ok.example/x"}}
    effective, _ = approved_module.resolve_execution_entry(entry, root)
    result = checks_module.check_http_health(effective, timeout=2)
    assert not result.ok
    assert result.error == "redirect refused"


def test_non_http_scheme_refused(tmp_path):
    entry = {"id": "f", "kind": "self_built", "check": {"type": "http_health", "url": "file:///etc/passwd"}}
    effective, _ = approved_module.resolve_execution_entry(entry, tmp_path / "hermes")
    result = checks_module.check_http_health(effective, timeout=2)
    assert not result.ok
    assert "scheme" in result.error


def test_url_userinfo_refused(tmp_path, monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", _fake_resolver({"api.github.com": "140.82.112.5"}))
    entry = {
        "id": "u",
        "kind": "self_built",
        "check": {"type": "http_health", "url": "http://user@api.github.com@evil.example/"},
    }
    effective, _ = approved_module.resolve_execution_entry(entry, tmp_path / "hermes")
    result = checks_module.check_http_health(effective, timeout=2)
    assert not result.ok
    assert "refused" in result.error


# =================================================== inventory sanitization


def test_inventory_flags_unapproved_agent_check(tmp_path):
    root = tmp_path / "hermes"
    _write_json(
        root / "state" / "services.json",
        {
            "services": [
                {"id": "svc:x", "check": {"type": "command", "command": "rm -rf /"}},
                {"id": "svc:y", "check": {"check_id": "approved-thing", "params": {"n": 1}}},
            ]
        },
    )
    entries = inventory_module.discover(root)
    by_id = {e["id"]: e for e in entries}
    assert by_id["svc:x"]["unapproved_check"] is True
    assert by_id["svc:x"]["check"] == {}
    assert by_id["svc:y"].get("unapproved_check") is None
    assert by_id["svc:y"]["check"] == {"check_id": "approved-thing", "params": {"n": 1}}


def test_agent_state_cannot_override_approved_template(tmp_path):
    """Merge fills only missing fields; agent state can't replace a template."""

    root = tmp_path / "hermes"
    _write_json(
        root / "monitor" / "approved-checks.json",
        {"checks": {"safe": {"type": "http_health", "url": "https://ok.example/health"}}},
    )
    # Owner inventory references the approved template.
    _write_json(
        root / "monitor" / "inventory.json",
        {"connectors": [{"id": "svc:z", "kind": "self_built", "check": {"check_id": "safe"}}]},
    )
    # Agent state tries to redefine the same id with an inline command.
    _write_json(
        root / "state" / "services.json",
        {"services": [{"id": "svc:z", "check": {"type": "command", "command": "evil"}}]},
    )
    merged = inventory_module.refresh_inventory(root)
    by_id = {e["id"]: e for e in merged}
    assert by_id["svc:z"]["check"] == {"check_id": "safe"}  # owner edit wins
