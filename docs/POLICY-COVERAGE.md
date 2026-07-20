# LPOS v4 Policy Coverage

| Policy | Enforcement point | Executable evidence |
|---|---|---|
| One Principal retains consequential authority | ApprovalService, IdentityVerifier, ActionService | spoofing, mismatch, expiry, replay, and consumption tests |
| Material work has an interpretation contract | PolicyEngine and task state machine | missing-contract and mutation tests |
| Material artifacts have specifications | LPOSRuntime creation guard | missing-spec and spec-binding tests |
| Creator cannot approve its own work | ReviewService and ContextCompiler | context exclusion and attestation tests |
| Five-gate review precedes completion | ReviewResult plus PolicyEngine | rejection, correction, and completion tests |
| External action needs exact approval | canonical ActionPlan hash and approval tables | altered payload, duplicate, concurrent claim, and replay tests |
| Silence is not consent | no timeout-to-grant transition exists | absent-grant tests |
| Missing capability is explicit | CapabilityRouter and AdapterRegistry | missing-route and partial-adapter tests |
| Fallback remains visible | decision and evidence records | fallback-context reuse and decision tests |
| State is transactional and traceable | SQLiteStore and append-only events | concurrency, migration, append-only, and atomic completion tests |
| Standing Operations run once per schedule key | runner plus operation claims | idempotency, lease, stale-worker, and error tests |
| Artifacts preserve exact governing context | artifact contract/spec/context hashes | post-creation mutation and binding tests |
| Schemas are executable contracts | packaged JSON Schemas and dataclass validation | schema validation and round-trip tests |
| Specification is part of the installed OS | packaged SpecRepository default | integrated-asset and doctor tests |

A policy not represented in this table must be classified as advisory or receive an
enforcement point and test before it is described as guaranteed behavior.
