"""Deterministic criticality classification for code changes.

:func:`classify` maps a set of change signals to one of LIGHT, STANDARD, HIGH, or
CRITICAL using the rules in the Code Testing Gauntlet Standard. The function is total:
it never raises, coerces unknown values, and defaults unknown or empty signal sets to
STANDARD. The returned record carries the rationale, the cumulative required gates, the
review authority, whether independent evidence is required, and the conditions that
would move the change to a higher tier.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from . import gauntlet

# Signals that, if present, force CRITICAL.
#   destructive, secrets, financial movement, irreversible migration,
#   production infrastructure.
# Signals that force at least HIGH.
#   auth, permissions, customer data, public API, migration, concurrency,
#   broad blast radius.

_REVIEW_AUTHORITY = {
    "LIGHT": "implementing engineer (automated gates)",
    "STANDARD": "Code Testing Guild peer review",
    "HIGH": "independent acceptance-spec review and the Release Verification Auditor",
    "CRITICAL": "Principal or qualified engineer approval of behavior and architecture",
}

_ESCALATION = {
    "LIGHT": (
        "Escalate to STANDARD if the change alters product or business logic, or its "
        "blast radius grows beyond a small, reversible internal change."
    ),
    "STANDARD": (
        "Escalate to HIGH if the change touches authentication, permissions, customer "
        "data, a public API, a migration, concurrency, or broad architecture."
    ),
    "HIGH": (
        "Escalate to CRITICAL if the change becomes destructive, handles secrets, moves "
        "money, becomes an irreversible migration, or touches production infrastructure."
    ),
    "CRITICAL": (
        "Already the highest tier; require Principal approval, isolated environment, "
        "staging/canary validation, a restore drill, and explicit release approval."
    ),
}


def _flag(signals: Mapping[str, Any], name: str) -> bool:
    try:
        return bool(signals.get(name))
    except Exception:  # pragma: no cover - defensive: signals may be a hostile mapping
        return False


def _blast_radius(signals: Mapping[str, Any]) -> str:
    try:
        value = str(signals.get("blast_radius") or "").strip().lower()
    except Exception:  # pragma: no cover - defensive
        value = ""
    return value if value in {"small", "medium", "broad"} else "medium"


def _reversible(signals: Mapping[str, Any]) -> bool:
    # Default to reversible=True only when explicitly stated; unknown reversibility is
    # treated as reversible for tiering but never downgrades a CRITICAL/HIGH trigger.
    if "reversible" not in signals:
        return True
    return bool(signals.get("reversible"))


def classify(signals: Mapping[str, Any] | None) -> dict[str, Any]:
    """Classify a code change into LIGHT / STANDARD / HIGH / CRITICAL.

    Deterministic and total: unknown or absent signals default to STANDARD.
    """
    signals = signals or {}
    if not isinstance(signals, Mapping):  # total: tolerate any input
        signals = {}

    blast = _blast_radius(signals)
    reversible = _reversible(signals)

    critical_reasons: list[str] = []
    if _flag(signals, "destructive"):
        critical_reasons.append("destructive operation")
    if _flag(signals, "secrets"):
        critical_reasons.append("handles secrets")
    if _flag(signals, "financial_movement"):
        critical_reasons.append("moves money")
    if _flag(signals, "migration") and not reversible:
        critical_reasons.append("irreversible migration")
    if _flag(signals, "production_infra"):
        critical_reasons.append("production infrastructure")

    high_reasons: list[str] = []
    if _flag(signals, "touches_auth"):
        high_reasons.append("authentication")
    if _flag(signals, "touches_permissions"):
        high_reasons.append("permissions")
    if _flag(signals, "customer_data"):
        high_reasons.append("customer data")
    if _flag(signals, "public_api"):
        high_reasons.append("public API")
    if _flag(signals, "migration"):
        high_reasons.append("migration")
    if _flag(signals, "concurrency"):
        high_reasons.append("concurrency")
    if blast == "broad":
        high_reasons.append("broad blast radius / architectural change")

    if critical_reasons:
        level = "CRITICAL"
        rationale = "CRITICAL: " + "; ".join(critical_reasons) + "."
    elif high_reasons:
        level = "HIGH"
        rationale = "HIGH: " + "; ".join(high_reasons) + "."
    elif blast == "small" and reversible:
        level = "LIGHT"
        rationale = (
            "LIGHT: low-risk internal change with small, reversible blast radius and no "
            "sensitive, external, or destructive signals."
        )
    else:
        level = "STANDARD"
        rationale = (
            "STANDARD: normal product or business logic with no high-risk or critical "
            "signals."
        )

    return {
        "level": level,
        "rationale": rationale,
        "required_gates": gauntlet.required_gates(level),
        "review_authority": _REVIEW_AUTHORITY[level],
        "evidence_required": level in {"STANDARD", "HIGH", "CRITICAL"},
        "escalation_conditions": _ESCALATION[level],
    }


__all__ = ["classify"]
