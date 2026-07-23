# Sentinel Adversarial Assurance

Sentinel is LPOS organization **GUILD-039**. It continuously performs passive,
non-destructive security analysis of every text artifact Chip persists. It records
findings against the exact artifact SHA-256, supplies remediation and verification
steps, and stages independently reviewed reports for the Principal.

## Constitutional trust model

Sentinel is independent from the guild that created the work, but independence does
not make it trusted. LPOS Constitution Article VIII applies to Sentinel and every future
new guild:

1. Raw guild output is persisted with `trust_state = "untrusted"`.
2. The exact assessment hash enters the normal fresh-context independent review
   process. Creation conversation, private reasoning, and self-assessment remain
   excluded.
3. The control plane independently re-runs the packaged checks against the exact
   artifact revision and compares stable finding fingerprints.
4. Only a PASS review with fresh-context attestation, producer/reviewer separation, and
   all structural checks passing creates a trusted assessment.
5. Only trusted findings may block completion or appear as factual findings in the
   Principal security inbox.
6. Sentinel cannot approve, suppress, downgrade, remediate, or close its own findings.
   Remediation is a new ordinary LPOS task and passes the usual approval and review
   controls.

If the independent review fails or is unavailable, LPOS creates an assurance-failure
notice that explicitly presents **no Sentinel finding as fact**. Completion fails closed
until the exact assessment is reviewed successfully.

## Continuous operation

The artifact-creation hook runs Sentinel immediately after every persisted revision.
SO-026 runs every five minutes as an idempotent backstop and finds revisions missed by
the event path. Both paths use the same assessment, review, report, and completion-gate
logic.

Default blocking severities are Critical and High. Medium, Low, and Info findings are
reported with remediation but remain advisory unless a higher policy or the Principal
makes them blocking.

## Passive checks

The packaged policy currently checks for high-signal forms of:

- embedded private keys and hard-coded credentials;
- shell and downloaded-code execution;
- unsafe dynamic execution and deserialization;
- SQL interpolation;
- disabled TLS verification;
- obsolete cryptography;
- overly permissive file modes; and
- instructions attempting to bypass approval, review, authentication, logging, safety,
  or constitutional controls.

Evidence stored in the database is limited to location, a redacted excerpt, and an
evidence digest. The raw secret or private key is never copied into a finding.

## Penetration-testing safety boundary

Continuous Sentinel operation does not execute artifacts, open network connections,
use credentials, invoke shells, exploit targets, create persistence, exfiltrate data,
or alter live state. An active penetration test requires a separate Principal-approved
engagement that records target ownership, scope, methods, time window, isolation, data
handling, stop conditions, and rollback. The exact engagement-scope hash must be
bound to an ordinary external, irreversible LPOS `ActionPlan` stored in the action ledger
and a persisted `ApprovalGrant` revalidated through the normal Principal identity service;
Sentinel identities are explicitly rejected as approvers. The packaged
release provides this fail-closed authorization gate but no live exploit runner. Its
results remain untrusted until the same independent adversarial process passes.

## CLI

```console
lpos sentinel status --db state/lpos.db
lpos sentinel scan --db state/lpos.db --task-id TASK-...
lpos sentinel reports --db state/lpos.db --unacknowledged
lpos sentinel show --db state/lpos.db --report-id SREPORT-...
lpos sentinel ack --db state/lpos.db --report-id SREPORT-... \
  --acknowledged-by Principal --note "Accepted for remediation planning"
```

Acknowledgement is append-only and does not close or remediate a finding.

## Stored records

Migration `002_sentinel.sql` creates immutable tables for raw assessments, independent
assessment reviews, Principal reports, and separate acknowledgements. Update and delete
triggers reject mutation. The ordinary append-only event stream records every stage.

## Limitations

Sentinel is an additional defense layer, not proof of security, a substitute for a
qualified scoped penetration test, or a compliance attestation. Sentinel is additive
assurance: the 14 findings from the LPOS v4.2.0 external audit were closed by the v4.2.1
remediation, not by Sentinel, and Sentinel's presence must not be represented as closing
them.
