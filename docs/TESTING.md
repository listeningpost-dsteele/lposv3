# LPOS v4 Testing

Run the complete source suite with:

```bash
python -m pytest
lpos validate-schemas
lpos doctor
lpos evals
python -m compileall -q src
```

The suite covers envelope validation, task and action state transitions, materiality,
routing, adapter capability and locality checks, context compilation, contract/spec/artifact
binding, review isolation, exact-action approval, identity verification, expiry, replay,
concurrent execution claims, file sandboxing, append-only events, migration drift,
optimistic concurrency, atomic completion, Standing Operation idempotency and leases, JSONL
export, CLI behavior, subprocess boundaries, fixed benchmark coverage, deterministic core evaluations, and package asset synchronization.

Release validation additionally builds a wheel, installs it in a clean virtual environment,
runs `lpos doctor`, initializes a fresh database, executes the no-side-effect v4 demo, runs
`pip check`, verifies the release manifest, extracts the final ZIP, and repeats the install
and smoke tests from the extracted archive.

Before enabling a live model, channel, or action adapter, add deployment-specific tests for
credentials, permission scope, sandbox execution, provider failure, rate limits, network
partitions, duplicate requests, timeout after partial success, reconciliation, retention,
redaction, backup, and recovery.
