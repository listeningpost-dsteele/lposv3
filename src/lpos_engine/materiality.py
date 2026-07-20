"""Deterministic implementation of LPOS-030 materiality."""

from __future__ import annotations

from .models import MaterialityDecision, MaterialitySignals

_SIGNAL_TO_BASIS = (
    ("external_or_irreversible", "external_or_irreversible_action"),
    ("changes_approved_artifact", "changes_approved_artifact"),
    ("customer_or_public_facing", "customer_or_public_facing"),
    ("legal_financial_security_privacy", "legal_financial_security_or_privacy_impact"),
    ("strategy_brand_or_taste", "strategy_brand_or_principal_taste"),
    ("modifies_long_lived_specification", "modifies_long_lived_specification"),
    ("failure_cost_exceeds_review_cost", "failure_cost_exceeds_review_cost"),
    ("uncertain", "uncertain_treated_as_material"),
)


class MaterialityPolicy:
    """Classify work without a model and record the exact basis."""

    @staticmethod
    def evaluate(signals: MaterialitySignals) -> MaterialityDecision:
        if signals.explicit_principal_designation is not None:
            note = (signals.designation_note or "principal_designation").strip()
            return MaterialityDecision(
                material=signals.explicit_principal_designation,
                basis=(f"principal_designation:{note}",),
            )

        basis = tuple(label for field_name, label in _SIGNAL_TO_BASIS if getattr(signals, field_name))
        return MaterialityDecision(
            material=bool(basis),
            basis=basis if basis else ("routine_internal_reversible",),
        )
