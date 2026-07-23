"""LPOS-05: approval identity authenticity is enforced at the runtime boundary.

These tests mirror the compliance-audit reproduction
(approval_and_database.fabricated_approval_identity): constructing a
MessageIdentity with an allowlisted sender string must NOT be sufficient to
grant approval.  Grants require a VerifiedMessage assertion minted by the
runtime's ChannelRegistry through a registered ChannelVerifier.
"""

from __future__ import annotations

import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

from lpos_engine.adapters import AdapterRegistry, DeterministicModelAdapter, RecordingActionAdapter
from lpos_engine.approvals import ChannelRegistry, TrustedLocalChannel
from lpos_engine.engine import LPOSRuntime, RuntimeConfig
from lpos_engine.errors import (
    ApprovalRequired,
    IdentityVerificationError,
    PolicyViolation,
    ReplayDetected,
)
from lpos_engine.models import ActionStatus, MessageIdentity, VerifiedMessage


PRINCIPAL = "principal@example.com"


class IdentityBoundaryTestCase(unittest.TestCase):
    """Shared plumbing: a runtime with an allowlisted sender and NO channels."""

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.action_adapter = RecordingActionAdapter()
        self.runtime = LPOSRuntime(
            RuntimeConfig(
                database_path=self.root / "state.db",
                verified_identities={"email": (PRINCIPAL,)},
            ),
            adapters=AdapterRegistry(
                model_adapters=(DeterministicModelAdapter("creator", priority=10),),
                action_adapters=(self.action_adapter,),
            ),
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def pending_request(self, key: str = "send-1"):
        task = self.runtime.submit_task(
            "Send the external notification",
            required_capabilities=("writing",),
        )
        self.runtime.create_artifact(task.task_id)
        plan, request = self.runtime.plan_action(
            task.task_id,
            kind="external_send",
            parameters={"to": "customer@example.com", "body": "hello"},
            external=True,
            reversible=False,
            idempotency_key=key,
        )
        self.assertIsNotNone(request)
        return plan, request

    @staticmethod
    def identity(
        provider: str = "attacker_controlled_provider",
        *,
        message_id: str = "fabricated-message-id",
        sender: str = PRINCIPAL,
    ) -> MessageIdentity:
        return MessageIdentity(
            channel="email",
            provider=provider,
            message_id=message_id,
            thread_id="fabricated-thread",
            sender=sender,
        )


class FabricatedIdentityTests(IdentityBoundaryTestCase):
    def test_fabricated_identity_with_allowlisted_sender_is_rejected(self) -> None:
        """The exact audit reproduction: allowlisted sender, fabricated
        provider/message/thread, runtime without a registered channel."""

        plan, request = self.pending_request()
        with self.assertRaises(IdentityVerificationError):
            self.runtime.grant_action_approval(
                request.question_id,
                message_identity=self.identity(),
                verified_identity=PRINCIPAL,
            )
        # No grant was created and the exact action cannot be applied.
        self.assertIsNone(self.runtime.store.get_grant_for_action(plan.action_id))
        self.assertEqual(
            self.runtime.store.get_action(plan.action_id)["status"],
            ActionStatus.AWAITING_APPROVAL,
        )
        with self.assertRaises(ApprovalRequired):
            self.runtime.actions.apply(plan.action_id)
        self.assertEqual(self.action_adapter.applied, [])

    def test_unregistered_provider_is_rejected_even_next_to_a_registered_one(self) -> None:
        self.runtime.channels.register(TrustedLocalChannel("local-demo"))
        _, request = self.pending_request()
        with self.assertRaises(IdentityVerificationError):
            self.runtime.grant_action_approval(
                request.question_id,
                message_identity=self.identity("some_other_provider"),
                verified_identity=PRINCIPAL,
            )

    def test_forged_verified_message_not_minted_by_registry_is_rejected(self) -> None:
        self.runtime.channels.register(TrustedLocalChannel("local-demo"))
        _, request = self.pending_request()
        message = self.identity("local-demo")
        forged = VerifiedMessage(
            message_identity=message,
            verification_method="trusted-local-session",
            verifier_id="trusted-local:local_demo",
            provider_event_digest="0" * 64,
            verified_at=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            nonce="f" * 32,
        )
        with self.assertRaises(ReplayDetected):
            self.runtime.grant_action_approval(
                request.question_id,
                message_identity=message,
                verified_identity=PRINCIPAL,
                verified_message=forged,
            )

    def test_assertion_nonce_is_single_use(self) -> None:
        self.runtime.channels.register(TrustedLocalChannel("local-demo"))
        _, first_request = self.pending_request("send-1")
        message = self.identity("local-demo", message_id="m-nonce")
        assertion = self.runtime.channels.ingest(message)
        self.runtime.grant_action_approval(
            first_request.question_id,
            message_identity=message,
            verified_identity=PRINCIPAL,
            verified_message=assertion,
        )
        _, second_request = self.pending_request("send-2")
        second_message = self.identity("local-demo", message_id="m-nonce-2")
        replayed = VerifiedMessage(
            message_identity=second_message,
            verification_method=assertion.verification_method,
            verifier_id=assertion.verifier_id,
            provider_event_digest=assertion.provider_event_digest,
            verified_at=assertion.verified_at,
            nonce=assertion.nonce,
        )
        with self.assertRaises(PolicyViolation):
            self.runtime.grant_action_approval(
                second_request.question_id,
                message_identity=second_message,
                verified_identity=PRINCIPAL,
                verified_message=replayed,
            )

    def test_stale_assertion_is_rejected(self) -> None:
        self.runtime.channels.register(TrustedLocalChannel("local-demo"))
        _, request = self.pending_request()
        message = self.identity("local-demo", message_id="m-stale")
        assertion = self.runtime.channels.ingest(message)
        future = (
            datetime.now(UTC) + timedelta(seconds=self.runtime.channels.max_age_seconds + 60)
        ).isoformat().replace("+00:00", "Z")
        with self.assertRaises(IdentityVerificationError):
            self.runtime.grant_action_approval(
                request.question_id,
                message_identity=message,
                verified_identity=PRINCIPAL,
                verified_message=assertion,
                granted_at=future,
            )

    def test_altered_assertion_is_rejected(self) -> None:
        self.runtime.channels.register(TrustedLocalChannel("local-demo"))
        _, request = self.pending_request()
        message = self.identity("local-demo", message_id="m-alter")
        assertion = self.runtime.channels.ingest(message)
        altered = VerifiedMessage(
            message_identity=assertion.message_identity,
            verification_method="webhook-hmac-sha256",  # claim a stronger method
            verifier_id=assertion.verifier_id,
            provider_event_digest=assertion.provider_event_digest,
            verified_at=assertion.verified_at,
            nonce=assertion.nonce,
        )
        with self.assertRaises(IdentityVerificationError):
            self.runtime.grant_action_approval(
                request.question_id,
                message_identity=message,
                verified_identity=PRINCIPAL,
                verified_message=altered,
            )

    def test_unverified_sender_is_still_rejected_on_a_registered_channel(self) -> None:
        self.runtime.channels.register(TrustedLocalChannel("local-demo"))
        _, request = self.pending_request()
        with self.assertRaises(IdentityVerificationError):
            self.runtime.grant_action_approval(
                request.question_id,
                message_identity=self.identity("local-demo", sender="attacker@example.com"),
                verified_identity="attacker@example.com",
            )


class TrustedLocalChannelTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.runtime = LPOSRuntime.local(
            RuntimeConfig(
                database_path=self.root / "state.db",
                verified_identities={"email": (PRINCIPAL,)},
            )
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def pending_request(self):
        task = self.runtime.submit_task(
            "Send the external notification",
            required_capabilities=("writing",),
        )
        self.runtime.create_artifact(task.task_id)
        return self.runtime.plan_action(
            task.task_id,
            kind="external_send",
            parameters={"to": "customer@example.com", "body": "hello"},
            external=True,
            reversible=False,
            idempotency_key="local-send",
        )

    def test_local_runtime_records_trusted_channel_audit_event(self) -> None:
        events = self.runtime.store.list_events(stream_type="channel")
        registrations = [
            event for event in events
            if event["event_type"] == "channel.trusted_local_registered"
        ]
        self.assertEqual(len(registrations), 1)
        self.assertEqual(registrations[0]["payload"]["provider"], "local_demo")
        self.assertEqual(
            registrations[0]["payload"]["verification_method"], "trusted-local-session"
        )
        self.assertTrue(self.runtime.channels.is_registered("local-demo"))

    def test_trusted_local_grant_works_and_persists_verification_metadata(self) -> None:
        plan, request = self.pending_request()
        grant = self.runtime.grant_action_approval(
            request.question_id,
            message_identity=MessageIdentity(
                channel="email",
                provider="local-demo",
                message_id="m-local",
                thread_id=request.question_id,
                sender=PRINCIPAL,
            ),
            verified_identity=PRINCIPAL,
        )
        self.assertEqual(grant.verification_method, "trusted-local-session")
        self.assertEqual(grant.verifier_id, "trusted-local:local_demo")
        self.assertEqual(len(grant.provider_event_digest), 64)
        self.assertIsNotNone(grant.verified_at)

        stored = self.runtime.store.get_grant_for_action(plan.action_id)
        self.assertEqual(stored.verification_method, "trusted-local-session")
        self.assertEqual(stored.verifier_id, "trusted-local:local_demo")
        self.assertEqual(stored.provider_event_digest, grant.provider_event_digest)
        self.assertEqual(stored.verified_at, grant.verified_at)

        granted_events = [
            event for event in self.runtime.store.list_events(stream_type="approval")
            if event["event_type"] == "approval.granted"
        ]
        self.assertEqual(len(granted_events), 1)
        payload_grant = granted_events[0]["payload"]["grant"]
        self.assertEqual(payload_grant["verification_method"], "trusted-local-session")
        self.assertEqual(payload_grant["verifier_id"], "trusted-local:local_demo")

        result = self.runtime.apply_action(plan.action_id)
        self.assertTrue(result.success)


if __name__ == "__main__":
    unittest.main()
