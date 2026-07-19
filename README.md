# Listening Post Operating System v3.2 Compact Repository

This repository is optimized for GitHub, distribution, and Hermes installation.
v3.2 merges patches 3.0.1 through 3.0.4 into the distribution and adds
model-routing onboarding.

## What changed from v3.0

- Model routing as an onboarding choice: work routes through classes (executive,
  routine, review, local) defined in `model-routing.yaml`, never to a named
  vendor. One license works out of the box; added models slot in through a short
  conversation, a benchmark, and one file edit.

- Lazy-load architecture: `CHIP-KERNEL.md` is the only always-loaded document
  (~3k tokens); everything else is retrieved by ID on demand. The v3.0 install
  loaded ~45k tokens per session.
- `SPECIALIST-INDEX.md` routing table with a fallback map for unstaffed guilds.
- `LEDGERS.md` persistence formats: evidence ledger, decision ledger, question
  registry, Principal Model (with office identity), per-operation state.
- `ONBOARDING.md` first-run flow: name your executive office (default Chip),
  guided email setup with real send/read verification, verified reply addresses,
  channel mapping, Standing Operation wiring with anti-noise rules.
- SO-021 Principal Feedback Loop: questions, consent, and approvals by email
  from the configured office address, checked every 10 minutes; sender
  verification; silence never equals consent; dormant until email verifies.
- Design guild + Web & Product Designer specialist; CS-002/CS-003 now reachable
  through routing; CS-003 applies to every material production artifact.
- Five-gate quality router (Intent gate restored), reviewer isolation
  requirement, single canonical completion report, runtime path discipline
  (canonical `current` symlink), evidence-per-run and decision-record rules.
- v2 remediation residue removed; `MIGRATION-FROM-V2.md` covers upgrades only.

## Structure

```text
Source/
  LPOS-Full-Source-v2.0.zip     (archived full source, unchanged)

Build/
  Hermes/                        (the compiled distribution, source of the zip)
  LPOS-Hermes-Compact-v3.2.zip   (the installable package)

Tests/
Examples/
```

## Install

Use `Build/LPOS-Hermes-Compact-v3.2.zip` and follow
`Examples/INSTALL-WITH-HERMES.md`.

## Develop

Extract `Source/LPOS-Full-Source-v2.0.zip`, make changes in the full source
repository, then rebuild the compact distribution and run
`Tests/verify_compact.py`.
