# COE Operations

Release: LPOS 4.5.0

## Required production configuration

```text
COE_ENABLED=true
COE_SCHEDULE_ENABLED=true
COE_DASHBOARD_ENABLED=true
COE_EMAIL_ENABLED=true
COE_TIMEZONE=America/Chicago
COE_CRON=0 3 * * *
COE_STATE_DIR=<writable path outside the release>
COE_REPORT_RECIPIENT=<secure operator profile reference>
COE_EMAIL_TRANSPORT=<configured transport adapter>
PUBLIC_BASE_URL=https://chip.listeningpost.ai
COE_DASHBOARD_PATH=/dashboard/coe
```

Doctor blocks production readiness when a required flag, path, schedule, recipient, transport, dashboard authentication policy, migration, identity mirror, or release verifier fails.

## Daily execution

The daily idempotency key is `coe-daily:<Central date> America/Chicago`. A database lease prevents overlap. A second runner exits visibly. Triggers are `scheduled-daily`, `manual`, `pre-release`, `post-deploy`, and `backfill`.

The scheduler first records a deterministic wake decision. No qualifying input produces `wakeAgent=false` and no model call.

## Backup and restore

Each audit creates a SQLite-consistent backup through the SQLite backup API, hashes it, restores it into an isolated temporary directory, reruns `PRAGMA integrity_check`, verifies the audit sentinel, records cleanup, and persists the outcome. Copy existence alone is not restore evidence.

## Emergency controls

Scheduler, email, and dashboard execution can be disabled for an incident while immutable release verification and evidence remain intact. A production release with required COE flags disabled stays blocked.

Database migrations are additive. Legacy `/Users/dan/lpos-state` remains read-only and is tracked as `TD-LEGACY-LPOS-STATE` until a separate reversible migration is approved and verified.
