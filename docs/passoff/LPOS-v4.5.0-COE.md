# LPOS 4.5.0 COE Pass-off

Status: implementation in progress, external publication verification pending

## Permanent operating contract

COE is a permanent constitutional subsystem. It runs daily at 03:00 America/Chicago. New or modified code is included in the engineering audit range. Release readiness is fail-closed and requires nine current command-backed gate records for one audit, source commit, release identity, and staged artifact.

Immutable application releases are fully enumerated and verified. Mutable state, evidence, reports, history, caches, and backups remain outside the release.

The deployed private dashboard is `https://chip.listeningpost.ai/dashboard/coe`. A report is rendered for every terminal daily audit and delivery is recorded only after verifiable provider acceptance.

## Ownership and rollback

LPOS Platform Operations owns audit execution, scheduler registration, evidence retention, backup restore tests, dashboard availability, and delivery retries. Rollback selects an exact verified artifact and does not destructively downgrade SQLite.

The legacy `/Users/dan/lpos-state` boundary remains read-only. It is tracked as `TD-LEGACY-LPOS-STATE` and requires a separate validated, reversible migration.

## External pass-off evidence

GitHub, project wiki, and Google Drive references must be recorded with content hash, verification timestamp, and status after readback. Until all three are verified, the documentation gate and release decision remain blocked.
