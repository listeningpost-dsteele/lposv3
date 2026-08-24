"""Tests for LPOS v4.8.3 executable guild model routing."""

from __future__ import annotations

import json
import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from lpos_engine.model_routing import (
    ROUTING_VERSION,
    bind_hermes_command,
    command_matches_lane,
    enforcement_enabled,
    find_wrapper_executable,
    install_wrapper_scripts,
    list_routes,
    load_routing_config,
    model_family,
    resolve_guild_lane,
    resolve_specialist_lane,
)


class TestModelFamily(unittest.TestCase):
    def test_families(self):
        self.assertEqual(model_family("glm-5.2"), "glm")
        self.assertEqual(model_family("hermes-gpt56"), "gpt")
        self.assertEqual(model_family("kimi-k2-thinking"), "kimi")
        self.assertEqual(model_family("laguna-xs-2.1"), "framework")
        self.assertEqual(model_family("qwen3.5:122b"), "framework")


class TestResolveLane(unittest.TestCase):
    def test_software_engineering_is_gpt(self):
        lane = resolve_guild_lane("GUILD-SOFTWARE-ENGINEERING")
        self.assertEqual(lane.wrapper, "hermes-gpt56")
        self.assertEqual(lane.family, "gpt")

    def test_operations_is_laguna(self):
        lane = resolve_guild_lane("GUILD-OPERATIONS-AUTOMATION-ENGINEERING")
        self.assertEqual(lane.wrapper, "hermes-laguna")
        self.assertEqual(lane.family, "framework")

    def test_short_guild_name(self):
        lane = resolve_guild_lane("DATA-ANALYTICS")
        self.assertEqual(lane.wrapper, "hermes-qwen35")

    def test_model_class_fallback(self):
        lane = resolve_guild_lane("GUILD-DOES-NOT-EXIST", model_class="routine")
        self.assertEqual(lane.wrapper, "hermes-qwen35")
        self.assertEqual(lane.source, "model_class")

    def test_specialist_uses_guild(self):
        lane = resolve_specialist_lane(
            specialist_id="SPECIALIST-X",
            guild="GUILD-EXPERIENCE-DESIGN",
            model_class="executive",
        )
        self.assertEqual(lane.wrapper, "hermes-gpt56")


class TestBindCommand(unittest.TestCase):
    def test_wrong_lane_fails_closed(self):
        decision = bind_hermes_command(
            specialist_id="SPECIALIST-X",
            guild="GUILD-SOFTWARE-ENGINEERING",
            model_class="executive",
            hermes_command="hermes-glm52",
        )
        self.assertFalse(decision.ok)
        self.assertIn("hermes_command_lane_mismatch", decision.gaps)

    def test_correct_lane_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            wrapper = Path(tmp) / "hermes-gpt56"
            wrapper.write_text("#!/bin/sh\nexit 0\n")
            wrapper.chmod(wrapper.stat().st_mode | stat.S_IEXEC)
            with mock.patch.dict(os.environ, {"PATH": tmp + os.pathsep + os.environ.get("PATH", "")}):
                decision = bind_hermes_command(
                    specialist_id="SPECIALIST-X",
                    guild="GUILD-SOFTWARE-ENGINEERING",
                    model_class="executive",
                    hermes_command="hermes-gpt56",
                )
            self.assertTrue(decision.ok)
            self.assertTrue(decision.bound_command)

    def test_bare_hermes_autobind(self):
        with tempfile.TemporaryDirectory() as tmp:
            wrapper = Path(tmp) / "hermes-laguna"
            wrapper.write_text("#!/bin/sh\nexit 0\n")
            wrapper.chmod(wrapper.stat().st_mode | stat.S_IEXEC)
            cfg = load_routing_config()
            cfg = dict(cfg)
            cfg["wrapper_bin_dirs"] = [tmp]
            decision = bind_hermes_command(
                specialist_id="SPECIALIST-X",
                guild="GUILD-OPERATIONS-AUTOMATION-ENGINEERING",
                model_class="routine",
                hermes_command="hermes",
                config=cfg,
            )
            self.assertTrue(decision.ok)
            self.assertIsNotNone(decision.bound_command)
            assert decision.bound_command is not None
            self.assertTrue(decision.bound_command.endswith("hermes-laguna"))

    def test_override_allows_mismatch(self):
        decision = bind_hermes_command(
            specialist_id="SPECIALIST-X",
            guild="GUILD-SOFTWARE-ENGINEERING",
            model_class="executive",
            hermes_command="hermes-glm52",
            authorize_override=True,
        )
        self.assertTrue(decision.ok)
        self.assertIn("model_lane_override", decision.gaps)

    def test_enforce_off(self):
        with mock.patch.dict(os.environ, {"LPOS_MODEL_ROUTING_ENFORCE": "0"}):
            self.assertFalse(enforcement_enabled())
            decision = bind_hermes_command(
                specialist_id="SPECIALIST-X",
                guild="GUILD-SOFTWARE-ENGINEERING",
                model_class="executive",
                hermes_command="hermes-glm52",
            )
            self.assertTrue(decision.ok)
            self.assertFalse(decision.enforce)


class TestWrappersAndList(unittest.TestCase):
    def test_list_routes_has_20_guilds(self):
        table = list_routes()
        self.assertGreaterEqual(len(table["guild_lanes"]), 20)
        self.assertIn("routing_version", table)

    def test_install_wrappers(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = install_wrapper_scripts(Path(tmp), hermes_binary="/usr/bin/env hermes", force=True)
            self.assertGreaterEqual(len(result["installed"]), 5)
            sample = Path(tmp) / "hermes-gpt56"
            self.assertTrue(sample.is_file())
            body = sample.read_text()
            self.assertIn("--provider openai-codex", body)
            self.assertIn("-m gpt-5.6-sol", body)
            self.assertTrue(os.access(sample, os.X_OK))

    def test_command_matches_lane_basename(self):
        lane = resolve_guild_lane("GUILD-DATA-ANALYTICS")
        self.assertTrue(command_matches_lane("hermes-qwen35", lane))
        self.assertTrue(command_matches_lane("/opt/bin/hermes-qwen35", lane))
        self.assertFalse(command_matches_lane("hermes-gpt56", lane))


class TestPackagedConfig(unittest.TestCase):
    def test_packaged_config_loads(self):
        cfg = load_routing_config()
        self.assertTrue(cfg.get("enforce", True))
        self.assertIn("guild_lanes", cfg)
        self.assertIn(ROUTING_VERSION.split("-")[0], cfg.get("routing_version", ROUTING_VERSION))


if __name__ == "__main__":
    unittest.main()
