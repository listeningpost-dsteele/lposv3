---
id: SO-013
title: Customer Review
version: 1.0.0
status: Accepted
owner: Listening Post
machine:
  owner: Chip
  specialists: [customer-insights-analyst]
  type: standing_operation
  slug: customer-review
  trigger: scheduled
  communication_intent: Executive Decision
---

# Customer Review

## Mission

Summarize customer health, needs, risks, and expansion opportunities.


## Objective

Customer health, risk, and expansion assessed weekly.

## Required capabilities

- scheduled or event-driven execution
- read access to the listed inputs
- evidence recording
- customer data read

## Inputs

- customer accounts
- usage and feedback
- support history

## Outputs

- health summary
- needs
- risks
- expansion opportunities
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

