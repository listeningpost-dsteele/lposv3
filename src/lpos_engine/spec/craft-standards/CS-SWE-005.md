---
id: CS-SWE-005
title: Software Diagnostics and Maintenance Standard
version: 1.0.0
status: Accepted
owner: Listening Post
---

<!-- Generated from LPOS expert corpus v1.2, source SHA-256 fcc787db6f8ab0be691f9030af927005a005561db1c0fecdee5f6dbdc87a060f, source lines 37532-37615. Runtime lifecycle is governed separately. -->

# Software Diagnostics and Maintenance Standard

## Purpose

Ensure defects and recurring failures are diagnosed through evidence rather than speculative patches.

## Required diagnostic sequence

For material failures:

1. freeze expected and observed behavior;
2. identify environment, version, configuration, data, and impact;
3. reproduce or document bounded non-reproduction;
4. compare working and failing conditions;
5. maintain a hypothesis ledger;
6. instrument the smallest relevant boundary;
7. isolate the mechanism;
8. distinguish mitigation, direct cause, contributing factors, detection failure, and recovery failure;
9. define the smallest safe correction;
10. verify the original failure and adjacent behavior;
11. and submit correction evidence for independent review.

## Root-cause standard

A root cause must explain:

- the mechanism;
- the observed evidence;
- the triggering or enabling conditions;
- and why the proposed correction prevents recurrence.

The component that emitted the error is not automatically the root cause.

A restart, rollback, cache clear, retry, feature flag, or manual cleanup is a mitigation unless it removes the mechanism.

## Non-reproduction standard

`DEFECT_NOT_REPRODUCED` must include:

- attempts;
- environment differences;
- evidence reviewed;
- limitations;
- missing telemetry;
- and the next discriminating step.

It must not be translated into “no issue.”

## Correction standard

The correction must:

- stay within the confirmed boundary;
- preserve approved behavior;
- include regression evidence;
- address migration or data repair;
- improve detection or diagnostics when they failed;
- and define rollback.

## Rejection conditions

Reject diagnostic work that:

- patches before bounding the failure;
- treats temporal proximity as causation;
- changes multiple variables without accounting;
- swallows the symptom;
- blames a user, provider, network, or race without evidence;
- broadens into a rewrite;
- deletes the exposing test;
- or closes from one successful run.
