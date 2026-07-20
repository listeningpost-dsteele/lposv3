---
id: SO-015
title: Provider Review
version: 1.0.0
status: Accepted
owner: Listening Post
machine:
  owner: Chip
  specialists: [data-analyst, technology-scout]
  type: standing_operation
  slug: provider-review
  trigger: scheduled
  communication_intent: Status
---

# Provider Review

## Mission

Evaluate provider health, quality, cost, and compatibility.


## Objective

Provider quality, cost, and health scored monthly.

## Required capabilities

- scheduled or event-driven execution
- read access to the listed inputs
- evidence recording
- provider telemetry read

## Inputs

- provider health
- cost and quality data
- benchmark history

## Outputs

- provider scorecard
- issues
- recommended changes
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

