---
title: SOC 2 Compliance Guild
section: includes
order: 6
---

# SOC 2 Compliance Guild

The SOC 2 Compliance Guild (GUILD-038) makes compliance a property of the operating
system rather than a project someone remembers to do. It codifies the AICPA Trust
Services Criteria, the 2017 TSC with the revised 2022 points of focus: the common
criteria series CC1 through CC9 plus the optional Availability, Confidentiality,
Processing Integrity, and Privacy categories, as a machine-checkable control catalog in
`lpos_engine.compliance`, and runs it autonomously every day as SO-025.

"Type 2" is the part most compliance tooling gets wrong: a Type 2 report is about
operating effectiveness **over an observation period**, not a point-in-time snapshot.
The guild is built around that: every control run appends to an evidence history, and
each control earns its "effective" verdict only by passing consistently across the
90-day observation window. One green run proves very little, and the report says so.

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

`~/.hermes/compliance/report.html` is a self-contained page with the status hero (overall
state, window coverage, control counts), **The Problems** (each failing control, its TSC
criterion, the risk in plain language, and the evidence), **The Fixes** (each staged
remediation, where it lives in the test environment, its validation result, and its
adoption status), the **Audit Log** of every check run and remediation staged, and the
full **Control Matrix** by TSC series with effectiveness meters.

## Running it yourself

```bash
lpos compliance audit    # run the full control audit now
lpos compliance report   # regenerate the HTML page
lpos compliance status   # print status.json
```

State lives in `~/.hermes/compliance/`: `status.json` (the stable contract, also read by
the dashboard), `history.jsonl` (the Type 2 evidence ledger), `report.html`, and
`staging/`. See `docs/COMPLIANCE.md` in the repository for the full control table.

## An honest boundary

This guild demonstrates and enforces controls over the LPOS system itself and produces
the evidence trail an auditor would ask for. It is not an attestation: a SOC 2 Type 2
report is issued by an independent CPA firm after examining an observation period.

## Related pages

- [Connector Health Monitor](/includes/connector-health-monitor.html)
- [Checking system health](/working-with/checking-system-health.html)
- [How this wiki works](/documentation/how-the-wiki-works.html)
