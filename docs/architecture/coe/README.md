# Continuous Operational Excellence

Release: LPOS 4.5.0

Continuous Operational Excellence, or COE, is a permanent constitutional subsystem. It converts release, security, reliability, efficiency, and operational-health claims into command-backed evidence.

## Trust boundaries

The system separates four responsibilities:

1. A gate command performs checks and decides its own result.
2. The gate runner records process facts, validates the evidence contract, and rejects process or evidence disagreement.
3. The release controller aggregates one current evidence chain. It does not run checks or fill gaps.
4. Private APIs and the dashboard render persisted decisions. A request cannot generate or mutate release evidence.

Missing, stale, malformed, skipped, mismatched, or failed evidence blocks release. Unknown information is shown as unknown.

## Components

- `coe_contract.py`: canonical JSON, release identity, evidence hashing, schema validation, and redaction.
- `coe_manifest.py`: clean staging, complete file enumeration, artifact identity, and fail-closed verification.
- `coe_store.py`: v4 SQLite persistence, append-only evidence and decisions, findings, metrics, debt, opportunities, backups, scheduler records, and report deliveries.
- `coe_gate.py`: nine independently executable gate commands.
- `coe_runtime.py`: gate runner, collectors, restore test, daily locking, orchestrator, release controller, scores, reports, and delivery evidence.
- `coe.py`: authenticated private API and dashboard views over persisted state.

Mutable COE state defaults to `${HERMES_STATE_DIR:-$HOME/.hermes/state}/chip-service/coe`. It is never written into a staged release.
