---
id: CS-SWE-003
title: Software Implementation and Change Integrity Standard
version: 1.0.0
status: Accepted
owner: Listening Post
---

<!-- Generated from LPOS expert corpus v1.2, source SHA-256 fcc787db6f8ab0be691f9030af927005a005561db1c0fecdee5f6dbdc87a060f, source lines 37346-37431. Runtime lifecycle is governed separately. -->

# Software Implementation and Change Integrity Standard

## Purpose

Ensure approved behavior becomes working software in the exact target system without hidden scope, placeholder completion, or evidence substitution.

## Required implementation process

The creator must:

1. validate the task and authority;
2. inspect the repository, revision, runtime, tests, configuration, and generated sources;
3. establish a baseline;
4. plan the smallest coherent change;
5. implement using repository-native practice;
6. handle material success, failure, retry, recovery, and state behavior;
7. protect data and interfaces;
8. write meaningful developer tests;
9. run static checks, build, tests, migrations, generators, and required real execution;
10. inspect the resulting state and diff;
11. produce the Change Manifest and Engineering Evidence Packet;
12. and submit the exact revision for fresh-context review.

## Implementation integrity

The implementation must not:

- prescribe or alter product behavior without authority;
- directly edit generated artifacts when a source and generator exist;
- hardcode success;
- leave dead controls or no-op handlers;
- swallow errors;
- hide partial failure;
- create retries without side-effect safety;
- weaken acceptance criteria;
- broaden scope through unrelated refactoring;
- add dependencies without a reason;
- include secrets;
- or claim completion from code generation or configuration.

## Developer-test quality

Developer tests must:

- protect intended behavior;
- cover meaningful boundaries and failure;
- use real dependencies where the tested behavior is the boundary;
- avoid implementation-only assertions without reason;
- be deterministic;
- verify state and side effects;
- and bind to the exact revision.

Tests written by the creator remain creator evidence.

## Real-execution rule

When the required outcome is an endpoint, UI workflow, file, queue, delivery, persisted state, integration, or scheduled operation, the creator must exercise that behavior in an authorized representative environment and inspect the outcome.

Source inspection and a green unit suite are insufficient.

## Rejection conditions

Reject an implementation when:

- it cannot be applied or built;
- the target revision is wrong;
- the behavior is disconnected;
- the code path is not executed;
- the data path is unverified;
- the migration is unsafe;
- the tests would pass for a meaningful defect;
- the evidence is stale or copied;
- or the creator labels its own work release-ready.
