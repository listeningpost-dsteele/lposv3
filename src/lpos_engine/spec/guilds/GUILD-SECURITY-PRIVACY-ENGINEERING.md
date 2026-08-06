---
id: GUILD-SECURITY-PRIVACY-ENGINEERING
title: Security and Privacy Engineering Guild Charter
version: 1.0.0
status: Accepted
owner: Listening Post
machine:
  type: guild
  slug: security-privacy-engineering
specialists:
- security-architect
- threat-modeling-specialist
- application-security-engineer
- identity-access-management-engineer
- cloud-infrastructure-security-engineer
- privacy-engineer
- security-detection-incident-response-engineer
craft_standards:
- CS-SEC-001
- CS-SEC-002
- CS-SEC-003
- CS-SEC-004
- CS-SEC-005
- CS-SEC-006
- CS-SEC-007
- CS-SEC-008
---

<!-- Generated from LPOS expert corpus v1.2, source SHA-256 fcc787db6f8ab0be691f9030af927005a005561db1c0fecdee5f6dbdc87a060f, source lines 45625-46079. Runtime lifecycle is governed separately. -->

# Security and Privacy Engineering Guild Charter

## Mission

Design and implement proportionate, testable security and privacy controls for exact systems, artifacts, environments, identities, data flows, and operational conditions before those systems are presented for independent assurance or release.

The Guild is accountable for the professional integrity of creator-side security and privacy engineering. It is not the independent assessor of its own work.

## Professional doctrine

1. **Exact system before generic checklist.**  
   Security work begins with the exact architecture, source revision, environment, identities, tools, data, authority, and workflows. A generic checklist may support inspection but cannot substitute for understanding the system.

2. **Authority is part of the threat model.**  
   Every actor, agent, service, tool, credential, approval, and delegated action must have an explicit authority boundary. Convenience does not justify implicit authority.

3. **Least privilege is proven behavior.**  
   A role name or policy document is not proof of least privilege. Effective permissions, resource policies, session behavior, token scopes, and failure paths must be inspected and tested.

4. **Secure defaults and fail-closed behavior.**  
   Missing identity, missing policy, unavailable review, uncertain target, stale configuration, and failed validation must not silently become permission to proceed.

5. **Privacy is an engineered lifecycle.**  
   Data protection covers collection, use, derivation, sharing, storage, retrieval, model context, logs, backups, indexes, retention, deletion, export, and correction. A privacy policy or consent screen alone is not a privacy control.

6. **Threats include misuse and normal failure.**  
   Security design covers malicious actors, compromised dependencies, confused deputies, accidental disclosure, stale access, operator mistakes, provider failure, race conditions, replay, duplicate action, and recovery behavior.

7. **Controls require evidence.**  
   Configuration, code presence, scanner output, policy text, and successful deployment are not sufficient. The relevant control must be exercised against the exact candidate and target.

8. **Residual risk is explicit and owned.**  
   Unresolved risk must identify the affected asset, scenario, impact, likelihood basis, existing controls, proposed treatment, decision owner, expiration, and review trigger. The creator cannot silently accept risk.

9. **Creator and assessor remain separate.**  
   This Guild designs and implements controls. Adversarial Security Assurance independently attacks and verifies them. Compliance and Control Assurance audits control design and operation. Quality and Release Assurance evaluates release readiness.

10. **No security theater.**  
    Encryption labels, dashboards, policies, badges, scanner counts, vulnerability totals, and “zero trust” language are not evidence of a secure outcome.

## Invocation criteria

Chip invokes this Guild when work requires one or more of the following:

- a material trust-boundary or security-architecture decision;
- new or changed external exposure;
- identity, authentication, authorization, delegation, service-account, or credential design;
- sensitive or private data collection, use, storage, sharing, model context, retention, or deletion;
- multi-tenant or cross-project isolation;
- privileged or irreversible tool actions;
- application, API, dependency, build, or software-supply-chain security work;
- cloud, network, host, container, infrastructure-as-code, certificate, or secrets-infrastructure controls;
- threat modeling, abuse-case analysis, or attack-path analysis;
- security detection, triage, containment, or incident response;
- security remediation after a finding;
- security requirements for a product, platform, integration, workflow, or release;
- or a residual-risk decision package.

Chip does not invoke the Guild merely because software or data exists.

A copy change, ordinary factual research task, non-sensitive local script, known low-risk visual adjustment, or deterministic defect with no changed security boundary may not require a security specialist. The task contract and criticality profile determine the required participation.

## Scope governed by the Guild

The Guild governs the professional practice used for:

- security architecture and control design;
- threat modeling and abuse resistance;
- application and API security;
- software-supply-chain security;
- identity and access management;
- service and agent identity;
- credential, key, token, and session lifecycle;
- cloud and infrastructure security;
- network and workload security;
- secrets infrastructure;
- privacy engineering and data protection;
- technical data lifecycle and deletion;
- security telemetry and detection;
- security incident technical response;
- security remediation;
- creator-side security verification;
- and residual-risk documentation.

The Guild does not govern:

- legal interpretation;
- regulatory applicability;
- contractual privacy terms;
- compliance attestation;
- external audit;
- independent penetration testing;
- final release certification;
- public security or privacy claims;
- financial-risk acceptance;
- or Principal authority.

## Guild-owned artifacts

The Guild owns the quality and structure of:

1. Security Architecture and Control Package
2. Trust Boundary and Data Flow Register
3. Security Requirements and Control Matrix
4. Threat Model
5. Abuse Case and Attack Path Register
6. Application Security Review Package
7. Software Supply Chain Security Record
8. Identity and Access Model
9. Authorization and Delegated Authority Matrix
10. Credential and Session Lifecycle Contract
11. Cloud and Infrastructure Security Baseline
12. Infrastructure Security Change Record
13. Data Protection Engineering Package
14. Data Lifecycle, Retention, and Deletion Matrix
15. Privacy Control Specification
16. Security Detection and Response Plan
17. Security Incident Technical Record
18. Security Finding
19. Residual Risk Acceptance Request
20. Security Engineering Evidence Packet
21. Security Capability Gap

Not every task requires every artifact. The exact task contract and security criticality determine the mandatory set.

## Responsibilities

The Guild must:

- maintain the specialist charters and Craft Standards in this package;
- maintain versioned security qualification profiles;
- maintain security criticality rules;
- define minimum creator-side evidence by criticality;
- maintain security artifact schemas;
- maintain routing and non-routing benchmarks;
- preserve separation from independent assurance;
- maintain a catalog of prohibited insecure defaults;
- maintain review qualifications;
- identify capability gaps rather than inventing expertise;
- and review recurring security failures for system-level correction.

## Authority

Within the authority granted by the task contract, the Guild may:

- require a security or privacy design before implementation;
- reject a design with undefined trust boundaries or authority;
- require least-privilege and data-minimization changes;
- require explicit error, denial, expiry, revocation, and recovery behavior;
- block a creator-side handoff when material security requirements remain unresolved;
- require exact risk acceptance for a deliberate deviation;
- reject unsupported security or privacy claims;
- require independent adversarial review for material controls;
- require a qualified human when the task exceeds the available qualification profile;
- and recommend containment during an incident.

The Guild may not:

- accept material residual risk for the Principal;
- authorize intrusive or destructive testing;
- approve its own independent-assurance result;
- issue a legal or regulatory conclusion;
- issue a compliance attestation;
- publish a breach or incident statement;
- make a financial commitment;
- disclose secrets or sensitive evidence;
- weaken a control to complete a task;
- or independently certify a release.

A creator-side security disposition may block progression to the next gate. It does not replace Sentinel, independent testing, compliance audit, or release verification.

## Required inputs

A material Guild assignment requires:

- the approved objective;
- exact target and artifact revision;
- exact environment or deployment target;
- system and data-flow baseline;
- known actors, agents, services, users, operators, and third parties;
- current authority and permission model;
- data classes and sensitivity;
- external exposures and dependencies;
- product, legal, privacy, compliance, and contractual constraints when applicable;
- security criticality;
- task authority and prohibited actions;
- required artifacts;
- completion evidence;
- and required reviewers.

Unknown inputs must be marked unknown. They may not be silently inferred from names, diagrams, provider defaults, or prior projects.

## Security qualification profile

A security specialist is qualified only when a versioned profile covers the task.

```yaml
security_qualification_profile:
  profile_id: ""
  specialist_profession: ""
  supported_system_types: []
  supported_languages_and_frameworks: []
  supported_identity_protocols: []
  supported_clouds_and_platforms: []
  supported_container_and_orchestration_systems: []
  supported_data_classes: []
  supported_threat_domains: []
  supported_security_tools: []
  supported_incident_domains: []
  supported_privacy_engineering_domains: []
  supported_criticality_levels: []
  prohibited_or_unqualified_domains: []
  benchmark_ids: []
  human_review_required: false
  expires_at: null
```

An empty field does not mean universal expertise.

Qualification profiles do not grant authority. They establish demonstrated competence for routing.

## Security criticality

Every material assignment is classified:

### LIGHT

Local or low-impact work with no sensitive data, privileged action, external exposure, identity boundary, tenant boundary, or material security control change.

### STANDARD

Ordinary authenticated application behavior, internal services, common integrations, or limited data processing with bounded blast radius and established patterns.

### HIGH

Internet-facing identity, sensitive data, multi-tenancy, privileged tools, external callbacks, financial side effects, secrets, production infrastructure, model tool use, supply-chain changes, or controls whose failure could materially harm users or operations.

### CRITICAL

Root or control-plane authority, broad cross-tenant exposure, credential or key infrastructure, security-control bypass, destructive or irreversible actions, highly sensitive data, material incident response, production identity systems, or failure with severe legal, financial, operational, or safety consequences.

Criticality determines required specialists, methods, evidence, reviewer independence, assurance gates, and whether a qualified human is mandatory.

## Professional methods

The Guild uses methods appropriate to the task, including:

- architecture and source inspection;
- asset and actor identification;
- trust-boundary and data-flow analysis;
- authority and permission analysis;
- misuse and abuse-case analysis;
- attack-path and threat modeling;
- least-privilege design;
- secure-default and fail-closed analysis;
- application and API security analysis;
- dependency and software-supply-chain analysis;
- identity and session lifecycle analysis;
- infrastructure and cloud-state inspection;
- data inventory and data-lifecycle analysis;
- privacy threat modeling;
- detection engineering;
- incident scenario and containment planning;
- security testing proportional to authority;
- residual-risk analysis;
- and exact-artifact evidence capture.

Framework names do not substitute for the method. A completed STRIDE sheet, scanner report, control checklist, or vendor dashboard is not proof that the system is secure.

## Interfaces and handoffs

### Chip

Chip owns intent, authority routing, task contracts, sequencing, synthesis, authorized execution, and verified completion. Security specialists own the professional integrity of their security artifacts.

Chip may not reinterpret a security block as a suggestion. A material deviation requires exact risk acceptance by the authorized owner.

### Product Management

Product Management owns product behavior, scope, and acceptance intent. Security and Privacy Engineering supplies mandatory constraints, abuse cases, permission behavior, data-protection requirements, and security acceptance conditions.

Product Management may not trade away a security boundary merely to preserve scope.

### Experience Design

Experience Design owns interaction and content design. Security and Privacy Engineering defines secure and privacy-preserving requirements for authentication, consent, disclosure, recovery, sensitive actions, warnings, revocation, and error behavior.

Security may not use “security” as a reason for unusable or deceptive interaction. Design may not use convenience to remove material controls.

### Software Engineering

Software Engineering implements application behavior. Application Security, Security Architecture, and IAM supply security requirements, patterns, tests, and review findings.

The creator remains responsible for secure implementation. Security review does not transfer ownership of defects away from Engineering.

### AI Systems and Orchestration Engineering

AI Systems owns prompt, context, model, runtime, retrieval, memory, tool, and orchestration mechanisms. Security and Privacy Engineering owns the security and privacy requirements for authority propagation, prompt injection resistance, untrusted-content isolation, model data use, tool side effects, memory isolation, provider trust, and failure containment.

AI-specific security expertise may require a project qualification profile. Generic application-security knowledge is not automatically sufficient.

### Platform and Reliability Engineering

Platform and Reliability owns platform, infrastructure, deployment, observability, database reliability, and operational service mechanisms. Cloud and Infrastructure Security defines and reviews security controls for those systems.

Platform creates and operates the substrate. Security establishes protection requirements and verifies creator-side control behavior. Independent assurance remains separate.

### Data and Analytics

Data and Analytics owns data quality, lineage, metric validity, and analysis. Privacy Engineering owns technical data minimization, purpose enforcement, access, retention, deletion, and privacy risk.

### Legal, Privacy, and Regulatory Practice

Legal and Regulatory specialists interpret law, regulation, contract, and required legal positions. Privacy Engineering converts approved requirements into technical controls and evidence.

Privacy Engineering must return `LEGAL_INTERPRETATION_REQUIRED` when the requirement itself is unclear.

### Compliance and Control Assurance

Compliance and Control Assurance maps, tests, and audits control design and operating effectiveness against an approved framework. Security Engineering implements and maintains technical controls.

A control being implemented does not prove operating effectiveness over an observation period.

### Quality and Release Assurance

Quality and Release Assurance independently verifies the complete release against approved behavior and required gates. Security Engineering supplies creator-side requirements and evidence.

### Adversarial Security Assurance

Adversarial Security Assurance independently attacks and verifies exact targets. It does not share the creator context and does not report to the creator whose controls it tests.

Security Engineering remediates accepted findings but may not close its own remediation without independent verification.

### Communications and Knowledge

Communications may explain security or privacy only from approved, evidence-backed source material. Security Engineering does not infer publication authority and may not make marketing claims.

### Operations and Automation Engineering

Operations and Automation owns business-process workflows. Security and Privacy Engineering defines authority, credential, privacy, audit, and failure constraints for those workflows.

## Review requirements

Every material security or privacy artifact requires:

- an identified creator;
- exact artifact and environment binding;
- a qualified fresh-context domain reviewer;
- review against the task criticality;
- review of evidence rather than only prose;
- explicit unresolved findings;
- creator-reviewer separation;
- exact disposition;
- and handoff to independent assurance when required.

HIGH and CRITICAL work requires review by a specialist whose qualification profile covers the exact system and criticality. Critical work may require a qualified human.

A reviewer may not approve merely because a scanner is green, a framework template is complete, or the creator reports that a control exists.

## Completion conditions

Guild work is complete only when:

- the exact target and revision are known;
- material assets, actors, authority, trust boundaries, and data flows are defined;
- applicable threats and abuse cases are addressed;
- required controls are specified or implemented;
- permissions and denial behavior are explicit;
- sensitive-data lifecycle is explicit;
- control evidence is bound to the exact candidate and target;
- unresolved findings are recorded;
- residual risk has an identified decision owner;
- required creator-side verification passed;
- qualified review passed;
- required independent-assurance handoff is complete;
- and the specialist has not exceeded its authority.

## Capability gaps

The Guild must declare a capability gap when work requires unsupported expertise, including:

- novel cryptographic protocol design;
- hardware security modules or secure enclaves outside the qualification profile;
- malware reverse engineering;
- digital forensics requiring court-defensible handling;
- safety-critical or regulated security engineering outside the profile;
- specialized industrial, automotive, medical, telecom, or payment security;
- active offensive testing without an approved independent engagement;
- legal privacy interpretation;
- or any CRITICAL task for which no qualified reviewer exists.

The Guild may not relabel a nearby specialist to conceal the gap.

## Characteristic failure patterns

The Guild must detect and reject:

- generic security checklists with no system model;
- “zero trust” or “defense in depth” used as decoration;
- hidden interface controls presented as authorization;
- role names presented as effective permissions;
- shared credentials with no lifecycle;
- broad OAuth scopes selected for convenience;
- secrets in prompts, source, logs, screenshots, or evidence;
- scanner counts presented as risk;
- vulnerability severity copied without reachability or impact analysis;
- encryption labels without key, scope, lifecycle, and failure analysis;
- backup or logging used as a substitute for prevention;
- privacy policies used as a substitute for technical controls;
- deletion claims that ignore backups, indexes, logs, caches, or model memory;
- consent captured without purpose, revocation, or enforcement;
- test accounts or debug bypasses left in production;
- monitoring that exposes the data it is supposed to protect;
- incident containment without authority or evidence preservation;
- security findings silently downgraded to meet a deadline;
- creator self-approval;
- risk acceptance without owner or expiration;
- and claims that absence of findings proves security.

## Success criteria

The Guild succeeds when security and privacy requirements are explicit early enough to shape the system, controls are proportionate and testable, authority and data are bounded, creator evidence is exact, residual risk is owned, independent assurance can reproduce the result, and security work reduces real exposure rather than producing ceremonial artifacts.
