#!/usr/bin/env python3
"""Static site generator for the LPOS User Guide wiki.

Stdlib-only. Reads Markdown pages from docs/wiki/**, generates additional
reference pages from the real system (workflow catalog, Standing Operation
definitions, specialist index, packaged skills), and writes a static site:

    dist/wiki/                  the browsable wiki (default output)
    dist/LPOS-User-Guide.html   single-file combined guide (printable)

Usage:
    python tools/build_wiki.py [--out DIR] [--repo-root DIR]

The output directory may also be set with the LPOS_WIKI_OUT environment
variable. The version badge is read from pyproject.toml.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import shutil
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

# --------------------------------------------------------------------------
# Site structure
# --------------------------------------------------------------------------

SITE_TITLE = "LPOS User Guide"

# (directory slug, human title) in sidebar order.
SECTIONS: list[tuple[str, str]] = [
    ("welcome", "Welcome & Concepts"),
    ("getting-started", "Getting Started"),
    ("includes", "Everything LPOS Includes"),
    ("reference", "Reference"),
    ("working-with", "Working With Your System"),
    ("administration", "Administration"),
    ("patch-notes", "Patch Notes"),
    ("documentation", "Documentation"),
]
SECTION_TITLES = dict(SECTIONS)
SECTION_ORDER = {slug: i for i, (slug, _) in enumerate(SECTIONS)}


@dataclass
class Page:
    slug: str              # e.g. "getting-started/install" (no extension)
    title: str
    section: str           # section directory slug
    order: float
    markdown: str
    generated: bool = False

    @property
    def url(self) -> str:
        return self.slug + ".html"

    @property
    def depth(self) -> int:
        return self.slug.count("/")


# --------------------------------------------------------------------------
# Frontmatter
# --------------------------------------------------------------------------

def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Parse a simple `key: value` YAML frontmatter block."""
    meta: dict = {}
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            block = text[3:end].strip("\n")
            body = text[end + 4 :]
            body = body[1:] if body.startswith("\n") else body
            for line in block.splitlines():
                line = line.strip()
                if not line or line.startswith("#") or ":" not in line:
                    continue
                key, _, value = line.partition(":")
                meta[key.strip()] = value.strip().strip("'\"")
            return meta, body
    return meta, text


# --------------------------------------------------------------------------
# Markdown -> HTML (small, self-contained converter)
# --------------------------------------------------------------------------

_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")
_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
_ITAL_RE = re.compile(r"(?<!\*)\*([^*\n]+)\*(?!\*)")


def _inline_fragment(text: str) -> str:
    """Escape and apply links / bold / italic to a non-code fragment."""
    out = html.escape(text, quote=False)
    out = _LINK_RE.sub(r'<a href="\2">\1</a>', out)
    out = _BOLD_RE.sub(r"<strong>\1</strong>", out)
    out = _ITAL_RE.sub(r"<em>\1</em>", out)
    return out


def render_inline(text: str) -> str:
    """Inline markdown: `code`, **bold**, *italic*, [links](url)."""
    parts = text.split("`")
    rendered: list[str] = []
    for i, part in enumerate(parts):
        if i % 2 == 1 and i != len(parts) - 1:
            rendered.append("<code>" + html.escape(part) + "</code>")
        elif i % 2 == 1:
            # Unbalanced backtick: treat literally.
            rendered.append("`" + _inline_fragment(part))
        else:
            rendered.append(_inline_fragment(part))
    return "".join(rendered)


def _is_table_sep(line: str) -> bool:
    body = line.strip()
    return bool(re.fullmatch(r"\|?[\s:|-]+\|?", body)) and "-" in body


def _split_row(line: str) -> list[str]:
    row = line.strip()
    if row.startswith("|"):
        row = row[1:]
    if row.endswith("|"):
        row = row[:-1]
    return [cell.strip() for cell in row.split("|")]


def markdown_to_html(text: str) -> str:
    lines = text.split("\n")
    out: list[str] = []
    i = 0
    n = len(lines)

    def render_list(start: int) -> int:
        """Render a (possibly two-level) list block starting at index start."""
        idx = start
        items: list[tuple[int, str, str]] = []  # (indent, marker, text)
        while idx < n:
            m = re.match(r"^(\s*)([-*]|\d+\.)\s+(.*)$", lines[idx])
            if not m:
                break
            items.append((len(m.group(1)), m.group(2), m.group(3)))
            idx += 1
        ordered = items[0][1] not in ("-", "*")
        tag = "ol" if ordered else "ul"
        out.append(f"<{tag}>")
        open_sub: str | None = None
        for indent, marker, body in items:
            if indent >= 2:
                if open_sub is None:
                    open_sub = "ol" if marker not in ("-", "*") else "ul"
                    out.append(f"<{open_sub}>")
                out.append("<li>" + render_inline(body) + "</li>")
            else:
                if open_sub is not None:
                    out.append(f"</{open_sub}>")
                    open_sub = None
                out.append("<li>" + render_inline(body) + "</li>")
        if open_sub is not None:
            out.append(f"</{open_sub}>")
        out.append(f"</{tag}>")
        return idx

    while i < n:
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            i += 1
            continue

        # Fenced code block
        if stripped.startswith("```"):
            lang = stripped[3:].strip()
            code_lines: list[str] = []
            i += 1
            while i < n and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i])
                i += 1
            i += 1  # closing fence
            cls = f' class="language-{html.escape(lang)}"' if lang else ""
            out.append(
                f"<pre><code{cls}>" + html.escape("\n".join(code_lines)) + "</code></pre>"
            )
            continue

        # Heading
        m = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if m:
            level = len(m.group(1))
            content = m.group(2).strip()
            anchor = re.sub(r"[^a-z0-9]+", "-", content.lower()).strip("-")
            out.append(f'<h{level} id="{anchor}">' + render_inline(content) + f"</h{level}>")
            i += 1
            continue

        # Horizontal rule
        if re.fullmatch(r"(-{3,}|\*{3,}|_{3,})", stripped):
            out.append("<hr>")
            i += 1
            continue

        # Blockquote
        if stripped.startswith(">"):
            quote: list[str] = []
            while i < n and lines[i].strip().startswith(">"):
                quote.append(re.sub(r"^\s*>\s?", "", lines[i]))
                i += 1
            out.append("<blockquote>" + markdown_to_html("\n".join(quote)) + "</blockquote>")
            continue

        # Table
        if stripped.startswith("|") and i + 1 < n and _is_table_sep(lines[i + 1]):
            header = _split_row(lines[i])
            i += 2
            rows: list[list[str]] = []
            while i < n and lines[i].strip().startswith("|"):
                rows.append(_split_row(lines[i]))
                i += 1
            out.append("<table><thead><tr>")
            out.extend("<th>" + render_inline(cell) + "</th>" for cell in header)
            out.append("</tr></thead><tbody>")
            for row in rows:
                out.append("<tr>")
                out.extend("<td>" + render_inline(cell) + "</td>" for cell in row)
                out.append("</tr>")
            out.append("</tbody></table>")
            continue

        # List
        if re.match(r"^(\s*)([-*]|\d+\.)\s+", line):
            i = render_list(i)
            continue

        # Paragraph: gather consecutive plain lines
        para: list[str] = [stripped]
        i += 1
        while i < n:
            nxt = lines[i]
            ns = nxt.strip()
            if (
                not ns
                or ns.startswith(("#", "```", ">", "|"))
                or re.match(r"^(\s*)([-*]|\d+\.)\s+", nxt)
                or re.fullmatch(r"(-{3,}|\*{3,}|_{3,})", ns)
            ):
                break
            para.append(ns)
            i += 1
        out.append("<p>" + render_inline(" ".join(para)) + "</p>")

    return "\n".join(out)


# --------------------------------------------------------------------------
# Generated reference pages (from the real system)
# --------------------------------------------------------------------------

def _humanize_cron(expr: str) -> str:
    """Best-effort human hint for the catalog's cron schedules."""
    days = {
        "0": "Sunday", "1": "Monday", "2": "Tuesday", "3": "Wednesday",
        "4": "Thursday", "5": "Friday", "6": "Saturday",
    }
    parts = expr.split()
    if len(parts) != 5:
        return ""
    minute, hour, dom, _month, dow = parts
    when = ""
    if minute.isdigit() and hour.isdigit():
        when = f"{int(hour):02d}:{int(minute):02d}"
    elif minute.startswith("*/") and hour == "*":
        return f"every {minute[2:]} minutes"
    elif minute.startswith("*/"):
        return f"every {minute[2:]} minutes during hours {hour}"
    elif hour and minute.isdigit():
        when = f"at minute {minute} of hours {hour}"
    if dow == "1-5":
        day = "weekdays"
    elif dow == "*" and dom == "*":
        day = "daily"
    elif dom.isdigit():
        day = f"day {dom} of each month"
    elif "," in dow:
        day = " and ".join(days.get(d, d) for d in dow.split(","))
    elif dow in days:
        day = days[dow] + "s"
    else:
        day = ""
    text = " ".join(x for x in (day, when and ("at " + when)) if x)
    return text


def split_spec_blocks(text: str) -> list[tuple[str, dict, str]]:
    """Split a compiled spec file into (source_path, frontmatter, body) blocks."""
    blocks: list[tuple[str, dict, str]] = []
    pattern = re.compile(r"^## Source: `([^`]+)`\s*$", re.MULTILINE)
    matches = list(pattern.finditer(text))
    for idx, m in enumerate(matches):
        start = m.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        chunk = text[start:end].strip("\n")
        # strip the leading horizontal rule before frontmatter, if present
        chunk = re.sub(r"^---\s*\n", "---\n", chunk, count=1)
        meta, body = parse_frontmatter(chunk)
        body = body.strip("\n").rstrip()
        body = re.sub(r"\n---\s*$", "", body)
        blocks.append((m.group(1), meta, body))
    return blocks


def _machine_field(block_text: str, key: str) -> str:
    m = re.search(rf"^\s*{key}:\s*(.+?)\s*(?:#.*)?$", block_text, re.MULTILINE)
    return m.group(1).strip() if m else ""


def generate_standing_operation_pages(repo: Path) -> list[Page]:
    workflows_dir = repo / "src" / "lpos_engine" / "workflows"
    catalog = json.loads((workflows_dir / "catalog.json").read_text(encoding="utf-8"))
    spec_text = (repo / "src" / "lpos_engine" / "spec" / "STANDING-OPERATIONS.md").read_text(
        encoding="utf-8"
    )

    # Index spec blocks by SO id.
    spec_by_id: dict[str, tuple[str, str]] = {}
    raw = spec_text
    for source, _meta, body in split_spec_blocks(raw):
        m = re.search(r"standing-operations/(SO-\d{3})", source)
        if m:
            spec_by_id[m.group(1)] = (source, body)
    # Raw frontmatter text per SO (for machine fields kept out of parse_frontmatter).
    raw_blocks: dict[str, str] = {}
    pattern = re.compile(r"^## Source: `standing-operations/(SO-\d{3})[^`]*`", re.MULTILINE)
    marks = list(pattern.finditer(raw))
    for idx, m in enumerate(marks):
        end = marks[idx + 1].start() if idx + 1 < len(marks) else len(raw)
        raw_blocks[m.group(1)] = raw[m.start():end]

    pages: list[Page] = []
    for pos, entry in enumerate(catalog.get("operations", [])):
        so_id = entry["so_id"]
        title = entry.get("title", so_id)
        schedule = entry.get("default_schedule", "")
        requires = entry.get("requires", [])
        enabled = entry.get("enabled_by_default", False)
        workflow_name = entry.get("workflow", "")

        raw_block = raw_blocks.get(so_id, "")
        trigger = _machine_field(raw_block, "trigger")
        intent = _machine_field(raw_block, "communication_intent")
        specialists = _machine_field(raw_block, "specialists").strip("[]")
        specialists = ", ".join(s.strip() for s in specialists.split(",") if s.strip())

        steps_md = ""
        workflow_path = workflows_dir / workflow_name
        if workflow_path.is_file():
            workflow = json.loads(workflow_path.read_text(encoding="utf-8"))
            model_class = workflow.get("model_class", "")
            rows = [
                "| Step | Handler | Depends on |",
                "|---|---|---|",
            ]
            for step in workflow.get("steps", []):
                deps = ", ".join(step.get("depends_on", [])) or "-"
                rows.append(
                    f"| {step.get('step_id', '')} | `{step.get('handler', '')}` | {deps} |"
                )
            steps_md = (
                f"\n## Workflow steps\n\nModel class: `{model_class}`. "
                f"Defined in `src/lpos_engine/workflows/{workflow_name}`.\n\n"
                + "\n".join(rows)
                + "\n"
            )

        human = _humanize_cron(schedule)
        schedule_cell = f"`{schedule}`" + (f" ({human})" if human else "")
        requires_cell = ", ".join(f"`{r}`" for r in requires) if requires else "none"
        facts = [
            "| | |",
            "|---|---|",
            f"| Operation ID | {so_id} |",
            f"| Default schedule | {schedule_cell} |",
            f"| Requires | {requires_cell} |",
            f"| Enabled by default | {'yes' if enabled else 'no'} |",
        ]
        if trigger:
            facts.append(f"| Trigger | {trigger} |")
        if intent:
            facts.append(f"| Communication intent | {intent} |")
        if specialists:
            facts.append(f"| Specialists | {specialists} |")

        body = ""
        if so_id in spec_by_id:
            _source, spec_body = spec_by_id[so_id]
            # Drop the duplicate H1 title from the spec body.
            spec_body = re.sub(r"^#\s+.*\n", "", spec_body, count=1).strip("\n")
            body = "\n" + spec_body + "\n"

        md = (
            f"# {so_id}: {title}\n\n"
            + "\n".join(facts)
            + "\n\n"
            + "Schedules use five-field cron syntax (minute, hour, day of month, month, "
            + "day of week), interpreted by the scheduler configured for your "
            + "installation. See `lpos list-workflows` for the packaged catalog.\n"
            + body
            + steps_md
            + "\n## Related pages\n\n"
            + "- [Standing Operations overview](/includes/index.html)\n"
            + "- [Onboarding: activate Standing Operations deliberately](/getting-started/onboarding.html)\n"
            + "- [Checking system health](/working-with/checking-system-health.html)\n"
        )
        pages.append(
            Page(
                slug=f"reference/{so_id.lower()}",
                title=f"{so_id}: {title}",
                section="reference",
                order=10 + pos,
                markdown=md,
                generated=True,
            )
        )
    return pages


def generate_specialists_page(repo: Path) -> Page:
    index_text = (repo / "src" / "lpos_engine" / "spec" / "SPECIALIST-INDEX.md").read_text(
        encoding="utf-8"
    )
    # Drop the file's own H1 and reuse the rest verbatim (table, fallback map, policy).
    body = re.sub(r"^#\s+.*\n", "", index_text, count=1).strip("\n")
    md = (
        "# Specialists\n\n"
        "LPOS routes work across 32 canonical specialists. Specialists are compiled "
        "roles the model assumes at routing time, grouped into guilds for "
        "accountability; capabilities determine execution. The table below is the "
        "packaged specialist index. You can print the same registry, including each "
        "specialist's capabilities and model class, with `lpos list-specialists`.\n\n"
        + body
        + "\n\n## Related pages\n\n"
        + "- [Core concepts](/welcome/concepts.html)\n"
        + "- [Everything LPOS includes](/includes/index.html)\n"
        + "- [CLI reference](/administration/cli-reference.html)\n"
    )
    return Page(
        slug="reference/specialists",
        title="Specialists",
        section="reference",
        order=1,
        markdown=md,
        generated=True,
    )


def generate_skills_page(repo: Path) -> Page:
    skills_dir = repo / "src" / "lpos_engine" / "spec" / "skills"
    rows = ["| Skill | Version | Description |", "|---|---|---|"]
    names: list[str] = []
    for skill_file in sorted(skills_dir.glob("*/SKILL.md")):
        meta, _body = parse_frontmatter(skill_file.read_text(encoding="utf-8"))
        name = meta.get("name", skill_file.parent.name)
        names.append(name)
        rows.append(
            f"| `{name}` | {meta.get('version', '')} | {meta.get('description', '')} |"
        )
    md = (
        "# Packaged skills\n\n"
        "LPOS ships a small set of skills as part of the packaged specification, "
        "under `src/lpos_engine/spec/skills/`. Each skill is a `SKILL.md` document "
        "the runtime loads on demand; skills are procedures, not services, and they "
        "run inside the same control-plane guardrails as everything else.\n\n"
        + "\n".join(rows)
        + "\n\nThe review skills are load-bearing: the Chip kernel requires "
        "`independent-reviewer` for the isolated review of material work, and "
        "`quality-router` defines how every material task is routed through craft "
        "standards and review.\n"
        + "\n## Related pages\n\n"
        + "- [Skill Evolution](/includes/skill-evolution.html)\n"
        + "- [Core concepts](/welcome/concepts.html)\n"
        + "- [Reading agent output](/working-with/reading-agent-output.html)\n"
    )
    return Page(
        slug="reference/skills",
        title="Packaged skills",
        section="reference",
        order=2,
        markdown=md,
        generated=True,
    )


# --------------------------------------------------------------------------
# HTML shell
# --------------------------------------------------------------------------

STYLE_CSS = """\
:root {
  --bg: #ffffff;
  --bg-alt: #f6f7f8;
  --fg: #1f2328;
  --fg-muted: #59636e;
  --border: #d9dde1;
  --accent: #2f5d8a;
  --accent-soft: #eaf1f7;
  --code-bg: #f2f3f5;
  --badge-bg: #eaf1f7;
  --badge-fg: #2f5d8a;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #14171a;
    --bg-alt: #1b1f24;
    --fg: #e3e7eb;
    --fg-muted: #9aa4ae;
    --border: #30363d;
    --accent: #7aa5cc;
    --accent-soft: #1f2c38;
    --code-bg: #22272e;
    --badge-bg: #1f2c38;
    --badge-fg: #9cc0e0;
  }
}
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica,
    Arial, sans-serif;
  background: var(--bg);
  color: var(--fg);
  line-height: 1.6;
}
a { color: var(--accent); text-decoration: none; }
a:hover { text-decoration: underline; }
.layout { display: flex; min-height: 100vh; }
.sidebar {
  width: 270px;
  flex-shrink: 0;
  border-right: 1px solid var(--border);
  background: var(--bg-alt);
  padding: 1rem;
  overflow-y: auto;
  position: sticky;
  top: 0;
  height: 100vh;
}
.sidebar .site-title {
  font-weight: 600;
  font-size: 1.05rem;
  display: block;
  margin-bottom: .25rem;
  color: var(--fg);
}
.badge {
  display: inline-block;
  font-size: .72rem;
  padding: .05rem .5rem;
  border-radius: 999px;
  background: var(--badge-bg);
  color: var(--badge-fg);
  border: 1px solid var(--border);
  margin-bottom: .75rem;
}
.sidebar h2 {
  font-size: .72rem;
  text-transform: uppercase;
  letter-spacing: .06em;
  color: var(--fg-muted);
  margin: 1.1rem 0 .3rem;
}
.sidebar ul { list-style: none; margin: 0; padding: 0; }
.sidebar li a {
  display: block;
  padding: .18rem .4rem;
  border-radius: 6px;
  color: var(--fg);
  font-size: .88rem;
}
.sidebar li a:hover { background: var(--accent-soft); text-decoration: none; }
.sidebar li a.current { background: var(--accent-soft); color: var(--accent); font-weight: 600; }
.content {
  flex: 1;
  min-width: 0;
  padding: 2rem 3rem 4rem;
  max-width: 60rem;
}
.content h1 { margin-top: 0; }
h1, h2, h3 { line-height: 1.3; }
code {
  background: var(--code-bg);
  border-radius: 4px;
  padding: .1rem .3rem;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: .88em;
}
pre {
  background: var(--code-bg);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: .8rem 1rem;
  overflow-x: auto;
}
pre code { background: none; padding: 0; }
blockquote {
  margin: 1rem 0;
  padding: .2rem 1rem;
  border-left: 3px solid var(--accent);
  background: var(--bg-alt);
  color: var(--fg-muted);
  border-radius: 0 6px 6px 0;
}
table { border-collapse: collapse; width: 100%; margin: 1rem 0; display: block; overflow-x: auto; }
th, td { border: 1px solid var(--border); padding: .4rem .6rem; text-align: left; font-size: .9rem; }
th { background: var(--bg-alt); }
hr { border: none; border-top: 1px solid var(--border); margin: 2rem 0; }
.search-box { position: relative; margin: .5rem 0 0; }
.search-box input {
  width: 100%;
  padding: .4rem .6rem;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--bg);
  color: var(--fg);
  font-size: .88rem;
}
.search-results {
  position: absolute;
  z-index: 10;
  left: 0; right: 0;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 6px;
  margin-top: .2rem;
  max-height: 300px;
  overflow-y: auto;
  box-shadow: 0 4px 14px rgba(0,0,0,.15);
  display: none;
}
.search-results a { display: block; padding: .35rem .6rem; font-size: .85rem; }
.search-results a small { display: block; color: var(--fg-muted); }
.search-results a:hover { background: var(--accent-soft); text-decoration: none; }
.menu-toggle { display: none; }
@media (max-width: 800px) {
  .layout { flex-direction: column; }
  .sidebar { width: 100%; height: auto; position: static; }
  .content { padding: 1.2rem; }
}
@media print {
  .sidebar { display: none; }
  .content { padding: 0; max-width: none; }
}
"""

APP_JS = """\
(function () {
  var input = document.getElementById('search-input');
  var results = document.getElementById('search-results');
  if (!input || !results) return;
  var prefix = document.body.getAttribute('data-root') || '';
  var index = null;

  function load(cb) {
    if (index) return cb(index);
    var xhr = new XMLHttpRequest();
    xhr.open('GET', prefix + 'search-index.json');
    xhr.onload = function () {
      try { index = JSON.parse(xhr.responseText); } catch (e) { index = []; }
      cb(index);
    };
    xhr.onerror = function () { cb([]); };
    xhr.send();
  }

  function search(q) {
    q = q.toLowerCase().trim();
    if (!q) { results.style.display = 'none'; results.innerHTML = ''; return; }
    load(function (pages) {
      var terms = q.split(/\\s+/);
      var scored = [];
      for (var i = 0; i < pages.length; i++) {
        var p = pages[i];
        var title = p.title.toLowerCase();
        var text = p.text.toLowerCase();
        var score = 0, ok = true;
        for (var t = 0; t < terms.length; t++) {
          var term = terms[t];
          if (title.indexOf(term) !== -1) { score += 10; }
          else if (text.indexOf(term) !== -1) { score += 1; }
          else { ok = false; break; }
        }
        if (ok) scored.push([score, p]);
      }
      scored.sort(function (a, b) { return b[0] - a[0]; });
      results.innerHTML = '';
      var top = scored.slice(0, 12);
      for (var j = 0; j < top.length; j++) {
        var page = top[j][1];
        var a = document.createElement('a');
        a.href = prefix + page.url;
        a.textContent = page.title;
        var small = document.createElement('small');
        small.textContent = page.section;
        a.appendChild(small);
        results.appendChild(a);
      }
      results.style.display = top.length ? 'block' : 'none';
    });
  }

  input.addEventListener('input', function () { search(input.value); });
  input.addEventListener('focus', function () { if (input.value) search(input.value); });
  document.addEventListener('click', function (ev) {
    if (!results.contains(ev.target) && ev.target !== input) {
      results.style.display = 'none';
    }
  });
})();
"""


def rewrite_root_links(html_text: str, depth: int) -> str:
    """Rewrite site-root-relative hrefs (href="/x/y.html") for page depth."""
    prefix = "../" * depth

    def repl(m: re.Match) -> str:
        return f'href="{prefix}{m.group(1)}"'

    return re.sub(r'href="/([^"]+)"', repl, html_text)


def rewrite_links_for_combined(html_text: str) -> str:
    """Rewrite internal links to in-document anchors for the combined guide."""

    def repl(m: re.Match) -> str:
        target = m.group(1)
        if target.endswith(".html"):
            target = target[: -len(".html")]
        return f'href="#page-{target.replace("/", "-")}"'

    return re.sub(r'href="/([^"#]+)(#[^"]*)?"', repl, html_text)


def build_nav(pages: list[Page], current: Page | None, depth: int) -> str:
    prefix = "../" * depth
    by_section: dict[str, list[Page]] = {}
    for page in pages:
        by_section.setdefault(page.section, []).append(page)
    parts: list[str] = []
    for slug, title in SECTIONS:
        section_pages = sorted(
            by_section.get(slug, []), key=lambda p: (p.order, p.title)
        )
        if not section_pages:
            continue
        parts.append(f"<h2>{html.escape(title)}</h2><ul>")
        for page in section_pages:
            cls = ' class="current"' if current is not None and page.slug == current.slug else ""
            parts.append(
                f'<li><a{cls} href="{prefix}{page.url}">{html.escape(page.title)}</a></li>'
            )
        parts.append("</ul>")
    return "".join(parts)


def page_html(page: Page, pages: list[Page], version: str) -> str:
    depth = page.depth
    prefix = "../" * depth
    body_html = rewrite_root_links(markdown_to_html(page.markdown), depth)
    nav = build_nav(pages, page, depth)
    section_title = SECTION_TITLES.get(page.section, page.section)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(page.title)} - {SITE_TITLE}</title>
<link rel="stylesheet" href="{prefix}style.css">
</head>
<body data-root="{prefix}">
<div class="layout">
<nav class="sidebar">
<a class="site-title" href="{prefix}index.html">{SITE_TITLE}</a>
<span class="badge">LPOS v{html.escape(version)}</span>
<div class="search-box">
<input id="search-input" type="search" placeholder="Search the guide" autocomplete="off">
<div id="search-results" class="search-results"></div>
</div>
{nav}
</nav>
<main class="content">
<p style="color: var(--fg-muted); font-size: .8rem; margin-bottom: .2rem;">{html.escape(section_title)}</p>
{body_html}
</main>
</div>
<script src="{prefix}app.js"></script>
</body>
</html>
"""


def strip_tags(html_text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", html_text)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def combined_guide_html(pages: list[Page], version: str) -> str:
    ordered = sorted(
        pages, key=lambda p: (SECTION_ORDER.get(p.section, 99), p.order, p.title)
    )
    toc_parts: list[str] = ["<nav class=\"toc\"><h2>Contents</h2><ol>"]
    body_parts: list[str] = []
    last_section = None
    for page in ordered:
        anchor = "page-" + page.slug.replace("/", "-")
        if page.section != last_section:
            last_section = page.section
            toc_parts.append(
                f"<li class=\"toc-section\">{html.escape(SECTION_TITLES.get(page.section, page.section))}</li>"
            )
            body_parts.append(
                f'<h1 class="section-divider">{html.escape(SECTION_TITLES.get(page.section, page.section))}</h1>'
            )
        toc_parts.append(f'<li><a href="#{anchor}">{html.escape(page.title)}</a></li>')
        page_body = rewrite_links_for_combined(markdown_to_html(page.markdown))
        body_parts.append(f'<section class="guide-page" id="{anchor}">{page_body}</section>')
    toc_parts.append("</ol></nav>")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{SITE_TITLE} - LPOS v{html.escape(version)}</title>
<style>
{STYLE_CSS}
body {{ padding: 2rem; max-width: 52rem; margin: 0 auto; }}
.guide-page {{ border-top: 1px solid var(--border); margin-top: 2rem; padding-top: 1rem; }}
.section-divider {{ margin-top: 3rem; border-bottom: 2px solid var(--accent); padding-bottom: .3rem; }}
.toc ol {{ columns: 2; }}
.toc-section {{ list-style: none; font-weight: 600; margin-top: .5rem; }}
@media print {{ .guide-page {{ page-break-before: always; }} }}
</style>
</head>
<body>
<header>
<h1>{SITE_TITLE}</h1>
<p><span class="badge">LPOS v{html.escape(version)}</span></p>
<p>The complete LPOS User Guide in one document. Generated from the wiki sources
in <code>docs/wiki/</code> and the packaged LPOS specification. Print this file to
produce a PDF snapshot of the guide.</p>
</header>
{''.join(toc_parts)}
{''.join(body_parts)}
</body>
</html>
"""


# --------------------------------------------------------------------------
# Build
# --------------------------------------------------------------------------

def read_version(repo: Path) -> str:
    data = tomllib.loads((repo / "pyproject.toml").read_text(encoding="utf-8"))
    return str(data["project"]["version"])


def collect_source_pages(repo: Path) -> list[Page]:
    wiki_root = repo / "docs" / "wiki"
    pages: list[Page] = []
    for path in sorted(wiki_root.rglob("*.md")):
        rel = path.relative_to(wiki_root)
        slug = rel.with_suffix("").as_posix()
        meta, body = parse_frontmatter(path.read_text(encoding="utf-8"))
        section = meta.get("section") or (rel.parts[0] if len(rel.parts) > 1 else "welcome")
        title = meta.get("title") or slug
        try:
            order = float(meta.get("order", 999))
        except ValueError:
            order = 999.0
        pages.append(Page(slug=slug, title=title, section=section, order=order, markdown=body))
    return pages


def build(repo: Path, out: Path) -> dict:
    version = read_version(repo)
    pages = collect_source_pages(repo)
    pages.extend(generate_standing_operation_pages(repo))
    pages.append(generate_specialists_page(repo))
    pages.append(generate_skills_page(repo))

    slugs = [p.slug for p in pages]
    duplicates = {s for s in slugs if slugs.count(s) > 1}
    if duplicates:
        raise SystemExit(f"duplicate page slugs: {sorted(duplicates)}")

    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    (out / "style.css").write_text(STYLE_CSS, encoding="utf-8")
    (out / "app.js").write_text(APP_JS, encoding="utf-8")

    search_index = []
    for page in pages:
        target = out / (page.slug + ".html")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(page_html(page, pages, version), encoding="utf-8")
        search_index.append(
            {
                "url": page.url,
                "title": page.title,
                "section": SECTION_TITLES.get(page.section, page.section),
                "text": strip_tags(markdown_to_html(page.markdown))[:6000],
            }
        )
    (out / "search-index.json").write_text(
        json.dumps(search_index, ensure_ascii=False, indent=1), encoding="utf-8"
    )

    # Site root: redirect to the welcome page.
    home = "welcome/index.html"
    (out / "index.html").write_text(
        "<!DOCTYPE html>\n<html lang=\"en\"><head><meta charset=\"utf-8\">"
        f"<meta http-equiv=\"refresh\" content=\"0; url={home}\">"
        f"<title>{SITE_TITLE}</title></head>"
        f"<body><p><a href=\"{home}\">{SITE_TITLE}</a></p></body></html>\n",
        encoding="utf-8",
    )

    combined_path = out.parent / "LPOS-User-Guide.html"
    combined_path.parent.mkdir(parents=True, exist_ok=True)
    combined_path.write_text(combined_guide_html(pages, version), encoding="utf-8")

    return {
        "version": version,
        "pages": len(pages),
        "site": str(out),
        "combined": str(combined_path),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the LPOS User Guide wiki.")
    default_repo = Path(__file__).resolve().parent.parent
    parser.add_argument("--repo-root", type=Path, default=default_repo)
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Site output directory (default: <repo>/dist/wiki, or $LPOS_WIKI_OUT). "
        "The combined single-file guide is written next to it.",
    )
    args = parser.parse_args(argv)
    repo = args.repo_root.resolve()
    if args.out is not None:
        out = args.out.resolve()
    elif os.environ.get("LPOS_WIKI_OUT"):
        out = Path(os.environ["LPOS_WIKI_OUT"]).resolve()
    else:
        out = repo / "dist" / "wiki"
    result = build(repo, out)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
