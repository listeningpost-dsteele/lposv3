---
id: CS-SWE-002
title: Software Architecture and Technical Decision Standard
version: 1.0.0
status: Accepted
owner: Listening Post
---

<!-- Generated from LPOS expert corpus v1.2, source SHA-256 fcc787db6f8ab0be691f9030af927005a005561db1c0fecdee5f6dbdc87a060f, source lines 37246-37345. Runtime lifecycle is governed separately. -->

# Software Architecture and Technical Decision Standard

## Purpose

Ensure architecture work resolves a necessary technical decision in an inspected system and produces an implementable, migratable, verifiable contract.

## Required architecture question

Every material architecture artifact must state:

- approved behavior or outcome;
- exact decision;
- current system evidence;
- decision owner;
- constraints and quality attributes;
- implementation blocked;
- and whether no architecture change is a credible option.

## Current-state requirement

Architecture may not be labeled implementation-ready unless the architect inspected:

- the target repository and revision;
- current components and interfaces;
- data and state ownership;
- runtime assumptions;
- tests and observability;
- migration state;
- and relevant failure evidence.

Documentation and diagrams may supplement, but not replace, inspection.

## Alternatives requirement

Evaluate credible alternatives, including when appropriate:

- existing architecture unchanged;
- local extension;
- consolidation;
- extraction;
- proven dependency;
- staged migration;
- reversible experiment;
- and no change.

Each option must show consequences for behavior, simplicity, failure, state, security, migration, testability, observability, cost, ownership, and reversibility.

## Architecture contract requirement

The selected design must define:

- component responsibilities;
- interfaces;
- data ownership;
- state transitions;
- consistency and transaction boundaries;
- error taxonomy;
- timeout, retry, idempotency, ordering, cancellation, and recovery;
- configuration and secret boundaries;
- trust boundaries requiring Security review;
- observability;
- migration;
- rollout and rollback;
- testability;
- and ownership.

## Simplicity rule

A new service, abstraction, dependency, framework, database, queue, event bus, or rewrite requires a material verified advantage over the smallest coherent existing-system alternative.

Architecture must not be used to display sophistication.

## Rejection conditions

Reject architecture that:

- was designed from a product description alone;
- uses a pattern name as reasoning;
- invents current system behavior;
- hides unknowns;
- omits state or failure;
- has no migration;
- has no owner;
- makes unbounded compatibility promises;
- treats a prototype as production-ready;
- delegates security or observability as later work;
- or cannot be translated into bounded implementation and verification.
