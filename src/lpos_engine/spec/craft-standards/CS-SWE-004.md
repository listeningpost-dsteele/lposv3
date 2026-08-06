---
id: CS-SWE-004
title: Integration Engineering Standard
version: 1.0.0
status: Accepted
owner: Listening Post
---

<!-- Generated from LPOS expert corpus v1.2, source SHA-256 fcc787db6f8ab0be691f9030af927005a005561db1c0fecdee5f6dbdc87a060f, source lines 37432-37531. Runtime lifecycle is governed separately. -->

# Integration Engineering Standard

## Purpose

Ensure software boundaries between separately owned systems remain authorized, versioned, recoverable, observable, and consistent.

## Required contract

Every material integration must identify:

- external system and owner;
- exact environment;
- API, SDK, schema, or protocol version;
- authoritative documentation;
- authentication;
- minimum scopes;
- credential lifecycle;
- tenant and account boundary;
- data classifications;
- source of truth;
- field and identifier mapping;
- create, update, delete, archive, and restore behavior;
- rate and quota behavior;
- timeout;
- retry classification;
- idempotency;
- ordering and deduplication;
- replay and backfill;
- reconciliation;
- observability;
- support;
- deprecation;
- and disconnect.

## Authority and privacy

Integration code may not request or use authority beyond the approved contract.

Secrets must remain in approved secret storage. Sensitive payloads must not be copied into prompts, source, fixtures, logs, or review evidence.

Security and Privacy specialists own approval of authority and data-use boundaries.

## Consistency and recovery

A synchronization integration must define how it detects and repairs:

- missed events;
- duplicate events;
- out-of-order events;
- partial batches;
- expired credentials;
- interrupted backfills;
- local and remote divergence;
- provider outage;
- and schema or contract drift.

Exactly-once behavior must not be assumed.

## Verification

Material integration evidence requires:

- contract tests;
- mapping tests;
- failure and recovery tests;
- retry and idempotency tests;
- ordering and duplicate tests where relevant;
- backfill and reconciliation tests where relevant;
- and an authorized real sandbox or contract-faithful boundary.

Mocks alone cannot establish readiness.

## Rejection conditions

Reject an integration that:

- uses unversioned or remembered provider behavior;
- asks for excessive scopes;
- lacks source-of-truth rules;
- silently loses data;
- omits pagination or rate limits;
- retries unsafe operations;
- trusts unsigned webhooks;
- assumes ordering or exactly-once delivery;
- has no reconciliation;
- exposes credentials;
- or calls authentication success a complete integration.
