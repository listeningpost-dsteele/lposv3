---
id: CS-PLAT-002
title: Platform Engineering and Developer Experience Standard
version: 1.0.0
status: Accepted
owner: Listening Post
---

<!-- Generated from LPOS expert corpus v1.2, source SHA-256 fcc787db6f8ab0be691f9030af927005a005561db1c0fecdee5f6dbdc87a060f, source lines 44862-44898. Runtime lifecycle is governed separately. -->

# Platform Engineering and Developer Experience Standard

A platform capability requires:

- multiple credible consumers or a justified high-leverage shared need;
- explicit consumer jobs;
- a stable contract;
- safe self-service boundaries;
- ownership and support;
- failure and recovery behavior;
- observable state;
- compatibility, migration, and deprecation;
- and adoption evidence based on successful outcomes.

Templates, portals, wrappers, or shared scripts do not become platforms by declaration.

The safe common path should be easier than the unsafe path, while legitimate exceptions remain possible through an explicit contract.

Reject:

- platform theater;
- one-off abstractions;
- hidden manual control planes;
- self-service that bypasses authority;
- unsupported universal claims;
- and adoption measured only by account, repository, or resource creation.
