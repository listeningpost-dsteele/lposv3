# LPOS v4 State and Audit Contract

The LPOS v4 runtime uses a transactional SQLite database as authoritative state. The
default location is `state/lpos.db`. JSONL is produced only as a portable audit export.
Secrets, provider credentials, authentication tokens, and private model reasoning never
enter the database or export.

## Authoritative records

- `tasks` — TaskEnvelope plus current state and optimistic version.
- `interpretations` — canonical InterpretationContract and content hash.
- `artifact_specs` — versioned ArtifactSpecification and content hash.
- `artifacts` — immutable artifact versions keyed by artifact ID and SHA-256.
- `context_bundles` — exact creation/review contexts and their hashes.
- `reviews` — ReviewEnvelope, result, reviewer identity, and isolation attestation.
- `actions` — exact ActionPlan, action hash, status, result, and idempotency key.
- `approval_requests` / `approval_grants` — exact-action binding, verified message
  identity, expiry, replay protection, and single consumption.
- `evidence` / `decisions` — validated EvidenceRecord and DecisionRecord objects.
- `operation_runs` / `operation_claims` — idempotent Standing Operation outcomes and
  worker leases.
- `completion_reports` — one canonical report committed atomically with completion
  evidence.
- `events` — append-only event stream; updates and deletes are rejected by database
  triggers.

## Transaction rules

1. Every state transition is checked against the deterministic state machine.
2. Concurrent updates require the expected object version.
3. Consequential actions are planned, hashed, approved, claimed, and applied exactly
   once per idempotency key.
4. An approval is valid only for the exact action hash and verified Principal identity.
5. Review records bind the artifact hash, contract hash, specification hash, review
   envelope hash, and fresh review context ID.
6. Standing Operation claims may be reclaimed only after lease expiry; a stale worker
   cannot finalize a reclaimed run.
7. Completion and its evidence record commit in the same transaction.
8. Database migrations are checksummed; drift in an applied migration stops startup.

## Portable export

Run:

```bash
lpos export --db state/lpos.db --output state/events.jsonl
```

Each line is one immutable event in sequence order. The export is suitable for review,
backup, and evidence bundles, but importing or replaying it requires a separately
validated recovery procedure.

## Principal and channel configuration

Principal identity, verified channel identities, model-host adapters, and live action
adapters are deployment configuration. Store credentials in the platform secret manager
or operating-system credential store; store only non-secret identifiers and policy
choices in deployment configuration. SO-021 remains disabled until outbound delivery,
inbound collection, Principal round-trip correlation, and verified identity mapping all
pass.
