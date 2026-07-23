---
title: Core concepts
section: welcome
order: 2
---

# Core concepts

You can use LPOS well with a handful of ideas. Everything else in this guide builds on the mental model on this page.

## The Principal

LPOS serves exactly one Principal — you. It has no independent mission. Authority originates with you and flows downward: you delegate to Chip, Chip delegates to specialists, providers satisfy capabilities, and the runtime executes. Consequential authority always remains with you unless you explicitly delegate it, and any such delegation is recorded.

Alongside you, LPOS maintains a **Principal Model**: a portable, inspectable, editable, versioned understanding of who you are — identity, mission, values, priorities, preferences, working style, organizations, relationships, active initiatives, constraints, decision history, and communication preferences. You own this model. Confirmed facts are kept separate from inference, secrets are excluded from it, and previous versions remain recoverable.

## Chip, the executive office

Chip is the fiduciary executive office of LPOS. Its mission is to understand you, coordinate specialists, preserve context, and turn work into clear decisions and completed outcomes. Its duties are loyalty, care, candor, stewardship, delegation, transparency, confidentiality, and advocacy. Chip interprets objectives, routes work, selects specialists, coordinates dependencies, synthesizes outputs, surfaces conflicts, and escalates when authority or confidence is insufficient.

Chip has boundaries: it is not the CEO, strategist, lawyer, engineer, or researcher — those are specialists — and it never overrides you. The name is configurable: whatever office name you confirm during onboarding is used everywhere the system says "Chip."

## Guilds and specialists

A **guild** is a domain charter that groups related specialists and capabilities — Engineering, Research, Communications, Finance, Security, and so on. Guilds define quality and structure for their domain: standards, capabilities, benchmarks, and the specialist charters they govern. Guilds do not replace Chip. No guild is a trust authority: under Constitution Article VIII,
new-guild output starts untrusted, cannot be self-approved or self-remediated, and must
pass the ordinary fresh-context adversarial-review process before it can affect a gate
or be presented as fact. Sentinel (GUILD-039) applies this rule to its own security work.

A **specialist** is a narrow expert role that performs delegated reasoning or work. LPOS v4 ships 33 canonical specialists (see the [specialist index](/reference/specialists.html)). Specialists are compiled roles the model assumes at routing time, not resident agents. When a guild has no dedicated specialist, a documented fallback map assigns the nearest specialist by domain — this is by design, never a stall.

Routing is **capability-first**: a task names the capabilities it requires (say, `software_implementation` and `testing`), and the router selects the smallest specialist set that covers them. Components request capabilities, never vendors; no provider or model name appears anywhere in the architecture.

## Standing Operations

A **Standing Operation** is a recurring responsibility defined by intent rather than by a runtime schedule — for example, SO-001 Executive Brief prepares one decision-focused briefing each scheduled morning. LPOS v4 packages 26 of them (SO-001 through SO-026) as machine-readable workflow definitions with default schedules. Every run uses an idempotency key, writes exactly one run record and one evidence record, and produces an explicit `ok`, `silent`, or `error` result. An operation with nothing worth sending returns `[SILENT]` rather than emailing you noise — and four consecutive silent or near-empty runs trigger a health review rather than continued noise.

## Materiality

Materiality is the switch that decides how much rigor a task gets. A task is **material** when any of these holds: it takes or enables an external or irreversible action; it changes an approved artifact; its output faces a customer or the public; it has legal, financial, security, or privacy impact; it involves strategy, brand, or your taste; it modifies a long-lived specification; or a failure would cost more to undo than the review costs to run.

Material work must have an interpretation contract, an artifact specification, an independent review, baselines, and a rollback path. Routine internal work — status summaries, internal notes, reversible scratch work — skips the material controls. You may designate any task material or non-material yourself; the designation is recorded as a decision. When classification is uncertain, LPOS treats the task as material.

Two related disciplines follow from materiality:

- **The interpretation contract.** Guessing is what happens when interpretation stays implicit. Before material work starts, the system writes down: your instruction verbatim, its interpretation, the invariants (what will *not* change), every conflict it detected and how each was resolved, and a verification plan. A conflict about what you actually want is a blocking question by definition — one option-framed question costs minutes; a wrong guess costs the artifact.
- **The five gates.** Every material artifact must pass Intent, Truth, Reasoning, Craft, and Outcome gates, and the creator context cannot approve its own material work — an independent reviewer, in a fresh context that excludes the creator's conversation and self-assessment, must pass it.

## Evidence

LPOS is built on evidence over claims: important recommendations define expected outcomes and how they will be measured. The **Evidence Engine** carries each recommendation through a lifecycle — hypothesis, expected outcome, implementation, observation, measurement, evaluation, evidence, future decision — and each evidence record carries a baseline, a target, an observed outcome, confidence, and a status (Proposed, Active, Measured, Validated, Refuted, or Inconclusive). Every Standing Operation run appends exactly one evidence record. The Evidence Engine evaluates work, not people.

Significant decisions get a **Decision Record**: what was decided, why, the alternatives, consequences, and risks. Decision records are historical — new decisions supersede old ones rather than rewriting them.

## Approvals and exact actions

Consequential actions require your approval, and approval is exact. A planned action is serialized canonically and hashed with SHA-256; your approval binds to that exact hash, your verified identity, and that action only. Grants expire, cannot be replayed, and are consumed atomically at execution. If the action changes in any way after you approved it, the approval no longer applies. Silence is never consent.

## Related pages

- [What LPOS is](/welcome/index.html)
- [Glossary](/welcome/glossary.html)
- [Specialists](/reference/specialists.html)
- [Everything LPOS includes](/includes/index.html)
- [Reading agent output](/working-with/reading-agent-output.html)
