# LPOS v4.2.0 Release Test Report

Date: 2026-07-22
Python: 3.11

## Results

- Full suite: `PYTHONPATH=src python3 -m pytest tests/` — **196 passed, 338 subtests passed** (0 failures)
  - 128 baseline engine/distribution tests (updated for the 24-operation catalog and v4.1.0)
  - 15 dashboard tests (`tests/test_dashboard.py`): scanner, state, snooze/wake, archive/restore, corrupt-state degradation, search, open-folder path containment, live HTTP round trip
  - 21 monitor tests (`tests/test_monitor.py`, fully offline): discovery/merge, transition alerting exactly-once, retry-before-offline, timeout handling, undelivered-alert fallback, status.json contract
  - 8 wiki tests (`tests/test_wiki.py`): clean build, page/nav/search completeness, generated reference pages, combined guide, no broken internal links, version badge
  - 2 evolution tests (`tests/test_evolution.py`): CS-001 domain — helpful edit accepted and harmful edit rejected by the held-out gate; LPOS loader reads all 53 benchmark fixtures
  - 14 compliance tests (`tests/test_compliance.py`, fully offline): full audit + status contract, staged remediation with repo-untouched proof, staging refusals of live/in-repo paths, Type 2 effectiveness boundary math, report HTML sections and escaping, SO-025 end-to-end through the runner
  - 8 publication tests (`tests/test_publication.py`): SO-022 release + docs gates, record-only publication plan, SO-024 enumeration/diff/report, standard handler registry
- Deterministic core evaluations: 53/53 benchmarks pass (`lpos evals`)
- Release integrity: `python3 verify_release.py` passes over the resealed tree
- End-to-end: SO-023 and SO-024 executed through `StandingOperationRunner` with packaged
  handlers — both OK, `monitor/status.json` and `docs/drift-report.json` written

## Notes

- The benchmark corpus remains the fixed 53 fixtures; SO-022/023/024 are catalog and
  workflow additions with packaged handlers, evaluated per LPOS-016 on first production run.
- The 4.0.1 external-derivation patch was not present in this checkout; `NOTICE-SKILLOPT.md`
  ships the attribution record at the repo root and in the distribution.
