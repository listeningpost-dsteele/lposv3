# LPOS COE Bloat Repair Closeout Addendum

Status: Approved and implemented as the LPOS 4.5.0 COE trust contract

## Mission

COE prevents assurance bloat and drift. Release claims must be provable. Every recurring
defect class becomes a command-backed check, schema, test, lifecycle record, or measured
audit domain.

## Constitutional Principle XI: Operational Sustainability

Every persistent artifact has an owner, purpose, lifecycle class, retention policy,
verification method, and retirement plan. Mutable state does not enter immutable releases.
Recurring work invokes a model only after a deterministic wake decision.

## Release assurance

`release/release.json` is the authoritative identity. A complete staged artifact is generated
outside the source tree and every regular file is enumerated in `release-manifest.json`.
The verifier rejects missing, unlisted, changed, mutable, unsafe, case-colliding, and
symlinked content, plus identity and provenance drift.

Nine independent commands produce schema-valid, hash-chained gate evidence:

1. Deterministic tests.
2. Application release verifier.
3. Doctor.
4. Engineering audit.
5. Security and reliability audit.
6. Documentation audit.
7. Bloat and efficiency audit.
8. Opportunity and value audit.
9. Release integrity and provenance.

The release controller reads the persisted chain. It cannot run checks, create defaults, or
turn unknown information green.

## Daily operation

Daily COE runs at 03:00 America/Chicago. The Central calendar date supplies deterministic
idempotency. A SQLite lease prevents overlap. Audit scope includes changed code, process and
skill efficiency, scheduler and wake behavior, prompt drift, real backup restore evidence,
storage trends, artifact lifecycle, technical debt, opportunities, documentation, and COE's
own cost and duplicate work.

State defaults to `${HERMES_STATE_DIR:-$HOME/.hermes/state}/chip-service`. The legacy
`/Users/dan/lpos-state` boundary remains read-only and is tracked as
`TD-LEGACY-LPOS-STATE`.

## Private operations surface

The canonical dashboard is `https://chip.listeningpost.ai/dashboard/coe`. `/ops/coe`
redirects to it. Dashboard and API responses require operator authentication, use private
no-store caching, and render persisted evidence only. All 18 named health and release fields
show blocked, failed, stale, or unknown explicitly.

Daily reports include the audit ID, release identity, dashboard link, all gate states, risks,
engineering findings, skill efficiency, scheduler and wake metrics, restore status, storage,
technical debt, opportunities, and pending decisions. Delivery is recorded only after a
provider message ID or equivalent transport acceptance is returned.

## Documentation map

- Architecture and operations: `docs/architecture/coe/`.
- API contract: `openapi-coe.yaml`.
- Release and evidence schemas: `schemas/release-manifest.schema.json` and
  `schemas/coe-gate-evidence.schema.json`.
- Pass-off: `docs/passoff/LPOS-v4.5.0-COE.md`.
- Acceptance evidence: `acceptance/ACCEPTANCE_CHECKLIST.md` and
  `docs/implementation-evidence/`.