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

