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

