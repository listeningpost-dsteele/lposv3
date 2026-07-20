# LPOS v4 Security Model

LPOS v4 moves authority-sensitive rules into deterministic code and transactional state.
The core is suitable for a trusted single-machine installation and for acceptance testing.
A multi-tenant or distributed deployment requires additional authentication, isolation,
secret management, database, and infrastructure controls.

## Enforced controls

- Consequential actions require an exact ActionPlan and, when required, a verified grant
  bound to the unchanged SHA-256 action hash.
- Silence is never approval.
- MessageIdentity is provider-neutral and replay-protected.
- Approvals are single-use and consumed atomically with an execution claim.
- Material work requires an InterpretationContract, ArtifactSpecification, immutable
  artifact binding, and context-isolated PASS review.
- Task and action transitions follow explicit state machines.
- Operation runs use idempotency keys and leases; stale workers cannot finalize reclaimed
  runs.
- Database migrations are checksummed and append-only events reject update or deletion.
- Local file writes are confined to a configured root, reject traversal, and use atomic
  replacement.
- The subprocess model adapter does not invoke a shell and enforces timeout and output
  limits.

## Secrets and sensitive content

The core does not persist credentials. Store provider tokens, email credentials, signing
keys, and service secrets in an operating-system credential store or deployment secret
manager. Context bundles, artifacts, action parameters, evidence, and audit events may
contain sensitive data; deploy on appropriately protected storage and define retention,
backup, redaction, and access policies.

The core does not provide encryption at rest. Use encrypted disks or replace the storage
adapter where that is insufficient.

## Live action adapters

A live adapter must be least-privileged, authenticated, idempotent where possible, and able
to distinguish success, failure, and uncertain outcome. Before registration, test it in a
sandbox for duplicate requests, timeouts after partial execution, retries, credential
failure, rate limits, and reconciliation. Do not register a broad generic shell executor as
a consequential action adapter.

## Model hosts

Treat model-host output as untrusted structured input. Validate every returned envelope.
Do not give a model host direct write access to the LPOS database or unrestricted access to
credentials. A model may propose tool parameters; the control plane and action adapter
validate and execute them.

## Reporting a vulnerability

Use the security-reporting process of the repository or organization distributing this
release. Do not place sensitive exploit details in a public issue.
