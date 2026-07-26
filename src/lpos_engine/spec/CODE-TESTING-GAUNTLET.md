# Code Testing Gauntlet Standard

Scope: executable software and code changes only.

## Principle

Human judgment moves upward from reading every generated line to approving behavior,
architecture, risk, and release evidence. Deterministic verification is the primary
gate, and inspection scales with criticality. This standard is codified as executable
data and gates in `lpos_engine.code_testing`; prompt instructions alone are insufficient.

## Criticality tiers and required gates

Gates are cumulative: STANDARD includes LIGHT, HIGH includes STANDARD, and CRITICAL
includes HIGH.

### LIGHT

For low-risk internal changes.

- Need-to-Change Gate
- format or syntax check
- lint or equivalent static check
- focused unit tests
- build or import verification
- changed-behavior smoke test

### STANDARD

For normal product and business logic.

- everything in LIGHT
- behavior acceptance criteria
- regression test
- unit test stream
- integration or contract test stream
- type check when available
- architecture and complexity checks
- real workflow smoke test

### HIGH

For authentication, permissions, billing, customer data, public APIs, migrations,
concurrency, or broad architectural changes.

- everything in STANDARD
- independent acceptance-spec review
- executable acceptance tests
- property or invariant tests when relevant
- changed-code mutation testing
- security tests
- performance or concurrency checks when relevant
- manual or system spot check
- rollback verification

### CRITICAL

For destructive operations, secrets, financial movement, irreversible migrations,
production infrastructure, or safety-sensitive behavior.

- everything in HIGH
- Principal or qualified-engineer approval of behavior and architecture
- isolated test environment
- full relevant mutation hardening or documented exception
- staging or canary validation
- restore or rollback drill
- production observability and incident response plan
- explicit release approval

## Deterministic classification

`classify(signals)` maps change signals to a tier and is total: unknown or absent
signals default to STANDARD, and the function never raises. Destructive operations,
secrets, financial movement, irreversible migrations, and production infrastructure
force CRITICAL. Authentication, permissions, customer data, public APIs, migrations,
concurrency, and a broad blast radius force at least HIGH. A small, reversible internal
change with no sensitive signals is LIGHT.

## Mandatory constraints

- A bug fix begins with reproduction or a failing behavior test.
- No production change is required when the behavior already works; `NO_CHANGE_REQUIRED`
  is a valid successful result.
- The implementation agent may not weaken frozen acceptance tests.
- Deleted, skipped, xfailed, or suppressed tests require explicit review.
- Tests that only prove execution did not crash are insufficient.
- Mocks may not replace the behavior that needs verification.
- Commands must be run, not merely proposed, and are taken only from the repository
  testing manifest; no build, test, lint, or type-check command is invented.
- A green unit suite alone cannot approve STANDARD, HIGH, or CRITICAL changes.
- Unexplained failing or flaky tests block release.

## Release decision

`evaluate_gauntlet(level, gate_results)` returns PASS or REJECT. A required gate that did
not run is a REJECT ("required command did not run"). A failing or flaky required gate is
a REJECT. A green unit suite alone can never approve STANDARD or above.

## Evidence packet

Every verified change records a change identifier, criticality, behavior contract, frozen
acceptance artifacts, commands executed, pass and fail results, coverage and mutation
evidence when applicable, architecture fitness results, known residual risk, rollback
method, the independent reviewer, and the release recommendation. The independent
reviewer may not be the implementer: a producer cannot audit its own release.
