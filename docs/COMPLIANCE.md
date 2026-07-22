# LPOS Compliance Engine — SOC 2 Type 2 (SO-025)

The compliance guild's operating doc for the packaged SOC 2 Type 2 compliance
engine: `src/lpos_engine/compliance/`, run as Standing Operation **SO-025**.

## The codified framework

The engine audits against the AICPA **2017 Trust Services Criteria** with the
**revised 2022 points of focus**, encoded as data in
`src/lpos_engine/compliance/criteria.py`:

- Common criteria **CC1–CC9** (control environment; communication and
  information; risk assessment; monitoring of controls; control activities;
  logical and physical access; system operations; change management; risk
  mitigation) — these are the Security category and apply to every SOC 2 scope.
- Optional categories **A** (availability), **C** (confidentiality),
  **PI** (processing integrity), **P** (privacy — encoded, marked out of scope:
  no machine-checkable privacy control ships yet).

**Type 2 vs Type 1.** A Type 1 report assesses control *design* at a point in
time. A Type 2 report assesses *operating effectiveness over an observation
period*. The engine therefore keeps an append-only run history per control and
computes an effectiveness ratio over `OBSERVATION_WINDOW_DAYS` (default **90**),
rather than reporting only the current snapshot.

## The control catalog

21 machine-checkable controls in `src/lpos_engine/compliance/controls.py`.
Every check runs offline against the release checkout (`repo_root`) and the
Hermes runtime root (`hermes_root`); a missing file is a failing control with
evidence saying why, never a crash. Evidence cites the exact files and values
inspected.

| Control | TSC | Category | What it checks |
| --- | --- | --- | --- |
| CTRL-CC1-01 | CC1 | standard | `spec/LPOS-CORE.md` + `spec/GUILDS.md` present and substantive |
| CTRL-CC1-02 | CC1 | standard | `NOTICE*` attribution files at the repo root |
| CTRL-CC2-01 | CC2 | standard | `README.md`; `docs/wiki` with patch-notes pages |
| CTRL-CC3-01 | CC3 | standard | `docs/THREAT-MODEL.md` + `docs/SECURITY.md` present, non-trivial |
| CTRL-CC4-01 | CC4 | standard | SO-024 docs drift audit wired in the workflow catalog |
| CTRL-CC4-02 | CC4 | standard | SO-025 workflow ships (catalog wiring tolerated as pending) |
| CTRL-CC5-01 | CC5 | critical | `tests/` carries ≥100 test functions |
| CTRL-CC5-02 | CC5 | standard | 53 `BENCH-*.json` fixtures match `RELEASE.json` benchmarks |
| CTRL-CC6-01 | CC6 | critical | dashboard `DEFAULT_HOST` is loopback (`127.0.0.1`) |
| CTRL-CC6-02 | CC6 | critical | `approvals.py` ships and `engine.py` wires `ApprovalService` |
| CTRL-CC6-03 | CC6 | critical | no plaintext secrets in repo `config/` or Hermes state (AKIA…, ghp\_…, sk-…, inline `"password"`) |
| CTRL-CC6-04 | CC6 | standard | `monitor/smtp.json` uses `password_file`, never an inline password |
| CTRL-CC7-01 | CC7 | standard | SO-023 connector monitor cataloged hourly (`0 * * * *`) |
| CTRL-CC7-02 | CC7 | standard | `monitor/status.json` fresh within 2h (pre-runtime: catalog wiring suffices, evidence "no runtime yet") |
| CTRL-CC7-03 | CC7 | critical | `events` table with `events_no_update`/`events_no_delete` ABORT triggers (append-only audit trail) |
| CTRL-CC8-01 | CC8 | critical | CHANGELOG entry for the `RELEASE.json` version; manifest, SHA256SUMS, `verify_release.py` present |
| CTRL-CC8-02 | CC8 | standard | SO-022 cataloged with `STEP-DOCS-GATE` (docs-gated publication) |
| CTRL-CC9-01 | CC9 | standard | rollback documented in `upgrading.md`; release wheel retained under `Packages/` |
| CTRL-A-01 | A | standard | `store.py` `integrity_check()` (PRAGMA integrity\_check); backups doc present |
| CTRL-C-01 | C | critical | `RELEASE.json` `external_action_default: record-only`; subprocess adapter boundary documented |
| CTRL-PI-01 | PI | critical | `operations.py` idempotency keys, frozen outputs, canonical digest |

## How the autonomous loop works

SO-025 (`src/lpos_engine/workflows/SO-025.json`, model class `routine`,
suggested schedule daily at 06:00) runs four steps:

1. **STEP-INVENTORY** (`inventory_compliance_controls`) — the framework
   summary and control catalog.
2. **STEP-AUDIT** (`audit_compliance_controls`) — runs every control, appends
   one line per result to `history.jsonl`, computes Type 2 effectiveness, and
   atomically writes `status.json`.
3. **STEP-REMEDIATE** (`stage_compliance_remediation`) — for each failing
   control, stages a **test environment** copy of the affected files under
   `staging/<run_id>/<control_id>/` with a `REMEDIATION.md` and a
   `validation.json`, and emits a **record-only adoption plan**
   (`{mode: "record-only", approval_required: true, actions: [...]}`). Staging
   refuses (ValidationError) any path inside the repo checkout, outside the
   compliance staging directory, or containing live/production tokens.
   Remediation **never writes to live system files**.
4. **STEP-REPORT** (`publish_compliance_report`) — renders `report.html`.

Adoption is **approval-gated**: the exact-action plan (action ids like
`ADOPT-CTRL-CC8-01-<run>`) flows through the normal LPOS-030 exact-action
approval mechanism before any staged fix moves into the main system. The
engine itself never adopts.

On demand: `python -m lpos_engine.compliance audit|report|status`
(`--root` Hermes root, `--repo` release checkout).

## Where state lives

Everything under `<hermes root>/compliance/`:

- `history.jsonl` — append-only check/staging history, capped at 10,000 lines
  (oldest trimmed). Check lines: `{ts, event: "check", control_id, passing, evidence}`.
- `status.json` — the stable status contract (below).
- `report.html` — the self-contained HTML report.
- `remediations.json` — the latest staged remediation plan.
- `staging/<run_id>/<control_id>/` — test-environment copies + `REMEDIATION.md`
  + `validation.json`.

## The status.json contract

```json
{
  "generated_at": "2026-07-22T06:00:00+00:00",
  "framework": "SOC 2 Type 2 (TSC 2017, 2022 POF)",
  "window_days": 90,
  "overall": "compliant" | "gaps",
  "coverage": {"days_of_history": 0, "runs_in_window": 21},
  "controls": [
    {
      "control_id": "CTRL-CC8-01", "tsc_id": "CC8", "title": "...",
      "category": "critical", "passing": true, "evidence": "...",
      "details": {},
      "runs_in_window": 90, "passes_in_window": 90,
      "effectiveness": 1.0, "verdict": "effective"
    }
  ],
  "summary": {"total": 21, "passing": 21, "failing": 0,
              "effective": 21, "not_yet_demonstrated": 0, "ineffective": 0}
}
```

Verdicts: **effective** = in-window pass ratio ≥ 0.98 *and* the current run
passes; **ineffective** = the current run fails; **not yet demonstrated** =
currently passing but the window has not shown a sustained ≥ 0.98 pass rate.
`overall` is `compliant` only when every control currently passes.

## How to read the HTML page

`report.html` is one self-contained page (inline CSS, no external assets,
dark mode via `prefers-color-scheme`), top to bottom:

1. **Status hero** — overall COMPLIANT / GAPS FOUND, days of the 90-day window
   covered, runs in window, and effective / not-yet-demonstrated / failing counts.
2. **The Problems** — each failing control: what it is, its TSC criterion,
   the risk in plain language, and the evidence of failure.
3. **The Fixes** — each staged remediation: the proposed fix, the staged
   test-environment location, the honest validation result, and the adoption
   status (awaiting approval until the Principal approves the exact action).
4. **Audit Log** — reverse-chronological table (last 200 shown) of every check
   run and every remediation staged.
5. **Control Matrix** — all controls grouped by TSC series with PASS/FAIL
   chips (words, not just color) and pure-CSS effectiveness meters per group.

## Honest limitations

- This engine **demonstrates and enforces controls over the LPOS system
  itself**. It is **not an attestation**: a SOC 2 Type 2 report is issued by an
  independent CPA firm after an observation period, based on its own testing.
- Checks are structural proofs against the shipped tree and runtime state.
  They verify that controls exist and operate, not that they are sufficient
  for any particular customer's scope.
- The secrets scan is pattern-based (AWS keys, GitHub tokens, `sk-` API keys,
  inline passwords) over text config/state files; it cannot find every secret.
- Effectiveness verdicts are only as strong as the history window: a fresh
  install shows a mathematically perfect ratio over very few runs. Coverage
  (days of history vs the 90-day window) is displayed for exactly this reason.
- Staged remediation baselines record the *pre-fix* state; a fix is proven
  only when the cited check passes against the edited staged copy, and adopted
  only through the approval flow. The privacy (P) category ships as codified
  framework text with no machine checks yet.
