# LPOS Changelog

## 4.3.0 — 2026-07-23

Feature release: the Sentinel Adversarial Assurance Guild (GUILD-039) as an additive
assurance layer on the hardened v4.2.1 base. Adds SPECIALIST-033 (Adversarial Assurance
Engineer) and SO-026 (Continuous Adversarial Assurance). Sentinel passively scans every
persisted Chip artifact revision; its raw output starts explicitly untrusted and must
pass LPOS's ordinary fresh-context independent adversarial review plus deterministic
structural verification before any finding can block completion, authorize anything, or
be reported to the Principal as fact. Constitution Article VIII codifies that no guild is
trusted by designation and no producer may approve, remediate, or close its own work.
Two improvements over the development candidate: (1) Sentinel's own record tables are
anchored to the 4.2.1 tamper-evident hash-chained event stream and reconciled by
integrity_check, so editing a stored record or flipping a review's trust decision is
detected; (2) the active-engagement authorization gate goes through the 4.2.1
verified-channel assertion path, so a fabricated MessageIdentity with no registered
channel cannot authorize an engagement. Counts: specialists 32→33, standing operations
25→26, benchmarks 53→55, schemas 17→20. Sentinel is additive assurance only: the 14
findings in the July 22 external audit of v4.2.0 were closed by v4.2.1, NOT by Sentinel.

## 4.2.1 — 2026-07-22

Security and assurance-integrity patch: remediation of all 13 code-level findings from
the July 22 external audit of v4.2.0 (LPOS-01 through LPOS-12, LPOS-14), each closed
with an adversarial regression test mirroring the audit's reproduction; LPOS-13
(organizational controls) is scaffolded in docs/SOC2-PROGRAM.md. Highlights: the
compliance module becomes a truthful control readiness monitor (never self-labels
"compliant"/"effective"); monitor shell execution removed and executable checks moved to
admin-approved templates with origin-bound credentials and SSRF egress controls;
approvals require channel-verified identity assertions; dashboard gains token auth,
Host/Origin validation and containment; state files 0600/0700; event store and
evidence ledger hash-chained with verification; subprocess hosts get streaming caps,
allowlist env and resource limits; Ed25519 release signing + CycloneDX SBOM; an
always-on structural schema gate; docs drift fixed. Full test suite: 326 tests.

## 4.2.0 — 2026-07-22

Feature release: the SOC 2 Compliance Guild — compliance codified into the operating
system, run autonomously, with staged remediation and a Type 2 evidence trail.

- **GUILD-038 SOC 2 Compliance Guild**: charter in the packaged spec; owns the codified
  control framework and the autonomous compliance loop.
- **`lpos_engine.compliance`**: the AICPA 2017 Trust Services Criteria (revised 2022
  points of focus) codified as data, with 21 machine-checkable controls mapped across
  CC1–CC9 plus Availability, Confidentiality, and Processing Integrity. Every control
  result carries evidence citing the exact files and values inspected. Type 2 operating
  effectiveness is computed per control over a 90-day observation window from the
  append-only evidence history (`compliance/history.jsonl`) — a control is "effective"
  only when it passes consistently across the window, not once.
- **SO-025 SOC 2 Compliance Audit** (daily, packaged handlers): inventory → audit →
  staged remediation → report. Fixes for failing controls are built as copies in the
  staging test environment (`compliance/staging/<run>/`) with a remediation note and
  validation result; the stager refuses live and in-repo paths by construction, and
  adoption into the main system is a record-only exact-action plan requiring Principal
  approval.
- **The compliance page** (`compliance/report.html`): self-contained HTML — status hero
  with window coverage, The Problems, The Fixes, the Audit Log of changes, and the full
  control matrix with effectiveness meters. `compliance/status.json` is the stable
  contract for the dashboard.
- **CLI**: `lpos compliance audit | report | status`.
- Catalog and counts move to 25 Standing Operations; version synchronized to 4.2.0.
- Boundary stated everywhere it matters: this demonstrates and enforces controls over
  the LPOS system itself and builds the evidence trail; an actual SOC 2 Type 2 report is
  an attestation issued by an independent CPA firm after an observation period.

## 4.1.0 — 2026-07-22

Feature release: the operating system gains self-improvement, its user-facing surfaces,
and a documentation pipeline that keeps itself current.

- **Skill Evolution** (`lpos_engine.evolution`, skill `skill-evolution`): validation-gated,
  staging-only skill improvement derived from Microsoft SkillOpt (MIT; see
  `NOTICE-SKILLOPT.md`). Offline by construction — no model calls, no network, no live
  skill writes; proposals are staged for independent review and Principal approval
  (LPOS-030). The gate demonstrably accepts a helpful edit and rejects a
  plausible-but-harmful one, and the loader reads all 53 packaged benchmark fixtures as
  evolution tasks.
- **Hermes Project Dashboard** (`lpos_engine.dashboard`, `lpos dashboard`, port 7373):
  the single pane of glass for agent work — Active / Research / Snoozed / Archive buckets,
  snooze with user-chosen durations, archive with one-action restore, and file
  discoverability as the headline feature (friendly paths, copy path, open folder, global
  project-and-file search). Localhost-only, stdlib-only, state in `~/.hermes/dashboard/`.
- **Connector Health Monitor** (`lpos_engine.monitor`, `lpos monitor audit`, SO-023
  hourly): auto-discovered inventory of everything the system runs on (email, GitHub,
  cloud, MCP connectors, self-built services), real authenticated checks with timeout and
  retry, transition-based email alerting with recovery all-clears and a fallback when the
  email connector is itself down. Publishes `~/.hermes/monitor/status.json`, which the
  dashboard renders as a system-health strip.
- **User Guide wiki** (`docs/wiki`, `tools/build_wiki.py`): a complete user guide written
  from the real system — getting started, everything LPOS includes, day-to-day usage,
  administration, patch notes — built as a static site for chip.listeningpost.ai plus a
  single-file combined guide for GitHub Releases and Google Drive.
- **New Standing Operations**: SO-022 Release Publication (gates: release verification,
  the codified docs gate, wiki rebuild, record-only exact-action publication plan for
  GitHub / Drive / site deploy), SO-023 Connector Health (hourly), SO-024 Documentation
  Drift Audit (weekly). Packaged handlers available via
  `lpos_engine.publication.standard_handlers()`.
- Version synchronized to 4.1.0 across the package, registries, workflow catalog, kernel,
  and release metadata; the benchmark corpus remains the fixed 53 fixtures.

Note: the 4.0.1 external-derivation patch referenced by the skill-evolution build was not
present in this checkout; its substance (external-derivation attribution policy) is
carried by `NOTICE-SKILLOPT.md` shipping at the repo root and in the distribution.

## 4.0.0

Baseline integrated distribution: deterministic control-plane engine, 32 specialists,
21 Standing Operations, 53 benchmark fixtures, 17 executable schemas, SQLite state,
append-only audit events, record-only external actions.
