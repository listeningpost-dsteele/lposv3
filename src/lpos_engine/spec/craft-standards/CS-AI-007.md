---
id: CS-AI-007
title: Tool and Capability Engineering Standard
version: 1.0.0
status: Accepted
owner: Listening Post
---

<!-- Generated from LPOS expert corpus v1.2, source SHA-256 fcc787db6f8ab0be691f9030af927005a005561db1c0fecdee5f6dbdc87a060f, source lines 41475-41504. Runtime lifecycle is governed separately. -->

Every model-executable capability must define:

- professional purpose and owner;
- qualified users;
- invocation and non-invocation criteria;
- strict input and output schemas;
- permissions and authority;
- side effects and reversibility;
- preconditions, postconditions, and invariants;
- errors, timeout, retry, cancellation, and recovery;
- idempotency and duplicate protection;
- evidence emitted;
- sensitivity and retention;
- implementation revision;
- versioning, compatibility, migration, and deprecation;
- benchmark requirements;
- capability-gap behavior.

A configured tool is not a proven capability. Run the real action and inspect resulting state or delivery.
