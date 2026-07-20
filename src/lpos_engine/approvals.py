"""Verified identity, exact-action approval binding, expiry, and replay protection."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Iterable, Mapping

from .canonical import new_id, parse_timestamp, utc_now
from .errors import (
    ApprovalExpired,
    ApprovalMismatch,
    ApprovalRequired,
    IdentityVerificationError,
)
from .models import ActionPlan, ApprovalGrant, ApprovalRequest, MessageIdentity
from .store import SQLiteStore


class IdentityVerifier:
    """Provider-neutral Principal identity registry."""

    def __init__(self, verified: Mapping[str, Iterable[str]] | None = None) -> None:
        self._verified: dict[str, set[str]] = {}
        for channel, identities in (verified or {}).items():
            self._verified[channel.strip().lower()] = {
                self.normalize(channel, identity) for identity in identities
            }

    @staticmethod
    def normalize(channel: str, identity: str) -> str:
        clean = identity.strip()
        if channel.strip().lower() == "email":
            clean = clean.lower()
        return clean

    def add(self, channel: str, identity: str) -> None:
        key = channel.strip().lower()
        self._verified.setdefault(key, set()).add(self.normalize(key, identity))

    def verify(self, message: MessageIdentity, claimed_verified_identity: str) -> str:
        channel = message.channel.lower()
        sender = self.normalize(channel, message.sender)
        claimed = self.normalize(channel, claimed_verified_identity)
        if sender != claimed:
            raise IdentityVerificationError(
                "message sender does not match the identity claimed by the approval grant"
            )
        if sender not in self._verified.get(channel, set()):
            raise IdentityVerificationError(
                f"sender {message.sender!r} is not a verified Principal identity for {channel}"
            )
        return sender


class ApprovalService:
    def __init__(self, store: SQLiteStore, identity_verifier: IdentityVerifier) -> None:
        self.store = store
        self.identity_verifier = identity_verifier

    def request(self, plan: ActionPlan, *, expires_at: str | None = None) -> ApprovalRequest:
        if not plan.approval_required:
            raise ApprovalMismatch("action does not require approval")
        request = ApprovalRequest.from_plan(
            plan,
            question_id=new_id("LPOS-Q"),
            expires_at=expires_at,
        )
        return self.store.save_approval_request(request)

    def grant(
        self,
        *,
        request: ApprovalRequest,
        message_identity: MessageIdentity,
        verified_identity: str,
        granted_action: str | None = None,
        granted_at: str | None = None,
    ) -> ApprovalGrant:
        self.identity_verifier.verify(message_identity, verified_identity)
        action_text = granted_action if granted_action is not None else request.exact_action
        if action_text != request.exact_action:
            raise ApprovalMismatch("approval text differs from the exact requested action")
        grant = ApprovalGrant(
            grant_id=new_id("APG"),
            question_id=request.question_id,
            task_id=request.task_id,
            action_id=request.action_id,
            granted_action=action_text,
            action_hash=request.action_hash,
            channel=message_identity.channel,
            message_identity=message_identity,
            verified_identity=verified_identity,
            granted_at=granted_at or utc_now(),
            expires_at=request.expires_at,
        )
        self._assert_not_expired(grant)
        self.store.save_approval_grant(grant)
        return grant

    def validate(self, plan: ActionPlan, *, now: str | None = None) -> ApprovalGrant | None:
        """Validate an exact-action grant without mutating state.

        The action service pairs this check with ``SQLiteStore.claim_action_execution``
        so grant consumption and the transition to ``executing`` commit atomically.
        """

        if not plan.approval_required:
            return None
        grant = self.store.get_grant_for_action(plan.action_id)
        if grant is None:
            raise ApprovalRequired(f"exact action {plan.action_id} has no approval grant")
        if (
            grant.task_id != plan.task_id
            or grant.action_id != plan.action_id
            or grant.action_hash != plan.action_hash
            or grant.granted_action != plan.exact_action
        ):
            raise ApprovalMismatch("approval grant does not bind to the exact stored action")
        self.identity_verifier.verify(grant.message_identity, grant.verified_identity)
        self._assert_not_expired(grant, now=now)
        return grant

    def authorize(self, plan: ActionPlan, *, now: str | None = None) -> ApprovalGrant | None:
        """Validate and consume a grant for callers outside ``ActionService``.

        Runtime execution should use ``validate`` followed by the store's atomic
        execution claim.  This compatibility method retains the explicit consume
        behavior for integrations that only need an authorization decision.
        """

        grant = self.validate(plan, now=now)
        if grant is not None:
            self.store.mark_grant_consumed(grant.grant_id, plan.action_id)
        return grant

    @staticmethod
    def _assert_not_expired(grant: ApprovalGrant, *, now: str | None = None) -> None:
        if not grant.expires_at:
            return
        observed = parse_timestamp(now or utc_now()).astimezone(UTC)
        expiry = parse_timestamp(grant.expires_at).astimezone(UTC)
        if observed > expiry:
            raise ApprovalExpired(f"approval {grant.grant_id} expired at {grant.expires_at}")
