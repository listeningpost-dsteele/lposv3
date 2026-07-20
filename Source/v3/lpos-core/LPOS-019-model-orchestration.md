---
id: LPOS-019
title: Model Orchestration
version: 1.0.0
status: Accepted
classification: Core Architecture
owner: Listening Post
---

# Model Orchestration

Models are providers. Components request capabilities, not model names.

The runtime routes requests using capability, context size, latency, cost, locality,
privacy, availability, health, benchmarks, and confidence.

Fallbacks preserve capability when providers fail.

