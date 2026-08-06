---
id: CS-GOV-005
title: Repository, Provenance, and Change Integrity Standard
version: 1.0.0
status: Accepted
owner: Listening Post
---

<!-- Generated from LPOS expert corpus v1.2, source SHA-256 fcc787db6f8ab0be691f9030af927005a005561db1c0fecdee5f6dbdc87a060f, source lines 49604-49644. Runtime lifecycle is governed separately. -->

# Repository, Provenance, and Change Integrity Standard

## Purpose

Prove the complete source and migration state without manual partial manifests.

## Required practice

- Freeze exact base and candidate.
- Classify the full tree.
- Reject dirty, missing, unlisted, orphaned, and stale state.
- Bind generated artifacts to source and generator.
- Cover source, registry, schema, data, docs, and rollback.

## Rejection conditions

- Manual file list.
- Missing file silently skipped.
- Dirty tree accepted.
- Generated artifact edited as source.
- Rollback restores code only.

## Required review

Material work requires a qualified fresh-context reviewer, exact-artifact binding, evidence that the
required method ran, recorded findings and dispositions, and verification before completion. The
creator may not certify independent acceptance of its own work.
