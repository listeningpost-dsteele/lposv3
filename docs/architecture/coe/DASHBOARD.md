# COE Dashboard

Release: LPOS 4.5.0

The canonical private page is `https://chip.listeningpost.ai/dashboard/coe`. `/ops/coe` redirects to the canonical path.

The dashboard requires operator authentication and returns private, no-store responses. It reads persisted audits and release decisions. It cannot run gates or change release readiness.

## Required fields

1. Overall Health Score.
2. Engineering Score.
3. Security Score.
4. Efficiency Score.
5. Cost Score.
6. Documentation Score.
7. Release Integrity.
8. Scheduler Health.
9. Wake-Agent Efficiency.
10. Prompt Drift.
11. Technical Debt.
12. Opportunity Backlog.
13. Release Readiness.
14. Top Risks.
15. Pending Approvals.
16. Recent Improvements.
17. Audit History.
18. Current Release Status.

It also exposes release version, Git commit, build ID, audit ID, update time, report delivery, restore evidence age, and storage trends. Missing data renders as unknown. Failed or incomplete gate data renders as blocked.

Private API endpoints live under `/api/v1/coe`. Operator opportunity decisions are validated and persisted append-only. The legacy operator release-gate endpoint renders the latest persisted COE decision.
