# HERMES IMPLEMENTATION ORDER
# Implement and Ship LPOS Continuous Operational Excellence (COE)

**Document status:** Approved implementation order
**Target:** `chip-service` / LPOS v4.5.0 and all later LPOS releases
**Canonical repository:** `/Users/dan/lpos45` unless the deployed `chip-service` repository is located elsewhere
**Starting branch:** `release/4.5.0`
**Required starting commit:** preserve `96e99b28b6b08d7b6d35c0415b3a386c35a8b3a4` if it is present in the applicable repository history
**Canonical dashboard URL:** `https://chip.listeningpost.ai/dashboard/coe`
**Daily schedule:** `03:00 America/Chicago`
**Authority:** Dan has approved implementation, testing, documentation, commit, push, deployment, and verified report delivery for this work. Destructive migration of legacy ledgers and deletion of unrelated data are not approved.

---

## 0. This document replaces the earlier COE documents

This is the authoritative implementation order. It supersedes all earlier COE patches, addenda, outlines, generated checklists, and recommendation-only documents.

Do not respond with another proposal, list of recommendations, or a request to split this work into more documents. Implement the system, validate it independently, ship it through the existing deployment path, and return the evidence and live dashboard link specified in the final-response contract.

The previous audit found that the existing release process could self-attest, that application release integrity was not actually verified, that release versions drifted, that six required gates did not exist, and that the COE dashboard, audit history, report delivery, backup verification, scheduler governance, storage trends, technical-debt lifecycle, and pass-off evidence were missing. Every one of those findings is a required deliverable below.

The primary defect is **assurance bloat and drift**, not tracked repository size. The implementation must make release claims provable rather than adding more descriptive policy around unverified claims.

---

## 1. Required execution behavior

Before changing files, tell Dan what will happen in a compact execution briefing. Do not wait for acknowledgment unless a genuinely destructive or credential-sensitive action falls outside the authority above.

Use this format:

```text
Implementation briefing
Goal: Implement and ship the LPOS COE subsystem.
Workstreams: evidence and release gates; immutable release verification; daily audit; code and process audits; dashboard; email; documentation; deployment verification.
Systems touched: source repository, LPOS state database, scheduler, private operator UI, email transport, release pipeline, documentation surfaces.
Safety boundaries: preserve unrelated work; no force push; no destructive legacy-ledger migration; no secrets in evidence or reports.
Completion proof: nine independent gates, deployed private dashboard, successful 03:00 schedule configuration, delivered test report, commit/push/deployment references, and a verified live dashboard URL.
```

Then begin. During long work, report only meaningful milestones and discovered blockers. Do not narrate every file read or command run.

For all future non-trivial Hermes tasks, add the same behavioral rule to the operating system:

1. State the goal and planned workstreams before execution.
2. State systems that will be touched and whether approval is needed.
3. Begin immediately when existing policy or the request already grants approval.
4. Provide milestone updates for long work.
5. Never claim completion without output or verification evidence.
6. Do not provide an elapsed-time promise or ask the operator to wait.

A task is non-trivial when it writes files, calls external services, modifies infrastructure, uses multiple tools, invokes agents, or is expected to require more than one meaningful execution stage.

---

## 2. Preserve the current system before editing

The audit reported preexisting modified, deleted, and untracked entries. Do not clean, reset, overwrite, or absorb unrelated changes into this implementation.

### 2.1 Repository isolation

1. Identify the actual source repository that serves `chip.listeningpost.ai`.
2. Record its absolute path, current branch, HEAD, remotes, and `git status --porcelain=v2` in the implementation evidence.
3. Confirm whether commit `96e99b28b6b08d7b6d35c0415b3a386c35a8b3a4` belongs to this repository and is an ancestor of the chosen starting point.
4. Create an isolated Git worktree from the current intended release HEAD. Preferred branch name: `feature/coe-v1`.
5. Do not use `git reset --hard`, `git clean`, force push, or destructive stash operations.
6. If the working directory is clean and repository policy explicitly requires in-place release work, a worktree is still preferred.
7. Capture a baseline archive or patch of all preexisting local changes without including credentials.

### 2.2 Baseline evidence

Before implementation, run and retain command-backed evidence for:

- Node and npm versions.
- Current Git commit and status.
- `npm run check`.
- `npm run test`.
- An isolated `npm run build` using a temporary output directory.
- Current `/api/v1/operator/release-gate` response.
- Current release/version values from `package.json`, generated status, API client, shells, and release metadata.
- Current scheduler inventory.
- Current state and build output paths.
- Current documentation manifest verification.

The baseline audit ID must be linked to the implementation audit so before-and-after changes are reconstructable.

---

## 3. Definition of the shipped outcome

The work is complete only when all of the following are true:

1. No release result is constructed as passing in application code.
2. Nine required release gates execute independent commands and emit schema-valid, append-only evidence.
3. Missing, stale, malformed, skipped, mismatched, or failed evidence blocks release.
4. A complete immutable application release manifest is generated from the final staged artifact and verified fail-closed.
5. The verifier rejects missing files, unlisted files, changed files, symlink escapes, mutable paths, version drift, and mismatched provenance.
6. One release identity controls package, API, build, shell, dashboard, report, and artifact metadata.
7. The daily COE audit is persisted and scheduled for `03:00 America/Chicago` with overlap protection and deterministic daily idempotency.
8. Every code file changed since the previous audit is reviewed explicitly.
9. Process efficiency, skill-search efficiency, organizational bloat, scheduler governance, wake-agent efficiency, backup restore evidence, storage trends, documentation drift, opportunity backlog, and technical-debt lifecycle are implemented.
10. `/dashboard/coe` is private, deployed, and shows all required fields from authoritative data.
11. `/ops/coe` redirects to `/dashboard/coe`.
12. The daily email contains a verified dashboard link and delivery evidence.
13. The COE specification and pass-off are committed to the repository and verified on all required documentation surfaces.
14. The application shipping artifact is rebuilt after all source changes.
15. The final release decision is generated only by aggregating current independent gate evidence.
16. The deployment is probed after release, including authentication, API contract, dashboard rendering, report generation, and release identity.
17. Dan receives a final response containing the clickable, successfully probed dashboard URL.

A passing test suite by itself does not satisfy this definition.

---

## 4. Non-negotiable assurance rules

These rules must be encoded as tests and release checks, not left only in documentation.

### 4.1 No self-attestation

- Delete or replace the preset pass objects in `src/security-reliability-runtime.js`.
- No production module may initialize a release, security, isolation, failure-injection, backup, restore, or disaster-recovery check as `pass` without executing the check or consuming independently generated evidence.
- Test fixtures may use synthetic evidence only inside test scope and must be visibly marked `fixture`.
- Tests must verify failure behavior, not only preset success behavior.

### 4.2 Fail closed

The release state is `blocked` unless all required evidence exists and validates. In particular:

- Missing evidence = blocked.
- Stale evidence = blocked.
- `skipped` = blocked for required gates.
- Command timeout = blocked.
- Unknown status = blocked.
- Version mismatch = blocked.
- Commit mismatch = blocked.
- Artifact mismatch = blocked.
- Invalid schema = blocked.
- Evidence hash-chain failure = blocked.
- Open critical finding = blocked.
- Required documentation pass-off not verified = blocked.

### 4.3 Evidence separation

- A gate command determines its own outcome from performed checks.
- The gate runner records process facts and validates the evidence schema.
- The release controller aggregates already produced evidence.
- The release controller must not invent checks, turn missing checks into pass, or substitute a default packet.
- The endpoint renders the release decision; it does not generate or mutate it.

### 4.4 Immutable versus mutable data

- Immutable application releases contain only release files enumerated by the release manifest.
- Runtime state, audit history, status, caches, generated reports, job history, and mutable dashboards must be outside the immutable release root.
- Default local state root: `${HERMES_STATE_DIR:-$HOME/.hermes/state}/chip-service`.
- Production state root must be explicitly configured and writable without changing the release tree.
- CI work and build staging must use a temporary directory or a dedicated ignored output directory, never source-controlled runtime files.

### 4.5 Unknown is not green

When a metric cannot be measured, render `unknown` with a reason. Do not display 100, healthy, complete, or passed.

---

## 5. Target architecture

Implement the following components. Names may follow repository conventions, but the responsibilities and interfaces are mandatory.

### 5.1 Release Identity Service

Reads the single authoritative release identity and validates all mirrors. It exposes the identity to build scripts, server routes, reports, dashboard APIs, release manifests, and gate evidence.

### 5.2 Gate Runner

Executes required commands with `spawn`/equivalent using `shell: false`, explicit arguments, explicit environment, timeout, output limits, and redaction. It validates each gate’s JSON result and writes append-only evidence.

### 5.3 Evidence Store

Persists audits, gates, findings, metrics, decisions, report deliveries, artifacts, and hash-chain metadata in v4 SQLite state. Evidence records are insert-only. Store large logs as files outside the release tree and record their hashes and paths.

### 5.4 COE Audit Orchestrator

Creates an audit ID, establishes the source/release scope, acquires a lock, runs collectors and gates, calculates transparent scores, creates findings/opportunities, renders reports, triggers email, and releases the lock.

### 5.5 Collectors

Implement collectors for:

- Source and release identity.
- Code changes and engineering quality.
- Security and reliability.
- Documentation drift.
- Repository and storage bloat.
- Scheduler inventory and run history.
- Model wake decisions and cost.
- Skill catalog/search/install efficiency.
- Backups and restore tests.
- Persistent artifact lifecycle.
- Technical debt.
- Opportunities and realized value.
- COE’s own runtime, cost, false-positive rate, and duplicate work.

### 5.6 Release Controller

Reads a complete evidence set for one audit ID and one release identity. Produces a signed or hash-addressed decision record. It never executes audits and never fills gaps with defaults.

### 5.7 Private COE API and Dashboard

Serves authenticated, privacy-safe operational data. The dashboard is a view over persisted evidence, not a separate source of truth.

### 5.8 Report Renderer and Delivery Adapter

Creates a text/HTML report from the persisted audit record and sends it through the configured operator email transport. It records provider message ID, attempts, final status, and dashboard URL.

### 5.9 Daily Scheduler

Runs at 03:00 Central, creates an idempotency key for the Central calendar date, prevents overlap, retries safely, and records scheduling/wake decisions.

---

## 6. Recommended repository layout

Adapt only where existing repository conventions require it. Keep equivalent separation.

```text
config/
  coe-gates.json
  coe-policy.json
  backup-policy.json
  artifact-lifecycle.json
  prompt-drift-allowlist.json

db/migrations/
  <next>_coe.sql

release/
  release.json
  manifest-policy.json

scripts/
  coe-run.js
  coe-run-gate.js
  coe-release-decision.js
  generate-release-manifest.js
  verify-release.js
  check-release-version.js
  coe-doctor.js
  coe-engineering-audit.js
  coe-security-audit.js
  coe-documentation-audit.js
  coe-bloat-audit.js
  coe-opportunity-audit.js
  coe-release-integrity-audit.js
  coe-send-report.js

src/coe/
  config.js
  identity.js
  canonical-json.js
  redaction.js
  evidence-store.js
  gate-runner.js
  release-controller.js
  audit-orchestrator.js
  scheduler.js
  scoring.js
  report-renderer.js
  report-delivery.js
  routes.js
  dashboard-view-model.js
  collectors/
    code.js
    process.js
    skills.js
    scheduler.js
    wakes.js
    backup.js
    storage.js
    artifacts.js
    documentation.js
    technical-debt.js
    opportunities.js
    coe-self.js

views or public application source/
  dashboard/coe/*

tests/coe/
  identity.test.js
  release-manifest.test.js
  release-verifier.test.js
  gate-runner.test.js
  release-controller.test.js
  audit-orchestrator.test.js
  scheduler.test.js
  dashboard-api.test.js
  dashboard-page.test.js
  report-delivery.test.js
  backup-restore.test.js
  engineering-audit.test.js
  bloat-audit.test.js
  prompt-drift.test.js
  skill-efficiency.test.js
  failure-injection.test.js

docs/architecture/coe/
  README.md
  DATA_MODEL.md
  RELEASE_ASSURANCE.md
  OPERATIONS.md
  DASHBOARD.md
  SECURITY.md

docs/passoff/
  LPOS-v4.5.0-COE.md
```

Do not write daily status, generated audit JSON, mutable asset copies, or report output into these source directories.

---

## 7. Configuration contract

Add source-controlled policy and environment-backed deployment settings. Validate all production-required settings in Doctor.

### 7.1 Required environment settings

```text
COE_ENABLED=true
COE_SCHEDULE_ENABLED=true
COE_DASHBOARD_ENABLED=true
COE_EMAIL_ENABLED=true
COE_TIMEZONE=America/Chicago
COE_CRON=0 3 * * *
COE_STATE_DIR=<outside immutable release root>
COE_REPORT_RECIPIENT=<Dan's configured operator email>
PUBLIC_BASE_URL=https://chip.listeningpost.ai
COE_DASHBOARD_PATH=/dashboard/coe
COE_GATE_TIMEOUT_MS=1800000
COE_AUDIT_MAX_RUNTIME_MS=7200000
COE_EVIDENCE_RETENTION_DAYS=365
COE_REPORT_RETENTION_DAYS=365
```

Production release is blocked when an enabled required setting is absent or invalid. Do not hardcode Dan’s address in source. Resolve it from the existing secure operator profile or a secret-backed environment variable.

### 7.2 Feature behavior

Feature flags may be false in local development, but production release readiness requires all four COE flags above to be true. The release controller must report which required feature is disabled.

### 7.3 Policy files

Use the support files in this package as initial contracts:

- `config/coe-gates.example.json`
- `config/coe-policy.example.json`
- `config/backup-policy.example.json`
- `config/artifact-lifecycle.example.json`

Copy them into the repository without the `.example` suffix and adjust paths to the repository’s real commands and state layout. Do not weaken the fail-closed requirements.

---

## 8. One authoritative release identity

### 8.1 Source of truth

Create `release/release.json` and make it the only authoritative product release identity.

Required fields:

```json
{
  "schema_version": 1,
  "product": "chip-service",
  "release_version": "4.5.0",
  "release_channel": "stable",
  "lpos_version": "4.5.0"
}
```

The final values must reflect the intended shipping release. `package.json`, generated clients, shells, status documents, dashboard, emails, API responses, manifests, and gate evidence must consume this identity. They may mirror it, but may not define a competing value.

### 8.2 Separate version from stage

Values such as `S04`, `S13`, or `0.10A.0` must not appear in fields named release version. When still operationally useful, store them under explicit names such as:

- `build_stage`
- `ui_generation_version`
- `api_schema_version`

A stage mismatch may be permitted only when policy defines it; it must never silently masquerade as the release version.

### 8.3 Drift detection

Implement `scripts/check-release-version.js`. It must fail if any required mirror differs from `release/release.json`.

At minimum compare:

- `package.json` version.
- Server identity response.
- Generated API client metadata.
- Built shell metadata.
- `status/current.json` if that file remains part of the product.
- Release manifest version.
- Dashboard summary version.
- Report version.
- Shipping artifact filename/metadata.

Generated outputs must be rebuilt from the identity, not manually edited to match.

### 8.4 Release API identity

Expose one read-only identity object in the release-gate contract:

```json
{
  "product": "chip-service",
  "release_version": "4.5.0",
  "release_channel": "stable",
  "git_commit": "<40 hex>",
  "build_id": "<deterministic or traceable id>",
  "artifact_sha256": "<64 hex>"
}
```

---

## 9. Complete immutable application release manifest

The documentation pack manifest is not an application verifier. Implement a manifest for the complete final application artifact.

### 9.1 Build staging

1. Build in a clean, isolated staging directory outside the source tree or in a dedicated ignored build area.
2. Fail the release build when the source tree contains unapproved modifications relative to the selected commit.
3. Copy only explicitly packaged source/runtime files and generated production assets into the staged release root.
4. Do not copy `.git`, `.terraform`, provider caches, local credentials, logs, state databases, reports, node caches, test output, backups, or nested releases.
5. Build the manifest only after the staged release is complete.
6. Do not silently skip a required file.

### 9.2 Manifest format

Create `release-manifest.json` in the staged artifact using `schemas/release-manifest.schema.json`. Enumerate every regular release file except the manifest itself and any separately defined detached signature.

For every file record:

- POSIX relative path using `/`.
- SHA-256 digest.
- Byte size.
- Mode or executable bit where material.
- File type.

Include manifest-level release identity, source commit, build ID, generation tool version, and creation time.

### 9.3 Verifier behavior

`verify-release.js <release-root>` must:

1. Validate manifest schema.
2. Recalculate every listed hash and size.
3. Fail on every missing listed file.
4. Enumerate the release tree and fail on every unlisted file except explicitly allowed manifest/signature files.
5. Reject duplicate normalized paths.
6. Reject absolute paths, `..`, path traversal, and case-collision hazards.
7. Reject symlinks escaping the release root. Prefer no symlinks unless required and explicitly represented.
8. Reject mutable runtime directories and file patterns inside the release root.
9. Verify release identity and source commit.
10. Verify the artifact itself has not been altered after the manifest was generated.
11. Emit schema-valid gate evidence and a nonzero exit code on any defect.

No `continue` or equivalent may turn an absent required file into success. The audit specifically demonstrated this flaw and the tests must prevent its return.

### 9.4 Required verifier tests

Implement at least these cases:

1. Clean release passes.
2. Changing `package.json` fails.
3. Changing a generated JS/CSS asset fails.
4. Removing a listed file fails.
5. Adding an unlisted file fails.
6. Adding a mutable status file fails.
7. Modifying the manifest without matching contents fails.
8. Version mismatch fails.
9. Commit mismatch fails.
10. Symlink escape fails.
11. Path traversal entry fails schema/verification.
12. Duplicate path fails.
13. Permission/executable-bit mismatch fails when material.
14. Corrupt JSON fails.
15. Empty manifest fails.
16. Running against the source tree instead of a staged release fails when mutable/unlisted content is present.

### 9.5 Doctor integration

`lpos doctor` or the chip-service equivalent must auto-detect when it is operating in an installed release tree and invoke the application verifier. Integrity failure makes Doctor unhealthy and blocks release.

---

## 10. Evidence model: independent, append-only, and tamper-evident

Use `schemas/coe-gate-evidence.schema.json` for every required gate.

### 10.1 Gate evidence requirements

Each record includes:

- `schema_version`.
- Unique `evidence_id`.
- `audit_id`.
- `gate_id`.
- Gate implementation version.
- `status`: `pass`, `fail`, `error`, or `skipped`.
- Started/completed UTC timestamps.
- Duration.
- Exact executable and argument array.
- Exit code and termination signal.
- Release identity.
- Git commit.
- Input hashes.
- Individual check results with evidence references.
- Redacted stdout/stderr hashes and bounded excerpts.
- Artifact references and SHA-256 values.
- `previous_evidence_hash`.
- `evidence_hash` calculated over canonical JSON excluding `evidence_hash`.
- Source designation: `command`, never `preset` for production gates.

### 10.2 Hash chain

Within each audit, order gate/evidence records deterministically. Calculate:

```text
evidence_hash = SHA256(canonical_json(record_without_evidence_hash) + previous_evidence_hash)
```

The first record uses a defined zero hash. Validate the complete chain before making a release decision.

### 10.3 Append-only enforcement

Implement insert-only evidence tables. Prevent ordinary application code from updating or deleting evidence. In SQLite, use triggers to reject update/delete on evidence and release-decision tables. Retention/archival must be an explicit maintenance operation with its own audit record and must not change historical decision meaning.

### 10.4 Logs and redaction

- Cap stored stdout/stderr excerpts.
- Hash complete log files stored outside the release root.
- Redact tokens, passwords, cookies, authorization headers, private keys, OAuth material, and configured secret patterns before persistence or email.
- Secret scan the generated evidence/report directories before report delivery.

---

## 11. Persistent COE data model

Apply the additive SQLite migration in `db/001_coe.sql`, adapting the migration number and database bootstrap to the existing v4 state system.

The data model must support:

- Audits and their scope.
- Independent gate runs and evidence.
- Release decisions.
- Findings and evidence links.
- Opportunities and operator decisions.
- Metrics and trends.
- Technical debt lifecycle.
- Scheduler jobs and executions.
- Wake decisions.
- Backups and restore tests.
- Persistent artifact lifecycle.
- Report deliveries.
- Documentation pass-off references.
- Audit locks/idempotency.

### 11.1 State location

Store the database outside immutable releases. Do not migrate or delete legacy `/Users/dan/lpos-state` history as part of this work.

Create a technical-debt record for the compatibility boundary:

```text
ID: TD-LEGACY-LPOS-STATE
Title: Import legacy lpos-state ledgers into v4 SQLite
Status: accepted-temporary
Constraint: legacy records remain read-only; new silent runs may not write compatibility records
Removal: separate validated, reversible migration
```

### 11.2 Audit ID

Use a UUIDv7, ULID, or equivalent sortable unique identifier. Every dashboard snapshot, email, release decision, metric, and evidence record must identify its audit ID.

### 11.3 Time

Store timestamps in UTC. Store the scheduling timezone and local Central date separately for daily idempotency and display.

---

## 12. Command-backed gate runner

### 12.1 Process execution

For each gate:

- Invoke the configured executable directly with an argument array.
- Do not use shell string interpolation.
- Set a timeout.
- Set a maximum output size.
- Capture exit code and signal.
- Provide a temporary working directory where needed.
- Provide only the minimum environment.
- Pass audit ID, release identity path, state path, staged release path, source commit, and evidence output path explicitly.
- Verify the evidence file was created, parses, validates, matches the current audit and release identity, and reflects the actual process exit.

A zero exit without valid pass evidence is an error. A pass evidence file with nonzero exit is an error. Both block release.

### 12.2 Gate isolation

Run destructive or failure-injection checks in isolated temporary resources. Never run simulated outage or restore tests against production state.

### 12.3 Evidence freshness

Release evidence must:

- Belong to the same audit ID.
- Match the exact source commit.
- Match the exact release identity.
- Match the exact staged artifact hash where applicable.
- Complete within the release audit window.
- Not predate any source/build change.

### 12.4 Package scripts

Add stable package commands, using repository conventions:

```json
{
  "scripts": {
    "coe:audit": "node scripts/coe-run.js",
    "coe:report": "node scripts/coe-send-report.js",
    "release:manifest": "node scripts/generate-release-manifest.js",
    "release:verify": "node scripts/verify-release.js",
    "release:version-check": "node scripts/check-release-version.js",
    "gate:deterministic": "<real deterministic suite command>",
    "gate:release-verifier": "<verifier gate command>",
    "gate:doctor": "<doctor command>",
    "gate:engineering": "<engineering audit command>",
    "gate:security": "<security audit command>",
    "gate:documentation": "<documentation audit command>",
    "gate:bloat": "<bloat audit command>",
    "gate:opportunity": "<opportunity audit command>",
    "gate:release-integrity": "<release integrity command>",
    "release:decision": "node scripts/coe-release-decision.js"
  }
}
```

Do not use placeholder commands in the committed implementation.

---

## 13. The nine mandatory release gates

All nine are required. Each must execute independently and emit evidence.

### Gate 1 — Deterministic Test Suite (`deterministic-tests`)

Run the actual deterministic suite. Include test count, pass/fail/skip count, test runner version, and output hash. Intentional skips must be enumerated with policy justification. New unapproved skips block release.

### Gate 2 — Application Release Verifier (`application-release-verifier`)

Run the complete immutable release verifier against the final staged artifact. Include manifest hash, file count, total bytes, artifact hash, and all validation results.

### Gate 3 — Doctor (`doctor`)

Doctor must validate at least:

- Required configuration.
- State directory outside release root.
- SQLite migration/integrity.
- Scheduler registration and timezone.
- Email transport configuration without exposing secrets.
- Dashboard route/auth configuration.
- Release identity convergence.
- Application release integrity when in a release tree.
- Required writable/read-only paths.
- No critical dependency or service misconfiguration.

### Gate 4 — Engineering Audit (`engineering-audit`)

Review every file added or modified between the previous successful audit/release baseline and target commit. Run real analyzers and tests where available. Produce per-file and aggregate findings for:

- Readability and maintainability.
- Complexity and oversized functions/modules.
- Duplicate logic.
- Dead or unreachable code.
- Unused dependencies.
- Error handling.
- Input validation.
- Observability.
- Test coverage of changed behavior.
- Performance hazards.
- Architecture drift.
- Unnecessary abstractions.
- Mutable writes into immutable/source paths.
- Documentation impact.

The gate may pass with noncritical findings only when every finding is recorded and the configured threshold is satisfied. Open critical engineering findings block release.

### Gate 5 — Security and Reliability Audit (`security-reliability-audit`)

Replace the constructed results in `src/security-reliability-runtime.js` with command-backed checks. At minimum execute:

- Authentication and authorization tests for operator routes.
- Dashboard privacy tests.
- CSRF/session/cookie controls as applicable.
- Secret scanning of tracked source, staged artifact, evidence, and reports.
- Dependency vulnerability check using the project’s pinned tool and lockfile; distinguish unavailable network from pass.
- Input validation and injection tests for new API parameters.
- Isolation tests using temporary state.
- Controlled failure-injection tests in an isolated environment.
- Actual backup restore test evidence within policy age.
- Service startup and graceful failure behavior.
- Sensitive logging review.

A mocked restore is not restore evidence. A test that asserts preset booleans is not an audit.

### Gate 6 — Documentation Audit (`documentation-audit`)

Verify:

- Required COE repository documents exist.
- Documentation release versions match the authoritative identity.
- Links/routes in docs resolve or are valid deployment-relative routes.
- The documentation manifest includes new COE documents.
- Constitution, architecture, developer, operations, release notes, and pass-off are updated.
- GitHub, wiki, and Google Drive pass-off evidence records contain stable references and verification timestamps.
- No active documentation directs Hermes to use LPOS v3 or obsolete release behavior.
- No ignored desktop attachment is treated as the authoritative copy.

### Gate 7 — Bloat and Efficiency Audit (`bloat-audit`)

Measure rather than assume. Include:

- Tracked bytes and file count.
- Untracked/ignored bytes by category.
- Build and cache bytes.
- Duplicate file groups and bytes.
- Release/artifact duplication.
- Backup growth and nested backup detection.
- Immutable-tree mutations.
- Stale build output.
- Scheduler fixture leaks.
- Paused/orphan/duplicate/legacy jobs.
- Repeated no-delta evidence writes.
- Prompt/context/skill surface bloat.
- Model wakes avoided versus unnecessary wakes.

Do not classify deliberate generated public copies as defects without evidence of harm. Distinguish repository bloat from assurance bloat.

### Gate 8 — Opportunity and Value Audit (`opportunity-audit`)

Verify that every unresolved critical/high finding has an associated opportunity or explicit accepted-risk decision. Rank opportunities by:

- Expected operator time saved.
- Compute/token cost saved.
- Latency reduced.
- Risk reduced.
- Maintenance reduced.
- Quality increased.
- Implementation effort.
- Confidence.

The gate fails when critical findings are orphaned, when required owner/decision fields are absent, or when claimed completed improvements lack before/after evidence.

### Gate 9 — Release Integrity and Provenance (`release-integrity`)

Verify the complete chain:

- Source commit and clean build context.
- Authoritative release identity.
- Build command and environment metadata.
- Final staged artifact hash.
- Application manifest hash.
- All eight other gate evidence hashes.
- Documentation pass-off evidence.
- Release decision hash.
- Deployment artifact identity.

This gate passes only when the exact artifact being approved is the artifact verified by all applicable evidence.

---

## 14. Replace the current release endpoint contract

The audit found `/api/v1/operator/release-gate` returns the old closed-pilot packet. Replace it with the COE release contract while preserving backward compatibility only through an explicitly versioned legacy field or endpoint if required.

Minimum response:

```json
{
  "schema_version": 1,
  "audit_id": "01...",
  "generated_at": "2026-07-28T...Z",
  "release": {
    "product": "chip-service",
    "release_version": "4.5.0",
    "release_channel": "stable",
    "git_commit": "...",
    "build_id": "...",
    "artifact_sha256": "..."
  },
  "status": "blocked",
  "ready_for_dan_approval": false,
  "decision_reason_codes": ["GATE_MISSING"],
  "gates": [
    {
      "gate_id": "deterministic-tests",
      "status": "pass",
      "evidence_id": "...",
      "evidence_hash": "...",
      "completed_at": "..."
    }
  ],
  "critical_findings": [],
  "documentation_passoff": {
    "status": "verified",
    "references": []
  },
  "decision_hash": "..."
}
```

The endpoint must be read-only, authenticated, cache-controlled for private operational data, and derived from a persisted release-decision record.

---

## 15. Daily COE audit scheduler

### 15.1 Schedule

Run at `03:00` in `America/Chicago` every day. Configure timezone explicitly; do not rely on server-local timezone.

### 15.2 DST and idempotency

Use the Central local calendar date as the idempotency key:

```text
coe-daily:<YYYY-MM-DD America/Chicago>
```

Only one scheduled daily audit may be active or complete for that key. DST must not create duplicate audits. A missed run may be backfilled once, with `trigger=backfill`.

### 15.3 Locking

Acquire a database-backed lease before the audit. Record owner, acquired time, expiry, and heartbeat. A second runner must exit visibly rather than overlap. Expired locks require a recovery record.

### 15.4 Retry

- Retry transient collector failures using bounded exponential backoff.
- Do not retry deterministic failures as though they were transient.
- Report partial/failed audit state on the dashboard.
- Email delivery retries are separate from audit execution.

### 15.5 Audit scope

Daily audit scope includes:

- All operational metrics since prior daily audit.
- All code changed since prior successful engineering audit.
- Current release and source integrity.
- Active scheduler/job inventory.
- Skill catalog and search/install history.
- Backup and restore evidence freshness.
- Storage trends.
- Documentation drift.
- Open findings, technical debt, and opportunities.
- COE system efficiency itself.

### 15.6 Manual and release triggers

Support:

```text
scheduled-daily
manual
pre-release
post-deploy
backfill
```

A pre-release audit always runs all nine gates. A daily audit may reuse only evidence explicitly allowed by freshness policy; it may never report a release ready from incomplete gates.

---

## 16. Process efficiency and value audit

Hermes must audit how it works, not only what files exist.

For each non-trivial workflow, record where instrumentation is available:

- Planning/routing duration.
- Model calls, model names, tokens, and cost estimate.
- Tool calls and duration.
- Skill discovery calls.
- Context bytes/tokens.
- Human approvals requested.
- Retries and rework.
- Result status.
- No-op or no-delta outcome.
- Evidence/documentation writes.
- Operator-visible value category.

Detect:

- Repeated serial work that can run in parallel safely.
- Repeated searches that should be cached.
- Re-reading unchanged context.
- Duplicate agents or guild responsibilities.
- Excess approval requests already covered by policy.
- Evidence generation on silent/no-delta runs.
- High-latency steps with low outcome value.
- High-cost model use where deterministic/local/lower-cost logic performs equivalently.

Every recommendation must include evidence, expected effect, risk, implementation effort, confidence, and approval status.

No process should be removed automatically solely because it had low recent usage. Safety, compliance, rollback, and rare-critical functions require qualitative value treatment.

---

## 17. Skill search and installation efficiency

The user explicitly asked whether skill discovery and approval are becoming an efficiency problem. Implement measurement and guardrails.

### 17.1 Discovery order

For a task requiring a capability:

1. Query a compact indexed local skill catalog by capability and compatibility.
2. Reuse a previously approved active skill when it satisfies the request.
3. Consult cached discovery results when fresh and tied to the catalog version.
4. Search external/new skills only when no approved local capability meets the need or when explicitly requested.
5. Present new installation choices for operator approval.
6. Install only after approval.
7. Verify, document, and index the installed skill.

Do not load or reread every full skill document on every task.

### 17.2 Metrics

Track:

- Catalog size and growth.
- Local lookup latency.
- External search latency.
- Search calls per task.
- Cache hit rate.
- Duplicate recommendation rate.
- Installed skill use frequency.
- Last used time.
- Failure/retry rate.
- Average context contribution.
- Maintenance burden.
- Superseded/duplicate capability.
- Approval-to-first-use ratio.
- Approved-but-never-used skills.

### 17.3 Findings

Flag:

- Multiple skills providing materially duplicate capability.
- Skills loaded globally when only one operation needs them.
- Stale or incompatible skills.
- Skills that add large context with little measured benefit.
- Repeated external searches returning the same candidates.
- Approved skills never used after a configurable evaluation window.

Changes remain approval-gated. The daily report should state whether skill management is currently efficient, degraded, or unknown and why.

---

## 18. Scheduler governance and wake-agent policy

### 18.1 Job inventory

Persist every scheduled job with:

- Stable job ID.
- Owner.
- Purpose.
- Schedule/timezone.
- Enabled/paused state.
- Creation/update time.
- Target operation.
- Prompt/policy version.
- Skills/tools allowed.
- Deterministic precondition.
- Wake policy.
- Retention.
- Retirement criteria.

### 18.2 Daily scheduler checks

Detect:

- Duplicate schedule/target signatures.
- Orphaned targets or missing handlers.
- Leaked test/fixture jobs.
- Paused jobs beyond policy age.
- Disabled jobs that should be retired.
- Legacy version prompts.
- Overlapping schedules.
- Jobs with persistently high no-op rate.
- Jobs with persistently low operator value.
- Jobs writing evidence on silent/no-delta runs.
- Overbroad skill/tool permissions.

### 18.3 Explicit wake policy

Every scheduled operation must make and record a deterministic wake decision before a model invocation:

```json
{
  "eligible": true,
  "wakeAgent": false,
  "reason_code": "NO_NEW_INPUT",
  "decision_source": "deterministic-policy",
  "model_invoked": false
}
```

Default to `wakeAgent=false` when there is no qualifying input. Uncertain, safety-relevant, or unresolved holds may wake the agent under documented policy. Silent discarding is not allowed where fail-visible behavior is required.

### 18.4 Wake efficiency

Expose:

- Eligible polls.
- Model wakes.
- Deterministic skips.
- False wakes/no-delta wakes.
- Fail-visible wakes.
- Tokens/cost avoided.
- Wake efficiency percentage.

Do not treat fewer wakes as automatically better. The metric must preserve missed-work and false-negative checks.

---

## 19. Prompt drift and minimum policy surface

Scan active job prompts, templates, and embedded instructions for:

- `LPOS v3`, `Use LPOS v3`, and other obsolete version references.
- Conflicting release/version instructions.
- Deprecated paths.
- Stale skill names.
- Broad tool/skill lists inconsistent with operation policy.
- Mutable writes into release paths.
- Instructions that bypass approval or evidence requirements.

Maintain a source-controlled allowlist for legitimate historical references. Every finding includes file/job, exact matched value, active/inactive status, and remediation.

Standing Operations must use only the narrow skills, tools, models, permissions, and context needed for their function. Changes to this surface require tests.

---

## 20. Backup governance and actual restore evidence

### 20.1 Source-controlled policy

Implement `config/backup-policy.json`. It must define:

- Approved sources and destinations.
- Exclusions.
- Maximum total bytes.
- Maximum file count.
- Maximum single-file size.
- Retention classes.
- Encryption requirement.
- Forbidden secret/material patterns.
- Nested backup detection.
- Restore-test frequency and maximum evidence age.
- Owner and purpose.

### 20.2 Backup behavior

- Do not back up release caches, nested backups, `.terraform`, provider caches, test fixtures, node caches, or credential material.
- Enforce ceilings before and during backup.
- Fail visibly when a ceiling is exceeded.
- Record backup manifest, bytes, file count, hash, destination, policy version, and expiration.
- Do not copy credentials merely because they are under a source directory.

### 20.3 Restore test

At least weekly and before release when evidence is stale:

1. Select a policy-valid backup.
2. Restore into an isolated temporary directory.
3. Verify backup manifest and hashes.
4. Run SQLite `integrity_check` where applicable.
5. Verify required sentinel records/files.
6. Start the relevant component in isolated/read-only mode if feasible.
7. Record cleanup and outcome.

A backup existence check is not a restore test. A mocked restore is not release evidence.

### 20.4 Artifact bucket lifecycle

Add a source-controlled lifecycle/retention rule to the artifact bucket infrastructure. At minimum distinguish:

- Current release artifacts.
- One full rollback release.
- One compact historical artifact.
- Temporary build/staging artifacts with short expiration.
- Audit evidence/report retention.

Terraform provider/plugin caches must remain ignored local tooling and must never enter artifacts.

---

## 21. Persistent artifact lifecycle metadata

Every persistent artifact record must include:

- Stable artifact ID.
- Owner.
- Purpose.
- Lifecycle class.
- Created time.
- Source audit/release.
- Storage location.
- Byte size and file count.
- SHA-256 or manifest hash.
- Immutability classification.
- Verification method and last verification time.
- Retention policy and expiration.
- Retirement plan or explicit `retain-indefinitely` justification.
- Contains-sensitive-data classification.

Existing artifact metadata containing only hash, retention, and immutability is insufficient. Doctor and the documentation audit must validate required fields.

---

## 22. Storage trend collector

Collect daily bytes and counts for at least:

- Tracked repository.
- Untracked workspace.
- Ignored caches/tools.
- Staged release.
- Installed releases.
- Rollback/historical artifacts.
- Mutable state.
- Audit evidence.
- Reports.
- Backups.
- Temporary build output.
- Duplicate content estimate.

Store measurements as time series. Alert on:

- Absolute policy ceilings.
- Unexpected day-over-day growth.
- Repeated growth without operator value.
- Nested backup patterns.
- Immutable release growth beyond release comparison threshold.
- Mutable writes inside release roots.

The dashboard must explain categories so a large ignored provider cache is not confused with tracked source bloat.

---

## 23. Explicit daily code and engineering audit

Every daily audit must determine the code range:

```text
baseline_commit = target commit of previous successful engineering audit
current_commit = current monitored branch/deployed source commit
```

If no code changed, record a no-change engineering audit with zero model invocation when deterministic checks are sufficient. If code changed, review every added/modified/renamed source, script, config, migration, infrastructure, test, and documentation file.

### 23.1 Required per-change analysis

For each changed implementation file, record:

- Change purpose from commit/diff context.
- Public interfaces changed.
- Complexity/size delta.
- Duplication introduced or removed.
- Error and failure behavior.
- Input and authorization boundaries.
- Mutable/immutable path behavior.
- Tests covering the change.
- Documentation required/updated.
- Performance and cost implications.
- Technical-debt impact.
- Suggested simplification when evidence supports it.

### 23.2 Tool-backed checks

Use actual repository tooling and add focused analyzers where missing. Include:

- Existing lint/anti-slop checks.
- Unit/integration/E2E tests.
- Coverage for changed behavior where supported.
- Duplicate-code detection or a deterministic equivalent.
- Dependency/import usage checks.
- Secret scan.
- Migration validation.
- Build reproducibility check.
- Release version drift check.
- Immutable-path write scan.

### 23.3 Engineering retrospective

For significant changes, answer with evidence:

- Was this more complex than necessary?
- Could fewer files/modules safely provide the same behavior?
- Did it reuse existing LPOS capabilities?
- Did it add an abstraction without multiple real consumers?
- Did it increase or reduce long-term maintenance?
- Did it create a recurring class of defect that should become a test or policy?
- Did it leave the codebase objectively better?

### 23.4 Findings and thresholds

Use severities `critical`, `high`, `medium`, `low`, `info`. A critical finding blocks release. High findings block unless explicitly accepted by an authorized operator decision with expiration. Unknown coverage or unavailable tooling must be shown as unknown, not pass.

---

## 24. Technical-debt lifecycle registry

Every compatibility layer, temporary implementation, TODO with operational impact, deprecated route, legacy state dependency, and accepted high-risk finding must be registered.

Required fields:

- Debt ID.
- Title and description.
- Evidence/source.
- Owner.
- Created time.
- Reason it exists.
- Affected components.
- Risk/severity.
- Current cost/impact.
- Retirement condition.
- Target date or explicit review date.
- Migration/removal plan.
- Verification and rollback plan.
- Status and decision history.

The daily audit flags debt with no owner, no review date, expired acceptance, or no retirement condition.

Do not silently delete the legacy `/Users/dan/lpos-state` boundary. Register and monitor it as specified in Section 11.

---

## 25. Opportunity backlog and value proof

Every optimization opportunity must be traceable to evidence or a measured trend.

Required fields:

- Opportunity ID.
- Source audit/finding.
- Problem statement.
- Proposed change.
- Expected operator-time savings.
- Expected compute/token savings.
- Expected latency reduction.
- Expected risk reduction.
- Expected maintenance reduction.
- Expected quality improvement.
- Implementation effort.
- Confidence.
- Dependencies.
- Approval requirement/status.
- Owner and target/review date.
- Before metrics.
- After metrics when completed.
- Outcome status: proposed, approved, rejected, in-progress, verified, ineffective, superseded.

An item may be marked `verified` only after the post-change measurement demonstrates value or documents why an important risk-control improvement is qualitative.

The COE system must audit its own backlog for duplicate low-value recommendations and stale noise.

---

## 26. Transparent scores and release readiness

Scores are summaries, never substitutes for gate results.

### 26.1 Score dimensions

Expose numeric scores when data is sufficient, otherwise `unknown`:

- Overall Health.
- Engineering.
- Security.
- Efficiency.
- Cost.
- Documentation.
- Release Integrity.
- Scheduler Health.
- Wake-Agent Efficiency.
- Backup Health.

### 26.2 Default overall weighting

Use source-controlled weights, initially:

```text
Engineering        20%
Security           20%
Efficiency         15%
Release Integrity  15%
Documentation      10%
Cost               10%
Scheduler Health    5%
Backup Health       5%
```

Normalize only across available dimensions for informational display, but if a required dimension is unknown, release readiness remains blocked and the UI must show the missing dimension.

### 26.3 Hard caps

- Any open critical finding: overall score maximum 59 and release blocked.
- Any required gate failed/missing/stale/skipped: release blocked.
- Any release identity or artifact mismatch: release blocked.
- Documentation pass-off unverified: release blocked.
- Report delivery failure does not rewrite the completed audit, but creates a critical operational finding and retry state.

### 26.4 No cosmetic green

Do not choose thresholds to make the current implementation green. Commit policy weights and thresholds with rationale and tests.

---

## 27. COE APIs

Implement authenticated private endpoints under `/api/v1/coe`.

Required endpoints:

```text
GET  /api/v1/coe/summary
GET  /api/v1/coe/audits
GET  /api/v1/coe/audits/:auditId
GET  /api/v1/coe/findings
GET  /api/v1/coe/opportunities
POST /api/v1/coe/opportunities/:opportunityId/decision
GET  /api/v1/coe/technical-debt
GET  /api/v1/coe/storage
GET  /api/v1/coe/scheduler
GET  /api/v1/coe/backups
GET  /api/v1/coe/reports/:auditId
GET  /api/v1/operator/release-gate
```

Use `openapi-coe.yaml` in this package as the minimum contract.

### 27.1 API controls

- Require the existing operator authentication and authorization.
- Return 401/403 correctly and test both.
- Do not expose raw secrets, full private email content, OAuth data, or credential-bearing logs.
- Apply pagination and bounded limits.
- Validate IDs, filters, and decisions.
- Record operator decisions append-only with actor and timestamp.
- Use private/no-store cache headers for sensitive endpoints.
- Include `audit_id`, `release_version`, and `generated_at` in summary responses.

---

## 28. Private COE dashboard

### 28.1 Routes

- Canonical page: `/dashboard/coe`.
- Alias: `/ops/coe` must redirect to `/dashboard/coe`.
- Production canonical URL: `https://chip.listeningpost.ai/dashboard/coe`.

The page must require operator authentication. Do not expose customer/private operational details publicly.

### 28.2 Required named fields

The dashboard must show all 18 fields explicitly:

1. Overall Health Score.
2. Engineering Score.
3. Security Score.
4. Efficiency Score.
5. Cost Score.
6. Documentation Score.
7. Release Integrity.
8. Scheduler Health.
9. Wake-Agent Efficiency.
10. Prompt Drift.
11. Technical Debt.
12. Opportunity Backlog.
13. Release Readiness.
14. Top Risks.
15. Pending Approvals.
16. Recent Improvements.
17. Audit History.
18. Current Release Status.

Also show:

- Current authoritative release version.
- Current git commit/build ID.
- Latest audit ID.
- Last updated time.
- Daily email delivery status.
- Backup/restore evidence age.
- Storage trend summary.

### 28.3 Data behavior

- Fetch from the COE APIs/persisted evidence.
- Do not embed preset success values.
- Show `unknown`, `stale`, `failed`, or `blocked` explicitly.
- Link every summary status to supporting checks/findings where practical.
- Use Central time for operator display and UTC in evidence details.
- Show release readiness independently from the overall score.

### 28.4 Dashboard acceptance

Automated tests must prove:

- Unauthenticated access is rejected or redirected to auth.
- Authenticated operator access renders.
- All 18 labels are present.
- Latest audit ID and release version match API data.
- A failed gate renders blocked, not green.
- Missing data renders unknown.
- `/ops/coe` redirects.
- Canonical URL uses `PUBLIC_BASE_URL` and configured path.
- No secrets appear in rendered HTML or API payload.
- The deployed URL returns a successful authenticated probe after release.

---

## 29. Daily report and email delivery

### 29.1 Trigger

After every daily audit reaches a terminal state, render and attempt delivery. Send failed/blocked audit reports as well as successful reports.

### 29.2 Recipient

Use the secure configured operator recipient. Production Doctor must fail when email is enabled and the recipient or transport configuration is absent.

### 29.3 Subject

```text
[LPOS COE] <PASS|BLOCKED|FAILED> — <release_version> — <Central date> — <audit_id>
```

### 29.4 Required content

- Executive summary.
- Audit terminal status.
- Audit ID.
- Authoritative release version and commit.
- Direct dashboard link.
- Release readiness.
- All gate statuses.
- Top risks.
- Top inefficiencies and low-value work.
- Code/engineering findings.
- Skill-search efficiency summary.
- Scheduler and wake efficiency.
- Backup/restore status.
- Storage trend.
- Technical debt and opportunities.
- Pending operator decisions.
- Report/evidence location.

Use `templates/daily-email.md` as the minimum structure.

### 29.5 Dashboard link

Build the exact URL as:

```text
${PUBLIC_BASE_URL}${COE_DASHBOARD_PATH}?audit=<audit_id>
```

The report must also include the canonical unfiltered dashboard URL.

### 29.6 Delivery evidence

Record:

- Audit ID.
- Recipient hash or appropriately protected address reference.
- Provider/transport.
- Attempt number.
- Started/completed time.
- Status.
- Provider message ID.
- Error code/message after redaction.
- Report hash.
- Dashboard URL.

Retry transient failure at bounded intervals such as 1, 5, and 15 minutes. Do not report email delivered without a provider acceptance/message ID or equivalent verifiable transport result.

### 29.7 Test delivery

Before declaring shipped, send one test/implementation-completion report to Dan and record delivery evidence. The report must contain the deployed dashboard link.

---

## 30. COE self-audit

COE itself can become bloat. Every daily audit must measure:

- COE runtime.
- Gate/collector durations.
- Tool/model calls.
- Tokens/cost.
- Evidence bytes and report bytes.
- Duplicate findings generated.
- Recommendations repeated without new evidence.
- False-positive/overturned finding rate.
- Audit failures and retries.
- Dashboard query latency.
- Email delivery success.

Flag checks that repeatedly consume resources with little decision value. Do not remove mandatory assurance controls solely for speed; simplify implementation or adjust frequency based on risk and evidence.

---

## 31. Documentation and pass-off

The addendum may not remain an ignored desktop attachment. Commit authoritative documentation into the repository.

### 31.1 Repository documentation

At minimum create/update:

- Constitution: Continuous Improvement and Operational Sustainability principles.
- `docs/architecture/coe/README.md`.
- `docs/architecture/coe/DATA_MODEL.md`.
- `docs/architecture/coe/RELEASE_ASSURANCE.md`.
- `docs/architecture/coe/OPERATIONS.md`.
- `docs/architecture/coe/DASHBOARD.md`.
- `docs/architecture/coe/SECURITY.md`.
- Developer guide.
- Operations manual.
- Deployment documentation.
- Changelog.
- Release notes.
- `docs/passoff/LPOS-v4.5.0-COE.md`.
- Documentation/build-pack manifest.

### 31.2 External surfaces

Publish the approved final documentation to the existing LPOS:

- GitHub repository/branch or merged release branch.
- Project wiki.
- Google Drive hand-off location.

Record stable references, content hashes where possible, timestamps, and verification status in `coe_documentation_passoff`.

Do not claim external synchronization without reading back or otherwise verifying the published item.

### 31.3 Pass-off note

The next operating-system version pass-off must state:

- COE is a permanent constitutional subsystem.
- Daily audit runs at 03:00 America/Chicago.
- All new/modified code is explicitly audited.
- Release readiness is evidence-backed and fail-closed.
- Immutable application releases are fully enumerated and verified.
- The private dashboard URL and report behavior.
- The legacy lpos-state boundary remains a separately governed migration.
- Rollback and operational ownership.

---

## 32. Testing requirements

Tests must prove the controls, including negative paths. Do not merely assert that fixtures contain `pass`.

### 32.1 Unit tests

- Release identity parsing and drift detection.
- Canonical JSON and evidence hashing.
- Evidence schema validation.
- Hash-chain verification.
- Gate process exit/evidence consistency.
- Redaction.
- Score calculation and unknown handling.
- Opportunity/technical-debt validation.
- Scheduler idempotency and timezone handling.
- Wake decision metrics.
- Report URL construction.

### 32.2 Integration tests

- SQLite migration and append-only triggers.
- Complete audit orchestration.
- Gate runner with real child commands.
- Release controller blocks missing/stale/failed evidence.
- Release manifest generation and verification.
- Backup creation and actual isolated restore.
- API authentication and response contracts.
- Dashboard data binding.
- Email adapter using a safe test transport, followed by one real configured completion delivery.
- Documentation pass-off verification adapters.

### 32.3 End-to-end tests

Run an isolated complete flow:

1. Build staged artifact.
2. Generate manifest.
3. Run nine gates.
4. Persist evidence.
5. Generate release decision.
6. Render dashboard summary.
7. Render report.
8. Deliver through test transport.
9. Verify links/identity/audit ID.

Then run at least these failure cases:

- Tampered artifact.
- Missing manifest file.
- Extra unlisted file.
- Version drift.
- Gate timeout.
- Gate exits zero without evidence.
- Gate evidence says pass with nonzero process exit.
- Stale evidence.
- Evidence from wrong commit.
- Broken evidence hash chain.
- Restore-test failure.
- Email failure.
- Missing documentation pass-off.
- Unauthenticated dashboard access.
- Mutable state inside release root.

### 32.4 Existing baseline commands

The final implementation must still pass:

- `npm run check`.
- `npm run test`.
- Isolated production build.
- Documentation pack verification.
- Anti-slop lint.

Add the COE commands and include them in CI/release workflows.

### 32.5 No intentional unexplained skips

Every skip must include a reason code and owner. New skips require explicit policy. A required gate cannot be skipped in production release mode.

---

## 33. Migration and rollout sequence

Implement in this order to avoid building UI on untrustworthy data.

### Phase 0 — Preserve and baseline

- Create isolated worktree.
- Capture baseline evidence.
- Identify deployment, auth, scheduler, mail, state, and docs integration points.

### Phase 1 — Trust foundation

- Authoritative release identity.
- Complete application manifest/verifier.
- SQLite COE schema.
- Canonical evidence and hash chain.
- Gate runner.
- Replace self-attesting security/reliability state.

Exit condition: negative verifier/evidence tests pass and old endpoint cannot be green without evidence.

### Phase 2 — Nine gates and release controller

- Implement all commands.
- Persist evidence.
- Implement fail-closed release decision.
- Replace release endpoint contract.

Exit condition: one isolated pre-release audit produces nine valid records and a reproducible decision.

### Phase 3 — Daily operational collectors

- Process/skill audit.
- Scheduler/wake audit.
- Prompt drift.
- Backup/restore.
- Storage trends.
- Artifact lifecycle.
- Technical debt/opportunities.
- COE self-audit.

Exit condition: daily audit persists complete data without writing into source/release paths.

### Phase 4 — Dashboard and reporting

- APIs.
- Authenticated dashboard.
- Email renderer/delivery.
- Delivery evidence.

Exit condition: local/integration E2E passes and all 18 fields are evidence-backed.

### Phase 5 — Documentation and release preparation

- Repository docs.
- Constitution.
- External pass-off surfaces.
- Rebuild final artifact.
- Generate final manifest.
- Run final nine-gate release audit.

### Phase 6 — Push, deploy, and verify

- Commit cohesive changes.
- Push without force.
- Use existing deployment pipeline/runbook.
- Run database migration additively.
- Enable COE production flags.
- Register the 03:00 Central schedule.
- Probe dashboard/API/auth.
- Run post-deploy audit.
- Send completion report.

Do not deploy a locally generated artifact different from the one verified by release evidence.

---

## 34. Git, commit, and shipping requirements

### 34.1 Commit discipline

Use clear commits, for example:

1. `feat(coe): add release identity, evidence store, and immutable verifier`
2. `feat(coe): implement nine command-backed release gates`
3. `feat(coe): add daily audit collectors and lifecycle registries`
4. `feat(coe): add private dashboard and report delivery`
5. `docs(coe): codify operations, governance, and v4.5 pass-off`

Repository policy may squash them, but retain traceability in the final release evidence.

### 34.2 Push behavior

- Do not force push.
- If the release branch can be fast-forwarded under existing policy, push after all local checks.
- If branch protection requires a PR, push `feature/coe-v1`, open the PR through the existing mechanism, run required checks, and merge using project policy.
- Preserve the preexisting local commit and unrelated changes.

### 34.3 Build artifact

The audit noted stale `dist/` had been removed. Rebuild the shipping artifact after all final changes. Verify the rebuilt artifact, not an earlier build.

### 34.4 Deployment

Use the existing authenticated deployment path and infrastructure definitions. Do not invent an unmanaged side deployment. Record:

- Deployment ID.
- Commit.
- Release version.
- Artifact hash.
- Start/end time.
- Migration result.
- Service health result.
- Rollback target.

### 34.5 Canonical dashboard link

After deployment, probe:

`https://chip.listeningpost.ai/dashboard/coe`

The probe must verify the route exists, authentication is enforced, and an authenticated operator session renders current COE data. If routing infrastructure uses another internal path, retain the canonical route through rewrite/redirect. The daily email and final response must use this canonical URL.

---

## 35. Rollback and failure handling

### 35.1 Additive migration

COE database migrations must be additive. Do not destructively rewrite legacy state. Back up the active v4 database before migration and validate restore evidence.

### 35.2 Feature rollback

Support disabling scheduler/email/dashboard execution through emergency configuration while retaining evidence and the release-integrity controls. A production release with required COE flags disabled is not release-ready, but emergency rollback must keep the service operable.

### 35.3 Application rollback

Maintain the approved retention posture:

- Current release.
- One full rollback release.
- One compact historical artifact.

Rollback must identify the exact artifact hash and compatible schema state. Do not automatically downgrade a database through destructive migration.

### 35.4 Failed release

When final gates fail:

- Do not deploy.
- Persist the blocked decision.
- Show it on the dashboard.
- Send the blocked report.
- Create opportunities for actionable findings.
- Continue implementation/remediation within approved scope rather than returning a recommendation-only response.

---

## 36. Acceptance checklist

Use `acceptance/ACCEPTANCE_CHECKLIST.md`. Every item requires one of:

- command and exit status;
- test reference;
- API response reference;
- screenshot/artifact reference where UI is involved;
- evidence ID/hash;
- stable external documentation reference;
- deployed URL probe.

Do not check an item based on implementation intent.

Critical acceptance items include:

- Hardcoded pass results removed.
- Application manifest covers complete staged release.
- Missing/unlisted files fail.
- Version convergence proven.
- Nine gates present and independently executable.
- Release controller blocked by absent evidence.
- Daily scheduler installed at 03:00 Central.
- Audit ID/history persisted.
- Code audit covers changed files.
- Skill-search efficiency measured.
- Backup restore performed.
- Scheduler/wake governance measured.
- Storage trends persisted.
- Technical-debt and opportunity lifecycle persisted.
- Private dashboard exposes all fields.
- Email delivered with dashboard link.
- Documentation pass-off verified.
- Final artifact rebuilt, verified, pushed, deployed, and probed.

---

## 37. Final response contract to Dan

Do not end with more recommendations. Return a compact implementation closeout containing:

```text
COE implementation: shipped | blocked
Release version:
Git commit(s):
Remote branch/PR/merge:
Deployment ID:
Artifact SHA-256:
Final audit ID:
Release gate: pass | blocked
Nine gate statuses:
Daily schedule: 03:00 America/Chicago — enabled/verified
Report delivery: delivered/failed — provider message ID
Dashboard: https://chip.listeningpost.ai/dashboard/coe
Dashboard probe: authenticated route verified at <timestamp>
Documentation pass-off:
Rollback target:
Remaining compatibility boundary: legacy /Users/dan/lpos-state is read-only and tracked as TD-LEGACY-LPOS-STATE
```

The dashboard URL must be clickable and must be the successfully probed deployed route. If shipping is genuinely blocked by an external credential, branch-protection decision, or unavailable deployment system, state the exact blocking evidence and still provide all completed implementation artifacts and commits. Do not replace execution with a new plan.

---

## 38. Prohibited shortcuts

The following do not count as implementation:

- Writing another policy-only Markdown file.
- Returning a dashboard URL without deploying/probing the route.
- Constructing pass objects in code.
- Tests that only assert fixture booleans.
- A manifest covering only documentation or a manually selected subset of app files.
- Silently skipping missing manifest inputs.
- Reusing evidence from a different commit, artifact, or release version.
- Calling missing data healthy.
- Writing mutable status into the immutable/source tree.
- Claiming an email was sent without delivery evidence.
- Claiming GitHub/wiki/Drive synchronization without verification.
- Deleting legacy ledgers or unrelated local changes.
- Declaring completion before rebuilding and verifying the final artifact.

---

# End of implementation order
