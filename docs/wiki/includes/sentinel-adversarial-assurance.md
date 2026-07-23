---
title: Sentinel adversarial assurance
section: includes
order: 7
---

# Sentinel adversarial assurance

**Sentinel (GUILD-039)** is an organization separate from the guilds that create Chip's
work. It passively scans every persisted artifact revision, identifies security
weaknesses, and gives you concrete remediation and verification steps through the
Principal security inbox.

## Independent does not mean trusted

The Constitution now says that no guild, specialist, agent, model, provider, or new
organization is trusted because of its title or mission. Sentinel follows that rule:

- its raw assessment is marked **untrusted**;
- Sentinel cannot review, approve, suppress, remediate, or close its own work;
- the exact assessment hash goes through the ordinary fresh-context independent review;
- the deterministic control plane re-runs the checks against the exact artifact hash;
- only output that passes both layers can affect completion or be shown to you as a
  factual finding.

A rejected or unavailable review creates an assurance-failure notice, not a list of
unverified findings. The task fails closed until review is restored.

## What happens when Sentinel finds a problem

Critical and High reviewed findings block completion. Medium, Low, and Info findings are
reported as advice by default. Each accepted item includes:

1. the exact task and artifact hash;
2. severity, confidence, and affected locations;
3. a redacted evidence pointer;
4. implementation steps; and
5. tests that demonstrate remediation.

Acknowledging the report does not close it. Remediation becomes a separate LPOS task and
passes the normal interpretation, approval, execution, and independent-review controls.

## Continuous coverage

Sentinel runs immediately after artifact creation. SO-026 also checks every five minutes
for any persisted revision the event hook missed. Both paths are read-only and
idempotent.

## Safety boundary

Continuous testing is passive: no artifact execution, network probing, credentials,
shell, exploitation, persistence, exfiltration, or live-state mutation. Active
penetration testing requires a separately approved, owned, isolated, time-bounded scope.
The exact scope must be bound to an action and grant already persisted through LPOS's
ordinary ledgers and revalidated through the normal identity/approval service immediately
before use. Sentinel identities cannot approve the engagement, and its results still pass
the same adversarial review.

## Useful commands

```console
lpos sentinel status --db state/lpos.db
lpos sentinel reports --db state/lpos.db --unacknowledged
lpos sentinel scan --db state/lpos.db --task-id TASK-...
```

Sentinel is a defense layer, not proof of security or compliance.
