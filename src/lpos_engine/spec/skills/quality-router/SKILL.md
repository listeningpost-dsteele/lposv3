---
name: quality-router
description: Route every material task through the correct craft standards and reviewer.
version: 4.0.0
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
5. Write the interpretation contract (LPOS-029): instruction verbatim,
   interpretation, invariants, every conflict between instruction, spec, and
   existing patterns (each asked as a blocking question or resolved by
   precedence with the resolution flagged), and the verification plan. Load or
   seed the artifact's spec from the versioned ArtifactSpecification store before executing.
6. Inspect existing work and preserve approved strengths (capture a baseline).
7. Define verification before execution. For corrections: update the spec
   first, then apply the smallest diff that satisfies the correction.
8. Route the full review envelope (LPOS-029: brief, baseline, artifact,
   interpretation contract, artifact specification, mapped craft standards,
   verification evidence, intended outcome) to an independent reviewer per the
   kernel's isolation mechanism (`skills/independent-reviewer/SKILL.md`).
9. Apply the Truth, Reasoning, Craft, and Outcome gates.
10. Require Principal approval when taste, brand, strategy, or irreversible
    action is material.
11. Record evidence in a validated EvidenceRecord in transactional state.

Do not allow a specialist charter to substitute for a craft standard.
## Customer-facing and Principal-facing prose

For any task producing customer-facing or Principal-facing prose, the routed team always includes Editor (SPECIALIST-021) for the mandatory CS-001 de-AI pass. The interpretation contract must name the voice spec in use, usually the `voice:<brand>` ArtifactSpecification. If no voice spec exists, seed one before drafting. The run record must state that the Editor pass was completed.
