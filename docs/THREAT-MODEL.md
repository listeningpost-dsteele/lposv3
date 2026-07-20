# LPOS v4 Threat Model

## Protected assets

Principal authority, verified identities, exact action parameters, approvals, artifacts,
interpretation contracts, specifications, review isolation, audit events, credentials,
and Standing Operation state.

## Trust boundaries

1. Principal channel to identity verifier.
2. LPOS control plane to model-host process.
3. LPOS control plane to action/channel adapters.
4. Process to SQLite and local artifact storage.
5. Scheduler to Standing Operation runner.

## Primary threats and controls

- **Spoofed approval:** verified identity mapping, provider-neutral message keys, exact
  action binding, expiry, and replay protection.
- **Approval drift:** canonical action hash checked again at apply time.
- **Duplicate external effect:** unique idempotency key, atomic claim, single approval
  consumption, and adapter-level idempotency/reconciliation.
- **Self-approval or review contamination:** fresh review context, mandatory exclusions,
  context ID attestation, and persisted creator/reviewer identities.
- **Prompt-based policy bypass:** state machines and policy guards outside prompts.
- **Context substitution:** persisted ContextBundle hash and artifact binding.
- **Database history tampering:** append-only event triggers, migration checksums, file
  permissions, and external backups. A privileged local administrator remains trusted.
- **Path traversal or overwrite:** sandboxed path resolution, expected hash, overwrite
  policy, and atomic file replacement.
- **Malicious model-host output:** JSON parsing, size/time limits, closed envelope schemas,
  capability checks, and no shell invocation.
- **Stale workflow worker:** expiring lease and stale-finalizer rejection.
- **Secret leakage:** credentials excluded from LPOS state by policy; deployment secret
  manager required.

## Residual risks

A fully compromised operating-system account can read or alter local state. SQLite is not a
distributed consensus system. A remote provider can retain submitted content according to
its own policy. Real external systems may return uncertain outcomes after a timeout. These
risks require deployment controls beyond the core package.
