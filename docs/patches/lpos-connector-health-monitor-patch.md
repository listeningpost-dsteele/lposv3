# Patch Spec: LPOS Connector Health Monitor

> Instruction document for patching LPOS with a system-wide health monitor. Hand this to Claude (or a developer) working inside the LPOS repo. Items marked `[LPOS]` are placeholders to resolve against the actual codebase; everything else is fixed by design. Companion to the Hermes Project Dashboard build spec — the monitor feeds the dashboard, but stands alone if the dashboard isn't built yet.

---

## 1. What this patch does

LPOS runs on external services: email, GitHub, cloud providers, MCP connectors, third-party APIs, and APIs the system built for itself. When one goes offline, agents fail quietly and the owner finds out hours later from a broken deliverable. This patch adds a **connector health monitor** that:

1. Discovers **everything the system runs on** — not a hand-maintained list.
2. **Audits every connector once an hour**, verifying each is actually reachable and authenticated, not just configured.
3. **Emails the owner** when anything is offline, when it recovers, and never spams in between.

The rule of scope is literal: if LPOS depends on it at runtime, the monitor checks it. Email, GitHub, cloud access, every MCP connector, every external API, and every API or service the system itself created and now relies on.

## 2. Where it lives in LPOS

- **Module home:** `[LPOS: alongside other service modules — mirror the layout used by existing services in src/ or Packages/]`
- **Scheduling:** hourly, via the system's own scheduler `[LPOS: the existing cron mechanism — ~/.hermes/cron appears to exist; register the audit there rather than adding a second scheduler]`. The audit must also be runnable on demand from the CLI for debugging.
- **State:** `~/.hermes/monitor/` — last-known status per connector, timestamps, alert history. Same conventions as other Hermes state dirs. Never store credentials here; the monitor uses the credentials the system already holds, in place.
- **Process model:** the audit is a short-lived job, not a daemon — it wakes, checks, records, alerts if needed, exits. Crash of the monitor must never affect any other LPOS service.

## 3. Discovery: build the inventory automatically

The monitor maintains a **connector inventory** assembled from what the system actually uses, so new dependencies are picked up without anyone editing a list:

- **Registered connectors/MCP servers:** enumerate from LPOS config `[LPOS: mcp-tokens/, gateway/, config/ — wherever connector registrations live]`.
- **Platform integrations:** email account(s), GitHub, cloud providers `[LPOS: platforms/ dir suggests per-platform registrations — enumerate from there]`.
- **Self-built services:** APIs, webhooks, and services the system created for itself `[LPOS: wherever agent-created services are recorded — sandboxes/, standing-operations/, deployment records. If the system doesn't currently record what it builds, this patch adds that: any agent that stands up a service must register it in the inventory as part of deployment.]`
- **Observed dependencies:** optionally, scan recent agent logs `[LPOS: logs/]` for external endpoints hit in the last N days and flag any that aren't in the inventory, so nothing the system quietly depends on escapes monitoring.

Each inventory entry: id, human name, kind (email / vcs / cloud / mcp / self-built api / other), how to check it (see §4), owner-facing description, and criticality (see §5). The inventory file is human-readable and hand-editable — auto-discovered entries can be annotated or muted, never silently dropped.

## 4. The hourly audit

For each connector, run the **lightest real check** that proves the service is up AND the system's access works. Configuration existing is not health; a 200 from an authenticated call is.

- **Email:** verify send capability via the provider's cheapest authenticated call `[LPOS: however LPOS sends mail — SMTP login/NOOP, Gmail API profile fetch, etc.]`. Once a day, upgrade to an actual send-to-self round trip.
- **GitHub:** authenticated API call (e.g. `GET /user` or rate-limit endpoint) with the system's token — proves both GitHub is up and the token is valid.
- **Cloud providers:** one cheap authenticated call per provider (e.g. STS get-caller-identity or equivalent) — proves credentials, not just reachability.
- **MCP connectors:** initialize/ping each server; a connector that connects but fails auth counts as offline.
- **Self-built APIs and services:** hit their health endpoint; if a service has none, this patch requires adding one (a trivial `/health` returning 200) as part of bringing it under monitoring.
- **Anything else:** the check interface is pluggable — a new connector kind needs only a small check function registered for it.

Mechanics: every check has a timeout (default 15 s) and one retry after a short delay before anything is declared offline — one blip must not page the owner. Checks run concurrently; the whole audit should finish in under a minute. Each result (ok/offline, latency, error detail) is appended to the state history so the dashboard and future audits can see trends. Auth-expiry distinct from outage: where a credential has a known expiry, warn **before** it lapses, not after.

## 5. Alerting: email the owner

- **Recipient:** the system owner's email from LPOS config `[LPOS: owner identity — profiles/?]`. Configurable, defaults to the account LPOS is set up under.
- **Send path:** the system's own email connector — with a fallback: if the email connector is *itself* the thing that's down, use the secondary channel `[LPOS: choose one that exists — a second SMTP config, a messaging connector, or at minimum a loud persistent failure surfaced in the dashboard and on next CLI interaction]`. The monitor must never be silenced by the failure of its own alert channel.
- **When to email:** on **transition to offline** (after the retry), one email covering everything currently down — connector name, what failed, exact error, how long it's been down, and the likely fix (re-auth link, token refresh command, service restart) when the monitor can infer it. On **recovery**, one short all-clear. While a known outage continues, no repeat emails — except a daily reminder for anything still down after 24 h.
- **Criticality:** entries marked `critical` (email, primary cloud, anything agents can't work without) alert immediately on first confirmed failure. Entries marked `informational` can batch into the daily reminder only. Default is critical.
- **Subject lines** readable on a phone lock screen: `LPOS ALERT: GitHub offline (auth failure)` / `LPOS RECOVERED: GitHub`.

## 6. Integration points

- **Dashboard:** publish current status to a small JSON the Hermes Project Dashboard can read (`~/.hermes/monitor/status.json`) — the dashboard gets a system-health strip for free. This file is the contract; keep it stable.
- **Agents:** agents can read the same status file before attempting work on a dead connector `[LPOS: optionally wire into whatever pre-flight checks agents already run]`.
- **Onboarding:** the monitor installs and schedules itself as part of standard LPOS setup, like the dashboard — no opt-in. First audit runs at the end of onboarding, which doubles as a verification pass that every connector the user just set up actually works, with results shown to the user.
- **No new cloud dependencies:** the monitor itself runs entirely locally and must not introduce a new external service to watch the existing ones.

## 7. Deliverables

1. The monitor module, scheduled hourly through the existing LPOS scheduler, with on-demand CLI invocation.
2. Auto-discovery across connectors, platform integrations, and self-built services, plus the deployment-time registration hook for anything agents build from now on.
3. Pluggable per-kind health checks covering, at minimum: email, GitHub, cloud provider(s), all registered MCP connectors, and all currently-running self-built services.
4. Email alerting with transition/recovery logic, fallback channel, and criticality tiers.
5. `status.json` contract for the dashboard, and a docs page `[LPOS: docs/]`: how discovery works, how to add a check, how to mute or reclassify a connector, and how alerting behaves.
6. Tests: at minimum, simulated offline/recovery transitions producing exactly one alert and one all-clear, timeout handling, and the email-connector-down fallback path.

## 8. Working style

Work inside the LPOS repo. Resolve every `[LPOS]` placeholder by reading the codebase first — especially the real locations of connector registrations, the cron mechanism, and how the system sends email — then confirm the resolved plan in a short summary before building. Reuse existing LPOS infrastructure everywhere; the monitor should feel like the system checking its own pulse, not a new product bolted on.
