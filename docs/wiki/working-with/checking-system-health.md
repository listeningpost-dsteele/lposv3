---
title: Checking system health
section: working-with
order: 4
---

# Checking system health

You want to know, quickly and with confidence, that LPOS is healthy — or exactly what is wrong if it is not. There are three layers of health in the system, from a one-command check to the operations that watch themselves.

## Layer 1: `lpos doctor` — the one-command check

```bash
lpos doctor --db state/lpos.db
```

Doctor verifies the integrated specification, runtime assets, and database in one pass and prints one JSON object:

- the specification kernel reference and whether it loaded
- specialist count (must be 32), Standing Operation count (must be 21), benchmark count (must be 53)
- schema validation results (20 schemas)
- your Python version
- with `--db`: the database path, its integrity check, and the applied migrations

If any of the counts is wrong or the kernel fails to load, `doctor` reports `"status": "unhealthy"` and exits nonzero — an unambiguous signal for both you and any script. See [Troubleshooting](/administration/troubleshooting.html) for what to do next.

## Layer 2: the Connector Health Monitor — the outside world

`doctor` checks the system itself; the [Connector Health Monitor](/includes/connector-health-monitor.html) checks everything the system *runs on*. It audits every connector hourly with real authenticated checks, and its current status is always visible in two places:

- the **system-health strip** in the dashboard, and
- the status file `~/.hermes/monitor/status.json`.

To re-check right now — say, after fixing a credential — run the audit on demand:

```bash
lpos monitor audit
```

If something is offline you will have an email about it already (`LPOS ALERT: ...`), with the exact error, how long it has been down, and the likely fix.

## Layer 3: the operations that watch the system

Two Standing Operations make health a recurring responsibility rather than something you remember to check:

- **[SO-008: Standing Operation Health](/reference/so-008.html)** runs daily at 06:00 and catches failed, noisy, low-value, or redundant recurring operations within a day. This is also the operation that reviews any operation with four consecutive silent or near-empty runs.
- **[SO-020: Platform Health Review](/reference/so-020.html)** runs weekly (Sundays at 07:00) and reviews runtime, provider, infrastructure, and integration health from runtime logs, integration status, and error rates.

Both record evidence for every run, so "how healthy has this system been?" is answerable from the evidence ledger, not from memory.

## A quick health checklist

1. `lpos doctor --db state/lpos.db` says healthy.
2. Dashboard health strip is green (or `~/.hermes/monitor/status.json` shows everything ok).
3. No unread `LPOS ALERT` emails.
4. `lpos evals` passes 55/55 (worth running after any upgrade).

## Related pages

- [Connector Health Monitor](/includes/connector-health-monitor.html)
- [Troubleshooting](/administration/troubleshooting.html)
- [CLI reference](/administration/cli-reference.html)
- [Using the dashboard](/working-with/using-the-dashboard.html)
