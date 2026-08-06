---
id: CS-EXP-008
title: Inclusive Design and Accessibility Standard
version: 1.0.0
status: Accepted
owner: Listening Post
---

<!-- Generated from LPOS expert corpus v1.2, source SHA-256 fcc787db6f8ab0be691f9030af927005a005561db1c0fecdee5f6dbdc87a060f, source lines 14678-14750. Runtime lifecycle is governed separately. -->

# Inclusive Design and Accessibility Standard

## Design requirement

Accessibility is part of the experience contract from research through design, content, implementation, and release. It is not a final checklist or optional quality attribute.

## Relevant dimensions

Address as applicable:

- Keyboard access
- Visible focus
- Logical focus order
- Semantic structure
- Accessible names and descriptions
- Contrast
- Non-color meaning
- Zoom and reflow
- Text spacing
- Touch target access
- Motion and reduced-motion behavior
- Time limits
- Error identification and recovery
- Form labels and instructions
- Alternative text and nonvisual alternatives
- Captions, transcripts, and media controls
- Status announcements
- Reading and navigation order
- Cognitive load and plain language
- Consistent identification
- Authentication and security flows
- Assistive-technology compatibility
- Localization and text expansion

## Research inclusion

When the experience materially affects people with disabilities or assistive-technology use, include relevant participants or explicitly state the evidence gap. Expert review is not a substitute for all participant evidence.

## Design evidence

Design artifacts must annotate accessibility behavior that is not obvious from the visual rendering, including focus, semantics, status, labels, keyboard interaction, motion, and alternatives.

## Blockers

The following block design readiness when material:

- Required content or controls are unreachable.
- Focus is missing, hidden, trapped, or illogical.
- Meaning depends only on color, position, sound, or motion.
- Contrast is insufficient.
- Zoom or reflow hides required content or action.
- Controls lack accessible names.
- Form errors cannot be identified or recovered from.
- Motion ignores reduced-motion needs.
- Images or media carrying meaning lack an alternative plan.
- Responsive order breaks reading or task order.
- Authentication or security interactions exclude users without a justified alternative.

## Independent verification

Creator-side accessibility design review does not certify the implementation. Quality and Release Assurance must independently test the exact rendered release with the applicable standards, tools, keyboard interaction, and assistive technologies.
