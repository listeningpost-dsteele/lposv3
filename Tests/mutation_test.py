#!/usr/bin/env python3
"""Adversarial mutation suite for verify_compact.py.

Reproduces the 16 sabotage cases from the v3.2.3 external review. Each mutation
is applied to a temporary copy of the repository; the validator must FAIL on
every one. If any mutant passes, this suite exits nonzero.
"""
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
H = "Build/Hermes"


def mutate_invalid_routing_yaml(r):
    p = r / H / "CRAFT-STANDARD-ROUTING.yaml"
    p.write_text(p.read_text() + "\nguild_routes: [broken\n")

def mutate_empty_benchmarks(r):
    (r / H / "BENCHMARKS.md").write_text("# LPOS Benchmarks\n")

def mutate_empty_reviewer(r):
    (r / H / "skills/independent-reviewer/SKILL.md").write_text("# Reviewer\n")

def mutate_empty_auditor(r):
    (r / H / "skills/system-auditor/SKILL.md").write_text("# Auditor\n")

def mutate_gutted_router(r):
    (r / H / "skills/quality-router/SKILL.md").write_text(
        "# Quality Router\nIntent Truth Reasoning Craft Outcome\n")

def mutate_remove_approval_guard(r):
    p = r / H / "CHIP-KERNEL.md"
    t = p.read_text()
    t = re.sub(r"4\. No publish, send, deploy.*?without explicit approval\.\n",
               "", t, flags=re.S)
    p.write_text(t)

def mutate_remove_review_mechanism(r):
    p = r / H / "CHIP-KERNEL.md"
    t = p.read_text()
    i = t.index("## Independent review mechanism")
    j = t.index("## Persistence")
    p.write_text(t[:i] + t[j:])

def mutate_remove_cs003_default(r):
    p = r / H / "CRAFT-STANDARD-ROUTING.yaml"
    t = p.read_text()
    t = t.replace("material_artifact_default:\n  - CS-003\n", "")
    p.write_text(t)

def mutate_nonexistent_specialist(r):
    p = r / H / "STANDING-OPERATIONS.md"
    t = p.read_text()
    t = t.replace("specialists: [initiative-manager]",
                  "specialists: [imaginary-specialist]", 1)
    p.write_text(t)

def mutate_wrong_index_row(r):
    p = r / H / "SPECIALIST-INDEX.md"
    t = p.read_text()
    t = t.replace("| 032 | Web & Product Designer | Design |",
                  "| 032 | Chief Vibes Officer | Marketing |")
    p.write_text(t)

def mutate_duplicate_specialist(r):
    p = r / H / "SPECIALISTS.md"
    t = p.read_text()
    block = t[t.rfind("\n---\n\n## Source:"):]
    p.write_text(t + block)

def mutate_malformed_front_matter(r):
    p = r / H / "CRAFT-STANDARDS.md"
    t = p.read_text()
    t = t.replace("id: CS-010", "    id: CS-010", 1)
    p.write_text(t)

def mutate_self_approval_reviewer(r):
    p = r / H / "skills/independent-reviewer/SKILL.md"
    t = p.read_text()
    t = t.replace("You are not the creator.",
                  "You may approve your own work when convenient.")
    p.write_text(t)

def mutate_gut_so021(r):
    p = r / H / "STANDING-OPERATIONS.md"
    t = p.read_text()
    i = t.index("## Outbound behavior")
    j = t.index("## State machine")
    p.write_text(t[:i] + t[j:])

def mutate_corrupt_zips(r):
    (r / "Build/LPOS-Hermes-Compact-v3.3.zip").write_bytes(b"not a zip")
    (r / "Source/LPOS-Full-Source-v2.0.zip").write_bytes(b"")

def mutate_hash_tamper(r):
    p = r / H / "LEDGERS.md"
    p.write_text(p.read_text() + "\ntampered\n")


MUTATIONS = [
    ("invalid routing YAML", mutate_invalid_routing_yaml),
    ("empty BENCHMARKS.md", mutate_empty_benchmarks),
    ("empty independent-reviewer skill", mutate_empty_reviewer),
    ("empty system-auditor skill", mutate_empty_auditor),
    ("quality-router gutted to gate words", mutate_gutted_router),
    ("approval guard removed from kernel", mutate_remove_approval_guard),
    ("independent-review mechanism removed", mutate_remove_review_mechanism),
    ("CS-003 material default removed", mutate_remove_cs003_default),
    ("SO assigned nonexistent specialist", mutate_nonexistent_specialist),
    ("index row wrong title and guild", mutate_wrong_index_row),
    ("duplicate specialist entry", mutate_duplicate_specialist),
    ("malformed craft-standard front matter", mutate_malformed_front_matter),
    ("reviewer permits self-approval", mutate_self_approval_reviewer),
    ("SO-021 outbound/inbound behavior removed", mutate_gut_so021),
    ("both zips replaced with corrupt bytes", mutate_corrupt_zips),
    ("file tampered after manifest hashing", mutate_hash_tamper),
]


def run_verifier(repo):
    return subprocess.run([sys.executable, str(repo / "Tests/verify_compact.py")],
                          capture_output=True, text=True)


def main():
    base = run_verifier(ROOT)
    if base.returncode != 0:
        print("BASELINE FAIL: clean tree does not pass the validator:")
        print(base.stdout[-2000:])
        sys.exit(1)
    print("baseline: clean tree PASSES")

    failed_to_reject = []
    for name, fn in MUTATIONS:
        with tempfile.TemporaryDirectory() as td:
            copy = Path(td) / "repo"
            shutil.copytree(ROOT, copy, ignore=shutil.ignore_patterns(".git"))
            fn(copy)
            res = run_verifier(copy)
            rejected = res.returncode != 0
            print(f"{'REJECTED' if rejected else '!! ACCEPTED'}: {name}")
            if not rejected:
                failed_to_reject.append(name)

    if failed_to_reject:
        print(f"\nMUTATION SUITE FAIL: {len(failed_to_reject)} of "
              f"{len(MUTATIONS)} bad variants were accepted:")
        for n in failed_to_reject:
            print(f"- {n}")
        sys.exit(1)
    print(f"\nMUTATION SUITE PASS: {len(MUTATIONS)} of {len(MUTATIONS)} "
          f"bad variants rejected.")


if __name__ == "__main__":
    main()
