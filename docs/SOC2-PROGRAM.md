# SOC 2 Program Scaffolding (LPOS-13)

The v4.2.0 audit's LPOS-13 finding is correct and cannot be closed by code: a SOC 2
Type 2 examination covers the *service organization* — its described system, people,
and operating evidence over a period — not a software archive. This document is the
scaffolding the organization fills in and operates. The control readiness monitor
(SO-025) tracks the technical half; everything below is the organizational half it
reports as "requires organizational evidence".

## 1. System description (AICPA Description Criteria) — to be completed

| Element | Owner | Content to supply |
|---|---|---|
| Service and boundaries | Principal | What the LPOS-based service is, for whom, and where the system boundary sits (which machines, which Hermes roots, which connectors). |
| Infrastructure & software | Principal | Hosts, OS versions, LPOS version, connectors/subservice organizations (email provider, GitHub, cloud, Drive). |
| People | Principal | Roles: operator, approver (Principal), reviewer; screening and training. |
| Data | Principal | Data classes handled per project; classification, retention, disposal. |
| Commitments & system requirements | Principal | What is promised to customers/users; availability and confidentiality commitments. |
| Complementary user-entity controls | Principal | What users of the service must do themselves. |

## 2. Control register — organizational controls to design and operate

Each row needs: owner, frequency, evidence source, retention, reviewer, exception
workflow. Machine-checkable rows already exist in `lpos_engine.compliance.controls`;
these are the human ones the monitor lists as not machine-checkable:

| Register ID | TSC | Control to operate | Evidence to retain |
|---|---|---|---|
| ORG-CC1-01 | CC1 | Governance oversight: periodic review of system operation and this register | Dated review notes in the evidence ledger |
| ORG-CC1-02 | CC1 | Personnel: screening, onboarding/offboarding (JML), role assignment | Records per person |
| ORG-CC3-01 | CC3 | Risk register maintained and reviewed on a schedule | Register + review dates |
| ORG-CC4-01 | CC4 | Independent evaluation of controls (not the self-monitor) | Reviewer reports |
| ORG-CC6-01 | CC6 | Periodic access reviews of accounts, keys, connectors | Review checklists, revocations |
| ORG-CC7-01 | CC7 | Incident response: documented process, at least one exercise per period | Incident/exercise records |
| ORG-CC7-02 | CC7 | Vulnerability and patch management operating on a cadence | Tickets, patch logs |
| ORG-CC8-01 | CC8 | Change authorization: review/approval evidence per release (SO-022 records the gate; a human authorizes) | Approved release records |
| ORG-CC9-01 | CC9 | Vendor / subservice organization oversight (email, GitHub, cloud, Drive) | Vendor reviews, SOC reports collected |
| ORG-A-01 | A | Backup schedule operated; restore exercised; RPO/RTO defined | Backup logs, restore-drill results |
| ORG-C-01 | C | Data classification, retention, and secure disposal operated | Classification policy, disposal records |
| ORG-P-01 | P | Privacy scope decision (in or out); if in: notices, consent, rights handling | Privacy program records |

## 3. Evidence and period

Type 2 requires operating evidence across the agreed observation period (typically
6–12 months). The evidence ledger (hash-chained `compliance/history.jsonl` plus the
append-only event store, both verifiable with `python -m lpos_engine.compliance verify`
and `lpos doctor`) is the technical record; organizational evidence lives with each
register row above. Export checkpoints off-host (see `store.export_jsonl` and the
checkpoint-key mechanism) so evidence integrity does not depend on the machine it
describes.

## 4. Path to the report

1. Complete §1 and stand up §2 with owners and frequencies.
2. Operate everything; let SO-025 and the register accumulate the period's evidence.
3. Engage a licensed independent CPA for a readiness assessment; agree scope, period,
   and sampling.
4. Remediate exceptions; then the CPA performs the Type 2 examination and issues the
   report. Only then may the organization state it holds a SOC 2 Type 2 report.
