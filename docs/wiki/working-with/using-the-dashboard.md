---
title: Using the dashboard
section: working-with
order: 1
---

# Using the dashboard

You want to check what your system is doing right now. The dashboard is where you look — open `http://localhost:7373` (it is already running; it starts with the system).

## A daily reading habit

The dashboard is built for scanning a few dozen projects at a glance, calm rather than flashy. A workable rhythm:

1. **Glance at the system-health strip.** It reflects the [Connector Health Monitor](/includes/connector-health-monitor.html)'s latest audit. Green: move on. Something down: you already know why the related agents may be stuck, and the [alert email](/includes/connector-health-monitor.html) has the details and likely fix.
2. **Scan Active.** Active is the default view. Each card shows the project name, the owning agent or guild, and last activity — recency is the fastest signal for "is anything stalled?"
3. **Look for the woke-from-snooze treatment.** Items returning from snooze carry an unmissable "returned" indicator; they are back because you asked to deal with them now.
4. **Check Research occasionally.** Longer-running exploratory work lives there so it does not clutter Active. Items move freely between the two buckets.

## Acting on a project

Select a card to open the detail panel. From there every core action is at most two clicks (and keyboard-friendly):

- **Open folder** — opens the project's directory in your OS file manager.
- **Copy path** — copies the full disk path.
- **Move bucket** — between Active and Research.
- **Snooze / Archive / Restore** — see [Snooze and archive](/working-with/snooze-and-archive.html).

The detail panel also lists the project's recently indexed output files, so you can jump straight to a deliverable.

## Searching

Global search in the left rail matches project names and file names across all Hermes roots — including archived items. If you remember anything about a deliverable ("the pricing memo", "that CSV from last week"), search is usually faster than browsing. For everything else about locating output, see [Finding your files](/working-with/finding-files.html).

## If the dashboard looks wrong

- **Everything is suddenly in Active.** The dashboard's state file (`~/.hermes/dashboard/state.json`) was missing or corrupt, and the dashboard degraded safely to "everything Active" rather than crashing. Your files and projects are untouched — only bucket assignments, snooze timers, and archive flags were in that file. Re-sort as you go.
- **A project is missing.** The dashboard reads projects from the Hermes directories on disk. If the folder exists but does not appear, check that it is under the configured Hermes root.
- **The page does not load.** The service starts with the system; restart LPOS, or start it manually with `lpos dashboard`.

## Related pages

- [Hermes Project Dashboard](/includes/dashboard.html)
- [Snooze and archive](/working-with/snooze-and-archive.html)
- [Finding your files](/working-with/finding-files.html)
- [Checking system health](/working-with/checking-system-health.html)
