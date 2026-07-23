"""Verified identity, trusted channel ingestion, exact-action approval binding,
expiry, and replay protection.

Trust model (LPOS-05)
---------------------
``MessageIdentity`` is plain data and is caller-constructible; it therefore
carries no authenticity on its own.  Authenticity is established only at the
trusted channel-ingestion boundary:

1. A host registers one ``ChannelVerifier`` per message provider on the
   ``ChannelRegistry`` (via ``RuntimeConfig.verified_channels`` or
   ``ChannelRegistry.register``).
2. The verifier validates raw provider evidence -- webhook signatures/secrets,
   authenticated API sessions, provider message lookups -- and the registry
   then mints a single-use ``VerifiedMessage`` assertion bound to that
   evidence.  Assertions can be minted only through the registry.
3. ``ApprovalService.grant`` accepts an approval only when the message is
   accompanied by (or can be ingested into) a registry-minted assertion whose
   provider is registered, whose nonce is unused, and whose age is inside the
   freshness window; the sender must additionally be on the
   ``IdentityVerifier`` allowlist.

Live consequential adapters require a real ``ChannelVerifier`` that validates
provider signatures or webhook secrets against the raw provider event.  The
enablement gate for any live adapter is a verified end-to-end round trip
(outbound prompt -> provider -> inbound signed event -> correlation ->
identity), not the presence of an allowlisted sender string.
"""

from __future__ import annotations

import abc
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Iterable, Mapping

from .canonical import digest, new_id, normalize_token, parse_timestamp, utc_now
from .errors import (
    ApprovalExpired,
    ApprovalMismatch,
    ApprovalRequired,
    IdentityVerificationError,
    ReplayDetected,
)
from .models import ActionPlan, ApprovalGrant, ApprovalRequest, MessageIdentity, VerifiedMessage
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


@dataclass(frozen=True, slots=True)
class ChannelVerification:
    """The provider-specific outcome a ChannelVerifier reports to the registry."""

    verification_method: str
    provider_event_digest: str


class ChannelVerifier(abc.ABC):
    """Authenticated ingestion adapter for one message provider.

    A real implementation for a live channel MUST validate cryptographic or
    session evidence from the provider itself -- e.g. verify the webhook HMAC
    with the shared secret, validate the provider's event signature and
    timestamp, or re-fetch the message over an authenticated API session --
    and bind the returned ``provider_event_digest`` to that raw evidence.
    Returning successfully from ``verify_evidence`` without such validation
    reintroduces the fabricated-identity vulnerability (LPOS-05).
    """

    #: Provider token this verifier authenticates (normalized on registration).
    provider: str = ""
    #: Stable identity of the verifier recorded on every grant it enables.
    verifier_id: str = ""

    @abc.abstractmethod
    def verify_evidence(
        self,
        message: MessageIdentity,
        evidence: Mapping[str, object] | None,
    ) -> ChannelVerification:
        """Validate provider evidence for ``message`` or raise
        ``IdentityVerificationError``."""


class TrustedLocalChannel(ChannelVerifier):
    """Explicit demo/test channel that trusts the local interactive session.

    This verifier performs NO provider authentication.  It exists so the
    bundled record-only demo and the test suite can exercise the approval flow
    without a live provider, while making that trust decision explicit and
    auditable: ``LPOSRuntime.local`` records an audit event whenever a
    trusted-local channel is registered.  Never register this channel in a
    deployment with live consequential adapters.
    """

    def __init__(self, provider: str = "local-demo") -> None:
        self.provider = normalize_token(provider)
        self.verifier_id = f"trusted-local:{self.provider}"

    def verify_evidence(
        self,
        message: MessageIdentity,
        evidence: Mapping[str, object] | None,
    ) -> ChannelVerification:
        return ChannelVerification(
            verification_method="trusted-local-session",
            provider_event_digest=digest(message.to_dict()),
        )


class ChannelRegistry:
    """Registry of authenticated channel verifiers and the only assertion mint.

    ``VerifiedMessage`` assertions are minted exclusively by ``ingest``: the
    registry issues an unpredictable single-use nonce, records a digest of the
    minted assertion, and later releases the nonce exactly once in
    ``consume``.  A ``VerifiedMessage`` constructed anywhere else (or replayed,
    altered, or held past the freshness window) is rejected.

    Nonces are held in process memory: an assertion must be consumed by the
    same runtime process that ingested it, which matches the ingestion-to-grant
    flow this registry protects.
    """

    def __init__(
        self,
        channels: Mapping[str, ChannelVerifier] | Iterable[ChannelVerifier] | None = None,
        *,
        max_age_seconds: int = 900,
    ) -> None:
        if max_age_seconds < 1:
            raise IdentityVerificationError("assertion freshness window must be positive")
        self.max_age_seconds = max_age_seconds
        self._verifiers: dict[str, ChannelVerifier] = {}
        self._active_nonces: dict[str, str] = {}
        if channels is None:
            return
        if isinstance(channels, Mapping):
            for provider, verifier in channels.items():
                self.register(verifier, provider=provider)
        else:
            for verifier in channels:
                self.register(verifier)

    def register(self, verifier: ChannelVerifier, *, provider: str | None = None) -> None:
        name = normalize_token(provider if provider is not None else verifier.provider)
        if not verifier.verifier_id:
            raise IdentityVerificationError("channel verifier requires a stable verifier_id")
        self._verifiers[name] = verifier

    def is_registered(self, provider: str) -> bool:
        return normalize_token(provider) in self._verifiers

    def registered_providers(self) -> tuple[str, ...]:
        return tuple(sorted(self._verifiers))

    def get(self, provider: str) -> ChannelVerifier:
        verifier = self._verifiers.get(normalize_token(provider))
        if verifier is None:
            raise IdentityVerificationError(
                f"no channel verifier is registered for provider {provider!r}; "
                "a caller-constructed MessageIdentity is not evidence of authenticity"
            )
        return verifier

    def ingest(
        self,
        message: MessageIdentity,
        evidence: Mapping[str, object] | None = None,
    ) -> VerifiedMessage:
        """Verify provider evidence for ``message`` and mint an assertion."""

        verifier = self.get(message.provider)
        verification = verifier.verify_evidence(message, evidence)
        assertion = VerifiedMessage(
            message_identity=message,
            verification_method=verification.verification_method,
            verifier_id=verifier.verifier_id,
            provider_event_digest=verification.provider_event_digest,
            verified_at=utc_now(),
            nonce=secrets.token_hex(16),
        )
        self._active_nonces[assertion.nonce] = digest(assertion.to_dict())
        return assertion

    def consume(
        self,
        assertion: VerifiedMessage,
        message: MessageIdentity,
        *,
        now: str | None = None,
    ) -> VerifiedMessage:
        """Validate a minted assertion for ``message`` and retire its nonce."""

        if not self.is_registered(assertion.message_identity.provider):
            raise IdentityVerificationError(
                "assertion provider has no registered channel verifier"
            )
        expected = self._active_nonces.get(assertion.nonce)
        if expected is None:
            raise ReplayDetected(
                "channel assertion is not active: it was not minted by this registry "
                "or has already been consumed"
            )
        if expected != digest(assertion.to_dict()):
            raise IdentityVerificationError("channel assertion was altered after minting")
        if assertion.message_identity != message:
            raise IdentityVerificationError(
                "channel assertion is bound to a different message identity"
            )
        observed = parse_timestamp(now or utc_now()).astimezone(UTC)
        verified = parse_timestamp(assertion.verified_at).astimezone(UTC)
        age = (observed - verified).total_seconds()
        if age > self.max_age_seconds:
            raise IdentityVerificationError(
                f"channel assertion is stale: verified {int(age)}s ago, "
                f"maximum age is {self.max_age_seconds}s"
            )
        del self._active_nonces[assertion.nonce]
        return assertion


class ApprovalService:
    def __init__(
        self,
        store: SQLiteStore,
        identity_verifier: IdentityVerifier,
        channel_registry: ChannelRegistry | None = None,
    ) -> None:
        self.store = store
        self.identity_verifier = identity_verifier
        # An absent registry is an EMPTY registry: every provider is
        # unregistered and every grant attempt is rejected until the host
        # registers an authenticated channel verifier.
        self.channels = channel_registry if channel_registry is not None else ChannelRegistry()

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
        verified_message: VerifiedMessage | None = None,
        provider_evidence: Mapping[str, object] | None = None,
        granted_action: str | None = None,
        granted_at: str | None = None,
    ) -> ApprovalGrant:
        """Grant an exact action from a channel-verified approval message.

        A caller-constructed ``MessageIdentity`` is never sufficient on its
        own.  Either the caller supplies a ``verified_message`` assertion
        previously minted by the channel registry, or the registry ingests the
        message now using the registered verifier for its provider (passing
        ``provider_evidence`` through to that verifier).  A provider without a
        registered channel verifier is rejected outright; assertion nonces are
        single-use and assertion age is bounded by the registry's freshness
        window.  Verification metadata is persisted with the grant.
        """

        if verified_message is None:
            verified_message = self.channels.ingest(message_identity, provider_evidence)
        moment = granted_at or utc_now()
        self.channels.consume(verified_message, message_identity, now=moment)
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
            granted_at=moment,
            expires_at=request.expires_at,
            verification_method=verified_message.verification_method,
            verifier_id=verified_message.verifier_id,
            provider_event_digest=verified_message.provider_event_digest,
            verified_at=verified_message.verified_at,
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
