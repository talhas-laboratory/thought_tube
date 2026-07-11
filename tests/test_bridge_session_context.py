from __future__ import annotations

import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from conversation_os.bridge_prepare import prepare_turn
from conversation_os.bridge_session_context import (
    CONTEXT_MODE_BOUNDED_GLOBAL,
    CONTEXT_MODE_SESSION_ONLY,
    build_dynamic_session_context,
    resolve_context_retrieval_mode,
    should_skip_agent_classify,
)
from conversation_os.bridge_session_tracking import start_bridge_session
from conversation_os.reasoning_bridge import classify_turn, get_context_bundle, heuristic_classify_turn


class BridgeSessionContextTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        config_dir = self.root / "product" / "inner_world_v1" / "config"
        config_dir.mkdir(parents=True)
        (config_dir / "runtime.json").write_text(
            json.dumps(
                {
                    "bridge": {
                        "enabled": True,
                        "tracking": {
                            "require_active_session": True,
                            "default_context_mode": "session_only",
                            "max_turn_window": 12,
                        },
                    }
                }
            ),
            encoding="utf-8",
        )
        runtime = self.root / "product" / "inner_world_v1" / "data" / "reasoning_runtime"
        runtime.mkdir(parents=True)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_resolve_context_retrieval_mode_defaults_to_session_only_for_active_session(self) -> None:
        start_bridge_session(self.root, session_id="session-ctx-001", surface="cursor")
        mode = resolve_context_retrieval_mode(
            self.root,
            session_id="session-ctx-001",
            depth_mode="contextual",
            policy=None,
            caller_hints={},
        )
        self.assertEqual(mode, CONTEXT_MODE_SESSION_ONLY)

    def test_build_dynamic_session_context_from_trace(self) -> None:
        start_bridge_session(self.root, session_id="session-ctx-002", surface="cursor", title="ctx")
        prepare_turn(
            self.root,
            raw_text="wire dynamic session context",
            session_id="session-ctx-002",
            surface="cursor",
            write_steering_file=False,
        )
        context = build_dynamic_session_context(self.root, "session-ctx-002")
        self.assertEqual(context["turn_count"], 1)
        self.assertEqual(len(context["recent_turns"]), 1)
        self.assertIn("wire dynamic session context", context["recent_turns"][0]["raw_text"])
        self.assertIn("Recent session turns", context["continuity_markdown"])

    @mock.patch("conversation_os.reasoning_bridge.build_retrieval_bundle")
    def test_get_context_bundle_skips_global_retrieval_for_tracked_session(
        self,
        retrieval_mock: mock.MagicMock,
    ) -> None:
        start_bridge_session(self.root, session_id="session-ctx-003", surface="cursor")
        prepare_turn(
            self.root,
            raw_text="first turn",
            session_id="session-ctx-003",
            surface="cursor",
            write_steering_file=False,
        )
        request = {
            "request_id": "req-ctx-003",
            "session_id": "session-ctx-003",
            "raw_text": "second turn",
            "caller_hints": {"workspace_id": "inner_space"},
            "domain_hints": [],
            "source_refs": [],
        }
        context_state = heuristic_classify_turn(self.root, request)
        start = time.time()
        bundle = get_context_bundle(self.root, context_state)
        elapsed = time.time() - start

        retrieval_mock.assert_not_called()
        self.assertEqual(bundle["context_retrieval_mode"], CONTEXT_MODE_SESSION_ONLY)
        self.assertEqual(bundle["global_fallback"]["count"], 0)
        self.assertGreaterEqual(len(bundle["session_local"]), 1)
        self.assertIn("recent_turns", bundle["session_context"])
        self.assertLess(elapsed, 2.0)

    @mock.patch("conversation_os.reasoning_bridge.build_retrieval_bundle")
    def test_get_context_bundle_allows_note_agent_policy_to_widen_tracked_session(
        self,
        retrieval_mock: mock.MagicMock,
    ) -> None:
        start_bridge_session(self.root, session_id="session-ctx-005", surface="cursor")
        prepare_turn(
            self.root,
            raw_text="capture first thought",
            session_id="session-ctx-005",
            surface="cursor",
            write_steering_file=False,
        )
        request = {
            "request_id": "req-ctx-005",
            "session_id": "session-ctx-005",
            "surface": "thought_chat",
            "raw_text": "I think this pattern connects to earlier notes. What does it suggest?",
            "caller_hints": {"workspace_id": "thought:thought-005", "thought_id": "thought-005"},
            "domain_hints": [],
            "source_refs": [],
        }
        context_state = heuristic_classify_turn(self.root, request)
        context_state.setdefault("attributes", {})["note_agent"] = {
            "user_state": {"mode": "reflective"},
            "retrieval_policy": {
                "retrieval_mode": "session_plus_ocean",
                "cross_ocean": False,
                "retrieval_limit": 6,
                "neighbor_limit": 4,
                "include_layers": ["session", "workspace", "user", "global"],
                "exclude_layers": [],
                "anchor_strategy": "topic_first",
            },
        }
        retrieval_mock.return_value = {
            "query": "pattern connects earlier notes",
            "seed_capsules": [{"label": "pattern"}],
            "related_capsules": [],
            "included_links": [],
            "source_refs": [],
            "count": 1,
            "alias_hits": [],
            "anchor_pond": "knowledge",
            "include_cross_pond": False,
        }

        bundle = get_context_bundle(self.root, context_state)

        retrieval_mock.assert_called_once()
        self.assertEqual(bundle["context_retrieval_mode"], CONTEXT_MODE_BOUNDED_GLOBAL)
        self.assertEqual(bundle["global_fallback"]["count"], 1)

    @mock.patch("conversation_os.reasoning_bridge._classify_turn_with_agent")
    def test_classify_turn_skips_agent_for_tracked_session(self, agent_mock: mock.MagicMock) -> None:
        start_bridge_session(self.root, session_id="session-ctx-004", surface="cursor")
        request = {
            "request_id": "req-ctx-004",
            "session_id": "session-ctx-004",
            "raw_text": "stay fast",
            "caller_hints": {},
            "domain_hints": [],
            "source_refs": [],
        }
        self.assertTrue(should_skip_agent_classify(self.root, request))
        classify_turn(self.root, request)
        agent_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
