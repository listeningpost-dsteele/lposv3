from pathlib import Path
import re, sys

root = Path(__file__).resolve().parents[1]
h = root / "Build/Hermes"
required = [
    root/"Source/LPOS-Full-Source-v2.0.zip", root/"Build/LPOS-Hermes-Compact-v3.2.zip",
    h/"CHIP-KERNEL.md", h/"SPECIALIST-INDEX.md", h/"LEDGERS.md", h/"ONBOARDING.md",
    h/"LPOS-CORE.md", h/"CRAFT-STANDARDS.md", h/"GUILDS.md", h/"SPECIALISTS.md",
    h/"STANDING-OPERATIONS.md", h/"BENCHMARKS.md", h/"INSTALL-LPOS-COMPACT.md",
    h/"MIGRATION-FROM-V2.md", h/"CRAFT-STANDARD-ROUTING.yaml",
    h/"skills/quality-router/SKILL.md", h/"skills/independent-reviewer/SKILL.md",
    h/"skills/system-auditor/SKILL.md",
]
errors = [f"missing file: {p.relative_to(root)}" for p in required if not p.exists()]

if not errors:
    routing = (h/"CRAFT-STANDARD-ROUTING.yaml").read_text()
    standards = (h/"CRAFT-STANDARDS.md").read_text()
    guilds_txt = (h/"GUILDS.md").read_text()
    specs = (h/"SPECIALISTS.md").read_text()
    sos = (h/"STANDING-OPERATIONS.md").read_text()

    # 1. every CS referenced in routing is defined
    defined_cs = set(re.findall(r"^id:\s*(CS-\d+)", standards, re.M))
    for cs in set(re.findall(r"CS-\d+", routing)):
        if cs not in defined_cs:
            errors.append(f"routing references undefined {cs}")
    # 2. every defined CS is reachable from routing
    for cs in sorted(defined_cs - set(re.findall(r"CS-\d+", routing))):
        errors.append(f"{cs} defined but unreachable from routing")
    # 3. every routing guild key exists as a guild title
    titles = set(re.findall(r"^title:\s*(.+?) Guild Charter", guilds_txt, re.M))
    for key in re.findall(r"^  ([A-Za-z][A-Za-z &-]+):\s*\[", routing, re.M):
        if key not in titles:
            errors.append(f"routing guild '{key}' has no guild charter")
    # 4. every specialist's guild has a routing entry
    for g in set(re.findall(r"^guild:\s*(.+)$", specs, re.M)):
        if f"\n  {g.strip()}:" not in routing:
            errors.append(f"specialist guild '{g.strip()}' missing from routing")
    # 5. front matter must start at column 1 (v3.0 indentation bug)
    if re.search(r"^    id:\s*CS-\d+", standards, re.M):
        errors.append("CRAFT-STANDARDS.md has indented front matter")
    # 6. every SO defines owner, specialists, Inputs, Outputs
    for sec in sos.split("## Source:")[1:]:
        m = re.search(r"id: (SO-\d+)", sec)
        if not m:
            continue
        so = m.group(1)
        if "owner: Chip" not in sec:
            errors.append(f"{so} missing machine owner")
        if "specialists:" not in sec:
            errors.append(f"{so} missing specialists")
        if so != "SO-021" and ("## Inputs" not in sec or "## Outputs" not in sec):
            errors.append(f"{so} missing Inputs/Outputs")
    # 7. specialist index covers every charter id
    index = (h/"SPECIALIST-INDEX.md").read_text()
    for sid in re.findall(r"^id:\s*SPECIALIST-(\d+)", specs, re.M):
        if not re.search(r"^\| %s " % sid, index, re.M):
            errors.append(f"SPECIALIST-{sid} missing from SPECIALIST-INDEX.md")
    # 8. no broken relative path claims in skills
    for skill in (h/"skills").rglob("SKILL.md"):
        for ref in re.findall(r"`([\w./-]+\.(?:md|yaml))`", skill.read_text()):
            if "/" in ref and not (h/ref).exists() and not (root/ref).exists():
                errors.append(f"{skill.relative_to(root)} references missing path {ref}")
    # 9. quality router lists all five gates
    qr = (h/"skills/quality-router/SKILL.md").read_text()
    for gate in ["Intent", "Truth", "Reasoning", "Craft", "Outcome"]:
        if gate not in qr:
            errors.append(f"quality-router missing {gate} gate")

if errors:
    print("FAIL:", *errors, sep="\n- "); sys.exit(1)
print("PASS: structure and cross-references verified.")
