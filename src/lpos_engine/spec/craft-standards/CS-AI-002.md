---
id: CS-AI-002
title: Agent Architecture and Control-Plane Standard
version: 1.0.0
status: Accepted
owner: Listening Post
---

<!-- Generated from LPOS expert corpus v1.2, source SHA-256 fcc787db6f8ab0be691f9030af927005a005561db1c0fecdee5f6dbdc87a060f, source lines 41298-41332. Runtime lifecycle is governed separately. -->

A material agent architecture must define:

- accountable outcome owner;
- agent roles and professional charters;
- control, data, evidence, and approval planes;
- authority propagation and reduction;
- context and trust boundaries;
- task, artifact, and state ownership;
- delegation depth, budgets, and stop conditions;
- human checkpoints;
- failure containment and blast radius;
- tool and side-effect boundaries;
- runtime, platform, security, and privacy dependencies;
- migration, rollback, and evaluation.

Reject:

- multi-agent design without a reason for separation;
- overlapping or unowned responsibilities;
- creator-reviewer collapse;
- authority escalation through delegation;
- unbounded recursion;
- hidden deterministic policy inside prompts;
- architecture that cannot explain recovery from partial failure.
