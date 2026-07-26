---
title: Code testing
section: includes
order: 8
---

# Code testing

The Code Testing Guild (GUILD-040) is an additive, executable code-verification layer. It
does not replace any existing testing — the full existing test suite and every prior
Standing Operation keep running unchanged. What it adds is the ability to classify a code
change's risk, enforce a criticality-weighted test gauntlet, and produce independently
verifiable release evidence, deterministically in code rather than by instruction alone.

It applies only to executable software: source code, APIs, scripts, database migrations,
infrastructure-as-code, executable configuration, and build and deployment logic.

## What it does

- **Criticality classification** — every material change is classified LIGHT, STANDARD,
  HIGH, or CRITICAL. The classifier is deterministic and total: unknown or absent signals
  default to STANDARD and it never fails.
- **The gauntlet** — a cumulative, tier-weighted table of required gates. A required gate
  that did not run is a rejection, a failing or flaky gate is a rejection, and a green
  unit suite alone can never approve a STANDARD, HIGH, or CRITICAL change.
- **The Need-to-Change Gate** — a production change requires a reproduction, a
  demonstrated missing behavior, or an objective-constraint proof; otherwise the correct
  successful answer is `NO_CHANGE_REQUIRED`.
- **Release evidence packets** — assembled with an independence rule: a producer cannot
  audit its own release, so the independent reviewer may not be the implementer.
- **A testing manifest** — repository-native commands are read from a manifest; the
  system never invents a build, test, lint, or type-check command.

## The specialists

Twelve specialists (SPECIALIST-034 through SPECIALIST-045) staff the guild: the Code Test
Director, Change Necessity Analyst, Acceptance Criteria Analyst, Acceptance Test
Architect, Characterization Test Engineer, Unit Test Engineer, Integration and System
Test Engineer, Property and Invariant Test Engineer, Mutation Test Analyst, Architecture
Fitness Analyst, Test Reliability Analyst, and Release Verification Auditor.

## The Standing Operations

- **SO-027 Code Test Gauntlet** — runs on every material code change (event-driven).
- **SO-028 Test Suite Health Review** — runs weekly; reports flaky, slow, duplicate,
  skipped, and low-value tests, coverage gaps, and mutation survivors.
- **SO-029 Critical Path Hardening** — runs before a HIGH or CRITICAL release and verifies
  the extra hardening gates are present and passing.

## The skills and module

Four Hermes skills ship with the guild: `code-test-gauntlet`,
`code-criticality-classifier`, `acceptance-spec-reviewer`, and `test-evidence-auditor`.
The executable core is the `code_testing` engine module, with a small CLI:
`python -m lpos_engine.code_testing classify` and `python -m lpos_engine.code_testing
gauntlet`.

## Related pages

- [Patch notes 4.4.0](/patch-notes/4-4-0.html)
- [Everything LPOS includes](/includes/index.html)

## The Test Coverage Map

Run `python tools/build_test_report.py` to generate `dist/test-coverage.html` — a
self-contained page that shows every source module, whether it is under test, its line
coverage, and its gauntlet tier, sorted so untested or low-coverage code surfaces first.
It is the visual answer to "is all of the code being tested?", and it is deliberately
honest: modules the test suite does not import (such as CLI entrypoints) show as low
rather than being hidden.

## Writing quality: anti-slop-editor

Shipped as a packaged skill (`anti-slop-editor` 1.0.1): a named-pattern de-AI editing pass
that preserves voice with minimum-effective edits, enforces deterministic lint, and refuses
to guess whether text was AI-authored. CS-001 and zero em dashes stay authoritative.
