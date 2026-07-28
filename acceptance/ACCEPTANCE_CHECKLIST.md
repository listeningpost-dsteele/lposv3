# LPOS COE Acceptance Checklist

Release: 4.5.0
Evidence audit: `audit-1785254125881-df3403c4b04be3a5`
Exact artifact: `cbb2a62b4bdcce1cec8025db146f99780a42a9bc92bb0f28781f17fb713ce7c9`

Every item is closed only by a command exit, test, evidence hash, API response, external reference, artifact, or deployed URL probe.

- [x] Hardcoded passing security and release objects removed. Evidence: `security-reliability-runtime.test.js` and release endpoint tests.
- [x] Complete staged application manifest generated. Evidence: 492 files, 5,374,732 bytes.
- [x] Missing, changed, unlisted, traversing, duplicate, symlink, mutable, and mode defects fail. Evidence: Python and Node release-manifest negative tests.
- [x] Version convergence proven. Evidence: `npm run release:version-check`, exit 0.
- [x] Nine independently executable gate commands present. Evidence: nine append-only records in the named audit.
- [x] Release controller blocks absent, stale, malformed, skipped, mismatched, or failed evidence. Evidence: controller tests and blocked decision hash `552e1b822dff0454ff1d3f3bda90ea59264f91d5ce728532003ec1ccdb431a24` from the named audit.
- [x] Daily 03:00 Central schedule installed. Evidence: cron job `ce51f7aeb7f1`, next run `2026-07-29T03:00:00-05:00`.
- [x] Audit IDs and history persisted in v4 SQLite. Evidence: `/Users/dan/.hermes/state/chip-service/coe/coe.db` integrity pass.
- [x] Engineering audit covers changed files across the LPOS and Chip repositories. Evidence: engineering gate pass.
- [x] Skill-search efficiency measured. Evidence: `skill.catalog.size` and `skill.catalog.bytes` metrics.
- [x] Actual isolated backup restore performed. Evidence: SQLite copy, `integrity_check`, sentinel verification, and cleanup records.
- [x] Scheduler and wake governance measured. Evidence: scheduler job and deterministic no-model wake metrics.
- [x] Storage trends persisted. Evidence: repository, staged release, state, evidence, report, backup, cache, and duplicate categories.
- [x] Technical-debt and opportunity lifecycles persisted. Evidence: `TD-LEGACY-LPOS-STATE`, append-only decisions, and orphan checks.
- [x] Private dashboard exposes all 18 required fields locally. Evidence: authenticated route tests and unknown/blocked rendering tests.
- [ ] Completion email delivered with dashboard link. Blocker: secure recipient/token configuration and deployment.
- [ ] Documentation pass-off verified on GitHub, wiki, and Google Drive. GitHub and versioned wiki are verified. Google Drive is pending owner-authenticated publication.
- [x] Final artifact rebuilt and dual-verified. Evidence: Node and LPOS verifiers pass the exact artifact hash above.
- [x] Cohesive changes pushed and merged. Evidence: LPOS PRs 3, 4, 5 and Chip PRs 1, 2.
- [ ] Exact artifact deployed through the existing pipeline. Blocker: `gcloud auth login` required.
- [ ] Canonical dashboard authentication and rendering probed after deployment.
- [ ] Post-deploy audit, projection import, report delivery, and provider message ID verified.

Release remains blocked. Unchecked items may not be inferred from implementation intent.