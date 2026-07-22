---
title: SOC 2 Compliance Guild
section: includes
order: 6
---

# SOC 2 Compliance Guild

> **Security audit update, July 22, 2026:** LPOS v4.2.0's built-in compliance output is a readiness diagnostic, not a SOC 2 attestation. An independent audit found that the v4.2.0 self-audit could falsely report compliance and control effectiveness from insufficient history. See [4.2.0 security audit and SOC 2 readiness remediation](/patch-notes/4-2-0-soc2-readiness-remediation.html).

The SOC 2 Compliance Guild (GUILD-038) makes compliance a property of the operating
system rather than a project someone remembers to do. It codifies the AICPA Trust
Services Criteria, the 2017 TSC with the revised 2022 points of focus: the common
criteria series CC1 through CC9 plus the optional Availability, Confidentiality,
Processing Integrity, and Privacy categories, as a machine-checkable control catalog in
`lpos_engine.compliance`, and runs it autonomously every day as SO-025.

"Type 2" is the part most compliance tooling gets wrong: a Type 2 report is about
operating effectiveness **over an observation period**, not a point-in-time snapshot.
The v4.2.0 implementation did not enforce that boundary correctly. Treat every built-in
result as a readiness signal until a remediated build passes the adversarial regression
suite and, separately, an independent CPA issues the applicable report.

## The autonomous loop

Each scheduled run of [SO-025](/reference/so-025.html) does four things. It enumerates
the codified control catalog (21 controls mapped to the TSC series). It audits every
control against the actual system, each result carries evidence naming the exact files
and values inspected, which is the proof. For anything failing, it builds the fix in the
**staging test environment** (`~/.hermes/compliance/staging/`), a copy, with a
remediation note and a validation result, so nothing you're working on breaks; the
stager refuses live paths by construction, and a staged fix enters the main system only
through exact-action Principal approval. Finally it publishes the compliance page.

## The compliance page

`~/.hermes/compliance/report.html` is a self-contained readiness page with the status
hero, control counts, gaps, staged remediation, and the control matrix by TSC series.
In v4.2.0, do not rely on this page for SOC 2 compliance or Type 2 effectiveness claims.

## Running it yourself

```bash
lpos compliance audit    # run the full control audit now
lpos compliance report   # regenerate the HTML page
lpos compliance status   # print status.json
```

State lives in `~/.hermes/compliance/`: `status.json` (the stable contract, also read by
the dashboard), `history.jsonl` (local readiness history), `report.html`, and `staging/`.
In v4.2.0 this local history is not independently tamper-evident evidence. See
`docs/COMPLIANCE.md` in the repository for the full control table.

## An honest boundary

This guild maps controls over the LPOS system and can support readiness work. It is not
an attestation: a SOC 2 Type 2 report is issued by an independent CPA firm after
examining a defined system and observation period.

## Related pages

- [Connector Health Monitor](/includes/connector-health-monitor.html)
- [Checking system health](/working-with/checking-system-health.html)
- [How this wiki works](/documentation/how-the-wiki-works.html)
