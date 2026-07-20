---
id: SO-004
title: Inbox Review
version: 1.0.0
status: Accepted
owner: Listening Post
machine:
  owner: Chip
  specialists: [executive-writer, relationship-analyst]
  type: standing_operation
  slug: inbox-review
  trigger: scheduled
  communication_intent: Status
---

# Inbox Review

## Mission

Identify messages requiring decisions, replies, delegation, or archival.


## Objective

Every inbox item triaged to decision, reply, delegation, or archive.

## Required capabilities

- scheduled or event-driven execution
- read access to the listed inputs
- evidence recording
- mailbox read
## Inputs

- email
- Principal Model
- active initiatives

## Outputs

- priority messages
- draft replies
- delegations
- follow-ups

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

