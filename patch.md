# LPOS Security and SOC 2 Readiness Remediation Patch

**Document owner:** Hermes release and compliance operator  
**Target:** LPOS v4.2.0 complete distribution  
**Target archive SHA-256:** `45d6cb6f1110c2c473b3a99f03bb22bd6d1f78dbf212deac434ff14fc23e8e69`  
**Source audit:** `LPOS_Compliance_Audit_Report_2026-07-22.md`  
**Priority:** P0 security remediation and release blocker  
**Required disposition:** Implement, independently review, re-test, publish, and include in the next full LPOS build

> **Important:** This patch can remediate the confirmed technical findings and make LPOS materially more ready for a SOC 2 examination. It must not cause LPOS, Hermes, documentation, dashboards, APIs, release notes, or marketing to claim “SOC 2 compliant,” “SOC 2 Type 2 compliant,” or “controls effective.” A Type 2 conclusion requires a defined service-organization scope, operating evidence across an agreed observation period, management’s assertion, and a report issued by an independent licensed CPA.

---

## 1. Mandatory instructions to Hermes

Hermes must treat this document as a binding security change order.

1. Create a protected remediation branch from the exact audited source revision. Use a name such as `security/soc2-readiness-remediation`.
2. Add this file to the repository root as **`patch.md`** and preserve its audit target hash and finding identifiers.
3. Implement every P0 and P1 requirement below. A finding may be closed only when all listed tests and acceptance criteria pass.
4. Keep external consequential adapters in record-only mode until the authenticated approval-ingestion requirements in LPOS-05 pass end to end.
5. Keep the dashboard loopback-only or disabled until the complete LPOS-06 boundary passes.
6. Do not restore command checks, shell alert transports, arbitrary credential-file paths, or unrestricted monitor URLs through a feature flag or undocumented compatibility switch.
7. Submit the implementation through a reviewed GitHub pull request. Direct commits to the protected release branch are prohibited.
8. After approval, Hermes must publish the final patch and its verification evidence to all of the following canonical LPOS destinations:
   - **Google Drive:** Upload `patch.md`, the final signed patch/release bundle, test evidence, and the remediation closure report to the controlled LPOS security/compliance release folder. Use restricted access and preserve version history.
   - **GitHub:** Commit `patch.md` at the repository root, link it from the pull request and release notes, and attach or link the signed release artifacts, SBOM, provenance, and verification results.
   - **Wiki:** Publish the operator-facing version under the LPOS security or patch-notes section, add it to the wiki index, and link back to the canonical GitHub revision. The wiki must state that this is readiness remediation, not a SOC 2 attestation.
   - **Next full build:** Include `patch.md` in the next complete LPOS source/release archive, list it in `RELEASE-MANIFEST.json` and `SHA256SUMS`, reference it from `CHANGELOG.md` and the release notes, and verify that it is present in the final distribution before signing.
9. Hermes must record the resulting Google Drive URL, GitHub issue/PR/commit/tag URLs, wiki URL, and next-build version in the completion record in Section 16. Publication is not complete until every field is populated and independently checked.
10. Hermes must not mark this patch “done” merely because code was merged. Completion requires the build, security, migration, documentation, publication, and re-audit gates in this document.

### Required publication filenames

Use stable names so all copies can be reconciled:

- `patch.md`
- `LPOS-Security-Remediation-Closure-<NEXT_VERSION>.md`
- `LPOS-Security-Test-Evidence-<NEXT_VERSION>.zip`
- `LPOS-<NEXT_VERSION>-SBOM.spdx.json` or an approved CycloneDX equivalent
- `LPOS-<NEXT_VERSION>-provenance.intoto.jsonl` or an approved signed provenance equivalent
- The signed release manifest, signature/certificate bundle, and final archive digest

Google Drive and the wiki are distribution channels, not substitutes for a protected evidence store or release-signing trust anchor.

---

## 2. Patch objectives and non-negotiable outcomes

This patch must deliver all of the following:

- Eliminate agent-controlled shell execution and arbitrary executable selection from monitor registration.
- Prevent connector credentials from being attached to arbitrary destinations and prevent unapproved SSRF paths.
- Replace caller-asserted approval identities with authenticated, replay-resistant provider assertions.
- Authenticate and harden every dashboard API boundary; keep non-loopback exposure disabled by default.
- Create runtime, monitor, dashboard, compliance, and database state with restrictive permissions independent of the process umask.
- Make local evidence tampering detectable and export evidence to an independently protected append-only destination when SOC 2 evidence collection is enabled.
- Stop the built-in readiness monitor from issuing false compliance or operating-effectiveness labels.
- Replace structural source-code proxies with outcome-based controls or an explicit `not_evidenced` result.
- Contain dashboard scanning to explicitly authorized roots, including symlink, junction, and kanban path handling.
- Put model hosts behind an enforceable sandbox/runner boundary with hard resource and output limits.
- Add authenticated release provenance, an SBOM, signed manifests, and a protected build workflow.
- Make full JSON Schema validation mandatory in clean offline installations.
- Correct documentation drift and generate factual counts from release metadata.
- Establish the organizational control register and evidence process required before a Type 2 examination can begin.

### Prohibited outcomes

The following are automatic patch failures:

- Returning `overall: compliant`, `effective`, or equivalent from a self-test.
- Counting control rows as separate audit executions.
- Silently treating missing evidence or missing validators as success.
- Allowing a raw `MessageIdentity` supplied by a general caller to authorize an action.
- Supporting string commands with `shell=True` anywhere in the monitor or alert path.
- Allowing an agent-written service record to choose an executable or arbitrary arguments.
- Sending a connector credential to a URL not bound to that connector’s approved origin.
- Binding the dashboard to a non-loopback address without explicit hardened reverse-proxy mode and authentication.
- Returning raw filesystem paths from an unauthenticated or unauthorized dashboard endpoint.
- Shipping a release whose authenticity depends only on checksums stored inside the same mutable archive.

---

## 3. Implementation order

### Phase P0 — immediate containment

Apply these controls before beginning broader refactoring:

- Remove `command` from `CHECKS` in `src/lpos_engine/monitor/checks.py`.
- Reject service registration records containing executable commands, command arguments, token paths, or arbitrary credentialed URLs.
- Remove or permanently disable `CommandTransport` in `src/lpos_engine/monitor/alert.py`.
- Force the dashboard to loopback-only and reject non-loopback `--host` values until hardened remote mode exists.
- Change the readiness output so it cannot emit `compliant` or `effective`, even before history redesign is complete.
- Create all state/config directories as `0700` and all sensitive files as `0600`; run a startup permission check.
- Keep every consequential external action adapter record-only.
- Disable credentialed custom monitor URLs and redirects until the safe outbound client is complete.

### Phase P1 — engineering remediation

Implement LPOS-01 through LPOS-12 and LPOS-14 below, including migrations and regression tests.

### Phase P2 — organizational readiness

Implement LPOS-13, operate the controls over the auditor-agreed period, resolve exceptions, and engage an independent CPA. P2 cannot be completed by source-code changes alone.

---

## 4. Cross-cutting secure primitives

Create reusable primitives before patching individual modules. Do not duplicate permission, URL, secret, or evidence logic across subsystems.

### 4.1 New secure filesystem module

Add `src/lpos_engine/security/secure_io.py` with at least:

- `ensure_private_dir(path, mode=0o700, strict=True)`
- `atomic_write_private(path, data, mode=0o600, fsync=True)`
- `open_private_read(path, approved_root, allow_symlink=False)`
- `validate_private_path(path, expected_owner=True, max_mode=0o600)`
- `repair_private_permissions(path)` with an emitted audit event
- Windows ACL equivalents or a documented fail-closed deployment requirement when equivalent enforcement is unavailable

Required behavior:

- Use secure creation flags; do not rely on the caller’s umask.
- Reject symlinks for secrets and mutable control files.
- Use a temporary file created in the target directory, set its mode before writing, flush and `fsync`, then `os.replace`.
- `fsync` the parent directory after security-sensitive replacements where supported.
- Check ownership and mode on startup. In strict production mode, fail closed for wrong ownership or group/other access.
- Create the SQLite database file before connecting with mode `0600`, and verify the SQLite `-wal` and `-shm` files after connection.

Use this module for database state, monitor files, dashboard state/auth material, compliance/readiness history, connector configuration, alert state, and evidence checkpoints.

### 4.2 New outbound network policy module

Add `src/lpos_engine/security/outbound.py` with:

- A typed `ConnectorOriginPolicy` bound to a connector ID.
- Allowed schemes, exact hosts, ports, redirect policy, and approved CIDRs.
- DNS resolution that validates every resolved IPv4 and IPv6 address.
- Default denial for loopback, link-local, multicast, unspecified, reserved, metadata endpoints, and private ranges.
- Explicit, administrator-approved private-network policies for named connectors that genuinely require private health endpoints.
- Redirect disabled by default. When enabled, validate every redirect target under the same policy before sending a request.
- Peer-address verification or connection pinning so DNS cannot be validated once and then silently resolved to another address at connection time.
- URL userinfo rejection and canonical hostname comparison.
- Response-size, header-size, timeout, and redirect-count limits.
- Error redaction that never includes authorization headers, tokens, secret paths, or full response bodies.

### 4.3 New evidence-integrity module

Add `src/lpos_engine/evidence/integrity.py` with:

- Canonical record hashing.
- Monotonic sequence validation.
- Previous-record hash chaining.
- Segment/checkpoint digests.
- A signer interface whose private key is not available to the LPOS runtime account.
- A write-only remote exporter interface for append-only/WORM storage.
- An independent verifier CLI that detects update, deletion, insertion, reordering, truncation, rollback, duplicate sequence, missing segment, clock anomaly, and checkpoint mismatch.

Local hash chaining is detection support, not independent assurance. The readiness status must remain `insufficient_evidence` when independent checkpointing/retention is required but not configured.

---

## 5. Finding remediation

## LPOS-01 — false SOC 2 Type 2 compliance/effectiveness status

**Severity:** Critical  
**Primary files:**

- `src/lpos_engine/compliance/audit.py`
- `src/lpos_engine/compliance/criteria.py`
- `src/lpos_engine/compliance/report.py`
- `src/lpos_engine/compliance/__main__.py`
- `src/lpos_engine/compliance/remediation.py`
- `docs/COMPLIANCE.md`
- `docs/wiki/includes/soc2-compliance.md`
- `tests/test_compliance.py`

### Required changes

1. Rename the user-facing feature to **Control Readiness Monitor**. A compatibility CLI alias may remain temporarily, but its output and help text must use readiness language.
2. Replace framework text such as `SOC 2 Type 2 Compliance` with `SOC 2 readiness mapping — not an attestation`.
3. Remove the `compliant` and `effective` result values from code, HTML, JSON, tests, examples, documentation, and schemas.
4. Use only these top-level readiness states:
   - `not_assessed`
   - `insufficient_evidence`
   - `control_gaps`
   - `readiness_demonstrated`
5. `readiness_demonstrated` is a technical readiness label only. It must include `attestation.is_attested=false` unless a separately configured, independently issued report record is present and validated.
6. Assign a cryptographically random `run_id` to every execution. Record one run envelope and associate every control result with that `run_id`.
7. Count `distinct_run_ids` and `distinct_run_dates`; never count per-control rows as runs.
8. Do not infer operating effectiveness from a pass ratio alone. Expose `observed_pass_rate` and `evidence_coverage`, not an auditor conclusion.
9. Require an explicit evidence policy before `readiness_demonstrated` is possible. The policy must define the observation window, expected frequency, minimum distinct run dates, maximum gaps, complete control scope, evidence-integrity requirement, and material-exception rule. Default policy state is insufficient.
10. A fresh install, a one-run history, sparse history, missing controls, malformed records, unverified integrity, or an open Critical/High exception must return `insufficient_evidence` or `control_gaps`.
11. Do not skip malformed history lines. Treat malformed, duplicate, out-of-sequence, or unverifiable records as integrity exceptions.
12. Stop rewriting and trimming the active history file. Rotate signed segments through the evidence-integrity module; retain according to the control-retention policy.

### Required status contract

The machine-readable output must contain at least:

```json
{
  "generated_at": "2026-07-22T00:00:00Z",
  "run_id": "CRUN-...",
  "program": "LPOS Control Readiness Monitor",
  "framework_mapping": "AICPA Trust Services Criteria mapping",
  "overall": "insufficient_evidence",
  "attestation": {
    "is_attested": false,
    "issued_by_cpa": false,
    "report_id": null,
    "report_period": null
  },
  "evidence_period": {
    "state": "insufficient",
    "window_days": 90,
    "distinct_runs": 1,
    "distinct_run_dates": 1,
    "days_covered": 0,
    "integrity_verified": false
  },
  "controls": [],
  "exceptions": []
}
```

### Required tests

- Zero history cannot return `readiness_demonstrated`.
- One run covering 21 controls is one run, not 21.
- Sparse runs, duplicated run IDs, timestamp gaps, current failures, historical failures, malformed lines, truncation, and hash-chain failures produce the correct non-success state.
- Report HTML and JSON contain no standalone claim of `COMPLIANT` or `effective`.
- Marketing/documentation tests fail when prohibited language appears without a validated independent report reference.

### Closure criteria

- All audit reproductions for the false-positive case fail safe.
- A fresh install clearly reports insufficient operating evidence.
- The only component allowed to record an actual attestation is a separate record representing an independently issued report; the self-monitor cannot mint it.

---

## LPOS-02 — structural proxy controls do not test control outcomes

**Severity:** High  
**Primary files:**

- `src/lpos_engine/compliance/controls.py`
- `src/lpos_engine/compliance/criteria.py`
- `src/lpos_engine/compliance/audit.py`
- New `compliance/control-register.schema.json`
- New `compliance/control-register.yaml` or JSON
- `tests/test_compliance.py`

### Required changes

1. Replace source-string and file-presence checks with an evidence-driven control model.
2. Every control definition must contain:
   - unique control ID and version
   - mapped criterion
   - risk addressed
   - control objective
   - control owner and backup owner
   - control type: automated, manual, hybrid, or third-party
   - frequency
   - population definition
   - evidence source and retention period
   - test procedure
   - exception threshold and escalation path
   - reviewer and review frequency
3. Every result must use one of:
   - `pass`
   - `fail`
   - `not_evidenced`
   - `not_applicable`
   - `error`
4. Missing organization-level evidence must be `not_evidenced`, never pass.
5. Automated technical controls must validate an outcome. Examples:
   - test control: verified execution result from the protected CI run for the exact commit, including command, environment, test count, exit code, and signed evidence digest
   - dashboard control: adversarial authentication/Host/Origin/CSRF test result, not a source-code constant
   - approval control: end-to-end signed-provider event test, not file presence
   - monitoring control: observed scheduled executions and alert-delivery evidence, not a catalog entry
   - availability control: successful backup and restore evidence measured against RPO/RTO, not backup documentation alone
   - change control: approved PR, reviews, protected build, signed provenance, test evidence, and release authorization
6. Separate technical control tests from human and third-party evidence. Do not automate a pass where human review is required.
7. Link every result to immutable evidence IDs and digests.
8. Require an independent mapping review before changing a criterion-to-control relationship.

### Required tests

- Deleting or disabling the actual control causes failure even when the documentation and source strings remain.
- Missing evidence produces `not_evidenced`.
- Evidence for another commit, control version, population, or period is rejected.
- Altered evidence is rejected by digest/signature validation.
- A reviewer can trace criterion → risk → control → owner → frequency → population → sample → evidence → exception → remediation.

---

## LPOS-03 — agent-registered monitor entries can execute arbitrary commands

**Severity:** Critical  
**Primary files:**

- `src/lpos_engine/monitor/checks.py`
- `src/lpos_engine/monitor/inventory.py`
- `src/lpos_engine/monitor/alert.py`
- `src/lpos_engine/monitor/audit.py`
- `docs/MONITOR.md`
- `docs/wiki/includes/connector-health-monitor.md`
- `tests/test_monitor.py`
- `tests/test_hardening.py`

### Required changes

1. Delete `check_command` from the runtime registry. Do not retain a hidden switch that re-enables it.
2. Delete `CommandTransport` and reject `smtp.json` entries containing `command`.
3. Agent-writable records such as `state/services.json` and `monitor/registered-services.json` may contain only:
   - service identity and display metadata
   - a reference to a pre-approved `check_id`
   - a narrow, schema-validated set of non-secret parameters declared by that check
4. Ignore and log a security exception for agent-supplied `command`, `argv`, executable path, environment, token file, arbitrary URL, or transport configuration.
5. Store administrator-approved check definitions outside agent-writable state, for example under `config/approved-monitor-checks.json`, with restrictive permissions and a signed configuration digest.
6. Prefer built-in in-process checks. If an executable check is unavoidable:
   - require an absolute executable path
   - require a pinned executable digest
   - use a fixed, administrator-defined argument template
   - reject PATH lookup and symlinks
   - use a minimal environment and explicit working directory
   - run under a dedicated monitor account/sandbox
   - enforce CPU, memory, process, file, descriptor, timeout, stdout, and stderr limits
   - terminate the entire process group on limit or timeout
7. Run the monitor with no write access to the LPOS database, no general credential directory access, a read-only code/config view, and only connector-specific network egress.
8. Audit every approved-check configuration change and export the event to protected evidence storage.

### Required tests

- String commands, shell metacharacters, lists of arbitrary executable arguments, PATH substitution, symlinked executables, inherited secrets, child-process escape, timeout, and output flooding are rejected or contained.
- An agent-written service entry cannot cause any process to start.
- Only an authenticated administrator change to the approved-check registry can add a new executable check.
- `smtp.json` with a command transport fails closed.

### Closure criteria

The original shell-command reproduction must create no marker and must produce a rejected configuration/security event.

---

## LPOS-04 — credential exfiltration and SSRF in monitor checks

**Severity:** High  
**Primary files:**

- `src/lpos_engine/monitor/checks.py`
- New `src/lpos_engine/security/outbound.py`
- New `src/lpos_engine/security/secrets.py`
- Monitor configuration schemas and docs
- `tests/test_monitor.py`
- New `tests/test_monitor_network_security.py`

### Required changes

1. Replace `_http_get` with the policy-enforcing outbound client from Section 4.2.
2. Bind every credential to a named connector and exact approved origin.
3. The GitHub check must use the approved GitHub API origin from administrator configuration. A custom URL must never receive a GitHub authorization header.
4. Remove arbitrary `token_file` support from agent/user-supplied connector records.
5. Accept only a secret-manager handle or a file reference under a dedicated administrator-owned secrets root. Resolve the path, reject symlinks, verify owner/mode, and open without following links.
6. Do not fall back automatically to a broadly scoped ambient `GITHUB_TOKEN` in production. Connector credentials must be explicit and least-privileged.
7. Disable redirects by default. Validate every redirect before following it and never carry an authorization header across an origin change.
8. Block unapproved loopback, private, link-local, multicast, reserved, metadata, and alternate-scheme destinations for both URL and host/port checks.
9. For named internal connectors, require explicit administrator approval of hostnames/CIDRs and ports. The approval must be outside agent-writable state.
10. Redact request headers, tokens, secret paths, query credentials, and sensitive response fragments from status, alerts, exceptions, and evidence.

### Required tests

Cover at least:

- custom URL with GitHub token
- URL userinfo
- HTTP downgrade from HTTPS
- redirect to another origin
- redirect to loopback/private/metadata address
- IPv4 and IPv6 private/link-local/loopback forms
- alternative numeric IP encodings where supported by parsers
- DNS resolution change/rebinding
- symlinked secret file
- secret path traversal and path outside approved root
- wrong file owner/mode
- oversized response and header output
- credential redaction in errors and alerts

### Closure criteria

The audit canary receiver must receive no credential, and no network request may occur after a secret-path or origin-policy rejection.

---

## LPOS-05 — approval identity is caller asserted rather than authenticated

**Severity:** High  
**Primary files:**

- `src/lpos_engine/models.py`
- `src/lpos_engine/approvals.py`
- `src/lpos_engine/engine.py`
- `src/lpos_engine/store.py`
- New SQL migration for verified inbound events/assertions
- Approval/message JSON schemas
- Channel adapter implementations
- `tests/test_approvals_actions.py`
- `tests/test_integration_boundaries.py`

### Required changes

1. Introduce a trusted channel-ingestion service that verifies the provider’s signed webhook/event or an authenticated interactive session before LPOS treats a sender as the Principal.
2. Add a persisted `VerifiedMessageAssertion` model containing at least:
   - assertion ID
   - adapter ID and adapter version
   - channel and provider
   - provider event/message/thread IDs
   - normalized sender/principal ID
   - verification method
   - key/webhook-secret version or identity-provider session ID
   - raw event digest
   - received and verified timestamps
   - replay key/nonce
   - assertion expiry
   - assertion signature/MAC
3. The signer/verifier key must be inaccessible to general LPOS callers and model/agent code.
4. Change `LPOSRuntime.grant_action_approval` and `ApprovalService.grant` so they accept a verified assertion ID or capability, not a raw `MessageIdentity` plus caller-provided `verified_identity`.
5. Derive the verified identity from the stored assertion. Remove the caller’s ability to choose it.
6. Bind the assertion to the exact approval request, action hash, provider event, channel thread/correlation ID, and expiry.
7. Enforce replay protection at ingestion and grant time with database uniqueness constraints and atomic consumption.
8. Persist the original provider-event digest and verification metadata as protected evidence.
9. Add an adapter enablement gate. A live consequential adapter remains disabled until its full outbound request → inbound signed response → correlation → identity → exact-action authorization test passes.
10. Preserve `MessageIdentity` only as descriptive event metadata; document that it is not proof of authentication.

### Required tests

- Constructing a `MessageIdentity` with an allowlisted sender cannot create a grant.
- Missing or invalid provider signature, wrong secret/key, altered body, stale timestamp, wrong event ID, wrong thread, replay, unregistered adapter, expired assertion, and forged assertion signature are rejected.
- A verified assertion for one request/action cannot authorize another.
- Replay attempts remain rejected under concurrent execution.
- Live adapter configuration is refused until the channel-specific end-to-end test record exists for the current adapter version.

### Migration requirements

Add tables for inbound provider events and verified assertions with unique replay keys, verification metadata, raw-event digest, status, and consumption timestamps. Existing approval grants created from raw identities must not be silently upgraded to verified. Mark them legacy/untrusted and require re-approval before live execution.

---

## LPOS-06 — unauthenticated dashboard mutation and missing web boundary controls

**Severity:** High  
**Primary files:**

- `src/lpos_engine/dashboard/server.py`
- `src/lpos_engine/dashboard/ui.py`
- `src/lpos_engine/dashboard/state.py`
- New dashboard authentication/session module
- `docs/DASHBOARD.md`
- `docs/wiki/working-with/using-the-dashboard.md`
- `tests/test_dashboard.py`
- New `tests/test_dashboard_security.py`

### Required changes

1. Keep `127.0.0.1`/`::1` as the only accepted bind addresses in local mode. Reject wildcard, LAN, and public addresses.
2. Remove unrestricted `--host`. Replace it with an explicit `--remote-behind-proxy` mode that requires:
   - trusted reverse-proxy configuration
   - TLS termination
   - an authenticated identity provider or approved bearer/session auth
   - a configured trusted-proxy list
   - strict forwarded-header handling
3. Generate a 256-bit or stronger dashboard secret on first use with mode `0600`.
4. Require authentication on every `/api/*` route. A browser session must use an `HttpOnly`, `SameSite=Strict` cookie where applicable; bearer authentication must use the `Authorization` header and never a query string.
5. Require a session-bound CSRF token for all state-changing methods, even in local mode. Reject missing or mismatched tokens.
6. Validate `Host` against the actual bound host/port and a strict allowlist.
7. Enforce an exact Origin policy for browser requests. Reject attacker-controlled, absent where required, `null`, or cross-origin values.
8. Require `Content-Type: application/json` for JSON API POST requests.
9. Set a small maximum request body size, query size, URL length, header size where the server permits, and search result/work limits.
10. Return `401` or `403` before reading or mutating protected state when authentication or request-origin checks fail.
11. Replace raw exception details with a generic request ID; log a sanitized server-side error.
12. Add security headers to HTML and JSON responses:
    - Content-Security-Policy with `default-src 'self'` and no unsafe remote sources
    - `frame-ancestors 'none'` and/or `X-Frame-Options: DENY`
    - `X-Content-Type-Options: nosniff`
    - `Referrer-Policy: no-referrer`
    - `Permissions-Policy` denying unneeded features
    - `Cache-Control: no-store`
13. Do not return raw absolute paths in project/search responses. Return opaque project/file IDs and authorize every follow-up lookup.
14. Audit dashboard authentication failures, state mutations, configuration changes, and remote-mode startup.

### Required tests

- Unauthenticated GET/POST returns `401/403` and does not mutate state.
- Wrong bearer/session, missing/invalid CSRF, cross-origin request, attacker Host, DNS-rebinding Host, `text/plain`, form content, oversized body, malformed content length, and non-loopback bind are rejected.
- Security headers are present.
- Internal exceptions do not disclose paths, stack details, tokens, or class names.
- Remote mode refuses startup unless all hardened-proxy requirements are present.

---

## LPOS-07 — sensitive state is world-readable under default umask

**Severity:** High  
**Primary files:**

- `src/lpos_engine/store.py`
- All monitor persistence modules
- All dashboard persistence/auth modules
- All compliance/readiness persistence modules
- Installer and doctor commands
- `docs/SECURITY.md`
- `tests/test_store.py`
- `tests/test_hardening.py`

### Required changes

1. Use the secure I/O primitives in Section 4.1 for every state/config/evidence file.
2. Create state and configuration directories as `0700` and sensitive files as `0600`, regardless of umask.
3. Secure the SQLite database, WAL, SHM, backups, exports, temporary files, and migration backups.
4. At startup and in `lpos doctor`, verify ownership and permissions for:
   - database and sidecar files
   - monitor inventory/status/alerts/config
   - dashboard state and auth secrets
   - compliance/readiness history/status/staging
   - connector secret references
   - exports and backup destinations
5. In strict production mode, fail closed when ownership or permissions are unsafe. In local developer mode, repair where safe and emit an audit event.
6. Provide Windows ACL enforcement or make unsupported ACL conditions a deployment blocker for confidentiality scope.
7. Add a deployment control requiring encrypted host storage and encrypted backups for confidentiality scope. Document key custody, rotation, restore access, retention, and secure disposal.
8. Redact secrets and sensitive fields from logs, monitor errors, evidence bundles, and support exports.

### Required tests

- Fresh files remain private under umasks `000`, `002`, `022`, and `077`.
- Startup detects and handles `0644`, group-writable, wrong-owner, symlink, and parent-directory permission failures.
- WAL/SHM, temporary files, backups, and exports are private.
- A non-owner local test user cannot read sensitive state on supported platforms.

---

## LPOS-08 — audit and compliance evidence can be rewritten by the runtime account

**Severity:** High  
**Primary files:**

- `src/lpos_engine/store.py`
- `src/lpos_engine/sql/001_initial.sql`
- New `src/lpos_engine/sql/002_evidence_integrity.sql`
- `src/lpos_engine/compliance/audit.py`
- New evidence integrity/export modules
- New `lpos evidence verify` and `lpos evidence reconcile` commands
- `tests/test_store.py`
- `tests/test_compliance.py`
- New `tests/test_evidence_integrity.py`

### Required changes

1. Add event hash-chain fields such as `previous_event_hash`, `event_hash`, and chain/segment identity. Compute the event hash from canonical event content plus the previous hash and sequence.
2. Backfill existing events during a controlled migration and record a signed migration checkpoint. Preserve the original database backup with private permissions.
3. Strengthen local triggers to reject update/delete of evidence rows and protected chain fields, while documenting that the database owner can still bypass local triggers.
4. Replace compliance history rewrite/trim behavior with append-only signed segments.
5. Produce periodic signed checkpoints using a key unavailable to the LPOS runtime account.
6. Export events and readiness results in near real time to an independently administered append-only/WORM destination using a write-only credential.
7. Separate application, database administration, evidence custodian, and audit reader roles in production deployments.
8. Reconcile local and remote sequence counts/digests daily. Alert on gaps, rewrites, duplicate sequence, out-of-order records, clock anomalies, missed exports, or retention-lock changes.
9. The readiness monitor must expose `integrity_verified=false` and remain `insufficient_evidence` when the independent checkpoint or remote retention requirement is not met.

### Required tests

The independent verifier must detect:

- payload update
- row deletion
- insertion between records
- reordering
- truncation
- database rollback to an older snapshot
- duplicated sequence/event ID
- missing remote segment/checkpoint
- altered checkpoint signature
- clock regression outside policy

The application account must be unable to alter remote retained evidence or access the checkpoint signing key.

---

## LPOS-09 — dashboard scanner escapes approved roots

**Severity:** Medium  
**Primary files:**

- `src/lpos_engine/dashboard/scanner.py`
- `src/lpos_engine/dashboard/server.py`
- Dashboard root configuration schema
- `tests/test_dashboard.py`
- New `tests/test_scanner_containment.py`

### Required changes

1. Resolve the Hermes root and every configured extra root before scanning.
2. Extra roots must be explicit administrator-approved root objects, not arbitrary path strings. Each must have a stable ID and authorization policy.
3. Reject symlinked or junction project roots and entries. Use non-following filesystem APIs where available.
4. Resolve every project and kanban card path and require it to be inside one approved root.
5. Reject absolute kanban paths unless they resolve inside an explicitly approved root. Reject `..` traversal and ambiguous path forms.
6. Use `os.walk(..., followlinks=False)` and re-check containment during traversal. Protect against race-time path replacement using file-descriptor-relative/non-following operations where supported.
7. Do not return absolute paths to the client. Return opaque IDs and resolve them server-side after authorization and containment checks.
8. Cap scanned entries, depth, file count, path length, and total processing time per request.

### Required tests

Cover symlinks, directory junctions, absolute card paths, relative traversal, nested symlink swaps, race-time path replacement, external extra roots without authorization, and supported Windows/POSIX filesystem behavior.

---

## LPOS-10 — subprocess model host is not sandboxed and output cap is post-buffering

**Severity:** Medium  
**Primary files:**

- `src/lpos_engine/adapters/subprocess_host.py`
- New sandbox runner abstraction
- Adapter configuration schema/docs
- `tests/test_schemas_cli_adapters.py`
- New `tests/test_subprocess_sandbox.py`

### Required changes

1. Replace direct `subprocess.run(..., capture_output=True)` with a sandbox runner that streams stdout/stderr and enforces hard byte caps while the process is running.
2. Start the child in its own process group/session and terminate the entire group on timeout, output limit, or cancellation.
3. Use an explicit minimal environment allowlist. Do not inherit the parent environment or secrets.
4. Require an explicit working directory, absolute executable path, and pinned executable digest/version.
5. Do not use PATH lookup. Reject symlinked executables and unapproved interpreter/script combinations.
6. Apply CPU, memory, file-size, process-count, open-file, and wall-clock limits using an OS-supported sandbox, container, job object, or dedicated launcher.
7. Give the model host only the filesystem inputs it needs. It must not read the LPOS database, compliance evidence, connector secrets, or unrelated user files.
8. Deny network access by default. Grant connector-specific egress only through an explicit policy and short-lived credential.
9. Treat `local`, model class, and capability declarations as policy inputs, not proof that the host is safe. Verify the deployed sandbox before enabling it.
10. If a supported secure sandbox backend is unavailable, fail closed for untrusted/third-party model hosts.

### Required tests

- Parent canary environment variables are absent.
- LPOS database and secret directories are inaccessible.
- Output never exceeds the configured in-memory/on-disk cap.
- Child and descendant processes are killed on timeout or limit.
- CPU/memory/process/file limits operate.
- Executable path/digest changes are rejected and audited.

---

## LPOS-11 — release integrity lacks publisher authenticity and provenance

**Severity:** Medium  
**Primary files:**

- `verify_release.py`
- `tools/reseal.py`
- `RELEASE.json`
- `RELEASE-MANIFEST.json`
- `SHA256SUMS`
- Protected CI release workflow
- Installer scripts
- `tests/test_v4_integrated_distribution.py`
- `tests/test_publication.py`

### Required changes

1. Keep internal checksums, but add an external trust anchor: an organization-approved signing mechanism with protected signing identity, key rotation, and revocation.
2. Sign the canonical release manifest and final archive digest. Verify the signature and trusted identity before installation.
3. Publish the expected archive digest and signer identity through an independent authenticated release channel.
4. Generate and ship an SPDX or CycloneDX SBOM.
5. Generate signed build provenance/attestation that identifies source revision, protected workflow, builder, dependencies, commands, test results, and produced artifacts.
6. Move release creation to a protected CI workflow with branch protection, required review, environment approval, and least-privileged publishing credentials.
7. `tools/reseal.py` may create an **unsigned development draft** only. It must not produce an artifact that the production verifier treats as publisher-authenticated.
8. Installer verification must fail when signature, provenance, trusted signer, manifest/archive digest, or required SBOM is absent or invalid.
9. Retain PR review, test, approval, build, signing, and publication evidence for each release.
10. The next full build must include this `patch.md` in the signed manifest and checksum list.

### Required tests

- A locally changed and re-sealed bundle fails production verification.
- A valid release verifies archive digest, manifest signature, trusted signer, source revision, protected workflow, tests, provenance, and SBOM.
- Revoked/expired/untrusted signer, altered SBOM, altered provenance, and mismatched commit fail closed.
- Offline verification works with the bundled public trust material and revocation policy snapshot defined by the release process.

---

## LPOS-12 — clean offline install silently downgrades schema validation

**Severity:** Medium  
**Primary files:**

- `pyproject.toml`
- `src/lpos_engine/cli.py`
- `install.py`
- `INSTALL.sh`, `INSTALL.ps1`, `INSTALL.cmd`
- `Packages/`
- `verify_release.py`
- `tests/test_schemas_cli_adapters.py`
- `tests/test_v4_integrated_distribution.py`

### Required changes

1. Make the full JSON Schema validator a required runtime/offline dependency, or bundle an equivalent complete validator.
2. Include all dependency wheels required for a clean offline installation in `Packages/`, with hashes and license metadata.
3. Remove the ImportError success path from `_validate_schemas`.
4. Fail installation, `doctor`, and release verification when full meta-schema validation is unavailable or fails.
5. Record validator name/version, schema count, schema digests, and validation result in installation and release evidence.
6. Ensure installer and `doctor` call the same validation function and produce identical decisions.

### Required tests

- A syntactically valid but meta-schema-invalid schema fails clean offline installation.
- Missing validator dependency fails closed.
- Root and packaged schema sets are fully validated and byte-equivalent.
- Installer and doctor results match exactly.

---

## LPOS-13 — organization-level controls and Type 2 operating evidence are missing

**Severity:** High  
**Nature:** Governance and operations; not solvable by code alone

### Required artifacts

Create a controlled compliance workspace containing:

- SOC 2 system description aligned to the applicable Description Criteria
- management assertion draft reviewed by the selected CPA firm
- service and product boundary, architecture, data-flow, trust-boundary, and subservice-organization diagrams
- customer commitments and system requirements
- data inventory, classification, retention, deletion, and encryption requirements
- risk register with periodic review and risk acceptance workflow
- control register using the fields defined in LPOS-02
- control-owner RACI and evidence calendar
- IAM policy, joiner/mover/leaver procedure, privileged-access process, and periodic access reviews
- security awareness and personnel-control evidence
- vendor/subservice-organization inventory, due diligence, contracts, and monitoring
- vulnerability, dependency, patch, and secure change-management procedures
- incident-response plan, exercises, incidents, lessons learned, and corrective actions
- backup, restore, RPO/RTO, disaster-recovery, and capacity evidence
- confidentiality, key-management, backup encryption, retention, and secure-disposal evidence
- exception, remediation, retest, and management-disposition workflow
- privacy scope determination and, when in scope, privacy control inventory and evidence

### Required operating process

1. Engage an independent CPA firm for readiness, scope, criteria, observation period, and sampling decisions.
2. Obtain CPA review of the system description and control matrix before starting the Type 2 period.
3. Operate each control at its required frequency and retain protected evidence.
4. Review evidence completeness at least monthly and remediate exceptions promptly.
5. Preserve population data so the auditor can select samples independently.
6. Do not allow the LPOS readiness monitor to substitute for management review or auditor testing.
7. Do not claim Type 2 compliance until the independent report is issued and the claim accurately reflects its scope and period.

### Closure criteria

- CPA-reviewed system description and management assertion exist.
- Every scoped criterion has designed controls and retained operating evidence across the agreed period.
- Exceptions include impact, root cause, remediation, retest, and management disposition.
- A licensed independent CPA issues the SOC 2 Type 2 report.

---

## LPOS-14 — documentation and release claims drift

**Severity:** Low  
**Primary files:**

- `docs/wiki/getting-started/first-hour.md`
- `docs/wiki/administration/configuration.md`
- `docs/wiki/patch-notes/index.md`
- `README.md`
- `CHANGELOG.md`
- `tools/build_wiki.py`
- `tests/test_wiki.py`
- `tests/test_v4_integrated_distribution.py`

### Required changes

1. Correct Standing Operation counts to match the canonical catalog.
2. Correct schema-validation wording so it describes full mandatory validation after LPOS-12.
3. Generate version, operation count, specialist count, benchmark count, schema count, and validation capability statements from canonical release metadata.
4. Add semantic documentation tests, not only link/build tests.
5. Add a wiki patch note for this remediation and link it from the patch-note index.
6. Ensure Google Drive, GitHub, wiki, release notes, CLI help, HTML reports, and next-build documentation use the same approved readiness/attestation language.

### Required tests

Any mismatch between doctor/release output and documented version/count/validation statements must fail CI.

---

## 6. Database and data-format migrations

Use forward-only, checksummed migrations. Do not silently reinterpret legacy evidence as trusted.

### Required migration set

At minimum, add migrations for:

- verified inbound provider events
- signed verified-message assertions
- approval assertion references and legacy trust status
- event hash-chain fields/checkpoints
- evidence-export status and reconciliation
- control-readiness run envelopes and result references, if stored in SQLite

### Migration safety

1. Stop LPOS services before migration.
2. Create a private encrypted backup and record its digest.
3. Validate current database integrity and migration ledger.
4. Apply migrations in one controlled maintenance procedure.
5. Verify permissions for database, WAL, SHM, and backups.
6. Run post-migration integrity, event-chain, approval, and record-only action tests.
7. Mark legacy raw-identity grants untrusted and unusable for live actions.
8. Mark legacy compliance history as `legacy_unverified`; do not count it toward operating evidence unless independently validated.

Rollback must never re-enable the vulnerable dashboard, monitor command execution, or raw-identity authorization. Prefer a forward fix. If application rollback is unavoidable, keep the dashboard/monitor disabled and external actions record-only.

---

## 7. Required security regression suite

Add focused test modules so the original exploit paths remain closed:

- `tests/test_readiness_status_security.py`
- `tests/test_control_evidence_model.py`
- `tests/test_monitor_trust_boundary.py`
- `tests/test_monitor_network_security.py`
- `tests/test_verified_identity_ingestion.py`
- `tests/test_dashboard_security.py`
- `tests/test_secure_storage.py`
- `tests/test_evidence_integrity.py`
- `tests/test_scanner_containment.py`
- `tests/test_subprocess_sandbox.py`
- `tests/test_release_authenticity.py`
- `tests/test_schema_gate.py`
- `tests/test_documentation_semantics.py`

### Mandatory CI matrix

- Python 3.11, 3.12, and 3.13
- Supported Linux, macOS, and Windows behavior where platform-specific controls are claimed
- Clean offline install from the final `Packages/` directory
- Full tests and deterministic evaluations
- Full schema meta-validation
- Release signature/provenance/SBOM verification
- Database migration from a v4.2.0 fixture
- Original audit reproduction suite, changed so every exploit attempt is rejected or contained
- No external internet requirement for the core test suite; use loopback fixtures for network security cases

### Coverage gate

- Do not reduce overall coverage.
- Security-sensitive changed modules must reach at least 90% line coverage and 85% branch coverage, with explicit adversarial tests for error paths.
- `monitor/checks.py`, dashboard request handling, approval ingestion, secure I/O, evidence verification, and the sandbox runner are release-blocking coverage targets.

### Additional analysis gates

Run organization-approved static analysis, dependency vulnerability scanning, secret scanning, license/SBOM validation, and packaging integrity checks. Findings rated Critical or High block release unless formally risk-accepted by authorized management and disclosed to the auditor; this patch’s confirmed Critical/High findings may not be risk-accepted as a substitute for remediation.

---

## 8. Release and deployment procedure

### Pre-release

- [ ] Every finding has an implementation owner and reviewer.
- [ ] P0 containment is active in all deployed environments.
- [ ] All code and configuration changes are in a reviewed GitHub PR.
- [ ] Database migration has been tested from an unmodified v4.2.0 fixture.
- [ ] All mandatory CI gates pass on the final commit.
- [ ] The independent security reviewer re-runs the original reproductions.
- [ ] Documentation and wiki are generated from the final commit.
- [ ] SBOM and signed provenance are generated by protected CI.
- [ ] Final manifest and archive digest are signed by the approved release identity.

### Deployment

1. Back up database/configuration/evidence privately and record digests.
2. Stop dashboard, monitor, scheduler, and LPOS runtime processes.
3. Deploy the signed build only after signature/provenance verification.
4. Apply migrations.
5. Rotate credentials that may have been exposed to monitor paths, including GitHub and SMTP credentials used during prior operation.
6. Generate new dashboard session/auth material.
7. Replace service checks with approved check IDs; remove all legacy command/custom credentialed URL definitions.
8. Start services under their dedicated least-privileged accounts/sandboxes.
9. Run post-deploy doctor, permission, evidence-chain, dashboard boundary, monitor, and record-only action checks.
10. Keep live consequential adapters disabled until the verified channel-ingestion gate passes.
11. Monitor security events and evidence export continuously during the stabilization period.

### Rollback

A rollback must use a signed, non-vulnerable build. Do not roll back to unpatched v4.2.0 with vulnerable features enabled. When no safe build is available, stop affected services and retain record-only operation while correcting forward.

---

## 9. Independent re-audit gate

The implementation team must not self-close the findings. Assign an independent reviewer who did not author the relevant changes.

The reviewer must:

- verify the exact final archive digest
- install from the clean offline bundle
- run all tests/evaluations and the original reproduction script
- review the security boundary changes manually
- verify database migration and legacy-data handling
- verify final file permissions and process privileges
- verify release signature, signer trust, provenance, and SBOM
- verify Google Drive, GitHub, wiki, and next-build publication records
- issue a closure report for each finding with evidence IDs and residual risk

A finding is `Closed` only when its acceptance criteria are met. Otherwise use `Open`, `Partially remediated`, or `Risk accepted` with documented authority. Critical/High technical findings in this patch must be closed before production enablement.

---

## 10. SOC 2 claim gate

After technical closure, LPOS remains at **SOC 2 readiness**, not Type 2 compliant, until all of the following are true:

- the service-organization scope and system description are complete
- management has approved the control design and assertion
- the CPA firm has agreed on criteria and observation period
- controls have operated and evidence has been retained across that period
- exceptions have been remediated and retested or properly disclosed
- the independent CPA has issued the Type 2 report

Only then may approved communications state that the organization has received a SOC 2 Type 2 report, and the wording must accurately describe the report’s scope and period. The software must still not self-issue the conclusion.

---

## 11. Definition of done by finding

| Finding | Release-blocking completion condition |
|---|---|
| LPOS-01 | No self-issued compliance/effectiveness label; distinct runs and insufficient-evidence logic verified. |
| LPOS-02 | Outcome/evidence controls implemented; missing organization evidence is not passed. |
| LPOS-03 | Agent registration cannot execute any process; command transport removed. |
| LPOS-04 | Credential-origin binding and SSRF policy pass all redirect/DNS/IP/secret-path tests. |
| LPOS-05 | Only authenticated provider assertions can grant approval; raw identity reproduction fails. |
| LPOS-06 | All APIs authenticated; CSRF/Host/Origin/body limits and loopback enforcement pass. |
| LPOS-07 | Sensitive state is private regardless of umask and is checked at startup/doctor. |
| LPOS-08 | Tampering is independently detectable and evidence is exported to protected retention where required. |
| LPOS-09 | Scanner cannot escape approved roots through symlinks, junctions, card paths, or races. |
| LPOS-10 | Enforced sandbox and streaming resource limits protect secrets and memory/process boundaries. |
| LPOS-11 | Final build has trusted signature, SBOM, provenance, protected CI evidence, and independent digest publication. |
| LPOS-12 | Full schema validation is mandatory and works in the clean offline install. |
| LPOS-13 | CPA-reviewed scope/control design and period evidence exist; final closure requires an issued Type 2 report. |
| LPOS-14 | Documentation values are generated/semantically tested and all distribution channels are synchronized. |

---

## 12. Hermes next-full-build gate

Hermes must add the remediation to the **next full LPOS build**, not only to a hotfix folder or wiki page.

The next full build fails release verification unless:

- `patch.md` exists at the archive root.
- The exact file digest appears in `RELEASE-MANIFEST.json` and `SHA256SUMS`.
- `CHANGELOG.md` identifies all LPOS finding IDs addressed.
- The release notes link to the GitHub pull request and wiki page.
- The source, wheel/package data where applicable, documentation, schemas, installer, and tests are mutually consistent.
- The build contains required dependency wheels for offline schema validation.
- The build contains its SBOM, signed provenance, signed manifest, and verification material.
- The original security reproduction suite passes in fail-safe form against the final archive.
- The final signed archive uploaded to Google Drive is byte-for-byte identical to the GitHub release artifact and the artifact verified for wiki documentation.

Hermes must compare SHA-256 values across Google Drive and GitHub after upload. The wiki should publish the verified digest but should not host a separately rebuilt binary.

---

## 13. Required GitHub workflow

Hermes must create or update:

- A tracking issue containing all 14 finding IDs.
- One protected remediation branch.
- One or more reviewed pull requests with finding IDs in commit messages.
- CODEOWNERS or equivalent required reviewers for monitor, approval, dashboard, evidence, release, and compliance code.
- Protected CI jobs for the mandatory matrix.
- A protected release environment for signing and publication.
- A release entry that includes the signed artifacts, `patch.md`, closure report, SBOM, provenance, and checksums.

The final PR description must contain:

- audited source hash
- before/after security behavior
- migration impact
- test and reproduction results
- residual risks
- rollback constraints
- links to Google Drive and wiki publication records
- planned next full build version

---

## 14. Required wiki update

Hermes must publish a page titled similar to:

`LPOS <NEXT_VERSION> Security and SOC 2 Readiness Remediation`

The page must include:

- affected versions
- severity and summary of each finding
- immediate operator containment
- upgrade/migration steps
- credential rotation guidance
- behavior changes and compatibility impact
- validation commands
- residual organizational SOC 2 requirements
- GitHub canonical revision and signed release digest
- explicit statement that the patch does not itself constitute a SOC 2 Type 2 report

Update `docs/wiki/patch-notes/index.md`, relevant monitor/dashboard/approval/security pages, and any external wiki index maintained by Hermes.

---

## 15. Required Google Drive publication

Hermes must upload the final, reviewed materials to the controlled LPOS Google Drive security/compliance folder:

- `patch.md`
- final signed source/release archive
- closure report
- test/evaluation output
- original reproduction results and remediated results
- SBOM
- signed provenance
- signed manifest and archive digest
- migration runbook
- wiki export or link record

Access must be restricted to authorized personnel and auditors as appropriate. Preserve version history. Do not place runtime credentials, raw secrets, personal data, or unredacted sensitive logs in the folder.

The Drive record must identify the exact GitHub commit/tag and final archive SHA-256. Hermes must verify that the uploaded archive’s digest matches the GitHub release artifact.

---

## 16. Hermes completion record

Hermes must fill this block in the merged `patch.md` or in a linked signed closure record. Empty fields block completion.

```yaml
patch_completion:
  target_audit_date: "2026-07-22"
  audited_archive_sha256: "45d6cb6f1110c2c473b3a99f03bb22bd6d1f78dbf212deac434ff14fc23e8e69"
  remediation_owner: ""
  independent_reviewer: ""
  github:
    repository: ""
    tracking_issue: ""
    pull_request: ""
    merge_commit: ""
    release_tag: ""
    release_url: ""
  google_drive:
    folder_url: ""
    patch_file_url: ""
    closure_package_url: ""
    verified_archive_sha256: ""
  wiki:
    page_url: ""
    index_url: ""
    canonical_revision: ""
  next_full_build:
    version: ""
    build_id: ""
    release_date: ""
    archive_name: ""
    archive_sha256: ""
    patch_manifest_entry_verified: false
    schema_validator_bundled: false
    signed_manifest_verified: false
    sbom_verified: false
    provenance_verified: false
  testing:
    unit_and_integration: ""
    deterministic_evaluations: ""
    clean_offline_install: ""
    original_reproductions: ""
    migration_test: ""
    independent_reaudit_report: ""
  findings:
    LPOS-01: "Open"
    LPOS-02: "Open"
    LPOS-03: "Open"
    LPOS-04: "Open"
    LPOS-05: "Open"
    LPOS-06: "Open"
    LPOS-07: "Open"
    LPOS-08: "Open"
    LPOS-09: "Open"
    LPOS-10: "Open"
    LPOS-11: "Open"
    LPOS-12: "Open"
    LPOS-13: "Open"
    LPOS-14: "Open"
  soc2_type2_report:
    issued: false
    auditor: ""
    report_period: ""
    report_date: ""
    approved_claim_language: ""
```

---

## 17. Final acceptance statement

Hermes may mark the engineering patch complete only after:

- all Critical and High technical findings are independently closed;
- all Medium and Low code/documentation findings are closed or have an authorized, time-bound remediation plan that does not expose production users;
- the final signed build passes every release and security gate;
- `patch.md` and closure evidence are present in Google Drive, GitHub, and the wiki;
- `patch.md` is included and verified in the next full build; and
- all publication links and artifact digests are recorded in Section 16.

Hermes must continue to label LPOS as **SOC 2 readiness in progress** until an independent CPA issues the applicable SOC 2 Type 2 report.
