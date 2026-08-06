---
id: CS-DATA-002
title: Data Engineering and Data Product Standard
version: 1.0.0
status: Accepted
owner: Listening Post
---

<!-- Generated from LPOS expert corpus v1.2, source SHA-256 fcc787db6f8ab0be691f9030af927005a005561db1c0fecdee5f6dbdc87a060f, source lines 29978-30028. Runtime lifecycle is governed separately. -->

# Data Engineering and Data Product Standard

## Purpose

Build reliable, contract-driven, recoverable analytical data systems.

## Required practice

- Inspect actual source behavior.
- Define schema, semantics owner, identity, freshness, retention, and compatibility.
- Engineer idempotency, ordering, late data, deletes, replay, and backfill.
- Preserve lineage and exact revisions.
- Prove recovery and consumer delivery.

## Rejection conditions

- Silent dropped records.
- Schema drift without migration.
- Backfill without reconciliation.
- Pipeline success without output completeness.
- Unauthorized collection.

## Required review

Material work requires a qualified fresh-context reviewer, exact-artifact binding, evidence that the
required method ran, recorded findings and dispositions, and verification before completion. The
creator may not certify independent acceptance of its own work.


---

## Craft Standard: Analytics Engineering and Metric Governance Standard

```yaml
id: CS-DATA-003
title: Analytics Engineering and Metric Governance Standard
version: 1.0.0
status: Accepted
owner: Listening Post
```
