from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from conversation_os.models import ReasoningRequest
from conversation_os.reasoning_bridge import (
    BRIDGE_BEHAVIOR_RULES,
    classify_turn,
    load_bridge_behavior_specs,
)


class ReasoningBridgeIsolationTestCase(unittest.TestCase):
    def test_load_bridge_behavior_specs_returns_independent_embedded_rules(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            specs = load_bridge_behavior_specs(root)

        original_priority = BRIDGE_BEHAVIOR_RULES["creative_expansion"]["priority"]
        specs["creative_expansion"]["priority"] = 0

        self.assertEqual(
            BRIDGE_BEHAVIOR_RULES["creative_expansion"]["priority"],
            original_priority,
        )

    def test_embedded_spec_mutation_does_not_break_metathought_routing(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            specs = load_bridge_behavior_specs(root)
            specs["creative_expansion"]["priority"] = 1

            request = ReasoningRequest(
                request_id="req-bridge-creative-isolation-001",
                session_id="session-bridge-creative-isolation-001",
                surface="chat",
                raw_text="Could this represent the subconscious in a symbolic way?",
                source_refs=["memory/events/session-bridge-creative-isolation-001.jsonl"],
                timestamp="2026-06-10T12:16:00+00:00",
                caller_hints={"routing_tags": ["metathought"]},
            )

            payload = classify_turn(root, request.to_dict())

        self.assertEqual(payload["reasoning_posture"], "expansive")
        self.assertEqual(payload["bridge_behaviors"][0]["behavior_id"], "creative_expansion")
        self.assertEqual(BRIDGE_BEHAVIOR_RULES["creative_expansion"]["priority"], 90)
