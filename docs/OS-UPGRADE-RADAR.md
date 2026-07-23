# OS Upgrade Radar — governed candidate intake

Hermes runs a daily radar that surfaces external skills, libraries, and patterns
that might improve LPOS. This document is where those candidates are recorded and
governed. It exists so the system can *learn about* improvements without any of
them silently becoming part of the OS.

## The rule (from the architect handoff, 2026-07-23)

> Treat these as design inputs, not installed requirements. Promote a lesson into
> OS guidelines only if it has a reusable failure mode, an evidence-backed
> improvement, and a testable acceptance gate.

Nothing on the radar is installed by being listed here. A candidate becomes part
of LPOS only by passing the same bar every shipped change passes: its own build,
adversarial audit, docs, and the release gates — exactly the process that produced
the v4.2.1 remediation and the v4.3.0 Sentinel guild.

## Acceptance gate for any adopted candidate

A radar candidate may be promoted only when all of these exist:

1. **Named source evidence** — where the idea came from.
2. **Frozen artifact or exact file path** — the reviewed input, pinned.
3. **Failure mode it prevents** — the concrete problem it solves.
4. **Test or inspection that proves it works** — a falsifiable acceptance check.
5. **Rollback or containment path** — how to undo it safely.
6. **Explicit boundary** between declared architecture and live runtime behavior.

## Decision rubric

Each candidate is classified as one of: constitutional guideline · Standing
Operation · runtime guard · skill/reference · watch item · reject.

## Current candidates (2026-07-22 / 2026-07-23 radar runs)

All are **design inputs, not approved, not installed.** Treatment is the radar's
recommendation; adoption still requires the acceptance gate above and Principal
approval.

| Candidate | Treatment | Why it matters | Boundary held |
|---|---|---|---|
| EchoMind Memory Engine | prototype | Explicit memory provenance, lifecycle, contradiction, freshness | Read-only eval harness first; no plugin wiring |
| VantaSoft Hermes Library | watch | Governed MCP install + profile-local OAuth patterns | Inspect only; do not install until security review |
| video-to-skill | prototype | Turns videos into auditable skill candidates | Quarantine + hashes + PII redaction + human gate |
| fnord123 local-model skills | build skill | More deterministic skills for the local-model path | Extract into an LPOS skill-quality rubric + fixtures |
| tldraw Hermes skill | watch | Version-aware domain skills; label unverified behavior | Copy the pattern, not the domain |
| Self-Improving Skills distillation | prototype | Detached lesson capture with validation + rollback | Read-only queue to quarantine; no background writes |
| Hermes Skill Git Automation | build script | Skill mutations as reviewed git history + receipts | Local one-shot; remote push disabled |
| Hermes ESRA experiment loop | watch | Value-driven experiment contract vs. random churn | Extract contract only; no autonomous evolution |
| 5dive no-ai-slop writing | build skill | Evidence-based, voice-preserving de-AI pass | Editor checklist aligned to CS-001 |
| App Business Skills (store ops) | security review first | Governed app-store pricing/release-note research | Apply paths disabled until explicit credential approval |

## How this connects to the OS

The radar itself is the reusable pattern worth keeping: a scheduled intake that
dedupes signals, records candidates with evidence, and holds every one behind an
acceptance gate and Principal approval. Two governance ideas above (skill mutations
as reviewed git history; detached distillation to quarantine with no direct write
path to installed skills) directly reinforce the LPOS-030 approval discipline and
the Skill Evolution guild's staging-only rule — they are strong references for a
future release, not code that ships in this one.

To promote a candidate, open it as its own change: build in isolation, audit
adversarially, document, and take it through the release gates. Until then it stays
here — visible, tracked, and uninstalled.
