---
title: Continuous Operational Excellence
section: administration
order: 2
---

# Continuous Operational Excellence

LPOS 4.5.0 COE makes release and operational-health claims command backed, append-only, and
fail-closed.

## Stage and verify a release

```bash
lpos coe stage --repo /path/to/clean/source --release-root /tmp/lpos-4.5.0-stage
lpos coe verify --release-root /tmp/lpos-4.5.0-stage
```

Staging copies tracked release inputs into an empty directory outside the repository. The
generated manifest enumerates every regular file. Missing, unlisted, changed, mutable,
unsafe, and symlinked content fails verification.

## Run the nine-gate release audit

```bash
lpos coe release-gate \
  --repo /path/to/clean/source \
  --release-root /tmp/lpos-4.5.0-stage \
  --state-root ~/.hermes/state/chip-service
```

The command runs deterministic tests, application verification, Doctor, engineering,
security and reliability, documentation, bloat and efficiency, opportunity and value, and
release-integrity gates. Each command writes schema-valid evidence for one audit, commit,
identity, and artifact. Any missing or nonpassing evidence returns nonzero.

## Private dashboard and API

```bash
COE_OPERATOR_TOKEN=<secure-value> lpos coe serve \
  --state-root ~/.hermes/state/chip-service \
  --host 127.0.0.1 \
  --port 8765
```

The local page is `http://127.0.0.1:8765/dashboard/coe`. Production uses the authenticated
canonical route `https://chip.listeningpost.ai/dashboard/coe`. `/ops/coe` redirects to the
canonical path. The dashboard and `/api/v1/coe` render persisted evidence only and use
private, no-store responses.

## Daily operation

Run at `03:00 America/Chicago`. The Central date creates the daily idempotency key and a
SQLite lease prevents overlap. The audit records deterministic model-wake decisions, changed
code, skill-search efficiency, scheduler health, prompt drift, storage, real restore tests,
technical debt, opportunities, and COE's own cost.

Reports are generated for pass, blocked, and failed terminal audits. A report is delivered
only through the configured operator transport. Delivery is not marked successful without a
provider message ID or equivalent acceptance record.

## State and compatibility

COE state lives outside releases under `~/.hermes/state/chip-service/coe` by default. SQLite
evidence and decisions are append-only. The legacy `/Users/dan/lpos-state` boundary remains
read-only and is registered as `TD-LEGACY-LPOS-STATE` until a separate reversible migration
is approved.