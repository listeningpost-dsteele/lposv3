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

