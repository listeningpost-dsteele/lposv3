# NOTICE: SkillOpt attribution and adaptation

LPOS Skill Evolution is derived from the ideas in Microsoft SkillOpt, used under
its MIT license, and reimplemented for the Hermes and LPOS environment. This note
records exactly what was taken and exactly what was changed, so the lineage is
honest and the license is honored.

## Source

- Project: Microsoft SkillOpt
- Repository: github.com/microsoft/SkillOpt
- Commit referenced during review: b860a5cf88ce75e2bd02ca981ac21fb28cffba83
- License: MIT
- Package version at review: skillopt 0.2.0
- Verified in this session: the repository exists at that commit, installs, and
  its validation gate and deployed companion (SkillOpt-Sleep) behave as its docs
  describe.

## What we took (the ideas, under MIT)

1. The validation gate. Accept a candidate skill only when it beats the current
   skill on held-out tasks. A plausible edit that does not measurably improve the
   held-out score is rejected. This is the core idea and the reason the system is
   worth having.
2. The offline improvement loop of SkillOpt-Sleep: mine recurring tasks, replay
   them, reflect into bounded skill edits, gate the edits, and stage proposals for
   a human rather than adopting automatically.
3. The bounded-edit discipline (their "textual learning rate"): few edits per
   candidate so change stays legible.
4. The train, validation, and held-out split as the basis for an honest score.

## What we did not take

- We did not vendor or depend on Microsoft's code. LPOS Skill Evolution is an
  independent implementation, so nothing in our runtime imports `skillopt` or
  `skillopt_sleep`.
- We did not adopt their transcript harvesters (Claude Code, Codex, Copilot,
  Devin). They do not read Hermes sessions, and their real backends send truncated
  transcript excerpts to a model provider with no guarantee of being secret-free,
  which is unacceptable for Hermes sessions that can contain keys and customer
  data.

## What we changed for Hermes and LPOS

1. Reimplemented the gate from the reference behavior as
   `lpos_engine.evolution.gate.evaluate_gate`, self-contained and auditable
   against LPOS standards, with an added minimum-gain margin so noise-sized wins
   cannot accumulate as instruction bloat.
2. Offline and secret-safe by construction for the shipped capability: no network,
   no model calls, and a reviewed task file rather than raw transcript harvesting.
   The privacy boundary that is a warning in SkillOpt is a hard default here.
3. Native scoring on an LPOS domain. The working example scores CS-001 style
   compliance deterministically. The operating system's own 53 benchmark fixtures
   load as tasks via `lpos_engine.evolution.lpos_tasks`, so evolution is measured
   against the same fixtures the OS already ships.
4. Staging-only adoption tied to LPOS governance. Accepted proposals are staged,
   never written live; the adopter refuses any path that looks live or production;
   material skill changes require independent review and Principal approval
   (LPOS-030), with the before and after score recorded in the evidence ledger.
5. Repeated-evidence requirement. An edit must be justified by more than one
   failing task before it is proposed, so the loop does not encode a single
   one-off preference.

## License

Microsoft SkillOpt is MIT licensed. This derived work is distributed under the
same MIT license. The full MIT license text accompanies the LPOS distribution.
