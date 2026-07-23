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

Security hardening in this release closes audit findings **LPOS-06** (session-token
authentication, Host/Origin validation, request limits, loopback-only policy,
hardening headers, safe error handling) and **LPOS-09** (symlink and
absolute-path containment in the scanner and the open-folder API). See
[Security model](#security-model) below.

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

## Security model

### Session token (LPOS-06)

Every start generates a fresh high-entropy session token
(`secrets.token_urlsafe(32)`). It is written atomically to:

```
<hermes-root>/dashboard/token        (mode 0600)
```

**Every `/api` route — GET and POST — requires the token.** Send it as either
header:

```
Authorization: Bearer <token>
X-LPOS-Token: <token>
```

Requests with a missing or wrong token get `401` with no data and no state
change. `GET /` (the UI shell) does not require the token — it contains no
project data — and the server injects the current token into the page's inline
script at render time, so the UI sends it automatically on every fetch.

curl users read the token file:

```bash
TOKEN=$(cat ~/.hermes/dashboard/token)
curl -H "X-LPOS-Token: $TOKEN" http://127.0.0.1:7373/api/projects
```

The token rotates on every server start; anything automating against the API
must re-read the file after a restart.

### Host and Origin rules (LPOS-06)

- **Host:** every request (including `GET /`) must carry a Host header matching
  the bound host and port. When bound to loopback, `localhost:<port>`,
  `127.0.0.1:<port>`, and `[::1]:<port>` are accepted; anything else is
  rejected with `400`. This defeats DNS-rebinding attacks.
- **Origin:** a state-changing (POST) request whose Origin header is present
  and is not the dashboard's own origin is rejected with `403`. Because
  authentication is header-based (never a cookie), cross-site form posts can
  never authenticate anyway — CSRF is covered twice over.

### Request limits (LPOS-06)

- POST bodies must be `Content-Type: application/json` (else `415`).
- Bodies are capped at 1 MB (`413`); query strings at 2048 characters (`414`).

### Loopback-only policy (LPOS-06)

The server **refuses to start** on a non-loopback `--host` unless the
environment variable `LPOS_DASHBOARD_ALLOW_NONLOOPBACK=1` is set, and even then
it prints a prominent warning. Remote use is only supported behind a hardened
reverse proxy that terminates TLS and performs its own authentication; the
proxy must forward a loopback Host header (e.g. `127.0.0.1:<port>`).

### Response hardening and errors (LPOS-06)

Every response carries:

```
Content-Security-Policy: default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; connect-src 'self'; img-src 'self' data:
X-Frame-Options: DENY
X-Content-Type-Options: nosniff
Referrer-Policy: no-referrer
Cache-Control: no-store
```

Unexpected server errors return a generic `{"error": "internal server error"}`
body; tracebacks and internal paths are never sent to clients (with
`--verbose` the traceback is logged to stderr only).

### Path containment (LPOS-09)

- Symlinked project directories are **never** scanned as projects.
- Every configured root (standard and `roots.json` extras) must exist and
  resolve cleanly; the resolved form is the approved boundary. Extra roots are
  separately approved roots, not arbitrary path strings.
- Search never follows directory symlinks and only walks directories that
  resolve inside an approved root.
- A kanban card `path` is resolved and must land inside an approved root
  (the Hermes root or an approved extra root); otherwise the card keeps its
  metadata but is reported with `path: null` and
  `note: "path outside approved roots"`.
- `POST /api/open` resolves the requested path (following symlinks) and
  requires containment inside an approved root **before** anything is handed
  to the OS opener; violations get `403`.

## Configuration

| Setting | How to set it | Default |
| --- | --- | --- |
| Hermes root | `LPOS_HERMES_ROOT` env var, or `--root` | `~/.hermes` |
| Port | `--port` | `7373` |
| Bind address | `--host` | `127.0.0.1` (localhost only) |
| Non-loopback override | `LPOS_DASHBOARD_ALLOW_NONLOOPBACK=1` env var | off |
| Extra project roots | `<root>/dashboard/roots.json` | none |
| Session token file | written by the server | `<root>/dashboard/token` (0600) |

`roots.json` is either a JSON array of directory paths or `{"roots": [...]}`.
Relative entries resolve against the Hermes root. Each entry is an approved
root: it must exist and resolve cleanly (symlinks followed) or it is ignored,
and everything the dashboard reports is contained inside the resolved approved
roots (LPOS-09).

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
Windows, `xdg-open` elsewhere) and refuses any path that does not resolve
inside the approved roots (symlinks are resolved first — LPOS-09).

## JSON API

All endpoints are JSON over the local port. **Every `/api` request must carry
the session token** (see [Security model](#security-model)); requests without
it get `401`.

- `GET /api/projects` — every project with its computed bucket, `woke` flag,
  snooze wake time, and archive timestamp.
- `POST /api/projects/<id>/snooze` — body `{"until": "<ISO 8601>"}`.
- `POST /api/projects/<id>/archive`
- `POST /api/projects/<id>/restore` — body `{"bucket": "active" | "research"}`.
- `POST /api/projects/<id>/move` — body `{"bucket": "active" | "research" | "archived"}`.
- `POST /api/open` — body `{"path": ...}`; rejected (403) when the resolved
  path is outside the approved roots.
- `GET /api/search?q=...` — matching projects and file names across all roots.
- `GET /api/health` — contents of `<root>/monitor/status.json`, or `null`.

## Upgrade note for existing users

On upgrade the dashboard simply installs with the package and populates from your
current Hermes directories on first launch. With no prior `dashboard/state.json`,
everything defaults to Active (or Research when a project's own metadata says so).
No migration step, and nothing in your project folders is modified.
