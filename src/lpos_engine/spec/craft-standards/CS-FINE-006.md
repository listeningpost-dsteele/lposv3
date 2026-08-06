---
id: CS-FINE-006
title: Financial Model Integrity and Review Standard
version: 1.0.0
status: Accepted
owner: Listening Post
---

<!-- Generated from LPOS expert corpus v1.2, source SHA-256 fcc787db6f8ab0be691f9030af927005a005561db1c0fecdee5f6dbdc87a060f, source lines 26625-26646. Runtime lifecycle is governed separately. -->

# Financial Model Integrity and Review Standard

Every material model records exact revision, creator, reviewer, decision, scope, currency, units, periods, source ledger, assumption ledger, formula map, scenarios, exclusions, reconciliations, sensitivities, limitations, and disposition.

Review the exact executable artifact. Inspect formulas, units, periods, signs, hidden constants, copied values, scenario isolation, currency conversion, duplicate benefits, omitted costs, and source reconciliation.

For high-consequence calculations, independently recalculate material outputs or implement a second calculation path. Reading the creator's explanation is not independent verification.

A green spreadsheet, notebook, or script execution does not prove that definitions, sources, or assumptions are valid. Model review and domain review are both required.
