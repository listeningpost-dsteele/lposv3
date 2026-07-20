---
id: SO-010
title: Technology Signals
version: 1.0.0
status: Accepted
owner: Listening Post
machine:
  owner: Chip
  specialists: [technology-scout, source-validator]
  type: standing_operation
  slug: technology-signals
  trigger: scheduled
  communication_intent: Executive Decision
---

# Technology Signals

## Mission

Surface weak technical signals rather than obvious news.


## Objective

Weak technical signals surfaced before they become news.

## Required capabilities

- scheduled or event-driven execution
- read access to the listed inputs
- evidence recording
## Inputs

- repositories
- papers
- standards
- communities
- benchmarks
- inference developments

## Outputs

- signals
- why they matter
- why they may not matter
- watch items
- recommended experiments

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

