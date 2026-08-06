---
id: CS-PLAT-004
title: Reliability, SLO, and Incident Engineering Standard
version: 1.0.0
status: Accepted
owner: Listening Post
---

<!-- Generated from LPOS expert corpus v1.2, source SHA-256 fcc787db6f8ab0be691f9030af927005a005561db1c0fecdee5f6dbdc87a060f, source lines 44938-44972. Runtime lifecycle is governed separately. -->

# Reliability, SLO, and Incident Engineering Standard

Reliability work must begin with a real user or consumer journey and define:

- material success and failure;
- SLIs;
- measurement quality;
- SLOs;
- error-budget response;
- dependencies;
- capacity and saturation;
- graceful degradation;
- recovery;
- ownership;
- and incident escalation.

Do not:

- use component uptime as the user journey;
- choose 100 percent without justified criticality;
- plan from averages alone;
- use retries without limits and idempotency;
- close incidents without residual-risk review;
- or use “human error” as the stopping point of causal analysis.
