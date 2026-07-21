---
id: SO-022
title: Bug Remediation
version: 1.0.0
status: Accepted
owner: Listening Post
machine:
  type: standing_operation
  slug: bug-remediation
  owner: Chip
  specialists: [bug-triage-analyst, debugging-specialist, software-engineer, test-engineer, code-reviewer]
  trigger: event-driven
  communication_intent: Status
---

# Bug Remediation

## Mission

Resolve user-reported defects without human effort where possible, surface only
the unresolvable with a full diagnostic package, and keep the reporter informed.

## Objective

Every reproducible defect fixed and verified autonomously; every fix leaves a
permanent regression fixture; reporters informed at receipt and outcome; only the
genuinely unresolvable reaches a human.

## Required capabilities

- event-driven execution
- sandboxed reproduction and code change (no network, resource-limited)
- test execution
- independent review
- verified-identity outbound email
- evidence recording and benchmark-fixture creation
- approval-gated production change

## Inputs

A BugReport envelope (schema: bug-report.schema.json).

## Outputs

A resolution (verified fix on an isolated branch and PR, a new permanent
regression fixture, a reporter email) or an escalation package (repro status,
root-cause hypothesis, every attempt and why it failed, recommended next action,
and a reporter email that a person is now handling it).

## The loop

1. Acknowledge. Email the reporter that the report was received, with a tracking
   id. Verified contact only; no secrets outbound.
2. Reproduce in a sandbox using more than one strategy. If not reproducible after
   the reproduction budget, escalate as needs-info and ask the reporter specific
   questions.
3. Regression first. Convert the reproduction into a failing fixture before any
   fix is attempted.
4. Diagnose. Localize the root cause with more than one hypothesis; record
   confidence.
5. Remediate loop. Up to the attempt budget, implement a candidate fix on an
   isolated branch, then verify: the new fixture passes and the full suite still
   passes. Record why each rejected attempt failed.
6. Review. An independent reviewer receives the full review envelope and must
   pass the fix. Any change beyond the bug's scope is an automatic reject.
7. Resolve or escalate.
   - Resolve: add the new fixture to the benchmark corpus permanently, record
     evidence, open the fix as a branch and PR, and email the reporter what was
     wrong and that it is fixed, in plain language. Merge or deploy to production
     is not automatic; it is governed by approval and the release pipeline.
   - Escalate: deliver the diagnostic package to the maintainer and email the
     reporter that a person is handling it.

## Escalation floor (the only path to interrupting a human)

Surface when any holds: not reproducible after budget; root cause not localized
with confidence; all fix attempts fail verification; the fix needs an external or
irreversible action; the defect is a product, taste, or policy decision;
security-sensitive; the fix would exceed the bug's scope; duplicate of an open
escalation.

## Success criteria

Reproducible defects fixed and verified with no human effort; a permanent
regression fixture per fix; reporters informed; only the unresolvable escalated,
each with a complete package.

## Failure conditions

An unverified fix claimed resolved; unrequested changes shipped; production
changed without approval; a reporter left uninformed; a report silently dropped;
an escalation without a diagnostic package.
