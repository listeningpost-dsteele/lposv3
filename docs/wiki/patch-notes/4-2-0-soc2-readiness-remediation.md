---
title: "4.2.0 security audit and SOC 2 readiness remediation"
section: patch-notes
order: 1.5
---

# 4.2.0 security audit and SOC 2 readiness remediation

On July 22, 2026 an independent technical audit reviewed the LPOS v4.2.0 complete release archive.

## Verdict

The release is functionally healthy in record-only workflow testing, but it is not SOC 2 Type 2 compliant and it is not audit-ready as shipped.

The built-in compliance module must be treated as a control readiness diagnostic only. It must not be used as a CPA attestation, Type 2 report, or self-issued compliance result.

## Affected release

- Release: LPOS v4.2.0 complete distribution
- Audited archive SHA-256: `45d6cb6f1110c2c473b3a99f03bb22bd6d1f78dbf212deac434ff14fc23e8e69`
- Audit bundle SHA-256: `0de98c990836a1a4b8dbe720862c1134c3182cd7c05a9f69339031b457471706`
- Inner audit package SHA-256: `1033e077bc82a6b509986faff53d1ca23d117b325a7222f569edc176872b14d5`

## What worked

The audit confirmed the release had strong packaging and functional verification evidence:

- safe archive extraction
- release checksum verification
- wheel RECORD parity
- clean offline installation
- dependency consistency check
- database initialization and doctor check
- record-only end-to-end demonstration
- 196 automated tests and 338 subtests
- 53 deterministic evaluations
- Python compilation
- full semantic validation of all 17 JSON schemas when the validator was available

## Open findings

The audit identified 14 open findings:

- 2 Critical
- 7 High
- 4 Medium
- 1 Low

Release-blocking technical findings include false SOC 2 self-attestation, agent-to-shell monitor execution, credential exfiltration and SSRF, caller-forged approval identity, unauthenticated dashboard mutation, weak state-file permissions, and mutable evidence history.

## Immediate containment

Until the Critical and High findings are closed:

- Treat all SOC 2 output as readiness diagnostics only.
- Do not claim SOC 2 compliance or Type 2 effectiveness from LPOS output.
- Keep consequential integrations in record-only mode.
- Disable agent-defined command checks, shell alert transports, credentialed custom monitor URLs, and unrestricted health-check egress.
- Keep the dashboard loopback-only or disabled until authentication, CSRF, Host, Origin, session, and security-header controls are implemented.
- Create state directories as `0700` and sensitive files as `0600`.
- Do not use raw `MessageIdentity` objects for authorization.

## Patch status

The uploaded `patch.md` is a remediation change order and acceptance contract. It is not, by itself, an implemented source patch. A finding is closed only when its exploit reproduction fails safely on the patched build and the required regression tests pass.

## Validation commands

Operators and reviewers should use a disposable copy for exploit reproductions.

```bash
python verify_release.py
python -m pytest -q --disable-warnings -o addopts=""
lpos validate-schemas
lpos evals
python -m compileall -q src verify_release.py
```

The audit package also includes `evidence/reproduce_findings.py`, which is an adversarial harness for local isolated testing.

## SOC 2 boundary

This remediation does not constitute a SOC 2 Type 2 report. A Type 2 report requires a defined system description, management assertion, operating evidence over an auditor-agreed period, and a report issued by an independent licensed CPA.

## Related pages

- [SOC 2 Compliance Guild](/includes/soc2-compliance.html)
- [4.2.0](/patch-notes/4-2-0.html)
- [Upgrading](/administration/upgrading.html)
