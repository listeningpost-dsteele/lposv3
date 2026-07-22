---
title: Connector Health Monitor
section: includes
order: 3
---

# Connector Health Monitor

LPOS runs on external services: email, GitHub, cloud providers, MCP connectors, third-party APIs, and APIs the system built for itself. When one goes offline, agents fail quietly and you find out hours later from a broken deliverable. The Connector Health Monitor closes that gap. It discovers everything the system runs on, audits every connector once an hour, and emails you when anything goes offline, and when it recovers, without spamming in between.

The rule of scope is literal: if LPOS depends on it at runtime, the monitor checks it.

## How discovery works

You never maintain the list. The monitor assembles a **connector inventory** automatically from what the system actually uses:

- **Registered connectors and MCP servers**, enumerated from LPOS configuration.
- **Platform integrations**: your email account(s), GitHub, cloud providers.
- **Self-built services**: APIs, webhooks, and services the system created for itself. Any agent that stands up a service must register it in the inventory as part of deployment, so nothing new escapes monitoring.
- **Observed dependencies**: optionally, recent agent logs are scanned for external endpoints hit in the last few days, and anything not already in the inventory is flagged.

Each inventory entry records an id, a human name, a kind (email / vcs / cloud / mcp / self-built api / other), how to check it, an owner-facing description, and a criticality tier. The inventory file is human-readable and hand-editable, you can annotate or mute auto-discovered entries, but they are never silently dropped.

## The hourly audit

For each connector, the monitor runs the lightest *real* check that proves the service is up **and** the system's access works. Configuration existing is not health; a 200 from an authenticated call is.

- **Email**, the provider's cheapest authenticated call; once a day, upgraded to an actual send-to-self round trip.
- **GitHub**, an authenticated API call with the system's token, proving both that GitHub is up and that the token is valid.
- **Cloud providers**, one cheap authenticated identity call per provider, proving credentials rather than mere reachability.
- **MCP connectors**, initialize/ping each server; a connector that connects but fails auth counts as offline.
- **Self-built APIs and services**, hit their health endpoint. A service without one gets a trivial `/health` added as part of coming under monitoring.
- **Anything else**, the check interface is pluggable; a new connector kind needs only a small check function registered for it.

Every check has a timeout (default 15 seconds) and one retry after a short delay before anything is declared offline, one blip must not page you. Checks run concurrently; the whole audit finishes in under a minute. Each result (ok/offline, latency, error detail) is appended to the state history, so the dashboard and future audits can see trends. Credential expiry is treated as distinct from outage: where an expiry is known, the monitor warns *before* it lapses, not after.

The audit itself is a short-lived job, not a daemon, it wakes, checks, records, alerts if needed, and exits. A crash of the monitor never affects any other LPOS service.

## Running it on demand

The audit is scheduled hourly through the system's own scheduler, but you can run it any time for debugging:

```bash
lpos monitor audit
```

The first audit runs automatically at the end of onboarding, which doubles as a verification pass that every connector you just set up actually works, with the results shown to you.

## What the alert emails mean

- **`LPOS ALERT: GitHub offline (auth failure)`**, a connector transitioned to offline (after the retry). One email covers everything currently down: connector name, what failed, the exact error, how long it has been down, and the likely fix (re-auth link, token refresh command, service restart) when the monitor can infer it.
- **`LPOS RECOVERED: GitHub`**, a short all-clear when it comes back.
- While a known outage continues, no repeat emails, except a daily reminder for anything still down after 24 hours.

Alerts go to the system owner's email from LPOS configuration (configurable; defaults to the account LPOS is set up under). If the email connector is *itself* the thing that is down, the monitor falls back to a secondary channel, it is never silenced by the failure of its own alert path.

**Criticality tiers:** entries marked `critical` (email, primary cloud, anything agents cannot work without) alert immediately on first confirmed failure; entries marked `informational` batch into the daily reminder only. The default is critical.

## Where its state lives

```text
~/.hermes/monitor/
```

Last-known status per connector, timestamps, and alert history live here, following the same conventions as other Hermes state directories. Credentials are **never** stored here, the monitor uses the credentials the system already holds, in place. The current status is also published to `~/.hermes/monitor/status.json`, a small stable JSON file the [dashboard](/includes/dashboard.html) reads for its system-health strip, and which agents can read before attempting work on a dead connector.

## Related pages

- [Checking system health](/working-with/checking-system-health.html)
- [Connector setup](/administration/connector-setup.html)
- [Hermes Project Dashboard](/includes/dashboard.html)
- [Troubleshooting](/administration/troubleshooting.html)
