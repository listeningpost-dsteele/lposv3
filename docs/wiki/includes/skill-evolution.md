---
title: Skill Evolution
section: includes
order: 4
---

# Skill Evolution

Skill Evolution is how LPOS improves its own skills from evidence instead of taste. When a skill has recurring, scorable failures, this capability proposes small, bounded edits, tests each candidate against a held-out validation set, and accepts only edits that measurably beat the current skill. Accepted proposals are staged for your review — a production skill is never changed automatically.

The engine lives in the package as `lpos_engine.evolution`, and the user-facing procedure ships as the `skill-evolution` skill under `spec/skills/skill-evolution` alongside `quality-router`, `independent-reviewer`, and `system-auditor`, so every installer of the 4.1.0 update receives it.

## Why it is safe

Three guarantees are built in, by construction rather than by policy:

- **Offline.** The shipped capability makes no model calls and no network calls, and it works from a *reviewed task file* — past cases with known correct outcomes — never from raw transcript harvesting. Nothing sensitive leaves your machine.
- **Staging-only.** The adoption module cannot write a live skill: it writes every accepted proposal (a rendered skill document plus a JSON report) under a staging directory, and it refuses outright any destination path that looks live or production (including anything under `.hermes` or the LPOS state directories).
- **Gated and governed.** A candidate must *beat* the current skill's score on the held-out validation split — a tie is a rejection; an edit must earn its place. A configurable minimum gain stops noise-sized wins from accumulating as instruction bloat. Adoption of a staged proposal then goes through the normal LPOS governance: independent review, and Principal approval for any material skill change, with the before-and-after score recorded in the evidence ledger.

## The loop

1. **Assemble a reviewed task file** for the target skill: past cases, each with the input and the correct outcome. Secrets and credential paths are redacted before anything enters this file.
2. **Split tasks into train, validation, and test** by a stable hash of each task's id, so a task lands in exactly one split and re-runs are deterministic. If any task leaks across splits, the run stops — a gate scored on a leaking split is meaningless.
3. **Propose edits from the train split only**, and only for failures that repeat across more than one task. One complaint is not evidence. The edit budget is bounded so change stays legible.
4. **Gate every candidate on the held-out validation split.** Accept only if it beats the current score by the configured margin. This is the point of the whole system: it rejects plausible-sounding edits that do not actually help.
5. **Report the honest number**: the score on the untouched test split, before and after.
6. **Stage the accepted proposal** and route it through the independent reviewer and, for material changes, Principal approval. Adoption uses the normal skill mechanism with a rollback path.

## What it scores

The working example scores CS-001 commercial-copy compliance deterministically — a domain whose metric is unambiguous, so accept/reject behavior is fully reproducible and auditable. Beyond that, the operating system's own 53 benchmark fixtures (one per specialist, one per Standing Operation) load as evolution tasks via `lpos_engine.evolution.lpos_tasks.load_lpos_tasks`, so skills are measured against the same fixtures the OS already ships.

## Provenance

Skill Evolution is derived from the ideas in Microsoft SkillOpt (MIT license) — the validation gate, the offline improvement loop, the bounded-edit discipline, and the train/validation/held-out split — reimplemented independently for LPOS, with the privacy boundary made a hard default and adoption tied to LPOS governance. Nothing in the runtime imports SkillOpt's code, and its transcript harvesters were deliberately not adopted. The full lineage is recorded in `NOTICE-SKILLOPT.md` at the repository root.

## What it does not do

Passing a benchmark is not the same as an outcome verified in the real world. The gate raises the floor on skill quality; it does not replace your judgment on taste, brand, or strategy.

## Related pages

- [Packaged skills](/reference/skills.html)
- [Core concepts](/welcome/concepts.html)
- [Reading agent output](/working-with/reading-agent-output.html)
- [Patch notes: 4.1.0](/patch-notes/4-1-0.html)
