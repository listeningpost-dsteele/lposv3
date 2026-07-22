# LPOS v4 Executable Schemas

The canonical machine contracts are the JSON Schema documents packaged under
`lpos_engine/schemas/`. The Python envelope classes and the human descriptions below
must remain synchronized with those files. `lpos validate-schemas` validates the
packaged set.

## Core envelopes

- `task-envelope.schema.json` — task identity, routing, materiality, constraints, and
  selected creator adapter.
- `interpretation-contract.schema.json` — verbatim instruction, interpretation,
  invariants, conflicts, verification plan, and specification reference.
- `artifact-specification.schema.json` — structural decisions, design tokens,
  invariants, approval, and history.
- `artifact.schema.json` — immutable artifact content, hashes, baseline, contract/spec
  bindings, context binding, and creator adapter.
- `context-bundle.schema.json` — exact compiled context, included/missing components,
  exclusions, and bundle hash.

## Review and authority envelopes

- `review-envelope.schema.json` — the only permitted review input: brief, baseline,
  artifact, contract, specification, standards, verification evidence, and intended
  outcome. Creation conversation, creator private reasoning, and creator self-assessment
  are always excluded.
- `review-result.schema.json` — PASS/REJECT decision, isolation attestation, recomputed
  checks, violations, regressions, corrections, and evidence reviewed.
- `action-plan.schema.json` — exact action parameters, externality, reversibility,
  idempotency key, and canonical action hash.
- `approval-request.schema.json` / `approval-grant.schema.json` — question and grant
  bound to the exact action and verified MessageIdentity.
- `message-identity.schema.json` — provider-neutral channel, provider, message, thread,
  and sender identity.

## Evidence and operations envelopes

- `evidence-record.schema.json` — expected outcome, baseline, target, observation,
  confidence, measurement, fallback use, and status.
- `decision-record.schema.json` — context, decision, rationale, alternatives, impact,
  risks, implementation notes, references, status, and owner.
- `workflow-definition.schema.json` — executable Standing Operation DAG.
- `benchmark-definition.schema.json` — fixed component fixture, explicit inputs, expected behavior, evaluation assertions, and evidence.
- `standing-operation-run.schema.json` — idempotent run identity, timing, result, output
  reference, evidence, fallback, and model class.
- `completion-report.schema.json` — final result, artifact/review binding, actions,
  evidence, decisions, limitations, and completion time.

Schemas are closed (`additionalProperties: false`) where the contract requires exact
shape. A runtime must reject malformed envelopes before persistence or adapter use.
