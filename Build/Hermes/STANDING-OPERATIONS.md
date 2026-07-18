# LPOS Standing Operations


---

## Source: `standing-operations/SO-001-executive-brief.md`

---
id: SO-001
title: Executive Brief
version: 1.0.0
status: Accepted
owner: Listening Post
machine:
  type: standing_operation
  slug: executive-brief
  trigger: scheduled
  communication_intent: Executive Decision
---

# Executive Brief

## Mission

Prepare one concise decision-focused briefing for the Principal.

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
  type: standing_operation
  slug: opportunity-intelligence
  trigger: scheduled
  communication_intent: Executive Decision
---

# Opportunity Intelligence

## Mission

Discover, validate, challenge, and prioritize high-value opportunities.

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
  type: standing_operation
  slug: calendar-review
  trigger: scheduled
  communication_intent: Status
---

# Calendar Review

## Mission

Prepare the Principal for upcoming commitments and identify conflicts.

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
  type: standing_operation
  slug: inbox-review
  trigger: scheduled
  communication_intent: Status
---

# Inbox Review

## Mission

Identify messages requiring decisions, replies, delegation, or archival.

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
  type: standing_operation
  slug: meeting-preparation
  trigger: event-driven
  communication_intent: Collaboration
---

# Meeting Preparation

## Mission

Create a concise brief before an important meeting.

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
  type: standing_operation
  slug: weekly-review
  trigger: scheduled
  communication_intent: Executive Decision
---

# Weekly Review

## Mission

Evaluate progress, evidence, decisions, and priorities.

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
  type: standing_operation
  slug: evidence-review
  trigger: scheduled
  communication_intent: Evidence
---

# Evidence Review

## Mission

Evaluate whether implemented work created intended value.

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
  type: standing_operation
  slug: standing-operation-health
  trigger: scheduled
  communication_intent: Operational Alert
---

# Standing Operation Health

## Mission

Detect failed, noisy, low-value, or redundant recurring operations.

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
  type: standing_operation
  slug: relationship-review
  trigger: scheduled
  communication_intent: Status
---

# Relationship Review

## Mission

Identify important relationship follow-ups and meeting opportunities.

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
  type: standing_operation
  slug: technology-signals
  trigger: scheduled
  communication_intent: Executive Decision
---

# Technology Signals

## Mission

Surface weak technical signals rather than obvious news.

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
  type: standing_operation
  slug: daily-execution-review
  trigger: scheduled
  communication_intent: Status
---

# Daily Execution Review

## Mission

Review active work, blockers, dependencies, and completion risk.

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
  type: standing_operation
  slug: pipeline-review
  trigger: scheduled
  communication_intent: Executive Decision
---

# Pipeline Review

## Mission

Review revenue pipeline health, next actions, and forecast risk.

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
  type: standing_operation
  slug: customer-review
  trigger: scheduled
  communication_intent: Executive Decision
---

# Customer Review

## Mission

Summarize customer health, needs, risks, and expansion opportunities.

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
  type: standing_operation
  slug: security-review
  trigger: scheduled
  communication_intent: Operational Alert
---

# Security Review

## Mission

Review security-relevant changes, permissions, providers, and incidents.

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
  type: standing_operation
  slug: provider-review
  trigger: scheduled
  communication_intent: Status
---

# Provider Review

## Mission

Evaluate provider health, quality, cost, and compatibility.

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
  type: standing_operation
  slug: model-benchmark-review
  trigger: scheduled
  communication_intent: Evidence
---

# Model Benchmark Review

## Mission

Compare available model providers against LPOS benchmarks.

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
  type: standing_operation
  slug: knowledge-review
  trigger: scheduled
  communication_intent: Status
---

# Knowledge Review

## Mission

Identify missing, stale, duplicate, or hard-to-find knowledge.

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
  type: standing_operation
  slug: monthly-effectiveness-review
  trigger: scheduled
  communication_intent: Evidence
---

# Monthly Effectiveness Review

## Mission

Measure LPOS value, adoption, friction, and Principal outcomes.

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
  type: standing_operation
  slug: decision-retrospective
  trigger: scheduled
  communication_intent: Evidence
---

# Decision Retrospective

## Mission

Compare important decisions with actual outcomes and assumptions.

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
  type: standing_operation
  slug: platform-health-review
  trigger: scheduled
  communication_intent: Operational Alert
---

# Platform Health Review

## Mission

Review runtime, provider, infrastructure, and integration health.

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
