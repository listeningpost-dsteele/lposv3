---
id: SO-005
title: Meeting Preparation
version: 1.0.0
status: Accepted
owner: Listening Post
machine:
  owner: Chip
  specialists: [relationship-analyst]
  type: standing_operation
  slug: meeting-preparation
  trigger: event-driven
  communication_intent: Collaboration
---

# Meeting Preparation

## Mission

Create a concise brief before an important meeting.


## Objective

A usable brief before each important meeting.

## Required capabilities

- scheduled or event-driven execution
- read access to the listed inputs
- evidence recording
- calendar read
- relationship context read
## Inputs

- calendar event
- relationship history
- customer intelligence
- active initiatives

## Outputs

- objective
- participants
- history
- open decisions
- agenda
- recommended questions

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

