---
id: CS-SWE-006
title: Software Review Standard
version: 1.0.0
status: Accepted
owner: Listening Post
---

<!-- Generated from LPOS expert corpus v1.2, source SHA-256 fcc787db6f8ab0be691f9030af927005a005561db1c0fecdee5f6dbdc87a060f, source lines 37616-37712. Runtime lifecycle is governed separately. -->

# Software Review Standard

## Purpose

Ensure material architecture and software artifacts receive qualified, fresh-context, exact-revision technical review before independent release assurance.

## Independence

The reviewer must:

- be distinct from the creator;
- use a fresh context;
- identify prior involvement;
- possess the required qualification profile;
- and review the exact candidate revision.

If the reviewer materially edits the artifact, another qualified reviewer must review the resulting revision.

## Review inputs

A material review requires:

- objective and behavior source;
- design and architecture references;
- exact repository, base, and candidate revision;
- Change Manifest;
- creator evidence;
- relevant constraints;
- and known risks.

The creator’s summary is not authoritative.

## Required review method

The reviewer must:

- reconstruct intent;
- inspect surrounding code and every material change;
- challenge failure, state, concurrency, interface, data, security, migration, and compatibility behavior;
- evaluate test and evidence strength;
- inspect scope and maintainability;
- verify generated and dependency changes;
- and issue evidence-bound findings.

## Finding quality

Each blocking or material finding must identify:

- exact location;
- observed behavior;
- expected contract or standard;
- evidence;
- impact;
- severity;
- required outcome;
- and closure verification.

Vague advice and stylistic preference are not findings.

## Allowed dispositions

```text
APPROVE_FOR_NEXT_GATE
APPROVE_WITH_NONBLOCKING_FINDINGS
CHANGES_REQUIRED
REVIEW_BLOCKED
WRONG_PROFESSION_OR_REVIEW_REQUIRED
CAPABILITY_GAP
```

Approval is for the next gate only. It is not release, deployment, security, or compliance approval.

## Rejection conditions

Reject a review when:

- it does not identify the exact revision;
- it relies on the creator’s narrative;
- it ignores surrounding behavior;
- it treats green tests as sufficient;
- it omits migrations, configuration, generated files, or lock files;
- it lacks reviewer qualification or independence;
- it says only “LGTM” or equivalent;
- or it approves a different artifact from the release candidate.
