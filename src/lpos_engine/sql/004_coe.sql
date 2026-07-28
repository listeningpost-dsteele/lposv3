PRAGMA foreign_keys = ON;

UPDATE schema_metadata SET value = '4' WHERE key = 'schema_version' AND value < '4';

CREATE TABLE IF NOT EXISTS coe_audits (
    audit_id TEXT PRIMARY KEY,
    trigger_name TEXT NOT NULL,
    local_date TEXT NOT NULL,
    timezone TEXT NOT NULL,
    idempotency_key TEXT NOT NULL UNIQUE,
    release_version TEXT NOT NULL,
    git_commit TEXT NOT NULL,
    artifact_sha256 TEXT NOT NULL,
    baseline_audit_id TEXT,
    status TEXT NOT NULL,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    audit_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS coe_gate_evidence (
    evidence_id TEXT PRIMARY KEY,
    audit_id TEXT NOT NULL REFERENCES coe_audits(audit_id) ON DELETE RESTRICT,
    gate_id TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('pass','fail','error','skipped')),
    completed_at TEXT NOT NULL,
    previous_evidence_hash TEXT NOT NULL,
    evidence_hash TEXT NOT NULL UNIQUE,
    evidence_json TEXT NOT NULL,
    UNIQUE(audit_id, gate_id)
);

CREATE TABLE IF NOT EXISTS coe_release_decisions (
    decision_id TEXT PRIMARY KEY,
    audit_id TEXT NOT NULL UNIQUE REFERENCES coe_audits(audit_id) ON DELETE RESTRICT,
    status TEXT NOT NULL CHECK(status IN ('pass','blocked')),
    decision_hash TEXT NOT NULL UNIQUE,
    decision_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS coe_findings (
    finding_id TEXT PRIMARY KEY,
    audit_id TEXT NOT NULL REFERENCES coe_audits(audit_id) ON DELETE RESTRICT,
    severity TEXT NOT NULL,
    status TEXT NOT NULL,
    owner TEXT,
    finding_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS coe_opportunities (
    opportunity_id TEXT PRIMARY KEY,
    audit_id TEXT NOT NULL REFERENCES coe_audits(audit_id) ON DELETE RESTRICT,
    finding_id TEXT,
    status TEXT NOT NULL,
    owner TEXT,
    opportunity_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS coe_operator_decisions (
    operator_decision_id TEXT PRIMARY KEY,
    opportunity_id TEXT NOT NULL REFERENCES coe_opportunities(opportunity_id) ON DELETE RESTRICT,
    decision TEXT NOT NULL CHECK(decision IN ('approved','rejected','deferred')),
    actor TEXT NOT NULL,
    decision_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS coe_metrics (
    metric_id TEXT PRIMARY KEY,
    audit_id TEXT NOT NULL REFERENCES coe_audits(audit_id) ON DELETE RESTRICT,
    metric_name TEXT NOT NULL,
    metric_value REAL,
    unit TEXT,
    status TEXT NOT NULL,
    metric_json TEXT NOT NULL,
    observed_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS coe_technical_debt (
    debt_id TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    owner TEXT NOT NULL,
    review_at TEXT NOT NULL,
    debt_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS coe_scheduler_jobs (
    job_id TEXT PRIMARY KEY,
    enabled INTEGER NOT NULL CHECK(enabled IN (0,1)),
    job_json TEXT NOT NULL,
    observed_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS coe_scheduler_executions (
    execution_id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL,
    audit_id TEXT,
    status TEXT NOT NULL,
    execution_json TEXT NOT NULL,
    started_at TEXT NOT NULL,
    completed_at TEXT
);
CREATE TABLE IF NOT EXISTS coe_wake_decisions (
    wake_id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL,
    audit_id TEXT,
    eligible INTEGER NOT NULL CHECK(eligible IN (0,1)),
    wake_agent INTEGER NOT NULL CHECK(wake_agent IN (0,1)),
    model_invoked INTEGER NOT NULL CHECK(model_invoked IN (0,1)),
    reason_code TEXT NOT NULL,
    decision_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS coe_backups (
    backup_id TEXT PRIMARY KEY,
    audit_id TEXT,
    status TEXT NOT NULL,
    manifest_hash TEXT NOT NULL,
    backup_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS coe_restore_tests (
    restore_test_id TEXT PRIMARY KEY,
    backup_id TEXT NOT NULL REFERENCES coe_backups(backup_id) ON DELETE RESTRICT,
    audit_id TEXT,
    status TEXT NOT NULL,
    restore_json TEXT NOT NULL,
    completed_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS coe_artifacts (
    artifact_id TEXT PRIMARY KEY,
    audit_id TEXT,
    owner TEXT NOT NULL,
    lifecycle_class TEXT NOT NULL,
    manifest_hash TEXT NOT NULL,
    artifact_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT
);
CREATE TABLE IF NOT EXISTS coe_report_deliveries (
    delivery_id TEXT PRIMARY KEY,
    audit_id TEXT NOT NULL REFERENCES coe_audits(audit_id) ON DELETE RESTRICT,
    status TEXT NOT NULL,
    attempt_number INTEGER NOT NULL,
    provider_message_id TEXT,
    report_hash TEXT NOT NULL,
    delivery_json TEXT NOT NULL,
    started_at TEXT NOT NULL,
    completed_at TEXT
);
CREATE TABLE IF NOT EXISTS coe_documentation_passoff (
    passoff_id TEXT PRIMARY KEY,
    audit_id TEXT,
    surface TEXT NOT NULL,
    status TEXT NOT NULL,
    reference TEXT NOT NULL,
    content_hash TEXT,
    verified_at TEXT,
    passoff_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS coe_audit_locks (
    idempotency_key TEXT PRIMARY KEY,
    owner TEXT NOT NULL,
    acquired_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    heartbeat_at TEXT NOT NULL
);

CREATE TRIGGER IF NOT EXISTS coe_gate_evidence_no_update BEFORE UPDATE ON coe_gate_evidence BEGIN SELECT RAISE(ABORT, 'COE gate evidence is append-only'); END;
CREATE TRIGGER IF NOT EXISTS coe_gate_evidence_no_delete BEFORE DELETE ON coe_gate_evidence BEGIN SELECT RAISE(ABORT, 'COE gate evidence is append-only'); END;
CREATE TRIGGER IF NOT EXISTS coe_release_decisions_no_update BEFORE UPDATE ON coe_release_decisions BEGIN SELECT RAISE(ABORT, 'COE release decisions are append-only'); END;
CREATE TRIGGER IF NOT EXISTS coe_release_decisions_no_delete BEFORE DELETE ON coe_release_decisions BEGIN SELECT RAISE(ABORT, 'COE release decisions are append-only'); END;
CREATE TRIGGER IF NOT EXISTS coe_operator_decisions_no_update BEFORE UPDATE ON coe_operator_decisions BEGIN SELECT RAISE(ABORT, 'COE operator decisions are append-only'); END;
CREATE TRIGGER IF NOT EXISTS coe_operator_decisions_no_delete BEFORE DELETE ON coe_operator_decisions BEGIN SELECT RAISE(ABORT, 'COE operator decisions are append-only'); END;
