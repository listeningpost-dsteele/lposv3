from __future__ import annotations

import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

from lpos_engine.actions import ActionService
from lpos_engine.adapters import (
    AdapterRegistry,
    RecordingActionAdapter,
    SandboxedFileActionAdapter,
)
from lpos_engine.approvals import ApprovalService, IdentityVerifier
from lpos_engine.errors import (
    ActionExecutionError,
    ApprovalExpired,
    ApprovalMismatch,
    ApprovalRequired,
    ConcurrencyError,
    IdentityVerificationError,
    ReplayDetected,
)
from lpos_engine.models import ActionStatus, MessageIdentity, TaskEnvelope
from lpos_engine.store import SQLiteStore


class ApprovalActionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.store = SQLiteStore(self.root / "state.db")
        self.store.create_task(
            TaskEnvelope(
                task_id="TASK-1",
                principal_instruction="Act",
                lead_guild="Operations",
                lead_specialist="PROFILE-OPERATIONS",
                required_capabilities=("operations",),
                material=False,
                materiality_basis=("routine_internal_reversible",),
            )
        )
        self.identity = IdentityVerifier({"email": ("principal@example.com",)})
        self.approvals = ApprovalService(self.store, self.identity)
        self.recording = RecordingActionAdapter()
        self.files = SandboxedFileActionAdapter(self.root / "files")
        self.registry = AdapterRegistry(action_adapters=(self.recording, self.files))
        self.service = ActionService(self.store, self.registry, self.approvals)

    def tearDown(self):
        self.temp.cleanup()

    def message(self, message_id="m1", sender="principal@example.com"):
        return MessageIdentity(
            channel="email",
            provider="test",
            message_id=message_id,
            thread_id="thread",
            sender=sender,
        )

    def external_plan(self, key="send-1", expires_at=None):
        return self.service.plan(
            task_id="TASK-1",
            kind="external_send",
            parameters={"to": "customer@example.com", "body": "hello"},
            external=True,
            reversible=False,
            idempotency_key=key,
            expires_at=expires_at,
        )

    def test_external_action_automatically_requires_approval(self):
        plan, request = self.external_plan()
        self.assertTrue(plan.approval_required)
        self.assertIsNotNone(request)
        self.assertEqual(self.store.get_action(plan.action_id)["status"], ActionStatus.AWAITING_APPROVAL)

    def test_missing_approval_blocks_apply(self):
        plan, _ = self.external_plan()
        with self.assertRaises(ApprovalRequired):
            self.service.apply(plan.action_id)
        self.assertFalse(self.recording.applied)

    def test_unverified_sender_cannot_grant(self):
        _, request = self.external_plan()
        with self.assertRaises(IdentityVerificationError):
            self.approvals.grant(
                request=request,
                message_identity=self.message(sender="attacker@example.com"),
                verified_identity="attacker@example.com",
            )

    def test_claimed_identity_must_match_sender(self):
        _, request = self.external_plan()
        with self.assertRaises(IdentityVerificationError):
            self.approvals.grant(
                request=request,
                message_identity=self.message(),
                verified_identity="other@example.com",
            )

    def test_altered_action_text_cannot_be_granted(self):
        _, request = self.external_plan()
        with self.assertRaises(ApprovalMismatch):
            self.approvals.grant(
                request=request,
                message_identity=self.message(),
                verified_identity="principal@example.com",
                granted_action=request.exact_action + " ",
            )

    def test_expired_approval_is_rejected(self):
        expiry = (datetime.now(UTC) - timedelta(minutes=1)).isoformat().replace("+00:00", "Z")
        _, request = self.external_plan(expires_at=expiry)
        with self.assertRaises(ApprovalExpired):
            self.approvals.grant(
                request=request,
                message_identity=self.message(),
                verified_identity="principal@example.com",
            )

    def test_valid_grant_applies_exactly_once(self):
        plan, request = self.external_plan()
        self.approvals.grant(
            request=request,
            message_identity=self.message(),
            verified_identity="principal@example.com",
        )
        first = self.service.apply(plan.action_id)
        second = self.service.apply(plan.action_id)
        self.assertTrue(first.success)
        self.assertEqual(first, second)
        self.assertEqual(len(self.recording.applied), 1)

    def test_message_replay_cannot_approve_second_action(self):
        _, first_request = self.external_plan("send-1")
        self.approvals.grant(
            request=first_request,
            message_identity=self.message("same-message"),
            verified_identity="principal@example.com",
        )
        _, second_request = self.external_plan("send-2")
        with self.assertRaises(ReplayDetected):
            self.approvals.grant(
                request=second_request,
                message_identity=self.message("same-message"),
                verified_identity="principal@example.com",
            )

    def test_same_request_cannot_be_granted_twice(self):
        _, request = self.external_plan()
        self.approvals.grant(
            request=request,
            message_identity=self.message("m1"),
            verified_identity="principal@example.com",
        )
        with self.assertRaises(ReplayDetected):
            self.approvals.grant(
                request=request,
                message_identity=self.message("m2"),
                verified_identity="principal@example.com",
            )

    def test_local_reversible_action_needs_no_approval(self):
        plan, request = self.service.plan(
            task_id="TASK-1",
            kind="filesystem_write",
            parameters={"path": "a.txt", "content": "hello"},
            external=False,
            reversible=True,
            idempotency_key="write-1",
        )
        self.assertIsNone(request)
        result = self.service.apply(plan.action_id)
        self.assertTrue(result.success)
        self.assertEqual((self.root / "files" / "a.txt").read_text(), "hello")

    def test_file_path_traversal_is_blocked_and_recorded(self):
        plan, _ = self.service.plan(
            task_id="TASK-1",
            kind="filesystem_write",
            parameters={"path": "../escape.txt", "content": "bad"},
            external=False,
            reversible=True,
            idempotency_key="write-traversal",
        )
        with self.assertRaises(ActionExecutionError):
            self.service.apply(plan.action_id)
        state = self.store.get_action(plan.action_id)
        self.assertEqual(state["status"], ActionStatus.FAILED)
        self.assertFalse((self.root / "escape.txt").exists())

    def test_expected_checksum_prevents_lost_update(self):
        target = self.root / "files" / "a.txt"
        target.write_text("current", encoding="utf-8")
        plan, _ = self.service.plan(
            task_id="TASK-1",
            kind="filesystem_write",
            parameters={"path": "a.txt", "content": "new", "expected_sha256": "0" * 64},
            external=False,
            reversible=True,
            idempotency_key="write-checksum",
        )
        with self.assertRaises(ActionExecutionError):
            self.service.apply(plan.action_id)
        self.assertEqual(target.read_text(), "current")

    def test_idempotency_key_cannot_change_exact_action(self):
        self.external_plan("same")
        with self.assertRaises(ConcurrencyError):
            self.service.plan(
                task_id="TASK-1",
                kind="external_send",
                parameters={"to": "different@example.com"},
                external=True,
                reversible=False,
                idempotency_key="same",
            )

    def test_identical_plan_retry_reuses_action_and_approval_question(self):
        first_plan, first_request = self.external_plan("retry-safe")
        second_plan, second_request = self.external_plan("retry-safe")
        self.assertEqual(second_plan.action_id, first_plan.action_id)
        self.assertEqual(second_plan.action_hash, first_plan.action_hash)
        self.assertIsNotNone(first_request)
        self.assertEqual(second_request, first_request)
        events = self.store.list_events(stream_type="approval")
        self.assertEqual(sum(event["event_type"] == "approval.requested" for event in events), 1)

    def test_identical_plan_retry_cannot_change_approval_expiry(self):
        expiry = (datetime.now(UTC) + timedelta(minutes=10)).isoformat().replace("+00:00", "Z")
        self.external_plan("expiry-safe", expires_at=expiry)
        changed = (datetime.now(UTC) + timedelta(minutes=20)).isoformat().replace("+00:00", "Z")
        with self.assertRaises(ActionExecutionError):
            self.external_plan("expiry-safe", expires_at=changed)
