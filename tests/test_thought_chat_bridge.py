from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from conversation_os.product_inner_world import chat_with_thought
from conversation_os.storage import write_jsonl
from conversation_os.thought_factory import thought_packets_path


def _minimal_thought(thought_id: str = "thought-bridge-001") -> dict:
    return {
        "packet_id": "packet-bridge-001",
        "thought_id": thought_id,
        "insight_id": "insight-bridge-001",
        "title": "Bridge Thought",
        "short_text": "A thought for bridge chat wiring.",
        "article_title": "Bridge Thought",
        "article_markdown": "## Section\n\nBody.",
        "status": "active",
        "review_status": "ready_for_review",
        "evidence_status": "grounded",
        "confidence_score": 0.9,
        "relevance_score": 0.8,
        "novelty_score": 0.7,
        "source_refs": ["source://bridge-thought"],
        "source_item_ids": [],
        "meta_refs": [],
        "shared_primitive_key": "pattern",
        "shared_primitive_label": "Pattern",
        "what_changed": "Bridge wiring test.",
        "why_it_matters_now": "Thought chat should route through bridge.",
        "next_action": "Inspect and continue.",
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


class ThoughtChatBridgeTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        data_dir = self.root / "product" / "inner_world_v1" / "data"
        data_dir.mkdir(parents=True)
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
                        "execution_mode": "operators",
                    },
                }
            ),
            encoding="utf-8",
        )
        write_jsonl(thought_packets_path(self.root), [_minimal_thought()])
        runtime = data_dir / "reasoning_runtime"
        runtime.mkdir(parents=True)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    @mock.patch("conversation_os.product_inner_world.run_reasoning")
    @mock.patch("conversation_os.product_inner_world.build_thought_context")
    def test_chat_with_thought_uses_bridge_when_enabled(
        self,
        context_mock: mock.MagicMock,
        reasoning_mock: mock.MagicMock,
    ) -> None:
        context_mock.return_value = {
            "character": "Grounded mirror",
            "system_prompt": "Stay grounded.",
            "context_summary": "Bridge thought summary.",
            "routing_tags": ["metathought"],
            "source_snippets": [{"title": "Snippet", "source_ref": "source://bridge-thought", "excerpt": "Evidence."}],
            "thought": _minimal_thought(),
        }
        reasoning_mock.return_value = {
            "context_state": {"attributes": {"routing_source": "agent"}},
            "result": {"response_text": "Bridge-backed thought reply."},
        }

        result = chat_with_thought(self.root, "thought-bridge-001", "Why does this matter now?")

        reasoning_mock.assert_called_once()
        request = reasoning_mock.call_args[0][1]
        self.assertEqual(request.surface, "thought_chat")
        self.assertEqual(request.caller_hints["thought_id"], "thought-bridge-001")
        self.assertEqual(result["assistant_message"]["content"], "Bridge-backed thought reply.")
        self.assertEqual(result["thread"]["backend_id"], "bridge:agent")
        self.assertIn("reasoning", result)

    @mock.patch("conversation_os.product_inner_world.request_openclaw_reply")
    @mock.patch("conversation_os.product_inner_world.build_thought_context")
    def test_chat_with_thought_keeps_openclaw_path_when_bridge_disabled(
        self,
        context_mock: mock.MagicMock,
        openclaw_mock: mock.MagicMock,
    ) -> None:
        runtime_path = self.root / "product" / "inner_world_v1" / "config" / "runtime.json"
        runtime = json.loads(runtime_path.read_text(encoding="utf-8"))
        runtime["bridge"]["enabled"] = False
        runtime_path.write_text(json.dumps(runtime), encoding="utf-8")

        context_mock.return_value = {
            "character": "Grounded mirror",
            "system_prompt": "Stay grounded.",
            "context_summary": "Direct openclaw summary.",
            "routing_tags": [],
            "source_snippets": [],
            "thought": _minimal_thought(),
        }
        openclaw_mock.return_value = {"content": "OpenClaw direct reply.", "backend_id": "openclaw_gateway"}

        result = chat_with_thought(self.root, "thought-bridge-001", "What next?")

        openclaw_mock.assert_called_once()
        self.assertEqual(result["assistant_message"]["content"], "OpenClaw direct reply.")
        self.assertEqual(result["thread"]["backend_id"], "openclaw_gateway")
        self.assertNotIn("reasoning", result)


if __name__ == "__main__":
    unittest.main()
