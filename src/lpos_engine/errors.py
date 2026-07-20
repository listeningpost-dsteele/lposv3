"""Typed failures used by the LPOS control plane."""


class LPOSError(Exception):
    """Base class for all expected engine failures."""


class ValidationError(LPOSError):
    """An envelope or record violates its schema or invariant."""


class NotFoundError(LPOSError):
    """A requested state object does not exist."""


class InvalidTransitionError(LPOSError):
    """A state transition is not permitted by the task state machine."""


class ConcurrencyError(LPOSError):
    """Optimistic concurrency or idempotency protection rejected a write."""


class PolicyViolation(LPOSError):
    """A constitutional policy blocked an operation."""


class ApprovalRequired(PolicyViolation):
    """An exact action lacks a valid, bound approval."""


class ApprovalMismatch(PolicyViolation):
    """An approval does not bind to the action being applied."""


class ApprovalExpired(PolicyViolation):
    """An approval is no longer valid."""


class IdentityVerificationError(PolicyViolation):
    """The purported Principal identity is not verified for the channel."""


class ReplayDetected(PolicyViolation):
    """An inbound message or approval has already been processed."""


class ContextIsolationError(PolicyViolation):
    """A review context contains prohibited creator material or is not fresh."""


class AdapterError(LPOSError):
    """A model, tool, channel, or scheduler adapter failed."""


class ActionExecutionError(LPOSError):
    """An action executor returned an explicit failure."""
