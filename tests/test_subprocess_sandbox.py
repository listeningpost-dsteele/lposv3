"""LPOS-10 regression tests: hardened subprocess model-host boundary.

These tests verify privilege-reduction behavior: environment allowlisting,
streamed output caps with bounded peak capture, process-group termination on
timeout, executable pinning, and POSIX resource limits.  They do NOT claim
the adapter is an OS sandbox.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

from lpos_engine.adapters.subprocess_host import SubprocessModelAdapter
from lpos_engine.errors import AdapterError, ValidationError

try:
    import resource as _resource
except ImportError:  # pragma: no cover - non-POSIX platforms
    _resource = None

IS_POSIX = os.name == "posix"

CANARY_KEY = "LPOS_TEST_PARENT_SECRET"
CANARY_VALUE = "AUDIT-CANARY-DO-NOT-LEAK"


def make_adapter(command, **overrides):
    arguments = {
        "model_classes": frozenset({"executive"}),
        "capabilities": frozenset({"software_architecture"}),
        "timeout_seconds": 10,
        "max_stdout_bytes": 10_000_000,
    }
    arguments.update(overrides)
    return SubprocessModelAdapter("sandbox-test", tuple(command), **arguments)


class SubprocessSandboxTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def write_script(self, body: str) -> Path:
        path = self.root / "child.py"
        path.write_text(body.strip() + "\n", encoding="utf-8")
        return path

    # -- environment allowlist ----------------------------------------------

    def test_parent_canary_secret_is_not_visible_to_child(self):
        script = self.write_script(
            """
import json, os
print(json.dumps({"env": dict(os.environ), "cwd": os.getcwd()}))
"""
        )
        os.environ[CANARY_KEY] = CANARY_VALUE
        os.environ["LPOS_TEST_INHERITED"] = "inherited-ok"
        self.addCleanup(os.environ.pop, CANARY_KEY, None)
        self.addCleanup(os.environ.pop, "LPOS_TEST_INHERITED", None)

        adapter = make_adapter(
            (sys.executable, str(script)),
            env={"LPOS_TEST_EXPLICIT": "explicit-ok"},
            inherit_env=("LPOS_TEST_INHERITED",),
        )
        result = adapter._invoke({"operation": "probe"})
        child_env = result["env"]

        self.assertNotIn(CANARY_KEY, child_env, "parent secret leaked into the child")
        self.assertNotIn(CANARY_VALUE, json.dumps(child_env))
        # Only the allowlist plus explicitly configured keys are present.
        allowed = {
            "PATH",
            "HOME",
            "LANG",
            "LC_ALL",
            "TMPDIR",
            "PYTHONIOENCODING",
            "LPOS_TEST_EXPLICIT",
            "LPOS_TEST_INHERITED",
            # Python itself may inject these in the child (PEP 538 locale
            # coercion, shell bookkeeping); they carry no parent secrets.
            "LC_CTYPE",
            "PWD",
            # macOS can synthesize this per-user encoding marker even when
            # subprocess.Popen receives an explicit env mapping; it carries
            # no credential material and is not inherited through the
            # adapter allowlist.
            "__CF_USER_TEXT_ENCODING",
            }
        # Assert nothing outside the allowlist that exists in the parent
        # leaked through.
        for key in child_env:
            if key in os.environ and key not in allowed:
                self.assertNotEqual(
                    child_env.get(key),
                    os.environ.get(key),
                    f"parent environment variable {key!r} was inherited",
                )
        self.assertEqual(child_env.get("LPOS_TEST_EXPLICIT"), "explicit-ok")
        self.assertEqual(child_env.get("LPOS_TEST_INHERITED"), "inherited-ok")
        self.assertEqual(child_env.get("PYTHONIOENCODING"), "utf-8")

    def test_child_runs_in_fresh_temporary_cwd_by_default(self):
        script = self.write_script(
            """
import json, os
print(json.dumps({"cwd": os.getcwd()}))
"""
        )
        adapter = make_adapter((sys.executable, str(script)))
        result = adapter._invoke({"operation": "probe"})
        child_cwd = result["cwd"]
        self.assertNotEqual(os.path.realpath(child_cwd), os.path.realpath(os.getcwd()))
        self.assertIn("lpos-model-host-", Path(child_cwd).name)
        self.assertFalse(Path(child_cwd).exists(), "per-invocation cwd must be removed")

    def test_configured_cwd_is_honored(self):
        script = self.write_script(
            """
import json, os
print(json.dumps({"cwd": os.getcwd()}))
"""
        )
        workdir = self.root / "workdir"
        workdir.mkdir()
        adapter = make_adapter((sys.executable, str(script)), cwd=workdir)
        result = adapter._invoke({"operation": "probe"})
        self.assertEqual(os.path.realpath(result["cwd"]), os.path.realpath(str(workdir)))

    # -- output flood --------------------------------------------------------

    def test_output_flood_is_capped_during_read_with_bounded_capture(self):
        cap = 1_000_000
        script = self.write_script(
            """
import sys
block = "x" * (1 << 20)
for _ in range(100):  # ~100 MB
    sys.stdout.write(block)
sys.stdout.flush()
"""
        )
        adapter = make_adapter(
            (sys.executable, str(script)),
            max_stdout_bytes=cap,
            timeout_seconds=60,
        )
        started = time.monotonic()
        with self.assertRaises(AdapterError) as caught:
            adapter._invoke({"operation": "probe"})
        elapsed = time.monotonic() - started
        self.assertIn("exceeded stdout limit", str(caught.exception))
        self.assertLessEqual(
            adapter._last_stdout_bytes_captured,
            cap,
            "captured stdout exceeded the configured cap: peak memory is unbounded",
        )
        self.assertLess(elapsed, 30.0, "flood was not terminated promptly")

    def test_stderr_flood_is_also_capped(self):
        script = self.write_script(
            """
import sys
block = "e" * (1 << 20)
for _ in range(50):
    sys.stderr.write(block)
sys.stderr.flush()
"""
        )
        adapter = make_adapter(
            (sys.executable, str(script)),
            max_stderr_bytes=500_000,
            timeout_seconds=60,
        )
        with self.assertRaises(AdapterError) as caught:
            adapter._invoke({"operation": "probe"})
        self.assertIn("exceeded stderr limit", str(caught.exception))

    # -- timeout and process-group kill -------------------------------------

    @unittest.skipUnless(IS_POSIX, "process-group kill is POSIX-only")
    def test_timeout_kills_spawned_grandchild_via_process_group(self):
        pid_file = self.root / "grandchild.pid"
        script = self.write_script(
            f"""
import subprocess, sys, time
grandchild = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(120)"])
with open({str(pid_file)!r}, "w") as fh:
    fh.write(str(grandchild.pid))
time.sleep(120)
"""
        )
        adapter = make_adapter(
            (sys.executable, str(script)),
            timeout_seconds=1,
            resource_limits={"processes": None},
        )
        started = time.monotonic()
        with self.assertRaises(AdapterError) as caught:
            adapter._invoke({"operation": "probe"})
        elapsed = time.monotonic() - started
        self.assertIn("timed out", str(caught.exception))
        self.assertLess(elapsed, 10.0)

        self.assertTrue(pid_file.is_file(), "grandchild never started")
        grandchild_pid = int(pid_file.read_text())
        deadline = time.monotonic() + 5.0
        alive = True
        while time.monotonic() < deadline:
            try:
                os.kill(grandchild_pid, 0)
            except ProcessLookupError:
                alive = False
                break
            except PermissionError:
                break
            time.sleep(0.05)
        self.assertFalse(alive, "grandchild survived the process-group kill")

    # -- executable pinning --------------------------------------------------

    def test_executable_sha256_mismatch_is_refused_before_exec(self):
        script = self.write_script("print('{}')")
        adapter = make_adapter(
            (sys.executable, str(script)),
            executable_sha256="0" * 64,
        )
        with self.assertRaises(AdapterError) as caught:
            adapter._invoke({"operation": "probe"})
        self.assertIn("does not match pinned", str(caught.exception))

    def test_executable_sha256_match_is_accepted(self):
        import hashlib

        script = self.write_script("print('{\"ok\": true}')")
        resolved = os.path.realpath(sys.executable)
        digest = hashlib.sha256(Path(resolved).read_bytes()).hexdigest()
        adapter = make_adapter(
            (sys.executable, str(script)),
            executable_sha256=digest.upper(),  # case-insensitive pin
        )
        self.assertEqual(adapter._invoke({"operation": "probe"}), {"ok": True})

    def test_missing_executable_is_an_adapter_error(self):
        adapter = make_adapter(("/nonexistent/lpos-model-host-binary",))
        with self.assertRaises(AdapterError) as caught:
            adapter._invoke({"operation": "probe"})
        self.assertIn("executable not found", str(caught.exception))

    def test_invalid_pin_and_env_configs_are_rejected(self):
        for kwargs in (
            {"executable_sha256": "zz"},
            {"executable_sha256": 42},
            {"env": {"BAD=KEY": "x"}},
            {"env": {"KEY": 42}},
            {"inherit_env": "PATH"},
            {"resource_limits": {"unknown_limit": 1}},
            {"resource_limits": {"cpu_seconds": 0}},
            {"max_stderr_bytes": 0},
        ):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValidationError):
                make_adapter((sys.executable, "-c", "pass"), **kwargs)

    # -- resource limits -----------------------------------------------------

    @unittest.skipUnless(
        IS_POSIX and _resource is not None, "resource limits are POSIX-only"
    )
    def test_resource_limits_are_applied_in_the_child(self):
        script = self.write_script(
            """
import json, resource
print(json.dumps({
    "cpu": resource.getrlimit(resource.RLIMIT_CPU),
    "nofile": resource.getrlimit(resource.RLIMIT_NOFILE),
}))
"""
        )
        requested_cpu = 7
        requested_nofile = 128
        adapter = make_adapter(
            (sys.executable, str(script)),
            resource_limits={
                "cpu_seconds": requested_cpu,
                "open_files": requested_nofile,
                "address_space_bytes": None,
                "file_size_bytes": None,
                "processes": None,
            },
        )
        result = adapter._invoke({"operation": "probe"})

        def expected(kind, requested):
            _soft, hard = _resource.getrlimit(kind)
            return requested if hard == _resource.RLIM_INFINITY else min(requested, hard)

        self.assertEqual(result["cpu"][0], expected(_resource.RLIMIT_CPU, requested_cpu))
        self.assertEqual(
            result["nofile"][0], expected(_resource.RLIMIT_NOFILE, requested_nofile)
        )

    def test_docstring_does_not_overclaim_isolation(self):
        doc = SubprocessModelAdapter.__doc__ or ""
        self.assertIn("not an OS sandbox", doc)
        self.assertIn("privilege REDUCTION", doc)
        self.assertIn("container", doc)


if __name__ == "__main__":
    unittest.main()
