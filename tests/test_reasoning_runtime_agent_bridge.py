from __future__ import annotations

import argparse
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from conversation_os.chat_backends import compose_execution_message, trim_context_bundle
from conversation_os.models import ContextPolicy, ControlPacket, ReasoningRequest
from conversation_os.reasoning_bridge import (
    _control_packets_path,
    classify_turn,
    heuristic_classify_turn,
    load_context_states,
    prepare_bridge_candidates,
)
from conversation_os.cli import reasoning_inspect
from conversation_os.reasoning_runtime import inspect_reasoning_request, run_reasoning
from conversation_os.storage import read_jsonl


def _agent_packet() -> ControlPacket:
    return ControlPacket(
        packet_id="pkt-agent-001",
        request_id="req-agent-001",
        active_topic="agent bridge topic",
        object_scope="same_main",
        object_id="object-agent-bridge-topic",
        user_goal="build",
        reasoning_posture="implementation",
        factual_anchor_level="high",
        bridge_behaviors=["implementation_scaffold"],
        pipeline_id="idea_embedding_v1",
        context_policy=ContextPolicy(
            mode="semantic_narrow",
            depth_mode="contextual",
            token_budget=1200,
            include_layers=["session", "workspace", "user"],
            exclude_layers=[],
            cross_ocean=False,
            retrieval_limit=6,
            neighbor_limit=4,
        ),
        steering_constraints=["preserve provenance"],
        confidence=0.9,
        routing_source="agent",
    )


class ReasoningRuntimeAgentBridgeTestCase(unittest.TestCase):
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
                        "enabled": True,
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
        runtime = self.root / "product" / "inner_world_v1" / "data" / "reasoning_runtime"
        runtime.mkdir(parents=True)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _request(self) -> ReasoningRequest:
        return ReasoningRequest(
            request_id="req-agent-001",
            session_id="session-agent-001",
            surface="reasoning",
            raw_text="How should we connect the bridge to the knowledge ocean?",
            source_refs=[],
            timestamp="2026-06-25T12:00:00+00:00",
        )

    @mock.patch("conversation_os.bridge_controller.classify_with_agent")
    def test_classify_turn_uses_agent_packet_when_enabled(self, classify_mock: mock.MagicMock) -> None:
        classify_mock.return_value = (_agent_packet(), {"routing_source": "agent", "validation_warnings": []})
        context = classify_turn(self.root, self._request().to_dict())
        self.assertEqual(context["active_topic"], "agent bridge topic")
        self.assertEqual(context["attributes"]["routing_source"], "agent")
        self.assertEqual(context["attributes"]["context_policy"]["depth_mode"], "contextual")

    @mock.patch("conversation_os.bridge_controller.classify_with_agent")
    def test_classify_turn_falls_back_to_heuristic_on_agent_failure(self, classify_mock: mock.MagicMock) -> None:
        classify_mock.return_value = None
        request = self._request().to_dict()
        heuristic = heuristic_classify_turn(self.root, request)
        context = classify_turn(self.root, request)
        self.assertEqual(context["user_goal"], heuristic["user_goal"])
        self.assertEqual(context["depth_mode"], heuristic["depth_mode"])
        self.assertNotIn("routing_source", context.get("attributes", {}))

    @mock.patch("conversation_os.reasoning_bridge.build_retrieval_bundle")
    @mock.patch("conversation_os.reasoning_bridge.heuristic_classify_turn")
    def test_prepare_bridge_candidates_retrieves_for_non_incognito_focused_preview(
        self,
        heuristic_mock: mock.MagicMock,
        retrieval_mock: mock.MagicMock,
    ) -> None:
        heuristic_mock.return_value = {
            "active_topic": "knowledge ocean bridge",
            "depth_mode": "focused",
            "user_goal": "build",
        }
        retrieval_mock.return_value = {
            "query": "knowledge ocean bridge",
            "seed_capsules": [{"label": "bridge"}],
            "related_capsules": [],
            "included_links": [],
            "source_refs": [],
            "count": 1,
            "alias_hits": [],
            "anchor_pond": "knowledge",
            "include_cross_pond": False,
        }

        candidates = prepare_bridge_candidates(self.root, self._request().to_dict())

        retrieval_mock.assert_called_once()
        self.assertEqual(candidates["retrieval_bundle"]["count"], 1)
        self.assertEqual(candidates["heuristic_preview"]["depth_mode"], "focused")

    @mock.patch("conversation_os.bridge_controller.classify_with_agent")
    def test_run_reasoning_persists_control_packet_for_agent_routing(self, classify_mock: mock.MagicMock) -> None:
        classify_mock.return_value = (_agent_packet(), {"routing_source": "agent", "validation_warnings": []})
        with mock.patch("conversation_os.reasoning_runtime.run_pipeline") as pipeline_mock:
            pipeline_mock.side_effect = lambda root, pipeline_id, packet, context=None: {
                **packet,
                "user_response": {"text": "scaffold"},
                "operator_trace": [],
            }
            run_reasoning(self.root, self._request())
        rows = read_jsonl(_control_packets_path(self.root))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["metadata"]["routing_source"], "agent")
        contexts = load_context_states(self.root)
        self.assertEqual(contexts[-1]["attributes"]["control_packet_id"], "pkt-agent-001")

    @mock.patch("conversation_os.bridge_controller.classify_with_agent")
    def test_incognito_skips_learning_side_effects(self, classify_mock: mock.MagicMock) -> None:
        packet = _agent_packet()
        packet.context_policy.depth_mode = "incognito"
        packet.context_policy.mode = "none"
        packet.context_policy.include_layers = ["session"]
        classify_mock.return_value = (packet, {"routing_source": "agent", "validation_warnings": []})
        request = self._request()
        request.caller_hints = {"feedback_kind": "accept"}
        with mock.patch("conversation_os.reasoning_runtime.run_pipeline") as pipeline_mock:
            pipeline_mock.side_effect = lambda root, pipeline_id, packet, context=None: {
                **packet,
                "user_response": {"text": "ok"},
                "operator_trace": [],
            }
            with mock.patch("conversation_os.reasoning_runtime.record_learning_event") as learning_mock:
                result = run_reasoning(self.root, request)
        learning_mock.assert_not_called()
        self.assertIsNone(result["learning_event"])

    @mock.patch("conversation_os.bridge_controller.classify_with_agent")
    def test_strict_envelope_skips_durable_learning_side_effects(self, classify_mock: mock.MagicMock) -> None:
        packet = _agent_packet()
        packet.context_policy.include_layers = ["session", "workspace", "user", "global"]
        packet.context_policy.exclude_layers = ["user", "global"]
        classify_mock.return_value = (packet, {"routing_source": "agent", "validation_warnings": []})
        request = self._request()
        request.caller_hints = {"feedback_kind": "accept"}
        with mock.patch("conversation_os.reasoning_runtime.run_pipeline") as pipeline_mock:
            pipeline_mock.side_effect = lambda root, pipeline_id, packet, context=None: {
                **packet,
                "user_response": {"text": "strict"},
                "operator_trace": [],
            }
            with mock.patch("conversation_os.reasoning_runtime.record_learning_event") as learning_mock:
                with mock.patch(
                    "conversation_os.reasoning_runtime.persist_bridge_behavior_preferences"
                ) as persist_mock:
                    persist_mock.return_value = []
                    result = run_reasoning(self.root, request)
        learning_mock.assert_not_called()
        persist_mock.assert_not_called()
        self.assertEqual(result["session_envelope"]["mode"], "strict")
        self.assertIsNone(result["learning_event"])

    def test_execution_compose_includes_constraints_and_excludes_blocked_layers(self) -> None:
        control_packet = {
            "active_topic": "bridge execution",
            "user_goal": "build",
            "reasoning_posture": "implementation",
            "pipeline_id": "idea_embedding_v1",
            "bridge_behaviors": ["implementation_scaffold"],
            "steering_constraints": ["preserve provenance", "stay concise"],
            "context_policy": {
                "mode": "semantic_narrow",
                "depth_mode": "contextual",
                "include_layers": ["session", "workspace"],
                "exclude_layers": ["global", "user"],
            },
        }
        bundle = {
            "context_state": {"bundle_layers": ["session", "workspace", "user", "global"]},
            "session_local": [{"actor": "user", "content": "prior turn"}],
            "workspace_local": {"workspace_id": "ws-001"},
            "user_local": {"behavior_patterns": [{"pattern_key": "bridge_behavior:test"}]},
            "global_fallback": {"count": 2, "seed_capsules": [{"label": "ocean", "summary": "capsule"}]},
            "budget": {"retrieval_limit": 6},
        }
        trimmed = trim_context_bundle(bundle, control_packet["context_policy"])
        message = compose_execution_message(control_packet, trimmed, "connect the bridge")

        self.assertEqual(trimmed["bundle_layers"], ["session", "workspace"])
        self.assertNotIn("global", trimmed)
        self.assertIn("preserve provenance", message)
        self.assertIn("prior turn", message)
        self.assertIn("ws-001", message)
        self.assertNotIn("ocean", message)
        self.assertNotIn("bridge_behavior:test", message)

    def test_execution_compose_includes_frame_envelope_and_suppression_summary(self) -> None:
        control_packet = {
            "active_topic": "bridge execution",
            "user_goal": "build",
            "reasoning_posture": "implementation",
            "pipeline_id": "idea_embedding_v1",
            "bridge_behaviors": ["implementation_scaffold"],
            "steering_constraints": ["preserve provenance"],
            "context_policy": {
                "mode": "semantic_narrow",
                "depth_mode": "contextual",
                "include_layers": ["session", "workspace"],
                "exclude_layers": ["global", "user"],
            },
        }
        bundle = {
            "context_state": {"bundle_layers": ["session", "workspace", "user", "global"]},
            "session_envelope": {
                "mode": "strict",
                "learning_mode": "session_scoped",
                "persistence_mode": "manual",
            },
            "frame_spec": {"frame_id": "frame-001"},
            "frame_bundle": {
                "frame_id": "frame-001",
                "assembly_status": "partial",
                "included_blocks": [
                    {"layer": "session", "summary": "1 session event(s)", "source_ref": "memory/events/session-agent-001.jsonl"},
                    {"layer": "workspace", "summary": "workspace binding for ws-001", "source_ref": "workspace:ws-001"},
                ],
                "suppressed_blocks": [
                    {"layer": "user", "summary": "1 user pattern(s)", "source_ref": "reasoning_runtime/bridge_state.json"},
                    {"layer": "global", "summary": "2 retrieval candidate(s)", "source_ref": "retrieval:bridge execution"},
                ],
                "provenance_summary": {
                    "source_refs": ["memory/events/session-agent-001.jsonl", "workspace:ws-001"],
                    "included_layer_count": 2,
                    "suppressed_layer_count": 2,
                },
            },
            "session_local": [{"actor": "user", "content": "prior turn"}],
            "workspace_local": {"workspace_id": "ws-001"},
            "user_local": {"behavior_patterns": [{"pattern_key": "bridge_behavior:test"}]},
            "global_fallback": {"count": 2, "seed_capsules": [{"label": "ocean", "summary": "capsule"}]},
            "budget": {"retrieval_limit": 6},
        }

        trimmed = trim_context_bundle(bundle, control_packet["context_policy"])
        message = compose_execution_message(control_packet, trimmed, "connect the bridge")

        self.assertEqual(trimmed["session_envelope"]["mode"], "strict")
        self.assertEqual(trimmed["frame_bundle"]["frame_id"], "frame-001")
        self.assertIn("Session envelope mode: strict", message)
        self.assertIn("Frame assembly: partial", message)
        self.assertIn("Suppressed frame blocks:", message)
        self.assertIn("global: 2 retrieval candidate(s)", message)
        self.assertIn("workspace: workspace binding for ws-001", message)
        self.assertIn("Do not mention internal bridge, routing, frame, or context-assembly mechanics", message)

    @mock.patch("conversation_os.bridge_controller.classify_with_agent")
    @mock.patch("conversation_os.reasoning_runtime.request_bridge_execution_reply")
    def test_end_to_end_execution_mode_uses_agent_reply(
        self,
        execution_mock: mock.MagicMock,
        classify_mock: mock.MagicMock,
    ) -> None:
        runtime_path = self.root / "product" / "inner_world_v1" / "config" / "runtime.json"
        runtime = json.loads(runtime_path.read_text(encoding="utf-8"))
        runtime["bridge"]["execution_mode"] = "agent"
        runtime_path.write_text(json.dumps(runtime), encoding="utf-8")

        classify_mock.return_value = (_agent_packet(), {"routing_source": "agent", "validation_warnings": []})
        execution_mock.return_value = {
            "content": "Agent execution scaffold.",
            "backend_id": "openclaw_gateway",
            "agent": "thought_tube_router",
        }

        request = self._request()
        request.caller_hints = {"constraints": ["speak as a conversational assistant"]}
        result = run_reasoning(self.root, request)

        execution_mock.assert_called_once()
        control_packet = execution_mock.call_args.args[1]
        self.assertIn("preserve provenance", control_packet["steering_constraints"])
        self.assertIn("speak as a conversational assistant", control_packet["steering_constraints"])
        self.assertEqual(result["result"]["response_text"], "Agent execution scaffold.")
        self.assertEqual(result["packet"]["operator_trace"][0]["step"], "bridge_execution_agent")

    @mock.patch("conversation_os.reasoning_runtime.run_pipeline")
    def test_end_to_end_operators_mode_still_uses_pipeline(self, pipeline_mock: mock.MagicMock) -> None:
        pipeline_mock.side_effect = lambda root, pipeline_id, packet, context=None: {
            **packet,
            "user_response": {"text": "operator scaffold"},
            "operator_trace": [{"step": "template_operator"}],
        }
        result = run_reasoning(self.root, self._request())
        pipeline_mock.assert_called_once()
        self.assertEqual(result["result"]["response_text"], "operator scaffold")

    @mock.patch("conversation_os.bridge_controller.classify_with_agent")
    def test_reasoning_inspect_summarizes_request(self, classify_mock: mock.MagicMock) -> None:
        classify_mock.return_value = (_agent_packet(), {"routing_source": "agent", "validation_warnings": []})
        with mock.patch("conversation_os.reasoning_runtime.run_pipeline") as pipeline_mock:
            pipeline_mock.side_effect = lambda root, pipeline_id, packet, context=None: {
                **packet,
                "user_response": {"text": "inspect scaffold"},
                "operator_trace": [],
            }
            run_result = run_reasoning(self.root, self._request())

        inspected = inspect_reasoning_request(self.root, "req-agent-001")
        self.assertEqual(inspected["request_id"], "req-agent-001")
        self.assertEqual(inspected["routing_source"], "agent")
        self.assertIn("session", inspected["bundle_layers"])
        self.assertEqual(len(inspected["control_packets"]), 1)
        self.assertEqual(inspected["result"]["response_text"], "inspect scaffold")
        self.assertEqual(inspected["active_field"]["request_id"], "req-agent-001")
        self.assertEqual(inspected["session_envelope"]["mode"], "bounded")
        self.assertTrue(inspected["frame_spec"]["preview_only"])
        self.assertEqual(inspected["frame_bundle"]["frame_id"], inspected["frame_spec"]["frame_id"])

        cli_result = reasoning_inspect(self.root, argparse.Namespace(request_id="req-agent-001"))
        self.assertEqual(cli_result["routing_source"], run_result["context_state"]["attributes"]["routing_source"])

    def test_learning_thought_feedback_persists_bridge_preferences(self) -> None:
        from conversation_os.personal_interface import load_bridge_state
        from conversation_os.product_inner_world import record_feedback
        from conversation_os.reasoning_bridge import heuristic_classify_turn
        from conversation_os.reasoning_learning import load_learning_events
        from conversation_os.storage import append_jsonl, write_jsonl

        thought = {
            "packet_id": "packet-learning-001",
            "thought_id": "thought-learning-001",
            "insight_id": "insight-learning-001",
            "title": "Learning thought",
            "short_text": "Bridge learning thought.",
            "article_title": "Learning thought",
            "article_markdown": "## Section\n\nBody.",
            "status": "active",
            "review_status": "ready_for_review",
            "evidence_status": "grounded",
            "confidence_score": 0.9,
            "relevance_score": 0.8,
            "novelty_score": 0.7,
            "source_refs": ["source://learning"],
            "source_item_ids": [],
            "meta_refs": [],
            "shared_primitive_key": "pattern",
            "shared_primitive_label": "Pattern",
            "what_changed": "Learning test.",
            "why_it_matters_now": "Feedback should update bridge preferences.",
            "next_action": "Inspect.",
            "reasoning_pipeline": "thought_pipeline",
            "primary_bubble_id": "",
            "primary_bubble_label": "",
            "related_bubble_ids": [],
            "feedback_state": "pending",
            "feedback_controls": ["relevant"],
            "article_sections": [],
            "article_profile": "",
            "article_module_order": [],
            "article_config_snapshot": {},
        }
        request = {
            "request_id": "req-learning-001",
            "session_id": "session-learning-001",
            "raw_text": "build implementation scaffold for bridge",
            "caller_hints": {"thought_id": thought["thought_id"], "routing_tags": ["metathought"]},
            "domain_hints": [],
            "source_refs": [],
        }
        context = heuristic_classify_turn(self.root, request)
        attributes = dict(context.get("attributes", {}) or {})
        attributes.setdefault("caller_hints", {})["thought_id"] = thought["thought_id"]
        context["attributes"] = attributes
        append_jsonl(self.root / "product" / "inner_world_v1" / "data" / "reasoning_runtime" / "context_states.jsonl", context)
        append_jsonl(
            self.root / "product" / "inner_world_v1" / "data" / "reasoning_runtime" / "reasoning_results.jsonl",
            {
                "result_id": "result-learning-001",
                "request_id": "req-learning-001",
                "pipeline_id": "idea_embedding_v1",
                "response_text": "scaffold",
            },
        )
        packets_path = self.root / "product" / "inner_world_v1" / "data" / "thought_packets.jsonl"
        packets_path.parent.mkdir(parents=True, exist_ok=True)
        write_jsonl(packets_path, [thought])

        result = record_feedback(self.root, thought["insight_id"], "relevant")

        self.assertIn("bridge_learning_event", result)
        events = load_learning_events(self.root)
        self.assertEqual(events[-1]["feedback_kind"], "accept")
        bridge_state = load_bridge_state(self.root)
        pattern_keys = [row.get("pattern_key", "") for row in bridge_state.get("behavior_patterns", [])]
        self.assertTrue(any(key.startswith("bridge_behavior:") for key in pattern_keys))

    def test_strict_thought_feedback_skips_durable_bridge_learning(self) -> None:
        from conversation_os.personal_interface import load_bridge_state
        from conversation_os.product_inner_world import record_feedback
        from conversation_os.reasoning_bridge import heuristic_classify_turn
        from conversation_os.reasoning_learning import load_learning_events
        from conversation_os.storage import append_jsonl, write_jsonl

        thought = {
            "packet_id": "packet-learning-strict-001",
            "thought_id": "thought-learning-strict-001",
            "insight_id": "insight-learning-strict-001",
            "title": "Strict learning thought",
            "short_text": "Strict bridge learning thought.",
            "article_title": "Strict learning thought",
            "article_markdown": "## Section\n\nBody.",
            "status": "active",
            "review_status": "ready_for_review",
            "evidence_status": "grounded",
            "confidence_score": 0.9,
            "relevance_score": 0.8,
            "novelty_score": 0.7,
            "source_refs": ["source://learning-strict"],
            "source_item_ids": [],
            "meta_refs": [],
            "shared_primitive_key": "pattern",
            "shared_primitive_label": "Pattern",
            "what_changed": "Learning test.",
            "why_it_matters_now": "Strict feedback should stay non-durable.",
            "next_action": "Inspect.",
            "reasoning_pipeline": "thought_pipeline",
            "primary_bubble_id": "",
            "primary_bubble_label": "",
            "related_bubble_ids": [],
            "feedback_state": "pending",
            "feedback_controls": ["relevant"],
            "article_sections": [],
            "article_profile": "",
            "article_module_order": [],
            "article_config_snapshot": {},
        }
        request = {
            "request_id": "req-learning-strict-001",
            "session_id": "session-learning-strict-001",
            "raw_text": "build implementation scaffold for bridge",
            "caller_hints": {"thought_id": thought["thought_id"], "routing_tags": ["metathought"]},
            "domain_hints": [],
            "source_refs": [],
        }
        context = heuristic_classify_turn(self.root, request)
        attributes = dict(context.get("attributes", {}) or {})
        attributes.setdefault("caller_hints", {})["thought_id"] = thought["thought_id"]
        attributes["context_policy"] = {
            "mode": "semantic_narrow",
            "depth_mode": "contextual",
            "include_layers": ["session", "workspace", "user", "global"],
            "exclude_layers": ["user", "global"],
        }
        context["attributes"] = attributes
        append_jsonl(self.root / "product" / "inner_world_v1" / "data" / "reasoning_runtime" / "context_states.jsonl", context)
        append_jsonl(
            self.root / "product" / "inner_world_v1" / "data" / "reasoning_runtime" / "reasoning_results.jsonl",
            {
                "result_id": "result-learning-strict-001",
                "request_id": "req-learning-strict-001",
                "pipeline_id": "idea_embedding_v1",
                "response_text": "strict scaffold",
            },
        )
        packets_path = self.root / "product" / "inner_world_v1" / "data" / "thought_packets.jsonl"
        packets_path.parent.mkdir(parents=True, exist_ok=True)
        write_jsonl(packets_path, [thought])

        result = record_feedback(self.root, thought["insight_id"], "relevant")

        self.assertNotIn("bridge_learning_event", result)
        self.assertEqual(load_learning_events(self.root), [])
        self.assertEqual(load_bridge_state(self.root).get("behavior_patterns", []), [])


if __name__ == "__main__":
    unittest.main()
