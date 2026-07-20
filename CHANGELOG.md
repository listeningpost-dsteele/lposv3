# Changelog

## 3.3.0

Hardening release, responding point by point to the external v3.2.3 re-audit:

- Canonical source restored: `Source/v3/` holds every architecture document;
  `Tools/compile.py` deterministically generates `Build/Hermes` and CI proves
  compile(source) == build byte-exact (LPOS-020/022 conformance).
- Validator replaced: `Tests/verify_compact.py` now parses every YAML block,
  validates component schemas, resolves the full reference graph, verifies the
  specialist index exactly, opens and compares both archives, checks manifest
  SHA-256 hashes and version consistency, asserts safety-critical content
  (approval guard, review envelope, self-approval ban, SO-021 behaviors,
  CS-003 default), and scans for secrets and hardcoded identity. The PASS
  message now states its scope honestly.
- `Tests/mutation_test.py`: the review's 16 sabotage variants are a permanent
  negative suite; all 16 must be rejected on every commit.
- Review envelope contradiction resolved: kernel, reviewer skill, quality
  router, and LPOS-029 now share one canonical envelope; isolation excludes
  the creation conversation and creator reasoning, never the contract or
  evidence. The prose-specific review check is now conditional on prose work.
- LPOS-030 Materiality Standard: a deterministic definition of "material"
  with Principal override and material-when-uncertain default.
- SO-021 formalized: explicit state machine, split verification timestamps
  (outbound, inbox read, Principal round trip, activation), provider-neutral
  message identity, atomic question closure with replay protection,
  per-channel verified identities, action-bound approvals.
- Schema conformance: every Standing Operation gains Objective and Required
  capabilities; decision records gain implementation notes; the Principal
  Model gains values, working style, decision history pointer, and snapshot
  history; LPOS-013 output contract canonicalized to Evidence Plan; LPOS-021
  scoped to canonical source documents; BENCH-S032 added.
- `SCHEMAS.md`: eleven machine-readable runtime envelopes (task, contract,
  spec, review, approval, message identity, evidence, decision, SO run).
- `Tests/benchmark-fixtures/`: fixture standard plus eight fixed fixtures
  (strategy, engineering with oracle cases, de-AI copy, design invariants,
  executive brief, SO-021 spoof and replay, multi-guild routing, review
  isolation with planted defects). Coverage floor enforced by the validator
  and allowed only to rise.
- CI: GitHub Actions runs compiler roundtrip, reproducible-artifact check,
  contract validation, and the mutation suite on every push.

Honest scope: this release verifies the distribution's contracts and
packaging. Runtime behavior (actual routing, scheduling, email, approvals)
is enforced by the Hermes adapter and measured through fixtures and the
evidence ledger, not by this repository's tests.

## 3.2.3

- CS-001 v2: human copy standard with voice specs, four tests, ban list, mandatory
  de-AI pass; CS-014/CS-018 extensions; router and reviewer wiring.

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
- 3.0.2 (email loop): SO-021 Principal Feedback Loop: questions, consent, and
  approvals by email, 10-minute checks, sender verification, question registry.
- 3.0.3 (runtime convergence): canonical path discipline, evidence-per-run and
  decision-record rules, single SO-021 collector/registry, collector dedup,
  staffing policy recorded as decision, Standing Operation wiring guidance with
  deferral rules.
- 3.0.4 (onboarding): ONBOARDING.md first-run flow: office naming (default
  Chip), guided email setup with real verification before SO-021 activates,
  verified reply addresses, channel mapping; office identity parameterized in
  kernel, SO-021, and templates.

## 3.0.0

Restructured LPOS into a compact GitHub repository, a single archived full
source package, a compiled Hermes distribution, and separate tests and examples.
