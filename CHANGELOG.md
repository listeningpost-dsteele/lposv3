# Changelog

## 3.2.1

- LPOS-029 Interpretation Contract: the anti-guessing standard. Precedence of
  intent (instruction > spec > artifact pattern > prior); conflicts between
  levels are blocking questions on material work; a written contract
  (instruction, interpretation, invariants, conflicts, verification) precedes
  execution; every long-lived artifact gets a spec in lpos-state/specs/;
  corrections update the spec first and apply minimal diffs; reviewers reject
  any change the contract does not name. Kernel, quality-router, reviewer, and
  LEDGERS updated accordingly.

## 3.2.0

- Model-routing onboarding (ONBOARDING.md step 6): the installer discovers the
  runtime's actual providers and asks the Principal to assign model classes.
  Single-license installs answer one question; multi-model installs answer at
  most three. Choices persist in `lpos-state/model-routing.yaml` (schema in
  LEDGERS.md) with fallback order and standing policies: visible fallback,
  quota-outage reroute with decision record, benchmark before promotion, and
  review diversity (independent review prefers a different model than the
  creator).
- Kernel: model routing section added; jobs and specialists reference classes,
  never providers.

## 3.1.0

Merged patches 3.0.1 through 3.0.4 into the distribution:

- 3.0.1 (structure): CHIP-KERNEL.md lazy-load operating prompt,
  SPECIALIST-INDEX.md with fallback map, LEDGERS.md persistence formats, Design
  guild and Web & Product Designer specialist, CS-002/CS-003 routing fixes,
  material_artifact_default (CS-003), five-gate quality router, reviewer
  isolation, single completion report, Standing Operation normalization
  (inputs/outputs/specialists/owner for all), CRAFT-STANDARDS.md formatting
  fix, LPOS-013 contract alignment, v2 residue moved to MIGRATION-FROM-V2.md.
- 3.0.2 (email loop): SO-021 Principal Feedback Loop — questions, consent, and
  approvals by email, 10-minute checks, sender verification, question registry.
- 3.0.3 (runtime convergence): canonical path discipline, evidence-per-run and
  decision-record rules, single SO-021 collector/registry, collector dedup,
  staffing policy recorded as decision, Standing Operation wiring guidance with
  deferral rules.
- 3.0.4 (onboarding): ONBOARDING.md first-run flow — office naming (default
  Chip), guided email setup with real verification before SO-021 activates,
  verified reply addresses, channel mapping; office identity parameterized in
  kernel, SO-021, and templates.

## 3.0.0

Restructured LPOS into a compact GitHub repository, a single archived full
source package, a compiled Hermes distribution, and separate tests and examples.
