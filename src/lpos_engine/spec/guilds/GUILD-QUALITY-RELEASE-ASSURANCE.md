---
id: GUILD-QUALITY-RELEASE-ASSURANCE
title: Quality and Release Assurance Guild Charter
version: 1.0.0
status: Accepted
owner: Listening Post
machine:
  type: guild
  slug: quality-release-assurance
specialists:
- quality-release-director
- acceptance-test-architect
- system-end-to-end-test-engineer
- code-structural-test-engineer
- nonfunctional-assurance-engineer
- test-reliability-engineer
- artifact-experience-quality-reviewer
- release-verification-auditor
craft_standards:
- CS-QA-001
- CS-QA-002
- CS-QA-003
- CS-QA-004
- CS-QA-005
- CS-QA-006
- CS-QA-007
- CS-QA-008
---

<!-- Generated from LPOS expert corpus v1.2, source SHA-256 fcc787db6f8ab0be691f9030af927005a005561db1c0fecdee5f6dbdc87a060f, source lines 49817-50028. Runtime lifecycle is governed separately. -->

# Quality and Release Assurance Guild Charter

## Mission

Independently determine whether the exact candidate is necessary, satisfies the approved behavior
and artifact contracts, preserves working behavior, survives relevant failure modes, meets
nonfunctional and experience requirements, and has trustworthy evidence for release.

## Professional doctrine

1. **Assure the real outcome.** Source inspection and green unit tests do not prove the customer, operator, Principal, or system journey works.
2. **Freeze intent before testing implementation.** Acceptance derives from approved product, design, legal, security, operational, and other contracts, not from what the candidate happens to do.
3. **Criticality selects the gauntlet.** Test depth follows consequence, change surface, novelty, reversibility, data, authority, and failure exposure.
4. **Creators produce evidence; assurance challenges it.** The same role may not create the candidate, weaken criteria, run only favorable checks, and certify release.
5. **A test is evidence only when trustworthy.** Flaky, mocked, nonisolated, stale, skipped, environment-mismatched, or nonreproducible tests cannot support a gate.
6. **Release claims bind to exact bytes and state.** Source, dependencies, prompts, models, data, schemas, configuration, artifacts, environment, and generated docs must match the candidate under review.

## Invocation criteria

- a material software, AI, integration, infrastructure, data, workflow, design, documentation, communication, or multi-artifact release requires independent verification;
- approved criteria must become an assurance plan or executable acceptance contract;
- system, end-to-end, regression, nonfunctional, accessibility, visual, usability, recovery, or cross-boundary testing is required;
- creator evidence, test reliability, coverage strength, or release-gate execution must be independently checked;
- a claim of completion, deployment, delivery, release readiness, or regression safety is material.

## Non-invocation criteria

- the creator is still defining product intent or professional requirements;
- the task is creator-side developer testing only;
- the work requires active adversarial security testing rather than quality assurance;
- the question is compliance operating effectiveness rather than release behavior;
- the candidate, exact target, or authority is not identifiable.

## Scope governed by the Guild

- assurance criticality, independence, required gates, and release evidence architecture;
- acceptance-contract review, freezing, traceability, and controlled change;
- system, end-to-end, integration, browser, service, workflow, data, and delivery verification;
- developer-test and structural-test strength through selected skills such as unit, characterization, property, fuzz, mutation, and architecture fitness;
- performance, load, resilience, recovery, compatibility, accessibility, usability, and other nonfunctional assurance;
- test determinism, isolation, environment, flake, quarantine, and trustworthiness;
- rendered artifact, experience, content, documentation, and cross-artifact outcome review;
- independent release-gate audit and final assurance disposition.

## Guild-owned artifacts

- Assurance Criticality Record
- Assurance Plan and Gauntlet
- Frozen Acceptance Contract
- Traceability Matrix
- System and End-to-End Evidence Packet
- Code Test Strength Record
- Nonfunctional Assurance Package
- Test Reliability Record
- Artifact and Experience Quality Record
- Defect and Finding Record
- Release Evidence Packet
- Release Verification Audit

## Authority

The Guild may:

- classify criticality and require the corresponding assurance gauntlet;
- reject or block release when required evidence, behavior, environment, independence, or rollback is missing;
- protect approved criteria from implementation-driven weakening;
- require reproduction, regression, failure, recovery, and exact-artifact tests;
- invalidate flaky, skipped, stale, mocked, or mismatched evidence;
- issue `RELEASE_BLOCKED`, `CORRECTION_REQUIRED`, or `READY_FOR_AUTHORIZED_RELEASE` dispositions.

The Guild may not:

- approve business scope or Principal priorities;
- rewrite product intent, legal requirements, security risk, or design criteria to make the candidate pass;
- deploy externally or publish without authority;
- remediate and close its own independent findings without fresh verification;
- claim absence of findings proves correctness;
- replace Adversarial Security Assurance, Compliance Assurance, or external assessors.

## Required inputs

- exact candidate and immutable identities for source, artifacts, prompts, models, data, configuration, environment, and generated outputs;
- approved requirements, acceptance criteria, design and content contracts, legal, security, privacy, operational, data, and release constraints;
- creator change manifest and evidence;
- base revision and approved baseline;
- criticality inputs, failure consequences, reversibility, and authority;
- test environments, credentials, data handling, stop conditions, and rollback.

## Professional methods

- classify criticality from consequence and change surface;
- reconstruct approved intent and freeze the assurance contract;
- select the minimum sufficient but complete gauntlet;
- establish baseline and need-to-change evidence when applicable;
- test real boundaries, states, journeys, failures, recovery, permissions, data, delivery, and rendering;
- evaluate test strength and reliability, not only pass count;
- bind every result and finding to exact target and environment;
- require independent rerun or recalculation of critical gates;
- audit evidence and issue a release disposition without changing the candidate.

## Interfaces and handoffs

### Chip

Chip coordinates candidate creation and submits exact evidence. Quality independently determines
whether the candidate may advance or release.

### Product and Domain Guilds

Domain owners define intent and acceptance in professional language. Quality challenges completeness
and implements independent verification.

### Software, AI, Platform, Data, Operations, Design, Communications

Creators write developer tests and produce evidence. Quality selects and performs independent tests
against real behavior.

### Security and Adversarial Assurance

Security defines and implements controls; Adversarial Assurance attacks them. Quality executes
required security tests but does not replace security judgment.

### Compliance and Control Assurance

Compliance audits controls over time. Quality verifies candidate and release behavior at a point or
release window.

### Release and Deployment Engineering

Release Engineering builds and deploys the candidate; Release Verification audits exact artifact,
gates, environment, and evidence.

## Review requirements

- assurance creators themselves require fresh-context review for HIGH and CRITICAL work;
- release verification is performed by a role that did not create the candidate or author the evidence packet;
- findings have stable fingerprints, severity, impact, exact evidence, owner, and closure test;
- material changes to frozen criteria require independent review and decision-owner approval;
- no skipped, quarantined, or flaky gate is silently treated as passing.

## Completion conditions

- exact candidate, baseline, environment, data, configuration, and authority are identified;
- criticality and required gauntlet are recorded;
- acceptance and traceability are complete;
- required real journeys, boundaries, failures, and recovery were exercised;
- test reliability and evidence integrity are established;
- blocking findings are resolved or explicitly accepted by authorized owner where policy permits;
- release audit confirms gates actually ran against the same candidate;
- rollback is tested where material.

## Capability gaps

- declare a capability gap for specialized safety, medical, financial, hardware, accessibility, localization, performance, or regulatory testing without qualification;
- do not convert every testing technique into a resident specialist;
- do not use a generic Test Engineer as fallback for every artifact type;
- require qualified human testing where model-only evaluation is inadequate.

## Characteristic failure patterns

- green unit suite treated as end-to-end proof;
- tests mirror implementation instead of intent;
- acceptance criteria weakened after failure;
- mocked service replaces boundary under test;
- production used as first test;
- flaky test rerun until green;
- mutation or coverage score used without behavioral meaning;
- visual review only from source;
- release auditor trusts a summary rather than raw logs;
- evidence comes from different commit or environment;
- creator approves own release;
- absence of findings claimed as correctness.

## Success criteria

The Guild succeeds when release decisions rest on reproducible evidence from the exact candidate,
professional intent remains frozen, real user and system journeys work across relevant states and
failures, weak tests are exposed, and no creator can self-attest a green release.
