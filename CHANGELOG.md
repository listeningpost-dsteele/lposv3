# LPOS Changelog

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
