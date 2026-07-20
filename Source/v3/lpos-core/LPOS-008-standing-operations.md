---
id: LPOS-008
title: Standing Operations
version: 1.0.0
status: Accepted
classification: Core Architecture
owner: Listening Post
---

# Standing Operations

Standing Operations define recurring responsibilities. Runtimes implement scheduling.

Each operation defines:

- Identity
- Mission
- Objective
- Trigger type
- Inputs
- Outputs
- Specialists
- Required capabilities
- Success criteria
- Failure conditions
- Evidence produced
- Communication intent
- Owner
- Version

Standing Operations never depend on cron, Hermes, Kubernetes, or another scheduler.

