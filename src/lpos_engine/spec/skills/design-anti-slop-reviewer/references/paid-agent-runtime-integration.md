# Paid-agent quality policy integration

Use this reference when a product claims that customer-facing agents inherit an operating system's writing or design standards.

## Audit the execution path, not the documentation

A skills page, prompt comment, or agent description does not prove runtime use. Trace every paid output through:

1. catalog or agent declaration
2. immutable job or configuration version
3. signed scheduler or execution envelope
4. worker run package and approved-skill list
5. model input or deterministic generator
6. output validator
7. independent-review record
8. delivery or publish gate

A missing quality policy at any boundary is a product defect. Do not report the capability as inherited merely because the website or operating-system documentation lists the skill.

## Required customer-facing quality set

For Listening Post and Chip paid output, carry these references explicitly:

- `voice-listeningpost`
- `commercial-copy-standard`
- `anti-slop-editor`
- `design-anti-slop-reviewer`
- `quality-router`
- `independent-reviewer`

Keep the policy versioned. Bind it into immutable and signed artifacts. A missing required skill must fail validation rather than generate a warning.

## Separate writing and visual gates

Text-only output can deliver after deterministic writing lint and required review pass.

Visual output must remain unpublishable until it has:

- zero deterministic blockers
- desktop and mobile viewport evidence
- task-order and interaction proof
- accessibility evidence
- named visual-pattern review
- independent review tied to the exact artifact

Owner approval and publish readiness are different states. It is acceptable to preserve owner approval while setting publish status to `quality_review_required`. Do not pretend a pending visual review passed.

## Website-generator safeguards

Do not improve sparse source data by inventing realistic-looking proof. Specifically avoid fallback ratings, review authors, testimonials, licenses, guarantees, years in business, response-time claims, or customer counts. Use explicit placeholders in drafts, and make placeholders deterministic publish blockers.

A safe generator should:

- derive ratings and proof only from source or owner-confirmed evidence
- label fixture or sample content visibly
- remove unsupported fallback claims
- lint rendered HTML, not only the source model
- preserve a pending visual-review state across edits
- recompute quality after every content or layout change
- require a fresh review when the generated artifact changes

## Release proof

For two-service products, build exact tagged images and deploy zero-traffic canaries. Point the gateway canary at the managed-service canary so integration proof exercises both candidate images. Verify public pages, paid-agent APIs, quality-policy fields, protected routes, and generated output before moving traffic.

If local container tooling is unavailable, use the configured remote image builder and retain the resulting image digest. The durable lesson is to verify the immutable container, not to record a local setup failure.

## Repository authority

A request to synchronize a product site with the active operating system authorizes product-side integration. It does not automatically authorize edits to a separately governed open-source operating-system repository. Report any source-package mismatch and obtain the required approval before changing that repository.
