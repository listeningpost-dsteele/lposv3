---
id: CS-AI-005
title: Agent Runtime and State Integrity Standard
version: 1.0.0
status: Accepted
owner: Listening Post
---

<!-- Generated from LPOS expert corpus v1.2, source SHA-256 fcc787db6f8ab0be691f9030af927005a005561db1c0fecdee5f6dbdc87a060f, source lines 41413-41440. Runtime lifecycle is governed separately. -->

Define:

- authoritative task and agent states;
- valid transitions and authorized actors;
- atomicity and partial commit;
- idempotency and deduplication;
- retries and terminal failure;
- timeouts, leases, and abandoned work;
- pause, approval, cancellation, and propagation;
- checkpoints and resume;
- concurrency and ordering;
- provider and tool-call evidence;
- budgets and loop prevention;
- runtime and state-schema compatibility;
- recovery and rollback.

Test crash, restart, timeout, rate limit, cancellation, duplicate delivery, partial commit, stale resume, and migration.
