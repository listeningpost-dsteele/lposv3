---
id: SO-017
title: Knowledge Review
version: 1.0.0
status: Accepted
owner: Listening Post
machine:
  owner: Chip
  specialists: [technical-writer]
  type: standing_operation
  slug: knowledge-review
  trigger: scheduled
  communication_intent: Status
---

# Knowledge Review

## Mission

Identify missing, stale, duplicate, or hard-to-find knowledge.


## Objective

Stale, missing, or duplicated knowledge found monthly.

## Required capabilities

- scheduled or event-driven execution
- read access to the listed inputs
- evidence recording

## Inputs

- documentation inventory
- search failures
- staleness signals

## Outputs

- gaps
- stale items
- duplicates
- fix list
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

