#!/usr/bin/env python3
"""LPOS distribution validator v2.

Parses every YAML block, validates component schemas, resolves the full
reference graph, opens and compares both archives, checks manifest hashes and
version consistency, and scans for secrets and hardcoded identity.

Exit 0 only when every check passes. The PASS message states what was checked;
it does not claim runtime behavior was verified.
"""
import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path

try:
    import yaml
except ImportError:
    print("FAIL: pyyaml is required (pip install pyyaml)")
    sys.exit(2)

ROOT = Path(__file__).resolve().parents[1]
H = ROOT / "Build/Hermes"
VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")
errors = []
checks = 0


def err(msg):
    errors.append(msg)


def check(cond, msg):
    global checks
    checks += 1
    if not cond:
        err(msg)


BOOKS = ["LPOS-CORE.md", "CRAFT-STANDARDS.md", "GUILDS.md", "SPECIALISTS.md",
         "STANDING-OPERATIONS.md", "BENCHMARKS.md"]
STANDALONE = ["CHIP-KERNEL.md", "SPECIALIST-INDEX.md", "LEDGERS.md", "ONBOARDING.md",
              "INSTALL-LPOS-COMPACT.md", "MIGRATION-FROM-V2.md", "SCHEMAS.md",
              "CRAFT-STANDARD-ROUTING.yaml", "skills/quality-router/SKILL.md",
              "skills/independent-reviewer/SKILL.md", "skills/system-auditor/SKILL.md"]
REQUIRED = [ROOT / "Source/LPOS-Full-Source-v2.0.zip",
            ROOT / "Build/LPOS-Hermes-Compact-v3.3.zip",
            ROOT / "Tools/compile.py", ROOT / "Source/v3/BOOKS.json",
            ROOT / "MANIFEST.json", ROOT / "CHANGELOG.md"] + \
           [H / b for b in BOOKS] + [H / s for s in STANDALONE]

for p in REQUIRED:
    check(p.exists() and p.stat().st_size > 0,
          f"missing or empty: {p.relative_to(ROOT)}")
if errors:
    print("FAIL:", *errors, sep="\n- ")
    sys.exit(1)


def front_matter_blocks(book_text, book_name):
    """Yield (front_matter_dict, body_text) for each '## Source:' section."""
    out = []
    for chunk in book_text.split("\n---\n\n## Source: ")[1:]:
        m = re.match(r"`[^`]+`\n\n---\n(.*?)\n---\n(.*)", chunk, re.S)
        if not m:
            err(f"{book_name}: section without parseable front matter: {chunk[:60]!r}")
            continue
        try:
            fm = yaml.safe_load(m.group(1))
        except yaml.YAMLError as e:
            err(f"{book_name}: invalid front-matter YAML: {e}")
            continue
        if not isinstance(fm, dict):
            err(f"{book_name}: front matter is not a mapping: {m.group(1)[:60]!r}")
            continue
        out.append((fm, m.group(2)))
    return out


texts = {b: (H / b).read_text() for b in BOOKS}
texts.update({s: (H / s).read_text() for s in STANDALONE})

# ---------- 1. Parse all component collections ----------
collections = {}
for book in BOOKS:
    collections[book] = front_matter_blocks(texts[book], book)

for book in BOOKS:
    check(not re.search(r"^    id:\s", texts[book], re.M),
          f"{book}: indented front matter present")

# ---------- 2. Routing YAML ----------
try:
    routing = yaml.safe_load(texts["CRAFT-STANDARD-ROUTING.yaml"])
except yaml.YAMLError as e:
    routing = None
    err(f"CRAFT-STANDARD-ROUTING.yaml: invalid YAML: {e}")
if isinstance(routing, dict):
    check(isinstance(routing.get("guild_routes"), dict) and routing["guild_routes"],
          "routing: guild_routes missing or empty")
    check("CS-003" in (routing.get("material_artifact_default") or []),
          "routing: material_artifact_default must include CS-003")
    check(set(routing.get("default") or []) >= {"LPOS-026", "LPOS-027"},
          "routing: default must include LPOS-026 and LPOS-027")
else:
    check(False, "routing: top level is not a mapping")

# ---------- 3. Schemas, unique IDs and slugs ----------
def ids_of(book, key="id"):
    return [fm.get(key) for fm, _ in collections[book]]

def dupes(seq):
    seen, d = set(), set()
    for x in seq:
        (d if x in seen else seen).add(x)
    return d

specialists, guilds, sos, cs_list, benches = {}, {}, {}, {}, {}

for fm, body in collections["SPECIALISTS.md"]:
    sid = fm.get("id", "?")
    specialists[sid] = (fm, body)
    for field in ["id", "title", "version", "status", "owner", "guild", "craft_standards"]:
        check(fm.get(field), f"{sid}: specialist missing front-matter field '{field}'")
    m = fm.get("machine") or {}
    check(m.get("type") == "specialist" and m.get("slug"),
          f"{sid}: machine.type/slug invalid")
    for sec in ["## Mission", "## Responsibilities", "## Non-responsibilities",
                "## Inputs", "## Output contract", "## Escalation", "## Success criteria"]:
        check(sec in body, f"{sid}: missing section {sec}")

for fm, body in collections["GUILDS.md"]:
    gid = fm.get("id", "?")
    guilds[fm.get("title", "").replace(" Guild Charter", "")] = fm
    check((fm.get("machine") or {}).get("type") == "guild", f"{gid}: machine.type != guild")
    for sec in ["## Mission", "## Responsibilities", "## Boundaries", "## Conformance"]:
        check(sec in body, f"{gid}: missing section {sec}")

for fm, body in collections["STANDING-OPERATIONS.md"]:
    oid = fm.get("id", "?")
    sos[oid] = (fm, body)
    m = fm.get("machine") or {}
    check(m.get("type") == "standing_operation", f"{oid}: machine.type invalid")
    check(m.get("owner") == "Chip", f"{oid}: machine.owner must be Chip")
    check(isinstance(m.get("specialists"), list) and m["specialists"],
          f"{oid}: machine.specialists missing")
    check(m.get("trigger") and m.get("communication_intent"),
          f"{oid}: trigger/communication_intent missing")
    for sec in ["## Mission", "## Objective", "## Required capabilities",
                "## Success criteria", "## Failure conditions"]:
        check(sec in body, f"{oid}: missing section {sec}")
    if oid == "SO-021":
        for sec in ["## Outbound behavior", "## Inbound behavior", "## State machine",
                    "## Activation"]:
            check(sec in body, f"SO-021: missing section {sec}")
        check("Silence never becomes consent" in body,
              "SO-021: silence-is-not-consent rule missing")
    else:
        for sec in ["## Inputs", "## Outputs"]:
            check(sec in body, f"{oid}: missing section {sec}")

for fm, body in collections["CRAFT-STANDARDS.md"]:
    cs_list[fm.get("id", "?")] = fm
    check("Required review" in body, f"{fm.get('id')}: missing Required review")

for fm, body in collections["BENCHMARKS.md"]:
    benches[fm.get("id", "?")] = fm

for book, key_ids in [("SPECIALISTS.md", list(specialists)), ("GUILDS.md", ids_of("GUILDS.md")),
                      ("STANDING-OPERATIONS.md", list(sos)), ("CRAFT-STANDARDS.md", list(cs_list)),
                      ("BENCHMARKS.md", list(benches))]:
    raw = key_ids if book != "SPECIALISTS.md" else \
        [fm.get("id") for fm, _ in collections["SPECIALISTS.md"]]
    d = dupes(raw)
    check(not d, f"{book}: duplicate ids {sorted(d)}")
slugs = [(fm.get("machine") or {}).get("slug") for fm, _ in collections["SPECIALISTS.md"]]
check(not dupes(slugs), f"SPECIALISTS.md: duplicate slugs {sorted(dupes(slugs))}")

# ---------- 4. Reference graph ----------
if isinstance(routing, dict) and isinstance(routing.get("guild_routes"), dict):
    routed_cs = set(routing.get("material_artifact_default") or [])
    for g, lst in routing["guild_routes"].items():
        check(g in guilds, f"routing guild '{g}' has no guild charter")
        for cs in lst or []:
            routed_cs.add(cs)
            check(cs in cs_list, f"routing references undefined {cs}")
    for cs in cs_list:
        check(cs in routed_cs, f"{cs} defined but unreachable from routing")
    for sid, (fm, _) in specialists.items():
        check(fm.get("guild") in routing["guild_routes"],
              f"{sid}: guild '{fm.get('guild')}' missing from routing")

slugset = set(slugs)
for oid, (fm, _) in sos.items():
    for s in (fm.get("machine") or {}).get("specialists", []):
        check(s in slugset, f"{oid}: unknown specialist slug '{s}'")

for sid in specialists:
    n = sid.split("-")[1]
    check(f"BENCH-S{n}" in benches, f"{sid}: no BENCH-S{n} benchmark")
for bid, fm in benches.items():
    comp = fm.get("component")
    if comp and str(comp).startswith("SPECIALIST"):
        check(comp in specialists, f"{bid}: component {comp} does not exist")

# exact index match: number, title, guild
index = texts["SPECIALIST-INDEX.md"]
for sid, (fm, _) in specialists.items():
    n = sid.split("-")[1]
    row = re.search(r"^\| %s \| ([^|]+) \| ([^|]+) \|" % n, index, re.M)
    check(bool(row), f"{sid}: missing from SPECIALIST-INDEX.md")
    if row:
        check(row.group(1).strip() == fm.get("title"),
              f"{sid}: index title '{row.group(1).strip()}' != charter '{fm.get('title')}'")
        check(row.group(2).strip() == fm.get("guild"),
              f"{sid}: index guild '{row.group(2).strip()}' != charter '{fm.get('guild')}'")

# ---------- 5. Safety-content assertions (whitespace-normalized) ----------
def flat(s):
    return re.sub(r"\s+", " ", s)

kernel = flat(texts["CHIP-KERNEL.md"])
check("No publish, send, deploy, purchase, delete" in kernel and
      "without explicit approval" in kernel, "kernel: approval guard missing")
check("## Independent review mechanism" in kernel and "review envelope" in kernel,
      "kernel: independent review mechanism missing")
check("NEVER includes the creation conversation" in kernel,
      "kernel: review-envelope exclusion missing")
check("## Materiality (LPOS-030)" in kernel, "kernel: materiality digest missing")
check("## Interpretation contract" in kernel, "kernel: interpretation contract missing")

rev = flat(texts["skills/independent-reviewer/SKILL.md"])
check("You are not the creator." in rev, "reviewer: self-approval ban missing")
check("Decision: PASS or REJECT" in rev, "reviewer: decision contract missing")
check("Isolation" in rev and "review envelope" in rev, "reviewer: envelope isolation missing")

qr = flat(texts["skills/quality-router/SKILL.md"])
for phrase in ["Intent Gate", "interpretation contract", "review envelope",
               "material_artifact_default", "Truth", "Reasoning", "Craft", "Outcome"]:
    check(phrase in qr, f"quality-router: missing '{phrase}'")
check(len(qr) > 800, "quality-router: implausibly short")

aud = texts["skills/system-auditor/SKILL.md"]
check("gap report" in aud and len(aud) > 400, "system-auditor: content missing")

check("LPOS-030" in texts["LPOS-CORE.md"], "LPOS-CORE: materiality standard missing")
check(len(texts["BENCHMARKS.md"]) > 10000 and len(benches) >= 42,
      f"BENCHMARKS.md: expected >=42 benchmarks, found {len(benches)}")

# ---------- 6. Archives ----------
inner = ROOT / "Build/LPOS-Hermes-Compact-v3.3.zip"
try:
    with zipfile.ZipFile(inner) as z:
        bad = z.testzip()
        check(bad is None, f"inner zip corrupt member: {bad}")
        zmap = {}
        for n in z.namelist():
            if n.endswith("/"):
                continue
            rel = n.split("/", 1)[1] if "/" in n else n
            zmap[rel] = z.read(n)
        disk = {str(p.relative_to(H)): p.read_bytes() for p in H.rglob("*") if p.is_file()}
        check(set(zmap) == set(disk),
              f"inner zip file set differs from Build/Hermes "
              f"(only-in-zip={sorted(set(zmap)-set(disk))[:3]}, "
              f"only-on-disk={sorted(set(disk)-set(zmap))[:3]})")
        for relname in set(zmap) & set(disk):
            check(zmap[relname] == disk[relname], f"inner zip content differs: {relname}")
except zipfile.BadZipFile:
    check(False, "Build/LPOS-Hermes-Compact-v3.3.zip is not a valid zip")
try:
    with zipfile.ZipFile(ROOT / "Source/LPOS-Full-Source-v2.0.zip") as z:
        check(z.testzip() is None and len(z.namelist()) > 100,
              "source archive corrupt or implausibly small")
except zipfile.BadZipFile:
    check(False, "Source/LPOS-Full-Source-v2.0.zip is not a valid zip")

# ---------- 7. Compiler roundtrip ----------
import subprocess
r = subprocess.run([sys.executable, str(ROOT / "Tools/compile.py"), "--check"],
                   capture_output=True, text=True)
check(r.returncode == 0, f"compile --check failed: {r.stdout}{r.stderr}")

# ---------- 8. Manifest hashes + version consistency ----------
manifest = json.loads((ROOT / "MANIFEST.json").read_text())
ver = manifest.get("version", "")
check(bool(VERSION_RE.match(ver)), f"manifest version invalid: {ver}")
chl = (ROOT / "CHANGELOG.md").read_text()
top = re.search(r"^## (\d+\.\d+\.\d+)", chl, re.M)
check(bool(top) and top.group(1) == ver,
      f"CHANGELOG top entry {top.group(1) if top else None} != manifest {ver}")
kv = re.search(r"Chip Kernel v(\d+\.\d+\.\d+)", texts["CHIP-KERNEL.md"])
check(bool(kv) and kv.group(1) == ver, f"kernel version {kv.group(1) if kv else None} != {ver}")
hashes = manifest.get("sha256", {})
check(bool(hashes), "manifest: sha256 map missing")
for rel, want in hashes.items():
    p = ROOT / rel
    if not p.exists():
        check(False, f"manifest lists missing file {rel}")
        continue
    got = hashlib.sha256(p.read_bytes()).hexdigest()
    check(got == want, f"hash mismatch: {rel}")
listed = set(hashes)
actual = {str(p.relative_to(ROOT)) for p in ROOT.rglob("*")
          if p.is_file() and ".git" not in p.parts and p.name != "MANIFEST.json"}
check(listed == actual,
      f"manifest file list differs (unlisted={sorted(actual-listed)[:3]}, "
      f"ghost={sorted(listed-actual)[:3]})")

# ---------- 9. Secret and identity scan ----------
SECRET_PATTERNS = [r"ghp_[A-Za-z0-9]{20,}", r"xox[baprs]-", r"AKIA[0-9A-Z]{16}",
                   r"-----BEGIN [A-Z ]*PRIVATE KEY", r"\b\d{8,10}:AA[0-9A-Za-z_-]{30,}"]
IDENTITY = [r"listeningpost\.ai", r"dsteele", r"dtsteele", r"/Users/dan"]
for base in [H, ROOT / "Source/v3", ROOT / "Tools"]:
    for p in base.rglob("*"):
        if not p.is_file() or p.suffix in {".zip", ".png"}:
            continue
        body = p.read_text(errors="ignore")
        for pat in SECRET_PATTERNS:
            check(not re.search(pat, body), f"possible secret in {p.relative_to(ROOT)} ({pat})")
        for pat in IDENTITY:
            check(not re.search(pat, body),
                  f"hardcoded identity in {p.relative_to(ROOT)} ({pat})")

# ---------- 10. Fixture coverage ----------
fixdir = ROOT / "Tests/benchmark-fixtures"
fixtures = sorted(d.name for d in fixdir.iterdir() if d.is_dir()) if fixdir.exists() else []
components = len(specialists) + len(sos)
FIXTURE_FLOOR = 8
check(len(fixtures) >= FIXTURE_FLOOR,
      f"fixture count {len(fixtures)} below committed floor {FIXTURE_FLOOR}")
for f in fixtures:
    fy = fixdir / f / "fixture.yaml"
    check(fy.exists(), f"fixture {f}: fixture.yaml missing")
    if fy.exists():
        try:
            spec = yaml.safe_load(fy.read_text())
            for field in ["id", "component", "inputs", "expected", "evaluation", "evidence"]:
                check(field in (spec or {}), f"fixture {f}: missing field '{field}'")
        except yaml.YAMLError as e:
            check(False, f"fixture {f}: invalid YAML: {e}")

if errors:
    print(f"FAIL ({len(errors)} of {checks} checks):", *errors, sep="\n- ")
    sys.exit(1)
print(f"PASS: {checks} contract checks passed "
      f"(schemas, reference graph, safety content, archives, hashes, secrets).")
print(f"Fixture coverage: {len(fixtures)} fixed benchmark fixtures for "
      f"{components} components; floor {FIXTURE_FLOOR}. "
      f"Runtime behavior is NOT verified by this script.")
