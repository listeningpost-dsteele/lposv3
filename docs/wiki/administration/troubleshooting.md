---
title: Troubleshooting
section: administration
order: 6
---

# Troubleshooting

Something failed and you want to know what it means and what to do. Start with one principle from the LPOS Laws: *failures are explicit, diagnostic, and actionable.* When the CLI hits an expected failure it prints a canonical JSON object to stderr — `{"error": "<ErrorType>", "message": "..."}` — and exits 1. The `error` field is the engine's typed failure class, and each one tells you which rule you ran into.

## The engine's error types

These are the real failure classes from the engine (`src/lpos_engine/errors.py`), what each means, and what to do.

| Error | Meaning | What to do |
|---|---|---|
| `ValidationError` | An envelope or record violates its schema or invariant | Check the message for the failing field; the 17 packaged schemas are the contract |
| `NotFoundError` | A requested state object does not exist | Check the ID (task, action, question) and that you are pointing at the right `--db` |
| `InvalidTransitionError` | A state transition is not permitted by the task state machine | The task is not in the state your operation assumes; `lpos inspect` shows its current status |
| `ConcurrencyError` | Optimistic concurrency or idempotency protection rejected a write | Something else updated the object first, or this operation already ran; re-read and retry deliberately — this is protection, not corruption |
| `PolicyViolation` | A constitutional policy blocked an operation | The base class for everything below; the message names the policy |
| `ApprovalRequired` | An exact action lacks a valid, bound approval | The action cannot execute until the Principal approves it; this is the system working as designed |
| `ApprovalMismatch` | An approval does not bind to the action being applied | The action changed after approval, or the wrong approval was presented; re-plan and re-approve the exact action |
| `ApprovalExpired` | An approval is no longer valid | Approvals expire and are single-use; request a fresh one |
| `IdentityVerificationError` | The purported Principal identity is not verified for the channel | Verify the channel during onboarding/connector setup; unverified identities can never authorize anything |
| `ReplayDetected` | An inbound message or approval has already been processed | Harmless by design — duplicates and replays are rejected, not re-executed |
| `ContextIsolationError` | A review context contains prohibited creator material or is not fresh | The independent review's isolation was violated; rebuild the review context per the review envelope rules |
| `AdapterError` | A model, tool, channel, or scheduler adapter failed | Check the adapter's own logs and the [Connector Health Monitor](/includes/connector-health-monitor.html) status |
| `ActionExecutionError` | An action executor returned an explicit failure | Read the action result via `lpos inspect`; the adapter reported a real failure performing the action |

Notice how many of these are the safety model showing itself: `ApprovalRequired`, `ApprovalMismatch`, `ApprovalExpired`, `IdentityVerificationError`, and `ReplayDetected` are the control plane refusing to guess.

## `lpos doctor` says unhealthy

Doctor reports `"status": "unhealthy"` (and exits nonzero) when the specification kernel fails to load or the counts are not exactly 32 specialists, 21 standing operations, and 53 benchmarks. That means the installation's packaged assets are damaged or mismatched. Re-run `python verify_release.py` from the release root — it will name every file that is missing, modified, or unlisted — and reinstall from a clean bundle if it fails.

## Installer failures

- **`Python 3.11+ is required; found ...`** — install a newer Python; re-run the installer.
- **`RELEASE.json is missing or invalid`** / **`RELEASE.json does not name the bundled wheel`** — you are not in the bundle root, or the extraction is incomplete.
- **`LPOS v4 release verification FAILED`** — the bundle's files do not match the manifest (`missing immutable file`, `hash mismatch`, `unlisted immutable file`, or version desynchronization). Re-download and re-extract; do not install a bundle that fails verification.
- **`virtual-environment Python was not created`** — your Python installation cannot create venvs; ensure the `venv` module works, or use `--reset-environment` to rebuild a broken one.

## Database problems

- **Migration errors on startup or `init`** — migrations are checksummed; drift in an applied migration stops startup deliberately. Restore from backup rather than editing the database.
- **Integrity check failures in `doctor --db`** — the SQLite file is damaged; restore from your latest backup ([Backups](/administration/backups.html)).
- **Attempts to modify events fail** — by design: the `events` table rejects updates and deletes through database triggers.

## Connector problems

Connector failures reach you as `LPOS ALERT` emails with the exact error and likely fix, and the current state is always in the dashboard's health strip and `~/.hermes/monitor/status.json`. Fix the credential or service, then confirm with `lpos monitor audit`. See [Connector Health Monitor](/includes/connector-health-monitor.html) and [Connector setup](/administration/connector-setup.html).

## Operations gone quiet or noisy

A Standing Operation that has nothing to say returns `[SILENT]` — that is normal and still records evidence. Four consecutive silent or near-empty runs trigger an SO-008 review automatically. If an operation is noisy or failing, [SO-008: Standing Operation Health](/reference/so-008.html) is the operation whose job is to catch it within a day; its output includes recommended changes.

## Related pages

- [Checking system health](/working-with/checking-system-health.html)
- [Install LPOS](/getting-started/install.html)
- [Backups](/administration/backups.html)
- [Connector setup](/administration/connector-setup.html)
