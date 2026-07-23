"""Owner alerting with transition/recovery logic and a loud fallback.

Rules (spec §5):

- On transition to offline (after the retry) send ONE email covering
  everything currently down: connector, exact error, down-since, and a likely
  fix hint inferred from the connector kind.
- On recovery, one short all-clear.
- While a known outage continues, no repeat emails — except a daily reminder
  for anything still down after 24 h.  ``informational`` entries never trigger
  an immediate alert; they batch into the daily reminder only.
- If the primary send path fails (or none is configured while alerts are
  pending), write ``<root>/monitor/ALERT-UNDELIVERED.json`` loudly and report
  failure so the caller can exit nonzero.  The monitor is never silenced by
  the failure of its own alert channel.

Dedup state lives in ``<root>/monitor/alerts.json``.
"""

from __future__ import annotations

import json
import os
import ssl
import subprocess
from collections.abc import Mapping
from datetime import timedelta
from pathlib import Path
from typing import Any

from .audit import load_status, parse_iso, utc_now_iso
from .inventory import hermes_root, monitor_dir

REMINDER_INTERVAL = timedelta(hours=24)

FIX_HINTS: dict[str, str] = {
    "email": "Check SMTP/IMAP credentials; refresh the app password or re-run mail setup.",
    "vcs": "Token likely expired — regenerate the GitHub token and update the stored credential.",
    "cloud": "Re-authenticate the cloud credentials (refresh the session or rotate keys).",
    "mcp": "Restart or re-register the MCP server; verify its token under mcp-tokens/.",
    "self_built": "Restart the service and verify its /health endpoint responds 200.",
    "other": "Verify network reachability and credentials for this connector.",
}


class Transport:
    """Abstract alert delivery channel."""

    def send(self, subject: str, body: str, recipient: str) -> None:  # pragma: no cover
        raise NotImplementedError


class SMTPTransport(Transport):
    """Primary path: SMTP config from <root>/monitor/smtp.json.

    Config: {host, port, starttls, username, password_file, from}.
    Credentials are read in place; never copied into monitor state.
    """

    def __init__(self, config: Mapping[str, Any]) -> None:
        self.config = dict(config)

    def send(self, subject: str, body: str, recipient: str) -> None:
        import smtplib
        from email.message import EmailMessage

        cfg = self.config
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = str(cfg.get("from") or cfg.get("username") or "lpos-monitor")
        message["To"] = recipient
        message.set_content(body)
        with smtplib.SMTP(str(cfg["host"]), int(cfg.get("port", 587)), timeout=30) as client:
            if cfg.get("starttls"):
                client.starttls(context=ssl.create_default_context())
            username = cfg.get("username")
            password_file = cfg.get("password_file")
            if username and password_file:
                password = (
                    Path(os.path.expanduser(str(password_file)))
                    .read_text(encoding="utf-8")
                    .strip()
                )
                client.login(str(username), password)
            client.send_message(message)


class CommandTransport(Transport):
    """Sendmail-style command: full RFC822-ish message piped to stdin.

    Argv lists only — shell strings are refused (audit LPOS-03): the command
    is executed directly with ``shell=False``, so metacharacters in subjects,
    bodies, or configuration are never interpreted by a shell.
    """

    def __init__(self, command: list[str]) -> None:
        if (
            isinstance(command, str)
            or not isinstance(command, list)
            or not command
            or not all(isinstance(item, str) for item in command)
        ):
            raise TypeError(
                "CommandTransport requires an argv list of strings; "
                "shell command strings are not supported"
            )
        self.command = list(command)

    def send(self, subject: str, body: str, recipient: str) -> None:
        payload = f"To: {recipient}\nSubject: {subject}\n\n{body}\n"
        completed = subprocess.run(  # noqa: S603 - argv list, never a shell
            self.command,
            shell=False,
            input=payload,
            text=True,
            capture_output=True,
            timeout=60,
        )
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout or "").strip()[:512]
            raise RuntimeError(f"alert command exited {completed.returncode}: {detail}")


def load_transport(root: Path | None = None) -> Transport | None:
    """Build the configured primary transport, or None if none is configured.

    A legacy string ``command`` is treated as unconfigured (shell execution
    was removed, LPOS-03); reconfigure it as an argv list.
    """

    path = monitor_dir(root) / "smtp.json"
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(config, Mapping):
        return None
    if config.get("command"):
        try:
            return CommandTransport(config["command"])
        except TypeError:
            return None
    if config.get("host"):
        return SMTPTransport(config)
    return None


def resolve_recipient(root: Path | None = None) -> str:
    base = Path(root) if root is not None else hermes_root()
    try:
        owner = json.loads((base / "profiles" / "owner.json").read_text(encoding="utf-8"))
        if isinstance(owner, Mapping) and owner.get("email"):
            return str(owner["email"])
    except (OSError, ValueError):
        pass
    return os.environ.get("LPOS_OWNER_EMAIL", "")


def alerts_path(root: Path | None = None) -> Path:
    return monitor_dir(root) / "alerts.json"


def undelivered_path(root: Path | None = None) -> Path:
    return monitor_dir(root) / "ALERT-UNDELIVERED.json"


def _load_alert_state(root: Path | None) -> dict[str, Any]:
    try:
        value = json.loads(alerts_path(root).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        value = None
    if not isinstance(value, Mapping):
        value = {}
    return {
        "alerted": dict(value.get("alerted") or {}),
        "last_reminder_at": value.get("last_reminder_at"),
        "history": list(value.get("history") or [])[-200:],
    }


def _save_alert_state(state: Mapping[str, Any], root: Path | None) -> None:
    path = alerts_path(root)
    tmp = path.with_suffix(".json.tmp")
    from ..store import harden_file_mode, secure_create_file

    secure_create_file(tmp)  # LPOS-15
    tmp.write_text(json.dumps(dict(state), indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)
    harden_file_mode(path)


def _short_reason(error: str) -> str:
    reason = (error or "").strip().splitlines()[0] if error else ""
    reason = reason or "unreachable"
    return reason[:48].rstrip()


def _down_line(connector: Mapping[str, Any]) -> str:
    hint = FIX_HINTS.get(str(connector.get("kind", "other")), FIX_HINTS["other"])
    return (
        f"- {connector.get('name')} ({connector.get('id')}, {connector.get('kind')})\n"
        f"    error: {connector.get('error') or 'unreachable'}\n"
        f"    down since: {connector.get('down_since') or 'unknown'}\n"
        f"    likely fix: {hint}"
    )


def build_alert_message(down: list[Mapping[str, Any]]) -> tuple[str, str]:
    if len(down) == 1:
        subject = f"LPOS ALERT: {down[0].get('name')} offline ({_short_reason(str(down[0].get('error', '')))})"
    else:
        subject = f"LPOS ALERT: {len(down)} connectors offline"
    body_lines = ["The LPOS connector health monitor found the following offline:", ""]
    body_lines.extend(_down_line(c) for c in down)
    body_lines += ["", "You will get one all-clear when they recover, and a daily reminder while they stay down."]
    return subject, "\n".join(body_lines)


def build_recovery_message(recovered: list[Mapping[str, Any]]) -> tuple[str, str]:
    if len(recovered) == 1:
        subject = f"LPOS RECOVERED: {recovered[0].get('name')}"
    else:
        subject = f"LPOS RECOVERED: {len(recovered)} connectors"
    lines = ["All clear — the following connectors are reachable again:", ""]
    lines.extend(f"- {c.get('name')} ({c.get('id')})" for c in recovered)
    return subject, "\n".join(lines)


def build_reminder_message(
    still_down: list[Mapping[str, Any]], warnings: list[Mapping[str, Any]]
) -> tuple[str, str]:
    subject = f"LPOS REMINDER: {len(still_down)} connector(s) still offline"
    lines = ["Daily reminder — still offline after 24h:", ""]
    lines.extend(_down_line(c) for c in still_down)
    if warnings:
        lines += ["", "Credential expiry warnings:"]
        lines.extend(f"- {w.get('id')}: {w.get('auth_warning')}" for w in warnings)
    return subject, "\n".join(lines)


def run_alert_cycle(
    root: Path | None = None,
    *,
    transport: Transport | None = None,
    recipient: str | None = None,
    now: str | None = None,
) -> dict[str, Any]:
    """Read status.json, decide what to send, send it, persist dedup state.

    Purely file-driven, so it works both as a workflow step after the audit
    and standalone.  Transition-to-offline is "offline in status.json and not
    yet in alerts.json"; recovery is "ok in status.json and still recorded as
    alerted".  Returns {"attempted", "delivered", "sent", ...}.
    """

    base = Path(root) if root is not None else hermes_root()
    now_iso = now or utc_now_iso()
    now_dt = parse_iso(now_iso)
    status = load_status(base)
    alert_state = _load_alert_state(base)
    if transport is None:
        transport = load_transport(base)
    if recipient is None:
        recipient = resolve_recipient(base)

    connectors = [c for c in status.get("connectors", []) if isinstance(c, Mapping)]
    down = [c for c in connectors if c.get("status") == "offline" and not c.get("muted")]
    down_critical = [c for c in down if str(c.get("criticality", "critical")) == "critical"]
    new_critical = [c for c in down_critical if str(c.get("id")) not in alert_state["alerted"]]
    recovered = [
        c
        for c in connectors
        if c.get("status") == "ok" and str(c.get("id")) in alert_state["alerted"]
    ]
    warnings = [c for c in connectors if c.get("auth_warning")]

    messages: list[dict[str, Any]] = []
    if new_critical:
        subject, body = build_alert_message(down_critical)
        messages.append(
            {"type": "alert", "subject": subject, "body": body, "ids": [str(c["id"]) for c in down_critical]}
        )
    if recovered:
        subject, body = build_recovery_message(recovered)
        messages.append(
            {"type": "recovery", "subject": subject, "body": body, "ids": [str(c["id"]) for c in recovered]}
        )

    still_down = []
    for connector in down:  # includes informational entries: reminder only
        since = parse_iso(connector.get("down_since"))
        if since is not None and now_dt is not None and now_dt - since >= REMINDER_INTERVAL:
            still_down.append(connector)
    if still_down:
        last_reminder = parse_iso(alert_state.get("last_reminder_at"))
        if last_reminder is None or (now_dt is not None and now_dt - last_reminder >= REMINDER_INTERVAL):
            subject, body = build_reminder_message(still_down, warnings)
            messages.append(
                {"type": "reminder", "subject": subject, "body": body, "ids": [str(c["id"]) for c in still_down]}
            )

    result: dict[str, Any] = {
        "attempted": len(messages),
        "delivered": True,
        "sent": [],
        "recipient": recipient,
        "generated_at": now_iso,
    }
    if not messages:
        _save_alert_state(alert_state, base)
        return result

    failure = ""
    if transport is None:
        failure = "no alert transport configured (missing <root>/monitor/smtp.json)"
    else:
        for message in messages:
            try:
                transport.send(message["subject"], message["body"], recipient)
            except Exception as exc:
                failure = f"{type(exc).__name__}: {exc}"
                break
            result["sent"].append(message["subject"])
            if message["type"] == "alert":
                for entry_id in message["ids"]:
                    alert_state["alerted"][entry_id] = {"alerted_at": now_iso}
            elif message["type"] == "recovery":
                for entry_id in message["ids"]:
                    alert_state["alerted"].pop(entry_id, None)
            elif message["type"] == "reminder":
                alert_state["last_reminder_at"] = now_iso
            alert_state["history"].append(
                {"ts": now_iso, "type": message["type"], "subject": message["subject"]}
            )

    if failure:
        result["delivered"] = False
        result["error"] = failure
        pending = messages[len(result["sent"]):]
        payload = {
            "written_at": now_iso,
            "reason": failure,
            "recipient": recipient,
            "undelivered": [
                {"type": m["type"], "subject": m["subject"], "body": m["body"]} for m in pending
            ],
        }
        path = undelivered_path(base)
        tmp = path.with_suffix(".json.tmp")
        from ..store import harden_file_mode, secure_create_file

        secure_create_file(tmp)  # LPOS-15
        tmp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        os.replace(tmp, path)
        harden_file_mode(path)
        result["undelivered_path"] = str(path)
    else:
        # A fully delivered cycle clears any stale undelivered marker.
        try:
            undelivered_path(base).unlink(missing_ok=True)
        except OSError:
            pass

    alert_state["history"] = alert_state["history"][-200:]
    _save_alert_state(alert_state, base)
    return result
