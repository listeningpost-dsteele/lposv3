---
id: CS-OPS-003
title: Workflow Automation Engineering Standard
version: 1.0.0
status: Accepted
owner: Listening Post
---

<!-- Generated from LPOS expert corpus v1.2, source SHA-256 fcc787db6f8ab0be691f9030af927005a005561db1c0fecdee5f6dbdc87a060f, source lines 32970-33003. Runtime lifecycle is governed separately. -->

# Workflow Automation Engineering Standard

Every material automation must define:

- approved source process;
- owner and operator;
- trigger and schedule;
- time zone and calendar behavior;
- inputs and validation;
- durable states;
- authority and approvals;
- external side effects;
- idempotency;
- retryable and non-retryable failures;
- timeout and cancellation;
- pause and resume;
- dead-letter or exception handling;
- compensation, reconciliation, and backfill;
- observability;
- manual recovery;
- and success postconditions.

A successful trigger, queue acknowledgement, API response, or process exit code is not sufficient when the real delivery or state change remains unverified.
