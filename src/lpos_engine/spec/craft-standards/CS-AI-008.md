---
id: CS-AI-008
title: AI Behavior Evaluation Standard
version: 1.0.0
status: Accepted
owner: Listening Post
---

<!-- Generated from LPOS expert corpus v1.2, source SHA-256 fcc787db6f8ab0be691f9030af927005a005561db1c0fecdee5f6dbdc87a060f, source lines 41505-41535. Runtime lifecycle is governed separately. -->

Every material AI-system change requires an evaluation claim, behavior contract, exact candidate manifest, representative suite, boundary cases, negative routing, adversarial cases, regressions, raw results, variance, qualified review, and explicit limitations.

Compare:

- prior accepted behavior;
- candidate behavior;
- generic baseline;
- relevant model or provider routes.

Do not:

- change the expected behavior after seeing failures;
- hide critical failures in aggregate scores;
- use one trial for probabilistic behavior;
- let the creator grade and approve its own work;
- test with context unavailable in production;
- treat evaluator-model preference as domain truth;
- claim a passed suite proves universal correctness.
