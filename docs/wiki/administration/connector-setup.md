---
title: Connector setup
section: administration
order: 3
---

# Connector setup

You want LPOS connected to the real world: a real model host doing the thinking, real channels reaching you, and, eventually, real actions being taken. LPOS treats each of these as an *adapter* with an explicit contract and an explicit test bar. This page explains the three kinds and the bar each must clear.

## Model hosts

Out of the box, the bundled model adapters are deterministic verification components, good for proving the system, not for real work. You connect a real model host through the **subprocess model adapter**: LPOS invokes your host command directly (argument vector, never a shell), sends one JSON object on standard input, and expects one JSON object on standard output.

The division of labor is strict. Your host process owns provider credentials, model selection, network access, and rate-limit handling. LPOS owns context assembly, capability checks, timeouts, output limits, envelope validation, persistence, and policy enforcement. A registered adapter declares its name, supported model classes, capability tokens, creation and review support, local or remote execution, priority, and availability, and LPOS rejects an adapter that lacks required metadata, does not cover a task's capabilities, violates a local-only constraint, returns invalid JSON, exceeds output limits, or times out.

Model-host output is treated as untrusted structured input: every returned envelope is validated, and a model host never gets direct write access to the LPOS database or unrestricted access to credentials.

The full protocol, with request and response examples, is in `docs/ADAPTER-PROTOCOL.md`, and `examples/example_model_host.py` is a working deterministic example to start from. During onboarding, available hosts are assigned to the `executive`, `routine`, `review`, and optional `local` classes; independent review prefers a different adapter from creation.

## Principal channels

A channel adapter carries questions, approvals, and briefings between LPOS and you. A channel is not "configured" until it is *verified*: outbound delivery, inbound collection, correlation, and your exact identity must all pass a real round trip, a configuration value alone is not verification. SO-021, the Principal Feedback Loop, stays disabled until at least one channel passes; until then, questions surface in your trusted session.

Every inbound message carries a provider-neutral MessageIdentity (channel, provider, message ID, thread ID, sender). Messages from identities not mapped to you are rejected for execution, and suspected impersonation is logged as an Operational Alert.

## Consequential action adapters

This is the highest bar, deliberately. Live email send, publishing, deployment, purchasing, deletion, and similar adapters are never silently enabled. Before a live action adapter may be registered, it must be least-privileged, authenticated, idempotent where possible, and able to distinguish success, failure, and *uncertain outcome*, and it must pass sandbox tests for duplicate requests, timeouts after partial execution, retries, credential failure, rate limits, and reconciliation. Do not register a broad generic shell executor as a consequential action adapter.

Until an adapter clears that bar, the bundled consequential-action adapter records approved actions without performing them, your approval flow works end to end, with no external effect.

## Keeping connectors healthy

Once connected, every connector comes under the [Connector Health Monitor](/includes/connector-health-monitor.html) automatically: it discovers registered connectors, platform integrations, and self-built services, audits them hourly with real authenticated checks, and emails you on failure and recovery. Where a credential has a known expiry, it warns before the lapse. When you fix a credential, confirm immediately with:

```bash
lpos monitor audit
```

The monitor's inventory file is human-editable: annotate entries, adjust criticality (`critical` alerts immediately; `informational` batches into the daily reminder), or mute, entries are never silently dropped.

## Re-authentication, practically

When a connector fails with an auth error, the alert email includes the likely fix, a re-auth link or token refresh command, when the monitor can infer it. The general loop: refresh the credential in your secret store (credentials live there, not in LPOS), run `lpos monitor audit`, and watch for the `LPOS RECOVERED` all-clear.

## Related pages

- [Connector Health Monitor](/includes/connector-health-monitor.html)
- [Configuration](/administration/configuration.html)
- [Onboarding walkthrough](/getting-started/onboarding.html)
- [Troubleshooting](/administration/troubleshooting.html)
