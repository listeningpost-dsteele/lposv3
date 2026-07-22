---
title: CLI reference
section: administration
order: 1
---

# CLI reference

The `lpos` command is installed into the release directory's `.venv` (use `.venv/bin/lpos`, or `.venv\Scripts\lpos.exe` on Windows; the module form `python -m lpos_engine` is equivalent). Every command prints JSON, so output is equally readable by you and by scripts. On an expected failure, the CLI prints a canonical JSON error object (`{"error": ..., "message": ...}`) to stderr and exits 1; Ctrl-C exits 130.

This page documents the CLI as implemented in `src/lpos_engine/cli.py` for this release.

## Inspection commands

### `lpos version`

Shows the installed LPOS name and version.

### `lpos doctor [--db PATH] [--schema-dir PATH]`

Verifies the integrated specification, runtime assets, and (with `--db`) the database. Reports kernel load, specialist/operation/benchmark counts, schema validation, Python version, database integrity, and migrations. Exits nonzero and reports `unhealthy` if the kernel is missing or the counts are not 32 / 21 / 53. See [Checking system health](/working-with/checking-system-health.html).

### `lpos list-specialists`

Prints the 32 capability-routable specialists: id, name, guild, model class, capabilities, and craft standards.

### `lpos list-workflows`

Prints the packaged Standing Operation catalog, all 21 operations with their workflow files, default schedules, requirements, and enabled-by-default flags.

### `lpos list-benchmarks`

Prints the 53 fixed benchmark fixtures.

### `lpos evals`

Runs the deterministic core evaluations against all 53 fixtures. Exits nonzero if any fail.

### `lpos validate-schemas [--schema-dir PATH]`

Validates the packaged executable JSON Schemas (or a directory you point it at). Without the `dev` extra installed, it parses the JSON and notes that full JSON Schema validation needs the dev extra.

## State commands

### `lpos init --db PATH`

Initializes (or migrates) the transactional state database at PATH, applying the checksummed migrations, and reports the migration list and an integrity check. The installer runs this for you against `state/lpos.db`.

### `lpos inspect --db PATH --task-id ID`

Shows one task in full: envelope, status, version, timestamps, latest artifact, every action (plan, status, result), the completion report, and the task's events. See [Reading agent output](/working-with/reading-agent-output.html).

### `lpos events --db PATH [--stream-type TYPE] [--stream-id ID]`

Lists immutable audit events, optionally filtered by stream type and stream id.

### `lpos export --db PATH --output PATH`

Exports the append-only event stream as JSONL, one immutable event per line, in sequence order. This is the portable audit and backup format; it is an export, not the live state.

## Verification command

### `lpos demo --workspace PATH [--spec-root PATH] [--principal-email ADDR]`

Runs the no-side-effect integrated verification flow into a workspace: submits a task, records the interpretation contract and artifact specification, creates an artifact, plans and approves an exact external action through a verified identity, applies it record-only, passes an isolated review, and exports the events. `--principal-email` defaults to `principal@example.com`; `--spec-root` can override the packaged specification for development.

## Module commands (4.1.0)

### `lpos dashboard`

Starts the [Hermes Project Dashboard](/includes/dashboard.html) server on port 7373. Normally unnecessary, the dashboard starts with the system.

### `lpos monitor audit`

Runs the [Connector Health Monitor](/includes/connector-health-monitor.html)'s audit on demand, outside its hourly schedule.

## Related pages

- [Your first hour](/getting-started/first-hour.html)
- [Checking system health](/working-with/checking-system-health.html)
- [Troubleshooting](/administration/troubleshooting.html)

## `lpos compliance`

Run the SOC 2 Compliance Guild by hand: `lpos compliance audit` runs the full control audit against the codified Trust Services Criteria catalog, `lpos compliance report` regenerates the compliance HTML page, and `lpos compliance status` prints the current `compliance/status.json`. Flags: `--root` (Hermes root) and `--repo` (release checkout). Added in 4.2.0; scheduled daily as SO-025. See [SOC 2 Compliance Guild](/includes/soc2-compliance.html).
