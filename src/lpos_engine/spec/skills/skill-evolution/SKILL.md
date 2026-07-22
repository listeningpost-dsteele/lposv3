---
name: skill-evolution
description: Improve an LPOS skill from evidence using a validation gate. Propose bounded edits from repeated failures, accept only edits that beat a held-out score, stage for review, never auto-adopt production skills.
version: 1.0.0
author: Listening Post
license: MIT
---

# Skill Evolution

LPOS improves its own skills from evidence, not from taste. Use this when a skill
has recurring, scorable failures and you want a disciplined improvement instead of
a hand-guess.

## The loop

1. Assemble a reviewed task file for the target skill: past cases with, for each,
   the input and the correct outcome. Never harvest raw transcripts into this file
   without redacting secrets and credential paths first.
2. Split tasks into train, validation, and test by stable id hash. A task lands in
   exactly one split. If any task leaks across splits, stop: the gate is invalid.
3. Propose edits from the TRAIN split only, and only for failures that repeat
   across more than one task. One complaint is not evidence.
4. Gate every candidate on the held-out validation split. Accept only if it beats
   the current score by the configured margin. A tie is a rejection. This gate is
   the point: it rejects plausible edits that do not actually help.
5. Report the honest number: the score on the untouched TEST split, before and
   after.
6. Stage the accepted proposal. Do not write a live skill. Route the staged
   proposal through the independent reviewer, and require Principal approval for
   any material skill change (LPOS-030). Adopt through the normal skill mechanism
   with a rollback path, and record the before and after score in the evidence
   ledger.

## Rules

- Auto-adopt is off for production skills. Always.
- The scorer defines the target. A wrong metric optimizes toward wrong behavior,
  so start on a domain whose metric is unambiguous (style compliance, routing
  correctness, schema validity) before anything with taste in it.
- Bound the edit budget and demand a minimum gain, so the skill does not accrue
  conflicting instructions from noise-sized wins.
- The engine that runs this loop is `lpos_engine.evolution`; the operating
  system's own 53 benchmark fixtures are loadable as tasks via
  `evolution.lpos_tasks.load_lpos_tasks`.

## What this does not do

Passing a benchmark is not the same as an outcome verified in the real world. The
gate raises the floor on skill quality; it does not replace Principal judgment on
taste, brand, or strategy.
