#!/usr/bin/env python3
"""Build the LPOS Test Coverage Map — a self-contained HTML page that shows every
source module, whether it is tested, its line coverage, and its Code Testing
Gauntlet tier.

Two data sources, degrading gracefully:

1. If ``coverage`` is available, run:
       coverage run --source=src/lpos_engine -m pytest tests/
       coverage json -o <tmp>
   and this tool reads the per-file line coverage. (Kept as a dev tool — the OS
   itself ships zero runtime dependencies.)
2. Always: a static inventory that maps each ``src/lpos_engine`` module to the
   test files that reference it and counts ``def test_`` functions, so the page
   is meaningful even with no coverage data.

Usage:
    python tools/build_test_report.py [--coverage-json PATH] [--out PATH]

Writes dist/test-coverage.html by default. The page is fully self-contained
(inline CSS/JS, no network) so it can be shipped as a release artifact or
persisted as a dashboard.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "lpos_engine"
TESTS = ROOT / "tests"

# Criticality tier per subsystem, from the Code Testing Gauntlet Standard: the
# security- and evidence-bearing modules are the ones that must be hardest tested.
TIERS = {
    "engine.py": "HIGH", "approvals.py": "HIGH", "store.py": "HIGH",
    "policy.py": "HIGH", "materiality.py": "HIGH", "state_machine.py": "HIGH",
    "adapters/subprocess_host.py": "HIGH", "schema_check.py": "HIGH",
    "monitor": "HIGH", "compliance": "HIGH", "dashboard": "HIGH",
    "sentinel": "HIGH", "code_testing": "STANDARD", "evolution": "STANDARD",
    "publication.py": "STANDARD", "routing.py": "STANDARD", "context.py": "STANDARD",
    "operations.py": "STANDARD", "canonical.py": "STANDARD", "models.py": "STANDARD",
    "cli.py": "STANDARD",
}


def tier_for(rel: str) -> str:
    for key, tier in TIERS.items():
        if rel == key or rel.startswith(key + "/") or rel.split("/")[0] == key:
            return tier
    return "LIGHT"


def run_coverage() -> dict | None:
    try:
        import coverage  # noqa: F401
    except ImportError:
        return None
    tmp = ROOT / ".coverage-report.json"
    env_run = subprocess.run(
        [sys.executable, "-m", "coverage", "run", "--source=src/lpos_engine",
         "-m", "pytest", "tests/", "-q"],
        cwd=ROOT, capture_output=True, text=True,
        env={**__import__("os").environ,
             "LPOS_EVALS_DIR": "src/lpos_engine/evals",
             "PYTHONPATH": "src"},
    )
    if env_run.returncode != 0:
        print("coverage run failed; falling back to static map", file=sys.stderr)
        return None
    subprocess.run([sys.executable, "-m", "coverage", "json", "-o", str(tmp)],
                   cwd=ROOT, capture_output=True, text=True)
    try:
        data = json.loads(tmp.read_text())
    finally:
        tmp.unlink(missing_ok=True)
    return data


def source_modules() -> list[str]:
    mods = []
    for path in sorted(SRC.rglob("*.py")):
        if "__pycache__" in path.parts or path.name == "__init__.py":
            continue
        mods.append(path.relative_to(SRC).as_posix())
    return mods


def test_inventory() -> dict[str, dict]:
    """Map each test file to the count of tests and the module names it references."""
    inv = {}
    for path in sorted(TESTS.glob("test_*.py")):
        text = path.read_text(encoding="utf-8", errors="replace")
        count = len(re.findall(r"^\s*def test_", text, re.MULTILINE))
        refs = set(re.findall(r"lpos_engine\.([a-zA-Z0-9_.]+)", text))
        inv[path.name] = {"tests": count, "refs": refs}
    return inv


def module_is_referenced(rel: str, inv: dict[str, dict]) -> list[str]:
    stem = rel[:-3].replace("/", ".")  # e.g. monitor/audit.py -> monitor.audit
    top = stem.split(".")[0]
    hits = []
    for name, meta in inv.items():
        if any(r == stem or r.startswith(stem + ".") or r == top or r.startswith(top + ".")
               for r in meta["refs"]):
            hits.append(name)
    return hits


def build(coverage_json: dict | None, out: Path) -> Path:
    mods = source_modules()
    inv = test_inventory()
    cov_files = {}
    if coverage_json:
        for fpath, fdata in coverage_json["files"].items():
            rel = Path(fpath).as_posix()
            marker = "src/lpos_engine/"
            if marker in rel:
                cov_files[rel.split(marker, 1)[1]] = fdata["summary"]

    total_tests = sum(m["tests"] for m in inv.values())
    rows = []
    tested = untested = 0
    for rel in mods:
        refs = module_is_referenced(rel, inv)
        cov = cov_files.get(rel)
        pct = cov["percent_covered"] if cov else None
        is_tested = bool(refs) or (pct is not None and pct > 0)
        tested += is_tested
        untested += not is_tested
        rows.append({
            "module": rel, "tier": tier_for(rel), "tests_files": refs,
            "pct": pct, "tested": is_tested,
            "lines": cov["num_statements"] if cov else None,
            "missing": cov["missing_lines"] if cov else None,
        })

    overall = coverage_json["totals"]["percent_covered"] if coverage_json else None
    rows.sort(key=lambda r: (r["pct"] if r["pct"] is not None else 999, r["module"]))

    def bar(pct):
        if pct is None:
            return '<span class="dim">no line data</span>'
        cls = "good" if pct >= 85 else "warn" if pct >= 60 else "bad"
        return (f'<div class="meter"><span class="{cls}" style="width:{pct:.0f}%"></span></div>'
                f'<span class="pct {cls}">{pct:.0f}%</span>')

    trows = ""
    for r in rows:
        files = ", ".join(sorted(r["tests_files"])) if r["tests_files"] else \
            '<span class="bad-word">no test references</span>'
        state = '<span class="ok-word">tested</span>' if r["tested"] else \
            '<span class="bad-word">UNTESTED</span>'
        trows += (
            f'<tr class="{"" if r["tested"] else "row-bad"}">'
            f'<td class="mono">{html.escape(r["module"])}</td>'
            f'<td><span class="chip t-{r["tier"].lower()}">{r["tier"]}</span></td>'
            f'<td>{state}</td><td>{bar(r["pct"])}</td>'
            f'<td class="mono small">{files}</td></tr>\n'
        )

    hero_cov = f"{overall:.1f}%" if overall is not None else "—"
    cov_note = ("Line coverage measured by running the full suite under coverage.py."
                if coverage_json else
                "Coverage.py was not available; showing the static module↔test map only.")
    generated = coverage_json.get("meta", {}).get("timestamp", "") if coverage_json else ""

    page = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>LPOS Test Coverage Map</title>
<style>
:root {{ --bg:#f4f4f2; --surface:#fff; --surface2:#ececea; --border:#dcdcd8;
 --text:#1f2125; --dim:#6b6f76; --accent:#3b6ea5; --good:#3b7a4e; --warn:#9a6b1f;
 --bad:#a53b3b; --radius:8px; }}
@media (prefers-color-scheme:dark){{:root{{--bg:#17181b;--surface:#1f2126;
 --surface2:#26282e;--border:#33363d;--text:#e6e7e9;--dim:#9a9ea6;--accent:#6ea8dc;
 --good:#7ac48f;--warn:#d9b36a;--bad:#d87a7a;}}}}
*{{box-sizing:border-box}} body{{margin:0;background:var(--bg);color:var(--text);
 font:14px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}}
main{{max-width:1080px;margin:0 auto;padding:24px 20px 60px}}
h1{{font-size:21px;margin:0 0 4px}} .dim{{color:var(--dim)}}
.hero{{display:flex;gap:28px;flex-wrap:wrap;align-items:baseline;
 background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);
 padding:16px 18px;margin-bottom:8px}}
.stat b{{font-size:24px}} .stat{{margin-right:8px}}
.big{{font-size:30px;font-weight:700;color:var(--accent)}}
table{{width:100%;border-collapse:collapse;font-size:12.5px;background:var(--surface);
 border:1px solid var(--border);border-radius:var(--radius);overflow:hidden;margin-top:14px}}
th,td{{text-align:left;padding:6px 9px;border-bottom:1px solid var(--border);vertical-align:middle}}
th{{color:var(--dim);font-weight:600;cursor:pointer;user-select:none}}
.mono{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}}
.small{{font-size:11px;color:var(--dim)}}
.meter{{display:inline-block;width:90px;height:8px;background:var(--surface2);
 border-radius:5px;overflow:hidden;vertical-align:middle;margin-right:6px}}
.meter>span{{display:block;height:100%}} .meter .good{{background:var(--good)}}
.meter .warn{{background:var(--warn)}} .meter .bad{{background:var(--bad)}}
.pct{{font-weight:600}} .pct.good{{color:var(--good)}} .pct.warn{{color:var(--warn)}}
.pct.bad{{color:var(--bad)}} .ok-word{{color:var(--good);font-weight:600}}
.bad-word{{color:var(--bad);font-weight:600}} .row-bad{{background:rgba(165,59,59,.06)}}
.chip{{display:inline-block;padding:1px 8px;border-radius:10px;font-size:11px;font-weight:600}}
.t-critical{{background:#f6e7e7;color:#a53b3b}} .t-high{{background:#f6efe0;color:#9a6b1f}}
.t-standard{{background:#e7eef6;color:#3b6ea5}} .t-light{{background:#ececea;color:#6b6f76}}
@media (prefers-color-scheme:dark){{.t-critical{{background:#3a2626}}.t-high{{background:#383021}}
 .t-standard{{background:#24303d}}.t-light{{background:#26282e}}}}
.legend{{margin:10px 0;font-size:12px;color:var(--dim)}}
</style></head><body><main>
<h1>LPOS Test Coverage Map</h1>
<div class="dim">Every source module, whether it is under test, its line coverage, and its
Code Testing Gauntlet tier. {html.escape(cov_note)}</div>
<div class="hero">
  <div class="stat"><span class="big">{hero_cov}</span><br><span class="dim">overall line coverage</span></div>
  <div class="stat"><b>{tested}</b><br><span class="dim">modules tested</span></div>
  <div class="stat"><b>{untested}</b><br><span class="dim">modules without test references</span></div>
  <div class="stat"><b>{total_tests}</b><br><span class="dim">test functions</span></div>
  <div class="stat"><b>{len(inv)}</b><br><span class="dim">test files</span></div>
</div>
<div class="legend">Tier reflects the gauntlet criticality of the subsystem: security- and
evidence-bearing code (HIGH) is held to the strongest test requirements. Rows are sorted by
coverage, lowest first, so gaps surface at the top. Click a column header to re-sort.</div>
<table id="t"><thead><tr>
<th onclick="sortBy(0)">Module</th><th onclick="sortBy(1)">Tier</th>
<th onclick="sortBy(2)">State</th><th onclick="sortBy(3)">Line coverage</th>
<th>Test files</th></tr></thead><tbody>
{trows}</tbody></table>
<p class="dim">Generated by <span class="mono">tools/build_test_report.py</span>. {html.escape(generated)}</p>
<script>
function sortBy(col){{
 const tb=document.querySelector('#t tbody');
 const rows=[...tb.rows];
 const num=col===3;
 rows.sort((a,b)=>{{
  let x=a.cells[col].innerText.trim(),y=b.cells[col].innerText.trim();
  if(num){{x=parseFloat(x)||999;y=parseFloat(y)||999;return x-y;}}
  return x.localeCompare(y);
 }});
 rows.forEach(r=>tb.appendChild(r));
}}
</script></main></body></html>
"""
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")
    print(f"wrote {out} — {tested}/{tested+untested} modules tested, "
          f"overall {hero_cov}")
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--coverage-json", type=Path, default=None,
                        help="pre-computed coverage.py JSON; if omitted, run coverage when available")
    parser.add_argument("--out", type=Path, default=ROOT / "dist" / "test-coverage.html")
    args = parser.parse_args()
    if args.coverage_json and args.coverage_json.is_file():
        cov = json.loads(args.coverage_json.read_text())
    else:
        cov = run_coverage()
    build(cov, args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
