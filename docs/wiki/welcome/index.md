---
title: What LPOS is
section: welcome
order: 1
---

# What LPOS is

LPOS is a personal agent operating system. It exists to serve exactly one person — you, the **Principal** — by coordinating AI specialists that research, analyze, draft, and prepare decisions on your behalf, while keeping every consequential decision in your hands.

LPOS v4 ships as a single, integrated distribution: the operating specification, a deterministic control plane, a capability registry of 32 specialists, executable schemas, 21 Standing Operation workflows, adapters, database migrations, tests, an installer, and a command-line interface all arrive together under one version. The packaged specification is loaded by the engine automatically; it is the specification the runtime enforces, not a separate document you have to install or point at.

## The shape of the system

Every piece of work flows the same way:

```text
Principal instruction
        |
        v
Deterministic LPOS control plane
  - materiality and state machines
  - capability and adapter routing
  - context compiler
  - approval and identity guards
  - review isolation
  - transactional store and audit events
  - Standing Operation runner
        |
        +---------------+
        v               v
Model adapters      Action/channel adapters
(probabilistic)     (permissioned side effects)
```

Two planes divide the labor. The **control plane** is deterministic code: it owns permissions, state transitions, materiality classification, exact-action hashes, approval validity, verified identities, idempotency, context boundaries, persistence, and execution. The **intelligence plane** — the models — owns interpretation, research, analysis, drafting, and review judgment. A model can propose an action; it cannot move an action through a forbidden state or execute it without the control plane. A prompt cannot waive a control-plane guard.

## What you actually get

- A fiduciary executive office, named **Chip** by default, that understands you, routes work to specialists, preserves context, and turns work into clear decisions and completed outcomes.
- 32 capability-routable specialists organized under guild charters, from Strategic Planner to Web & Product Designer.
- 21 Standing Operations — recurring responsibilities like the morning Executive Brief, Weekly Review, and Standing Operation Health — each defined as a machine-readable workflow.
- A five-gate quality system: every material artifact must pass the Intent, Truth, Reasoning, Craft, and Outcome gates, and the creator can never be the sole approver of its own material work.
- Exact-action approval: no publish, send, deploy, purchase, or delete happens without your explicit approval, bound cryptographically to the exact action payload.
- Transactional SQLite state with append-only audit events, so everything the system did — and why — stays inspectable.

## What LPOS deliberately does not do

Out of the box, LPOS performs no live external actions. The bundled consequential-action adapter records an approved action without performing it, and the bundled model adapters are deterministic verification components. Live email, publishing, deployment, and purchasing adapters must be explicitly configured, tested, and enabled by a deployment — they are never silently switched on. Until then, your installation is a safe place to learn the system.

## Related pages

- [Core concepts](/welcome/concepts.html)
- [Glossary](/welcome/glossary.html)
- [Requirements](/getting-started/requirements.html)
- [Install LPOS](/getting-started/install.html)
