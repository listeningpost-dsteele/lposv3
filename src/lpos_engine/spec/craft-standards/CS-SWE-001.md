---
id: CS-SWE-001
title: Software Engineering Practice Standard
version: 1.0.0
status: Accepted
owner: Listening Post
---

<!-- Generated from LPOS expert corpus v1.2, source SHA-256 fcc787db6f8ab0be691f9030af927005a005561db1c0fecdee5f6dbdc87a060f, source lines 37135-37245. Runtime lifecycle is governed separately. -->

# Software Engineering Practice Standard

## Purpose

Govern professional software creation and technical review across architecture, implementation, integration, maintenance, diagnostics, and review.

## Required practice

Every material Software Engineering assignment must:

1. identify the exact repository, revision, environment, and artifact;
2. trace to an approved objective and behavior contract;
3. load a project-specific qualification profile;
4. inspect the real repository and relevant runtime before deciding;
5. establish current behavior or system state;
6. preserve approved strengths;
7. choose the smallest coherent change;
8. separate product, design, architecture, implementation, platform, AI-system, security, data, and assurance decisions;
9. address failure, recovery, compatibility, migration, observability, and rollback where material;
10. run repository-native checks and required real behavior;
11. bind evidence to the exact artifact revision;
12. use a fresh-context qualified reviewer;
13. treat creator evidence as necessary but not independent;
14. declare capability gaps instead of improvising expertise;
15. and avoid production or consequential action outside explicit authority.

## Evidence classes

Software Engineering evidence must distinguish:

```text
SOURCE_INSPECTION
RUNTIME_OBSERVATION
REPRODUCTION
STATIC_CHECK
BUILD_RESULT
DEVELOPER_TEST_RESULT
CONTRACT_TEST_RESULT
REAL_WORKFLOW_RESULT
STATE_VALIDATION
MIGRATION_RESULT
ROLLBACK_RESULT
REVIEW_FINDING
ASSURANCE_RESULT
CREATOR_CLAIM
ASSUMPTION
```

A creator claim is not execution evidence. A configuration file is not deployment evidence. A passing unit test is not end-to-end evidence.

## Change discipline

A material change must include:

- objective and non-goals;
- baseline;
- exact change boundary;
- behavior and constraints;
- files and interfaces affected;
- tests;
- real execution;
- data and migration effects;
- security and privacy effects;
- observability;
- documentation impact;
- rollback;
- known limitations;
- and review disposition.

Unrelated cleanup must be separated unless it is necessary to implement or verify the approved change.

## Required review

Review depth is risk-weighted, but material work always requires:

- exact target identity;
- qualification;
- creator-reviewer separation;
- artifact inspection;
- evidence inspection;
- specific findings;
- and explicit disposition.

## Rejection conditions

Reject work when:

- the repository or revision is unknown;
- current behavior was not inspected;
- behavior was invented;
- the loaded specialist lacks qualification;
- the change includes placeholder success;
- the implementation cannot be executed;
- failures or data effects are hidden;
- migration or rollback is missing where required;
- evidence belongs to another revision;
- review is self-attested;
- or an adjacent role is substituting for a missing profession.
