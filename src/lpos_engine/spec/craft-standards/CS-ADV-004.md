---
id: CS-ADV-004
title: Authorized Penetration Testing and Red Team Standard
version: 1.0.0
status: Accepted
owner: Listening Post
---

<!-- Generated from LPOS expert corpus v1.2, source SHA-256 fcc787db6f8ab0be691f9030af927005a005561db1c0fecdee5f6dbdc87a060f, source lines 53310-53360. Runtime lifecycle is governed separately. -->

# Authorized Penetration Testing and Red Team Standard

## Purpose

Validate realistic attacks under explicit ownership, authority, safety, and cleanup controls.

## Required practice

- Revalidate authorization immediately before testing.
- Escalate least-invasively.
- Use test tenants and synthetic data where possible.
- Stop on scope, data, third-party, or availability triggers.
- Verify cleanup and restoration.

## Rejection conditions

- Unowned target.
- Persistent or destructive action outside scope.
- Real data exfiltration.
- No stop control.
- Self-approval.

## Required review

Material work requires a qualified fresh-context reviewer, exact-artifact binding, evidence that the
required method ran, recorded findings and dispositions, and verification before completion. The
creator may not certify independent acceptance of its own work.


---

## Craft Standard: Adversarial Finding Trust and Closure Standard

```yaml
id: CS-ADV-005
title: Adversarial Finding Trust and Closure Standard
version: 1.0.0
status: Accepted
owner: Listening Post
```
