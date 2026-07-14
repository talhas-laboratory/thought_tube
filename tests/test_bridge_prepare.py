from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from conversation_os.bridge_prepare import (
    load_bridge_session,
    prepare_turn,
    render_steering_markdown,
    resolve_session_id,
    thought_tube_dir,
)
from conversation_os.bridge_session_tracking import start_bridge_session
from conversation_os.reasoning_bridge import get_context_bundle
from conversation_os.storage import read_jsonl, session_events_path


class BridgePrepareTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        config_dir = self.root / "product" / "inner_world_v1" / "config"
        config_dir.mkdir(parents=True)
        (config_dir / "runtime.json").write_text(
            json.dumps({"bridge": {"enabled": False, "execution_mode": "operators"}}),
            encoding="utf-8",
        )
        runtime = self.root / "product" / "inner_world_v1" / "data" / "reasoning_runtime"
        runtime.mkdir(parents=True)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_resolve_session_id_is_stable_when_explicit(self) -> None:
        self.assertEqual(
            resolve_session_id(self.root, session_id="session-fixed", surface="cursor"),
            "session-fixed",
        )

    def test_render_steering_markdown_includes_policy(self) -> None:
        markdown = render_steering_markdown(
            {
                "routing_source": "heuristic",
                "active_topic": "bridge steering",
                "user_goal": "build",
                "reasoning_posture": "implementation",
                "depth_mode": "contextual",
                "object_scope": "same_main",
                "pipeline_id": "idea_embedding_v1",
                "bridge_behavior_ids": ["implementation_scaffold"],
                "context_policy": {
                    "mode": "semantic_narrow",
                    "depth_mode": "contextual",
                    "token_budget": 1200,
                    "include_layers": ["session", "workspace"],
                    "exclude_layers": [],
                    "cross_ocean": False,
                    "retrieval_limit": 6,
                    "neighbor_limit": 4,
                },
                "steering_constraints": ["preserve provenance"],
            },
            session_id="session-001",
            surface="cursor",
            bridge_config={"enabled": False},
        )
        self.assertIn("binding control-plane guidance", markdown)
        self.assertIn("semantic_narrow", markdown)
        self.assertIn("implementation_scaffold", markdown)

    @mock.patch("conversation_os.bridge_prepare.heuristic_classify_turn")
    def test_prepare_turn_writes_steering_file_and_ledger(self, classify_mock: mock.MagicMock) -> None:
        start_bridge_session(self.root, session_id="session-prepare-001", surface="cursor")
        classify_mock.return_value = {
            "request_id": "req-prepare-001",
            "active_topic": "steering",
            "user_goal": "build",
            "reasoning_posture": "implementation",
            "depth_mode": "contextual",
            "object_scope": "same_main",
            "attributes": {
                "routing_source": "heuristic",
                "pipeline_id": "idea_embedding_v1",
                "bridge_behavior_ids": [],
                "context_policy": {"mode": "semantic_narrow", "depth_mode": "contextual"},
                "steering_constraints": [],
                "control_packet_metadata": {},
            },
        }
        result = prepare_turn(
            self.root,
            raw_text="prepare steering for this turn",
            session_id="session-prepare-001",
            surface="cursor",
        )
        self.assertTrue(result["ok"])
        steering_path = Path(result["steering_file"])
        self.assertTrue(steering_path.exists())
        self.assertEqual(steering_path, thought_tube_dir(self.root) / "latest-steering.md")
        ledger_path = self.root / "product" / "inner_world_v1" / "data" / "reasoning_runtime" / "turn_ledger.jsonl"
        self.assertTrue(ledger_path.exists())
        session_path = (
            self.root
            / "product"
            / "inner_world_v1"
            / "data"
            / "reasoning_runtime"
            / "sessions"
            / "session-prepare-001.json"
        )
        self.assertTrue(session_path.exists())

    @mock.patch("conversation_os.bridge_prepare.heuristic_classify_turn")
    def test_prepare_turn_writes_session_event_for_strict_session_bundle(
        self,
        classify_mock: mock.MagicMock,
    ) -> None:
        start_bridge_session(self.root, session_id="session-prepare-002", surface="codex")
        classify_mock.return_value = {
            "request_id": "req-prepare-002",
            "active_topic": "bridge session continuity",
            "user_goal": "build",
            "reasoning_posture": "implementation",
            "depth_mode": "contextual",
            "object_scope": "same_main",
            "attributes": {
                "routing_source": "heuristic",
                "pipeline_id": "idea_embedding_v1",
                "bridge_behavior_ids": [],
                "context_policy": {"mode": "semantic_narrow", "depth_mode": "contextual"},
                "steering_constraints": [],
                "control_packet_metadata": {},
            },
        }

        result = prepare_turn(
            self.root,
            raw_text="prepare strict session continuity",
            session_id="session-prepare-002",
            surface="codex",
        )

        session_rows = read_jsonl(session_events_path(self.root, "session-prepare-002"))
        self.assertEqual(len(session_rows), 2)
        self.assertEqual(session_rows[1]["content"], "prepare strict session continuity")
        self.assertIn(result["ledger_entry_id"], session_rows[1]["source_ref"])

        session = load_bridge_session(self.root, "session-prepare-002")
        context_state = {
            "request_id": "req-followup-002",
            "active_topic": "bridge session continuity",
            "object_scope": "same_main",
            "object_id": "object-bridge-session-continuity",
            "user_goal": "build",
            "reasoning_posture": "implementation",
            "answer_shape": "implementation_scaffold",
            "active_workspace_id": "workspace-main",
            "depth_mode": "contextual",
            "confidence": 0.8,
            "bundle_layers": [],
            "attributes": {
                "session_id": session["session_id"],
                "caller_hints": {"workspace_id": "workspace-main"},
            },
        }

        bundle = get_context_bundle(self.root, context_state)
        user_turns = [row for row in bundle["session_local"] if row.get("kind") == "turn"]
        self.assertEqual(len(user_turns), 1)
        self.assertEqual(user_turns[0]["content"], "prepare strict session continuity")

if __name__ == "__main__":
    unittest.main()
