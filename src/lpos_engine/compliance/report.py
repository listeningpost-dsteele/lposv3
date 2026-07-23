"""The control readiness report: one self-contained HTML page.

No CDNs, no external assets, no chart libraries. Inline CSS only, system font
stack, dark mode via ``prefers-color-scheme``, one calm accent -- the same
tone as the Hermes dashboard (``dashboard/ui.py``). Every value is HTML-escaped
and every signal is carried by words as well as color.

This page is a SELF-ASSESSMENT (audit finding LPOS-01): it never renders
"compliant" or "effective" as self-determined states. A zero-day fresh run
reads NOT ASSESSED / INSUFFICIENT EVIDENCE, never green, and the standing
banner states that a SOC 2 Type 2 report is issued by an independent CPA.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from html import escape
from pathlib import Path
from typing import Any

AUDIT_LOG_DISPLAY_CAP = 200

_CSS = """
:root {
  --bg: #f4f4f2; --surface: #ffffff; --surface-2: #ececea; --border: #dcdcd8;
  --text: #1f2125; --text-dim: #6b6f76; --accent: #3b6ea5; --accent-soft: #e7eef6;
  --bad: #a53b3b; --bad-soft: #f6e7e7; --good: #3b7a4e; --good-soft: #e9f3ec;
  --warn: #9a6b1f; --warn-soft: #f6efe0;
  --radius: 8px; --shadow: 0 1px 2px rgba(20,22,26,.06);
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #17181b; --surface: #1f2126; --surface-2: #26282e; --border: #33363d;
    --text: #e6e7e9; --text-dim: #9a9ea6; --accent: #6ea8dc; --accent-soft: #24303d;
    --bad: #d87a7a; --bad-soft: #3a2626; --good: #7ac48f; --good-soft: #24352a;
    --warn: #d9b36a; --warn-soft: #383021;
    --shadow: 0 1px 2px rgba(0,0,0,.35);
  }
}
* { box-sizing: border-box; }
body {
  margin: 0; background: var(--bg); color: var(--text);
  font: 14px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
        "Helvetica Neue", Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
}
main { max-width: 960px; margin: 0 auto; padding: 24px 20px 60px; }
h1 { font-size: 20px; font-weight: 650; margin: 0 0 4px; }
h2 {
  font-size: 13px; font-weight: 600; letter-spacing: .05em; text-transform: uppercase;
  color: var(--text-dim); margin: 36px 0 12px; border-bottom: 1px solid var(--border);
  padding-bottom: 6px;
}
h3 { font-size: 14px; font-weight: 600; margin: 0 0 6px; }
.card {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius); box-shadow: var(--shadow);
  padding: 14px 16px; margin-bottom: 10px;
}
.banner {
  border: 1px solid var(--warn); background: var(--warn-soft); color: var(--text);
  border-radius: var(--radius); padding: 10px 14px; margin-bottom: 12px;
  font-size: 13px;
}
.hero { display: flex; flex-wrap: wrap; gap: 24px; align-items: baseline; }
.hero .overall { font-size: 26px; font-weight: 700; }
.hero .overall.ready { color: var(--good); }
.hero .overall.gaps { color: var(--bad); }
.hero .overall.warn { color: var(--warn); }
.period { font-size: 15px; font-weight: 650; margin-top: 8px; }
.period.warn { color: var(--warn); }
.period.good { color: var(--good); }
.stat { display: inline-block; margin-right: 18px; }
.stat b { font-size: 18px; }
.dim { color: var(--text-dim); font-size: 12px; }
.chip {
  display: inline-block; padding: 1px 9px; border-radius: 10px;
  font-size: 11px; font-weight: 600; margin-left: 6px; vertical-align: middle;
}
.chip.pass { background: var(--good-soft); color: var(--good); }
.chip.fail { background: var(--bad-soft); color: var(--bad); }
.chip.warn { background: var(--warn-soft); color: var(--warn); }
.chip.tsc  { background: var(--accent-soft); color: var(--accent); }
.meter {
  height: 8px; background: var(--surface-2); border-radius: 5px;
  overflow: hidden; margin-top: 6px;
}
.meter > span { display: block; height: 100%; background: var(--accent); }
.evidence {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 12px; color: var(--text-dim); background: var(--surface-2);
  border-radius: 6px; padding: 8px 10px; margin-top: 8px;
  white-space: pre-wrap; word-break: break-word;
}
table { width: 100%; border-collapse: collapse; font-size: 12.5px; }
th, td {
  text-align: left; padding: 6px 8px; border-bottom: 1px solid var(--border);
  vertical-align: top; word-break: break-word;
}
th { color: var(--text-dim); font-weight: 600; }
.ok-word { color: var(--good); font-weight: 600; }
.bad-word { color: var(--bad); font-weight: 600; }
.warn-word { color: var(--warn); font-weight: 600; }
.empty { color: var(--text-dim); font-style: italic; }
"""

#: overall -> (display words, css class). NEVER "COMPLIANT": readiness only.
_OVERALL_WORDS: dict[str, tuple[str, str]] = {
    "not_assessed": ("NOT ASSESSED", "warn"),
    "insufficient_evidence": ("INSUFFICIENT EVIDENCE", "warn"),
    "gaps": ("GAPS FOUND", "gaps"),
    "ready_pending_attestation": ("READY — PENDING ATTESTATION", "ready"),
}

#: verdict -> (display words, chip class).
_VERDICT_WORDS: dict[str, tuple[str, str]] = {
    "failing": ("failing", "fail"),
    "insufficient_history": ("insufficient history", "warn"),
    "structural_evidence_only": ("structural evidence only", "warn"),
    "operating": ("operating", "pass"),
}

_BANNER = (
    "These results are a <b>self-assessment</b> produced by the LPOS control "
    "readiness monitor. They are <b>not an attestation</b> and are never a "
    "SOC 2 conclusion: a SOC 2 Type 2 report is issued by an independent CPA "
    "firm after its own testing over an observation period."
)


def _chip(passing: bool) -> str:
    word = "PASS" if passing else "FAIL"
    cls = "pass" if passing else "fail"
    return f'<span class="chip {cls}">{word}</span>'


def _verdict_chip(verdict: str) -> str:
    word, cls = _VERDICT_WORDS.get(str(verdict), (str(verdict), "warn"))
    return f'<span class="chip {cls}">{escape(word)}</span>'


def _meter(ratio: float) -> str:
    pct = max(0, min(100, round(ratio * 100)))
    return (
        f'<div class="meter" role="img" aria-label="pass ratio {pct}%">'
        f'<span style="width:{pct}%"></span></div>'
    )


def _period_line(status: Mapping[str, Any]) -> str:
    window = int(status.get("window_days", 90) or 90)
    days = int(status.get("distinct_run_days", 0) or 0)
    period = str(status.get("evidence_period_status", "insufficient"))
    if period == "covers_window":
        word, cls = "observation window covered", "good"
    elif period == "partial":
        word, cls = "evidence period partially covered", "warn"
    else:
        word, cls = "insufficient operating evidence", "warn"
    return (
        f'<div class="period {cls}">{days} of {window} observation days — '
        f"{escape(word)}</div>"
    )


def _hero(status: Mapping[str, Any]) -> str:
    summary = status.get("summary", {}) or {}
    overall = str(status.get("overall", "not_assessed"))
    overall_word, overall_cls = _OVERALL_WORDS.get(
        overall, (overall.replace("_", " ").upper(), "warn")
    )
    return f"""
<div class="banner">{_BANNER}</div>
<section id="status" class="card">
  <div class="hero">
    <div>
      <h1>LPOS Control Readiness Report</h1>
      <div class="dim">Self-assessment, not an attestation —
        target framework: {escape(str(status.get("framework", "")))}</div>
    </div>
    <div class="overall {escape(overall_cls)}">{escape(overall_word)}</div>
  </div>
  {_period_line(status)}
  <p>
    <span class="stat"><b>{int(status.get("distinct_runs", 0) or 0)}</b>
      <span class="dim">distinct audit runs in window</span></span>
    <span class="stat"><b>{int(status.get("distinct_run_days", 0) or 0)}</b>
      <span class="dim">distinct run days</span></span>
    <span class="stat"><b>{int(status.get("days_of_history", 0) or 0)}</b>
      <span class="dim">days of history</span></span>
  </p>
  <p>
    <span class="stat"><b>{summary.get("operating", 0)}</b> <span class="dim">operating</span></span>
    <span class="stat"><b>{summary.get("structural_evidence_only", 0)}</b>
      <span class="dim">structural evidence only</span></span>
    <span class="stat"><b>{summary.get("insufficient_history", 0)}</b>
      <span class="dim">insufficient history</span></span>
    <span class="stat"><b>{summary.get("failing", 0)}</b> <span class="dim">failing</span></span>
    <span class="stat"><b>{summary.get("total", 0)}</b> <span class="dim">controls total</span></span>
  </p>
  <div class="dim">attestation: false · issued_by_cpa: false · self_assessment: true
    · run {escape(str(status.get("run_id", "")))}
    · generated at {escape(str(status.get("generated_at", "")))}</div>
</section>"""


def _problems(status: Mapping[str, Any]) -> str:
    failing = [c for c in status.get("controls", []) if not c.get("passing")]
    if not failing:
        body = '<div class="card empty">No failing controls. Every codified control passed its latest check.</div>'
    else:
        cards = []
        for control in failing:
            cards.append(
                f"""<div class="card">
  <h3>{escape(str(control.get("control_id", "")))} — {escape(str(control.get("title", "")))}
    {_chip(False)}<span class="chip tsc">{escape(str(control.get("tsc_id", "")))}</span></h3>
  <p>{escape(str(control.get("risk", control.get("control_objective", ""))) or "This control protects the criterion above; while it fails, that protection is not in force.")}</p>
  <div class="evidence">Evidence of failure: {escape(str(control.get("evidence", "")))}</div>
</div>"""
            )
        body = "\n".join(cards)
    return f'<section id="problems"><h2>The Problems</h2>{body}</section>'


def _not_evidenced(status: Mapping[str, Any]) -> str:
    items = list(status.get("not_evidenced", []) or [])
    if not items:
        return ""
    rows = "\n".join(
        "<tr>"
        f"<td>{escape(str(item.get('id', '')))}</td>"
        f"<td><span class=\"chip tsc\">{escape(str(item.get('tsc_id', '')))}</span></td>"
        f"<td>{escape(str(item.get('requirement', '')))}</td>"
        "</tr>"
        for item in items
    )
    return f"""<section id="not-evidenced"><h2>Requires Organizational Evidence</h2>
<div class="card">
  <div class="dim">These criteria have no machine check: each requires organizational evidence — not machine-checkable — supplied by humans or third parties. They are open readiness items,
  not passes.</div>
  <table>
    <tr><th>Item</th><th>TSC</th><th>Requirement</th></tr>
    {rows}
  </table>
</div></section>"""


def _fixes(remediations: Sequence[Mapping[str, Any]], adoption: Any) -> str:
    if not remediations:
        body = '<div class="card empty">No remediations needed — nothing is staged.</div>'
    else:
        adoption_actions = {}
        if isinstance(adoption, Mapping):
            for action in adoption.get("actions", []) or []:
                adoption_actions[str(action.get("staged_path", ""))] = action
        cards = []
        for remediation in remediations:
            validation = remediation.get("validation", {}) or {}
            validated = validation.get("validated", False)
            validation_word = (
                '<span class="ok-word">validated</span>'
                if validated
                else '<span class="bad-word">not validated</span>'
                + f' <span class="dim">({escape(str(validation.get("note", "")))})</span>'
            )
            cards.append(
                f"""<div class="card">
  <h3>Fix for {escape(str(remediation.get("control_id", "")))}</h3>
  <p>{escape(str(remediation.get("proposed_fix", "")))}</p>
  <table>
    <tr><th>Staged location (test environment)</th>
        <td>{escape(str(remediation.get("staged_dir", "")))}</td></tr>
    <tr><th>Validation</th><td>{validation_word}</td></tr>
    <tr><th>Adoption status</th>
        <td>awaiting approval <span class="dim">(record-only plan; the exact-action
        approval flow moves this into the main system)</span></td></tr>
  </table>
</div>"""
            )
        body = "\n".join(cards)
    return f'<section id="fixes"><h2>The Fixes</h2>{body}</section>'


def _audit_log(entries: Sequence[Mapping[str, Any]]) -> str:
    shown = list(entries)[-AUDIT_LOG_DISPLAY_CAP:]
    shown.reverse()
    if not shown:
        rows = '<tr><td colspan="5" class="empty">No history recorded yet.</td></tr>'
    else:
        parts = []
        for entry in shown:
            event = str(entry.get("event", "check"))
            if event == "check":
                outcome = (
                    '<span class="ok-word">pass</span>'
                    if entry.get("passing")
                    else '<span class="bad-word">fail</span>'
                )
            else:
                outcome = '<span class="dim">staged</span>'
            parts.append(
                "<tr>"
                f"<td>{escape(str(entry.get('ts', '')))}</td>"
                f"<td>{escape(str(entry.get('run_id', '')))}</td>"
                f"<td>{escape(str(entry.get('control_id', '')))}</td>"
                f"<td>{escape(event)} ({outcome})</td>"
                f"<td>{escape(str(entry.get('evidence', '')))}</td>"
                "</tr>"
            )
        rows = "\n".join(parts)
    return f"""<section id="audit-log"><h2>Audit Log</h2>
<div class="card">
  <div class="dim">Most recent first; showing up to {AUDIT_LOG_DISPLAY_CAP} of the retained,
  hash-chained history (verify with: python -m lpos_engine.compliance verify).</div>
  <table>
    <tr><th>Timestamp</th><th>Run</th><th>Control</th><th>Event</th><th>Evidence</th></tr>
    {rows}
  </table>
</div></section>"""


def _matrix(status: Mapping[str, Any]) -> str:
    groups: dict[str, list[Mapping[str, Any]]] = {}
    for control in status.get("controls", []):
        groups.setdefault(str(control.get("tsc_id", "?")), []).append(control)
    sections = []
    for tsc_id in sorted(groups):
        controls = groups[tsc_id]
        ratios = [float(c.get("pass_ratio", 0.0)) for c in controls]
        avg = sum(ratios) / len(ratios) if ratios else 0.0
        rows = "\n".join(
            "<tr>"
            f"<td>{escape(str(c.get('control_id', '')))}</td>"
            f"<td>{escape(str(c.get('title', '')))}"
            f"<div class=\"dim\">{escape(str(c.get('assurance', '')))} check"
            f" · owner {escape(str(c.get('owner', '')))}"
            f" · {escape(str(c.get('frequency', '')))}</div></td>"
            f"<td>{_chip(bool(c.get('passing')))} "
            f"{'pass' if c.get('passing') else 'fail'}</td>"
            f"<td>{_verdict_chip(str(c.get('verdict', '')))}"
            f"<div class=\"dim\">{float(c.get('pass_ratio', 0.0)):.2%} pass ratio · "
            f"{int(c.get('distinct_runs', 0) or 0)} runs · "
            f"{int(c.get('distinct_run_days', 0) or 0)} days</div>"
            f"{_meter(float(c.get('pass_ratio', 0.0)))}</td>"
            "</tr>"
            for c in controls
        )
        sections.append(
            f"""<div class="card">
  <h3><span class="chip tsc">{escape(tsc_id)}</span> series — group pass ratio {avg:.2%}</h3>
  {_meter(avg)}
  <table>
    <tr><th>Control</th><th>Title</th><th>State</th><th>Operating evidence</th></tr>
    {rows}
  </table>
</div>"""
        )
    return '<section id="matrix"><h2>Control Matrix</h2>' + "\n".join(sections) + "</section>"


def render_report(
    status: Mapping[str, Any],
    remediations: Sequence[Mapping[str, Any]] = (),
    audit_log_entries: Sequence[Mapping[str, Any]] = (),
    adoption: Any = None,
) -> str:
    """Render the full report as one self-contained HTML document string."""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>LPOS Control Readiness Report — self-assessment, not an attestation</title>
<style>{_CSS}</style>
</head>
<body>
<main>
{_hero(status)}
{_problems(status)}
{_not_evidenced(status)}
{_fixes(remediations, adoption)}
{_audit_log(audit_log_entries)}
{_matrix(status)}
<p class="dim">This page is the LPOS control readiness monitor's self-assessment of
controls over the LPOS system itself. It is not a SOC 2 attestation and it never
self-certifies: a SOC 2 Type 2 report is issued by an independent CPA firm after an
observation period. Structural checks prove artifacts exist, not that controls
operate; organizational criteria require evidence no machine can produce.</p>
</main>
</body>
</html>
"""


def generate_report(
    status: Mapping[str, Any],
    remediations: Sequence[Mapping[str, Any]],
    audit_log_entries: Sequence[Mapping[str, Any]],
    out_path: Path,
    *,
    adoption: Any = None,
) -> Path:
    """Write the report atomically to ``out_path`` and return it."""

    html = render_report(status, remediations, audit_log_entries, adoption=adoption)
    out_path = Path(out_path).expanduser()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = out_path.with_suffix(out_path.suffix + ".tmp")
    tmp.write_text(html, encoding="utf-8")
    tmp.replace(out_path)
    return out_path


def _load_remediation_plan(hermes_root: Path) -> dict[str, Any]:
    """Load the persisted remediation plan, if a prior run staged one."""

    path = Path(hermes_root).expanduser() / "compliance" / "remediations.json"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"remediations": [], "adoption": "none"}
    if not isinstance(value, Mapping):
        return {"remediations": [], "adoption": "none"}
    return dict(value)
