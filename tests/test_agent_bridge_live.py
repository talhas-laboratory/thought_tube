from __future__ import annotations

import json
import os
import shutil
import unittest
from pathlib import Path

import pytest

from conversation_os.bridge_controller import load_bridge_config
from conversation_os.reasoning_bridge import classify_turn
from conversation_os.reasoning_runtime import run_reasoning
from conversation_os.models import ReasoningRequest

pytestmark = pytest.mark.live


def _openclaw_available() -> bool:
    return shutil.which("openclaw") is not None


@unittest.skipUnless(os.getenv("INNER_WORLD_BRIDGE_LIVE_TEST") == "1", "set INNER_WORLD_BRIDGE_LIVE_TEST=1 to run")
@unittest.skipUnless(_openclaw_available(), "openclaw CLI not available")
class AgentBridgeLiveTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(__file__).resolve().parents[1]
        self._previous_enabled = os.getenv("INNER_WORLD_BRIDGE_ENABLED")
        os.environ["INNER_WORLD_BRIDGE_ENABLED"] = "1"

    def tearDown(self) -> None:
        if self._previous_enabled is None:
            os.environ.pop("INNER_WORLD_BRIDGE_ENABLED", None)
        else:
            os.environ["INNER_WORLD_BRIDGE_ENABLED"] = self._previous_enabled

    def test_live_gateway_classify_turn_returns_control_packet_fields(self) -> None:
        config = load_bridge_config(self.root)
        if not config.get("enabled"):
            self.skipTest("bridge not enabled in runtime config")

        request = {
            "request_id": "req-live-bridge-001",
            "session_id": "session-live-bridge-001",
            "raw_text": "How should we connect the bridge to the knowledge ocean?",
            "caller_hints": {},
            "domain_hints": ["product"],
            "source_refs": [],
        }
        context = classify_turn(self.root, request)
        attributes = context.get("attributes", {}) or {}
        if attributes.get("routing_source") != "agent":
            self.skipTest("live gateway unavailable or agent fallback activated")
        self.assertIn("context_policy", attributes)
        self.assertTrue(attributes.get("control_packet_id"))

    def test_live_gateway_reasoning_run_persists_control_packet(self) -> None:
        config = load_bridge_config(self.root)
        if not config.get("enabled"):
            self.skipTest("bridge not enabled in runtime config")

        request = ReasoningRequest(
            request_id="req-live-runtime-001",
            session_id="session-live-runtime-001",
            surface="reasoning",
            raw_text="Give me a short bridge execution scaffold.",
            source_refs=[],
            timestamp="2026-06-25T12:00:00+00:00",
        )
        result = run_reasoning(self.root, request)
        attributes = result["context_state"].get("attributes", {}) or {}
        if attributes.get("routing_source") != "agent":
            self.skipTest("live gateway unavailable or agent fallback activated")
        self.assertTrue(result["result"]["response_text"].strip())


if __name__ == "__main__":
    unittest.main()
