from __future__ import annotations

import json
import unittest

from conversation_os.models import ContextPolicy, ControlPacket


def _sample_policy(**overrides) -> ContextPolicy:
    base = {
        "mode": "semantic_narrow",
        "depth_mode": "contextual",
        "token_budget": 1200,
        "include_layers": ["session", "workspace", "user", "global"],
        "exclude_layers": [],
        "cross_ocean": False,
        "retrieval_limit": 6,
        "neighbor_limit": 4,
    }
    base.update(overrides)
    return ContextPolicy(**base)


def _sample_packet(**overrides) -> ControlPacket:
    policy = overrides.pop("context_policy", None) or _sample_policy()
    base = {
        "packet_id": "pkt-001",
        "request_id": "req-001",
        "active_topic": "bridge integration",
        "object_scope": "same_main",
        "object_id": "object-bridge-integration",
        "user_goal": "build",
        "reasoning_posture": "implementation",
        "factual_anchor_level": "high",
        "bridge_behaviors": ["implementation_scaffold"],
        "pipeline_id": "idea_embedding_v1",
        "context_policy": policy,
        "steering_constraints": ["preserve provenance"],
        "confidence": 0.84,
        "routing_source": "agent",
    }
    base.update(overrides)
    return ControlPacket(**base)


class ControlPacketContractTestCase(unittest.TestCase):
    def test_context_policy_to_dict_round_trip(self) -> None:
        policy = _sample_policy()
        payload = policy.to_dict()
        restored = ContextPolicy.from_dict(payload)

        self.assertEqual(restored.mode, "semantic_narrow")
        self.assertEqual(restored.depth_mode, "contextual")
        self.assertEqual(restored.token_budget, 1200)
        self.assertEqual(restored.include_layers, ["session", "workspace", "user", "global"])
        self.assertEqual(restored.exclude_layers, [])
        self.assertFalse(restored.cross_ocean)
        self.assertEqual(restored.retrieval_limit, 6)
        self.assertEqual(restored.neighbor_limit, 4)

    def test_control_packet_to_dict_round_trip(self) -> None:
        packet = _sample_packet(
            parent_object_id="parent-001",
            dimension_axis="architecture",
            current_tension="speed vs depth",
            answer_shape="scaffold",
            attributes={"source": "unit-test"},
        )
        payload = packet.to_dict()
        restored = ControlPacket.from_dict(payload)

        self.assertEqual(restored.packet_id, "pkt-001")
        self.assertEqual(restored.request_id, "req-001")
        self.assertEqual(restored.parent_object_id, "parent-001")
        self.assertEqual(restored.dimension_axis, "architecture")
        self.assertEqual(restored.current_tension, "speed vs depth")
        self.assertEqual(restored.answer_shape, "scaffold")
        self.assertEqual(restored.routing_source, "agent")
        self.assertEqual(restored.attributes, {"source": "unit-test"})
        self.assertIsInstance(restored.context_policy, ContextPolicy)

    def test_nested_context_policy_is_json_serializable(self) -> None:
        packet = _sample_packet()
        encoded = json.dumps(packet.to_dict())
        decoded = json.loads(encoded)
        self.assertEqual(decoded["context_policy"]["depth_mode"], "contextual")

    def test_optional_fields_have_sane_defaults(self) -> None:
        packet = _sample_packet()
        payload = packet.to_dict()
        self.assertIsNone(payload["parent_object_id"])
        self.assertEqual(payload["dimension_axis"], "")
        self.assertEqual(payload["current_tension"], "")
        self.assertEqual(payload["answer_shape"], "")
        self.assertEqual(payload["attributes"], {})

    def test_enum_like_string_fields_preserved_literally(self) -> None:
        packet = _sample_packet(
            object_scope="parallel_object",
            user_goal="evaluate",
            reasoning_posture="evaluative",
            factual_anchor_level="low",
            routing_source="hybrid",
        )
        payload = packet.to_dict()
        self.assertEqual(payload["object_scope"], "parallel_object")
        self.assertEqual(payload["user_goal"], "evaluate")
        self.assertEqual(payload["reasoning_posture"], "evaluative")
        self.assertEqual(payload["factual_anchor_level"], "low")
        self.assertEqual(payload["routing_source"], "hybrid")


if __name__ == "__main__":
    unittest.main()
