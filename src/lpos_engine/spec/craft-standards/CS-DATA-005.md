---
id: CS-DATA-005
title: Data Quality, Lineage, and Incident Standard
version: 1.0.0
status: Accepted
owner: Listening Post
---

<!-- Generated from LPOS expert corpus v1.2, source SHA-256 fcc787db6f8ab0be691f9030af927005a005561db1c0fecdee5f6dbdc87a060f, source lines 30102-30152. Runtime lifecycle is governed separately. -->

# Data Quality, Lineage, and Incident Standard

## Purpose

Make data fitness, defects, correction, and downstream impact explicit and verifiable.

## Required practice

- Define decision-relevant quality expectations.
- Trace field-level lineage to consumers.
- Use reconciliation and contract controls.
- Contain and correct defects.
- Verify every affected output and decision.

## Rejection conditions

- One quality score.
- Freshness used as accuracy proof.
- Upstream fix without downstream rerun.
- Incident closed without consumer inventory.
- History changed silently.

## Required review

Material work requires a qualified fresh-context reviewer, exact-artifact binding, evidence that the
required method ran, recorded findings and dispositions, and verification before completion. The
creator may not certify independent acceptance of its own work.


---

## Craft Standard: Experimentation and Causal Inference Standard

```yaml
id: CS-DATA-006
title: Experimentation and Causal Inference Standard
version: 1.0.0
status: Accepted
owner: Listening Post
```
