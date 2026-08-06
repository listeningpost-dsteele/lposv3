# LPOS v4.7.0 Release Test Report

Date: 2026-08-05
Python: 3.11

## Results

- Full suite on the committed, sealed candidate: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src LPOS_EVALS_DIR=src/lpos_engine/evals pytest -p no:cacheprovider -q`, **426 passed, 0 failures**.
- Test inventory: **426 tests**, including fail-closed gate evidence, append-only database triggers, complete release-manifest tampering cases, authentication, dashboard binding, scheduler idempotency, restore verification, and prior LPOS behavior.
- Nine command gates emit schema-valid records and a deterministic hash chain.
- Release-controller tests block missing, stale, failed, malformed, mismatched, and incomplete evidence.
- Immutable release tests cover changed assets, missing and extra files, mutable paths, traversal, duplicates, case hazards, symlinks, mode drift, corrupt JSON, identity drift, commit drift, and source-tree misuse.
- COE API and dashboard tests prove unauthorized denial, authenticated rendering, all 18 labels, explicit unknown handling, blocked release rendering, and `/ops/coe` redirect behavior.
- Backup tests create a real SQLite backup, restore it into an isolated directory, compare hashes, and run `PRAGMA integrity_check`.
- Existing Code Testing Guild, Sentinel, compliance, security, publication, dashboard, monitor, evolution, schema, workflow, and engine tests remain in the suite.
- Release integrity: `python verify_release.py` passes over 398 immutable files in both the resealed committed tree and a separate clean `git archive` export.
- Doctor reports LPOS 4.7.0 healthy with release integrity passed, 103 specialists, 29 Standing Operations, 70 benchmarks, and 22 schemas.

## Notes

- Product Studio is absent from this release and remains deferred.
- The release includes 103 specialists, 29 Standing Operations, 70 benchmarks, and 22 schemas.
- The expert capability corpus (20 guild charters, 103 specialist charters, 122 craft standards, 103 admission suites) is frozen.
- External actions remain record-only by default.
- External publication was explicitly authorized by the Principal on 2026-08-05; the packaged runtime remains record-only by default.