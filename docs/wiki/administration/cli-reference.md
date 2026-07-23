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

Verifies the integrated specification, runtime assets, and (with `--db`) the database. Reports kernel load, specialist/operation/benchmark counts, schema validation, Python version, database integrity, and migrations. Exits nonzero and reports `unhealthy` if the kernel is missing or the counts are not 33 / 26 / 55. See [Checking system health](/working-with/checking-system-health.html).

### `lpos list-specialists`

Prints the 33 capability-routable specialists: id, name, guild, model class, capabilities, and craft standards.

### `lpos list-workflows`

Prints the packaged Standing Operation catalog — all 26 operations with their workflow files, default schedules, requirements, and enabled-by-default flags.

### `lpos list-benchmarks`

Prints the 55 fixed benchmark fixtures.

### `lpos evals`

Runs the deterministic core evaluations against all 55 fixtures. Exits nonzero if any fail.

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

Exports the append-only event stream as JSONL — one immutable event per line, in sequence order. This is the portable audit and backup format; it is an export, not the live state.

## Sentinel adversarial-assurance commands

### `lpos sentinel status --db PATH`

Shows the persisted assessment, review, trusted-review, report, and unacknowledged-report counts. Sentinel output is never trusted by guild designation: only hash-bound assessments that have passed the ordinary fresh-context independent review and deterministic exact-revision checks may be treated as findings.

### `lpos sentinel scan --db PATH --task-id ID [--spec-root PATH]`

Runs a passive, static, non-destructive assessment of the latest persisted artifact for the selected task. The raw assessment is stored as untrusted and then submitted through LPOS's normal adversarial-review process. This command does not execute the artifact, open network connections, launch shells, or perform live exploitation.

### `lpos sentinel reports --db PATH [--task-id ID] [--unacknowledged]`

Lists Principal-facing Sentinel reports. `--unacknowledged` limits the result to reports without a Principal acknowledgement. An assurance failure is clearly distinguished from a verified finding and never republishes unreviewed raw claims as fact.

### `lpos sentinel show --db PATH --report-id ID`

Shows one reviewed report, including redacted evidence, remediation suggestions, and verification guidance. Its assessment and review identifiers and hashes bind the report to the immutable assurance records.

### `lpos sentinel ack --db PATH --report-id ID [--acknowledged-by NAME] [--note TEXT]`

Appends a Principal acknowledgement without mutating, suppressing, downgrading, closing, or deleting the report. Sentinel identities cannot acknowledge their own reports.

Live or destructive penetration testing is not provided by these commands. A future active runner must remain separately disabled by default and satisfy an exact, time-bounded, isolated-environment action approval; the candidate includes only the fail-closed authorization gate.

## Verification command

### `lpos demo --workspace PATH [--spec-root PATH] [--principal-email ADDR]`

Runs the no-side-effect integrated verification flow into a workspace: submits a task, records the interpretation contract and artifact specification, creates an artifact, plans and approves an exact external action through a verified identity, applies it record-only, passes an isolated review, and exports the events. `--principal-email` defaults to `principal@example.com`; `--spec-root` can override the packaged specification for development.

## Module commands (4.1.0)

### `lpos dashboard`

Starts the [Hermes Project Dashboard](/includes/dashboard.html) server on port 7373. Normally unnecessary — the dashboard starts with the system.

### `lpos monitor audit`

Runs the [Connector Health Monitor](/includes/connector-health-monitor.html)'s audit on demand, outside its hourly schedule.

## Related pages

- [Your first hour](/getting-started/first-hour.html)
- [Checking system health](/working-with/checking-system-health.html)
- [Troubleshooting](/administration/troubleshooting.html)

## `lpos compliance`

Run the SOC 2 Compliance Guild by hand: `lpos compliance audit` runs the full control audit against the codified Trust Services Criteria catalog, `lpos compliance report` regenerates the compliance HTML page, and `lpos compliance status` prints the current `compliance/status.json`. Flags: `--root` (Hermes root) and `--repo` (release checkout). Added in 4.2.0; scheduled daily as SO-025. See [SOC 2 Compliance Guild](/includes/soc2-compliance.html).
