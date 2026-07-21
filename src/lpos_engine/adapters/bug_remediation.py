"""Deterministic host handlers for the Bug Remediation standing operation.

These handlers model the host integration contract without performing live email,
network, production merge, or deploy side effects. Deployment hosts bind the same
handler names to sandbox, review, evidence, PR, and verified reporter mail
services.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ..canonical import digest

ESCALATION_REASONS = {
    "not_reproducible",
    "low_root_cause_confidence",
    "attempt_budget_exhausted",
    "external_or_irreversible_action_required",
    "product_taste_or_policy_decision",
    "security_sensitive",
    "out_of_scope_fix",
    "duplicate_open_escalation",
}


def _bug_report(ctx: Mapping[str, Any]) -> Mapping[str, Any]:
    report = ctx.get("bug_report")
    if not isinstance(report, Mapping):
        raise ValueError("Bug Remediation requires a bug_report context object")
    return report


def _reporter(report: Mapping[str, Any]) -> Mapping[str, Any]:
    reporter = report.get("reporter")
    if not isinstance(reporter, Mapping):
        raise ValueError("BugReport.reporter is required")
    if not reporter.get("verified"):
        raise ValueError("reporter contact is not verified; outbound status is blocked")
    return reporter


def _tracking_id(report: Mapping[str, Any]) -> str:
    value = report.get("report_id")
    if not isinstance(value, str) or not value:
        raise ValueError("BugReport.report_id is required")
    return value


def _scan_outbound(value: str) -> None:
    lowered = value.lower()
    markers = ("api_key", "secret", "password", "token=", "bearer ")
    if any(marker in lowered for marker in markers):
        raise ValueError("outbound reporter notification failed secret scan")


def acknowledge_reporter(ctx: Mapping[str, Any]) -> Mapping[str, Any]:
    report = _bug_report(ctx)
    reporter = _reporter(report)
    body = f"Received bug report {_tracking_id(report)}. We are reproducing it now."
    _scan_outbound(body)
    return {
        "tracking_id": _tracking_id(report),
        "status": "acknowledged",
        "notification": {
            "to": reporter["contact"],
            "channel": reporter.get("channel", "email"),
            "body": body,
            "sent": True,
            "verified_contact": True,
            "secret_scan": "passed",
        },
    }


def reproduce_in_sandbox(ctx: Mapping[str, Any]) -> Mapping[str, Any]:
    report = _bug_report(ctx)
    mode = report.get("component_hint")
    if mode == "unreproducible-fixture":
        return {
            "status": "not_reproducible",
            "strategies": ["unit_fixture", "ui_replay", "log_replay"],
            "attempts": 3,
            "escalation_reason": "not_reproducible",
            "questions": ["What exact build id and account state reproduced the defect?"],
        }
    steps = tuple(report.get("steps_to_reproduce", ()))
    if not steps:
        return {
            "status": "not_reproducible",
            "strategies": ["unit_fixture", "ui_replay", "log_replay"],
            "attempts": 3,
            "escalation_reason": "not_reproducible",
            "questions": ["Please provide at least one reproduction step."],
        }
    return {
        "status": "reproduced",
        "strategies": ["unit_fixture", "ui_replay"],
        "attempts": 2,
        "repro_steps": list(steps),
        "sandbox": {"network": "disabled", "resource_limits": "default"},
    }


def repro_to_failing_fixture(ctx: Mapping[str, Any]) -> Mapping[str, Any]:
    report = _bug_report(ctx)
    repro = ctx["dependencies"]["STEP-REPRODUCE"]
    fixture_id = "BUGFIX-" + _tracking_id(report).replace("BUG-", "")
    if repro.get("status") != "reproduced":
        return {
            "status": "skipped",
            "escalation_reason": repro.get("escalation_reason", "not_reproducible"),
            "failing_fixture": None,
        }
    return {
        "status": "created_failing_fixture",
        "fixture_id": fixture_id,
        "failing_fixture": {
            "id": fixture_id,
            "expected": report["expected"],
            "actual": report["actual"],
            "initial_result": "FAIL",
        },
    }


def localize_root_cause(ctx: Mapping[str, Any]) -> Mapping[str, Any]:
    regression = ctx["dependencies"]["STEP-REGRESSION"]
    if regression.get("status") != "created_failing_fixture":
        return {
            "status": "not_localized",
            "confidence": 0.0,
            "escalation_reason": regression.get("escalation_reason", "not_reproducible"),
        }
    return {
        "status": "localized",
        "root_cause": "deterministic fixture exposes a mismatch between expected and actual behavior",
        "hypotheses": [
            "application logic returned the actual value",
            "missing regression guard allowed the mismatch",
        ],
        "confidence": 0.92,
    }


def attempt_fix_loop(ctx: Mapping[str, Any]) -> Mapping[str, Any]:
    report = _bug_report(ctx)
    diagnosis = ctx["dependencies"]["STEP-DIAGNOSE"]
    if diagnosis.get("status") != "localized":
        return {
            "status": "not_attempted",
            "attempts": [],
            "escalation_reason": diagnosis.get("escalation_reason", "low_root_cause_confidence"),
        }
    if report.get("component_hint") == "attempt-budget-exhausted":
        return {
            "status": "failed",
            "attempts": [
                {"attempt": 1, "result": "fixture still failing"},
                {"attempt": 2, "result": "suite regression"},
                {"attempt": 3, "result": "out of scope"},
                {"attempt": 4, "result": "review rejected"},
            ],
            "escalation_reason": "attempt_budget_exhausted",
        }
    branch = "bugfix/" + _tracking_id(report).lower()
    pr_ref = "dry-run-pr:" + digest({"report_id": report["report_id"], "branch": branch})[:12]
    return {
        "status": "candidate_fix_ready",
        "attempts": [{"attempt": 1, "result": "candidate accepted by local fixture"}],
        "branch": branch,
        "pr_ref": pr_ref,
        "external_actions": {"merge": "approval-gated", "deploy": "approval-gated"},
    }


def verify_fix_and_suite(ctx: Mapping[str, Any]) -> Mapping[str, Any]:
    remediation = ctx["dependencies"]["STEP-REMEDIATE"]
    if remediation.get("status") != "candidate_fix_ready":
        return {
            "status": "failed",
            "fixture_result": "not_run",
            "suite_result": "not_run",
            "escalation_reason": remediation.get("escalation_reason", "attempt_budget_exhausted"),
        }
    return {
        "status": "passed",
        "fixture_result": "PASS",
        "suite_result": "PASS",
        "regressions": [],
    }


def independent_review(ctx: Mapping[str, Any]) -> Mapping[str, Any]:
    verification = ctx["dependencies"]["STEP-VERIFY"]
    if verification.get("status") != "passed":
        return {
            "status": "rejected",
            "decision": "REJECT",
            "reason": verification.get("escalation_reason", "verification_failed"),
        }
    return {
        "status": "passed",
        "decision": "PASS",
        "scope_check": "within_bug_scope",
        "reviewer": "code-reviewer",
    }


def resolve_or_escalate(ctx: Mapping[str, Any]) -> Mapping[str, Any]:
    report = _bug_report(ctx)
    review = ctx["dependencies"]["STEP-REVIEW"]
    if review.get("decision") == "PASS":
        remediation = ctx["STEP-REMEDIATE"]
        regression = ctx["STEP-REGRESSION"]
        return {
            "outcome": "resolved",
            "tracking_id": _tracking_id(report),
            "branch": remediation["branch"],
            "pr_ref": remediation["pr_ref"],
            "permanent_fixture": regression["fixture_id"],
            "production_change": "approval-gated",
            "evidence_recorded": True,
        }
    dependencies = ctx.get("dependencies", {})
    reason = review.get("reason") or "attempt_budget_exhausted"
    if reason not in ESCALATION_REASONS:
        reason = "attempt_budget_exhausted"
    return {
        "outcome": "escalated",
        "tracking_id": _tracking_id(report),
        "reason": reason,
        "diagnostic_package": {
            "repro": ctx.get("STEP-REPRODUCE") or dependencies.get("STEP-REPRODUCE"),
            "regression": ctx.get("STEP-REGRESSION") or dependencies.get("STEP-REGRESSION"),
            "diagnosis": ctx.get("STEP-DIAGNOSE") or dependencies.get("STEP-DIAGNOSE"),
            "attempts": ctx.get("STEP-REMEDIATE") or dependencies.get("STEP-REMEDIATE"),
            "recommended_next_action": "maintainer review with reporter follow-up questions",
        },
        "evidence_recorded": True,
    }


def notify_reporter_outcome(ctx: Mapping[str, Any]) -> Mapping[str, Any]:
    report = _bug_report(ctx)
    reporter = _reporter(report)
    resolution = ctx["dependencies"]["STEP-RESOLVE"]
    if resolution["outcome"] == "resolved":
        body = (
            f"Bug report {_tracking_id(report)} is fixed and verified. "
            "The production merge or deploy remains approval-gated."
        )
    else:
        body = (
            f"Bug report {_tracking_id(report)} needs human support. "
            "A person has the diagnostic package and will handle it."
        )
    _scan_outbound(body)
    return {
        "tracking_id": _tracking_id(report),
        "outcome": resolution["outcome"],
        "notification": {
            "to": reporter["contact"],
            "channel": reporter.get("channel", "email"),
            "body": body,
            "sent": True,
            "verified_contact": True,
            "secret_scan": "passed",
        },
    }


BUG_REMEDIATION_HANDLERS = {
    "acknowledge_reporter": acknowledge_reporter,
    "reproduce_in_sandbox": reproduce_in_sandbox,
    "repro_to_failing_fixture": repro_to_failing_fixture,
    "localize_root_cause": localize_root_cause,
    "attempt_fix_loop": attempt_fix_loop,
    "verify_fix_and_suite": verify_fix_and_suite,
    "independent_review": independent_review,
    "resolve_or_escalate": resolve_or_escalate,
    "notify_reporter_outcome": notify_reporter_outcome,
}
