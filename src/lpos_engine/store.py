"""Transactional SQLite state and append-only, hash-chained event storage.

File confidentiality (LPOS-07)
------------------------------
State directories are created ``0700`` and the database file ``0600``
independently of the process umask.  On open of an existing database the
store checks the file mode and repairs group/other access to ``0600`` with an
audit event, or fails closed when repair is impossible (e.g. foreign
ownership).  On Windows this is a best-effort no-op.  The module-level
helpers ``secure_mkdir``, ``secure_create_file``, and ``harden_file_mode``
are reusable; other LPOS writers of sensitive state (monitor, compliance,
dashboard) should adopt them.

Evidence tamper evidence (LPOS-08)
----------------------------------
Every audit event is linked into a SHA-256 hash chain
(``this_hash = sha256(prev.this_hash + "\\n" + canonical_json(event_row))``,
anchored at a GENESIS constant).  ``verify_event_chain`` recomputes the chain
and reports the first divergent event; ``integrity_check``/``integrity_report``
combine this with SQLite's PRAGMA check.  Chaining DETECTS after-the-fact
edits (including dropping the append-only triggers and updating a payload);
it does not PREVENT them: an operator with database privileges can regenerate
the whole chain.  Mitigations layered here: optional HMAC checkpoints keyed
by an admin-held key file (``LPOS_EVIDENCE_CHECKPOINT_KEY``) make full-chain
regeneration without that key detectable, and ``export_jsonl`` provides the
hook for near-real-time export of events to an off-host append-only/WORM
destination, which is required for evidence that must survive a compromised
runtime account.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import sqlite3
import stat
from contextlib import contextmanager
from importlib.resources import files
from pathlib import Path
from typing import Any, Iterator, Mapping

from .canonical import canonical_json, digest, new_id, parse_timestamp, text_digest, utc_now
from .errors import ConcurrencyError, NotFoundError, ReplayDetected, ValidationError
from .models import (
    ActionPlan,
    ActionResult,
    ActionStatus,
    ApprovalGrant,
    ApprovalRequest,
    Artifact,
    ArtifactSpecification,
    CompletionReport,
    ContextBundle,
    DecisionRecord,
    EvidenceRecord,
    InterpretationContract,
    ReviewDecision,
    ReviewEnvelope,
    ReviewResult,
    StandingOperationRun,
    TaskEnvelope,
    TaskStatus,
)
from .state_machine import ActionStateMachine, TaskStateMachine

#: Fixed anchor for the audit event hash chain.
EVENT_CHAIN_GENESIS = hashlib.sha256(b"LPOS-EVENT-CHAIN-GENESIS").hexdigest()

#: Environment variable naming an admin-held key file for HMAC checkpoints.
CHECKPOINT_KEY_ENV = "LPOS_EVIDENCE_CHECKPOINT_KEY"

_POSIX = os.name == "posix"


def secure_mkdir(path: str | Path) -> Path:
    """Create ``path`` (and missing parents) with mode ``0700``.

    Modes are applied with ``chmod`` after creation so the result does not
    depend on the process umask.  Reusable helper for every LPOS component
    that writes sensitive state (store, monitor, compliance, dashboard).
    On non-POSIX platforms directory creation happens without mode changes.
    """

    target = Path(path)
    missing: list[Path] = []
    probe = target
    while not probe.exists():
        missing.append(probe)
        if probe.parent == probe:
            break
        probe = probe.parent
    target.mkdir(parents=True, exist_ok=True)
    if _POSIX:
        for created in missing:
            try:
                os.chmod(created, 0o700)
            except FileNotFoundError:  # pragma: no cover - concurrent removal
                pass
    return target


def secure_create_file(path: str | Path, mode: int = 0o600) -> bool:
    """Create ``path`` with a restrictive mode, umask-independent.

    Returns True when this call created the file, False when it already
    existed.  The file is created empty via ``os.open`` with the requested
    mode and then explicitly ``chmod``-ed (POSIX) so the umask cannot widen
    it.  Best-effort no-op for the mode on non-POSIX platforms.
    """

    target = Path(path)
    try:
        handle = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY, mode)
    except FileExistsError:
        return False
    os.close(handle)
    if _POSIX:
        os.chmod(target, mode)
    return True


def audit_state_permissions(hermes_root: str | Path) -> dict[str, Any]:
    """Report group/other-readable state files under the Hermes root (LPOS-15).

    Walks the runtime state directories (monitor, compliance, dashboard, plus any
    top-level ``*.db``) and flags any regular file whose mode grants group/other
    access. Status is ``ok`` when everything is 0600-tight, ``insecure`` when any
    world/group-readable state file is found, so ``lpos doctor --hermes-root``
    fails closed instead of merely claiming coverage. Best-effort no-op on
    non-POSIX platforms.
    """

    root = Path(hermes_root).expanduser()
    if not _POSIX:
        return {"status": "skipped", "reason": "non-POSIX platform", "insecure_files": []}
    insecure: list[dict[str, str]] = []
    checked = 0
    # State LPOS itself writes (not admin-supplied inputs like approved-checks.json
    # or registered-services.json, whose modes the operator owns).
    written = [
        root / "monitor" / "status.json", root / "monitor" / "state.json",
        root / "monitor" / "inventory.json", root / "monitor" / "alerts.json",
        root / "compliance" / "status.json", root / "compliance" / "history.jsonl",
        root / "compliance" / "report.html", root / "dashboard" / "token",
        root / "dashboard" / "state.json",
    ]
    candidates: list[Path] = [p for p in written if p.is_file()]
    candidates.extend(p for p in (root / "compliance").glob("history-archive-*.jsonl") if p.is_file())
    candidates.extend(p for p in root.glob("*.db") if p.is_file())
    for path in candidates:
        checked += 1
        try:
            current = stat.S_IMODE(os.stat(path).st_mode)
        except OSError:
            continue
        if current & 0o077:
            insecure.append({"path": str(path), "mode": format(current, "04o")})
    return {
        "status": "insecure" if insecure else "ok",
        "checked": checked,
        "insecure_files": insecure,
    }


def harden_file_mode(path: str | Path, mode: int = 0o600) -> dict[str, str] | None:
    """Remove group/other access from an existing file.

    Returns a repair description when the mode was corrected, ``None`` when it
    was already restrictive (or on non-POSIX platforms).  Raises ``OSError``
    when the repair is impossible (for example, the file is owned by another
    account) so callers can fail closed.
    """

    if not _POSIX:
        return None
    target = Path(path)
    info = os.stat(target)
    current = stat.S_IMODE(info.st_mode)
    if current & 0o077 == 0:
        return None
    os.chmod(target, mode)
    return {
        "path": str(target),
        "previous_mode": format(current, "04o"),
        "repaired_mode": format(mode, "04o"),
    }


class SQLiteStore:
    """Authoritative transactional state with an immutable, hash-chained audit stream."""

    #: A checkpoint row is written every N chained events when a key is configured.
    checkpoint_interval = 100

    def __init__(self, path: str | Path, *, checkpoint_key_path: str | Path | None = None) -> None:
        self.path = Path(path)
        secure_mkdir(self.path.parent)
        created = secure_create_file(self.path)
        permission_repair: dict[str, str] | None = None
        if not created:
            try:
                permission_repair = harden_file_mode(self.path)
            except OSError as exc:
                raise ValidationError(
                    f"state database {self.path} has insecure permissions or ownership "
                    f"that could not be repaired: {exc}"
                ) from exc
        self._load_checkpoint_key(checkpoint_key_path)
        self._initialize()
        self._harden_sidecar_files()
        self._backfill_event_chain()
        if permission_repair is not None:
            self.append_system_event(
                stream_type="store",
                stream_id="database",
                event_type="store.permissions_repaired",
                payload=permission_repair,
            )

    def _load_checkpoint_key(self, checkpoint_key_path: str | Path | None) -> None:
        self._checkpoint_key: bytes | None = None
        self._checkpoint_key_id: str | None = None
        source = checkpoint_key_path or os.environ.get(CHECKPOINT_KEY_ENV)
        if not source:
            return
        try:
            raw = Path(source).read_bytes().strip()
        except OSError as exc:
            raise ValidationError(
                f"evidence checkpoint key file is not readable: {source}"
            ) from exc
        if not raw:
            raise ValidationError(f"evidence checkpoint key file is empty: {source}")
        self._checkpoint_key = raw
        self._checkpoint_key_id = hashlib.sha256(raw).hexdigest()[:16]

    def _harden_sidecar_files(self) -> None:
        """Best-effort 0600 on WAL/SHM/journal sidecars (POSIX only).

        SQLite copies the main database's permissions when it creates these,
        so with a 0600 database they normally inherit 0600; this repairs
        sidecars created before hardening.
        """

        if not _POSIX:
            return
        for suffix in ("-wal", "-shm", "-journal"):
            sidecar = Path(str(self.path) + suffix)
            try:
                harden_file_mode(sidecar)
            except FileNotFoundError:
                continue
            except OSError:  # pragma: no cover - transient sidecar ownership issues
                continue

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=30, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = FULL")
        conn.execute("PRAGMA busy_timeout = 30000")
        return conn

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        """Yield a read connection and always close it.

        ``sqlite3.Connection``'s own context manager commits or rolls back but does
        not close the connection, so the store owns that lifecycle explicitly.
        """
        conn = self._connect()
        try:
            yield conn
        finally:
            conn.close()

    def _initialize(self) -> None:
        """Apply packaged SQL migrations and reject migration drift.

        Migration names and SHA-256 digests are persisted before the store is
        exposed.  Existing v0.1 databases without this ledger safely replay the
        idempotent initial migration once and then gain drift protection.
        """

        root = files("lpos_engine.sql")
        migrations = sorted(
            (item for item in root.iterdir() if item.name[:1].isdigit() and item.name.endswith(".sql")),
            key=lambda item: item.name,
        )
        if not migrations:
            raise ValidationError("LPOS engine package contains no SQL migrations")

        with self.connection() as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations ("
                "migration_name TEXT PRIMARY KEY, checksum TEXT NOT NULL, applied_at TEXT NOT NULL)"
            )
            for resource in migrations:
                name = resource.name
                script = resource.read_text(encoding="utf-8")
                checksum = text_digest(script)
                row = conn.execute(
                    "SELECT checksum FROM schema_migrations WHERE migration_name = ?",
                    (name,),
                ).fetchone()
                if row is not None:
                    if row["checksum"] != checksum:
                        raise ValidationError(
                            f"applied migration {name} differs from the packaged migration"
                        )
                    continue

                # ``executescript`` does not accept parameters, so only fixed
                # package-controlled metadata is quoted into the transaction.
                quoted_name = name.replace("'", "''")
                quoted_checksum = checksum.replace("'", "''")
                quoted_at = utc_now().replace("'", "''")
                wrapped = (
                    "BEGIN IMMEDIATE;\n"
                    + script
                    + "\nINSERT OR IGNORE INTO schema_migrations"
                    "(migration_name, checksum, applied_at) VALUES "
                    f"('{quoted_name}', '{quoted_checksum}', '{quoted_at}');\nCOMMIT;"
                )
                try:
                    conn.executescript(wrapped)
                except Exception:
                    if conn.in_transaction:
                        conn.rollback()
                    raise
                applied = conn.execute(
                    "SELECT checksum FROM schema_migrations WHERE migration_name = ?",
                    (name,),
                ).fetchone()
                if applied is None or applied["checksum"] != checksum:
                    raise ValidationError(f"migration {name} could not be recorded safely")

    def list_migrations(self) -> tuple[dict[str, str], ...]:
        with self.connection() as conn:
            rows = conn.execute(
                "SELECT migration_name, checksum, applied_at FROM schema_migrations "
                "ORDER BY migration_name"
            ).fetchall()
        return tuple(
            {
                "migration_name": row["migration_name"],
                "checksum": row["checksum"],
                "applied_at": row["applied_at"],
            }
            for row in rows
        )

    def integrity_check(self) -> str:
        """Combined database and audit-chain integrity summary.

        Returns ``"ok"`` only when BOTH the SQLite PRAGMA integrity check and
        the recomputed audit event hash chain pass; otherwise returns the
        failing detail as a human-readable string (the shape ``lpos doctor``
        and ``lpos init`` already surface).  Use ``integrity_report`` for the
        structured breakdown.
        """

        report = self.integrity_report()
        if report["ok"]:
            return "ok"
        if report["pragma"] != "ok":
            return report["pragma"]
        chain = report["event_chain"]
        if not chain["ok"]:
            detail = chain.get("error") or "event chain verification failed"
            first_bad = chain.get("first_bad_id")
            if first_bad:
                return f"event chain broken at {first_bad}: {detail}"
            return f"event chain broken: {detail}"
        sentinel = report["sentinel_records"]
        detail = sentinel.get("error") or "sentinel record verification failed"
        first_bad = sentinel.get("first_bad")
        if first_bad:
            return f"sentinel records tampered at {first_bad}: {detail}"
        return f"sentinel records tampered: {detail}"

    def integrity_report(self) -> dict[str, Any]:
        """Structured integrity details: PRAGMA result plus event-chain verification."""

        with self.connection() as conn:
            row = conn.execute("PRAGMA integrity_check").fetchone()
        pragma = str(row[0]) if row is not None else "unknown"
        chain = self.verify_event_chain()
        sentinel = self.verify_sentinel_records()
        return {
            "ok": pragma == "ok" and chain["ok"] and sentinel["ok"],
            "pragma": pragma,
            "event_chain": chain,
            "sentinel_records": sentinel,
        }

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    @staticmethod
    def _chain_material(
        *,
        sequence: int,
        event_id: str,
        stream_type: str,
        stream_id: str,
        event_type: str,
        payload_json: str,
        occurred_at: str,
    ) -> str:
        return canonical_json(
            {
                "sequence": sequence,
                "event_id": event_id,
                "stream_type": stream_type,
                "stream_id": stream_id,
                "event_type": event_type,
                "payload_json": payload_json,
                "occurred_at": occurred_at,
            }
        )

    @staticmethod
    def _chain_hash(prev_hash: str, material: str) -> str:
        return hashlib.sha256((prev_hash + "\n" + material).encode("utf-8")).hexdigest()

    @staticmethod
    def _chain_tip(conn: sqlite3.Connection) -> tuple[int, str]:
        row = conn.execute(
            "SELECT sequence, this_hash FROM event_chain ORDER BY sequence DESC LIMIT 1"
        ).fetchone()
        if row is None:
            return 0, EVENT_CHAIN_GENESIS
        return int(row["sequence"]), str(row["this_hash"])

    def _link_event(
        self,
        conn: sqlite3.Connection,
        *,
        sequence: int,
        event_id: str,
        stream_type: str,
        stream_id: str,
        event_type: str,
        payload_json: str,
        occurred_at: str,
    ) -> str:
        _, prev_hash = self._chain_tip(conn)
        material = self._chain_material(
            sequence=sequence,
            event_id=event_id,
            stream_type=stream_type,
            stream_id=stream_id,
            event_type=event_type,
            payload_json=payload_json,
            occurred_at=occurred_at,
        )
        this_hash = self._chain_hash(prev_hash, material)
        conn.execute(
            "INSERT INTO event_chain(sequence, event_id, prev_hash, this_hash, linked_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (sequence, event_id, prev_hash, this_hash, utc_now()),
        )
        self._maybe_checkpoint(conn, sequence=sequence, this_hash=this_hash)
        return this_hash

    def _checkpoint_tag(self, sequence: int, this_hash: str) -> str | None:
        if self._checkpoint_key is None:
            return None
        message = f"{sequence}\n{this_hash}".encode("utf-8")
        return hmac.new(self._checkpoint_key, message, hashlib.sha256).hexdigest()

    def _maybe_checkpoint(self, conn: sqlite3.Connection, *, sequence: int, this_hash: str) -> None:
        if self._checkpoint_key is None:
            return
        if sequence % self.checkpoint_interval != 0:
            return
        self._insert_checkpoint(conn, sequence=sequence, this_hash=this_hash)

    def _insert_checkpoint(self, conn: sqlite3.Connection, *, sequence: int, this_hash: str) -> None:
        conn.execute(
            "INSERT INTO event_checkpoints(sequence, this_hash, hmac_tag, key_id, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                sequence,
                this_hash,
                self._checkpoint_tag(sequence, this_hash),
                self._checkpoint_key_id,
                utc_now(),
            ),
        )

    def write_checkpoint(self) -> dict[str, Any] | None:
        """Checkpoint the current chain tip; returns the row data or None when empty.

        With an admin key configured (``LPOS_EVIDENCE_CHECKPOINT_KEY`` or the
        ``checkpoint_key_path`` constructor argument) the row carries an HMAC
        tag a runtime-only attacker cannot regenerate.  Checkpoints (and
        ``export_jsonl`` output) only provide independent assurance once
        copied off-host.
        """

        with self.transaction() as conn:
            sequence, this_hash = self._chain_tip(conn)
            if sequence == 0:
                return None
            self._insert_checkpoint(conn, sequence=sequence, this_hash=this_hash)
        return {
            "sequence": sequence,
            "this_hash": this_hash,
            "hmac_tag": self._checkpoint_tag(sequence, this_hash),
            "key_id": self._checkpoint_key_id,
        }

    def _backfill_event_chain(self) -> None:
        """Link any pre-chain event rows (in insertion order) into the chain."""

        with self.transaction() as conn:
            rows = conn.execute(
                "SELECT e.* FROM events e LEFT JOIN event_chain c ON c.sequence = e.sequence "
                "WHERE c.sequence IS NULL ORDER BY e.sequence"
            ).fetchall()
            for row in rows:
                self._link_event(
                    conn,
                    sequence=int(row["sequence"]),
                    event_id=row["event_id"],
                    stream_type=row["stream_type"],
                    stream_id=row["stream_id"],
                    event_type=row["event_type"],
                    payload_json=row["payload_json"],
                    occurred_at=row["occurred_at"],
                )

    def verify_event_chain(self) -> dict[str, Any]:
        """Recompute the audit event hash chain from GENESIS.

        Returns ``{"ok", "events", "first_bad_id", "error", "checkpoints"}``.
        ``first_bad_id`` is the event_id of the first row whose recomputed
        link diverges from the stored chain -- including a payload edited
        after ``DROP TRIGGER`` removed the append-only guard.  Chain
        verification detects tampering; it cannot prevent an operator with
        database privileges from regenerating the chain.  HMAC checkpoints
        (admin key) plus off-host export via ``export_jsonl`` cover that case.
        """

        with self.connection() as conn:
            events = conn.execute("SELECT * FROM events ORDER BY sequence").fetchall()
            links = {
                int(row["sequence"]): row
                for row in conn.execute("SELECT * FROM event_chain").fetchall()
            }
            checkpoints = conn.execute(
                "SELECT * FROM event_checkpoints ORDER BY checkpoint_id"
            ).fetchall()

        ok = True
        first_bad_id: str | None = None
        error: str | None = None
        computed: dict[int, str] = {}
        prev_hash = EVENT_CHAIN_GENESIS
        for row in events:
            sequence = int(row["sequence"])
            link = links.pop(sequence, None)
            material = self._chain_material(
                sequence=sequence,
                event_id=row["event_id"],
                stream_type=row["stream_type"],
                stream_id=row["stream_id"],
                event_type=row["event_type"],
                payload_json=row["payload_json"],
                occurred_at=row["occurred_at"],
            )
            expected = self._chain_hash(prev_hash, material)
            computed[sequence] = expected
            if link is None:
                ok, first_bad_id = False, row["event_id"]
                error = f"event {row['event_id']} has no chain link"
                break
            if link["prev_hash"] != prev_hash or link["this_hash"] != expected:
                ok, first_bad_id = False, row["event_id"]
                error = (
                    f"stored chain link for event {row['event_id']} does not match "
                    "the recomputed hash (event edited, reordered, or chain rewritten)"
                )
                break
            prev_hash = expected
        if ok and links:
            ok = False
            error = "event chain contains links for events that no longer exist"

        checkpoint_summary = {"total": len(checkpoints), "verified": 0, "failed": 0}
        for checkpoint in checkpoints:
            sequence = int(checkpoint["sequence"])
            expected_hash = computed.get(sequence)
            valid = expected_hash is not None and checkpoint["this_hash"] == expected_hash
            if valid and self._checkpoint_key is not None and checkpoint["hmac_tag"] is not None:
                expected_tag = self._checkpoint_tag(sequence, str(checkpoint["this_hash"]))
                valid = hmac.compare_digest(str(checkpoint["hmac_tag"]), expected_tag or "")
            if valid:
                checkpoint_summary["verified"] += 1
            else:
                checkpoint_summary["failed"] += 1
                if ok:
                    ok = False
                    error = f"checkpoint {checkpoint['checkpoint_id']} does not match the recomputed chain"

        return {
            "ok": ok,
            "events": len(events),
            "first_bad_id": first_bad_id,
            "error": error,
            "checkpoints": checkpoint_summary,
        }

    def verify_sentinel_records(self) -> dict[str, Any]:
        """Reconcile the Sentinel record tables against the tamper-evident chain.

        Sentinel's own tables (assessments, independent reviews, Principal
        reports, acknowledgements) carry ordinary ``BEFORE UPDATE``/``BEFORE
        DELETE`` guards, but a database owner can drop those triggers and edit
        a row in place.  To detect that, every Sentinel record hash is also
        recorded in LPOS's SHA-256 hash-chained event stream when the record is
        written (see ``save_sentinel_assessment`` / ``save_sentinel_review`` /
        ``save_sentinel_report``).  This method recomputes each stored record's
        content hash and reconciles it with (a) the record's own hash column and
        (b) the authoritative hash anchored in the chained event, so an edited
        ``*_json`` payload is DETECTED even after the append-only triggers are
        dropped.  Editing the anchoring event instead breaks
        ``verify_event_chain``.  Returns ``{"ok", "checked", "error",
        "first_bad"}``.
        """

        from .sentinel.models import (
            PrincipalSecurityReport,
            SecurityAssessment,
            SecurityAssessmentReview,
        )

        checked = 0
        with self.connection() as conn:
            # Authoritative hashes/decisions from the hash-chained event stream.
            assessment_events: dict[str, str] = {}
            report_events: dict[str, str] = {}
            review_events: dict[str, dict[str, Any]] = {}
            for row in conn.execute(
                "SELECT stream_id, event_type, payload_json FROM events "
                "WHERE stream_type LIKE 'sentinel_%'"
            ).fetchall():
                payload = json.loads(row["payload_json"])
                if row["event_type"] == "sentinel.assessment.recorded_untrusted":
                    assessment_events[row["stream_id"]] = payload.get("assessment_hash")
                elif row["event_type"] == "sentinel.report.staged_for_principal":
                    report_events[row["stream_id"]] = payload.get("report_hash")
                elif row["event_type"] == "sentinel.assessment.reviewed":
                    review_events[payload.get("assessment_id")] = payload

            assessment_rows = conn.execute(
                "SELECT assessment_id, assessment_hash, assessment_json FROM sentinel_assessments"
            ).fetchall()
            review_rows = conn.execute(
                "SELECT review_id, assessment_id, review_hash, trusted, decision, review_json "
                "FROM sentinel_assessment_reviews"
            ).fetchall()
            report_rows = conn.execute(
                "SELECT report_id, report_hash, report_json FROM sentinel_reports"
            ).fetchall()

        def fail(detail: str, bad: str) -> dict[str, Any]:
            return {"ok": False, "checked": checked, "error": detail, "first_bad": bad}

        for row in assessment_rows:
            checked += 1
            try:
                recomputed = SecurityAssessment.from_dict(
                    json.loads(row["assessment_json"])
                ).assessment_hash
            except Exception as exc:  # pragma: no cover - defensive
                return fail(f"assessment {row['assessment_id']} could not be parsed: {exc}", row["assessment_id"])
            if recomputed != row["assessment_hash"]:
                return fail(
                    f"assessment {row['assessment_id']} content does not match its stored hash",
                    row["assessment_id"],
                )
            anchored = assessment_events.get(row["assessment_id"])
            if anchored is None:
                return fail(
                    f"assessment {row['assessment_id']} has no anchoring chained event",
                    row["assessment_id"],
                )
            if anchored != recomputed:
                return fail(
                    f"assessment {row['assessment_id']} content diverges from the hash-chained event",
                    row["assessment_id"],
                )

        for row in review_rows:
            checked += 1
            try:
                recomputed = SecurityAssessmentReview.from_dict(
                    json.loads(row["review_json"])
                ).review_hash
            except Exception as exc:  # pragma: no cover - defensive
                return fail(f"review {row['review_id']} could not be parsed: {exc}", row["review_id"])
            if recomputed != row["review_hash"]:
                return fail(
                    f"review {row['review_id']} content does not match its stored hash",
                    row["review_id"],
                )
            anchored = review_events.get(row["assessment_id"])
            if anchored is None:
                return fail(
                    f"review {row['review_id']} has no anchoring chained event",
                    row["review_id"],
                )
            # The trust decision is the security-critical field: it must match the
            # tamper-evident chained event, so flipping ``trusted`` 0->1 is detected.
            if bool(anchored.get("trusted")) != bool(row["trusted"]) or str(
                anchored.get("decision")
            ) != str(row["decision"]):
                return fail(
                    f"review {row['review_id']} trust decision diverges from the hash-chained event",
                    row["review_id"],
                )

        for row in report_rows:
            checked += 1
            try:
                recomputed = PrincipalSecurityReport.from_dict(
                    json.loads(row["report_json"])
                ).report_hash
            except Exception as exc:  # pragma: no cover - defensive
                return fail(f"report {row['report_id']} could not be parsed: {exc}", row["report_id"])
            if recomputed != row["report_hash"]:
                return fail(
                    f"report {row['report_id']} content does not match its stored hash",
                    row["report_id"],
                )
            anchored = report_events.get(row["report_id"])
            if anchored is None:
                return fail(
                    f"report {row['report_id']} has no anchoring chained event",
                    row["report_id"],
                )
            if anchored != recomputed:
                return fail(
                    f"report {row['report_id']} content diverges from the hash-chained event",
                    row["report_id"],
                )

        return {"ok": True, "checked": checked, "error": None, "first_bad": None}

    def append_system_event(
        self,
        *,
        stream_type: str,
        stream_id: str,
        event_type: str,
        payload: Mapping[str, Any],
    ) -> str:
        """Append a standalone audit event in its own transaction."""

        with self.transaction() as conn:
            return self._append_event(
                conn,
                stream_type=stream_type,
                stream_id=stream_id,
                event_type=event_type,
                payload=payload,
            )

    def _append_event(
        self,
        conn: sqlite3.Connection,
        *,
        stream_type: str,
        stream_id: str,
        event_type: str,
        payload: Mapping[str, Any],
    ) -> str:
        event_id = new_id("EVT")
        payload_json = canonical_json(payload)
        occurred_at = utc_now()
        cursor = conn.execute(
            "INSERT INTO events(event_id, stream_type, stream_id, event_type, payload_json, occurred_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (event_id, stream_type, stream_id, event_type, payload_json, occurred_at),
        )
        self._link_event(
            conn,
            sequence=int(cursor.lastrowid),
            event_id=event_id,
            stream_type=stream_type,
            stream_id=stream_id,
            event_type=event_type,
            payload_json=payload_json,
            occurred_at=occurred_at,
        )
        return event_id

    def create_task(self, envelope: TaskEnvelope) -> None:
        now = utc_now()
        with self.transaction() as conn:
            try:
                conn.execute(
                    "INSERT INTO tasks(task_id, envelope_json, status, version, created_at, updated_at) "
                    "VALUES (?, ?, ?, 0, ?, ?)",
                    (
                        envelope.task_id,
                        canonical_json(envelope),
                        TaskStatus.RECEIVED.value,
                        now,
                        now,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise ConcurrencyError(f"task already exists: {envelope.task_id}") from exc
            self._append_event(
                conn,
                stream_type="task",
                stream_id=envelope.task_id,
                event_type="task.created",
                payload={"envelope": envelope.to_dict(), "status": TaskStatus.RECEIVED.value},
            )

    def get_task(self, task_id: str) -> dict[str, Any]:
        with self.connection() as conn:
            row = conn.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,)).fetchone()
        if row is None:
            raise NotFoundError(f"task not found: {task_id}")
        return {
            "envelope": TaskEnvelope.from_dict(json.loads(row["envelope_json"])),
            "status": TaskStatus(row["status"]),
            "version": int(row["version"]),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def save_context_bundle(self, bundle: ContextBundle) -> None:
        with self.transaction() as conn:
            self._require_task(conn, bundle.task_id)
            try:
                conn.execute(
                    "INSERT INTO context_bundles(bundle_id, task_id, purpose, bundle_hash, bundle_json, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        bundle.bundle_id,
                        bundle.task_id,
                        bundle.purpose,
                        bundle.bundle_hash,
                        canonical_json(bundle),
                        bundle.created_at,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                existing = conn.execute(
                    "SELECT bundle_hash, bundle_json FROM context_bundles WHERE bundle_id = ?",
                    (bundle.bundle_id,),
                ).fetchone()
                if (
                    existing is None
                    or existing["bundle_hash"] != bundle.bundle_hash
                    or json.loads(existing["bundle_json"]) != bundle.to_dict()
                ):
                    raise ConcurrencyError(f"context bundle identity collision: {bundle.bundle_id}") from exc
                return
            self._append_event(
                conn,
                stream_type="context",
                stream_id=bundle.bundle_id,
                event_type="context.compiled",
                payload={
                    "task_id": bundle.task_id,
                    "purpose": bundle.purpose,
                    "bundle_hash": bundle.bundle_hash,
                    "loaded_components": bundle.loaded_components,
                    "missing_components": bundle.missing_components,
                    "excluded": bundle.excluded,
                },
            )

    def get_context_bundle(self, bundle_id: str) -> ContextBundle | None:
        with self.connection() as conn:
            row = conn.execute(
                "SELECT bundle_json FROM context_bundles WHERE bundle_id = ?",
                (bundle_id,),
            ).fetchone()
        return None if row is None else ContextBundle.from_dict(json.loads(row["bundle_json"]))

    def transition_task(
        self,
        task_id: str,
        target: TaskStatus,
        *,
        expected_version: int | None = None,
        reason: str | None = None,
    ) -> int:
        with self.transaction() as conn:
            row = conn.execute(
                "SELECT status, version FROM tasks WHERE task_id = ?",
                (task_id,),
            ).fetchone()
            if row is None:
                raise NotFoundError(f"task not found: {task_id}")
            current = TaskStatus(row["status"])
            version = int(row["version"])
            if expected_version is not None and expected_version != version:
                raise ConcurrencyError(
                    f"task {task_id} version changed: expected {expected_version}, found {version}"
                )
            TaskStateMachine.assert_transition(current, target)
            now = utc_now()
            cursor = conn.execute(
                "UPDATE tasks SET status = ?, version = version + 1, updated_at = ? "
                "WHERE task_id = ? AND version = ?",
                (target.value, now, task_id, version),
            )
            if cursor.rowcount != 1:
                raise ConcurrencyError(f"task {task_id} changed concurrently")
            self._append_event(
                conn,
                stream_type="task",
                stream_id=task_id,
                event_type="task.transitioned",
                payload={
                    "from": current.value,
                    "to": target.value,
                    "reason": reason,
                    "version": version + 1,
                },
            )
            return version + 1

    def save_interpretation(self, contract: InterpretationContract) -> int:
        contract_json = canonical_json(contract)
        contract_hash = digest(contract)
        now = utc_now()
        with self.transaction() as conn:
            self._require_task(conn, contract.task_id)
            existing = conn.execute(
                "SELECT version FROM interpretations WHERE task_id = ?", (contract.task_id,)
            ).fetchone()
            if existing:
                version = int(existing["version"]) + 1
                conn.execute(
                    "UPDATE interpretations SET contract_json = ?, contract_hash = ?, version = ?, updated_at = ? "
                    "WHERE task_id = ?",
                    (contract_json, contract_hash, version, now, contract.task_id),
                )
            else:
                version = 1
                conn.execute(
                    "INSERT INTO interpretations(task_id, contract_json, contract_hash, version, updated_at) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (contract.task_id, contract_json, contract_hash, version, now),
                )
            self._append_event(
                conn,
                stream_type="task",
                stream_id=contract.task_id,
                event_type="interpretation.recorded",
                payload={"contract": contract.to_dict(), "contract_hash": contract_hash, "version": version},
            )
            return version

    def get_interpretation(self, task_id: str) -> InterpretationContract | None:
        with self.connection() as conn:
            row = conn.execute(
                "SELECT contract_json FROM interpretations WHERE task_id = ?", (task_id,)
            ).fetchone()
        return None if row is None else InterpretationContract.from_dict(json.loads(row["contract_json"]))

    def save_artifact_spec(self, task_id: str, spec: ArtifactSpecification) -> int:
        spec_json = canonical_json(spec)
        spec_hash = digest(spec)
        now = utc_now()
        with self.transaction() as conn:
            self._require_task(conn, task_id)
            existing = conn.execute(
                "SELECT task_id, version FROM artifact_specs WHERE artifact_id = ?", (spec.artifact_id,)
            ).fetchone()
            if existing:
                if existing["task_id"] != task_id:
                    raise ConcurrencyError(
                        f"artifact specification {spec.artifact_id} is already bound to another task"
                    )
                version = int(existing["version"]) + 1
                conn.execute(
                    "UPDATE artifact_specs SET task_id = ?, spec_json = ?, spec_hash = ?, version = ?, updated_at = ? "
                    "WHERE artifact_id = ?",
                    (task_id, spec_json, spec_hash, version, now, spec.artifact_id),
                )
            else:
                version = 1
                conn.execute(
                    "INSERT INTO artifact_specs(artifact_id, task_id, spec_json, spec_hash, version, updated_at) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (spec.artifact_id, task_id, spec_json, spec_hash, version, now),
                )
            self._append_event(
                conn,
                stream_type="artifact_spec",
                stream_id=spec.artifact_id,
                event_type="artifact_spec.recorded",
                payload={"task_id": task_id, "spec": spec.to_dict(), "spec_hash": spec_hash, "version": version},
            )
            return version

    def get_artifact_spec(self, artifact_id: str) -> ArtifactSpecification | None:
        with self.connection() as conn:
            row = conn.execute(
                "SELECT spec_json FROM artifact_specs WHERE artifact_id = ?", (artifact_id,)
            ).fetchone()
        return None if row is None else ArtifactSpecification.from_dict(json.loads(row["spec_json"]))

    def get_latest_artifact_spec_for_task(self, task_id: str) -> ArtifactSpecification | None:
        with self.connection() as conn:
            row = conn.execute(
                "SELECT spec_json FROM artifact_specs WHERE task_id = ? ORDER BY rowid DESC LIMIT 1",
                (task_id,),
            ).fetchone()
        return None if row is None else ArtifactSpecification.from_dict(json.loads(row["spec_json"]))

    def save_artifact(self, artifact: Artifact) -> None:
        with self.transaction() as conn:
            self._require_task(conn, artifact.task_id)
            existing_owner = conn.execute(
                "SELECT task_id FROM artifacts WHERE artifact_id = ? LIMIT 1",
                (artifact.artifact_id,),
            ).fetchone()
            if existing_owner is not None and existing_owner["task_id"] != artifact.task_id:
                raise ConcurrencyError(
                    f"artifact {artifact.artifact_id} is already bound to another task"
                )
            spec_owner = conn.execute(
                "SELECT task_id FROM artifact_specs WHERE artifact_id = ?",
                (artifact.artifact_id,),
            ).fetchone()
            if spec_owner is not None and spec_owner["task_id"] != artifact.task_id:
                raise ConcurrencyError(
                    f"artifact {artifact.artifact_id} conflicts with another task's specification"
                )
            try:
                conn.execute(
                    "INSERT INTO artifacts(artifact_id, artifact_hash, task_id, artifact_json, created_at) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (
                        artifact.artifact_id,
                        artifact.content_hash,
                        artifact.task_id,
                        canonical_json(artifact),
                        artifact.created_at,
                    ),
                )
            except sqlite3.IntegrityError:
                existing = conn.execute(
                    "SELECT artifact_json FROM artifacts WHERE artifact_id = ? AND artifact_hash = ?",
                    (artifact.artifact_id, artifact.content_hash),
                ).fetchone()
                if existing is None or json.loads(existing["artifact_json"]) != artifact.to_dict():
                    raise ConcurrencyError("artifact identity collision")
                return
            self._append_event(
                conn,
                stream_type="artifact",
                stream_id=artifact.artifact_id,
                event_type="artifact.created",
                payload={"artifact": artifact.to_dict()},
            )

    def get_latest_artifact(self, task_id: str) -> Artifact | None:
        with self.connection() as conn:
            row = conn.execute(
                "SELECT artifact_json FROM artifacts WHERE task_id = ? ORDER BY rowid DESC LIMIT 1",
                (task_id,),
            ).fetchone()
        return None if row is None else Artifact.from_dict(json.loads(row["artifact_json"]))

    def save_review(
        self,
        *,
        review_id: str,
        task_id: str,
        artifact: Artifact,
        envelope: ReviewEnvelope,
        result: ReviewResult,
        context_isolated: bool,
        creator_adapter: str | None,
        reviewer_adapter: str,
        review_context_id: str,
    ) -> None:
        with self.transaction() as conn:
            self._require_task(conn, task_id)
            if artifact.task_id != task_id:
                raise ValidationError("review artifact belongs to a different task")
            persisted_artifact = conn.execute(
                "SELECT 1 FROM artifacts WHERE artifact_id = ? AND artifact_hash = ? AND task_id = ?",
                (artifact.artifact_id, artifact.content_hash, task_id),
            ).fetchone()
            if persisted_artifact is None:
                raise ValidationError("review requires the persisted artifact revision")
            supplied_artifact = envelope.artifact
            if (
                supplied_artifact.get("artifact_id") != artifact.artifact_id
                or supplied_artifact.get("task_id") != task_id
                or supplied_artifact.get("content_hash") != artifact.content_hash
            ):
                raise ValidationError("ReviewEnvelope does not bind to the reviewed artifact")
            context = conn.execute(
                "SELECT task_id, purpose FROM context_bundles WHERE bundle_id = ?",
                (review_context_id,),
            ).fetchone()
            if context is None or context["task_id"] != task_id or context["purpose"] != "review":
                raise ValidationError("review_context_id is not a persisted review context for this task")
            conn.execute(
                "INSERT INTO reviews(review_id, task_id, artifact_id, artifact_hash, envelope_hash, envelope_json, "
                "result_json, decision, context_isolated, creator_adapter, reviewer_adapter, review_context_id, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    review_id,
                    task_id,
                    artifact.artifact_id,
                    artifact.content_hash,
                    envelope.envelope_hash,
                    canonical_json(envelope),
                    canonical_json(result),
                    result.decision.value,
                    1 if context_isolated else 0,
                    creator_adapter,
                    reviewer_adapter,
                    review_context_id,
                    utc_now(),
                ),
            )
            self._append_event(
                conn,
                stream_type="review",
                stream_id=review_id,
                event_type="review.completed",
                payload={
                    "task_id": task_id,
                    "artifact_hash": artifact.content_hash,
                    "envelope_hash": envelope.envelope_hash,
                    "result": result.to_dict(),
                    "context_isolated": context_isolated,
                    "creator_adapter": creator_adapter,
                    "reviewer_adapter": reviewer_adapter,
                    "review_context_id": review_context_id,
                },
            )

    def get_latest_review(self, task_id: str, artifact_hash: str) -> dict[str, Any] | None:
        with self.connection() as conn:
            row = conn.execute(
                "SELECT * FROM reviews WHERE task_id = ? AND artifact_hash = ? ORDER BY rowid DESC LIMIT 1",
                (task_id, artifact_hash),
            ).fetchone()
        if row is None:
            return None
        return {
            "review_id": row["review_id"],
            "envelope": ReviewEnvelope.from_dict(json.loads(row["envelope_json"])),
            "result": ReviewResult.from_dict(json.loads(row["result_json"])),
            "context_isolated": bool(row["context_isolated"]),
            "creator_adapter": row["creator_adapter"],
            "reviewer_adapter": row["reviewer_adapter"],
            "review_context_id": row["review_context_id"],
        }

    def create_action(self, plan: ActionPlan) -> ActionPlan:
        now = utc_now()
        status = ActionStatus.AWAITING_APPROVAL if plan.approval_required else ActionStatus.PLANNED
        with self.transaction() as conn:
            self._require_task(conn, plan.task_id)
            existing = conn.execute(
                "SELECT plan_json, action_hash FROM actions WHERE idempotency_key = ?",
                (plan.idempotency_key,),
            ).fetchone()
            if existing:
                if existing["action_hash"] != plan.action_hash:
                    raise ConcurrencyError(
                        "idempotency key already binds to a different exact action"
                    )
                return ActionPlan.from_dict(json.loads(existing["plan_json"]))
            conn.execute(
                "INSERT INTO actions(action_id, task_id, idempotency_key, action_hash, plan_json, status, "
                "created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    plan.action_id,
                    plan.task_id,
                    plan.idempotency_key,
                    plan.action_hash,
                    canonical_json(plan),
                    status.value,
                    now,
                    now,
                ),
            )
            self._append_event(
                conn,
                stream_type="action",
                stream_id=plan.action_id,
                event_type="action.planned",
                payload={"plan": plan.to_dict(), "status": status.value},
            )
            return plan

    def get_action(self, action_id: str) -> dict[str, Any]:
        with self.connection() as conn:
            row = conn.execute("SELECT * FROM actions WHERE action_id = ?", (action_id,)).fetchone()
        if row is None:
            raise NotFoundError(f"action not found: {action_id}")
        return {
            "plan": ActionPlan.from_dict(json.loads(row["plan_json"])),
            "status": ActionStatus(row["status"]),
            "result": ActionResult.from_dict(json.loads(row["result_json"])) if row["result_json"] else None,
            "version": int(row["version"]),
        }

    def get_action_by_idempotency_key(self, idempotency_key: str) -> dict[str, Any] | None:
        with self.connection() as conn:
            row = conn.execute(
                "SELECT * FROM actions WHERE idempotency_key = ?",
                (idempotency_key,),
            ).fetchone()
        if row is None:
            return None
        return {
            "plan": ActionPlan.from_dict(json.loads(row["plan_json"])),
            "status": ActionStatus(row["status"]),
            "result": (
                ActionResult.from_dict(json.loads(row["result_json"]))
                if row["result_json"]
                else None
            ),
            "version": int(row["version"]),
        }

    def list_actions(self, task_id: str) -> list[dict[str, Any]]:
        with self.connection() as conn:
            rows = conn.execute(
                "SELECT * FROM actions WHERE task_id = ? ORDER BY rowid", (task_id,)
            ).fetchall()
        return [
            {
                "plan": ActionPlan.from_dict(json.loads(row["plan_json"])),
                "status": ActionStatus(row["status"]),
                "result": ActionResult.from_dict(json.loads(row["result_json"])) if row["result_json"] else None,
                "version": int(row["version"]),
            }
            for row in rows
        ]

    def claim_action_execution(
        self,
        action_id: str,
        *,
        expected_version: int,
        grant_id: str | None = None,
    ) -> int:
        """Atomically consume an approval grant and claim an action for execution.

        Only one worker can move a given exact action into ``executing``.  For
        approved actions, grant consumption and the state transition share the
        same SQLite transaction, eliminating the partial state where an approval
        is consumed but the action was never claimed.
        """

        with self.transaction() as conn:
            row = conn.execute(
                "SELECT status, version, action_hash FROM actions WHERE action_id = ?",
                (action_id,),
            ).fetchone()
            if row is None:
                raise NotFoundError(f"action not found: {action_id}")
            version = int(row["version"])
            if version != expected_version:
                raise ConcurrencyError(
                    f"action {action_id} version changed: expected {expected_version}, found {version}"
                )
            current = ActionStatus(row["status"])
            ActionStateMachine.assert_transition(current, ActionStatus.EXECUTING)

            consumed_payload: dict[str, Any] | None = None
            if current is ActionStatus.APPROVED:
                if not grant_id:
                    raise ValidationError("approved action execution requires its approval grant")
                grant = conn.execute(
                    "SELECT action_id, action_hash, consumed_at FROM approval_grants "
                    "WHERE grant_id = ?",
                    (grant_id,),
                ).fetchone()
                if grant is None:
                    raise NotFoundError(f"approval grant not found: {grant_id}")
                if grant["action_id"] != action_id or grant["action_hash"] != row["action_hash"]:
                    raise ValidationError("grant is bound to a different exact action")
                if grant["consumed_at"] is None:
                    consumed_at = utc_now()
                    cursor = conn.execute(
                        "UPDATE approval_grants SET consumed_at = ? "
                        "WHERE grant_id = ? AND consumed_at IS NULL",
                        (consumed_at, grant_id),
                    )
                    if cursor.rowcount != 1:
                        raise ConcurrencyError(f"approval grant {grant_id} was consumed concurrently")
                    consumed_payload = {
                        "action_id": action_id,
                        "consumed_at": consumed_at,
                    }
            elif grant_id is not None:
                raise ValidationError("unapproved action cannot consume an approval grant")

            cursor = conn.execute(
                "UPDATE actions SET status = ?, version = version + 1, updated_at = ? "
                "WHERE action_id = ? AND version = ?",
                (ActionStatus.EXECUTING.value, utc_now(), action_id, version),
            )
            if cursor.rowcount != 1:
                raise ConcurrencyError(f"action {action_id} changed concurrently")
            if consumed_payload is not None:
                self._append_event(
                    conn,
                    stream_type="approval",
                    stream_id=grant_id,
                    event_type="approval.consumed",
                    payload=consumed_payload,
                )
            self._append_event(
                conn,
                stream_type="action",
                stream_id=action_id,
                event_type="action.status_changed",
                payload={
                    "from": current.value,
                    "to": ActionStatus.EXECUTING.value,
                    "result": None,
                    "version": version + 1,
                },
            )
            return version + 1

    def update_action(
        self,
        action_id: str,
        status: ActionStatus,
        *,
        result: ActionResult | None = None,
        expected_version: int | None = None,
    ) -> int:
        with self.transaction() as conn:
            row = conn.execute(
                "SELECT status, version FROM actions WHERE action_id = ?", (action_id,)
            ).fetchone()
            if row is None:
                raise NotFoundError(f"action not found: {action_id}")
            version = int(row["version"])
            if expected_version is not None and version != expected_version:
                raise ConcurrencyError(
                    f"action {action_id} version changed: expected {expected_version}, found {version}"
                )
            ActionStateMachine.assert_transition(ActionStatus(row["status"]), status)
            cursor = conn.execute(
                "UPDATE actions SET status = ?, result_json = COALESCE(?, result_json), "
                "version = version + 1, updated_at = ? WHERE action_id = ? AND version = ?",
                (
                    status.value,
                    canonical_json(result) if result is not None else None,
                    utc_now(),
                    action_id,
                    version,
                ),
            )
            if cursor.rowcount != 1:
                raise ConcurrencyError(f"action {action_id} changed concurrently")
            self._append_event(
                conn,
                stream_type="action",
                stream_id=action_id,
                event_type="action.status_changed",
                payload={
                    "from": row["status"],
                    "to": status.value,
                    "result": result.to_dict() if result else None,
                    "version": version + 1,
                },
            )
            return version + 1

    def save_approval_request(self, request: ApprovalRequest) -> ApprovalRequest:
        with self.transaction() as conn:
            action = conn.execute(
                "SELECT action_hash FROM actions WHERE action_id = ?", (request.action_id,)
            ).fetchone()
            if action is None:
                raise NotFoundError(f"action not found: {request.action_id}")
            if action["action_hash"] != request.action_hash:
                raise ValidationError("approval request does not bind to stored action")
            try:
                conn.execute(
                    "INSERT INTO approval_requests(question_id, task_id, action_id, action_hash, request_json, "
                    "status, created_at) VALUES (?, ?, ?, ?, ?, 'open', ?)",
                    (
                        request.question_id,
                        request.task_id,
                        request.action_id,
                        request.action_hash,
                        canonical_json(request),
                        request.created_at,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                existing = conn.execute(
                    "SELECT request_json, action_hash FROM approval_requests WHERE action_id = ?",
                    (request.action_id,),
                ).fetchone()
                if existing is None or existing["action_hash"] != request.action_hash:
                    raise ConcurrencyError(
                        "approval request identity collision for exact action"
                    ) from exc
                return ApprovalRequest.from_dict(json.loads(existing["request_json"]))
            self._append_event(
                conn,
                stream_type="approval",
                stream_id=request.question_id,
                event_type="approval.requested",
                payload={"request": request.to_dict()},
            )
            return request

    def get_approval_request(self, question_id: str) -> ApprovalRequest:
        with self.connection() as conn:
            row = conn.execute(
                "SELECT request_json FROM approval_requests WHERE question_id = ?", (question_id,)
            ).fetchone()
        if row is None:
            raise NotFoundError(f"approval request not found: {question_id}")
        return ApprovalRequest.from_dict(json.loads(row["request_json"]))

    def get_approval_request_for_action(self, action_id: str) -> ApprovalRequest | None:
        """Return the canonical request for an action, including a closed one.

        An exact action has at most one approval question in LPOS v4.
        Repeated plan calls therefore return the existing question rather than
        generating duplicate Principal prompts.
        """
        with self.connection() as conn:
            row = conn.execute(
                "SELECT request_json FROM approval_requests WHERE action_id = ? "
                "ORDER BY rowid LIMIT 1",
                (action_id,),
            ).fetchone()
        return None if row is None else ApprovalRequest.from_dict(json.loads(row["request_json"]))

    def save_approval_grant(self, grant: ApprovalGrant) -> None:
        with self.transaction() as conn:
            request = conn.execute(
                "SELECT status, task_id, action_id, action_hash FROM approval_requests WHERE question_id = ?",
                (grant.question_id,),
            ).fetchone()
            if request is None:
                raise NotFoundError(f"approval request not found: {grant.question_id}")
            if request["status"] != "open":
                raise ReplayDetected(f"approval request already closed: {grant.question_id}")
            action_state = conn.execute(
                "SELECT status, version FROM actions WHERE action_id = ?", (grant.action_id,)
            ).fetchone()
            if action_state is None:
                raise NotFoundError(f"action not found: {grant.action_id}")
            ActionStateMachine.assert_transition(
                ActionStatus(action_state["status"]), ActionStatus.APPROVED
            )
            if (
                request["task_id"] != grant.task_id
                or request["action_id"] != grant.action_id
                or request["action_hash"] != grant.action_hash
            ):
                raise ValidationError("grant does not bind to its request")
            try:
                conn.execute(
                    "INSERT INTO approval_grants(grant_id, question_id, task_id, action_id, action_hash, "
                    "message_key, grant_json, granted_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        grant.grant_id,
                        grant.question_id,
                        grant.task_id,
                        grant.action_id,
                        grant.action_hash,
                        grant.message_identity.replay_key,
                        canonical_json(grant),
                        grant.granted_at,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise ReplayDetected("approval message, request, or action has already been used") from exc
            conn.execute(
                "UPDATE approval_requests SET status = 'granted', closed_at = ? WHERE question_id = ?",
                (grant.granted_at, grant.question_id),
            )
            conn.execute(
                "UPDATE actions SET status = ?, version = version + 1, updated_at = ? WHERE action_id = ?",
                (ActionStatus.APPROVED.value, utc_now(), grant.action_id),
            )
            self._append_event(
                conn,
                stream_type="action",
                stream_id=grant.action_id,
                event_type="action.status_changed",
                payload={
                    "from": action_state["status"],
                    "to": ActionStatus.APPROVED.value,
                    "result": None,
                    "version": int(action_state["version"]) + 1,
                },
            )
            self._append_event(
                conn,
                stream_type="approval",
                stream_id=grant.question_id,
                event_type="approval.granted",
                payload={"grant": grant.to_dict()},
            )

    def get_grant_for_action(self, action_id: str) -> ApprovalGrant | None:
        with self.connection() as conn:
            row = conn.execute(
                "SELECT grant_json FROM approval_grants WHERE action_id = ?", (action_id,)
            ).fetchone()
        return None if row is None else ApprovalGrant.from_dict(json.loads(row["grant_json"]))

    def mark_grant_consumed(self, grant_id: str, action_id: str) -> None:
        with self.transaction() as conn:
            row = conn.execute(
                "SELECT action_id, consumed_at FROM approval_grants WHERE grant_id = ?", (grant_id,)
            ).fetchone()
            if row is None:
                raise NotFoundError(f"approval grant not found: {grant_id}")
            if row["action_id"] != action_id:
                raise ValidationError("grant is bound to a different action")
            if row["consumed_at"] is None:
                now = utc_now()
                conn.execute(
                    "UPDATE approval_grants SET consumed_at = ? WHERE grant_id = ?", (now, grant_id)
                )
                self._append_event(
                    conn,
                    stream_type="approval",
                    stream_id=grant_id,
                    event_type="approval.consumed",
                    payload={"action_id": action_id, "consumed_at": now},
                )

    def _save_evidence_tx(
        self,
        conn: sqlite3.Connection,
        record: EvidenceRecord,
        *,
        task_id: str | None = None,
    ) -> None:
        if task_id:
            self._require_task(conn, task_id)
        conn.execute(
            "INSERT INTO evidence(evidence_id, task_id, record_json, created_at) VALUES (?, ?, ?, ?)",
            (record.id, task_id, canonical_json(record), utc_now()),
        )
        self._append_event(
            conn,
            stream_type="evidence",
            stream_id=record.id,
            event_type="evidence.recorded",
            payload={"task_id": task_id, "record": record.to_dict()},
        )

    def save_evidence(self, record: EvidenceRecord, *, task_id: str | None = None) -> None:
        with self.transaction() as conn:
            self._save_evidence_tx(conn, record, task_id=task_id)

    def list_evidence(self, task_id: str | None = None) -> list[EvidenceRecord]:
        query = "SELECT record_json FROM evidence"
        params: tuple[Any, ...] = ()
        if task_id is not None:
            query += " WHERE task_id = ?"
            params = (task_id,)
        query += " ORDER BY rowid"
        with self.connection() as conn:
            rows = conn.execute(query, params).fetchall()
        return [EvidenceRecord.from_dict(json.loads(row["record_json"])) for row in rows]

    def save_decision(self, record: DecisionRecord, *, task_id: str | None = None) -> None:
        with self.transaction() as conn:
            if task_id:
                self._require_task(conn, task_id)
            conn.execute(
                "INSERT INTO decisions(decision_id, task_id, record_json, created_at) VALUES (?, ?, ?, ?)",
                (record.id, task_id, canonical_json(record), utc_now()),
            )
            self._append_event(
                conn,
                stream_type="decision",
                stream_id=record.id,
                event_type="decision.recorded",
                payload={"task_id": task_id, "record": record.to_dict()},
            )

    def list_decisions(self, task_id: str | None = None) -> list[DecisionRecord]:
        query = "SELECT record_json FROM decisions"
        params: tuple[Any, ...] = ()
        if task_id is not None:
            query += " WHERE task_id = ?"
            params = (task_id,)
        query += " ORDER BY rowid"
        with self.connection() as conn:
            rows = conn.execute(query, params).fetchall()
        return [DecisionRecord.from_dict(json.loads(row["record_json"])) for row in rows]

    def claim_operation(
        self,
        *,
        so_id: str,
        run_id: str,
        idempotency_key: str,
        lease_seconds: int = 900,
    ) -> None:
        if lease_seconds < 1:
            raise ValidationError("Standing Operation lease_seconds must be positive")
        now = utc_now()
        with self.transaction() as conn:
            existing = conn.execute(
                "SELECT run_id, so_id, status, claimed_at FROM operation_claims "
                "WHERE idempotency_key = ?",
                (idempotency_key,),
            ).fetchone()
            if existing is not None:
                if existing["so_id"] != so_id:
                    raise ConcurrencyError(
                        f"Standing Operation key {idempotency_key!r} is bound to {existing['so_id']}"
                    )
                if existing["status"] == "completed":
                    return
                age = (parse_timestamp(now) - parse_timestamp(existing["claimed_at"])).total_seconds()
                if age < lease_seconds:
                    raise ConcurrencyError(
                        f"Standing Operation key {idempotency_key!r} is already claimed by "
                        f"{existing['run_id']}"
                    )
                prior_run = existing["run_id"]
                conn.execute(
                    "UPDATE operation_claims SET run_id = ?, status = 'running', claimed_at = ?, "
                    "finished_at = NULL WHERE idempotency_key = ?",
                    (run_id, now, idempotency_key),
                )
                self._append_event(
                    conn,
                    stream_type="standing_operation",
                    stream_id=so_id,
                    event_type="standing_operation.reclaimed",
                    payload={
                        "run_id": run_id,
                        "replaced_run_id": prior_run,
                        "idempotency_key": idempotency_key,
                        "lease_seconds": lease_seconds,
                    },
                )
                return
            conn.execute(
                "INSERT INTO operation_claims(idempotency_key, run_id, so_id, status, claimed_at) "
                "VALUES (?, ?, ?, 'running', ?)",
                (idempotency_key, run_id, so_id, now),
            )
            self._append_event(
                conn,
                stream_type="standing_operation",
                stream_id=so_id,
                event_type="standing_operation.claimed",
                payload={
                    "run_id": run_id,
                    "idempotency_key": idempotency_key,
                    "lease_seconds": lease_seconds,
                },
            )

    def save_operation_run(
        self,
        run: StandingOperationRun,
        *,
        evidence: EvidenceRecord | None = None,
    ) -> StandingOperationRun:
        with self.transaction() as conn:
            existing = conn.execute(
                "SELECT run_json FROM operation_runs WHERE idempotency_key = ?",
                (run.idempotency_key,),
            ).fetchone()
            if existing:
                return StandingOperationRun.from_dict(json.loads(existing["run_json"]))
            claim = conn.execute(
                "SELECT run_id, status FROM operation_claims WHERE idempotency_key = ?",
                (run.idempotency_key,),
            ).fetchone()
            if (
                claim is None
                or claim["run_id"] != run.run_id
                or claim["status"] != "running"
            ):
                raise ConcurrencyError("Standing Operation run does not own its active idempotency claim")
            if evidence is not None:
                if evidence.id != run.evidence_id:
                    raise ValidationError("Standing Operation evidence does not match run.evidence_id")
                self._save_evidence_tx(conn, evidence)
            elif conn.execute(
                "SELECT 1 FROM evidence WHERE evidence_id = ?", (run.evidence_id,)
            ).fetchone() is None:
                raise ValidationError("Standing Operation run requires its evidence record")
            conn.execute(
                "INSERT INTO operation_runs(run_id, so_id, idempotency_key, run_json, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (run.run_id, run.so_id, run.idempotency_key, canonical_json(run), utc_now()),
            )
            cursor = conn.execute(
                "UPDATE operation_claims SET status = 'completed', finished_at = ? "
                "WHERE idempotency_key = ? AND run_id = ? AND status = 'running'",
                (run.finished_at, run.idempotency_key, run.run_id),
            )
            if cursor.rowcount != 1:
                raise ConcurrencyError("Standing Operation claim changed before completion")
            self._append_event(
                conn,
                stream_type="standing_operation",
                stream_id=run.so_id,
                event_type="standing_operation.completed",
                payload={"run": run.to_dict()},
            )
            return run

    def get_operation_run_by_key(self, idempotency_key: str) -> StandingOperationRun | None:
        with self.connection() as conn:
            row = conn.execute(
                "SELECT run_json FROM operation_runs WHERE idempotency_key = ?",
                (idempotency_key,),
            ).fetchone()
        return None if row is None else StandingOperationRun.from_dict(json.loads(row["run_json"]))

    def finalize_task(
        self,
        report: CompletionReport,
        *,
        expected_version: int | None = None,
        completion_evidence: EvidenceRecord | None = None,
    ) -> int:
        with self.transaction() as conn:
            row = conn.execute(
                "SELECT status, version FROM tasks WHERE task_id = ?", (report.task_id,)
            ).fetchone()
            if row is None:
                raise NotFoundError(f"task not found: {report.task_id}")
            current = TaskStatus(row["status"])
            version = int(row["version"])
            if expected_version is not None and expected_version != version:
                raise ConcurrencyError(
                    f"task {report.task_id} version changed: expected {expected_version}, found {version}"
                )
            TaskStateMachine.assert_transition(current, TaskStatus.COMPLETED)
            if completion_evidence is not None:
                if completion_evidence.id not in report.evidence_ids:
                    raise ValidationError(
                        "completion report must reference its atomic completion evidence"
                    )
                self._save_evidence_tx(
                    conn, completion_evidence, task_id=report.task_id
                )
            try:
                conn.execute(
                    "INSERT INTO completion_reports(task_id, report_json, report_hash, created_at) "
                    "VALUES (?, ?, ?, ?)",
                    (report.task_id, canonical_json(report), digest(report), report.completed_at),
                )
            except sqlite3.IntegrityError as exc:
                raise ConcurrencyError(f"completion report already exists for {report.task_id}") from exc
            cursor = conn.execute(
                "UPDATE tasks SET status = ?, version = version + 1, updated_at = ? "
                "WHERE task_id = ? AND version = ?",
                (TaskStatus.COMPLETED.value, report.completed_at, report.task_id, version),
            )
            if cursor.rowcount != 1:
                raise ConcurrencyError(f"task {report.task_id} changed concurrently")
            self._append_event(
                conn,
                stream_type="task",
                stream_id=report.task_id,
                event_type="task.completed",
                payload={
                    "from": current.value,
                    "report": report.to_dict(),
                    "report_hash": digest(report),
                    "version": version + 1,
                },
            )
            return version + 1

    def save_completion_report(self, report: CompletionReport) -> None:
        # Retained for import tools; normal runtime completion should use finalize_task.
        with self.transaction() as conn:
            self._require_task(conn, report.task_id)
            try:
                conn.execute(
                    "INSERT INTO completion_reports(task_id, report_json, report_hash, created_at) "
                    "VALUES (?, ?, ?, ?)",
                    (report.task_id, canonical_json(report), digest(report), report.completed_at),
                )
            except sqlite3.IntegrityError as exc:
                raise ConcurrencyError(f"completion report already exists for {report.task_id}") from exc

    def get_completion_report(self, task_id: str) -> CompletionReport | None:
        with self.connection() as conn:
            row = conn.execute(
                "SELECT report_json FROM completion_reports WHERE task_id = ?", (task_id,)
            ).fetchone()
        return None if row is None else CompletionReport.from_dict(json.loads(row["report_json"]))

    def get_artifact_revision(self, task_id: str, artifact_hash: str) -> Artifact | None:
        """Return one exact immutable artifact revision by task and content hash."""
        with self.connection() as conn:
            row = conn.execute(
                "SELECT artifact_json FROM artifacts WHERE task_id = ? AND artifact_hash = ? "
                "ORDER BY rowid DESC LIMIT 1",
                (task_id, artifact_hash),
            ).fetchone()
        return None if row is None else Artifact.from_dict(json.loads(row["artifact_json"]))

    # ------------------------------------------------------------------ Sentinel

    def save_sentinel_assessment(self, assessment):
        """Persist raw Sentinel output as an immutable, explicitly untrusted record."""
        from .sentinel.models import SecurityAssessment

        if not isinstance(assessment, SecurityAssessment):
            raise ValidationError("assessment must be a SecurityAssessment")
        with self.transaction() as conn:
            self._require_task(conn, assessment.task_id)
            if assessment.artifact_id is not None and assessment.artifact_hash is not None:
                artifact = conn.execute(
                    "SELECT 1 FROM artifacts WHERE task_id = ? AND artifact_id = ? AND artifact_hash = ?",
                    (assessment.task_id, assessment.artifact_id, assessment.artifact_hash),
                ).fetchone()
                if artifact is None:
                    raise ValidationError("Sentinel assessment must bind to a persisted artifact revision")
            try:
                conn.execute(
                    "INSERT INTO sentinel_assessments(assessment_id, task_id, artifact_id, artifact_hash, "
                    "assessment_hash, policy_version, trigger_name, status, assessment_json, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        assessment.assessment_id,
                        assessment.task_id,
                        assessment.artifact_id,
                        assessment.artifact_hash,
                        assessment.assessment_hash,
                        assessment.policy_version,
                        assessment.trigger,
                        assessment.status,
                        canonical_json(assessment),
                        assessment.completed_at,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                row = conn.execute(
                    "SELECT assessment_json, assessment_hash FROM sentinel_assessments "
                    "WHERE task_id = ? AND artifact_hash IS ? AND policy_version = ? AND trigger_name = ?",
                    (
                        assessment.task_id,
                        assessment.artifact_hash,
                        assessment.policy_version,
                        assessment.trigger,
                    ),
                ).fetchone()
                if row is not None:
                    existing = SecurityAssessment.from_dict(json.loads(row["assessment_json"]))
                    if existing.assessment_hash == assessment.assessment_hash:
                        return existing
                raise ConcurrencyError("Sentinel assessment identity or idempotency collision") from exc
            self._append_event(
                conn,
                stream_type="sentinel_assessment",
                stream_id=assessment.assessment_id,
                event_type="sentinel.assessment.recorded_untrusted",
                payload={
                    "task_id": assessment.task_id,
                    "artifact_hash": assessment.artifact_hash,
                    "assessment_hash": assessment.assessment_hash,
                    "trust_state": "untrusted",
                    "status": assessment.status,
                    "finding_count": len(assessment.findings),
                },
            )
        return assessment

    def get_sentinel_assessment(self, assessment_id: str):
        from .sentinel.models import SecurityAssessment

        with self.connection() as conn:
            row = conn.execute(
                "SELECT assessment_json FROM sentinel_assessments WHERE assessment_id = ?",
                (assessment_id,),
            ).fetchone()
        if row is None:
            raise NotFoundError(f"Sentinel assessment not found: {assessment_id}")
        return SecurityAssessment.from_dict(json.loads(row["assessment_json"]))

    def get_latest_sentinel_assessment(self, task_id: str, artifact_hash: str):
        from .sentinel.models import SecurityAssessment

        with self.connection() as conn:
            row = conn.execute(
                "SELECT assessment_json FROM sentinel_assessments "
                "WHERE task_id = ? AND artifact_hash = ? ORDER BY rowid DESC LIMIT 1",
                (task_id, artifact_hash),
            ).fetchone()
        return None if row is None else SecurityAssessment.from_dict(json.loads(row["assessment_json"]))

    def list_artifacts_without_sentinel_assessment(self, *, policy_version: str):
        with self.connection() as conn:
            rows = conn.execute(
                "SELECT a.artifact_json FROM artifacts a "
                "LEFT JOIN sentinel_assessments s ON s.task_id = a.task_id "
                "AND s.artifact_hash = a.artifact_hash AND s.policy_version = ? "
                "WHERE s.assessment_id IS NULL ORDER BY a.rowid",
                (policy_version,),
            ).fetchall()
        return tuple(Artifact.from_dict(json.loads(row["artifact_json"])) for row in rows)

    def save_sentinel_review(self, review):
        from .sentinel.models import SecurityAssessmentReview

        if not isinstance(review, SecurityAssessmentReview):
            raise ValidationError("review must be a SecurityAssessmentReview")
        with self.transaction() as conn:
            assessment = conn.execute(
                "SELECT task_id, artifact_hash, assessment_hash, assessment_json "
                "FROM sentinel_assessments WHERE assessment_id = ?",
                (review.assessment_id,),
            ).fetchone()
            if assessment is None:
                raise ValidationError("Sentinel review requires a persisted assessment")
            if (
                assessment["task_id"] != review.task_id
                or assessment["artifact_hash"] != review.artifact_hash
                or assessment["assessment_hash"] != review.assessment_hash
            ):
                raise ValidationError("Sentinel review does not bind the persisted assessment")
            serialized_assessment = canonical_json(json.loads(assessment["assessment_json"]))
            if (
                str(review.envelope.artifact.get("content", "")) != serialized_assessment
                or text_digest(serialized_assessment) != review.assessment_hash
            ):
                raise ValidationError("Sentinel review envelope does not contain the exact persisted assessment")
            context = conn.execute(
                "SELECT task_id, purpose, bundle_json FROM context_bundles WHERE bundle_id = ?",
                (review.review_context_id,),
            ).fetchone()
            if context is None or context["task_id"] != review.task_id or context["purpose"] != "review":
                raise ValidationError("Sentinel review context is not a fresh persisted review context")
            context_bundle = ContextBundle.from_dict(json.loads(context["bundle_json"]))
            if canonical_json(review.envelope) not in context_bundle.content:
                raise ValidationError("Sentinel review context does not contain the exact ReviewEnvelope")
            if review.context_isolated and f"fresh_context:{context_bundle.bundle_id}" not in review.result.isolation:
                raise ValidationError("Sentinel review result does not attest to its exact persisted context")
            try:
                conn.execute(
                    "INSERT INTO sentinel_assessment_reviews(review_id, assessment_id, assessment_hash, task_id, "
                    "artifact_hash, envelope_hash, review_hash, decision, trusted, reviewer_adapter, "
                    "review_context_id, review_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        review.review_id,
                        review.assessment_id,
                        review.assessment_hash,
                        review.task_id,
                        review.artifact_hash,
                        review.envelope.envelope_hash,
                        review.review_hash,
                        review.result.decision.value,
                        1 if review.trusted else 0,
                        review.reviewer_adapter,
                        review.review_context_id,
                        canonical_json(review),
                        review.reviewed_at,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                existing = conn.execute(
                    "SELECT review_json FROM sentinel_assessment_reviews WHERE assessment_id = ?",
                    (review.assessment_id,),
                ).fetchone()
                if existing is not None:
                    stored = SecurityAssessmentReview.from_dict(json.loads(existing["review_json"]))
                    if stored.review_hash == review.review_hash:
                        return stored
                raise ConcurrencyError("Sentinel assessment already has a different review") from exc
            self._append_event(
                conn,
                stream_type="sentinel_review",
                stream_id=review.review_id,
                event_type="sentinel.assessment.reviewed",
                payload={
                    "assessment_id": review.assessment_id,
                    "assessment_hash": review.assessment_hash,
                    "artifact_hash": review.artifact_hash,
                    "decision": review.result.decision.value,
                    "trusted": review.trusted,
                    "structural_failures": list(review.structural_failures),
                    "reviewer_adapter": review.reviewer_adapter,
                    "review_context_id": review.review_context_id,
                },
            )
        return review

    def get_latest_sentinel_review(self, task_id: str, artifact_hash: str):
        from .sentinel.models import SecurityAssessmentReview

        with self.connection() as conn:
            row = conn.execute(
                "SELECT review_json FROM sentinel_assessment_reviews "
                "WHERE task_id = ? AND artifact_hash = ? ORDER BY rowid DESC LIMIT 1",
                (task_id, artifact_hash),
            ).fetchone()
        return None if row is None else SecurityAssessmentReview.from_dict(json.loads(row["review_json"]))

    def get_sentinel_review_for_assessment(self, assessment_id: str):
        from .sentinel.models import SecurityAssessmentReview

        with self.connection() as conn:
            row = conn.execute(
                "SELECT review_json FROM sentinel_assessment_reviews WHERE assessment_id = ?",
                (assessment_id,),
            ).fetchone()
        return None if row is None else SecurityAssessmentReview.from_dict(json.loads(row["review_json"]))

    def save_sentinel_report(self, report):
        from .sentinel.models import PrincipalSecurityReport

        if not isinstance(report, PrincipalSecurityReport):
            raise ValidationError("report must be a PrincipalSecurityReport")
        with self.transaction() as conn:
            review = conn.execute(
                "SELECT assessment_id, assessment_hash, review_hash, task_id, artifact_hash, trusted "
                "FROM sentinel_assessment_reviews WHERE review_id = ?",
                (report.review_id,),
            ).fetchone()
            if review is None:
                raise ValidationError("Sentinel report requires a persisted independent review")
            if (
                review["assessment_id"] != report.assessment_id
                or review["assessment_hash"] != report.assessment_hash
                or review["review_hash"] != report.review_hash
                or review["task_id"] != report.task_id
                or review["artifact_hash"] != report.artifact_hash
            ):
                raise ValidationError("Sentinel report does not bind its assessment and review")
            if report.overall == "attention_required" and not bool(review["trusted"]):
                raise ValidationError("untrusted new-guild findings may not enter the Principal inbox")
            try:
                conn.execute(
                    "INSERT INTO sentinel_reports(report_id, assessment_id, review_id, task_id, artifact_hash, "
                    "overall, report_hash, report_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        report.report_id,
                        report.assessment_id,
                        report.review_id,
                        report.task_id,
                        report.artifact_hash,
                        report.overall,
                        report.report_hash,
                        canonical_json(report),
                        report.generated_at,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                existing = conn.execute(
                    "SELECT report_json FROM sentinel_reports WHERE review_id = ?",
                    (report.review_id,),
                ).fetchone()
                if existing is not None:
                    stored = PrincipalSecurityReport.from_dict(json.loads(existing["report_json"]))
                    if stored.report_hash == report.report_hash:
                        return stored
                raise ConcurrencyError("Sentinel review already has a different report") from exc
            self._append_event(
                conn,
                stream_type="sentinel_report",
                stream_id=report.report_id,
                event_type="sentinel.report.staged_for_principal",
                payload={
                    "task_id": report.task_id,
                    "artifact_hash": report.artifact_hash,
                    "overall": report.overall,
                    "report_hash": report.report_hash,
                    "finding_count": len(report.findings),
                    "destination": report.destination,
                },
            )
        return report

    def get_sentinel_report_for_review(self, review_id: str):
        from .sentinel.models import PrincipalSecurityReport

        with self.connection() as conn:
            row = conn.execute(
                "SELECT report_json FROM sentinel_reports WHERE review_id = ?",
                (review_id,),
            ).fetchone()
        return None if row is None else PrincipalSecurityReport.from_dict(json.loads(row["report_json"]))

    def get_sentinel_report(self, report_id: str):
        from .sentinel.models import PrincipalSecurityReport, ReportAcknowledgement

        with self.connection() as conn:
            row = conn.execute(
                "SELECT r.report_json, a.acknowledgement_json FROM sentinel_reports r "
                "LEFT JOIN sentinel_report_acknowledgements a ON a.report_id = r.report_id "
                "WHERE r.report_id = ?",
                (report_id,),
            ).fetchone()
        if row is None:
            raise NotFoundError(f"Sentinel report not found: {report_id}")
        return {
            "report": PrincipalSecurityReport.from_dict(json.loads(row["report_json"])),
            "acknowledgement": (
                ReportAcknowledgement.from_dict(json.loads(row["acknowledgement_json"]))
                if row["acknowledgement_json"] else None
            ),
        }

    def list_sentinel_reports(self, *, task_id: str | None = None, unacknowledged_only: bool = False):
        from .sentinel.models import PrincipalSecurityReport, ReportAcknowledgement

        clauses = []
        params: list[Any] = []
        if task_id is not None:
            clauses.append("r.task_id = ?")
            params.append(task_id)
        if unacknowledged_only:
            clauses.append("a.report_id IS NULL")
        query = (
            "SELECT r.report_json, a.acknowledgement_json FROM sentinel_reports r "
            "LEFT JOIN sentinel_report_acknowledgements a ON a.report_id = r.report_id"
        )
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY r.rowid DESC"
        with self.connection() as conn:
            rows = conn.execute(query, params).fetchall()
        return tuple(
            {
                "report": PrincipalSecurityReport.from_dict(json.loads(row["report_json"])),
                "acknowledgement": (
                    ReportAcknowledgement.from_dict(json.loads(row["acknowledgement_json"]))
                    if row["acknowledgement_json"] else None
                ),
            }
            for row in rows
        )

    def acknowledge_sentinel_report(self, acknowledgement):
        from .sentinel.models import ReportAcknowledgement

        if not isinstance(acknowledgement, ReportAcknowledgement):
            raise ValidationError("acknowledgement must be a ReportAcknowledgement")
        with self.transaction() as conn:
            if conn.execute(
                "SELECT 1 FROM sentinel_reports WHERE report_id = ?",
                (acknowledgement.report_id,),
            ).fetchone() is None:
                raise NotFoundError(f"Sentinel report not found: {acknowledgement.report_id}")
            try:
                conn.execute(
                    "INSERT INTO sentinel_report_acknowledgements(acknowledgement_id, report_id, "
                    "acknowledgement_json, created_at) VALUES (?, ?, ?, ?)",
                    (
                        acknowledgement.acknowledgement_id,
                        acknowledgement.report_id,
                        canonical_json(acknowledgement),
                        acknowledgement.acknowledged_at,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise ConcurrencyError("Sentinel report is already acknowledged") from exc
            self._append_event(
                conn,
                stream_type="sentinel_report",
                stream_id=acknowledgement.report_id,
                event_type="sentinel.report.acknowledged",
                payload={"acknowledgement": acknowledgement.to_dict()},
            )
        return acknowledgement

    def sentinel_status(self) -> dict[str, Any]:
        with self.connection() as conn:
            row = conn.execute(
                "SELECT "
                "(SELECT COUNT(*) FROM sentinel_assessments) AS assessments, "
                "(SELECT COUNT(*) FROM sentinel_assessment_reviews) AS reviews, "
                "(SELECT COUNT(*) FROM sentinel_assessment_reviews WHERE trusted = 1) AS trusted_reviews, "
                "(SELECT COUNT(*) FROM sentinel_reports) AS reports, "
                "(SELECT COUNT(*) FROM sentinel_reports r LEFT JOIN sentinel_report_acknowledgements a "
                " ON a.report_id = r.report_id WHERE a.report_id IS NULL) AS unacknowledged"
            ).fetchone()
        return {key: int(row[key]) for key in row.keys()}


    def list_events(
        self,
        *,
        stream_type: str | None = None,
        stream_id: str | None = None,
    ) -> list[dict[str, Any]]:
        where: list[str] = []
        params: list[Any] = []
        if stream_type is not None:
            where.append("stream_type = ?")
            params.append(stream_type)
        if stream_id is not None:
            where.append("stream_id = ?")
            params.append(stream_id)
        query = "SELECT * FROM events"
        if where:
            query += " WHERE " + " AND ".join(where)
        query += " ORDER BY sequence"
        with self.connection() as conn:
            rows = conn.execute(query, params).fetchall()
        return [
            {
                "sequence": row["sequence"],
                "event_id": row["event_id"],
                "stream_type": row["stream_type"],
                "stream_id": row["stream_id"],
                "event_type": row["event_type"],
                "payload": json.loads(row["payload_json"]),
                "occurred_at": row["occurred_at"],
            }
            for row in rows
        ]

    def export_jsonl(self, destination: str | Path) -> Path:
        path = Path(destination)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            for event in self.list_events():
                handle.write(canonical_json(event) + "\n")
        return path

    @staticmethod
    def _require_task(conn: sqlite3.Connection, task_id: str) -> None:
        if conn.execute("SELECT 1 FROM tasks WHERE task_id = ?", (task_id,)).fetchone() is None:
            raise NotFoundError(f"task not found: {task_id}")
