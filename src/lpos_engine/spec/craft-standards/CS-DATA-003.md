---
id: CS-DATA-003
title: Analytics Engineering and Metric Governance Standard
version: 1.0.0
status: Accepted
owner: Listening Post
---

<!-- Generated from LPOS expert corpus v1.2, source SHA-256 fcc787db6f8ab0be691f9030af927005a005561db1c0fecdee5f6dbdc87a060f, source lines 30019-30069. Runtime lifecycle is governed separately. -->

# Analytics Engineering and Metric Governance Standard

## Purpose

Create consistent analytical meaning across models, metrics, and consumers.

## Required practice

- Define grain, keys, temporal behavior, and joins.
- Specify numerator, denominator, population, period, exclusions, and attribution.
- Assign semantic owner.
- Test edge cases and comparability.
- Version, migrate, and deprecate definitions.

## Rejection conditions

- Metric only defined by query.
- Many-to-many double count.
- Silent definition change.
- No owner.
- Comparing incomparable periods.

## Required review

Material work requires a qualified fresh-context reviewer, exact-artifact binding, evidence that the
required method ran, recorded findings and dispositions, and verification before completion. The
creator may not certify independent acceptance of its own work.


---

## Craft Standard: Decision Analysis and Reproducibility Standard

```yaml
id: CS-DATA-004
title: Decision Analysis and Reproducibility Standard
version: 1.0.0
status: Accepted
owner: Listening Post
```
