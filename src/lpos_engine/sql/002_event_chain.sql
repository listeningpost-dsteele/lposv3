PRAGMA foreign_keys = ON;

-- LPOS-08: tamper-evident audit event chain.
--
-- Every audit event gains a hash-chain link:
--   this_hash = sha256(prev.this_hash || "\n" || canonical_json(event_row))
-- anchored at a fixed GENESIS constant.  The chain is computed by
-- SQLiteStore (SQLite has no SHA-256 function); this migration creates the
-- storage and SQLiteStore backfills links for pre-existing event rows, in
-- insertion order, during the same initialization that applies it.
--
-- The append-only triggers below are an ordinary-write guard only: the
-- database owner can drop them.  Dropping them and editing an event breaks
-- the recomputed chain, which store.verify_event_chain() detects.

CREATE TABLE IF NOT EXISTS event_chain (
    sequence INTEGER PRIMARY KEY REFERENCES events(sequence) ON DELETE RESTRICT,
    event_id TEXT NOT NULL UNIQUE,
    prev_hash TEXT NOT NULL,
    this_hash TEXT NOT NULL UNIQUE,
    linked_at TEXT NOT NULL
);

CREATE TRIGGER IF NOT EXISTS event_chain_no_update
BEFORE UPDATE ON event_chain
BEGIN
    SELECT RAISE(ABORT, 'event chain is append-only');
END;

CREATE TRIGGER IF NOT EXISTS event_chain_no_delete
BEFORE DELETE ON event_chain
BEGIN
    SELECT RAISE(ABORT, 'event chain is append-only');
END;

-- Optional externally-keyed checkpoints: when an admin checkpoint key is
-- configured (LPOS_EVIDENCE_CHECKPOINT_KEY), periodic rows carry an HMAC tag
-- over (sequence, this_hash) so wholesale chain regeneration without the key
-- is detectable.
CREATE TABLE IF NOT EXISTS event_checkpoints (
    checkpoint_id INTEGER PRIMARY KEY AUTOINCREMENT,
    sequence INTEGER NOT NULL,
    this_hash TEXT NOT NULL,
    hmac_tag TEXT,
    key_id TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_event_checkpoints_sequence ON event_checkpoints(sequence);

UPDATE schema_metadata SET value = '2' WHERE key = 'schema_version' AND value < '2';
