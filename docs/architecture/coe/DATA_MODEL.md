# COE Data Model

Release: LPOS 4.5.0

Migration `004_coe.sql` adds the COE model to the checksummed LPOS v4 SQLite migration chain.

## Primary records

- `coe_audits`: audit scope, trigger, Central date, idempotency key, release identity, baseline, and terminal state.
- `coe_gate_evidence`: one record per required gate and audit. Records are append-only and hash chained.
- `coe_release_decisions`: one immutable decision for an audit.
- `coe_findings`: measured defects and risk states with evidence references.
- `coe_opportunities`: value-ranked proposed changes linked to findings.
- `coe_operator_decisions`: append-only approval, rejection, or deferral records.
- `coe_metrics`: time-series storage, wake, skill, cost, and health measurements.
- `coe_technical_debt`: owned compatibility and temporary-state lifecycle records.
- `coe_scheduler_jobs`, `coe_scheduler_executions`, and `coe_wake_decisions`: scheduler governance and deterministic model-wake facts.
- `coe_backups` and `coe_restore_tests`: backup identity plus actual isolated restore evidence.
- `coe_artifacts`: owner, purpose, lifecycle, verification, retention, and retirement metadata.
- `coe_report_deliveries`: transport attempts and provider acceptance evidence.
- `coe_documentation_passoff`: stable external references and readback verification.
- `coe_audit_locks`: database leases for overlap protection.

## Integrity

Gate evidence and release decisions reject ordinary update and delete operations through SQLite triggers. Each gate record includes `previous_evidence_hash` and `evidence_hash`. The controller validates all nine records in deterministic order before deciding.

Timestamps are UTC. Daily idempotency uses the Central local calendar date and stores `America/Chicago` explicitly.
