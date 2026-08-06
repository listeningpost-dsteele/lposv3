---
id: CS-PLAT-003
title: Infrastructure and Cloud Engineering Standard
version: 1.0.0
status: Accepted
owner: Listening Post
---

<!-- Generated from LPOS expert corpus v1.2, source SHA-256 fcc787db6f8ab0be691f9030af927005a005561db1c0fecdee5f6dbdc87a060f, source lines 44899-44937. Runtime lifecycle is governed separately. -->

# Infrastructure and Cloud Engineering Standard

Material infrastructure must define:

- provider and exact target;
- regions and residency;
- resource and network boundaries;
- identity and permissions;
- compute, storage, and capacity;
- source and state;
- drift controls;
- security and privacy inputs;
- cost inputs;
- blast radius;
- rollback or recovery;
- and actual service verification.

Prefer source-controlled, versioned, reviewable infrastructure. Manual changes must be reconciled immediately or explicitly documented as controlled emergency state.

Reject:

- DNS as hosting proof;
- plan as apply proof;
- open access for convenience;
- mutable critical artifacts;
- secrets in source or logs;
- unsupported provider defaults;
- and untested destructive changes.
