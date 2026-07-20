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

