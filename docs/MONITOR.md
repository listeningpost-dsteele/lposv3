# Connector Health Monitor (SO-023)

LPOS runs on external services — email, GitHub, cloud providers, MCP
connectors, and APIs the system built for itself. The monitor discovers all of
them, audits them hourly, publishes a stable `status.json`, and emails the
owner on offline/recovery transitions. It is stdlib-only, fully local, and a
short-lived job: it wakes, checks, records, alerts if needed, and exits.

- Package: `src/lpos_engine/monitor/` (`inventory.py`, `checks.py`,
  `audit.py`, `alert.py`, `approved.py`)
- Workflow: `SO-023` (`src/lpos_engine/workflows/SO-023.json`), steps
  STEP-DISCOVER → STEP-AUDIT → STEP-ALERT
- State: `<hermes root>/monitor/` where the root is `$LPOS_HERMES_ROOT`
  (default `~/.hermes`)

On-demand invocation for debugging:

```sh
python -m lpos_engine.monitor audit             # discover + audit + alert
python -m lpos_engine.monitor audit --no-alert  # audit only
python -m lpos_engine.monitor discover          # refresh + print inventory
python -m lpos_engine.monitor status            # print current status.json
```

Exit codes: `0` on a completed audit (even when connectors are down — the
scheduler must not flap on outages), `2` when alerts were pending but could
not be delivered (see [Alerting](#alerting)).

## Trust boundary and the admin approval model

> Fixes audit findings **LPOS-03** (agent-registered services could execute
> arbitrary shell commands) and **LPOS-04** (credential exfiltration to
> arbitrary URLs + SSRF).

The registration files the monitor reads (`state/services.json`,
`monitor/registered-services.json`) are **agent-writable**: any process that
stands up a service can append to them. Therefore agent state is treated as
untrusted and can never, by itself:

- define an executable check (a `command`/`argv` to run), or
- receive a credential (a GitHub token), or
- grant itself egress to a private/loopback/metadata address.

Anything that can *execute* or *receive a secret* must be declared by an
administrator in `monitor/approved-checks.json`. That file is **admin-owned**:
discovery never writes it and merging never sources from it, so agent state
cannot override or inject an approved template.

### `monitor/approved-checks.json` (admin-owned)

```json
{
  "checks": {
    "report-api-health": {
      "type": "http_health",
      "url": "http://127.0.0.1:{port}/health",
      "parameters": ["port"],
      "private_network_approved": true,
      "description": "Health endpoint of the self-built report API"
    },
    "disk-free": {
      "type": "command",
      "argv": ["/usr/bin/df", "-P", "{mount}"],
      "parameters": ["mount"],
      "description": "df must exit 0 for the given mount"
    }
  }
}
```

Each template declares a `type`, its executable/endpoint definition
(`argv` / `url` / `host` ...), the placeholder `parameters` a registration may
fill, and optionally `private_network_approved` for named local services.
Placeholders are written `{name}` and are only ever filled with **non-secret
scalar** parameters.

### How an agent references a template

A registration's `check` may only be a reference:

```json
{
  "services": [
    {
      "id": "svc:report-api",
      "name": "Report API",
      "kind": "self_built",
      "check": {"check_id": "report-api-health", "params": {"port": 9001}},
      "criticality": "critical"
    }
  ]
}
```

- `params` values must be scalars (str/int/float/bool) and may only fill
  placeholders the template declared. Undeclared params or non-scalars are
  rejected.
- A registration whose `check` carries its own executable definition (an
  inline `command`, `argv`, `url`, `host`, a raw `type: command`, ...) is
  **not executed**. It is sanitised at discovery, flagged
  `unapproved_check: true` in the inventory, and reported in `status.json`
  with `status: "unknown"` and `error: "unapproved check definition"`.
- An unknown `check_id` is likewise reported `unknown` and never run.

### Egress restrictions (all URL/host checks)

Every `http_health` / `github_api` / `mcp_ping` / `tcp` / `smtp` / `imap`
check enforces:

- scheme must be `http`/`https` (other schemes, and URL userinfo, are refused);
- the hostname is **resolved** and the request is refused if any resolved
  address is loopback, link-local (`169.254.0.0/16`, `fe80::/10`), multicast,
  unspecified, a private range (`10/8`, `172.16/12`, `192.168/16`, `fc00::/7`),
  or the cloud metadata host `169.254.169.254`;
- HTTP **redirects are disabled entirely** — a 3xx is a failure
  (`error: "redirect refused"`), so DNS-rebinding / redirect pivots are closed.

The private/loopback block is lifted **only** when the *approved template* sets
`private_network_approved: true`. Self-built services legitimately live on
localhost, so an admin can approve them by name; an agent-supplied URL can
never self-grant this (the flag is stripped from any inline spec).

### Credential binding (github_api)

- The `Authorization: Bearer <token>` header is attached **only** when the
  request origin is exactly `https://api.github.com` (scheme + host + default
  port). Any other URL with a token configured fails closed with
  `error: "refused: token bound to api.github.com"` — the token is never sent.
- `token_file` must resolve (via `realpath`, symlinks followed) inside
  `<hermes>/monitor/secrets/`. Anything outside — including a symlink pointing
  out — is rejected **before any network request**. `token_env` remains
  available for environment-provided tokens.
- Secrets are redacted (`[REDACTED]`) from all error strings, state history,
  `status.json`, and alert emails; header/token values are never echoed.

### Command-check hardening (defense in depth)

Even from an approved template, `command` checks:

- are **argv lists only** — no shell anywhere (`shell=True` was removed from
  both `checks.py` and `alert.CommandTransport`); a shell string is refused;
- require an **absolute** executable path that exists and resolves inside
  `/usr`, `/bin`, `/sbin`, `/opt`, or `<hermes>/monitor/approved/` (symlinks
  out of those roots are refused);
- run with a **minimal environment** (`PATH`, `LANG` only), in a **new session**
  (`start_new_session=True`), and on timeout the whole process **group** is
  killed;
- have stdout/stderr **capped at 64 KiB** to prevent output flooding.

`CommandTransport` (the sendmail-style alert path) is likewise argv-only and
constructing it with a string raises `TypeError`.

## How discovery works

Every audit refreshes the inventory at `<root>/monitor/inventory.json` from
what the system actually uses. All scans are defensive: missing directories
and malformed files are skipped, never fatal.

| Source | Becomes | Kind |
| --- | --- | --- |
| `<root>/mcp-tokens/<name>` (file or dir) | `mcp:<name>` | `mcp` (or guessed from the name) |
| `<root>/gateway/<name>` | `gateway:<name>` | `mcp` (or guessed) |
| `<root>/platforms/<name>` | `platform:<name>` | guessed: `email` / `vcs` / `cloud` / `other` |
| `<root>/state/services.json` or `<root>/monitor/registered-services.json` | entries as declared, but `check` is reduced to an approved-template reference (see [Trust boundary](#trust-boundary-and-the-admin-approval-model)) | `self_built` by default |
| repo `config/default_registry.json` `connectors` / `external_connectors` keys | entries as declared | as declared |

Name guessing: `github`/`gitlab` → `vcs`; `smtp`/`imap`/`mail`/`gmail` →
`email`; `aws`/`gcp`/`azure`/`cloud` → `cloud`.

Merging never overwrites your edits: for an entry that already exists in
`inventory.json`, discovery only fills fields that are missing. Entries that
discovery no longer sees are kept — nothing is silently dropped; delete them
by hand if a connector is truly retired.

### Inventory entry format

```json
{
  "id": "svc:report-api",
  "name": "Report API",
  "kind": "self_built",
  "check": {"type": "http_health", "url": "http://localhost:8080/health"},
  "criticality": "critical",
  "description": "what this is, for the owner",
  "muted": false,
  "auth_expires": "2026-09-01T00:00:00+00:00"
}
```

`kind` ∈ `email | vcs | cloud | mcp | self_built | other`. `criticality` ∈
`critical | informational` (default `critical`). `auth_expires` is optional;
if set, the monitor warns when the credential is within 7 days of expiry —
before it lapses, not after.

## Registration hook for self-built services

Any agent that stands up a service must register it as part of deployment by
appending to `<root>/monitor/registered-services.json` (or
`<root>/state/services.json`). Because these files are agent-writable, the
`check` may **only reference an admin-approved template** by `check_id` (see
[Trust boundary](#trust-boundary-and-the-admin-approval-model)):

```json
{
  "services": [
    {
      "id": "svc:my-new-api",
      "name": "My New API",
      "kind": "self_built",
      "check": {"check_id": "local-http-health", "params": {"port": 9001}},
      "criticality": "critical"
    }
  ]
}
```

For this to run, an administrator must have declared `local-http-health` in
`monitor/approved-checks.json` (with a `port` placeholder, and
`private_network_approved` if the service lives on localhost). If the service
has no health endpoint, add a trivial `/health` returning 200 as part of
bringing it under monitoring. The next audit picks the entry up automatically.

An inline `check` that defines its own command/argv/url is **not run**: it is
reported `unknown` with evidence `unapproved check definition`. Ask the admin
to add a template rather than embedding the definition in agent state.

## The audit

Every check has a 15 s timeout and one retry after 5 s before anything is
declared offline — one blip never pages the owner. Checks run concurrently
(ThreadPoolExecutor); the whole audit finishes well under a minute. Results
are appended to per-connector history in `<root>/monitor/state.json`, capped
at 500 entries per connector.

Built-in checks (`monitor/checks.py`, registry `CHECKS`):

| `check.type` | Proves | Config |
| --- | --- | --- |
| `http_health` | GET returns < 400 | `url` |
| `tcp` | TCP connect succeeds | `host`, `port` |
| `smtp` | connect + NOOP | `host`, `port` (587), `starttls` |
| `imap` | connect + NOOP | `host`, `port` (993), `ssl` |
| `github_api` | authenticated GET (default `/rate_limit`) | optional `url` (token attached only to `https://api.github.com`), `token_env`, `token_file` (must live in `monitor/secrets/`) |
| `mcp_ping` | HTTP or TCP reachability | `url`, or `host` + `port` |
| `command` | approved-template argv exits 0 (never a shell; admin-only) | template `argv` + declared `parameters` |

When an entry has no explicit `check.type`, a default is chosen by kind:
`email → smtp`, `vcs → github_api`, `cloud → http_health`, `mcp → mcp_ping`,
`self_built → http_health`. An entry whose check cannot be resolved or is
missing required config gets status `unknown` — never a crash, never a false
offline.

### Adding a new check kind

Register a callable `(entry, timeout) -> CheckResult` in
`lpos_engine.monitor.checks.CHECKS`:

```python
from lpos_engine.monitor.checks import CHECKS, CheckResult

def check_my_thing(entry, timeout):
    ...
    return CheckResult(ok=True, latency_ms=12)

CHECKS["my_thing"] = check_my_thing
```

Then set `"check": {"type": "my_thing", ...}` on the entry. Test code can
instead pass a whole fake registry to `run_audit(..., registry=...)` — the
test suite runs fully offline this way.

## Muting and reclassifying

Edit `<root>/monitor/inventory.json` by hand:

- **Mute** (`"muted": true`): the connector is skipped by checks, shown as
  `unknown` in `status.json`, never degrades `overall`, and never alerts.
  Discovery honors the flag forever.
- **Reclassify** (`"criticality": "informational"`): the connector no longer
  triggers an immediate alert; it appears only in the daily reminder while
  down. `critical` (the default) alerts on first confirmed failure.
- Renames and check edits survive re-discovery — your values always win.

## Alerting

Recipient: `<root>/profiles/owner.json` `{"email": ...}`, else
`$LPOS_OWNER_EMAIL`.

Primary send path: `<root>/monitor/smtp.json` — either an SMTP config
`{"host", "port", "starttls", "username", "password_file", "from"}` (the
password stays in its own file; the monitor never copies credentials into its
state) or a sendmail-style `{"command": [...]}` that receives the message on
stdin. Both implement the same `Transport` interface.

Behavior:

- **Transition to offline** (after the retry): ONE email covering everything
  currently down — connector, exact error, down-since, and a likely fix hint
  inferred from the kind. Subject: `LPOS ALERT: <name> offline (<reason>)`,
  or `LPOS ALERT: N connectors offline` for multiples.
- **Recovery**: one short all-clear, `LPOS RECOVERED: <name>`.
- **Ongoing outage**: no repeat emails, except one daily reminder
  (`LPOS REMINDER: ...`) for anything still down after 24 h. Informational
  entries and credential-expiry warnings batch into the reminder.
- **Fallback**: if the send path fails or none is configured while alerts are
  pending, the monitor writes a loud `<root>/monitor/ALERT-UNDELIVERED.json`
  (full undelivered messages included) and exits nonzero — it is never
  silenced by the failure of its own alert channel. Delivery is retried on
  the next cycle because dedup state is only advanced after a successful
  send; a later fully-delivered cycle removes the marker.

Dedup/alert history lives in `<root>/monitor/alerts.json`.

## The status.json contract

`<root>/monitor/status.json` is written atomically every audit and is the
stable contract for the Hermes Project Dashboard and for agents doing
pre-flight checks. Keep it stable.

```json
{
  "generated_at": "2026-07-21T10:00:00+00:00",
  "overall": "ok",
  "connectors": [
    {
      "id": "mcp:github",
      "name": "github",
      "kind": "vcs",
      "status": "ok",
      "latency_ms": 143,
      "error": "",
      "criticality": "critical",
      "last_ok": "2026-07-21T10:00:00+00:00",
      "down_since": null
    }
  ]
}
```

- `overall` ∈ `ok | degraded` — degraded when any non-muted connector is
  offline.
- `status` ∈ `ok | offline | unknown`; `latency_ms` is null when not checked.
- `error` is the exact failure detail; `down_since` is set while offline.
- Additive optional fields: `muted: true` on muted entries, `auth_warning`
  when a credential expires within 7 days, and `unapproved_check: true` on an
  entry whose registration carried an executable definition that was refused
  (reported `unknown` / `unapproved check definition`). Consumers must tolerate
  additive fields; the fields above never change meaning.

## Security findings addressed

This subsystem implements the required remediations for two external-audit
findings (`LPOS_Compliance_Audit_Report_2026-07-22.md`):

- **LPOS-03 (Critical)** — agent-registered monitor services could execute
  arbitrary shell commands. Fixed by removing all `shell=True` execution,
  making executable checks admin-approved templates
  (`monitor/approved-checks.json`), refusing inline agent definitions, and
  hardening the command runner (absolute vetted executable, minimal env, new
  session with process-group kill, 64 KiB output cap).
- **LPOS-04 (High)** — credential exfiltration to arbitrary URLs + SSRF. Fixed
  by binding the GitHub token to the `https://api.github.com` origin,
  constraining `token_file` to `monitor/secrets/`, validating scheme and
  resolved addresses (blocking loopback/link-local/multicast/private/metadata
  unless an admin template approves), disabling redirects, and redacting
  secrets from all errors, state, status, and alerts.
