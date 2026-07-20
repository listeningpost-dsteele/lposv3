# LPOS v4 Model-Host Adapter Protocol

`SubprocessModelAdapter` connects the deterministic LPOS control plane to any configured
model host. LPOS invokes an argument-vector command directly with `shell=False`, sends one
JSON object on standard input, and expects one JSON object on standard output.

The host process owns provider credentials, model selection, network access, rate-limit
handling, and provider-specific behavior. LPOS owns context assembly, capability checks,
timeouts, output limits, envelope validation, persistence, and policy enforcement.

## Creation request

```json
{
  "operation": "create_artifact",
  "task": {"task_id": "TASK-..."},
  "context": {"bundle_id": "CTX-...", "bundle_hash": "...", "content": "..."}
}
```

The host returns a ModelOutput:

```json
{
  "content": "artifact text",
  "media_type": "text/plain",
  "evidence": ["source or verification reference"],
  "assumptions": [],
  "adapter_metadata": {"model": "deployment-defined"}
}
```

## Review request

```json
{
  "operation": "review",
  "review_envelope": {"brief": "...", "artifact": {}},
  "context": {"bundle_id": "RCTX-...", "bundle_hash": "...", "content": "..."}
}
```

The host returns a ReviewResult with `decision`, `isolation`, `recomputed`, gate findings,
corrections, strengths, and evidence reviewed. The `isolation` value must attest to the
exact review context ID supplied by LPOS.

## Required adapter metadata

A registered adapter declares:

- name
- supported model classes
- normalized capability tokens
- creation and review support
- local or remote execution
- deterministic priority
- current availability

LPOS rejects an adapter that lacks required metadata, does not cover the task capabilities,
violates a local-only constraint, returns invalid JSON, exceeds output limits, times out, or
returns an invalid envelope.

See `examples/example_model_host.py` for a deterministic executable example.
