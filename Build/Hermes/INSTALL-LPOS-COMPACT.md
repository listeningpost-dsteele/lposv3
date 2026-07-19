# Install LPOS Compact Distribution v3.2

Treat this folder as the compiled Hermes distribution of LPOS.

## Load order

1. `CHIP-KERNEL.md`              — load fully; this is the operating prompt.
2. `CRAFT-STANDARD-ROUTING.yaml` — load fully (small).
3. `SPECIALIST-INDEX.md`         — load fully (small).
4. Everything else (`LPOS-CORE.md`, `CRAFT-STANDARDS.md`, `GUILDS.md`,
   `SPECIALISTS.md`, `STANDING-OPERATIONS.md`, `BENCHMARKS.md`, `skills/`) is
   REFERENCE material. Do not load whole files into context. Retrieve only the
   section for the ID you need (LPOS-###, CS-###, SPECIALIST-###, SO-###,
   BENCH-###) at the moment you need it.
5. On first install, create `lpos-state/` per `LEDGERS.md`.
6. Install this distribution behind a single canonical path (for example a
   `current` symlink) and point every scheduled job at that path, never at a
   versioned folder.
7. Run the first-run onboarding in `ONBOARDING.md`: name the office (default
   Chip), set up and verify the email channel, record verified reply addresses
   and available channels, wire the Standing Operations. The Principal feedback
   loop (SO-021) activates only after the email round trip verifies; until then,
   questions stay in the session.

Note: LPOS-026 and LPOS-027 are sections inside `LPOS-CORE.md`.

## Required installation behavior

- Back up the current Hermes environment.
- Install the office (kernel) as the executive office under its configured name.
- Map each capability to a Guild, Specialist, and craft standard.
- Preserve useful existing knowledge and integrations.
- Require Intent, Truth, Reasoning, Craft, and Outcome gates.
- Require independent review for material work.
- Preserve strong existing artifacts and compare before and after.
- Do not expose internal reasoning in public artifacts.
- Do not deploy or perform irreversible external actions without approval.
- Verify real operation before disabling legacy components.

## Upgrading from an earlier LPOS

Existing v2 environments: see `MIGRATION-FROM-V2.md`. Existing v3.0.x
environments: repoint all jobs to the canonical path, keep existing
`lpos-state/`, backfill `confirmed.office` values, and treat ONBOARDING.md as a
short confirmation of recorded values rather than a fresh setup.

## Completion report (the only report format — supersedes all others)

Return only:

### Installed
### Updated
### Verified (state how each item was verified)
### Archived
### Known limitations (anything unverified — never claim perfect operation)
### Owner Approval Required
