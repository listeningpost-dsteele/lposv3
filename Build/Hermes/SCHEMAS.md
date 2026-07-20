# LPOS Runtime Envelopes (machine-readable contracts)

These schemas remove ambiguity spread across prose. Runtimes exchange these
envelopes; documents explain them. Field values are YAML/JSON; timestamps are
ISO 8601; ids are strings.

## TaskEnvelope
    task_id, principal_instruction, lead_guild, lead_specialist,
    supporting_specialists: [], craft_standards: [], material: true|false,
    materiality_basis, model_class, deadline, created_at

## InterpretationContract (LPOS-029)
    task_id, instruction_verbatim, interpretation, invariants: [],
    conflicts: [{levels, description, resolution: asked|precedence, question_id}],
    verification_plan, spec_ref, created_at

## ArtifactSpecification
    artifact_id, structural_decisions: {}, design_tokens: {}, invariants: [],
    approved_by, updated_at, history: [snapshot refs]

## ReviewEnvelope (the ONLY review input; nothing else may be provided)
    brief, baseline, artifact, interpretation_contract,
    artifact_specification, mapped_craft_standards: [], verification_evidence,
    intended_outcome
    excluded_always: [creation_conversation, creator_private_reasoning,
                      creator_self_assessment]

## ReviewResult
    decision: PASS|REJECT, isolation: <method>, recomputed: <what|none>,
    contract_violations: [], truth: [], reasoning: [], craft: [], outcome: [],
    regressions: [], required_corrections: [], strengths_to_preserve: [],
    evidence_reviewed: []

## ApprovalRequest
    question_id, kind: consent|clarification|approval, exact_action,
    options: [], recommended, expires_policy: hold, created_at

## ApprovalGrant
    question_id, granted_action,          # binds to the exact_action text; nothing else
    channel, message_identity, verified_identity, granted_at

## MessageIdentity (provider neutral)
    channel: email|telegram|desktop|slack, provider, message_id, thread_id

## EvidenceRecord (LPOS-007)
    id, recommendation, owner, expected_outcome, baseline, target, observed,
    confidence, measurement, fallback_used, review_date,
    status: Proposed|Active|Measured|Validated|Refuted|Inconclusive

## DecisionRecord (LPOS-015)
    id, date, context, decision, rationale, alternatives: [], consequences,
    risks, implementation_notes, references: [], status: Accepted|Superseded,
    superseded_by, owner

## StandingOperationRun
    so_id, run_id, started_at, finished_at, result: ok|silent|error,
    outputs_ref, evidence_id, fallback_used, model_class
