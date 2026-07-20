# Benchmark Fixture Standard

A fixture is a fixed, repeatable benchmark case (LPOS-016). Unlike the
scenario templates in BENCHMARKS.md, a fixture never asks the evaluator to
invent a request: inputs are pinned, expectations are explicit, and evaluation
is assertable.

Each fixture directory contains `fixture.yaml` with required fields:
`id`, `component`, `inputs`, `expected` (required and prohibited),
`evaluation` (method, assertions, threshold), and `evidence`.

Coverage policy: every specialist and Standing Operation ultimately needs at
least one fixture. Current coverage is reported by `Tests/verify_compact.py`
and enforced as a floor that may only rise. Adding a fixture for an uncovered
component is always accepted work; removing one is a release blocker.

Model promotion (SO-016) runs candidates against fixtures, never against
invented tasks.
