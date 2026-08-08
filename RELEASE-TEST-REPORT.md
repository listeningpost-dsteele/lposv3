# LPOS v4.8.0 Release Test Report

Date: 2026-08-08
Python: 3.11

## Results

- Focused managed-execution suite: `./.venv/bin/pytest -q -k managed_execution`, **10 passed, 0 failures**.
- Full repository suite on the final corrected candidate: `./.venv/bin/pytest -q -o addopts='' -r s`, **496 passed, 2 skipped, 0 failures**, with **2,026 subtests passed**, from **498 collected tests**.
- Release verification: **779 immutable files, 103 specialists, 29 Standing Operations, 70 benchmarks, and 28 schemas**.
- The versioned offline wheel is `Packages/lpos_os-4.8.0-py3-none-any.whl`.

## Managed-execution evidence

- The focused suite uses an executable fake Hermes CLI child and proves subprocess creation, deterministic checks, exact source and artifact hash binding, a distinct reviewer identity, terminal capability gaps, bounded correction policy, consequential-tier authorization, pre-child artifact-path confinement, malformed-receipt correction, and clean termination at the correction limit.
- Root and packaged copies of all three managed-execution schemas are byte-identical and strict.
- Prior execution receipts `LPOSX-44F2AC2A410F4B1A814D9E75A26991AC` and `LPOSX-A8EB5CC7667F45D68CA66400EFE9AF93` remain preserved as predecessor evidence.
- Real managed run `MRUN-9FC398FD997643F2` used the installed Hermes CLI and the exact Integration Engineer role to create the correct repository artifact. It stopped before review because the creator wrote an absolute receipt artifact path. The failed run and evidence are preserved under `/tmp/lpos480-managed-state`.
- Correction execution `LPOSX-54A58EBDF2AE4C4DB7AA034C3A46C0ED` required strict relative receipt paths and one bounded correction. Commit `38a583ce4c7188d9d899057b328bf7e559a6b48c` implemented that correction. The final focused suite reproduces the exact absolute-path defect and proves one corrected continuation reaches review while repeated invalid receipts terminate cleanly.

## Evidence limits

- The real managed canary proved specialist file and terminal access, artifact creation, and contribution receipt generation. It did not reach live independent review or a completion latch before exposing the corrected receipt defect.
- No second paid-model canary was run after correction, as required by the bounded correction handoff. Final qualification therefore combines the preserved real execution evidence with deterministic reproduction of the corrected path and fresh-context review of the exact final source.
- No publication, installation, activation, deployment, Drive operation, email, or Hermes-core modification had occurred when this report was written.
