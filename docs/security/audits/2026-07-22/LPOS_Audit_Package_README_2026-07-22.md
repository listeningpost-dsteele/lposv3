# LPOS v4.2.0 Compliance Audit Package

Audit date: July 22, 2026

## Verdict

The supplied release is functionally healthy in its bundled record-only workflow, but it is not SOC 2 Type 2 compliant or audit-ready as shipped. The package contains a point-in-time technical readiness assessment, not a SOC examination or CPA opinion.

## Target

- Input: `LPOS-v4.2.0-Complete.zip`
- Input SHA-256: `45d6cb6f1110c2c473b3a99f03bb22bd6d1f78dbf212deac434ff14fc23e8e69`
- Original release modified by the audit: No
- Test environment: Linux x86_64, Python 3.13.5

## Contents

- `LPOS_Compliance_Audit_Report_2026-07-22.pdf`: formatted 26-page report.
- `LPOS_Compliance_Audit_Report_2026-07-22.md`: searchable source report.
- `LPOS_Audit_Summary_2026-07-22.json`: machine-readable verdict, findings, and readiness matrix.
- `evidence/`: release verification, tests, evaluations, coverage, clean-install output, self-audit output, static inventory, and confirmed local-only reproductions.
- `report_quality/`: PDF inspection and preflight results.
- `SHA256SUMS.txt`: checksums for every package file except the checksum file itself.

## Reproduction safety

`evidence/reproduce_findings.py` is an audit harness, not an ordinary unit test. It uses temporary local fixtures, loopback HTTP listeners, canary credentials, and canary shell commands to demonstrate control failures. Review the script before execution and run it only in an isolated test environment against a disposable copy. It does not require internet access or real credentials.

## Integrity verification

From this directory, run:

```sh
sha256sum -c SHA256SUMS.txt
```

## Assurance limitation

This package supports remediation and SOC 2 readiness planning. A SOC 2 Type 2 report requires an examination by a licensed independent CPA of a defined service-organization system and the design and operating effectiveness of controls over an agreed period.
