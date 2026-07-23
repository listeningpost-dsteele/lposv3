PRAGMA foreign_keys = ON;

UPDATE schema_metadata SET value = '3' WHERE key = 'schema_version' AND value < '3';

CREATE TABLE IF NOT EXISTS sentinel_assessments (
    assessment_id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL REFERENCES tasks(task_id) ON DELETE RESTRICT,
    artifact_id TEXT,
    artifact_hash TEXT,
    assessment_hash TEXT NOT NULL UNIQUE,
    policy_version TEXT NOT NULL,
    trigger_name TEXT NOT NULL,
    status TEXT NOT NULL,
    assessment_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(task_id, artifact_hash, policy_version, trigger_name)
);
CREATE INDEX IF NOT EXISTS idx_sentinel_assessments_artifact
    ON sentinel_assessments(task_id, artifact_hash, created_at);

CREATE TABLE IF NOT EXISTS sentinel_assessment_reviews (
    review_id TEXT PRIMARY KEY,
    assessment_id TEXT NOT NULL UNIQUE REFERENCES sentinel_assessments(assessment_id) ON DELETE RESTRICT,
    assessment_hash TEXT NOT NULL,
    task_id TEXT NOT NULL REFERENCES tasks(task_id) ON DELETE RESTRICT,
    artifact_hash TEXT,
    envelope_hash TEXT NOT NULL,
    review_hash TEXT NOT NULL UNIQUE,
    decision TEXT NOT NULL,
    trusted INTEGER NOT NULL CHECK(trusted IN (0, 1)),
    reviewer_adapter TEXT NOT NULL,
    review_context_id TEXT NOT NULL,
    review_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sentinel_reviews_artifact
    ON sentinel_assessment_reviews(task_id, artifact_hash, trusted, created_at);

CREATE TABLE IF NOT EXISTS sentinel_reports (
    report_id TEXT PRIMARY KEY,
    assessment_id TEXT NOT NULL REFERENCES sentinel_assessments(assessment_id) ON DELETE RESTRICT,
    review_id TEXT NOT NULL UNIQUE REFERENCES sentinel_assessment_reviews(review_id) ON DELETE RESTRICT,
    task_id TEXT NOT NULL REFERENCES tasks(task_id) ON DELETE RESTRICT,
    artifact_hash TEXT,
    overall TEXT NOT NULL,
    report_hash TEXT NOT NULL UNIQUE,
    report_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sentinel_reports_task
    ON sentinel_reports(task_id, created_at);

CREATE TABLE IF NOT EXISTS sentinel_report_acknowledgements (
    acknowledgement_id TEXT PRIMARY KEY,
    report_id TEXT NOT NULL UNIQUE REFERENCES sentinel_reports(report_id) ON DELETE RESTRICT,
    acknowledgement_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TRIGGER IF NOT EXISTS sentinel_assessments_no_update
BEFORE UPDATE ON sentinel_assessments
BEGIN SELECT RAISE(ABORT, 'sentinel assessments are append-only'); END;
CREATE TRIGGER IF NOT EXISTS sentinel_assessments_no_delete
BEFORE DELETE ON sentinel_assessments
BEGIN SELECT RAISE(ABORT, 'sentinel assessments are append-only'); END;

CREATE TRIGGER IF NOT EXISTS sentinel_assessment_reviews_no_update
BEFORE UPDATE ON sentinel_assessment_reviews
BEGIN SELECT RAISE(ABORT, 'sentinel assessment reviews are append-only'); END;
CREATE TRIGGER IF NOT EXISTS sentinel_assessment_reviews_no_delete
BEFORE DELETE ON sentinel_assessment_reviews
BEGIN SELECT RAISE(ABORT, 'sentinel assessment reviews are append-only'); END;

CREATE TRIGGER IF NOT EXISTS sentinel_reports_no_update
BEFORE UPDATE ON sentinel_reports
BEGIN SELECT RAISE(ABORT, 'sentinel reports are append-only'); END;
CREATE TRIGGER IF NOT EXISTS sentinel_reports_no_delete
BEFORE DELETE ON sentinel_reports
BEGIN SELECT RAISE(ABORT, 'sentinel reports are append-only'); END;

CREATE TRIGGER IF NOT EXISTS sentinel_acknowledgements_no_update
BEFORE UPDATE ON sentinel_report_acknowledgements
BEGIN SELECT RAISE(ABORT, 'sentinel acknowledgements are append-only'); END;
CREATE TRIGGER IF NOT EXISTS sentinel_acknowledgements_no_delete
BEFORE DELETE ON sentinel_report_acknowledgements
BEGIN SELECT RAISE(ABORT, 'sentinel acknowledgements are append-only'); END;
