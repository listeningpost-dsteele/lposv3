---
title: Uninstall
section: administration
order: 7
---

# Uninstall

You want LPOS off this machine, cleanly, without losing anything you might want later. Because the installer creates one self-contained directory and never scatters files into hidden system locations, uninstalling is short.

## Before you delete anything

1. **Export the audit trail** if you want to keep the record of what the system did:

    ```bash
    lpos export --db state/lpos.db --output ~/lpos-final-events.jsonl
    ```

2. **Copy the state database** (`state/lpos.db`) somewhere safe if you might ever reinstall, it holds every task, artifact, evidence record, and decision record.
3. **Collect your project files.** Deliverables live in your Hermes project directories, not inside the LPOS release directory. Use the [dashboard](/working-with/finding-files.html) to locate anything you want to keep first, its search covers the archive too.
4. **Unschedule LPOS.** Remove whatever invokes the installed `lpos` command on a schedule or at boot (scheduled jobs and service supervision were pointed at the release directory during setup), so nothing tries to run a deleted binary.

## Remove the system

1. **Delete the release directory**, the directory where you extracted the bundle. This removes the engine, the `.venv` local environment, the packaged specification, and `state/` (including `state/lpos.db` and `state/verification/`) in one step.
2. **Delete module state** if you do not plan to reinstall:

    ```text
    ~/.hermes/dashboard/    (bucket assignments, snooze timers, archive records)
    ~/.hermes/monitor/      (connector health history and status.json)
    ```

    If you *do* plan to reinstall, leave these: they survive re-onboarding by design, and the dashboard will pick your bucket assignments back up.
3. **Revoke credentials.** LPOS never stored your secrets, they live in your OS credential store or secret manager, so uninstalling LPOS does not remove them. Revoke or delete any tokens you provisioned specifically for LPOS connectors (model hosts, email, GitHub, cloud) from the store where you keep them.

## What is left afterward

Nothing runs, and nothing of the system remains except what you chose to keep: your exported JSONL, your database copy, and your project files. Your project directories are never touched by an uninstall, archiving, snoozing, and even deleting the dashboard state never modified files on disk.

## Related pages

- [Backups](/administration/backups.html)
- [Finding your files](/working-with/finding-files.html)
- [Install LPOS](/getting-started/install.html)
