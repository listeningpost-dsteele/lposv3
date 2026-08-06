---
id: CS-QA-007
title: Test Reliability and Evidence Trust Standard
version: 1.0.0
status: Accepted
owner: Listening Post
---

<!-- Generated from LPOS expert corpus v1.2, source SHA-256 fcc787db6f8ab0be691f9030af927005a005561db1c0fecdee5f6dbdc87a060f, source lines 51908-51959. Runtime lifecycle is governed separately. -->

# Test Reliability and Evidence Trust Standard

## Purpose

Ensure required tests are deterministic, isolated, reproducible, and not green through rerun or
quarantine abuse.

## Required practice

- Freeze command, candidate, seed, order, environment, and raw failure.
- Reproduce and classify mechanism.
- Fix root cause.
- Validate repeated and varied runs.
- Time-box quarantine with owner, risk, compensation, expiry, and exit.

## Rejection conditions

- Rerun until green.
- Arbitrary sleep.
- Permanent quarantine.
- Product race labeled flake without evidence.
- Failure logs discarded.

## Required review

Material work requires a qualified fresh-context reviewer, exact-artifact binding, evidence that the
required method ran, recorded findings and dispositions, and verification before completion. The
creator may not certify independent acceptance of its own work.


---

## Craft Standard: Production Artifact and Release Verification Standard

```yaml
id: CS-QA-008
title: Production Artifact and Release Verification Standard
version: 1.0.0
status: Accepted
owner: Listening Post
```
