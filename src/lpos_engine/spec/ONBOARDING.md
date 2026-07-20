# LPOS v4 First-Run Onboarding

Run onboarding once after `INSTALL` completes and `lpos doctor --db state/lpos.db`
returns healthy. Ask in the current trusted session until a verified Principal channel
is active. Keep the process to two concise question rounds.

## 1. Establish the Principal and office identity

Confirm the single Principal, the executive-office name (default **Chip**), local time
zone, and the address or account the office will use. Record confirmed facts separately
from inference. The Principal remains the only source of consequential authority unless a
scoped delegation is explicitly recorded.

## 2. Discover model hosts and action adapters

Enumerate only adapters actually configured in this installation. Assign available model
hosts to the `executive`, `routine`, `review`, and optional `local` classes by capability,
privacy/locality, health, cost, and benchmark evidence. Prefer a different review adapter
from the creator. Do not declare any live external-action adapter until its authentication,
permissions, sandbox test, idempotency, and uncertain-outcome reconciliation have passed.

## 3. Verify Principal channels

For each configured channel, verify outbound delivery, inbound collection, correlation,
and the Principal's exact identity. A configuration value alone is not verification.
SO-021 remains disabled until a real round trip succeeds. Silence never equals consent.

## 4. Activate Standing Operations deliberately

The package contains workflow definitions for SO-001 through SO-021. Enable only those
whose required data and handlers exist. Record each activation or deferral and its revisit
condition. Default schedules are visible with:

```bash
lpos list-workflows
```

Every run uses an idempotency key, writes exactly one run record and evidence record, and
produces an explicit `ok`, `silent`, or `error` result. Four consecutive silent or near-empty
runs trigger an SO-008 review rather than continued noise.

## 5. Complete the installation record

Run the integrated local verification flow:

```bash
lpos demo --workspace state/verification
lpos doctor --db state/lpos.db
```

Record the office identity, verified channels, model-class assignments, enabled operations,
deferred operations, adapter safety boundaries, verification result, and outstanding
limitations. Do not describe a channel, adapter, review, or operation as active unless the
corresponding test actually passed.
