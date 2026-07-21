# Hermes Project Dashboard

The Hermes Project Dashboard is a core LPOS module. It is installed with LPOS, configured during onboarding, and starts with the local system so the Principal can see active work, research, snoozed items, archive, and the disk paths behind every project and deliverable.

## URL and commands

Default URL:

```bash
http://127.0.0.1:4177
```

Commands:

```bash
lpos dashboard init
lpos dashboard start
lpos dashboard status
lpos dashboard open
lpos dashboard serve
```

`install.py` runs `lpos dashboard init` and starts the dashboard unless `--no-dashboard` is passed. Use `--open-dashboard` during install to open the browser automatically.

## State and config

Dashboard state is local and user-specific:

```text
~/.hermes/dashboard/config.json
~/.hermes/dashboard/state.json
~/.hermes/dashboard/dashboard.pid
~/.hermes/dashboard/dashboard.log
```

The state file stores bucket assignments, snooze wake times, archive dates, and wake indicators. Project folders are never modified. Missing or corrupt state falls back to all discovered work in Active or Research.

## Scanner conventions

The scanner reads the user's Hermes root, defaulting to `~/.hermes`. It indexes:

- `~/.hermes/kanban.db` tasks, including workspace paths and task status.
- `~/.hermes/sessions/request_dump*.json` recent Hermes session activity.
- Optional project-like directories under `projects/`, `guilds/`, `standing-operations/`, `specialists/`, and `lpos-runtime/`.

For project directories, optional `project.json` can supply:

```json
{
  "name": "Investor Outreach",
  "description": "One-line summary shown on the card",
  "agents": ["Chip"],
  "type": "research"
}
```

Without metadata, the dashboard uses the folder name, first README paragraph, and file modification times. Deliverables are recent readable outputs such as Markdown, PDFs, spreadsheets, CSV, JSON, HTML, images, and video.

## Buckets

- Active: current execution and work in progress.
- Research: investigations, sessions, guild or specialist roots.
- Snoozed: hidden until a selected wake time, then returned with a visible wake indicator.
- Archive: hidden from working views while files remain untouched.

## Changing root or port

```bash
lpos dashboard init --hermes-root ~/.hermes --port 4177
lpos dashboard start
```

The server binds to `127.0.0.1` only. It makes no cloud calls, creates no accounts, and sends no telemetry.

## Existing user migration

On upgrade, LPOS installs and configures the dashboard. Existing Hermes tasks, sessions, and project directories populate automatically. Items default to Active or Research unless the dashboard state file already records a bucket, snooze, or archive assignment.
