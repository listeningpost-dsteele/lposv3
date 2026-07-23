---
title: Reading agent output
section: working-with
order: 5
---

# Reading agent output

You have output from an agent — a briefing, an artifact, a completed task — and you want to read it critically: what is fact, what is inference, what did the system actually do, and how would you check. LPOS structures its output so those questions always have answers.

## The output contract

Every piece of specialist work follows the same eight-part contract:

1. **Executive Summary**
2. **Findings**
3. **Assumptions**
4. **Tradeoffs**
5. **Risks**
6. **Recommendation**
7. **Confidence**
8. **Evidence Plan**

Two disciplines back this up. Specialists are required to distinguish facts, inference, and speculation — if a briefing does not make clear which is which, that is a failure condition, not a style choice. And the final output contains the result, not a transcript of deliberation: internal reasoning is used to improve the result, never exposed as narration.

When a decision is needed, the output produces **one clear next action** for you. Standing Operation output with nothing worth sending is exactly `[SILENT]` — silence in your inbox means "nothing needed you," and the run still recorded evidence.

## Communication intents

Every outbound message declares one intent, and the intent determines how it reaches you: **Executive Decision**, **Operational Alert**, **Evidence**, **Status**, **Collaboration**, or **Conversation**. The intent-to-channel mapping is set in your deployment configuration during onboarding. Interruptions are reserved for emergencies. Every communication should answer: why was this sent, what happened, why it matters, and what should happen next — if a message does not, it is below the system's own standard.

## Reading a task's full record

For anything beyond the summary, the database has the whole story:

```bash
lpos inspect --db state/lpos.db --task-id TASK-...
```

The output contains, in order:

- **The task envelope** — the instruction, required capabilities, materiality, current status, and version.
- **The artifact** — the immutable output, with its SHA-256 content hash and its bindings to the interpretation contract and artifact specification that governed it.
- **The actions** — every planned action with its exact parameters, status, and result. For consequential actions you will see the approval linkage; in a fresh install the result records the action rather than performing it (record-only mode).
- **The completion report** — the final result, its artifact and review bindings, evidence, decisions, limitations, and completion time. Honesty is enforced here too: for example, if the runtime could not isolate the review context, the report must say "independent review not isolated" rather than claiming a clean review.
- **The events** — the append-only audit stream for the task.

## Reading evidence records

Evidence records are how the system proves (or disproves) that work created value. Each one records: the expected outcome, the baseline, the target, the observed outcome, confidence, the measurement method, and a status — Proposed, Active, Measured, Validated, Refuted, or Inconclusive. Every Standing Operation run appends exactly one.

To pull the raw streams:

```bash
lpos events --db state/lpos.db --stream-type <type> --stream-id <id>
lpos export --db state/lpos.db --output events.jsonl
```

`export` writes every immutable event, one JSON object per line, in sequence order — suitable for review, backup, and evidence bundles.

## Giving feedback and corrections

When an agent got it wrong, tell it what you wanted — through the trusted session, or through any verified channel once SO-021 (the Principal Feedback Loop) is active. Two things happen with your correction:

- **A correction is a spec event.** Your correction means the artifact's specification was wrong or silent. The system updates the spec first, then applies the smallest diff that satisfies the correction and compares against the invariants. Regenerating from scratch, or drifting while correcting, fails review.
- **Unmatched feedback becomes a task.** Verified feedback that does not answer an open question is routed as a normal LPOS task through the quality router.

And when the system asks *you* something — a blocking question or an exact-action approval — remember the rules it operates under: it asks only when genuinely blocked, it batches non-urgent questions, it sends at most one reminder, and no reply means **hold**, never consent.

## Related pages

- [Core concepts](/welcome/concepts.html)
- [Glossary](/welcome/glossary.html)
- [Finding your files](/working-with/finding-files.html)
- [CLI reference](/administration/cli-reference.html)
