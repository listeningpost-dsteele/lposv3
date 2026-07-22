# Hermes Project Dashboard

The Hermes Project Dashboard is a first-class LPOS module: a local, zero-dependency
single pane of glass for what your Hermes agents are doing. It scans the Hermes
directories on disk, shows every project in one of four buckets — **Active**,
**Research**, **Snoozed**, **Archive** — and serves a calm, OS-native-feeling UI on a
localhost-only port. Every project card carries its disk location with one-click
copy-path and open-folder actions, and global search matches both project names and
file names across all Hermes roots.

It is pure standard library (Python >= 3.11): no runtime dependencies, no CDN assets,
no network calls beyond the local loopback.

## Running it

Through the CLI (once wired by the orchestrator):

```bash
lpos dashboard --port 7373
```

Or directly as a module:

```bash
python -m lpos_engine.dashboard            # default: http://127.0.0.1:7373/
python -m lpos_engine.dashboard --port 8080 --root ~/alt-hermes
```

Flags: `--port` (default 7373), `--root` (Hermes root override), `--host`
(default `127.0.0.1`; keep it loopback), `--verbose` (request logging).

## Configuration

| Setting | How to set it | Default |
| --- | --- | --- |
| Hermes root | `LPOS_HERMES_ROOT` env var, or `--root` | `~/.hermes` |
| Port | `--port` | `7373` |
| Bind address | `--host` | `127.0.0.1` (localhost only) |
| Extra project roots | `<root>/dashboard/roots.json` | none |

`roots.json` is either a JSON array of directory paths or `{"roots": [...]}`.
Relative entries resolve against the Hermes root.

## The directory convention the scanner uses

The scanner reads what Hermes already writes and never invents parallel state:

- **Project roots scanned:** `<root>/sessions`, `<root>/standing-operations`,
  `<root>/projects`, plus anything listed in `<root>/dashboard/roots.json`.
- **Each top-level folder in a root is one project.** An optional `project.json`
  inside the folder may supply `name`, `description`, `agent`, and `type`
  (`active` or `research`). When metadata is missing or malformed the scanner
  falls back to the folder name and modification time — a broken file never
  breaks the scan.
- **Kanban boards:** any `<root>/kanban/*.json` files are merged in as projects.
  The reader is defensive about shape (top-level lists, `cards`/`items`/`columns`
  keys, nested cards) and skips anything unrecognizable.
- **System health:** if `<root>/monitor/status.json` exists and parses as a JSON
  object, its top-level scalar fields appear in the health strip at the top of the
  UI. Absent or corrupt, the strip simply hides.

The scanner only reads project folders. It never writes into them.

## Where state lives

All dashboard metadata is one JSON file:

```
<hermes-root>/dashboard/state.json
```

It records bucket overrides (`active` | `research` | `snoozed` | `archived`),
snooze wake times (ISO 8601 UTC), and archive timestamps, keyed by project ID.
Writes are atomic (temp file + rename), so a crash mid-write cannot tear the file.
Corrupt or missing state degrades to "everything Active" — never a crash — and
project files on disk are untouched by any dashboard action.

Snooze-wake is computed at read time: a snoozed item whose wake time has passed
returns to its previous bucket and is reported with `woke: true`, which the UI
renders as an unmissable "woke from snooze" badge until you act on the item.

## The UI

- Left rail: the four buckets with live counts, plus global search (`/` focuses it).
- Main pane: project cards — name, owning agent, relative last activity, short
  description, friendly path with Copy path and Open folder buttons.
- Clicking a card opens a detail panel with move/snooze/archive/restore actions,
  never more than two clicks deep. Snooze presets: 1 h, 1 day, 3 days, 1 week,
  plus a custom date-time picker.
- Dark-mode aware via `prefers-color-scheme`; system font stack; one accent color.
- A purposeful empty state explains the buckets on a fresh install.

"Open folder" uses the platform file manager (`open` on macOS, `explorer` on
Windows, `xdg-open` elsewhere) and refuses any path outside the Hermes root.

## JSON API

All endpoints are JSON over the local port:

- `GET /api/projects` — every project with its computed bucket, `woke` flag,
  snooze wake time, and archive timestamp.
- `POST /api/projects/<id>/snooze` — body `{"until": "<ISO 8601>"}`.
- `POST /api/projects/<id>/archive`
- `POST /api/projects/<id>/restore` — body `{"bucket": "active" | "research"}`.
- `POST /api/projects/<id>/move` — body `{"bucket": "active" | "research" | "archived"}`.
- `POST /api/open` — body `{"path": ...}`; rejected (403) outside the Hermes root.
- `GET /api/search?q=...` — matching projects and file names across all roots.
- `GET /api/health` — contents of `<root>/monitor/status.json`, or `null`.

## Upgrade note for existing users

On upgrade the dashboard simply installs with the package and populates from your
current Hermes directories on first launch. With no prior `dashboard/state.json`,
everything defaults to Active (or Research when a project's own metadata says so).
No migration step, and nothing in your project folders is modified.
