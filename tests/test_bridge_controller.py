from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from conversation_os.bridge_controller import (
    build_bridge_candidate_package,
    classify_with_agent,
    load_bridge_config,
    parse_control_packet,
    validate_control_packet,
)
from conversation_os.models import ContextPolicy, ControlPacket
from conversation_os.reasoning_bridge import BRIDGE_BEHAVIOR_RULES


def _valid_packet_payload() -> dict:
    return {
        "packet_id": "pkt-test-001",
        "request_id": "req-test-001",
        "active_topic": "knowledge ocean bridge",
        "object_scope": "same_main",
        "object_id": "object-knowledge-ocean-bridge",
        "user_goal": "build",
        "reasoning_posture": "implementation",
        "factual_anchor_level": "high",
        "bridge_behaviors": ["implementation_scaffold", "unknown_behavior"],
        "pipeline_id": "idea_embedding_v1",
        "context_policy": {
            "mode": "graph_contextual",
            "depth_mode": "deep",
            "token_budget": 5000,
            "include_layers": ["session", "global"],
            "exclude_layers": [],
            "cross_ocean": True,
            "retrieval_limit": 99,
            "neighbor_limit": 99,
        },
        "steering_constraints": ["preserve provenance"],
        "confidence": 1.5,
        "routing_source": "agent",
    }


class BridgeControllerTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        config_dir = self.root / "product" / "inner_world_v1" / "config"
        config_dir.mkdir(parents=True)
        (config_dir / "runtime.json").write_text(
            json.dumps(
                {
                    "chat_backend": "openclaw_gateway",
                    "openclaw": {"agent": "main", "thinking": "low", "timeout_seconds": 60},
                    "bridge": {
                        "enabled": False,
                        "agent": "thought_tube_router",
                        "thinking": "low",
                        "timeout_seconds": 25,
                        "fallback": "heuristic",
                        "emit_heuristic_preview": True,
                    },
                }
            ),
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_load_bridge_config_reads_runtime_and_env(self) -> None:
        config = load_bridge_config(self.root)
        self.assertFalse(config["enabled"])
        self.assertEqual(config["agent"], "thought_tube_router")
        self.assertEqual(config["timeout_seconds"], 25)

        with mock.patch.dict(os.environ, {"INNER_WORLD_BRIDGE_ENABLED": "1", "INNER_WORLD_BRIDGE_TIMEOUT": "40"}):
            config = load_bridge_config(self.root)
        self.assertTrue(config["enabled"])
        self.assertEqual(config["timeout_seconds"], 40)

    def test_validate_control_packet_clamps_policy_and_filters_behaviors(self) -> None:
        packet, warnings = validate_control_packet(_valid_packet_payload())
        self.assertIsNotNone(packet)
        assert packet is not None
        self.assertEqual(packet.bridge_behaviors, ["implementation_scaffold"])
        self.assertEqual(packet.context_policy.retrieval_limit, 8)
        self.assertEqual(packet.context_policy.neighbor_limit, 6)
        self.assertFalse(packet.context_policy.cross_ocean)
        self.assertEqual(packet.confidence, 1.0)
        self.assertTrue(any("bridge_behaviors" in warning for warning in warnings))

    def test_parse_control_packet_rejects_malformed_json(self) -> None:
        self.assertIsNone(parse_control_packet("not json"))
        self.assertIsNone(parse_control_packet('{"reply":"hello"}'))

    def test_parse_control_packet_reads_openclaw_gateway_payload(self) -> None:
        packet = _valid_packet_payload()
        wrapped = {
            "status": "ok",
            "result": {
                "payloads": [
                    {"text": "```json\n" + json.dumps(packet) + "\n```"}
                ]
            },
        }
        parsed = parse_control_packet(json.dumps(wrapped))
        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertEqual(parsed["packet_id"], "pkt-test-001")
        self.assertEqual(parsed["context_policy"]["depth_mode"], "deep")

    def test_build_bridge_candidate_package_includes_behavior_menu(self) -> None:
        request = {
            "request_id": "req-001",
            "session_id": "session-001",
            "raw_text": "connect bridge to ocean",
            "caller_hints": {},
            "domain_hints": [],
            "source_refs": [],
        }
        package = build_bridge_candidate_package(
            self.root,
            request,
            retrieval_bundle={"count": 2, "seed_capsules": [{"label": "bridge"}]},
            bridge_state={"behavior_patterns": []},
            heuristic_preview={"active_topic": "connect bridge"},
        )
        self.assertEqual(package["request"]["request_id"], "req-001")
        self.assertEqual(len(package["behavior_menu"]), len(BRIDGE_BEHAVIOR_RULES))
        self.assertEqual(package["retrieval_candidates"]["count"], 2)

    @mock.patch("conversation_os.bridge_controller.subprocess.run")
    def test_classify_with_agent_returns_packet_on_valid_json(self, run_mock: mock.MagicMock) -> None:
        payload = _valid_packet_payload()
        payload["context_policy"]["retrieval_limit"] = 6
        payload["context_policy"]["neighbor_limit"] = 4
        payload["context_policy"]["cross_ocean"] = False
        payload["bridge_behaviors"] = ["implementation_scaffold"]
        run_mock.return_value = mock.Mock(returncode=0, stdout=json.dumps(payload), stderr="")

        request = {"request_id": "req-001", "session_id": "", "raw_text": "build bridge", "caller_hints": {}}
        result = classify_with_agent(
            self.root,
            request,
            retrieval_bundle={"count": 0},
            bridge_state={},
            heuristic_preview=None,
        )
        self.assertIsNotNone(result)
        packet, metadata = result
        self.assertEqual(packet.request_id, "req-test-001")
        self.assertEqual(metadata["routing_source"], "agent")
        command = run_mock.call_args[0][0]
        self.assertIn("thought_tube_router", command)
        self.assertNotIn("--deliver", command)

    @mock.patch("conversation_os.bridge_controller.subprocess.run")
    def test_classify_with_agent_returns_none_on_timeout(self, run_mock: mock.MagicMock) -> None:
        run_mock.side_effect = subprocess.TimeoutExpired(cmd="openclaw", timeout=25)
        request = {"request_id": "req-001", "session_id": "", "raw_text": "build bridge", "caller_hints": {}}
        self.assertIsNone(
            classify_with_agent(
                self.root,
                request,
                retrieval_bundle={"count": 0},
                bridge_state={},
                heuristic_preview=None,
            )
        )


if __name__ == "__main__":
    unittest.main()
