---
title: Your first hour
section: getting-started
order: 4
---

# Your first hour

Installation and onboarding are done. This page walks your first hour with a running system: look around, run one complete task end to end, and learn where everything lands on disk — so nothing your agents ever produce is a mystery.

All commands below assume you are in the release directory, using `.venv/bin/lpos` (macOS/Linux) or `.venv\Scripts\lpos.exe` (Windows).

## Minute 0-10: look at what you own

```bash
lpos version
lpos doctor --db state/lpos.db
lpos list-specialists
lpos list-workflows
lpos list-benchmarks
```

`doctor` confirms the whole system is healthy in one JSON object: the specification kernel is loaded, 32 specialists, 25 standing operations, 53 benchmarks, and 17 schemas that pass full structural meta-validation in every install (plus jsonschema meta-validation when the dev extra is present), and your database's migrations and integrity. `list-specialists` shows every specialist with its guild, capabilities, and model class. `list-workflows` shows every Standing Operation with its default schedule. This is the entire inventory — there is nothing hidden.

If you set up the dashboard during onboarding, it is already open in your browser at its localhost port showing the four buckets — empty for now, with an explanation of what will appear where. That is intentional: no blank screens.

## Minute 10-25: run one complete task

```bash
lpos demo --workspace state/verification
```

This runs a full LPOS task with zero real-world side effects, and it exercises everything you read about in [Core concepts](/welcome/concepts.html): a task is submitted with required capabilities and a materiality signal, an interpretation contract is recorded, an artifact specification is approved, an artifact is created and hashed, an external `external_send` action is planned and approved through a verified identity bound to the exact action hash, the action is applied in record-only mode, and an isolated review passes the artifact before the completion report commits.

The command prints the whole story as JSON: the task, the artifact with its content hash, the completion report, and `"external_action_mode": "record-only"` — the proof that nothing actually left your machine.

## Minute 25-40: learn where files land

Everything LPOS creates lives inside the release directory. After the demo:

| Path | What it is |
|---|---|
| `state/lpos.db` | The authoritative transactional database: tasks, contracts, specs, artifacts, reviews, actions, approvals, evidence, decisions, operation runs, completion reports, events |
| `state/verification/` | The demo workspace |
| `state/verification/lpos-state.db` | The demo's own database |
| `state/verification/files/` | The sandboxed root for the demo's file actions |
| `state/verification/events.jsonl` | The demo's exported audit stream, one immutable event per line |
| `.venv/` | The local Python environment holding the installed `lpos` command |

The rule behind the layout: the installer creates one self-contained LPOS directory. Nothing is scattered into hidden system locations, and scheduled jobs always invoke the installed `lpos` command in this directory. From 4.1.0, the dashboard and monitor keep their own runtime metadata under `~/.hermes/dashboard/` and `~/.hermes/monitor/` — metadata only, never your project files. And when you want to find any file an agent produced, the [dashboard](/includes/dashboard.html) shows every project and deliverable with its disk path, one click to copy, one click to open.

## Minute 40-55: read the audit trail

Take the task ID from the demo output (it looks like `TASK-...`) and inspect it:

```bash
lpos inspect --db state/verification/lpos-state.db --task-id TASK-...
lpos events --db state/verification/lpos-state.db
lpos export --db state/verification/lpos-state.db --output /tmp/audit.jsonl
```

`inspect` shows the task envelope, status, artifact, every action with its plan and result, the completion report, and the task's event stream. `events` lists the immutable audit events; `export` writes them as portable JSONL. This is the same trail every future task leaves — [Reading agent output](/working-with/reading-agent-output.html) explains how to read it.

## Minute 55-60: prove the quality bar to yourself

```bash
lpos evals
```

This runs the 53 deterministic core evaluations — one fixture per specialist and per Standing Operation — against the installed system and reports passed/failed counts. A fresh install passes all 53.

From here, day-to-day use is covered in [Working With Your System](/working-with/using-the-dashboard.html), and wiring up real model hosts and connectors is covered in [Administration](/administration/connector-setup.html).

## Related pages

- [Onboarding walkthrough](/getting-started/onboarding.html)
- [Using the dashboard](/working-with/using-the-dashboard.html)
- [Finding your files](/working-with/finding-files.html)
- [CLI reference](/administration/cli-reference.html)
