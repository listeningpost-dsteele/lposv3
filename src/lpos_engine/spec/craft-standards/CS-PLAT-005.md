---
id: CS-PLAT-005
title: Observability and Operational Telemetry Standard
version: 1.0.0
status: Accepted
owner: Listening Post
---

<!-- Generated from LPOS expert corpus v1.2, source SHA-256 fcc787db6f8ab0be691f9030af927005a005561db1c0fecdee5f6dbdc87a060f, source lines 44973-45007. Runtime lifecycle is governed separately. -->

# Observability and Operational Telemetry Standard

Every material signal, dashboard, and alert must have:

- audience;
- operational question;
- source and semantics;
- owner;
- freshness and retention;
- sensitive-data controls;
- action or diagnostic path;
- and lifecycle.

Telemetry must be tied to exact service and release revisions where material.

Reject:

- logging all inputs or outputs;
- secrets and unnecessary personal data;
- unbounded cardinality;
- dashboards without decisions;
- alerts without owners and runbooks;
- heartbeats presented as service health;
- and correlation presented as proof of causation.
