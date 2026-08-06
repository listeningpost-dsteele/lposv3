---
id: CS-OPS-005
title: Operational Recovery, Reconciliation, and Runbook Standard
version: 1.0.0
status: Accepted
owner: Listening Post
---

<!-- Generated from LPOS expert corpus v1.2, source SHA-256 fcc787db6f8ab0be691f9030af927005a005561db1c0fecdee5f6dbdc87a060f, source lines 33024-33051. Runtime lifecycle is governed separately. -->

# Operational Recovery, Reconciliation, and Runbook Standard

A material workflow must have a version-bound recovery contract when missed, duplicated, partial, out-of-order, or uncertain execution can create harm.

Recovery must distinguish:

- rollback;
- compensation;
- forward recovery;
- replay;
- backfill;
- reconciliation;
- and manual completion.

A timeout does not prove no side effect occurred. A restart is not a recovery strategy. A document that has never been exercised is not proven executable.

Capture exact scenario, operator, revision, steps, decisions, resulting state, timing, limitations, and required corrections.
