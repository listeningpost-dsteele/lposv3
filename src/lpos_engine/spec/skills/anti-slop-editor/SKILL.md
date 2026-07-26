---
name: anti-slop-editor
description: A named-pattern de-AI editing pass that removes AI-slop tells with minimum-effective edits while preserving Dan, Chip, and LPOS voice. Detect before rewriting; never guess whether text was AI-authored.
version: 1.0.1
author: Listening Post
license: MIT
---

# Anti-Slop Editor

Improve prose by removing specific, named AI-slop patterns — not by vaguely "making it
less AI." Detect first, then apply the smallest edit that fixes the pattern, so strong
voice is preserved rather than flattened.

## Authoritative rules (do not override)

- CS-001 governs. Zero em dashes. Independent review remains required for material text.
- Contextual technical-term handling is authoritative: do not strip precise technical
  vocabulary just because a generic detector flags it.
- Preserve Dan, Chip, and LPOS voice signals. Minimum-effective edits only.

## The pass

1. **Detect before rewriting.** Flag each occurrence of a named pattern with its location.
   Named patterns include: em dashes; the "not just X, it's Y" antithesis; forced rule-of-
   three triads; banned marketing vocabulary (seamless, effortless, unlock, supercharge,
   elevate, empower, game-changing, revolutionize, delve, robust, cutting-edge); number
   parades; hollow hedging; and summary restatement.
2. **Edit minimally.** Replace only the flagged span with the smallest change that removes
   the tell and keeps the sentence's meaning and cadence. Do not rewrite whole paragraphs
   to remove one pattern.
3. **Preserve voice.** Keep the author's characteristic phrasing, rhythm, and stance. If an
   edit would flatten a genuine voice signal, leave it and note it instead.
4. **Deterministic lint.** The same input yields the same flags and the same edits. No
   stochastic rewriting.

## What this skill refuses to do

- It does not guess or assert whether text was AI-authored. It edits patterns, not origins.
- It does not remove precise technical terms in context.
- It does not replace independent review — a material piece still gets a fresh-context pass.

## Boundary

This is a prose-quality skill. It has no authority over code, security, or release
decisions, and it never weakens CS-001 or the zero-em-dash rule.
