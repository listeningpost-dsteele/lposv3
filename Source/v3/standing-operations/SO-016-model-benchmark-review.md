---
id: SO-016
title: Model Benchmark Review
version: 1.0.0
status: Accepted
owner: Listening Post
machine:
  owner: Chip
  specialists: [data-analyst]
  type: standing_operation
  slug: model-benchmark-review
  trigger: scheduled
  communication_intent: Evidence
---

# Model Benchmark Review

## Mission

Compare available model providers against LPOS benchmarks.


## Objective

Models compared against fixed benchmarks monthly.

## Required capabilities

- scheduled or event-driven execution
- read access to the listed inputs
- evidence recording
- model invocation across configured providers

## Inputs

- LPOS benchmarks
- model provider results

## Outputs

- comparison
- regressions
- routing recommendations
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

