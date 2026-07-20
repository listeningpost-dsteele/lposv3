---
id: LPOS-029
title: Interpretation Contract
version: 1.0.0
status: Accepted
classification: Core Architecture
owner: Listening Post
machine:
  normative: true
---

# Interpretation Contract

Guessing is what happens when interpretation stays implicit. Interpretation is
therefore an artifact, not a thought.

## Precedence of intent

1. The Principal's explicit instruction for this task.
2. The recorded specification of the artifact.
3. The existing artifact's observed patterns.
4. General best practice and model priors.

A lower level never silently overrides a higher one. On material work, a conflict
between levels is a blocking question by definition. This refines "ask only
blocking questions": a conflict about what the Principal wants IS blocking. One
option-framed question costs minutes; a wrong guess costs the artifact.

## The contract

Before executing material work, write to the run record:

1. Instruction, verbatim.
2. Interpretation: what will be created or changed.
3. Invariants: what will not change.
4. Conflicts and ambiguities detected, and for each: the question asked, or the
   resolution and why it was not blocking.
5. Verification plan.

Work may not start until the contract exists. Unattended runs resolve conflicts
by precedence (instruction over spec over pattern), flag the resolution
prominently in the output, and never resolve taste or structure by pattern alone.

## Specification discipline

Every long-lived artifact has one spec (`lpos-state/specs/<artifact>.md`):
structural decisions, design tokens, and approved invariants. If no spec exists
when material work begins, seed it from the current approved artifact first.
The artifact is never its own spec; inferring intent from the artifact is
level 3, not level 2.

## Corrections are spec events

A Principal correction means the spec was wrong or silent. Order: update the
spec, then apply the smallest diff that satisfies the correction, then compare
against invariants. A correction applied without a spec update is incomplete.
Regeneration is not correction; drift introduced while correcting is a
regression and fails review.

## Review

The reviewer receives exactly the review envelope: brief, baseline, artifact,
interpretation contract, artifact specification, mapped craft standards,
verification evidence, and intended outcome. Excluded always: the creation
conversation, the creator's private reasoning, and the creator's
self-assessment. Any change not named by the contract, or any conflict resolved
by guess on material work, is an automatic REJECT.

