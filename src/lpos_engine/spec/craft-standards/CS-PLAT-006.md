---
id: CS-PLAT-006
title: Release, Deployment, and Environment Integrity Standard
version: 1.0.0
status: Accepted
owner: Listening Post
---

<!-- Generated from LPOS expert corpus v1.2, source SHA-256 fcc787db6f8ab0be691f9030af927005a005561db1c0fecdee5f6dbdc87a060f, source lines 45008-45041. Runtime lifecycle is governed separately. -->

# Release, Deployment, and Environment Integrity Standard

Every material release must identify:

- exact source;
- dependency locks;
- build inputs;
- immutable artifacts and digests;
- signatures or provenance where required;
- configuration revision;
- migrations;
- environment targets;
- required gates;
- deployment strategy;
- pause and abort conditions;
- rollback or forward recovery;
- and resulting service evidence.

Promote the same artifact through environments where possible. Do not rebuild an unreviewed production variant.

A green pipeline does not prove a healthy service or successful customer workflow.

Reject mutable tags, target ambiguity, skipped gates, production-as-test, secret exposure, incompatible rollback, and creator self-approval.
