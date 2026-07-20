# LPOS Standing Operations

Per LPOS-016, each Standing Operation's first production run is evaluated against
BENCH-001 (routing) plus its lead specialist's BENCH-S### benchmark until a dedicated
SO benchmark exists; record the result in the evidence ledger.

Every Standing Operation run appends exactly one evidence record to the evidence
ledger. Runs with nothing worth sending return exactly [SILENT] and still record
evidence.


---

## Source: `standing-operations/SO-001-executive-brief.md`

---
id: SO-001
title: Executive Brief
version: 1.0.0
status: Accepted
owner: Listening Post
machine:
  owner: Chip
  specialists: [executive-writer, strategic-planner]
  type: standing_operation
  slug: executive-brief
  trigger: scheduled
  communication_intent: Executive Decision
---

# Executive Brief

## Mission

Prepare one concise decision-focused briefing for the Principal.


## Objective

One decision-ready brief each scheduled morning.

## Required capabilities

- scheduled or event-driven execution
- read access to the listed inputs
- evidence recording
## Inputs

- Principal Model
- active initiatives
- calendar
- email
- evidence
- operation health

## Outputs

- Executive summary
- decisions required
- evidence
- risks
- opportunities
- priorities

## Required behavior

- Reuse known context.
- Complete available work before escalating.
- Distinguish facts, inference, and speculation.
- Include evidence, tradeoffs, risk, and confidence when recommending action.
- Produce one clear next action for the Principal when a decision is needed.
- Record measurable outcomes in the Evidence Ledger.

## Success criteria

The operation creates useful output with low interruption and measurable value.

## Failure conditions

Missing data, unsupported conclusions, unclear next action, repeated noise, or no
measurable value.


---

## Source: `standing-operations/SO-002-opportunity-intelligence.md`

---
id: SO-002
title: Opportunity Intelligence
version: 1.0.0
status: Accepted
owner: Listening Post
machine:
  owner: Chip
  specialists: [technology-scout, market-research-analyst, decision-analyst]
  type: standing_operation
  slug: opportunity-intelligence
  trigger: scheduled
  communication_intent: Executive Decision
---

# Opportunity Intelligence

## Mission

Discover, validate, challenge, and prioritize high-value opportunities.


## Objective

A ranked, evidence-based opportunity queue.

## Required capabilities

- scheduled or event-driven execution
- read access to the listed inputs
- evidence recording
## Inputs

- technology signals
- research sources
- customer evidence
- internal ideas
- benchmarks

## Outputs

- ranked opportunities
- rejections
- implementation plans
- evidence estimates

## Required behavior

- Reuse known context.
- Complete available work before escalating.
- Distinguish facts, inference, and speculation.
- Include evidence, tradeoffs, risk, and confidence when recommending action.
- Produce one clear next action for the Principal when a decision is needed.
- Record measurable outcomes in the Evidence Ledger.

## Success criteria

The operation creates useful output with low interruption and measurable value.

## Failure conditions

Missing data, unsupported conclusions, unclear next action, repeated noise, or no
measurable value.


---

## Source: `standing-operations/SO-003-calendar-review.md`

---
id: SO-003
title: Calendar Review
version: 1.0.0
status: Accepted
owner: Listening Post
machine:
  owner: Chip
  specialists: [operations-manager, relationship-analyst]
  type: standing_operation
  slug: calendar-review
  trigger: scheduled
  communication_intent: Status
---

# Calendar Review

## Mission

Prepare the Principal for upcoming commitments and identify conflicts.


## Objective

Conflicts and preparation needs surfaced before commitments.

## Required capabilities

- scheduled or event-driven execution
- read access to the listed inputs
- evidence recording
- calendar read
## Inputs

- calendar
- Principal Model
- relationship context
- active initiatives

## Outputs

- conflicts
- preparation needs
- meeting briefs
- recommended changes

## Required behavior

- Reuse known context.
- Complete available work before escalating.
- Distinguish facts, inference, and speculation.
- Include evidence, tradeoffs, risk, and confidence when recommending action.
- Produce one clear next action for the Principal when a decision is needed.
- Record measurable outcomes in the Evidence Ledger.

## Success criteria

The operation creates useful output with low interruption and measurable value.

## Failure conditions

Missing data, unsupported conclusions, unclear next action, repeated noise, or no
measurable value.


---

## Source: `standing-operations/SO-004-inbox-review.md`

---
id: SO-004
title: Inbox Review
version: 1.0.0
status: Accepted
owner: Listening Post
machine:
  owner: Chip
  specialists: [executive-writer, relationship-analyst]
  type: standing_operation
  slug: inbox-review
  trigger: scheduled
  communication_intent: Status
---

# Inbox Review

## Mission

Identify messages requiring decisions, replies, delegation, or archival.


## Objective

Every inbox item triaged to decision, reply, delegation, or archive.

## Required capabilities

- scheduled or event-driven execution
- read access to the listed inputs
- evidence recording
- mailbox read
## Inputs

- email
- Principal Model
- active initiatives

## Outputs

- priority messages
- draft replies
- delegations
- follow-ups

## Required behavior

- Reuse known context.
- Complete available work before escalating.
- Distinguish facts, inference, and speculation.
- Include evidence, tradeoffs, risk, and confidence when recommending action.
- Produce one clear next action for the Principal when a decision is needed.
- Record measurable outcomes in the Evidence Ledger.

## Success criteria

The operation creates useful output with low interruption and measurable value.

## Failure conditions

Missing data, unsupported conclusions, unclear next action, repeated noise, or no
measurable value.


---

## Source: `standing-operations/SO-005-meeting-preparation.md`

---
id: SO-005
title: Meeting Preparation
version: 1.0.0
status: Accepted
owner: Listening Post
machine:
  owner: Chip
  specialists: [relationship-analyst]
  type: standing_operation
  slug: meeting-preparation
  trigger: event-driven
  communication_intent: Collaboration
---

# Meeting Preparation

## Mission

Create a concise brief before an important meeting.


## Objective

A usable brief before each important meeting.

## Required capabilities

- scheduled or event-driven execution
- read access to the listed inputs
- evidence recording
- calendar read
- relationship context read
## Inputs

- calendar event
- relationship history
- customer intelligence
- active initiatives

## Outputs

- objective
- participants
- history
- open decisions
- agenda
- recommended questions

## Required behavior

- Reuse known context.
- Complete available work before escalating.
- Distinguish facts, inference, and speculation.
- Include evidence, tradeoffs, risk, and confidence when recommending action.
- Produce one clear next action for the Principal when a decision is needed.
- Record measurable outcomes in the Evidence Ledger.

## Success criteria

The operation creates useful output with low interruption and measurable value.

## Failure conditions

Missing data, unsupported conclusions, unclear next action, repeated noise, or no
measurable value.


---

## Source: `standing-operations/SO-006-weekly-review.md`

---
id: SO-006
title: Weekly Review
version: 1.0.0
status: Accepted
owner: Listening Post
machine:
  owner: Chip
  specialists: [strategic-planner, evidence-analyst]
  type: standing_operation
  slug: weekly-review
  trigger: scheduled
  communication_intent: Executive Decision
---

# Weekly Review

## Mission

Evaluate progress, evidence, decisions, and priorities.


## Objective

A weekly account of progress, evidence, and next priorities.

## Required capabilities

- scheduled or event-driven execution
- read access to the listed inputs
- evidence recording
## Inputs

- decision ledger
- evidence ledger
- initiative status
- operation health

## Outputs

- completed outcomes
- misses
- lessons
- next priorities
- decisions

## Required behavior

- Reuse known context.
- Complete available work before escalating.
- Distinguish facts, inference, and speculation.
- Include evidence, tradeoffs, risk, and confidence when recommending action.
- Produce one clear next action for the Principal when a decision is needed.
- Record measurable outcomes in the Evidence Ledger.

## Success criteria

The operation creates useful output with low interruption and measurable value.

## Failure conditions

Missing data, unsupported conclusions, unclear next action, repeated noise, or no
measurable value.


---

## Source: `standing-operations/SO-007-evidence-review.md`

---
id: SO-007
title: Evidence Review
version: 1.0.0
status: Accepted
owner: Listening Post
machine:
  owner: Chip
  specialists: [evidence-analyst]
  type: standing_operation
  slug: evidence-review
  trigger: scheduled
  communication_intent: Evidence
---

# Evidence Review

## Mission

Evaluate whether implemented work created intended value.


## Objective

Each implemented recommendation judged against its expected outcome.

## Required capabilities

- scheduled or event-driven execution
- read access to the listed inputs
- evidence recording
## Inputs

- evidence ledger
- baselines
- targets
- observations

## Outputs

- validated outcomes
- refuted hypotheses
- inconclusive items
- next measurements

## Required behavior

- Reuse known context.
- Complete available work before escalating.
- Distinguish facts, inference, and speculation.
- Include evidence, tradeoffs, risk, and confidence when recommending action.
- Produce one clear next action for the Principal when a decision is needed.
- Record measurable outcomes in the Evidence Ledger.

## Success criteria

The operation creates useful output with low interruption and measurable value.

## Failure conditions

Missing data, unsupported conclusions, unclear next action, repeated noise, or no
measurable value.


---

## Source: `standing-operations/SO-008-standing-operation-health.md`

---
id: SO-008
title: Standing Operation Health
version: 1.0.0
status: Accepted
owner: Listening Post
machine:
  owner: Chip
  specialists: [operations-manager]
  type: standing_operation
  slug: standing-operation-health
  trigger: scheduled
  communication_intent: Operational Alert
---

# Standing Operation Health

## Mission

Detect failed, noisy, low-value, or redundant recurring operations.


## Objective

Failing, noisy, or redundant operations caught within one day.

## Required capabilities

- scheduled or event-driven execution
- read access to the listed inputs
- evidence recording
## Inputs

- operation history
- errors
- delivery logs
- evidence

## Outputs

- health summary
- failures
- redundancy
- recommended changes

## Required behavior

- Reuse known context.
- Complete available work before escalating.
- Distinguish facts, inference, and speculation.
- Include evidence, tradeoffs, risk, and confidence when recommending action.
- Produce one clear next action for the Principal when a decision is needed.
- Record measurable outcomes in the Evidence Ledger.

## Success criteria

The operation creates useful output with low interruption and measurable value.

## Failure conditions

Missing data, unsupported conclusions, unclear next action, repeated noise, or no
measurable value.


---

## Source: `standing-operations/SO-009-relationship-review.md`

---
id: SO-009
title: Relationship Review
version: 1.0.0
status: Accepted
owner: Listening Post
machine:
  owner: Chip
  specialists: [relationship-analyst]
  type: standing_operation
  slug: relationship-review
  trigger: scheduled
  communication_intent: Status
---

# Relationship Review

## Mission

Identify important relationship follow-ups and meeting opportunities.


## Objective

Timely follow-ups on the relationships that matter.

## Required capabilities

- scheduled or event-driven execution
- read access to the listed inputs
- evidence recording
## Inputs

- relationship context
- calendar
- email history
- customer intelligence

## Outputs

- priority contacts
- relationship risks
- follow-ups
- meeting suggestions

## Required behavior

- Reuse known context.
- Complete available work before escalating.
- Distinguish facts, inference, and speculation.
- Include evidence, tradeoffs, risk, and confidence when recommending action.
- Produce one clear next action for the Principal when a decision is needed.
- Record measurable outcomes in the Evidence Ledger.

## Success criteria

The operation creates useful output with low interruption and measurable value.

## Failure conditions

Missing data, unsupported conclusions, unclear next action, repeated noise, or no
measurable value.


---

## Source: `standing-operations/SO-010-technology-signals.md`

---
id: SO-010
title: Technology Signals
version: 1.0.0
status: Accepted
owner: Listening Post
machine:
  owner: Chip
  specialists: [technology-scout, source-validator]
  type: standing_operation
  slug: technology-signals
  trigger: scheduled
  communication_intent: Executive Decision
---

# Technology Signals

## Mission

Surface weak technical signals rather than obvious news.


## Objective

Weak technical signals surfaced before they become news.

## Required capabilities

- scheduled or event-driven execution
- read access to the listed inputs
- evidence recording
## Inputs

- repositories
- papers
- standards
- communities
- benchmarks
- inference developments

## Outputs

- signals
- why they matter
- why they may not matter
- watch items
- recommended experiments

## Required behavior

- Reuse known context.
- Complete available work before escalating.
- Distinguish facts, inference, and speculation.
- Include evidence, tradeoffs, risk, and confidence when recommending action.
- Produce one clear next action for the Principal when a decision is needed.
- Record measurable outcomes in the Evidence Ledger.

## Success criteria

The operation creates useful output with low interruption and measurable value.

## Failure conditions

Missing data, unsupported conclusions, unclear next action, repeated noise, or no
measurable value.


---

## Source: `standing-operations/SO-011-daily-execution-review.md`

---
id: SO-011
title: Daily Execution Review
version: 1.0.0
status: Accepted
owner: Listening Post
machine:
  owner: Chip
  specialists: [initiative-manager]
  type: standing_operation
  slug: daily-execution-review
  trigger: scheduled
  communication_intent: Status
---

# Daily Execution Review

## Mission

Review active work, blockers, dependencies, and completion risk.


## Objective

Blockers and completion risks visible before end of day.

## Required capabilities

- scheduled or event-driven execution
- read access to the listed inputs
- evidence recording

## Inputs

- active work items
- blockers
- dependency state
- deadlines

## Outputs

- status deltas
- blockers
- completion risks
- next actions
## Required behavior

- Load the constitutional core and the relevant Principal context.
- Use the minimum sufficient specialists.
- Distinguish facts, inference, and speculation.
- Include evidence, tradeoffs, risk, confidence, and one clear next action.
- Record measurable outcomes in the Evidence Ledger.
- Escalate only when missing information or authority blocks progress.

## Success criteria

The operation creates useful, low-noise output and measurable value.

## Failure conditions

Unsupported conclusions, hidden assumptions, unclear action, repeated noise,
unavailable required capabilities, or no measurable value.


---

## Source: `standing-operations/SO-012-pipeline-review.md`

---
id: SO-012
title: Pipeline Review
version: 1.0.0
status: Accepted
owner: Listening Post
machine:
  owner: Chip
  specialists: [financial-analyst, customer-insights-analyst]
  type: standing_operation
  slug: pipeline-review
  trigger: scheduled
  communication_intent: Executive Decision
---

# Pipeline Review

## Mission

Review revenue pipeline health, next actions, and forecast risk.


## Objective

Pipeline health and forecast risk quantified weekly.

## Required capabilities

- scheduled or event-driven execution
- read access to the listed inputs
- evidence recording
- pipeline data read

## Inputs

- pipeline records
- account history
- forecast
- activity

## Outputs

- pipeline health
- at-risk deals
- forecast risk
- next actions
## Required behavior

- Load the constitutional core and the relevant Principal context.
- Use the minimum sufficient specialists.
- Distinguish facts, inference, and speculation.
- Include evidence, tradeoffs, risk, confidence, and one clear next action.
- Record measurable outcomes in the Evidence Ledger.
- Escalate only when missing information or authority blocks progress.

## Success criteria

The operation creates useful, low-noise output and measurable value.

## Failure conditions

Unsupported conclusions, hidden assumptions, unclear action, repeated noise,
unavailable required capabilities, or no measurable value.


---

## Source: `standing-operations/SO-013-customer-review.md`

---
id: SO-013
title: Customer Review
version: 1.0.0
status: Accepted
owner: Listening Post
machine:
  owner: Chip
  specialists: [customer-insights-analyst]
  type: standing_operation
  slug: customer-review
  trigger: scheduled
  communication_intent: Executive Decision
---

# Customer Review

## Mission

Summarize customer health, needs, risks, and expansion opportunities.


## Objective

Customer health, risk, and expansion assessed weekly.

## Required capabilities

- scheduled or event-driven execution
- read access to the listed inputs
- evidence recording
- customer data read

## Inputs

- customer accounts
- usage and feedback
- support history

## Outputs

- health summary
- needs
- risks
- expansion opportunities
## Required behavior

- Load the constitutional core and the relevant Principal context.
- Use the minimum sufficient specialists.
- Distinguish facts, inference, and speculation.
- Include evidence, tradeoffs, risk, confidence, and one clear next action.
- Record measurable outcomes in the Evidence Ledger.
- Escalate only when missing information or authority blocks progress.

## Success criteria

The operation creates useful, low-noise output and measurable value.

## Failure conditions

Unsupported conclusions, hidden assumptions, unclear action, repeated noise,
unavailable required capabilities, or no measurable value.


---

## Source: `standing-operations/SO-014-security-review.md`

---
id: SO-014
title: Security Review
version: 1.0.0
status: Accepted
owner: Listening Post
machine:
  owner: Chip
  specialists: [threat-analyst, security-architect]
  type: standing_operation
  slug: security-review
  trigger: scheduled
  communication_intent: Operational Alert
---

# Security Review

## Mission

Review security-relevant changes, permissions, providers, and incidents.


## Objective

Security-relevant changes reviewed within a week.

## Required capabilities

- scheduled or event-driven execution
- read access to the listed inputs
- evidence recording
- configuration and log read

## Inputs

- permission changes
- provider changes
- incidents
- config diffs

## Outputs

- findings
- severities
- mitigations
- approvals needed
## Required behavior

- Load the constitutional core and the relevant Principal context.
- Use the minimum sufficient specialists.
- Distinguish facts, inference, and speculation.
- Include evidence, tradeoffs, risk, confidence, and one clear next action.
- Record measurable outcomes in the Evidence Ledger.
- Escalate only when missing information or authority blocks progress.

## Success criteria

The operation creates useful, low-noise output and measurable value.

## Failure conditions

Unsupported conclusions, hidden assumptions, unclear action, repeated noise,
unavailable required capabilities, or no measurable value.


---

## Source: `standing-operations/SO-015-provider-review.md`

---
id: SO-015
title: Provider Review
version: 1.0.0
status: Accepted
owner: Listening Post
machine:
  owner: Chip
  specialists: [data-analyst, technology-scout]
  type: standing_operation
  slug: provider-review
  trigger: scheduled
  communication_intent: Status
---

# Provider Review

## Mission

Evaluate provider health, quality, cost, and compatibility.


## Objective

Provider quality, cost, and health scored monthly.

## Required capabilities

- scheduled or event-driven execution
- read access to the listed inputs
- evidence recording
- provider telemetry read

## Inputs

- provider health
- cost and quality data
- benchmark history

## Outputs

- provider scorecard
- issues
- recommended changes
## Required behavior

- Load the constitutional core and the relevant Principal context.
- Use the minimum sufficient specialists.
- Distinguish facts, inference, and speculation.
- Include evidence, tradeoffs, risk, confidence, and one clear next action.
- Record measurable outcomes in the Evidence Ledger.
- Escalate only when missing information or authority blocks progress.

## Success criteria

The operation creates useful, low-noise output and measurable value.

## Failure conditions

Unsupported conclusions, hidden assumptions, unclear action, repeated noise,
unavailable required capabilities, or no measurable value.


---

## Source: `standing-operations/SO-016-model-benchmark-review.md`

---
id: SO-016
title: Model Benchmark Review
version: 1.0.0
status: Accepted
owner: Listening Post
machine:
  owner: Chip
  specialists: [data-analyst]
  type: standing_operation
  slug: model-benchmark-review
  trigger: scheduled
  communication_intent: Evidence
---

# Model Benchmark Review

## Mission

Compare available model providers against LPOS benchmarks.


## Objective

Models compared against fixed benchmarks monthly.

## Required capabilities

- scheduled or event-driven execution
- read access to the listed inputs
- evidence recording
- model invocation across configured providers

## Inputs

- LPOS benchmarks
- model provider results

## Outputs

- comparison
- regressions
- routing recommendations
## Required behavior

- Load the constitutional core and the relevant Principal context.
- Use the minimum sufficient specialists.
- Distinguish facts, inference, and speculation.
- Include evidence, tradeoffs, risk, confidence, and one clear next action.
- Record measurable outcomes in the Evidence Ledger.
- Escalate only when missing information or authority blocks progress.

## Success criteria

The operation creates useful, low-noise output and measurable value.

## Failure conditions

Unsupported conclusions, hidden assumptions, unclear action, repeated noise,
unavailable required capabilities, or no measurable value.


---

## Source: `standing-operations/SO-017-knowledge-review.md`

---
id: SO-017
title: Knowledge Review
version: 1.0.0
status: Accepted
owner: Listening Post
machine:
  owner: Chip
  specialists: [technical-writer]
  type: standing_operation
  slug: knowledge-review
  trigger: scheduled
  communication_intent: Status
---

# Knowledge Review

## Mission

Identify missing, stale, duplicate, or hard-to-find knowledge.


## Objective

Stale, missing, or duplicated knowledge found monthly.

## Required capabilities

- scheduled or event-driven execution
- read access to the listed inputs
- evidence recording

## Inputs

- documentation inventory
- search failures
- staleness signals

## Outputs

- gaps
- stale items
- duplicates
- fix list
## Required behavior

- Load the constitutional core and the relevant Principal context.
- Use the minimum sufficient specialists.
- Distinguish facts, inference, and speculation.
- Include evidence, tradeoffs, risk, confidence, and one clear next action.
- Record measurable outcomes in the Evidence Ledger.
- Escalate only when missing information or authority blocks progress.

## Success criteria

The operation creates useful, low-noise output and measurable value.

## Failure conditions

Unsupported conclusions, hidden assumptions, unclear action, repeated noise,
unavailable required capabilities, or no measurable value.


---

## Source: `standing-operations/SO-018-monthly-effectiveness-review.md`

---
id: SO-018
title: Monthly Effectiveness Review
version: 1.0.0
status: Accepted
owner: Listening Post
machine:
  owner: Chip
  specialists: [evidence-analyst]
  type: standing_operation
  slug: monthly-effectiveness-review
  trigger: scheduled
  communication_intent: Evidence
---

# Monthly Effectiveness Review

## Mission

Measure LPOS value, adoption, friction, and Principal outcomes.


## Objective

LPOS value and friction measured monthly.

## Required capabilities

- scheduled or event-driven execution
- read access to the listed inputs
- evidence recording

## Inputs

- evidence ledger
- decision ledger
- usage friction

## Outputs

- value summary
- adoption
- friction
- improvements
## Required behavior

- Load the constitutional core and the relevant Principal context.
- Use the minimum sufficient specialists.
- Distinguish facts, inference, and speculation.
- Include evidence, tradeoffs, risk, confidence, and one clear next action.
- Record measurable outcomes in the Evidence Ledger.
- Escalate only when missing information or authority blocks progress.

## Success criteria

The operation creates useful, low-noise output and measurable value.

## Failure conditions

Unsupported conclusions, hidden assumptions, unclear action, repeated noise,
unavailable required capabilities, or no measurable value.


---

## Source: `standing-operations/SO-019-decision-retrospective.md`

---
id: SO-019
title: Decision Retrospective
version: 1.0.0
status: Accepted
owner: Listening Post
machine:
  owner: Chip
  specialists: [decision-analyst]
  type: standing_operation
  slug: decision-retrospective
  trigger: scheduled
  communication_intent: Evidence
---

# Decision Retrospective

## Mission

Compare important decisions with actual outcomes and assumptions.


## Objective

Important decisions compared with actual outcomes.

## Required capabilities

- scheduled or event-driven execution
- read access to the listed inputs
- evidence recording

## Inputs

- decision ledger
- observed outcomes

## Outputs

- validated and refuted decisions
- lessons
- calibration notes
## Required behavior

- Load the constitutional core and the relevant Principal context.
- Use the minimum sufficient specialists.
- Distinguish facts, inference, and speculation.
- Include evidence, tradeoffs, risk, confidence, and one clear next action.
- Record measurable outcomes in the Evidence Ledger.
- Escalate only when missing information or authority blocks progress.

## Success criteria

The operation creates useful, low-noise output and measurable value.

## Failure conditions

Unsupported conclusions, hidden assumptions, unclear action, repeated noise,
unavailable required capabilities, or no measurable value.


---

## Source: `standing-operations/SO-020-platform-health-review.md`

---
id: SO-020
title: Platform Health Review
version: 1.0.0
status: Accepted
owner: Listening Post
machine:
  owner: Chip
  specialists: [software-architect, automation-architect]
  type: standing_operation
  slug: platform-health-review
  trigger: scheduled
  communication_intent: Operational Alert
---

# Platform Health Review

## Mission

Review runtime, provider, infrastructure, and integration health.


## Objective

Runtime and integration health reviewed weekly.

## Required capabilities

- scheduled or event-driven execution
- read access to the listed inputs
- evidence recording
- runtime telemetry read

## Inputs

- runtime logs
- integration status
- error rates

## Outputs

- health summary
- failures
- capacity risks
- actions
## Required behavior

- Load the constitutional core and the relevant Principal context.
- Use the minimum sufficient specialists.
- Distinguish facts, inference, and speculation.
- Include evidence, tradeoffs, risk, confidence, and one clear next action.
- Record measurable outcomes in the Evidence Ledger.
- Escalate only when missing information or authority blocks progress.

## Success criteria

The operation creates useful, low-noise output and measurable value.

## Failure conditions

Unsupported conclusions, hidden assumptions, unclear action, repeated noise,
unavailable required capabilities, or no measurable value.


---

## Source: `standing-operations/SO-021-principal-feedback-loop.md`

---
id: SO-021
title: Principal Feedback Loop
version: 1.1.0
status: Accepted
owner: Listening Post
machine:
  type: standing_operation
  slug: principal-feedback-loop
  owner: Chip
  specialists: [executive-writer, operations-manager]
  trigger: scheduled            # runtime schedule: every 10 minutes
  communication_intent: Collaboration
---

# Principal Feedback Loop

## Mission

Carry blocking questions, consent requests, and exact-action approvals to the Principal
through verified channel adapters; collect answers; close the first verified answer
atomically; and route new feedback as normal LPOS tasks.

## Objective

Principal questions are delivered and resolved through a verified channel within one
collection cycle without duplicate sends, replay, guessed consent, or authorization drift.

## Required capabilities

- scheduled or event-driven workflow execution
- verified outbound and inbound Principal channel adapters
- provider-neutral MessageIdentity capture
- transactional question closure and replay protection
- exact-action approval binding
- evidence and decision recording

## Activation

SO-021 is disabled until onboarding verifies outbound delivery, inbound collection,
Principal round-trip correlation, and the Principal's exact identity for at least one
channel. Credentials stay in the deployment secret store. Until activation, questions
remain pending and surface in the trusted session.

## Outbound behavior

- Ask only when work is blocked on a consequential action, material clarification, or
  taste, brand, or strategy approval. Batch non-urgent questions.
- Assign an immutable question ID and persist the ApprovalRequest or clarification before
  delivery.
- For approvals, include the exact proposed action, its canonical SHA-256 action hash,
  options, recommendation, and the result of no reply: **hold**.
- Send through the configured intent-to-channel route and sign with the confirmed office
  identity.
- Send at most one reminder per question and never convert silence into consent.

## Inbound behavior

1. Collect messages since the transactional channel cursor.
2. Construct a provider-neutral MessageIdentity containing channel, provider, message ID,
   thread ID, and sender.
3. Reject execution from identities not mapped to the Principal. Log suspected
   impersonation as an Operational Alert.
4. Correlate the message to an open question. An approval counts only when it is
   affirmative and bound to the unchanged exact action hash.
5. Close the question and record the answer in one transaction. The first verified answer
   wins; later answers are audit events only and are never executed.
6. Route unmatched verified Principal feedback through the normal TaskEnvelope and Quality
   Router.
7. Advance the channel cursor only after the message outcome is safely persisted.

## State machine

`disabled → outbound_verified → inbox_verified → round_trip_pending → active → degraded →
suspended`. The workflow runs only in `active` or `degraded`. Two consecutive failed cycles
move `active` to `degraded`; five move it to `suspended` and emit an Operational Alert.

## Success criteria

Questions reach the Principal once, verified answers are applied within one cycle, exact
actions cannot change after approval, duplicates and replays are harmless, and every cycle
produces one StandingOperationRun and one EvidenceRecord.

## Failure conditions

An unverified identity is treated as the Principal; silence becomes consent; an approval
applies to a different action hash; duplicate or replayed messages execute twice; a cursor
advances before persistence; or a question is acknowledged without being transactionally
closed.
