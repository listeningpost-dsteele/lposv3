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

