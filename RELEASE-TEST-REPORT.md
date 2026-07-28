# LPOS v4.5.0 Release Test Report

Date: 2026-07-28
Python: 3.11

## Results

- Full suite on the committed COE candidate: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest -p no:cacheprovider -q`, **425 passed, 1 optional skip, 0 failures**.
- Test inventory: **426 collected tests**, including fail-closed gate evidence, append-only database triggers, complete release-manifest tampering cases, authentication, dashboard binding, scheduler idempotency, restore verification, and prior LPOS behavior.
- Nine command gates emit schema-valid records and a deterministic hash chain.
- Release-controller tests block missing, stale, failed, malformed, mismatched, and incomplete evidence.
- Immutable release tests cover changed assets, missing and extra files, mutable paths, traversal, duplicates, case hazards, symlinks, mode drift, corrupt JSON, identity drift, commit drift, and source-tree misuse.
- COE API and dashboard tests prove unauthorized denial, authenticated rendering, all 18 labels, explicit unknown handling, blocked release rendering, and `/ops/coe` redirect behavior.
- Backup tests create a real SQLite backup, restore it into an isolated directory, compare hashes, and run `PRAGMA integrity_check`.
- Existing Code Testing Guild, Sentinel, compliance, security, publication, dashboard, monitor, evolution, schema, workflow, and engine tests remain in the suite.
- Release integrity: `python3.11 verify_release.py` passes over the resealed committed tree.

## Notes

- One optional evolution test is skipped when `LPOS_EVALS_DIR` is not set to a fixtures directory.
- The release preserves 45 specialists, 29 Standing Operations, 70 benchmarks, and 22 schemas.
- External actions remain record-only by default.
- Production release readiness remains blocked unless all nine current command records, documentation pass-off, exact artifact identity, and deployment provenance validate.