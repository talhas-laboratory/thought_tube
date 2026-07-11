from __future__ import annotations

import asyncio
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict
from unittest import mock

from conversation_os.bridge_mcp import (
    build_bridge_mcp_server,
    classify_preview,
    list_control_packet_summaries,
    summarize_control_packet_row,
    summarize_run_result,
)
from conversation_os.bridge_prepare import build_reasoning_request_payload
from conversation_os.reasoning_bridge import persist_control_packet


def _tool_result(payload: Any) -> Dict[str, Any]:
    if isinstance(payload, tuple) and len(payload) == 2:
        metadata = payload[1]
        if isinstance(metadata, dict) and isinstance(metadata.get("result"), dict):
            return metadata["result"]
    if isinstance(payload, dict):
        return payload
    raise TypeError(f"Unexpected MCP tool result shape: {type(payload)!r}")


class BridgeMcpTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        vendor = Path(__file__).resolve().parents[1] / ".vendor" / "mcp_py"
        if vendor.exists() and str(vendor) not in sys.path:
            sys.path.insert(0, str(vendor))
        config_dir = self.root / "product" / "inner_world_v1" / "config"
        config_dir.mkdir(parents=True)
        (config_dir / "runtime.json").write_text(
            json.dumps(
                {
                    "bridge": {
                        "enabled": True,
                        "agent": "thought_tube_router",
                        "execution_mode": "operators",
                    }
                }
            ),
            encoding="utf-8",
        )
        behavior_dir = config_dir / "bridge_behaviors"
        behavior_dir.mkdir(parents=True)
        (behavior_dir / "implementation_scaffold.json").write_text(
            json.dumps(
                {
                    "behavior_id": "implementation_scaffold",
                    "priority": 82,
                    "preferred_pipeline": "idea_embedding_v1",
                    "routing_mode": "bias",
                    "reasoning_posture": "implementation",
                    "response_directives": ["translate_into_steps"],
                    "operator_biases": {"prefer_actionable_structure": True},
                }
            ),
            encoding="utf-8",
        )
        runtime = self.root / "product" / "inner_world_v1" / "data" / "reasoning_runtime"
        runtime.mkdir(parents=True)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_summarize_control_packet_row(self) -> None:
        row = {
            "timestamp": "2026-06-25T12:00:00+00:00",
            "packet": {
                "packet_id": "pkt-001",
                "request_id": "req-001",
                "routing_source": "agent",
                "active_topic": "bridge mcp",
                "user_goal": "build",
                "reasoning_posture": "implementation",
                "pipeline_id": "idea_embedding_v1",
                "bridge_behaviors": ["implementation_scaffold"],
                "confidence": 0.9,
                "context_policy": {"mode": "semantic_narrow", "depth_mode": "contextual"},
            },
            "metadata": {},
        }
        summary = summarize_control_packet_row(row)
        self.assertEqual(summary["packet_id"], "pkt-001")
        self.assertEqual(summary["context_policy_mode"], "semantic_narrow")

    def test_list_control_packet_summaries_filters_and_limits(self) -> None:
        for index in range(3):
            persist_control_packet(
                self.root,
                {
                    "packet_id": f"pkt-{index}",
                    "request_id": "req-shared" if index < 2 else "req-other",
                    "routing_source": "agent",
                    "active_topic": f"topic-{index}",
                    "context_policy": {"mode": "semantic_narrow", "depth_mode": "contextual"},
                },
            )
        listed = list_control_packet_summaries(self.root, request_id="req-shared", limit=1)
        self.assertTrue(listed["ok"])
        self.assertEqual(listed["count"], 1)
        self.assertEqual(listed["total_available"], 2)
        self.assertEqual(listed["packets"][0]["request_id"], "req-shared")

    def test_mcp_server_registers_inspect_tools(self) -> None:
        if importlib.util.find_spec("mcp") is None:
            self.skipTest("mcp SDK not installed in active interpreter")
        server = build_bridge_mcp_server(self.root)
        tool_names = [tool.name for tool in asyncio.run(server.list_tools())]
        self.assertEqual(
            tool_names,
            [
                "bridge_inspect_request",
                "bridge_list_control_packets",
                "bridge_list_behaviors",
                "bridge_get_config",
                "bridge_record_assistant_turn",
                "bridge_compact_session",
                "bridge_get_session_context",
                "bridge_list_element_captures",
                "bridge_review_element_captures",
                "bridge_ingest_to_element",
                "bridge_start_session",
                "bridge_end_session",
                "bridge_get_session",
                "bridge_list_sessions",
                "bridge_get_session_trace",
                "bridge_prepare_turn",
                "bridge_classify_preview",
                "bridge_run",
            ],
        )

    def test_bridge_list_behaviors_via_tool(self) -> None:
        if importlib.util.find_spec("mcp") is None:
            self.skipTest("mcp SDK not installed in active interpreter")
        server = build_bridge_mcp_server(self.root)
        result = _tool_result(asyncio.run(server.call_tool("bridge_list_behaviors", {})))
        self.assertTrue(result["ok"])
        behavior_ids = [row["behavior_id"] for row in result["behaviors"]]
        self.assertIn("implementation_scaffold", behavior_ids)

    def test_bridge_get_config_via_tool(self) -> None:
        if importlib.util.find_spec("mcp") is None:
            self.skipTest("mcp SDK not installed in active interpreter")
        server = build_bridge_mcp_server(self.root)
        result = _tool_result(asyncio.run(server.call_tool("bridge_get_config", {})))
        self.assertTrue(result["ok"])
        self.assertTrue(result["config"]["enabled"])
        self.assertEqual(result["config"]["execution_mode"], "operators")

    @mock.patch("conversation_os.bridge_mcp.inspect_reasoning_request_impl")
    def test_bridge_inspect_request_returns_not_found_envelope(self, inspect_mock: mock.MagicMock) -> None:
        if importlib.util.find_spec("mcp") is None:
            self.skipTest("mcp SDK not installed in active interpreter")
        inspect_mock.side_effect = FileNotFoundError("No reasoning context found for request_id=missing")
        server = build_bridge_mcp_server(self.root)
        result = _tool_result(
            asyncio.run(server.call_tool("bridge_inspect_request", {"request_id": "missing"}))
        )
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "request_not_found")

    def test_build_reasoning_request_payload_requires_text(self) -> None:
        with self.assertRaises(ValueError):
            build_reasoning_request_payload(raw_text="   ")

    @mock.patch("conversation_os.bridge_mcp.classify_turn_impl")
    def test_classify_preview_returns_bounded_summary(self, classify_mock: mock.MagicMock) -> None:
        classify_mock.return_value = {
            "request_id": "req-preview-001",
            "active_topic": "bridge mcp",
            "user_goal": "build",
            "reasoning_posture": "implementation",
            "depth_mode": "contextual",
            "object_scope": "same_main",
            "attributes": {
                "routing_source": "agent",
                "pipeline_id": "idea_embedding_v1",
                "control_packet_id": "pkt-preview-001",
                "bridge_behavior_ids": ["implementation_scaffold"],
                "context_policy": {"mode": "semantic_narrow", "depth_mode": "contextual"},
                "steering_constraints": [],
                "control_packet_metadata": {"validation_warnings": []},
            },
        }
        request = build_reasoning_request_payload(raw_text="preview bridge routing")
        result = classify_preview(self.root, request)
        self.assertTrue(result["ok"])
        self.assertEqual(result["preview"]["routing_source"], "agent")
        self.assertEqual(result["preview"]["control_packet_id"], "pkt-preview-001")

    @mock.patch("conversation_os.bridge_mcp.prepare_turn_impl")
    def test_bridge_prepare_turn_via_tool(self, prepare_mock: mock.MagicMock) -> None:
        if importlib.util.find_spec("mcp") is None:
            self.skipTest("mcp SDK not installed in active interpreter")
        prepare_mock.return_value = {
            "ok": True,
            "session_id": "session-mcp-001",
            "steering_markdown": "# steering",
            "routing_source": "heuristic",
        }
        server = build_bridge_mcp_server(self.root)
        result = _tool_result(
            asyncio.run(server.call_tool("bridge_prepare_turn", {"raw_text": "steer this turn"}))
        )
        self.assertTrue(result["ok"])
        prepare_mock.assert_called_once()

    @mock.patch("conversation_os.bridge_mcp.run_reasoning_impl")
    def test_bridge_run_via_tool(self, run_mock: mock.MagicMock) -> None:
        if importlib.util.find_spec("mcp") is None:
            self.skipTest("mcp SDK not installed in active interpreter")
        run_mock.return_value = {
            "context_state": {
                "request_id": "req-run-001",
                "attributes": {"routing_source": "heuristic", "control_packet_id": ""},
            },
            "route": {"pipeline_id": "idea_embedding_v1"},
            "result": {
                "response_text": "scaffold reply",
                "integration_verdict": "fit",
                "fit_score": 0.8,
                "confidence": 0.7,
                "recommended_next_action": "continue",
                "operator_trace": ["template_operator"],
            },
            "evaluation": {
                "integration_verdict": "fit",
                "fit_score": 0.8,
                "novelty_score": 0.4,
                "generic_flattening_risk": 0.1,
            },
        }
        server = build_bridge_mcp_server(self.root)
        result = _tool_result(
            asyncio.run(
                server.call_tool(
                    "bridge_run",
                    {"raw_text": "run the bridge spine", "request_id": "req-run-001"},
                )
            )
        )
        self.assertTrue(result["ok"])
        self.assertEqual(result["summary"]["response_text"], "scaffold reply")
        run_mock.assert_called_once()

    @mock.patch("conversation_os.bridge_mcp.classify_turn_impl")
    def test_bridge_classify_preview_via_tool(self, classify_mock: mock.MagicMock) -> None:
        if importlib.util.find_spec("mcp") is None:
            self.skipTest("mcp SDK not installed in active interpreter")
        classify_mock.return_value = {
            "request_id": "req-preview-tool",
            "active_topic": "routing",
            "user_goal": "understand",
            "reasoning_posture": "exploration",
            "depth_mode": "contextual",
            "object_scope": "same_main",
            "attributes": {"routing_source": "heuristic", "bridge_behavior_ids": []},
        }
        server = build_bridge_mcp_server(self.root)
        result = _tool_result(
            asyncio.run(server.call_tool("bridge_classify_preview", {"raw_text": "how does routing work?"}))
        )
        self.assertTrue(result["ok"])
        self.assertEqual(result["preview"]["routing_source"], "heuristic")

    def test_summarize_run_result(self) -> None:
        summary = summarize_run_result(
            {
                "context_state": {
                    "request_id": "req-run-002",
                    "attributes": {"routing_source": "agent", "control_packet_id": "pkt-002"},
                },
                "route": {"pipeline_id": "idea_embedding_v1"},
                "result": {"response_text": "done", "integration_verdict": "fit", "fit_score": 0.9},
                "evaluation": {"integration_verdict": "fit", "fit_score": 0.9, "novelty_score": 0.5},
            }
        )
        self.assertEqual(summary["request_id"], "req-run-002")
        self.assertEqual(summary["response_text"], "done")


if __name__ == "__main__":
    unittest.main()
