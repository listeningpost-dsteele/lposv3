---
name: quality-router
description: Route every material task through the correct craft standards and reviewer.
version: 3.1.0
author: Listening Post
license: MIT
---

# Quality Router

For every material task:

1. Load LPOS-026 and LPOS-027 (they are sections inside `LPOS-CORE.md`).
2. Identify the lead Guild and Specialist via `SPECIALIST-INDEX.md`
   (apply its fallback map when the Guild is unstaffed).
3. Load the craft standards for that Guild from `CRAFT-STANDARD-ROUTING.yaml`
   (file at the distribution root), then the mapped CS-### sections from
   `CRAFT-STANDARDS.md`. Always include `material_artifact_default` (CS-003)
   for production artifacts.
4. Apply the Intent Gate before work starts: audience, objective, constraints,
   and success condition must be explicit.
5. Inspect existing work and preserve approved strengths (capture a baseline).
6. Define verification before execution.
7. Route the draft to an independent reviewer per the kernel's isolation
   mechanism (`skills/independent-reviewer/SKILL.md`).
8. Apply the Truth, Reasoning, Craft, and Outcome gates.
9. Require Principal approval when taste, brand, strategy, or irreversible
   action is material.
10. Record evidence in `lpos-state/evidence-ledger.jsonl`.

Do not allow a specialist charter to substitute for a craft standard.
