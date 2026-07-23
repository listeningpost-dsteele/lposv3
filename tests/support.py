from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from lpos_engine.adapters import AdapterRegistry, DeterministicModelAdapter, RecordingActionAdapter
from lpos_engine.approvals import TrustedLocalChannel
from lpos_engine.engine import LPOSRuntime, RuntimeConfig


class RuntimeTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.creator = DeterministicModelAdapter("creator", priority=10)
        self.reviewer = DeterministicModelAdapter(
            "reviewer",
            priority=5,
            supports_creation=False,
        )
        self.action_adapter = RecordingActionAdapter()
        self.adapters = AdapterRegistry(
            model_adapters=(self.creator, self.reviewer),
            action_adapters=(self.action_adapter,),
        )
        self.runtime = LPOSRuntime(
            RuntimeConfig(
                database_path=self.root / "state.db",
                verified_identities={"email": ("principal@example.com",)},
                # A registered verified channel for the "verified-connector"
                # provider so approval grants exercise the 4.2.1 verified-channel
                # assertion path rather than trusting a caller-built identity.
                verified_channels={"verified-connector": TrustedLocalChannel("verified-connector")},
            ),
            adapters=self.adapters,
        )

    def tearDown(self) -> None:
        self.temp.cleanup()
