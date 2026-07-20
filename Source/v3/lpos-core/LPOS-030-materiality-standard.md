---
id: LPOS-030
title: Materiality Standard
version: 1.0.0
status: Accepted
classification: Core Architecture
owner: Listening Post
machine:
  normative: true
---

# Materiality Standard

Materiality decides whether a task requires the interpretation contract,
independent review, CS-003, blocking conflict questions, baselines, and a
rollback path. Without a shared definition, two runs treat the same task
differently; this standard is that definition.

## A task is material when any of the following holds

- It takes or enables an external or irreversible action.
- It changes an approved artifact.
- Its output faces a customer or the public.
- It has legal, financial, security, or privacy impact.
- It involves strategy, brand, or the Principal's taste.
- It modifies a long-lived specification.
- A failure would cost more to undo than the review costs to run.

## Otherwise

Routine internal work such as status summaries, internal notes, and reversible
scratch work is non-material and skips the material controls. Evidence
recording still applies to every Standing Operation run.

## Overrides and doubt

The Principal may designate any task material or non-material; the designation
is recorded as a decision record. When classification is uncertain, treat the
task as material.
