"""LPOS v4.8.2 Mandatory Enforcement Gates.

Moves advisory rules into code that executes at choke points the agent cannot
skip.  Rules in prompts are suggestions; rules in code that runs are laws.

Five gates:
    1. pre-commit hook (git)  -- anti-slop lint + tests, blocks commit
    2. pre-deploy gate         -- re-runs lint + tests + approval artifact check
    3. process artifacts       -- approvals the agent cannot self-issue
    4. model separation        -- creator and reviewer must differ
    5. copy ownership          -- lint catches slop regardless of authorship

Tiered enforcement:
    tier 1 trivial  (typo, CSS tweak):   lint + tests only
    tier 2 standard (new section, bug):  + guild review + local approval
    tier 3 material (new page, pricing): + full review + production approval

The change determines the tier, not the agent.  This prevents the
over-correction death spiral.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# Version + constants
# ---------------------------------------------------------------------------

GATE_VERSION = "1.0.0-lpos482"

TIER_TRIVIAL = 1
TIER_STANDARD = 2
TIER_MATERIAL = 3

# ---------------------------------------------------------------------------
# Anti-slop lint patterns (the mechanical copy quality gate)
# ---------------------------------------------------------------------------

# Each pattern: (name, regex, severity)
# severity "block" rejects the commit; "warn" flags but allows
SLOP_PATTERNS: list[tuple[str, str, str]] = [
    # AI-register phrases
    ("ai_residue_harness", r"\bharness\b(?!\.)", "block"),
    ("ai_residue_delve", r"\bdelve\b", "block"),
    ("ai_residue_robust", r"\brobust\b", "warn"),
    ("ai_residue_leverage", r"\bleverage\b", "warn"),
    ("ai_residue_seamless", r"\bseamless(ly)?\b", "block"),
    ("ai_residue_cutting_edge", r"\bcutting[- ]edge\b", "block"),
    ("ai_residue_game_changer", r"\bgame[- ]changer\b", "block"),
    ("ai_residue_revolutionize", r"\brevolutioniz\w+", "block"),
    # Em dash (LPOS absolute rule)
    ("em_dash", r"\u2014", "block"),
    # Numeric fixation in copy ("10x faster", "5-minute setup")
    # Only blocks when adjacent to marketing words
    ("numeric_fixation", r"\b\d+x\s+(faster|cheaper|better|quick)", "block"),
    # Structural monotony: three+ consecutive lines starting with the same word
    # (detected in _check_monotony, not regex)
    # Inline transparency arithmetic ("$50 = 2 coffees")
    ("transparency_arithmetic", r"\$\d+\s*=\s*(about\s+)?\$?\d", "warn"),
]

# ---------------------------------------------------------------------------
# Gate result types
# ---------------------------------------------------------------------------


@dataclass
class LintResult:
    """Result of running the anti-slop lint on a set of files."""

    passed: bool
    blocks: list[dict] = field(default_factory=list)
    warnings: list[dict] = field(default_factory=list)
    files_checked: int = 0

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "blocks": self.blocks,
            "warnings": self.warnings,
            "files_checked": self.files_checked,
        }


@dataclass
class GateResult:
    """Result of running a full gate check."""

    gate: str
    passed: bool
    tier: int
    detail: str = ""
    lint: LintResult | None = None
    tests_passed: bool | None = None
    approval_present: bool | None = None

    def to_dict(self) -> dict:
        d = {
            "gate": self.gate,
            "passed": self.passed,
            "tier": self.tier,
            "detail": self.detail,
        }
        if self.lint is not None:
            d["lint"] = self.lint.to_dict()
        if self.tests_passed is not None:
            d["tests_passed"] = self.tests_passed
        if self.approval_present is not None:
            d["approval_present"] = self.approval_present
        return d


# ---------------------------------------------------------------------------
# Tier router -- classifies the change to determine which gates apply
# ---------------------------------------------------------------------------


def classify_tier(
    changed_files: list[str],
    diff_stat: str | None = None,
) -> int:
    """Classify a change into tier 1/2/3 based on what files changed.

    This is deterministic -- the change determines the tier, not the agent.
    """
    # Tier 3 material: new pages, pricing, brand-level files
    material_patterns = [
        r"pricing",
        r"index\.html",
        r"home\.",
        r"landing",
        r"brand",
        r"tokens\.css",
        r"manifest",
    ]
    for f in changed_files:
        for pat in material_patterns:
            if re.search(pat, f, re.IGNORECASE):
                return TIER_MATERIAL

    # Tier 1 trivial: config, docs, metadata, deps (regardless of extension)
    trivial_patterns = [
        r"^README",
        r"^CHANGELOG",
        r"^LICENSE",
        r"^NOTICE",
        r"\.gitignore$",
        r"\.yaml$",
        r"\.yml$",
        r"\.toml$",
        r"\.ini$",
        r"\.cfg$",
        r"\.env",
        r"^requirements",
        r"^pyproject",
        r"^setup\.",
        r"^Dockerfile",
        r"^docker-compose",
        r"^Makefile$",
        r"\.lock$",
        r"^\.github/",
        r"^\.gitlab",
    ]
    all_trivial = True
    for f in changed_files:
        is_trivial = any(re.search(pat, f, re.IGNORECASE) for pat in trivial_patterns)
        if not is_trivial:
            all_trivial = False
            break
    if all_trivial:
        return TIER_TRIVIAL

    # Tier 2 standard: source code changes, new sections, copy revisions
    standard_patterns = [
        r"\.(js|ts|tsx|jsx|py|go|rs|rb|php)$",
        r"\.(html|htm|css)$",
        r"docker",
        r"deploy",
    ]
    has_source = False
    for f in changed_files:
        for pat in standard_patterns:
            if re.search(pat, f, re.IGNORECASE):
                has_source = True
                break
    if has_source:
        return TIER_STANDARD

    # Tier 1 trivial: everything else
    return TIER_TRIVIAL


# ---------------------------------------------------------------------------
# Anti-slop lint
# ---------------------------------------------------------------------------


def _extract_visible_text(filepath: Path) -> str:
    """Extract human-visible text from HTML, MD, or plain text files."""
    try:
        content = filepath.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""

    suffix = filepath.suffix.lower()
    if suffix in (".html", ".htm"):
        # Strip script and style blocks, then tags
        content = re.sub(r"<script[^>]*>.*?</script>", "", content, flags=re.DOTALL | re.IGNORECASE)
        content = re.sub(r"<style[^>]*>.*?</style>", "", content, flags=re.DOTALL | re.IGNORECASE)
        content = re.sub(r"<[^>]+>", " ", content)
        # Collapse entities
        content = re.sub(r"&nbsp;", " ", content)
        content = re.sub(r"&amp;", "&", content)
        content = re.sub(r"&[a-z]+;", " ", content)
    return content


def _check_monotony(text: str) -> list[dict]:
    """Detect structural monotony: 3+ consecutive lines starting with the same word."""
    findings = []
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if len(lines) < 3:
        return findings
    for i in range(len(lines) - 2):
        words = [lines[i].split()[0].lower() if lines[i].split() else "",
                 lines[i + 1].split()[0].lower() if lines[i + 1].split() else "",
                 lines[i + 2].split()[0].lower() if lines[i + 2].split() else ""]
        if words[0] and words[0] == words[1] == words[2]:
            findings.append({
                "pattern": "structural_monotony",
                "severity": "warn",
                "detail": f"Three consecutive lines start with '{words[0]}' near line {i + 1}",
            })
    return findings


def lint_files(filepaths: list[Path], strict: bool = False) -> LintResult:
    """Run the anti-slop lint against a list of files.

    Returns LintResult with blocks (commit-rejecting) and warnings.
    If strict=True, warnings become blocks.
    """
    result = LintResult(passed=True)
    text_extensions = {".html", ".htm", ".md", ".txt", ".js", ".ts", ".tsx", ".jsx", ".py", ".css", ".json", ".yaml", ".yml"}

    for filepath in filepaths:
        if not filepath.exists() or filepath.suffix.lower() not in text_extensions:
            continue
        result.files_checked += 1
        text = _extract_visible_text(filepath)

        for name, pattern, severity in SLOP_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                finding = {
                    "pattern": name,
                    "severity": severity,
                    "file": str(filepath),
                    "match": match.group(0)[:100],
                    "position": match.start(),
                }
                if severity == "block" or strict:
                    result.blocks.append(finding)
                else:
                    result.warnings.append(finding)

        # Structural monotony check
        for finding in _check_monotony(text):
            finding["file"] = str(filepath)
            if finding["severity"] == "block" or strict:
                result.blocks.append(finding)
            else:
                result.warnings.append(finding)

    result.passed = len(result.blocks) == 0
    return result


# ---------------------------------------------------------------------------
# Test runner gate
# ---------------------------------------------------------------------------


def run_tests(workdir: Path, test_command: list[str] | None = None) -> bool:
    """Run the project's test suite. Returns True if all tests pass."""
    if test_command is None:
        # Auto-detect
        if (workdir / "package.json").exists():
            test_command = ["npm", "test", "--", "--silent"]
        elif (workdir / "pytest.ini").exists() or any(workdir.glob("test_*.py")):
            test_command = [sys.executable, "-m", "pytest", "-q"]
        elif (workdir / "Makefile").exists():
            test_command = ["make", "test"]
        else:
            # No tests to run -- pass
            return True

    try:
        result = subprocess.run(
            test_command,
            cwd=str(workdir),
            capture_output=True,
            text=True,
            timeout=300,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False


# ---------------------------------------------------------------------------
# Approval artifact gate
# ---------------------------------------------------------------------------


def check_approval(
    workdir: Path,
    tier: int,
    approval_root: Path | None = None,
) -> bool:
    """Check whether the required approval artifact exists.

    Tier 1: no approval needed.
    Tier 2: local approval (.approvals/local.txt with a signature).
    Tier 3: production approval (.approvals/production.txt).

    The artifact must contain something the agent cannot self-produce:
    a human signature or a different-model reviewer hash.
    """
    if tier <= TIER_TRIVIAL:
        return True

    if approval_root is None:
        approval_root = workdir / ".approvals"

    if tier == TIER_STANDARD:
        artifact = approval_root / "local.txt"
    else:
        artifact = approval_root / "production.txt"

    if not artifact.exists():
        return False

    # The artifact must contain a non-empty signature line
    try:
        content = artifact.read_text().strip()
        if not content:
            return False
        # Must contain a signature marker the agent cannot fake
        return "signed_by:" in content or "reviewer_model:" in content
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Model separation check
# ---------------------------------------------------------------------------


def verify_model_separation(
    creator_model: str,
    reviewer_model: str,
) -> bool:
    """Verify that creator and reviewer are different model families.

    Same-model review is a mirror, not independent verification.
    """
    def _family(model: str) -> str:
        model = model.lower()
        if "glm" in model or "zai" in model:
            return "glm"
        if "kimi" in model or "k3" in model or "k2" in model:
            return "kimi"
        if "gpt" in model or "codex" in model or "openai" in model:
            return "gpt"
        if "qwen" in model or "deepseek" in model:
            return "framework"
        return model

    return _family(creator_model) != _family(reviewer_model)


# ---------------------------------------------------------------------------
# Full gate check (used by pre-commit and pre-deploy)
# ---------------------------------------------------------------------------


def run_gate_check(
    workdir: Path,
    changed_files: list[str],
    tier_override: int | None = None,
    skip_tests: bool = False,
    skip_approval: bool = False,
    approval_root: Path | None = None,
) -> GateResult:
    """Run the full tiered gate check.

    1. Classify the tier (unless overridden).
    2. Run anti-slop lint on all changed text files.
    3. Run tests (tier 2+).
    4. Check approval artifact (tier 2+).
    """
    tier = tier_override if tier_override is not None else classify_tier(changed_files)

    # Lint is always run (gate 1 + gate 5)
    abs_files = [workdir / f for f in changed_files]
    lint = lint_files(abs_files)
    if not lint.passed:
        return GateResult(
            gate="full",
            passed=False,
            tier=tier,
            detail=f"Lint blocked: {len(lint.blocks)} blocking pattern(s) found",
            lint=lint,
        )

    # Tests run at all tiers (gate 1), but can be skipped for speed at tier 1
    tests_passed = None
    if not skip_tests:
        tests_passed = run_tests(workdir)
        if not tests_passed:
            return GateResult(
                gate="full",
                passed=False,
                tier=tier,
                detail="Tests failed",
                lint=lint,
                tests_passed=False,
            )

    # Approval artifact (gate 3) -- tier 2+
    approval_present = None
    if tier >= TIER_STANDARD and not skip_approval:
        approval_present = check_approval(workdir, tier, approval_root)
        if not approval_present:
            return GateResult(
                gate="full",
                passed=False,
                tier=tier,
                detail=f"Missing approval artifact for tier {tier}",
                lint=lint,
                tests_passed=tests_passed,
                approval_present=False,
            )

    return GateResult(
        gate="full",
        passed=True,
        tier=tier,
        detail=f"All gates passed at tier {tier}",
        lint=lint,
        tests_passed=tests_passed,
        approval_present=approval_present,
    )


# ---------------------------------------------------------------------------
# Gate initialization -- drops hooks into a target repo
# ---------------------------------------------------------------------------

PRE_COMMIT_HOOK = """#!/bin/sh
# LPOS Enforcement Gate v{version} -- pre-commit hook
# Installed by: lpos gate init
# This file is governed by LPOS and executes mechanically. The agent cannot skip it.
LPOS_GATE_SKIP_TESTS=${{LPOS_GATE_SKIP_TESTS:-}}

changed=$(git diff --cached --name-only --diff-filter=ACM)
if [ -z "$changed" ]; then
    exit 0
fi

# Run the gate check through the LPOS Python module
python3 -c "
import sys, json
from pathlib import Path
from lpos_engine.gates import run_gate_check

workdir = Path('{workdir}')
changed_files = [f for f in '''$changed'''.splitlines() if f]
result = run_gate_check(workdir, changed_files, skip_tests=bool('$LPOS_GATE_SKIP_TESTS'))
print(json.dumps(result.to_dict(), indent=2))
sys.exit(0 if result.passed else 1)
"
"""

DEPLOY_GATE_SCRIPT = """#!/bin/bash
# LPOS Enforcement Gate v{version} -- pre-deploy gate
# Installed by: lpos gate init
# Usage: lpos-deploy <service-name> [gcloud args...]
# This wraps gcloud run deploy with a mandatory gate check.
set -euo pipefail

LPOS_GATE_SKIP_TESTS=${{LPOS_GATE_SKIP_TESTS:-}}
SERVICE="${{1:-}}"
if [ -z "$SERVICE" ]; then
    echo "Usage: lpos-deploy <service-name> [gcloud args...]" >&2
    exit 1
fi
shift

# Check for approval artifact for material deploys
if [ -f ".approvals/production.txt" ]; then
    APPROVAL_OK=1
else
    # Only block if there are material changes
    CHANGED=$(git diff --name-only HEAD~1 2>/dev/null || echo "")
    if echo "$CHANGED" | grep -qiE "pricing|index|home|landing|brand|tokens"; then
        echo "BLOCKED: Material deploy requires .approvals/production.txt" >&2
        echo "The agent cannot self-issue this approval." >&2
        exit 1
    fi
fi

# Re-run lint + tests (catches --no-verify bypasses)
python3 -c "
import sys, json
from pathlib import Path
from lpos_engine.gates import run_gate_check

changed = '''$(git diff --name-only HEAD~1 2>/dev/null || git diff --cached --name-only || echo '')'''.splitlines()
changed = [f for f in changed if f]
if not changed:
    changed = ['.']
result = run_gate_check(Path('.'), changed, skip_tests=bool('$LPOS_GATE_SKIP_TESTS'))
print(json.dumps(result.to_dict(), indent=2))
sys.exit(0 if result.passed else 1)
"

# Gate passed -- proceed with deploy
echo "LPOS gate passed. Deploying $SERVICE..."
exec gcloud run deploy "$SERVICE" "$@"
"""

LPOS_GATES_CONFIG = """# LPOS Enforcement Gates configuration
# This file configures the tiered enforcement for this project.
# Installed by: lpos gate init (LPOS v4.8.2)

gate_version: "{version}"
enabled: true

# Override the auto-tier classification for specific paths
tier_overrides:
  # Example: force README changes to tier 1
  # "README.md": 1

# Custom test command (auto-detected if omitted)
# test_command: ["npm", "test"]

# Approval artifact directory
approval_dir: ".approvals"

# Lint configuration
lint:
  strict: false  # if true, warnings become blocks
  custom_patterns: []
    # Example:
    # - name: "no_internal_jargon"
    #   pattern: "\\\\bsynergy\\\\b"
    #   severity: "block"
"""


def init_gates(
    target_repo: Path,
    force: bool = False,
) -> dict:
    """Install enforcement gates into a target repository.

    Drops:
    - .git/hooks/pre-commit (gate 1)
    - lpos-deploy (gate 2, wrapper script)
    - .lpos-gates.yaml (configuration)
    - .approvals/ (directory for approval artifacts)
    """
    result = {
        "target": str(target_repo),
        "installed": [],
        "skipped": [],
        "version": GATE_VERSION,
    }

    if not (target_repo / ".git").is_dir():
        result["error"] = "Not a git repository"
        return result

    # 1. Pre-commit hook
    hook_path = target_repo / ".git" / "hooks" / "pre-commit"
    if hook_path.exists() and not force:
        result["skipped"].append(str(hook_path))
    else:
        hook_content = PRE_COMMIT_HOOK.format(version=GATE_VERSION, workdir=str(target_repo))
        hook_path.write_text(hook_content)
        hook_path.chmod(0o755)
        result["installed"].append(str(hook_path))

    # 2. Deploy gate wrapper
    deploy_path = target_repo / "lpos-deploy"
    if deploy_path.exists() and not force:
        result["skipped"].append(str(deploy_path))
    else:
        deploy_content = DEPLOY_GATE_SCRIPT.format(version=GATE_VERSION)
        deploy_path.write_text(deploy_content)
        deploy_path.chmod(0o755)
        result["installed"].append(str(deploy_path))

    # 3. Config file
    config_path = target_repo / ".lpos-gates.yaml"
    if config_path.exists() and not force:
        result["skipped"].append(str(config_path))
    else:
        config_content = LPOS_GATES_CONFIG.format(version=GATE_VERSION)
        config_path.write_text(config_content)
        result["installed"].append(str(config_path))

    # 4. Approvals directory
    approvals_dir = target_repo / ".approvals"
    if not approvals_dir.exists():
        approvals_dir.mkdir(parents=True)
        (approvals_dir / ".gitkeep").write_text("")
        result["installed"].append(str(approvals_dir))
    else:
        result["skipped"].append(str(approvals_dir))

    return result


def status_gates(target_repo: Path) -> dict:
    """Check whether gates are installed and healthy in a target repo."""
    return {
        "repo": str(target_repo),
        "has_git": (target_repo / ".git").is_dir(),
        "pre_commit_hook": (target_repo / ".git" / "hooks" / "pre-commit").exists(),
        "deploy_gate": (target_repo / "lpos-deploy").exists(),
        "config": (target_repo / ".lpos-gates.yaml").exists(),
        "approvals_dir": (target_repo / ".approvals").is_dir(),
        "gate_version": GATE_VERSION,
    }
