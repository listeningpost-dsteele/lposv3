# LPOS Changelog

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
