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

