from __future__ import annotations

import json
import os
import socket
import sqlite3
import subprocess
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest import mock

from lpos_engine.adapters import AdapterRegistry, DeterministicModelAdapter, RecordingActionAdapter
from lpos_engine.canonical import canonical_json
from lpos_engine.engine import LPOSRuntime, RuntimeConfig
from lpos_engine.errors import (
    ConcurrencyError,
    IdentityVerificationError,
    PolicyViolation,
    ValidationError,
)
from lpos_engine.models import ActionPlan, ApprovalGrant, MessageIdentity, ReviewEnvelope, TaskStatus
from lpos_engine.sentinel import (
    ActiveEngagementScope,
    SENTINEL_ORGANIZATION_ID,
    SENTINEL_POLICY_VERSION,
    SentinelPolicy,
    SentinelService,
)
from lpos_engine.sentinel.models import SecurityAssessment
from lpos_engine.sentinel.operations import (
    assess_and_adversarially_review_artifacts,
    inventory_unassessed_artifacts,
    report_sentinel_assurance_status,
)
from lpos_engine.sentinel.rules import SentinelScanner

from support import RuntimeTestCase


class SentinelIntegrationTests(RuntimeTestCase):
    def _submit_with_content(self, content: str):
        self.creator.artifact_factory = lambda task, context: content
        task = self.runtime.submit_task(
            "Create a software artifact",
            required_capabilities=("code_generation",),
        )
        artifact = self.runtime.create_artifact(task.task_id)
        return task, artifact

    def test_every_artifact_is_assessed_untrusted_then_independently_reviewed(self) -> None:
        task, artifact = self._submit_with_content("def add(a, b):\n    return a + b\n")
        assessment = self.runtime.store.get_latest_sentinel_assessment(
            task.task_id, artifact.content_hash
        )
        self.assertIsNotNone(assessment)
        self.assertEqual(assessment.trust_state, "untrusted")
        self.assertEqual(assessment.policy_version, SENTINEL_POLICY_VERSION)
        self.assertEqual(assessment.artifact_hash, artifact.content_hash)

        review = self.runtime.store.get_sentinel_review_for_assessment(
            assessment.assessment_id
        )
        self.assertIsNotNone(review)
        self.assertTrue(review.trusted)
        self.assertEqual(review.assessment_hash, assessment.assessment_hash)
        self.assertEqual(review.envelope.artifact["content_hash"], assessment.assessment_hash)
        self.assertNotEqual(review.producer_id, review.reviewer_adapter)
        self.assertTrue(review.context_isolated)
        self.assertIn(
            f"fresh_context:{review.review_context_id}", review.result.isolation
        )
        self.assertTrue(all(review.structural_checks.values()))
        self.assertEqual(review.structural_failures, ())
        self.assertNotIn("# LPOS Creation Context", self.reviewer.last_review_context.content)
        self.assertIn("creator_private_reasoning", self.reviewer.last_review_context.excluded)
        self.assertEqual(self.runtime.store.list_sentinel_reports(task_id=task.task_id), ())

    def test_raw_assessment_cannot_claim_trust(self) -> None:
        task, artifact = self._submit_with_content("safe = True")
        assessment = self.runtime.store.get_latest_sentinel_assessment(
            task.task_id, artifact.content_hash
        )
        with self.assertRaisesRegex(ValidationError, "must remain untrusted"):
            replace(assessment, trust_state="trusted")

    def test_high_findings_are_redacted_reported_with_remediation_and_block_completion(self) -> None:
        secret = "correct-horse-battery-staple"
        content = (
            f'password = "{secret}"\n'
            "import subprocess\n"
            "subprocess.run(user_input, shell=True)\n"
        )
        with (
            mock.patch.object(os, "system") as os_system,
            mock.patch.object(subprocess, "run") as process_run,
            mock.patch.object(socket, "socket") as network_socket,
        ):
            task, artifact = self._submit_with_content(content)
        os_system.assert_not_called()
        process_run.assert_not_called()
        network_socket.assert_not_called()

        assessment = self.runtime.store.get_latest_sentinel_assessment(
            task.task_id, artifact.content_hash
        )
        self.assertEqual({item.rule_id for item in assessment.findings}, {"SENT-002", "SENT-003"})
        self.assertTrue(all(item.blocking for item in assessment.findings))

        records = self.runtime.store.list_sentinel_reports(task_id=task.task_id)
        self.assertEqual(len(records), 1)
        report = records[0]["report"]
        self.assertEqual(report.overall, "attention_required")
        self.assertEqual(report.destination, "principal_security_inbox")
        self.assertEqual(len(report.findings), 2)
        self.assertNotIn(secret, canonical_json(report))
        for finding in report.findings:
            self.assertTrue(finding.rule_id.startswith("SENT-"))
            self.assertTrue(finding.category)
            self.assertGreater(finding.confidence, 0)
            self.assertEqual(len(finding.fingerprint), 64)
            self.assertTrue(finding.evidence)
            self.assertTrue(finding.remediation_steps)
            self.assertTrue(finding.verification_steps)
        secret_finding = next(item for item in report.findings if item.rule_id == "SENT-002")
        self.assertIn("[REDACTED]", secret_finding.evidence[0].redacted_excerpt)

        with self.assertRaisesRegex(PolicyViolation, "Sentinel finding"):
            self.runtime.complete_task(task.task_id, result_summary="unsafe work")
        self.assertEqual(
            self.runtime.store.get_task(task.task_id)["status"],
            TaskStatus.CORRECTION_REQUIRED,
        )

    def test_medium_finding_is_advisory_under_default_policy(self) -> None:
        task, artifact = self._submit_with_content("digest = hashlib.md5(payload).hexdigest()")
        assessment = self.runtime.store.get_latest_sentinel_assessment(
            task.task_id, artifact.content_hash
        )
        self.assertEqual(len(assessment.findings), 1)
        self.assertEqual(assessment.findings[0].severity, "medium")
        self.assertFalse(assessment.findings[0].blocking)
        report = self.runtime.complete_task(task.task_id, result_summary="advisory accepted")
        self.assertEqual(report.status, TaskStatus.COMPLETED)

    def test_corrected_revision_receives_a_new_assessment_before_completion(self) -> None:
        task, first = self._submit_with_content('password = "unsafe-password"')
        with self.assertRaises(PolicyViolation):
            self.runtime.complete_task(task.task_id, result_summary="first attempt")
        first_assessment = self.runtime.store.get_latest_sentinel_assessment(
            task.task_id, first.content_hash
        )

        self.creator.artifact_factory = lambda task, context: "secret = os.environ['APP_SECRET']"
        second = self.runtime.create_artifact(task.task_id)
        self.assertNotEqual(first.content_hash, second.content_hash)
        second_assessment = self.runtime.store.get_latest_sentinel_assessment(
            task.task_id, second.content_hash
        )
        self.assertNotEqual(first_assessment.assessment_id, second_assessment.assessment_id)
        self.assertEqual(second_assessment.status, "clean")
        second_review = self.runtime.store.get_sentinel_review_for_assessment(
            second_assessment.assessment_id
        )
        self.assertTrue(second_review.trusted)
        self.runtime.complete_task(task.task_id, result_summary="corrected")
        self.assertEqual(
            self.runtime.store.get_task(task.task_id)["status"], TaskStatus.COMPLETED
        )

    def test_report_acknowledgement_is_separate_append_only_and_not_self_service(self) -> None:
        task, _ = self._submit_with_content('password = "unsafe-password"')
        report = self.runtime.store.list_sentinel_reports(task_id=task.task_id)[0]["report"]
        with self.assertRaisesRegex(ValidationError, "may not acknowledge"):
            self.runtime.sentinel.acknowledge_report(
                report.report_id,
                acknowledged_by=SENTINEL_ORGANIZATION_ID,
                note="self-approved",
            )
        acknowledgement = self.runtime.sentinel.acknowledge_report(
            report.report_id,
            acknowledged_by="principal@example.com",
            note="Remediation task opened; acknowledgement is not closure.",
        )
        record = self.runtime.store.get_sentinel_report(report.report_id)
        self.assertEqual(record["acknowledgement"].acknowledgement_id, acknowledgement.acknowledgement_id)
        with self.assertRaises(ConcurrencyError):
            self.runtime.sentinel.acknowledge_report(
                report.report_id,
                acknowledged_by="principal@example.com",
                note="second acknowledgement",
            )

        tables = (
            "sentinel_assessments",
            "sentinel_assessment_reviews",
            "sentinel_reports",
            "sentinel_report_acknowledgements",
        )
        for table in tables:
            with self.subTest(table=table), self.runtime.store.connection() as conn:
                with self.assertRaises(sqlite3.DatabaseError):
                    conn.execute(f"UPDATE {table} SET created_at = created_at")
                with self.assertRaises(sqlite3.DatabaseError):
                    conn.execute(f"DELETE FROM {table}")

    def test_forged_review_hash_cannot_be_saved(self) -> None:
        task, artifact = self._submit_with_content("safe = True")
        assessment = self.runtime.store.get_latest_sentinel_assessment(
            task.task_id, artifact.content_hash
        )
        review = self.runtime.store.get_sentinel_review_for_assessment(assessment.assessment_id)
        envelope_data = review.envelope.to_dict()
        envelope_data["artifact"]["content_hash"] = "0" * 64
        forged = replace(
            review,
            review_id="SREV-FORGED-HASH",
            assessment_hash="0" * 64,
            envelope=ReviewEnvelope.from_dict(envelope_data),
        )
        with self.assertRaisesRegex(ValidationError, "persisted assessment"):
            self.runtime.store.save_sentinel_review(forged)

    def test_malformed_structural_failure_claim_is_rejected(self) -> None:
        task, artifact = self._submit_with_content("safe = True")
        assessment = self.runtime.store.get_latest_sentinel_assessment(
            task.task_id, artifact.content_hash
        )
        review = self.runtime.store.get_sentinel_review_for_assessment(assessment.assessment_id)
        checks = dict(review.structural_checks)
        checks["findings_reproducible"] = False
        with self.assertRaisesRegex(ValidationError, "failure list"):
            replace(review, structural_checks=checks, structural_failures=())

    def test_enabled_policy_cannot_disable_independent_review(self) -> None:
        with self.assertRaisesRegex(ValidationError, "may not bypass"):
            SentinelPolicy(enabled=True, require_trusted_review=False)
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "may not bypass"):
                RuntimeConfig(
                    database_path=Path(directory) / "state.db",
                    sentinel_enabled=True,
                    sentinel_require_trusted_review=False,
                )

    def test_active_probe_requires_exact_principal_approval_and_isolated_scope(self) -> None:
        task = self.runtime.submit_task(
            "Authorize a scoped isolated adversarial test",
            required_capabilities=("code_generation",),
        )
        with self.assertRaisesRegex(ValidationError, "dedicated isolated environment"):
            ActiveEngagementScope(
                engagement_id="ENG-ACTIVE-001",
                task_id=task.task_id,
                target_owner="Principal",
                targets=("test.example.internal",),
                excluded_assets=("all production systems",),
                allowed_methods=("authenticated application testing",),
                isolated_environment="production",
                network_boundary="deny-by-default egress",
                data_handling="Synthetic test data only; no retained credentials.",
                stop_conditions=("Stop on any instability or scope ambiguity.",),
                rollback_plan="Destroy the disposable environment and restore the clean snapshot.",
                window_start="2026-07-22T00:00:00Z",
                window_end="2026-07-22T23:59:59Z",
            )

        scope = ActiveEngagementScope(
            engagement_id="ENG-ACTIVE-001",
            task_id=task.task_id,
            target_owner="Principal",
            targets=("test.example.internal",),
            excluded_assets=("all production systems",),
            allowed_methods=("authenticated application testing", "read-only validation"),
            isolated_environment="disposable isolated test environment",
            network_boundary="deny-by-default egress allowlist",
            data_handling="Synthetic test data only; no retained credentials.",
            stop_conditions=("Stop on any instability or scope ambiguity.",),
            rollback_plan="Destroy the disposable environment and restore the clean snapshot.",
            window_start="2026-07-22T00:00:00Z",
            window_end="2026-07-22T23:59:59Z",
        )
        service = SentinelService(
            self.runtime.store,
            self.runtime.adapters,
            self.runtime.context_compiler,
            policy=SentinelPolicy(passive_only=False),
            approval_service=self.runtime.approvals,
        )
        with self.assertRaisesRegex(PolicyViolation, "exact-action plan"):
            service.assert_active_engagement_authorized(
                scope, plan=None, grant=None, checked_at="2026-07-22T12:00:00Z"
            )

        forged_plan = ActionPlan.create(
            action_id="ACTION-FORGED-ACTIVE-001",
            task_id=scope.task_id,
            kind="sentinel_active_penetration_test",
            parameters={
                "engagement_id": scope.engagement_id,
                "engagement_scope_hash": scope.scope_hash,
                "isolated_environment": scope.isolated_environment,
            },
            external=True,
            reversible=False,
            idempotency_key="sentinel-active:forged:ENG-ACTIVE-001",
        )
        with self.assertRaisesRegex(PolicyViolation, "ordinary LPOS action ledger"):
            service.assert_active_engagement_authorized(
                scope, plan=forged_plan, grant=None, checked_at="2026-07-22T12:00:00Z"
            )

        plan, request = self.runtime.plan_action(
            scope.task_id,
            kind="sentinel_active_penetration_test",
            parameters={
                "engagement_id": scope.engagement_id,
                "engagement_scope_hash": scope.scope_hash,
                "isolated_environment": scope.isolated_environment,
            },
            external=True,
            reversible=False,
            idempotency_key="sentinel-active:ENG-ACTIVE-001",
        )
        self.assertIsNotNone(request)
        grant = self.runtime.grant_action_approval(
            request.question_id,
            message_identity=MessageIdentity(
                channel="email",
                provider="verified-connector",
                message_id="MSG-ACTIVE-001",
                thread_id=request.question_id,
                sender="principal@example.com",
            ),
            verified_identity="principal@example.com",
        )
        self.assertEqual(
            service.assert_active_engagement_authorized(
                scope, plan=plan, grant=grant, checked_at="2026-07-22T12:00:00Z"
            ),
            scope.scope_hash,
        )
        with self.assertRaisesRegex(PolicyViolation, "differs from the persisted grant"):
            service.assert_active_engagement_authorized(
                scope,
                plan=plan,
                grant=replace(grant, verified_identity="forged@example.com"),
                checked_at="2026-07-22T12:00:00Z",
            )

        self.runtime.identity_verifier.add("email", SENTINEL_ORGANIZATION_ID)
        self_task = self.runtime.submit_task(
            "Attempt a Sentinel self-approved active engagement",
            required_capabilities=("code_generation",),
        )
        self_scope = replace(
            scope,
            engagement_id="ENG-ACTIVE-SELF-001",
            task_id=self_task.task_id,
        )
        self_plan, self_request = self.runtime.plan_action(
            self_scope.task_id,
            kind="sentinel_active_penetration_test",
            parameters={
                "engagement_id": self_scope.engagement_id,
                "engagement_scope_hash": self_scope.scope_hash,
                "isolated_environment": self_scope.isolated_environment,
            },
            external=True,
            reversible=False,
            idempotency_key="sentinel-active:ENG-ACTIVE-SELF-001",
        )
        self_grant = self.runtime.grant_action_approval(
            self_request.question_id,
            message_identity=MessageIdentity(
                channel="email",
                provider="verified-connector",
                message_id="MSG-ACTIVE-SELF-001",
                thread_id=self_request.question_id,
                sender=SENTINEL_ORGANIZATION_ID,
            ),
            verified_identity=SENTINEL_ORGANIZATION_ID,
        )
        with self.assertRaisesRegex(PolicyViolation, "may not approve"):
            service.assert_active_engagement_authorized(
                self_scope,
                plan=self_plan,
                grant=self_grant,
                checked_at="2026-07-22T12:00:00Z",
            )

    def test_sentinel_record_tampering_is_detected_by_the_hash_chain(self) -> None:
        """Improvement 3a: Sentinel's own record tables are anchored to the
        4.2.1 tamper-evident event chain.  Dropping the append-only triggers and
        editing a stored assessment row is DETECTED, and flipping a review's
        trust decision 0->1 diverges from the hash-chained event."""
        task, artifact = self._submit_with_content('password = "unsafe-password"')
        # Baseline: records reconcile with the chain.
        self.assertEqual(self.runtime.store.integrity_check(), "ok")
        self.assertTrue(self.runtime.store.verify_sentinel_records()["ok"])

        # An operator drops the append-only guard and rewrites a stored assessment.
        with self.runtime.store.connection() as conn:
            conn.execute("DROP TRIGGER sentinel_assessments_no_update")
            conn.execute(
                "UPDATE sentinel_assessments SET assessment_json = "
                "json_set(assessment_json, '$.status', 'clean')"
            )
            conn.commit()
        result = self.runtime.store.verify_sentinel_records()
        self.assertFalse(result["ok"])
        self.assertIsNotNone(result["first_bad"])
        self.assertNotEqual(self.runtime.store.integrity_check(), "ok")
        self.assertIn("sentinel records tampered", self.runtime.store.integrity_check())

    def test_sentinel_review_trust_flip_is_detected(self) -> None:
        """Improvement 3a: flipping a persisted review's ``trusted`` flag away
        from the hash-chained decision is detected even if the row's own
        recomputed hash is left consistent."""
        task, artifact = self._submit_with_content("safe = True")
        assessment = self.runtime.store.get_latest_sentinel_assessment(
            task.task_id, artifact.content_hash
        )
        review = self.runtime.store.get_sentinel_review_for_assessment(assessment.assessment_id)
        self.assertTrue(review.trusted)
        with self.runtime.store.connection() as conn:
            conn.execute("DROP TRIGGER sentinel_assessment_reviews_no_update")
            # Flip only the indexed trust column; the JSON/hash stay internally
            # consistent, but the chained review event still records trusted=1.
            conn.execute(
                "UPDATE sentinel_assessment_reviews SET trusted = 0 WHERE review_id = ?",
                (review.review_id,),
            )
            conn.commit()
        result = self.runtime.store.verify_sentinel_records()
        self.assertFalse(result["ok"])
        self.assertEqual(result["first_bad"], review.review_id)

    def test_fabricated_identity_without_registered_channel_cannot_authorize_active_engagement(self) -> None:
        """Improvement 3b: the active-engagement gate goes through the 4.2.1
        verified-channel assertion path, so a caller-built MessageIdentity whose
        provider has no registered channel verifier cannot mint an approval grant
        and therefore cannot authorize a Sentinel active engagement."""
        task = self.runtime.submit_task(
            "Authorize a scoped isolated adversarial test",
            required_capabilities=("code_generation",),
        )
        scope = ActiveEngagementScope(
            engagement_id="ENG-ACTIVE-FORGED-CHANNEL",
            task_id=task.task_id,
            target_owner="Principal",
            targets=("test.example.internal",),
            excluded_assets=("all production systems",),
            allowed_methods=("authenticated application testing", "read-only validation"),
            isolated_environment="disposable isolated test environment",
            network_boundary="deny-by-default egress allowlist",
            data_handling="Synthetic test data only; no retained credentials.",
            stop_conditions=("Stop on any instability or scope ambiguity.",),
            rollback_plan="Destroy the disposable environment and restore the clean snapshot.",
            window_start="2026-07-22T00:00:00Z",
            window_end="2026-07-22T23:59:59Z",
        )
        service = SentinelService(
            self.runtime.store,
            self.runtime.adapters,
            self.runtime.context_compiler,
            policy=SentinelPolicy(passive_only=False),
            approval_service=self.runtime.approvals,
        )
        plan, request = self.runtime.plan_action(
            scope.task_id,
            kind="sentinel_active_penetration_test",
            parameters={
                "engagement_id": scope.engagement_id,
                "engagement_scope_hash": scope.scope_hash,
                "isolated_environment": scope.isolated_environment,
            },
            external=True,
            reversible=False,
            idempotency_key="sentinel-active:ENG-ACTIVE-FORGED-CHANNEL",
        )
        # A fabricated MessageIdentity on an UNREGISTERED provider is not evidence
        # of authenticity: the verified-channel registry refuses to mint a grant.
        with self.assertRaisesRegex(IdentityVerificationError, "no channel verifier is registered"):
            self.runtime.grant_action_approval(
                request.question_id,
                message_identity=MessageIdentity(
                    channel="email",
                    provider="totally-unregistered-connector",
                    message_id="MSG-FORGED-CHANNEL-001",
                    thread_id=request.question_id,
                    sender="principal@example.com",
                ),
                verified_identity="principal@example.com",
            )
        # With no minted grant the action never reaches the approved state, so the
        # active-engagement gate fails closed rather than trusting the forged identity.
        with self.assertRaisesRegex(PolicyViolation, "approved state"):
            service.assert_active_engagement_authorized(
                scope, plan=plan, grant=None, checked_at="2026-07-22T12:00:00Z"
            )


class SentinelAdversarialFailureTests(unittest.TestCase):
    def _artifact_without_sentinel(self, directory: str, adapters: AdapterRegistry):
        runtime = LPOSRuntime(
            RuntimeConfig(database_path=Path(directory) / "state.db", sentinel_enabled=False),
            adapters=adapters,
        )
        task = runtime.submit_task(
            "Create an artifact",
            required_capabilities=("code_generation",),
        )
        artifact = runtime.create_artifact(task.task_id)
        return runtime, task, artifact

    def test_sentinel_named_adapter_cannot_review_sentinel_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            sentinel_adapter = DeterministicModelAdapter("sentinel-static-analyzer")
            adapters = AdapterRegistry(
                model_adapters=(sentinel_adapter,),
                action_adapters=(RecordingActionAdapter(),),
            )
            runtime, task, artifact = self._artifact_without_sentinel(directory, adapters)
            service = SentinelService(runtime.store, adapters, runtime.context_compiler)
            assessment, review, report = service.assess_and_review(artifact)
            self.assertFalse(review.trusted)
            self.assertEqual(review.result.decision.value, "REJECT")
            self.assertIsNone(sentinel_adapter.last_review_context)
            self.assertEqual(report.overall, "assurance_failure")
            self.assertEqual(report.findings, ())
            self.assertTrue(all(value == 0 for value in report.counts.values()))
            with self.assertRaisesRegex(PolicyViolation, "independent adversarial review"):
                service.assert_can_complete(task.task_id, artifact.content_hash)
            self.assertEqual(assessment.trust_state, "untrusted")

    def test_rejected_review_never_exposes_raw_findings_as_fact(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            creator = DeterministicModelAdapter(
                "creator",
                artifact_factory=lambda task, context: 'password = "unsafe-password"',
                priority=10,
            )
            reviewer = DeterministicModelAdapter(
                "reviewer",
                supports_creation=False,
                reject_markers=("sentinel-static-analyzer",),
                priority=0,
            )
            adapters = AdapterRegistry(
                model_adapters=(creator, reviewer),
                action_adapters=(RecordingActionAdapter(),),
            )
            runtime, task, artifact = self._artifact_without_sentinel(directory, adapters)
            service = SentinelService(runtime.store, adapters, runtime.context_compiler)
            assessment, review, report = service.assess_and_review(artifact)
            self.assertTrue(assessment.findings)
            self.assertFalse(review.trusted)
            self.assertEqual(report.overall, "assurance_failure")
            self.assertEqual(report.findings, ())
            self.assertNotIn("unsafe-password", canonical_json(report))
            self.assertIn("being presented as fact", report.summary)

    def test_deterministic_rescan_mismatch_overrides_model_pass(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            creator = DeterministicModelAdapter("creator", priority=10)
            reviewer = DeterministicModelAdapter(
                "reviewer", supports_creation=False, priority=0
            )
            adapters = AdapterRegistry(
                model_adapters=(creator, reviewer),
                action_adapters=(RecordingActionAdapter(),),
            )
            runtime, _, artifact = self._artifact_without_sentinel(directory, adapters)
            service = SentinelService(runtime.store, adapters, runtime.context_compiler)
            assessment = service.assess_artifact(artifact)
            # Return a different but internally valid scan result to prove that a model PASS
            # cannot override deterministic reproduction failure.
            mismatched = replace(assessment, status="error", checked_rules=(), findings=())
            with mock.patch.object(service.scanner, "scan_artifact", return_value=mismatched):
                review = service.review_assessment(assessment)
            self.assertEqual(review.result.decision.value, "PASS")
            self.assertFalse(review.structural_checks["findings_reproducible"])
            self.assertIn("findings_reproducible", review.structural_failures)
            self.assertFalse(review.trusted)
            _, persisted_review, report = service.assess_and_review(artifact)
            self.assertEqual(persisted_review.review_id, review.review_id)
            self.assertEqual(report.overall, "assurance_failure")
            self.assertEqual(report.findings, ())

    def test_standing_operation_catches_artifact_missed_by_event_hook(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "state.db"
            runtime = LPOSRuntime.local(
                RuntimeConfig(database_path=database, sentinel_enabled=False)
            )
            task = runtime.submit_task(
                "Create a clean note",
                required_capabilities=("writing",),
            )
            artifact = runtime.create_artifact(task.task_id)
            context = {"database_path": str(database)}
            inventory = inventory_unassessed_artifacts(context)
            self.assertEqual(inventory["count"], 1)
            self.assertEqual(inventory["artifacts"][0]["artifact_hash"], artifact.content_hash)
            execution = assess_and_adversarially_review_artifacts(context)
            self.assertEqual(execution["processed"], 1)
            self.assertEqual(execution["trusted"], 1)
            self.assertFalse(execution["external_side_effects"])
            self.assertEqual(inventory_unassessed_artifacts(context)["count"], 0)
            status = report_sentinel_assurance_status(context)
            self.assertEqual(status["assessments"], 1)
            self.assertEqual(status["trusted_reviews"], 1)
            self.assertFalse(status["raw_guild_findings_exposed"])


class SentinelConstitutionAndDistributionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path(__file__).resolve().parents[1]

    def test_constitution_and_patch_require_no_guild_trust(self) -> None:
        constitution = (
            self.root / "src" / "lpos_engine" / "spec" / "LPOS-CORE.md"
        ).read_text(encoding="utf-8")
        patch = (self.root / "patch.md").read_text(encoding="utf-8")
        kernel = (
            self.root / "src" / "lpos_engine" / "spec" / "CHIP-KERNEL.md"
        ).read_text(encoding="utf-8")
        normalized_constitution = " ".join(constitution.split())
        for phrase in (
            "Article VIII. Institutional Skepticism and Independent Adversarial Review",
            "New organizational output begins in an **untrusted** state.",
            "may not approve, certify, publish, enforce, remediate, or close its own work",
            "fresh-context",
        ):
            self.assertIn(phrase, normalized_constitution)
        self.assertIn("No guild, specialist, agent, model, provider, or new organization is trusted", " ".join(kernel.split()))
        self.assertIn("## 18. Constitutional amendment and Sentinel Adversarial Assurance", patch)
        self.assertIn("ordinary LPOS adversarial process", patch)
        self.assertIn("Google Drive", patch)
        self.assertIn("GitHub", patch)
        self.assertIn("Wiki", patch)
        self.assertIn("Next full build", patch)
        self.assertIn("does **not** close\nLPOS-01 through LPOS-14", patch)

    def test_registry_charter_and_workflow_define_separate_organization(self) -> None:
        registry = json.loads(
            (self.root / "src" / "lpos_engine" / "config" / "default_registry.json").read_text()
        )
        specialist = next(
            item for item in registry["specialists"] if item["specialist_id"] == "SPECIALIST-033"
        )
        self.assertEqual(specialist["guild"], "Sentinel Adversarial Assurance")
        self.assertIn("adversarial_testing", specialist["capabilities"])
        workflow = json.loads(
            (self.root / "src" / "lpos_engine" / "workflows" / "SO-026.json").read_text()
        )
        self.assertEqual(workflow["so_id"], "SO-026")
        catalog = json.loads(
            (self.root / "src" / "lpos_engine" / "workflows" / "catalog.json").read_text()
        )
        entry = next(item for item in catalog["operations"] if item["so_id"] == "SO-026")
        self.assertEqual(entry["title"], "Continuous Adversarial Assurance")
        self.assertTrue(entry["enabled_by_default"])
        charter = (self.root / "src" / "lpos_engine" / "spec" / "STANDING-OPERATIONS.md").read_text()
        self.assertIn("SPECIALIST-033", charter[charter.index("SO-026"):])
        docs = (self.root / "docs" / "SENTINEL.md").read_text()
        self.assertIn("passive", docs.casefold())
        self.assertIn("separate", docs.casefold())
        self.assertIn("does not make it trusted", " ".join(docs.casefold().split()))


if __name__ == "__main__":
    unittest.main()
