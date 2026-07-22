---
title: Hermes Project Dashboard
section: includes
order: 2
---

# Hermes Project Dashboard

The Hermes Project Dashboard is your single pane of glass for what your Hermes agents are doing: active work, research projects, snoozed items, and the archive. It is a first-class LPOS module, not an add-on, every LPOS user gets it by default, installed during onboarding, styled with the LPOS default design, and started with the system.

It exists to fix Hermes's worst usability problem: raw file paths that are hard to find. Every item in the dashboard carries its disk location, viewable, copyable, and openable in one click.

## Opening it

The dashboard is a small local server serving a browser UI at:

```text
http://localhost:7373
```

You should never need to start it manually: it launches automatically as the final stage of onboarding (the first thing a new user sees is their own system showing its own projects) and auto-starts on every subsequent boot of LPOS. If you ever need to start it by hand, the CLI command is:

```bash
lpos dashboard
```

Everything is local: no cloud calls, no accounts, no telemetry.

## The four buckets

The left rail shows four buckets, with global search above them. **Active** is the default view.

- **Active**, work your agents are currently doing or that needs your attention.
- **Research**, longer-running exploratory projects. Items move freely between Active and Research.
- **Snoozed**, items you have put to sleep for a chosen duration, listed with their wake times.
- **Archive**, items hidden from the working views. Files on disk are untouched; everything is browsable, searchable, and restorable.

Each project card shows: name, bucket, the owning Hermes agent(s) or guild, last activity (from file modification times or Hermes logs), a short description when project metadata has one, and the disk location. Status is designed to be readable at a glance, strong visual distinction between buckets, clear recency, and an unmissable indicator when something has just woken from snooze.

Core actions, snooze, archive, restore, open folder, copy path, move bucket, are keyboard-friendly and never more than two clicks deep.

## File discoverability, the headline feature

Every project and indexed deliverable shows a friendly rendering of its path; one click copies the full path, one click opens the folder in your operating system's file manager (platform-detected on macOS, Windows, and Linux). The dashboard indexes recent output files inside each project, so you jump straight to deliverables instead of digging through directories. Global search matches project names and file names across all Hermes roots.

For the fuller picture of where LPOS puts files, see [Finding your files](/working-with/finding-files.html).

## Where its data comes from, and where its state lives

The dashboard *reads* project state from the Hermes directories on disk, it reuses the metadata Hermes already writes, falling back gracefully to folder name and modification time when metadata is absent. It never writes into your project folders.

Its own metadata, bucket assignments, snooze timers, archive records, lives in a single state file under the Hermes state root:

```text
~/.hermes/dashboard/state.json
```

This state survives restarts, upgrades, and re-onboarding. If the state file is ever corrupt or missing, the dashboard degrades to "everything Active", never a crash, and never lost project files, because project files were never in it.

## System health strip

The dashboard reads the [Connector Health Monitor](/includes/connector-health-monitor.html)'s status file (`~/.hermes/monitor/status.json`) and shows a system-health strip, so a dead connector is visible the moment you look at your projects.

## First run and upgrades

On a fresh system with no projects, the dashboard shows a purposeful empty state: what the buckets mean and where projects will appear as agents start work. For existing users upgrading, the dashboard installs, starts, and populates from your current Hermes directories with everything defaulting to Active, nothing to migrate by hand.

## Related pages

- [Using the dashboard](/working-with/using-the-dashboard.html)
- [Snooze and archive](/working-with/snooze-and-archive.html)
- [Finding your files](/working-with/finding-files.html)
- [Connector Health Monitor](/includes/connector-health-monitor.html)
- [Onboarding walkthrough](/getting-started/onboarding.html)
