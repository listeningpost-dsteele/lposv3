# LPOS v4 Architecture

## One integrated system

```text
Principal instruction
        │
        ▼
Deterministic LPOS control plane
  ├─ materiality and state machines
  ├─ capability and adapter routing
  ├─ context compiler
  ├─ approval and identity guards
  ├─ review isolation
  ├─ transactional store and audit events
  └─ Standing Operation runner
        │
        ├───────────────┐
        ▼               ▼
Model adapters      Action/channel adapters
(probabilistic)     (permissioned side effects)
```

The operating specification is package data consumed by the same installed runtime. There
is no separate constitutional release to install or point at.

## Control plane and intelligence plane

The control plane owns permissions, state transitions, materiality, exact-action hashes,
approval validity, verified identities, idempotency, context boundaries, persistence,
operation claims, audit events, and execution. These decisions are deterministic.

Model adapters own interpretation, decomposition, research, analysis, drafting, artifact
creation, and review judgment. A model can propose an action but cannot move an action
through a forbidden state or execute it without the control plane.

## Runtime entities

The main immutable or versioned entities are:

- TaskEnvelope
- InterpretationContract
- ArtifactSpecification
- ContextBundle
- Artifact
- ReviewEnvelope and ReviewResult
- ActionPlan and ActionResult
- ApprovalRequest and ApprovalGrant
- MessageIdentity
- EvidenceRecord and DecisionRecord
- WorkflowDefinition and StandingOperationRun
- CompletionReport

Each entity has a Python validation class and a synchronized JSON Schema.

## Task lifecycle

```text
received → interpreted → planned → executing → reviewing → completed
     │           │           │          │          │
     ├─ awaiting_clarification           └─ correction_required
     └──────────────── awaiting_approval

terminal: completed | failed | cancelled | suspended
```

Only enumerated transitions are accepted. Material work cannot execute without an
InterpretationContract and ArtifactSpecification, and cannot complete without an isolated
PASS review of the exact artifact hash.

## Capability-first routing

A TaskEnvelope names required capabilities. The router selects the smallest specialist set
that covers those capabilities, using the 32 canonical `SPECIALIST-###` profiles. Guilds
remain the accountability view; capabilities determine execution. The route also selects
craft standards and a model class. Missing capabilities are explicit and block execution.

A configured model adapter must cover the complete required capability set and satisfy any
locality constraint. A provider or vendor name never appears in the constitutional route.

## Context compilation

The context compiler always loads the Chip kernel, then retrieves only the selected
specialist and craft-standard sections. The packaged specification is the default source.
Every ContextBundle records loaded components, missing components, exclusions, token
estimate, and SHA-256 bundle hash.

Review uses a fresh ReviewEnvelope context. It excludes the creation conversation, creator
private reasoning, and creator self-assessment. The persisted review record binds the
review context ID, envelope hash, artifact hash, creator adapter, reviewer adapter, and
isolation result.

## Exact-action authority

A consequential action is planned before it is applied. The canonical action payload is
hashed. An approval grant must refer to the same question, task, action ID, action hash, and
verified Principal identity. Grants expire, cannot be replayed, and are consumed atomically
with the execution claim. The adapter receives only a plan that has passed these checks.

## State and events

SQLite is the authoritative single-machine store. WAL mode, foreign keys, explicit
transactions, optimistic versions, operation leases, unique idempotency keys, and
checksummed migrations protect consistency. The `events` table is append-only through
triggers. JSONL is an ordered audit export rather than live concurrent state.

## Standing Operations

The package includes 21 WorkflowDefinition documents. Each is a deterministic DAG of named
handlers with dependencies and error behavior. The runner claims the scheduled idempotency
key, executes each ready step once, freezes JSON-compatible outputs, records an explicit
`ok`, `silent`, or `error` result, and commits one EvidenceRecord. Schedulers and concrete
handlers remain adapters.

## Executable evaluation corpus

LPOS packages 53 fixed fixtures: one for every specialist and one for every Standing
Operation. Each fixture records explicit inputs, expected behavior, success and failure
criteria, an evaluation method, and required evidence. `lpos evals` runs deterministic
routing and workflow assertions against the complete corpus. Model-host deployments reuse
the same immutable fixtures for provider/model quality scoring.

## Deployment boundary

The bundled local adapters are safe verification components, not hidden production
connectors. Real deployments supply model hosts, channel collectors, schedulers, secret
management, and consequential action adapters. Their permissions and failure semantics are
outside the core until registered and tested through the same adapter contracts.
