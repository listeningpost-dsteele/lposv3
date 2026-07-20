# LPOS v4.0.0 Release Test Report

## Release identity

- Product: LPOS
- Version: 4.0.0
- Distribution: integrated, complete source-and-offline-install bundle
- Python requirement: 3.11 or later
- Default consequential-action mode: record-only

## Integrated contents verified

- Packaged LPOS v4 operating specification and always-loaded Chip kernel
- Deterministic control plane and state machines
- Transactional SQLite state and append-only audit events
- 32 canonical capability-routable specialists
- 21 machine-readable Standing Operation workflows
- 53 fixed benchmark fixtures: one per specialist and one per Standing Operation
- 17 synchronized executable JSON Schemas
- Model-host and action-adapter boundaries
- Offline wheel and cross-platform installer

## Source acceptance

Command:

```bash
PYTHONPATH=src python -m pytest -q --disable-warnings -o addopts=''
```

Result:

```text
128 passed, 310 subtests passed
```

The suite covers validation, routing, materiality, task and action transitions, exact-action
approval, verified identities, expiry and replay, context isolation, artifact/contract/spec
binding, fallback, concurrency, append-only events, migrations, atomic completion, operation
leases and idempotency, file sandboxing, subprocess boundaries, packaging synchronization,
all 53 benchmark fixtures, and the integrated CLI.

## Schema and benchmark acceptance

```text
Python compilation: PASS
JSON Schemas: 17 valid
Deterministic core evaluations: 53/53 PASS
```

All benchmark cases contain fixed inputs, expected behavior, success criteria, failure
criteria, an evaluation method, and required evidence.

## Clean-wheel acceptance

The bundled `lpos_os-4.0.0-py3-none-any.whl` was installed with `--no-index` in a newly
created virtual environment. The following checks passed:

- `pip check`
- `lpos version`
- `lpos validate-schemas`
- `lpos doctor --db <fresh database>`
- `lpos evals`
- `lpos demo --workspace <fresh workspace>`

The clean install reported LPOS 4.0.0, database integrity `ok`, 32 specialists, 21 Standing
Operations, 53 benchmarks, and a completed independently reviewed material task.

## Safety boundary

The verification flow binds an approval to an exact action hash and consumes it through the
action state machine, but the bundled consequential-action adapter is intentionally
record-only. It does not send email, publish, deploy, purchase, or delete. Live adapters must
be authenticated, least-privileged, idempotent, and tested for their deployment environment
before registration.
