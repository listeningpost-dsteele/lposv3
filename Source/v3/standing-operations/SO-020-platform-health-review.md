---
id: SO-020
title: Platform Health Review
version: 1.0.0
status: Accepted
owner: Listening Post
machine:
  owner: Chip
  specialists: [software-architect, automation-architect]
  type: standing_operation
  slug: platform-health-review
  trigger: scheduled
  communication_intent: Operational Alert
---

# Platform Health Review

## Mission

Review runtime, provider, infrastructure, and integration health.


## Objective

Runtime and integration health reviewed weekly.

## Required capabilities

- scheduled or event-driven execution
- read access to the listed inputs
- evidence recording
- runtime telemetry read

## Inputs

- runtime logs
- integration status
- error rates

## Outputs

- health summary
- failures
- capacity risks
- actions
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

