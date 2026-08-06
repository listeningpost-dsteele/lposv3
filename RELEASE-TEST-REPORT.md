# LPOS v4.7.0 Release Test Report

Date: 2026-08-06
Python: 3.11

## Results

- Full suite on the 4.7 candidate: `python -m pytest -q`, **485 passed, 2 skipped, 0 failures** from **487 collected tests**.
- Focused admission, publication, and packaged-quality contracts: **75 passed, 0 failures**.
- Release verification: **769 immutable files, 103 specialists, 29 Standing Operations, 70 benchmarks, and 25 schemas**.
- Doctor reports LPOS 4.7.0 healthy after resealing.
- The versioned offline wheel is `Packages/lpos_os-4.7.0-py3-none-any.whl`.

## Behavioral qualification

A one-pass GLM 4.5 Air sample tested one specialist from each of the 20 guilds against a capable generic baseline, followed by blinded judging with no retries:

- Specialist wins: **16**
- Ties: **1**
- Generic-baseline wins: **3**
- Specialist win rate: **80%**
- Specialist average: **72.35**
- Generic baseline average: **44.65**

The raw harness gate returned FAIL because four generated positive cases demanded completed artifacts while withholding inputs that the governing specialist charters require. In all four, the specialist preserved evidence discipline and refused to fabricate the missing inputs; the generic baseline produced an invented template or artifact. These failures remain recorded as admission-oracle defects and were not hidden or used to weaken the prompts.

## Release scope

- The expert capability corpus contains 20 guild charters, 103 specialist charters, 122 craft standards, and 103 frozen admission suites.
- The active registry binds all 103 specialists to guild and craft-standard prompts.
- Product Studio is absent and remains deferred.
- External actions remain record-only by default.
- No repository push or public site publication was performed as part of this local release activation.
