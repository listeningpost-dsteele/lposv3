---
id: SO-002
title: Opportunity Intelligence
version: 1.0.0
status: Accepted
owner: Listening Post
machine:
  owner: Chip
  specialists: [technology-scout, market-research-analyst, decision-analyst]
  type: standing_operation
  slug: opportunity-intelligence
  trigger: scheduled
  communication_intent: Executive Decision
---

# Opportunity Intelligence

## Mission

Discover, validate, challenge, and prioritize high-value opportunities.


## Objective

A ranked, evidence-based opportunity queue.

## Required capabilities

- scheduled or event-driven execution
- read access to the listed inputs
- evidence recording
## Inputs

- technology signals
- research sources
- customer evidence
- internal ideas
- benchmarks

## Outputs

- ranked opportunities
- rejections
- implementation plans
- evidence estimates

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

