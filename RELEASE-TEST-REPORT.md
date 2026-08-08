# LPOS v4.8.0 Release Test Report

Date: 2026-08-08
Python: 3.11

## Results

- Focused managed-execution suite: `./.venv/bin/pytest -q -k managed_execution`, **6 passed, 0 failures**.
- Full repository suite on the final corrected candidate: `./.venv/bin/pytest -q -o addopts='' -r s`, **492 passed, 2 skipped, 0 failures**, with **2,026 subtests passed**, from **494 collected tests**.
- Release verification: **779 immutable files, 103 specialists, 29 Standing Operations, 70 benchmarks, and 28 schemas**.
- The versioned offline wheel is `Packages/lpos_os-4.8.0-py3-none-any.whl`.

## Managed-execution evidence

- The focused suite uses an executable fake Hermes CLI child and proves subprocess creation, deterministic checks, exact source/artifact hash binding, an independent reviewer identity, terminal capability gaps, bounded correction policy, consequential-tier authorization, and pre-child artifact-path confinement.
- Root and packaged copies of all three managed-execution schemas are byte-identical and strict.
- Prior execution receipts `LPOSX-44F2AC2A410F4B1A814D9E75A26991AC` and `LPOSX-A8EB5CC7667F45D68CA66400EFE9AF93` remain preserved as predecessor evidence.

## Evidence limits

- The focused subprocess test is deterministic integration evidence, not a paid-provider canary.
- No real paid-model canary was run for this candidate; exactly one remains reserved for the parent after commit.
- No publication, installation, activation, deployment, Drive operation, email, or Hermes-core modification was performed.
