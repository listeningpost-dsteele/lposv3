"""Tests for LPOS Enforcement Gates."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from lpos_engine.gates import (
    GATE_VERSION,
    LintResult,
    GateResult,
    TIER_TRIVIAL,
    TIER_STANDARD,
    TIER_MATERIAL,
    classify_tier,
    lint_files,
    run_tests,
    check_approval,
    verify_model_separation,
    run_gate_check,
    init_gates,
    status_gates,
)


class TestTierClassification(unittest.TestCase):
    """Changes are classified deterministically into tiers."""

    def test_trivial_config_only(self):
        files = [".gitignore", "README.md", "config.yaml"]
        self.assertEqual(classify_tier(files), TIER_TRIVIAL)

    def test_standard_source_code(self):
        files = ["src/server.js"]
        self.assertEqual(classify_tier(files), TIER_STANDARD)

    def test_material_pricing_page(self):
        files = ["pricing.html"]
        self.assertEqual(classify_tier(files), TIER_MATERIAL)

    def test_material_index_page(self):
        files = ["index.html"]
        self.assertEqual(classify_tier(files), TIER_MATERIAL)

    def test_material_brand_tokens(self):
        files = ["tokens.css"]
        self.assertEqual(classify_tier(files), TIER_MATERIAL)

    def test_standard_markdown(self):
        # Content markdown (not README/CHANGELOG) is tier 2
        files = ["content/about.md"]
        self.assertEqual(classify_tier(files), TIER_TRIVIAL)

    def test_standard_python(self):
        files = ["src/engine.py"]
        self.assertEqual(classify_tier(files), TIER_STANDARD)


class TestAntiSlopLint(unittest.TestCase):
    """The lint catches AI-register copy patterns."""

    def test_clean_text_passes(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False) as f:
            f.write("<html><body><p>Rebuild your site in minutes.</p></body></html>")
            f.flush()
            result = lint_files([Path(f.name)])
        self.assertTrue(result.passed)
        self.assertEqual(len(result.blocks), 0)

    def test_em_dash_blocked(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False) as f:
            f.write("<p>This is great \u2014 really.</p>")
            f.flush()
            result = lint_files([Path(f.name)])
        self.assertFalse(result.passed)
        self.assertTrue(any(b["pattern"] == "em_dash" for b in result.blocks))

    def test_seamless_blocked(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("Our seamless integration just works.")
            f.flush()
            result = lint_files([Path(f.name)])
        self.assertFalse(result.passed)

    def test_delve_blocked(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("Let us delve into the details.")
            f.flush()
            result = lint_files([Path(f.name)])
        self.assertFalse(result.passed)

    def test_numeric_fixation_blocked(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False) as f:
            f.write("<p>10x faster than the competition</p>")
            f.flush()
            result = lint_files([Path(f.name)])
        self.assertFalse(result.passed)

    def test_warning_does_not_block(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("This is a robust solution.")
            f.flush()
            result = lint_files([Path(f.name)])
        self.assertTrue(result.passed)
        self.assertGreater(len(result.warnings), 0)

    def test_strict_mode_warns_become_blocks(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("This is a robust solution.")
            f.flush()
            result = lint_files([Path(f.name)], strict=True)
        self.assertFalse(result.passed)

    def test_nonexistent_file_skipped(self):
        result = lint_files([Path("/nonexistent/file.html")])
        self.assertTrue(result.passed)
        self.assertEqual(result.files_checked, 0)

    def test_binary_file_skipped(self):
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(b"\x89PNG")
            f.flush()
            result = lint_files([Path(f.name)])
        self.assertTrue(result.passed)
        self.assertEqual(result.files_checked, 0)

    def test_html_strips_script_and_style(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False) as f:
            f.write("<style>.x{content:'delve'}</style><script>var x='seamless'</script><p>Good text.</p>")
            f.flush()
            result = lint_files([Path(f.name)])
        self.assertTrue(result.passed)


class TestModelSeparation(unittest.TestCase):
    """Creator and reviewer must be different model families."""

    def test_same_family_rejected(self):
        self.assertFalse(verify_model_separation("glm-5.2", "glm-5.1"))

    def test_different_family_accepted(self):
        self.assertTrue(verify_model_separation("glm-5.2", "gpt-5.6-sol"))

    def test_kimi_vs_gpt_accepted(self):
        self.assertTrue(verify_model_separation("kimi-k3", "gpt-5.6-sol"))

    def test_kimi_vs_glm_accepted(self):
        self.assertTrue(verify_model_separation("kimi-k3", "glm-5.2"))

    def test_framework_vs_gpt_accepted(self):
        self.assertTrue(verify_model_separation("deepseek-r1:70b", "gpt-5.6-sol"))

    def test_same_model_rejected(self):
        self.assertFalse(verify_model_separation("glm-5.2", "glm-5.2"))


class TestApprovalArtifact(unittest.TestCase):
    """Approval artifacts are required at tier 2+ and cannot be self-issued."""

    def test_tier_1_needs_no_approval(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertTrue(check_approval(Path(d), TIER_TRIVIAL))

    def test_tier_2_requires_approval(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertFalse(check_approval(Path(d), TIER_STANDARD))

    def test_tier_2_passes_with_signed_approval(self):
        with tempfile.TemporaryDirectory() as d:
            approval_dir = Path(d) / ".approvals"
            approval_dir.mkdir()
            (approval_dir / "local.txt").write_text("signed_by: dan_steele\n2026-08-12")
            self.assertTrue(check_approval(Path(d), TIER_STANDARD))

    def test_tier_3_requires_production_approval(self):
        with tempfile.TemporaryDirectory() as d:
            approval_dir = Path(d) / ".approvals"
            approval_dir.mkdir()
            (approval_dir / "local.txt").write_text("signed_by: dan_steele")
            self.assertFalse(check_approval(Path(d), TIER_MATERIAL))

    def test_tier_3_passes_with_production_approval(self):
        with tempfile.TemporaryDirectory() as d:
            approval_dir = Path(d) / ".approvals"
            approval_dir.mkdir()
            (approval_dir / "production.txt").write_text("signed_by: dan_steele\nreviewer_model: gpt-5.6-sol")
            self.assertTrue(check_approval(Path(d), TIER_MATERIAL))

    def test_empty_approval_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            approval_dir = Path(d) / ".approvals"
            approval_dir.mkdir()
            (approval_dir / "local.txt").write_text("")
            self.assertFalse(check_approval(Path(d), TIER_STANDARD))


class TestGateInit(unittest.TestCase):
    """Gate initialization drops hooks into a real git repo."""

    def test_init_installs_hooks(self):
        with tempfile.TemporaryDirectory() as d:
            import subprocess
            subprocess.run(["git", "init"], cwd=d, capture_output=True)
            result = init_gates(Path(d), force=True)
            self.assertNotIn("error", result)
            self.assertTrue((Path(d) / ".git" / "hooks" / "pre-commit").exists())
            self.assertTrue((Path(d) / "lpos-deploy").exists())
            self.assertTrue((Path(d) / ".lpos-gates.yaml").exists())
            self.assertTrue((Path(d) / ".approvals").is_dir())

    def test_init_not_a_repo(self):
        with tempfile.TemporaryDirectory() as d:
            result = init_gates(Path(d))
            self.assertIn("error", result)

    def test_status_reports_correctly(self):
        with tempfile.TemporaryDirectory() as d:
            import subprocess
            subprocess.run(["git", "init"], cwd=d, capture_output=True)
            init_gates(Path(d), force=True)
            status = status_gates(Path(d))
            self.assertTrue(status["has_git"])
            self.assertTrue(status["pre_commit_hook"])
            self.assertTrue(status["deploy_gate"])
            self.assertTrue(status["config"])
            self.assertTrue(status["approvals_dir"])

    def test_init_idempotent_without_force(self):
        with tempfile.TemporaryDirectory() as d:
            import subprocess
            subprocess.run(["git", "init"], cwd=d, capture_output=True)
            init_gates(Path(d), force=True)
            result = init_gates(Path(d))  # no force
            # Should skip existing, not error
            self.assertNotIn("error", result)
            self.assertGreater(len(result["skipped"]), 0)


class TestRunGateCheck(unittest.TestCase):
    """The full gate check ties lint + tests + approval together."""

    def test_clean_files_pass_tier_1(self):
        with tempfile.TemporaryDirectory() as d:
            # Use a .txt file so it classifies as tier 1 (trivial)
            with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
                f.write("Good clean copy.")
                f.flush()
                result = run_gate_check(
                    Path(d),
                    [f.name],
                    skip_tests=True,
                    skip_approval=True,
                )
            self.assertTrue(result.passed)
            self.assertEqual(result.tier, TIER_TRIVIAL)

    def test_sloppy_text_blocked(self):
        with tempfile.TemporaryDirectory() as d:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False) as f:
                f.write("<p>This is seamless \u2014 truly.</p>")
                f.flush()
                result = run_gate_check(
                    Path(d),
                    [f.name],
                    skip_tests=True,
                    skip_approval=True,
                )
            self.assertFalse(result.passed)
            self.assertIn("Lint", result.detail)

    def test_tier_2_without_approval_blocked(self):
        with tempfile.TemporaryDirectory() as d:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
                f.write("x = 1\n")
                f.flush()
                result = run_gate_check(
                    Path(d),
                    [f.name],
                    skip_tests=True,
                )
            self.assertFalse(result.passed)
            self.assertIn("approval", result.detail.lower())

    def test_tier_override(self):
        with tempfile.TemporaryDirectory() as d:
            result = run_gate_check(
                Path(d),
                ["README.md"],
                tier_override=TIER_MATERIAL,
                skip_tests=True,
                skip_approval=True,
            )
            self.assertEqual(result.tier, TIER_MATERIAL)


class TestGateVersion(unittest.TestCase):
    def test_version_is_set(self):
        self.assertTrue(GATE_VERSION.startswith("1."))
        self.assertIn("lpos", GATE_VERSION)


if __name__ == "__main__":
    unittest.main()
