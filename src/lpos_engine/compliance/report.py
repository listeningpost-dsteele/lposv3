"""The compliance report: one self-contained HTML page.

No CDNs, no external assets, no chart libraries. Inline CSS only, system font
stack, dark mode via ``prefers-color-scheme``, one calm accent -- the same
tone as the Hermes dashboard (``dashboard/ui.py``). Every value is HTML-escaped
and every signal is carried by words as well as color.
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
  --radius: 8px; --shadow: 0 1px 2px rgba(20,22,26,.06);
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #17181b; --surface: #1f2126; --surface-2: #26282e; --border: #33363d;
    --text: #e6e7e9; --text-dim: #9a9ea6; --accent: #6ea8dc; --accent-soft: #24303d;
    --bad: #d87a7a; --bad-soft: #3a2626; --good: #7ac48f; --good-soft: #24352a;
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
.hero { display: flex; flex-wrap: wrap; gap: 24px; align-items: baseline; }
.hero .overall { font-size: 26px; font-weight: 700; }
.hero .overall.compliant { color: var(--good); }
.hero .overall.gaps { color: var(--bad); }
.stat { display: inline-block; margin-right: 18px; }
.stat b { font-size: 18px; }
.dim { color: var(--text-dim); font-size: 12px; }
.chip {
  display: inline-block; padding: 1px 9px; border-radius: 10px;
  font-size: 11px; font-weight: 600; margin-left: 6px; vertical-align: middle;
}
.chip.pass { background: var(--good-soft); color: var(--good); }
.chip.fail { background: var(--bad-soft); color: var(--bad); }
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
.empty { color: var(--text-dim); font-style: italic; }
"""


def _chip(passing: bool) -> str:
    word = "PASS" if passing else "FAIL"
    cls = "pass" if passing else "fail"
    return f'<span class="chip {cls}">{word}</span>'


def _meter(ratio: float) -> str:
    pct = max(0, min(100, round(ratio * 100)))
    return (
        f'<div class="meter" role="img" aria-label="effectiveness {pct}%">'
        f'<span style="width:{pct}%"></span></div>'
    )


def _hero(status: Mapping[str, Any]) -> str:
    summary = status.get("summary", {}) or {}
    coverage = status.get("coverage", {}) or {}
    overall = str(status.get("overall", "gaps"))
    overall_word = "COMPLIANT" if overall == "compliant" else "GAPS FOUND"
    return f"""
<section id="status" class="card">
  <div class="hero">
    <div>
      <h1>SOC 2 Type 2 Compliance</h1>
      <div class="dim">{escape(str(status.get("framework", "")))}</div>
    </div>
    <div class="overall {escape(overall)}">{overall_word}</div>
  </div>
  <p>
    <span class="stat"><b>{coverage.get("days_of_history", 0)}</b>
      <span class="dim">of {status.get("window_days", 90)} observation days covered</span></span>
    <span class="stat"><b>{coverage.get("runs_in_window", 0)}</b>
      <span class="dim">check runs in window</span></span>
  </p>
  <p>
    <span class="stat"><b>{summary.get("effective", 0)}</b> <span class="dim">effective</span></span>
    <span class="stat"><b>{summary.get("not_yet_demonstrated", 0)}</b>
      <span class="dim">not yet demonstrated</span></span>
    <span class="stat"><b>{summary.get("failing", 0)}</b> <span class="dim">failing</span></span>
    <span class="stat"><b>{summary.get("total", 0)}</b> <span class="dim">controls total</span></span>
  </p>
  <div class="dim">Generated at {escape(str(status.get("generated_at", "")))}</div>
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
  <p>{escape(str(control.get("risk", control.get("description", ""))) or "This control protects the criterion above; while it fails, that protection is not in force.")}</p>
  <div class="evidence">Evidence of failure: {escape(str(control.get("evidence", "")))}</div>
</div>"""
            )
        body = "\n".join(cards)
    return f'<section id="problems"><h2>The Problems</h2>{body}</section>'


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
        rows = '<tr><td colspan="4" class="empty">No history recorded yet.</td></tr>'
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
                f"<td>{escape(str(entry.get('control_id', '')))}</td>"
                f"<td>{escape(event)} ({outcome})</td>"
                f"<td>{escape(str(entry.get('evidence', '')))}</td>"
                "</tr>"
            )
        rows = "\n".join(parts)
    return f"""<section id="audit-log"><h2>Audit Log</h2>
<div class="card">
  <div class="dim">Most recent first; showing up to {AUDIT_LOG_DISPLAY_CAP} of the retained history.</div>
  <table>
    <tr><th>Timestamp</th><th>Control</th><th>Event</th><th>Evidence</th></tr>
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
        ratios = [float(c.get("effectiveness", 0.0)) for c in controls]
        avg = sum(ratios) / len(ratios) if ratios else 0.0
        rows = "\n".join(
            "<tr>"
            f"<td>{escape(str(c.get('control_id', '')))}</td>"
            f"<td>{escape(str(c.get('title', '')))}</td>"
            f"<td>{_chip(bool(c.get('passing')))} "
            f"{'pass' if c.get('passing') else 'fail'}</td>"
            f"<td>{float(c.get('effectiveness', 0.0)):.2%} — {escape(str(c.get('verdict', '')))}"
            f"{_meter(float(c.get('effectiveness', 0.0)))}</td>"
            "</tr>"
            for c in controls
        )
        sections.append(
            f"""<div class="card">
  <h3><span class="chip tsc">{escape(tsc_id)}</span> series — group effectiveness {avg:.2%}</h3>
  {_meter(avg)}
  <table>
    <tr><th>Control</th><th>Title</th><th>State</th><th>Type 2 effectiveness</th></tr>
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
<title>LPOS Compliance — SOC 2 Type 2</title>
<style>{_CSS}</style>
</head>
<body>
<main>
{_hero(status)}
{_problems(status)}
{_fixes(remediations, adoption)}
{_audit_log(audit_log_entries)}
{_matrix(status)}
<p class="dim">This page demonstrates and enforces controls over the LPOS system itself.
It is not a SOC 2 attestation: a SOC 2 Type 2 report is issued by an independent CPA
firm after an observation period.</p>
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
