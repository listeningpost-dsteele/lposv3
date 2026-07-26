---
name: design-anti-slop-reviewer
description: Detect and remove generic AI-generated visual patterns from websites, product interfaces, images, decks, and other designed artifacts while preserving brand and task fidelity.
version: 1.1.0
---

# Design anti-slop reviewer

## Purpose

Apply the same rigor used by the LPOS Editor anti-slop pass to visual design. The goal is not to guess whether AI made an artifact. The goal is to find specific, observable design failures, remove generic model defaults, and preserve a coherent human-directed visual system.

This skill does not replace accessibility testing, product requirements, brand standards, browser testing, factual review, or independent release review.

## Modes

### Detect

Name each pattern, point to the exact component or region, explain the user cost, and recommend the smallest useful correction. Do not redesign unless requested.

### Repair

Make the minimum coherent set of changes. Preserve the approved information architecture, brand palette, typography, interaction model, and strongest distinctive decisions.

## Deterministic blockers

A material design artifact fails when any blocker remains:

- Horizontal overflow at an approved viewport
- Clipped, hidden, overlapping, or unreachable required content
- Text or controls below WCAG AA contrast for the intended size
- Missing keyboard focus indication on an interactive control
- Images without meaningful alternative text when the image conveys information
- Controls without accessible names
- Broken states, placeholder copy, lorem ipsum, or fabricated customer proof presented as real
- A claimed interaction that is not implemented
- Unsupported metrics, badges, ratings, or social proof
- Multiple conflicting palettes or type systems without an explicit product reason
- Mobile behavior that merely shrinks desktop instead of preserving task order and usable targets
- Motion that ignores reduced-motion preferences

## Named visual slop patterns

- Card soup: every idea is placed in an identical rounded rectangle
- Pill infestation: decorative capsules used for labels, navigation, metadata, and buttons without hierarchy
- Gradient fog: glow, blur, glass, or gradients used as atmosphere instead of structure
- Fake dashboard: decorative charts, activity feeds, or status widgets that do not represent real data or actions
- Hero template reflex: oversized headline, vague subtitle, two generic buttons, and an unrelated product mockup
- Bento reflex: arbitrary uneven tiles used because the pattern is fashionable, not because the content needs it
- Floating-object collage: disconnected icons, screenshots, or 3D objects used to fill empty space
- Icon confetti: repeated icons that add no information
- Uniform radius: every surface, field, image, and control receives the same oversized corner radius
- Shadow stack: depth simulated with many soft shadows and no clear elevation model
- Centered-everything: long-form or task content centered at the cost of scanning and hierarchy
- Type-scale theater: huge display text paired with undersized body text or weak information density
- Empty-space theater: excessive whitespace used to imply premium quality while hiding low utility
- Decorative microcopy: labels such as powerful, smart, seamless, next-generation, or magic without evidence
- Premature polish: elaborate animation or illustration before the primary task works
- Component drift: the same action, state, or data appears with inconsistent styles or labels
- Stock-persona imagery: generic artificial people or staged teams that do not support the buyer's decision
- AI image residue: malformed hands, illegible text, inconsistent lighting, repeated objects, or impossible geometry
- Brand wash: applying accent colors everywhere until no element has emphasis
- Responsive collapse: desktop sections stack on mobile in the wrong task order or with unusable controls

## Required process

1. Read the full brief, approved claims, brand system, and task-critical flows.
2. Identify the primary user, decision, and action for each screen.
3. Inventory the existing palette, type scale, spacing, radii, shadows, components, and interaction states.
4. Run deterministic checks at the approved desktop and mobile viewports.
5. Inspect every named visual slop pattern manually.
6. Verify real content, real state, and real interactions. Reject decorative evidence.
7. Check task hierarchy: the primary action must be obvious, usable, and supported by the content around it.
8. Check responsive task order, touch targets, focus states, reduced motion, and overflow.
9. Compare before and after at matching viewports. Preserve distinctive approved design choices.
10. For material work, route the exact artifact and screenshots to an independent reviewer.
11. Record viewport sizes, routes, artifact identity, findings, repairs, and remaining limitations.

## Acceptance checks

- Zero deterministic blockers
- One coherent palette and type voice per approved brand system
- Each surface has a clear task hierarchy
- Every component earns its space through information or action
- Real evidence is visually distinct from claims and samples
- Desktop and mobile preserve the intended task order
- Accessibility and interaction states are proven, not inferred
- No named pattern remains unless the brief gives a specific product reason
- Material work has independent review evidence tied to the exact artifact

## Runtime contract for paid agents

Any paid agent that writes customer-facing content or generates visual artifacts must carry these quality references in its immutable run package:

- `voice-listeningpost`
- `commercial-copy-standard`
- `anti-slop-editor`
- `design-anti-slop-reviewer`
- `quality-router`
- `independent-reviewer`

Writing outputs must pass deterministic writing lint before delivery. Visual outputs must provide viewport evidence and a design review report before publish. A missing quality reference or missing gate is a validation failure, not a warning.

For the reusable catalog-to-delivery integration pattern, website-generator safeguards, and two-service canary proof, read `references/paid-agent-runtime-integration.md`.

## Evidence shape

Record:

- artifact identity and version
- routes or files reviewed
- approved desktop and mobile viewports
- deterministic blocker count
- named-pattern findings with exact locations
- before and after screenshots when repaired
- accessibility and interaction evidence
- reviewer identity and independent verdict
- explicit limitations

## Rollback

Disable the design anti-slop gate only by an explicit versioned policy change. Do not silently remove it from a paid agent's run package or downgrade failure to warning.
