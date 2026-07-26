# Code Testing Governance

The Code Testing Guild (GUILD-040) codifies mandatory verification for source code,
executable configuration, database migrations, APIs, scripts, infrastructure-as-code,
build logic, and deployment logic. It does not apply to copy, visual taste, research,
finance, legal analysis, or other non-code artifacts. It is an additive layer: existing
testing behavior is preserved.

## Separation of responsibility

Engineering builds code. The Code Testing Guild proves whether the code satisfies its
behavior contract and can be released safely. Quality Assurance evaluates the complete
release across all artifact types. Security owns security judgment; Code Testing executes
and verifies security tests when required.

## Core law

A material code change is not complete because it compiles, looks plausible, or passes
agent-written unit tests. It is complete only when it passes the required
criticality-weighted test gauntlet and produces independently verifiable evidence.

## Executable enforcement

The standard is enforced by `lpos_engine.code_testing`, not by prompt instruction alone:

- `criticality.classify` deterministically assigns LIGHT, STANDARD, HIGH, or CRITICAL.
- `gauntlet.need_to_change_gate` requires a reproduction, a demonstrated missing
  behavior, or an objective-constraint proof before production code is modified;
  otherwise `NO_CHANGE_REQUIRED` is the correct successful result.
- `gauntlet.evaluate_gauntlet` REJECTS a release when a required gate did not run, when a
  gate failed or is flaky, or when only a green unit suite is offered for STANDARD or
  above.
- `evidence.build_evidence_packet` assembles the release evidence and rejects a packet
  whose independent reviewer is the implementer.
- `manifest` loads repository-native commands and never invents a build, test, lint, or
  type-check command.

## Standing Operations

- SO-027 Code Test Gauntlet runs on every material code change (event-driven).
- SO-028 Test Suite Health Review runs weekly and reports flaky, slow, duplicate,
  skipped, and low-value tests, coverage gaps, and mutation survivors.
- SO-029 Critical Path Hardening runs before a HIGH or CRITICAL release and verifies the
  extra hardening gates are present and passing.

## Test independence

After acceptance behavior is approved, the implementation agent may not silently weaken,
delete, skip, rewrite, or reinterpret it. Changes to frozen acceptance behavior require
independent review, mirroring the Sentinel independence rule that no producer may approve
its own material output.

## Completion evidence

Every verified change records the behavior contract, criticality, exact commands run,
test results, static and architecture results, mutation results when required, known
residual risk, rollback method, the independent reviewer, and the release decision.
