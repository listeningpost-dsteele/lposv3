---
id: CS-RINT-003
title: Evidence Integrity and Source Validation Standard
version: 1.0.0
status: Accepted
owner: Listening Post
---

<!-- Generated from LPOS expert corpus v1.2, source SHA-256 fcc787db6f8ab0be691f9030af927005a005561db1c0fecdee5f6dbdc87a060f, source lines 7785-7855. Runtime lifecycle is governed separately. -->

## Purpose

Govern source, provenance, methodology, and claim-level verification across LPOS.

## Claim-level review

For each material claim, evaluate:

- exact wording and type;
- intended use and consequence;
- supporting source and location;
- source provenance and citation chain;
- authority for the exact claim;
- methodology and sample;
- date, version, and applicability;
- independence, incentives, and conflicts;
- corroboration and contrary evidence;
- quote or calculation integrity;
- and permitted conclusion.

## Approved claim statuses

Use:

- `VERIFIED`
- `SUPPORTED`
- `SUPPORTED_WITH_LIMITS`
- `INFERRED`
- `FORECAST`
- `CONTESTED`
- `STALE`
- `MISQUOTED`
- `MISINTERPRETED`
- `SOURCE_UNAVAILABLE`
- `UNSUPPORTED`
- `REFUTED`
- `OUT_OF_SCOPE`

Do not replace these with vague “high confidence” labels.

## Independence

Material evidence review must be fresh-context and exact-revision. A creator may not independently approve its own research. Review records must remain separate from creator records.

## Blocking rules

A material `UNSUPPORTED`, `REFUTED`, `MISQUOTED`, `MISINTERPRETED`, or materially `STALE` claim may not be represented as verified fact. The authorized owner may accept a known uncertainty or risk, but the evidence status must remain visible.

## Prohibited shortcuts

Reject:

- domain-reputation-only source scoring;
- citation counting;
- secondary-source repetition treated as corroboration;
- abstract-only study review;
- quote verification without context;
- and claim rewriting that evades the original review.
