---
title: Glossary
section: welcome
order: 3
---

# Glossary

Terms you will meet throughout LPOS and this guide. The first twelve are the canonical definitions from the LPOS glossary (LPOS-004); the rest are runtime terms used across the system.

**Principal**, The single human served by LPOS. That is you.

**Chip**, The fiduciary executive office that knows the Principal, routes work, preserves context, and synthesizes results. The name is configurable during onboarding; "Chip" is the default.

**Guild**, A domain charter that groups related specialists and capabilities.

**Specialist**, A narrow expert role that performs delegated reasoning or work.

**Capability**, A durable provider-independent function. Architecture requests capabilities; providers satisfy them.

**Provider**, An implementation of one or more capabilities (a model, a service, an integration).

**Runtime**, The execution environment that schedules and runs LPOS. Hermes is one runtime, not the architecture.

**Standing Operation**, A recurring responsibility defined by intent rather than runtime schedule. LPOS v4 packages SO-001 through SO-021.

**Evidence**, Observable information showing whether intended value was created.

**Decision Record**, A traceable record of what was decided and why.

**Principal Model**, The portable, versioned representation of the Principal.

**Communication Intent**, The purpose of a communication independent of channel: Executive Decision, Operational Alert, Evidence, Status, Collaboration, or Conversation.

---

**Materiality**, The classification that decides whether a task requires the interpretation contract, independent review, blocking questions, baselines, and a rollback path. When in doubt, a task is treated as material.

**Interpretation contract**, The record written before material work starts: the instruction verbatim, the interpretation, invariants, detected conflicts and their resolutions, and a verification plan.

**Artifact**, An immutable, hashed output version produced by a task. Artifacts bind to their contract, specification, and creation context.

**ArtifactSpecification**, The versioned record of a long-lived artifact's structural decisions, design tokens, and approved invariants. The artifact is never its own spec.

**Five gates**, The quality gates every material artifact must pass: Intent, Truth, Reasoning, Craft, and Outcome.

**Independent review**, Review of material work in a fresh, isolated context that receives exactly the review envelope and never the creation conversation, the creator's private reasoning, or the creator's self-assessment.

**Review envelope**, The only permitted review input: brief, baseline, artifact, interpretation contract, artifact specification, mapped craft standards, verification evidence, and intended outcome.

**Craft standard (CS-###)**, A domain excellence standard (for example CS-007 Software Engineering) that a specialist must load for its domain. A specialist charter defines responsibility; a craft standard defines excellence; a reviewer validates the artifact, none substitutes for another.

**TaskEnvelope**, The typed object that carries a task: identity, routing, materiality, and constraints.

**ActionPlan / exact action**, A consequential action, planned and canonically hashed (SHA-256) before it may be applied.

**ApprovalRequest / ApprovalGrant**, The question put to the Principal about an exact action, and the verified, expiring, single-use grant bound to that exact action hash.

**MessageIdentity**, The provider-neutral identity of an inbound message: channel, provider, message ID, thread ID, and sender. Used to verify that an answer really came from the Principal and to reject replays.

**EvidenceRecord**, The validated record of an expected outcome, baseline, target, observation, confidence, measurement method, and status.

**StandingOperationRun**, The idempotent record of one Standing Operation execution, with its explicit `ok`, `silent`, or `error` result.

**CompletionReport**, The canonical final report of a task, committed atomically with its completion evidence.

**Model class**, The routing tier a task's model adapter must serve: `executive`, `routine`, `review`, or `local`.

**Chip kernel**, The small, always-loaded core of the packaged specification; all other components (specialist charters, craft standards, operation definitions) are retrieved on demand.

**Evidence Ledger / Decision Ledger**, The persistent, queryable stores of evidence records and decision records inside the transactional state database.

**Record-only mode**, The default for consequential actions in a fresh install: an approved action is recorded but not performed, because no live external adapter has been configured and tested.

## Related pages

- [Core concepts](/welcome/concepts.html)
- [What LPOS is](/welcome/index.html)
- [Reading agent output](/working-with/reading-agent-output.html)
