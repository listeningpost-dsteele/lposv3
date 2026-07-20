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

