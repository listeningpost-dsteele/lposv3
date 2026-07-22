---
title: Upgrading
section: administration
order: 5
---

# Upgrading

You have a new LPOS release and a running system you care about. The upgrade discipline is written into the operating specification itself: **a release is replaced completely, and only after verification, backup, and a passing doctor.** No partial upgrades, no in-place file swapping.

## The rules (from the runtime path discipline)

- The installer creates one self-contained LPOS directory per release.
- Scheduled jobs invoke the installed `lpos` command and packaged workflow IDs, never a temporary staging or historical release directory.
- Upgrades replace the complete release only after: bundle verification, database backup, migration validation, and a passing `lpos doctor`.

## A safe upgrade, step by step

1. **Extract the new release** into a *new* directory next to the current one (for example `LPOS-vN.N.N/`). Do not extract over the running install.
2. **Verify the bundle** from inside the new directory:

    ```bash
    python verify_release.py
    ```

    This checks every file hash against the release manifest and confirms version synchronization. Do not proceed on a failure.
3. **Back up your database** from the current install (see [Backups](/administration/backups.html)):

    ```bash
    lpos export --db state/lpos.db --output pre-upgrade-events.jsonl
    ```

    and copy `state/lpos.db` itself.
4. **Install the new release** in its directory: `bash INSTALL.sh` (or the platform equivalent). This builds the new `.venv`, installs the new wheel offline, and runs its own verification flow.
5. **Point the new install at your state** and validate migrations against a *copy* first if you want the extra caution, then run:

    ```bash
    lpos init --db state/lpos.db
    lpos doctor --db state/lpos.db
    ```

    `init` applies any new checksummed migrations; drift in an already-applied migration stops startup rather than corrupting state. `doctor` must report healthy before the new release is considered live.
6. **Run the evaluations**: `lpos evals` should pass everything (53/53 on v4.0.0).
7. **Repoint whatever launches LPOS** (scheduled jobs, service supervision) at the new release directory's installed `lpos`, and keep the prior version's directory as your rollback path until you are confident.

## Rollback

Because each release is self-contained and you kept the prior directory plus a pre-upgrade database backup, rollback is: repoint scheduled jobs back to the previous directory, restore the database backup if migrations were applied, and run `lpos doctor` there. Keeping a rollback path is not optional politeness, preserving one is part of the system's own preserve-good-work rule.

## What upgrades do to your data and modules

- **Your state carries forward.** The database is migrated, never recreated; artifacts, evidence, decisions, and events persist.
- **Dashboard and monitor state survive.** `~/.hermes/dashboard/state.json` and `~/.hermes/monitor/` live outside the release directory, so bucket assignments, snooze timers, archive records, and connector history survive upgrades and re-onboarding. On upgrade to 4.1.0, the dashboard installs, starts, and populates from your current Hermes directories with everything defaulting to Active.
- **The docs upgrade with the code.** Every release rebuilds this wiki from the same repository, and the version badge on every page tells you which release you are reading about. Check [Patch Notes](/patch-notes/index.html) after each upgrade.

## Related pages

- [Backups](/administration/backups.html)
- [Install LPOS](/getting-started/install.html)
- [Patch notes](/patch-notes/index.html)
- [Troubleshooting](/administration/troubleshooting.html)
