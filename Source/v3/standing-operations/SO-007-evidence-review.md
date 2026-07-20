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

