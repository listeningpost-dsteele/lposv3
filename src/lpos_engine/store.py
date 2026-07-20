"""Transactional SQLite state and append-only event storage."""

from __future__ import annotations

import json
import sqlite3
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


class SQLiteStore:
    """Authoritative transactional state with an immutable audit stream."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

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
        with self.connection() as conn:
            row = conn.execute("PRAGMA integrity_check").fetchone()
        return str(row[0]) if row is not None else "unknown"

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
    def _append_event(
        conn: sqlite3.Connection,
        *,
        stream_type: str,
        stream_id: str,
        event_type: str,
        payload: Mapping[str, Any],
    ) -> str:
        event_id = new_id("EVT")
        conn.execute(
            "INSERT INTO events(event_id, stream_type, stream_id, event_type, payload_json, occurred_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (event_id, stream_type, stream_id, event_type, canonical_json(payload), utc_now()),
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

    @classmethod
    def _save_evidence_tx(
        cls,
        conn: sqlite3.Connection,
        record: EvidenceRecord,
        *,
        task_id: str | None = None,
    ) -> None:
        if task_id:
            cls._require_task(conn, task_id)
        conn.execute(
            "INSERT INTO evidence(evidence_id, task_id, record_json, created_at) VALUES (?, ?, ?, ?)",
            (record.id, task_id, canonical_json(record), utc_now()),
        )
        cls._append_event(
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
