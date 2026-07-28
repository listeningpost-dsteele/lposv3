---
title: Continuous Operational Excellence
section: administration
order: 2
---

# Continuous Operational Excellence

LPOS Continuous Operational Excellence, or COE, detects and prevents operational bloat before it becomes a reliability or cost problem.

## Run the audit

```bash
lpos coe audit \
  --repo /path/to/LPOS \
  --hermes-root ~/.hermes \
  --state-root ~/.local/state/lpos
```

The command prints machine-readable JSON and creates an immutable audit history plus current report surfaces under `~/.local/state/lpos/coe/`.

## Run the release gate

```bash
lpos coe release-gate \
  --repo /path/to/LPOS \
  --hermes-root ~/.hermes \
  --state-root ~/.local/state/lpos
```

Exit code `0` means the critical COE controls and deterministic evaluations passed. Any critical failure returns a nonzero exit code and blocks release.

## View current status

```bash
lpos coe status --state-root ~/.local/state/lpos
lpos coe report --state-root ~/.local/state/lpos
```

## Serve the dashboard

```bash
lpos coe serve --state-root ~/.local/state/lpos --host 127.0.0.1 --port 7374
```

Open `http://127.0.0.1:7374/dashboard/coe`. The service refuses a non-loopback bind unless the operator deliberately sets `LPOS_COE_ALLOW_NONLOOPBACK=1`. Use a trusted tunnel for remote access rather than exposing the service directly.

## Daily operation

Schedule `lpos coe audit` once daily. The audit itself is deterministic and does not wake a model. The generated `daily-email.md` is the delivery-ready report. Connect it to an approved authenticated email adapter only after the Principal has authorized that destination and schedule.

Every daily report includes the dashboard URL, timestamp, current release version, latest audit ID, executive summary, key findings, critical risks, engineering summary, bloat findings, recommendations, and full appendix.

## Technical debt records

Create `~/.local/state/lpos/coe/technical-debt.json` as a JSON array. Every record requires:

```json
{
  "id": "TD-001",
  "owner": "Platform",
  "rationale": "Temporary compatibility boundary",
  "retirement_date": "2026-12-31",
  "migration_plan": "Import legacy records into SQLite, verify parity, then remove the compatibility reader",
  "status": "open"
}
```

Missing fields and overdue open records create an audit warning.

## Restore and retention

COE writes current derived files atomically and appends one JSON object per audit to `history.jsonl`. Back up the mutable state root through the normal bounded backup system. Never copy the mutable COE state into an immutable LPOS release directory.
