---
name: code-test-gauntlet
description: Run the criticality-weighted LPOS code testing gauntlet before release.
author: Listening Post
license: MIT
---

# Code Test Gauntlet

Use only for executable software and code changes.

1. Inspect the repository and testing manifest.
2. Run the Need-to-Change Gate.
3. Classify LIGHT, STANDARD, HIGH, or CRITICAL.
4. Create or validate the behavior contract.
5. Freeze reviewed acceptance behavior when required.
6. Run required test streams and deterministic gates.
7. Do not allow implementation to weaken tests.
8. Produce exact command evidence.
9. Route evidence to the Release Verification Auditor.

Return PASS, REJECT, or NO_CHANGE_REQUIRED.

Never report PASS when a required command did not run.
