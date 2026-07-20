---
id: SO-014
title: Security Review
version: 1.0.0
status: Accepted
owner: Listening Post
machine:
  owner: Chip
  specialists: [threat-analyst, security-architect]
  type: standing_operation
  slug: security-review
  trigger: scheduled
  communication_intent: Operational Alert
---

# Security Review

## Mission

Review security-relevant changes, permissions, providers, and incidents.


## Objective

Security-relevant changes reviewed within a week.

## Required capabilities

- scheduled or event-driven execution
- read access to the listed inputs
- evidence recording
- configuration and log read

## Inputs

- permission changes
- provider changes
- incidents
- config diffs

## Outputs

- findings
- severities
- mitigations
- approvals needed
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

