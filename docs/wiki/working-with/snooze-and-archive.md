---
title: Snooze and archive
section: working-with
order: 3
---

# Snooze and archive

You want a project out of your face — either until later (snooze) or indefinitely (archive) — without losing anything. Both actions live on every project card and in the detail panel of the [dashboard](/includes/dashboard.html), never more than two clicks deep.

## Snooze: "not now, but come back"

Snooze any item for a duration you choose: presets of **1 hour, 1 day, 3 days, or 1 week**, or a custom date and time from the picker.

What happens:

- The item leaves the working views (Active and Research) immediately.
- It appears in the **Snoozed** view, which lists everything currently sleeping together with its wake time.
- At wake time it resurfaces automatically in its original bucket, carrying a visible "returned" treatment so you cannot miss that it is back and why.

From the Snoozed view you can also **wake an item early** or **extend** its snooze. Use snooze for anything with a natural revisit date: work waiting on someone else, a decision you have deliberately parked, research that should resurface before a meeting.

## Archive: "done with this, keep the record"

Archiving hides an item from the working views. That is all it does:

- **Files on disk are untouched.** Archive is a view-level state, not a delete.
- The **Archive** view is browsable and searchable, and shows when each item was archived.
- Any archived item can be **restored** to Active or Research in one action.

Use archive for completed projects, dead ends, and anything you want out of daily scanning but findable forever.

## Where this state lives (and why it is robust)

Bucket assignments, snooze timers, and archive records are dashboard metadata, stored in a single file at `~/.hermes/dashboard/state.json`. It survives restarts, upgrades, and re-onboarding. If it is ever corrupt or missing, the dashboard degrades to "everything Active" rather than crashing — annoying, but nothing is lost except the sorting, because project files were never inside it.

## Related pages

- [Using the dashboard](/working-with/using-the-dashboard.html)
- [Hermes Project Dashboard](/includes/dashboard.html)
- [Finding your files](/working-with/finding-files.html)
