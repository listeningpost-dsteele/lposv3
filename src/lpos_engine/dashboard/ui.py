"""The dashboard's single-page UI as one self-contained inline HTML string.

No CDNs, no external assets, no build step.  Served verbatim at ``GET /``.
"""

from __future__ import annotations

PAGE_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Hermes Projects</title>
<style>
:root {
  --bg: #f4f4f2;
  --surface: #ffffff;
  --surface-2: #ececea;
  --border: #dcdcd8;
  --text: #1f2125;
  --text-dim: #6b6f76;
  --accent: #3b6ea5;
  --accent-soft: #e7eef6;
  --warn: #a5673b;
  --warn-soft: #f6efe7;
  --radius: 8px;
  --shadow: 0 1px 2px rgba(20,22,26,.06);
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #17181b;
    --surface: #1f2126;
    --surface-2: #26282e;
    --border: #33363d;
    --text: #e6e7e9;
    --text-dim: #9a9ea6;
    --accent: #6ea8dc;
    --accent-soft: #24303d;
    --warn: #d8a06a;
    --warn-soft: #3a2f24;
    --shadow: 0 1px 2px rgba(0,0,0,.35);
  }
}
* { box-sizing: border-box; }
html, body { height: 100%; }
body {
  margin: 0;
  background: var(--bg);
  color: var(--text);
  font: 14px/1.45 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
        "Helvetica Neue", Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
}
#app { display: flex; flex-direction: column; height: 100vh; }

/* health strip */
#health {
  display: none;
  padding: 6px 16px;
  font-size: 12px;
  color: var(--text-dim);
  background: var(--surface-2);
  border-bottom: 1px solid var(--border);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
#health.visible { display: block; }
#health .dot { color: var(--accent); margin-right: 6px; }

#layout { display: flex; flex: 1; min-height: 0; }

/* left rail */
#rail {
  width: 208px; flex-shrink: 0;
  display: flex; flex-direction: column; gap: 2px;
  padding: 14px 10px;
  border-right: 1px solid var(--border);
  background: var(--surface);
}
#rail h1 {
  font-size: 13px; font-weight: 600; letter-spacing: .04em;
  text-transform: uppercase; color: var(--text-dim);
  margin: 0 6px 10px;
}
#search {
  width: 100%; margin-bottom: 12px;
  padding: 7px 10px;
  border: 1px solid var(--border); border-radius: var(--radius);
  background: var(--bg); color: var(--text);
  font: inherit; outline: none;
}
#search:focus { border-color: var(--accent); }
.bucket-btn {
  display: flex; justify-content: space-between; align-items: center;
  width: 100%; padding: 7px 10px;
  border: 0; border-radius: var(--radius);
  background: transparent; color: var(--text);
  font: inherit; text-align: left; cursor: pointer;
}
.bucket-btn:hover { background: var(--surface-2); }
.bucket-btn.selected { background: var(--accent-soft); color: var(--accent); font-weight: 600; }
.bucket-btn .count {
  font-size: 11px; color: var(--text-dim);
  background: var(--surface-2); border-radius: 10px; padding: 1px 7px;
}
.bucket-btn.selected .count { background: transparent; color: var(--accent); }
#rail .hint { margin-top: auto; font-size: 11px; color: var(--text-dim); padding: 6px; }
#rail .hint kbd {
  border: 1px solid var(--border); border-bottom-width: 2px; border-radius: 4px;
  padding: 0 5px; font-family: inherit; font-size: 11px;
}

/* main pane */
#main { flex: 1; min-width: 0; overflow-y: auto; padding: 18px 22px; }
#main h2 { font-size: 16px; font-weight: 600; margin: 0 0 14px; }
#cards { display: flex; flex-direction: column; gap: 10px; max-width: 860px; }
.card {
  background: var(--surface);
  border: 1px solid var(--border); border-radius: var(--radius);
  box-shadow: var(--shadow);
  padding: 12px 14px;
  cursor: pointer;
}
.card:hover { border-color: var(--accent); }
.card .row1 { display: flex; align-items: baseline; gap: 10px; flex-wrap: wrap; }
.card .name { font-weight: 600; font-size: 14px; }
.card .agent { color: var(--text-dim); font-size: 12px; }
.card .when { margin-left: auto; color: var(--text-dim); font-size: 12px; white-space: nowrap; }
.badge {
  display: inline-block; font-size: 11px; font-weight: 600;
  border-radius: 10px; padding: 1px 8px; vertical-align: middle;
}
.badge.woke { background: var(--warn-soft); color: var(--warn); }
.badge.bucket { background: var(--surface-2); color: var(--text-dim); font-weight: 500; }
.card .desc { color: var(--text-dim); font-size: 13px; margin-top: 4px; }
.card .pathrow {
  display: flex; align-items: center; gap: 8px; margin-top: 8px;
  font-size: 12px; color: var(--text-dim);
}
.card .path {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 11.5px;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
button.mini {
  border: 1px solid var(--border); border-radius: 6px;
  background: var(--surface); color: var(--text);
  font: inherit; font-size: 11.5px; padding: 2px 9px; cursor: pointer;
  white-space: nowrap;
}
button.mini:hover { border-color: var(--accent); color: var(--accent); }
button.mini.primary { background: var(--accent); border-color: var(--accent); color: #fff; }

/* empty state */
#empty {
  max-width: 520px; margin: 48px auto; text-align: left;
  color: var(--text-dim); font-size: 13.5px;
}
#empty h3 { color: var(--text); font-size: 15px; margin: 0 0 8px; }
#empty dt { color: var(--text); font-weight: 600; margin-top: 10px; }
#empty dd { margin: 2px 0 0 0; }

/* detail panel */
#detail {
  width: 340px; flex-shrink: 0; display: none;
  border-left: 1px solid var(--border);
  background: var(--surface);
  padding: 18px; overflow-y: auto;
}
#detail.visible { display: block; }
#detail h3 { margin: 0 0 2px; font-size: 15px; }
#detail .sub { color: var(--text-dim); font-size: 12px; margin-bottom: 12px; }
#detail .section { margin: 14px 0; }
#detail .label {
  font-size: 11px; text-transform: uppercase; letter-spacing: .05em;
  color: var(--text-dim); margin-bottom: 4px;
}
#detail .path {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 11.5px; word-break: break-all; color: var(--text);
}
#detail .actions { display: flex; flex-wrap: wrap; gap: 6px; }
#detail .close { float: right; }
.snooze-menu { display: none; margin-top: 8px; padding: 10px;
  background: var(--surface-2); border-radius: var(--radius); }
.snooze-menu.visible { display: block; }
.snooze-menu .presets { display: flex; gap: 6px; margin-bottom: 8px; }
.snooze-menu input[type="datetime-local"] {
  font: inherit; font-size: 12px; padding: 3px 6px;
  border: 1px solid var(--border); border-radius: 6px;
  background: var(--surface); color: var(--text);
}
.filehit { padding: 6px 0; border-bottom: 1px solid var(--border); font-size: 12.5px; }
.filehit .path { color: var(--text-dim); font-size: 11px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }
#toast {
  position: fixed; bottom: 18px; left: 50%; transform: translateX(-50%);
  background: var(--text); color: var(--bg);
  border-radius: 6px; padding: 6px 14px; font-size: 12.5px;
  opacity: 0; transition: opacity .2s; pointer-events: none;
}
#toast.visible { opacity: .92; }
</style>
</head>
<body>
<div id="app">
  <div id="health"></div>
  <div id="layout">
    <nav id="rail">
      <h1>Hermes</h1>
      <input id="search" type="search" placeholder="Search  /" autocomplete="off">
      <button class="bucket-btn" data-bucket="active">Active <span class="count"></span></button>
      <button class="bucket-btn" data-bucket="research">Research <span class="count"></span></button>
      <button class="bucket-btn" data-bucket="snoozed">Snoozed <span class="count"></span></button>
      <button class="bucket-btn" data-bucket="archived">Archive <span class="count"></span></button>
      <div class="hint">Press <kbd>/</kbd> to search</div>
    </nav>
    <main id="main">
      <h2 id="view-title">Active</h2>
      <div id="cards"></div>
    </main>
    <aside id="detail"></aside>
  </div>
</div>
<div id="toast"></div>
<script>
"use strict";
const BUCKET_LABEL = { active: "Active", research: "Research", snoozed: "Snoozed", archived: "Archive" };
let state = { projects: [], bucket: "active", selected: null, query: "", search: null };

function esc(s) {
  return String(s == null ? "" : s).replace(/[&<>"']/g,
    c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
}
function relTime(epoch) {
  if (!epoch) return "unknown";
  const s = Math.max(0, Date.now() / 1000 - epoch);
  if (s < 90) return "just now";
  const m = s / 60; if (m < 90) return Math.round(m) + " min ago";
  const h = m / 60; if (h < 36) return Math.round(h) + " h ago";
  const d = h / 24; if (d < 14) return Math.round(d) + " d ago";
  const w = d / 7; if (w < 9) return Math.round(w) + " wk ago";
  return Math.round(d / 30) + " mo ago";
}
function untilText(iso) {
  if (!iso) return "";
  const t = Date.parse(iso);
  if (isNaN(t)) return iso;
  return "wakes " + new Date(t).toLocaleString();
}
async function api(path, opts) {
  const res = await fetch(path, opts);
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(body.error || res.statusText);
  return body;
}
async function post(path, payload) {
  return api(path, { method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload || {}) });
}
function toast(msg) {
  const el = document.getElementById("toast");
  el.textContent = msg;
  el.classList.add("visible");
  clearTimeout(toast._t);
  toast._t = setTimeout(() => el.classList.remove("visible"), 1800);
}
async function refresh() {
  try {
    const data = await api("/api/projects");
    state.projects = data.projects || [];
  } catch (e) { toast("Could not load projects: " + e.message); }
  try {
    const h = await api("/api/health");
    renderHealth(h.health);
  } catch (e) { renderHealth(null); }
  render();
}
function renderHealth(health) {
  const el = document.getElementById("health");
  if (!health || typeof health !== "object") { el.classList.remove("visible"); return; }
  const parts = [];
  for (const [k, v] of Object.entries(health)) {
    if (v === null || typeof v === "object") continue;
    parts.push(esc(k) + ": " + esc(v));
    if (parts.length >= 6) break;
  }
  if (!parts.length) { el.classList.remove("visible"); return; }
  el.innerHTML = '<span class="dot">&#9679;</span>System ' + parts.join(" &nbsp;&middot;&nbsp; ");
  el.classList.add("visible");
}
function bucketCounts() {
  const counts = { active: 0, research: 0, snoozed: 0, archived: 0 };
  for (const p of state.projects) counts[p.bucket] = (counts[p.bucket] || 0) + 1;
  return counts;
}
function cardHtml(p) {
  const woke = p.woke ? '<span class="badge woke">woke from snooze</span>' : "";
  const snoozeInfo = p.bucket === "snoozed" && p.snooze_until
    ? '<span class="badge bucket">' + esc(untilText(p.snooze_until)) + "</span>" : "";
  const archived = p.bucket === "archived" && p.archived_at
    ? '<span class="badge bucket">archived ' + esc(p.archived_at.slice(0, 10)) + "</span>" : "";
  return '<div class="card" data-id="' + esc(p.id) + '">'
    + '<div class="row1"><span class="name">' + esc(p.name) + "</span>"
    + (p.agent ? '<span class="agent">' + esc(p.agent) + "</span>" : "")
    + woke + snoozeInfo + archived
    + '<span class="when">' + esc(relTime(p.last_activity)) + "</span></div>"
    + (p.description ? '<div class="desc">' + esc(p.description) + "</div>" : "")
    + '<div class="pathrow"><span class="path" title="' + esc(p.path) + '">' + esc(p.friendly_path) + "</span>"
    + '<button class="mini" data-act="copy" data-path="' + esc(p.path) + '">Copy path</button>'
    + '<button class="mini" data-act="open" data-path="' + esc(p.path) + '">Open folder</button>'
    + "</div></div>";
}
const EMPTY_HTML = '<div id="empty"><h3>No projects here yet</h3>'
  + "<p>This dashboard watches your Hermes directories and shows every project your agents work on. Projects appear automatically as work starts — nothing to configure.</p><dl>"
  + "<dt>Active</dt><dd>Work in motion. New projects land here by default.</dd>"
  + "<dt>Research</dt><dd>Exploratory work. Move items freely between Active and Research.</dd>"
  + "<dt>Snoozed</dt><dd>Set aside until a wake time you choose; items resurface automatically.</dd>"
  + "<dt>Archive</dt><dd>Done or dormant. Files on disk are never touched; restore any time.</dd>"
  + "</dl></div>";
function render() {
  const counts = bucketCounts();
  document.querySelectorAll(".bucket-btn").forEach(btn => {
    const b = btn.dataset.bucket;
    btn.classList.toggle("selected", !state.query && state.bucket === b);
    btn.querySelector(".count").textContent = counts[b] || 0;
  });
  const title = document.getElementById("view-title");
  const cards = document.getElementById("cards");
  if (state.query) {
    title.textContent = 'Search: "' + state.query + '"';
    const r = state.search || { projects: [], files: [] };
    let html = "";
    if (r.projects.length) html += r.projects.map(cardHtml).join("");
    if (r.files.length) {
      html += '<div style="margin-top:14px" class="label">Files</div>'
        + r.files.map(f => '<div class="filehit"><div>' + esc(f.name)
          + ' <span class="agent">in ' + esc(f.project_name) + "</span></div>"
          + '<div class="path">' + esc(f.friendly_path) + "</div>"
          + '<button class="mini" data-act="copy" data-path="' + esc(f.path) + '">Copy path</button> '
          + '<button class="mini" data-act="open" data-path="' + esc(f.path) + '">Open</button>'
          + "</div>").join("");
    }
    cards.innerHTML = html || '<div id="empty"><h3>No matches</h3><p>Nothing in your Hermes roots matches that search.</p></div>';
  } else {
    title.textContent = BUCKET_LABEL[state.bucket];
    const list = state.projects
      .filter(p => p.bucket === state.bucket)
      .sort((a, b) => (b.last_activity || 0) - (a.last_activity || 0));
    cards.innerHTML = list.length ? list.map(cardHtml).join("") : EMPTY_HTML;
  }
  renderDetail();
}
function findProject(id) { return state.projects.find(p => p.id === id) || null; }
function renderDetail() {
  const el = document.getElementById("detail");
  const p = state.selected ? findProject(state.selected) : null;
  if (!p) { el.classList.remove("visible"); el.innerHTML = ""; return; }
  const inWorking = p.bucket === "active" || p.bucket === "research";
  let actions = "";
  if (inWorking) {
    const other = p.bucket === "active" ? "research" : "active";
    actions += '<button class="mini" data-act="move" data-bucket="' + other + '">Move to '
      + BUCKET_LABEL[other] + "</button>"
      + '<button class="mini" data-act="snooze-menu">Snooze&hellip;</button>'
      + '<button class="mini" data-act="archive">Archive</button>';
  } else if (p.bucket === "snoozed") {
    actions += '<button class="mini" data-act="wake">Wake now</button>'
      + '<button class="mini" data-act="snooze-menu">Extend&hellip;</button>'
      + '<button class="mini" data-act="archive">Archive</button>';
  } else {
    actions += '<button class="mini primary" data-act="restore" data-bucket="active">Restore to Active</button>'
      + '<button class="mini" data-act="restore" data-bucket="research">Restore to Research</button>';
  }
  el.innerHTML =
    '<button class="mini close" data-act="close">Close</button>'
    + "<h3>" + esc(p.name) + "</h3>"
    + '<div class="sub">' + esc(BUCKET_LABEL[p.bucket])
    + (p.agent ? " &middot; " + esc(p.agent) : "")
    + " &middot; " + esc(relTime(p.last_activity))
    + (p.woke ? ' &middot; <span class="badge woke">woke from snooze</span>' : "")
    + (p.bucket === "snoozed" ? " &middot; " + esc(untilText(p.snooze_until)) : "")
    + "</div>"
    + (p.description ? '<div class="section">' + esc(p.description) + "</div>" : "")
    + '<div class="section"><div class="label">Location</div>'
    + '<div class="path">' + esc(p.friendly_path) + "</div>"
    + '<div class="actions" style="margin-top:6px">'
    + '<button class="mini" data-act="copy" data-path="' + esc(p.path) + '">Copy path</button>'
    + '<button class="mini" data-act="open" data-path="' + esc(p.path) + '">Open folder</button>'
    + "</div></div>"
    + '<div class="section"><div class="label">Actions</div>'
    + '<div class="actions">' + actions + "</div>"
    + '<div class="snooze-menu" id="snooze-menu">'
    + '<div class="presets">'
    + '<button class="mini" data-act="snooze" data-hours="1">1 h</button>'
    + '<button class="mini" data-act="snooze" data-hours="24">1 day</button>'
    + '<button class="mini" data-act="snooze" data-hours="72">3 days</button>'
    + '<button class="mini" data-act="snooze" data-hours="168">1 week</button>'
    + "</div>"
    + '<input type="datetime-local" id="snooze-custom"> '
    + '<button class="mini" data-act="snooze-custom">Set</button>'
    + "</div></div>";
  el.classList.add("visible");
}
async function copyPath(path) {
  try {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(path);
    } else {
      const ta = document.createElement("textarea");
      ta.value = path; document.body.appendChild(ta); ta.select();
      document.execCommand("copy"); ta.remove();
    }
    toast("Path copied");
  } catch (e) { toast("Copy failed"); }
}
async function act(target) {
  const act = target.dataset.act;
  const id = state.selected;
  try {
    if (act === "copy") return copyPath(target.dataset.path);
    if (act === "open") {
      await post("/api/open", { path: target.dataset.path });
      return toast("Opening folder");
    }
    if (act === "close") { state.selected = null; return render(); }
    if (act === "snooze-menu") {
      return document.getElementById("snooze-menu").classList.toggle("visible");
    }
    if (!id) return;
    const enc = encodeURIComponent(id);
    if (act === "move") await post("/api/projects/" + enc + "/move", { bucket: target.dataset.bucket });
    else if (act === "archive") await post("/api/projects/" + enc + "/archive", {});
    else if (act === "restore") await post("/api/projects/" + enc + "/restore", { bucket: target.dataset.bucket });
    else if (act === "wake") await post("/api/projects/" + enc + "/restore", { bucket: "active" });
    else if (act === "snooze") {
      const until = new Date(Date.now() + Number(target.dataset.hours) * 3600 * 1000);
      await post("/api/projects/" + enc + "/snooze", { until: until.toISOString() });
    } else if (act === "snooze-custom") {
      const raw = document.getElementById("snooze-custom").value;
      if (!raw) return toast("Pick a date and time");
      await post("/api/projects/" + enc + "/snooze", { until: new Date(raw).toISOString() });
    } else return;
    await refresh();
  } catch (e) { toast(e.message); }
}
document.addEventListener("click", ev => {
  const btn = ev.target.closest("button[data-act]");
  if (btn) { ev.stopPropagation(); act(btn); return; }
  const bucketBtn = ev.target.closest(".bucket-btn");
  if (bucketBtn) {
    state.bucket = bucketBtn.dataset.bucket;
    state.query = ""; state.search = null;
    document.getElementById("search").value = "";
    return render();
  }
  const card = ev.target.closest(".card[data-id]");
  if (card) { state.selected = card.dataset.id; return render(); }
});
document.addEventListener("keydown", ev => {
  if (ev.key === "/" && document.activeElement !== document.getElementById("search")) {
    ev.preventDefault();
    document.getElementById("search").focus();
  } else if (ev.key === "Escape") {
    if (state.selected) { state.selected = null; render(); }
  }
});
let searchTimer = null;
document.getElementById("search").addEventListener("input", ev => {
  const q = ev.target.value.trim();
  clearTimeout(searchTimer);
  searchTimer = setTimeout(async () => {
    state.query = q;
    if (!q) { state.search = null; return render(); }
    try { state.search = await api("/api/search?q=" + encodeURIComponent(q)); }
    catch (e) { state.search = { projects: [], files: [] }; }
    render();
  }, 180);
});
refresh();
setInterval(refresh, 60000);
</script>
</body>
</html>
"""
