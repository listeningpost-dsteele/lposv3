---
id: CS-QA-005
title: Code Test Strength and Structural Fitness Standard
version: 1.0.0
status: Accepted
owner: Listening Post
---

<!-- Generated from LPOS expert corpus v1.2, source SHA-256 fcc787db6f8ab0be691f9030af927005a005561db1c0fecdee5f6dbdc87a060f, source lines 51825-51875. Runtime lifecycle is governed separately. -->

# Code Test Strength and Structural Fitness Standard

## Purpose

Select risk-relevant code-testing techniques and evaluate whether tests detect meaningful defects.

## Required practice

- Map change to defect classes and invariants.
- Inspect creator assertions and mocks.
- Use characterization, unit, property, fuzz, mutation, and fitness as justified.
- Interpret results, not only scores.
- Bind findings to exact code.

## Rejection conditions

- Universal coverage target.
- Mutation score without survivor review.
- Characterization after refactor.
- Fuzzing without oracle.
- Architecture rule invented after candidate.

## Required review

Material work requires a qualified fresh-context reviewer, exact-artifact binding, evidence that the
required method ran, recorded findings and dispositions, and verification before completion. The
creator may not certify independent acceptance of its own work.


---

## Craft Standard: Nonfunctional Assurance Standard

```yaml
id: CS-QA-006
title: Nonfunctional Assurance Standard
version: 1.0.0
status: Accepted
owner: Listening Post
```
