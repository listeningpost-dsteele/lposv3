---
title: Onboarding walkthrough
section: getting-started
order: 3
---

# Onboarding walkthrough

You have installed LPOS and `lpos doctor --db state/lpos.db` reports healthy. Onboarding is the one-time conversation that turns the installed engine into *your* system: it establishes who you are, discovers what adapters exist, verifies your channels, and deliberately switches on the recurring operations that make sense for you.

Onboarding runs once, in your current trusted session, and is kept to two concise question rounds. Until a verified Principal channel is active, all questions come to you through that trusted session.

## 1. Establish the Principal and office identity

The system confirms four things: that you are the single Principal, the executive-office name (default **Chip** — pick anything; the configured name is used everywhere the specification says "Chip"), your local time zone, and the address or account the office will use as its sending identity.

Confirmed facts are recorded separately from inference. You remain the only source of consequential authority unless you explicitly record a scoped delegation.

## 2. Discover model hosts and action adapters

Onboarding enumerates only the adapters actually configured in this installation — nothing is assumed. Available model hosts are assigned to the `executive`, `routine`, `review`, and optional `local` classes by capability, privacy and locality, health, cost, and benchmark evidence. Where possible, the review class gets a *different* adapter from the creator class, so independent review really is independent.

Live external-action adapters (email send, publishing, deployment, purchases) are held to a hard bar: none is declared active until its authentication, permissions, sandbox test, idempotency, and uncertain-outcome reconciliation have all passed. Until then, consequential actions stay record-only.

## 3. Verify Principal channels

For each configured communication channel, onboarding verifies four things: outbound delivery works, inbound collection works, messages correlate correctly, and your exact identity on that channel is confirmed. A configuration value alone is not verification — a real round trip has to succeed.

This matters because SO-021, the Principal Feedback Loop, is the operation that carries blocking questions and approval requests to you and collects your answers. It stays disabled until a real round trip succeeds on at least one channel. Silence never equals consent, so an unverified channel cannot be used to infer anything.

## 4. Activate Standing Operations deliberately

The package contains workflow definitions for SO-001 through SO-021, each with a default schedule. Onboarding enables only those whose required data and handlers actually exist in your installation — for example, SO-003 Calendar Review requires a `calendar` connector and SO-004 Inbox Review requires a `mailbox` connector, so both start disabled until those exist. Each activation or deferral is recorded along with its revisit condition.

See the default schedules any time:

```bash
lpos list-workflows
```

Every run uses an idempotency key, writes exactly one run record and one evidence record, and produces an explicit `ok`, `silent`, or `error` result. Four consecutive silent or near-empty runs trigger an SO-008 health review rather than continued noise.

The [Reference section](/includes/index.html) has one page per operation with its schedule, requirements, and workflow steps.

## 5. Complete the installation record

Onboarding finishes by running the integrated local verification flow and re-checking health:

```bash
lpos demo --workspace state/verification
lpos doctor --db state/lpos.db
```

Then it records the installation record: the office identity, verified channels, model-class assignments, enabled operations, deferred operations, adapter safety boundaries, the verification result, and outstanding limitations. The rule throughout is honesty: nothing — no channel, adapter, review, or operation — is described as active unless its corresponding test actually passed.

## What onboarding also sets up (v4.1.0)

From release 4.1.0, onboarding also installs and starts two modules for every user, with no opt-in step and no dashboard-specific questions:

- The **Hermes Project Dashboard** — installed with the system, configured from values onboarding already knows, and opened in your browser as the final stage of onboarding, so the first thing you see is your new system showing its own projects. See [Hermes Project Dashboard](/includes/dashboard.html).
- The **Connector Health Monitor** — installs and schedules itself hourly; its first audit runs at the end of onboarding, doubling as a verification pass that every connector you just set up actually works, with results shown to you. See [Connector Health Monitor](/includes/connector-health-monitor.html).

## Related pages

- [Install LPOS](/getting-started/install.html)
- [Your first hour](/getting-started/first-hour.html)
- [Hermes Project Dashboard](/includes/dashboard.html)
- [Connector Health Monitor](/includes/connector-health-monitor.html)
- [Connector setup](/administration/connector-setup.html)
