# Managed execution

LPOS 4.8 adds a bounded local execution path for work that needs an exact LPOS specialist and a tool-capable Hermes child.

`lpos managed-run` binds one creator specialist, a different reviewer specialist, an exact Git worktree and optional expected HEAD, a relative artifact path, deterministic checks, a risk-tier tool allowlist, and preserved prior receipts. It stores machine-readable preflight, process, check, contribution, review, and terminal-state evidence under `.lpos-managed/` by default.

A run completes only when the creator writes the declared artifact and a hash-bound contribution receipt, every configured check passes, and the independent reviewer returns a PASS bound to the exact artifact and source hashes. Capability gaps are terminal. Reviews may request at most two consolidated correction cycles.

Consequential execution is denied unless `--risk-tier consequential` and `--authorize-consequential` are both supplied. That flag authorizes the tier only; it does not bypass LPOS approval controls or enable publication, deployment, email, purchase, deletion, or other external actions.

The three managed receipt/state schemas are shipped in both `schemas/` and `lpos_engine.schemas` and are byte-identical, strict JSON Schema 2020-12 contracts.
