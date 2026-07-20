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

