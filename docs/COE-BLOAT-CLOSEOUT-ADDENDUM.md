# LPOS COE Bloat Repair Closeout Addendum

Status: Approved
Target: LPOS v4.5.0 and later

## Mission

Continuous Operational Excellence prevents recurrence of operational bloat. Every defect class discovered becomes a durable engineering rule, deterministic validation, or recurring audit.

## Constitutional Principle XI: Operational Sustainability

LPOS preserves long-term operational health by preventing unnecessary data, artifacts, workflows, prompts, releases, backups, scheduler fixtures, compatibility layers, and technical debt.

Every persistent artifact must have:

- Owner
- Purpose
- Lifecycle
- Retention policy
- Verification
- Retirement plan

## Daily audit domains

The executable `lpos coe audit` command evaluates:

1. Release integrity: immutable manifest, checksums, verifier result, and shipping tree.
2. Backup governance: total size, file count, nested backups, retention limits, and secret-bearing files.
3. Scheduler governance: duplicate, paused, orphaned, legacy, fixture, and low-value scheduled work.
4. Wake-agent efficiency: frequent recurring work must be deterministic or use a `wakeAgent=false` preflight.
5. Prompt drift: obsolete version references and deprecated operating guidance.
6. Mutable versus immutable boundaries: mutable state cannot live in an immutable release tree.
7. Storage efficiency: repository, release, cache, backup, and retention growth.
8. Technical debt lifecycle: every compatibility layer needs an owner, rationale, retirement date, migration plan, and status.
9. Documentation audit: required operator, architecture, testing, backup, and CLI documents.
10. Engineering, security, bloat, opportunity, and release-readiness synthesis.

## Release gate

Before release, run:

```bash
lpos coe release-gate \
  --repo /path/to/release \
  --hermes-root ~/.hermes \
  --state-root ~/.local/state/lpos
```

The release gate executes immutable release verification, all COE audit domains, and the packaged deterministic evaluation suite. Critical failures block release.

## Dashboard and report contract

Each audit writes only to the configured mutable state root:

- `coe/latest.json`
- `coe/history.jsonl`
- `coe/report.md`
- `coe/daily-email.md`
- `coe/dashboard.html`

The local dashboard is served at `http://127.0.0.1:7374/dashboard/coe` by default. `daily-email.md` contains the required subject, executive summary, findings, risks, dashboard URL, timestamp, release version, audit ID, and full appendix. Delivery remains an explicit deployment integration because LPOS does not embed credentials or bypass Principal communication controls.

## Engineering rule

Historical behavior is not preserved only because it exists. Every behavior must continue to justify its operational value.

## Pass-off map

This approved addendum is integrated into:

- Constitution and kernel: `src/lpos_engine/spec/CHIP-KERNEL.md`
- Operating system: `src/lpos_engine/coe.py` and `lpos coe`
- Wiki and operations manual: `docs/wiki/administration/continuous-operational-excellence.md`
- Developer guide: `docs/ARCHITECTURE.md` and `docs/TESTING.md`
- Release notes: `CHANGELOG.md` and `docs/wiki/patch-notes/4-5-0.md`
- Next full build: release manifest and checksums include every COE implementation and document
- GitHub and Google Drive: the ordinary approved publication workflow distributes the frozen release after the Principal ships it
