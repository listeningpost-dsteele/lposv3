---
title: Finding your files
section: working-with
order: 2
---

# Finding your files

You know your agents produced something — a memo, a dataset, a report — and you want it on your screen now. This page is the map. The promise of LPOS v4.1.0 is that you should never have to remember a raw file path again.

## Start with the dashboard

The [Hermes Project Dashboard](/includes/dashboard.html) exists for exactly this. Three ways in, fastest first:

1. **Global search** (left rail): type any part of the project name or the file name. Search matches project names and file names across all Hermes roots, including the archive.
2. **The project card**: every project shows its disk location. One click copies the full path; one click opens the folder in your file manager.
3. **Indexed deliverables**: the detail panel lists recent output files inside each project, so you can jump straight to the deliverable without opening the folder at all.

If a project was snoozed or archived, it is still findable: the Snoozed view lists everything sleeping, and the Archive is browsable and searchable — archiving hides an item from the working views but never touches files on disk.

## The LPOS directory layout

When you want to understand where things live rather than just get one file, the layout is small and predictable. The installer creates one self-contained LPOS directory (wherever you extracted the release), and architecturally significant state is discoverable by law — Law 12 of the LPOS Laws.

Inside the release directory:

| Path | Contents |
|---|---|
| `state/lpos.db` | The authoritative database: every task, artifact, review, action, approval, evidence record, decision record, operation run, and completion report |
| `state/verification/` | The record-only verification workspace from install/onboarding |
| `src/lpos_engine/spec/` | The packaged operating specification (readable Markdown) |
| `docs/` | System documentation, including this wiki's sources under `docs/wiki/` |

Under your home directory (module runtime metadata only — never your project files):

| Path | Contents |
|---|---|
| `~/.hermes/dashboard/state.json` | Dashboard metadata: bucket assignments, snooze timers, archive records |
| `~/.hermes/monitor/` | Connector health history and `status.json` |

## Artifacts that live in the database

Not everything is a loose file: artifacts created through the task pipeline are stored immutably in the state database, keyed by artifact ID and SHA-256 content hash. To see a task's artifact and where its actions wrote files, use:

```bash
lpos inspect --db state/lpos.db --task-id TASK-...
```

The output includes the artifact (with its content hash) and every file action's parameters — including the exact paths written by the sandboxed file adapter. [Reading agent output](/working-with/reading-agent-output.html) walks through this output field by field.

## When you truly cannot find it

- Search the dashboard's Archive view — items restored in one action.
- Run `lpos events --db state/lpos.db` and scan for the task or operation in question; every write left an event.
- Check the dashboard's Hermes root configuration — a project outside the configured root will not be scanned.

## Related pages

- [Using the dashboard](/working-with/using-the-dashboard.html)
- [Snooze and archive](/working-with/snooze-and-archive.html)
- [Reading agent output](/working-with/reading-agent-output.html)
- [Backups](/administration/backups.html)
