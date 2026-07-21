# Bug Remediation Escalation Policy

The system fixes silently and interrupts a human only for the unresolvable. This
policy defines both.

## Budgets (defaults; tune per component)

- Reproduction budget: 3 distinct strategies before declaring not-reproducible.
- Attempt budget: 4 candidate fixes, each fully verified, before declaring
  unfixable.
- One escalation per distinct defect; duplicates attach to the open escalation.

## Fix acceptance gate

A candidate fix is accepted only when all hold: the defect's regression fixture
now passes; no previously passing test regresses; an independent reviewer passes
the full review envelope; the change stays within the bug's scope (no unrequested
edits); and it requires no external or irreversible action to take effect.

## Escalation floor

Surface to a human when any holds: not reproducible after the reproduction budget;
root cause not localized with sufficient confidence; the attempt budget is
exhausted without an accepted fix; the fix requires an external or irreversible
action (a deploy, a data migration, a third-party change); the report is really a
product, taste, or policy decision rather than a defect; the defect is
security-sensitive and needs human judgment; a correct fix would exceed the bug's
scope; or it duplicates an open escalation.

## Every escalation carries

Repro status and steps, the root-cause hypothesis and confidence, each fix attempt
and the specific reason it failed, the failing fixture, and a recommended next
action. An escalation without this package is a failure condition.

## The compounding rule

A reproduction always becomes a failing fixture before any fix. A verified fix
promotes that fixture into the permanent benchmark corpus, so the defect can never
silently return. Recurring defect classes are fed to the skill-evolution loop to
improve the remediation skills themselves.

## Safety

Reproduction runs untrusted reporter input and the fixer writes code: both run in
the sandbox with no network and resource limits. No production merge or deploy
happens without approval; because externality is derived from the action kind, a
deploy is inherently external and cannot execute without a grant.
