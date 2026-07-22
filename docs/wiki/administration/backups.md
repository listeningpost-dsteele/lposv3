---
title: Backups
section: administration
order: 4
---

# Backups

You want to be able to lose this machine and not lose your system's memory. The good news: LPOS keeps its authoritative state in one place, and ships a portable export format designed for exactly this.

## What to back up

| What | Where | Why |
|---|---|---|
| The state database | `state/lpos.db` | The authoritative record: tasks, contracts, specs, artifacts, reviews, actions, approvals, evidence, decisions, operation runs, completion reports, events |
| JSONL event exports | wherever you write them | Portable, ordered, line-per-event audit snapshots |
| Module state | `~/.hermes/dashboard/state.json`, `~/.hermes/monitor/` | Bucket/snooze/archive metadata and connector health history, small, and losing them degrades gracefully, but cheap to include |
| Your project files | your Hermes project directories | The deliverables themselves |

The release directory's *code* does not need backing up, it is reproducible from the release bundle. Secrets are not in LPOS state at all (they live in your credential store or secret manager), so back that store up by its own means.

## The export command

```bash
lpos export --db state/lpos.db --output backups/events-$(date +%F).jsonl
```

Each line of the export is one immutable event in sequence order. The export is explicitly suitable for review, backup, and evidence bundles. One caveat from the state contract, worth respecting: JSONL is an export format, not the concurrent source of truth, importing or replaying it requires a separately validated recovery procedure. For full restoration, the database file itself is the thing to preserve.

## Backing up the database file

`state/lpos.db` is a SQLite database running in WAL mode. Back it up when LPOS is quiescent (no operations mid-run), or use SQLite-aware tooling that handles WAL correctly. Copy the file, verify the copy opens, and then confirm health against it:

```bash
lpos doctor --db /path/to/backup/lpos.db
```

Doctor reports the backup's integrity check and applied migrations, a cheap way to know your backup is actually restorable.

Two properties protect the record itself: the `events` table is append-only (database triggers reject updates and deletes), and migrations are checksummed, so drift in an applied migration stops startup rather than silently corrupting history. Note the residual risk from the threat model: a privileged local administrator can alter local files, which is precisely why *external* backups of the database are part of the security posture, not just a convenience.

## Backups and upgrades

The upgrade discipline requires a database backup *before* the new release goes live: an upgrade replaces the complete release only after bundle verification, database backup, migration validation, and a passing `lpos doctor`. If you follow [Upgrading](/administration/upgrading.html), you get a pre-upgrade backup every time by construction.

## Storage and retention

Context bundles, artifacts, action parameters, evidence, and audit events may contain sensitive business data. Keep backups on appropriately protected storage, and define retention, redaction, and access policies for them the same way you would for the live database. LPOS core does not provide encryption at rest, use encrypted disks for both the live state and the backups.

## Related pages

- [Upgrading](/administration/upgrading.html)
- [Finding your files](/working-with/finding-files.html)
- [Configuration](/administration/configuration.html)
