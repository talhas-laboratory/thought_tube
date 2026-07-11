from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from conversation_os.bridge_prepare import prepare_turn
from conversation_os.bridge_session_context import build_element_scoped_session_context
from conversation_os.bridge_session_tracking import end_bridge_session, start_bridge_session
from conversation_os.element_capture import (
    CAPTURE_STATUS_PROVISIONAL,
    CAPTURE_STATUS_PROMOTED,
    list_element_captures,
    list_promoted_element_records,
    should_capture_turn,
)
from conversation_os.element_curator import apply_curator_recommendations, review_session_for_promotion


class ElementCaptureTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        config_dir = self.root / "product" / "inner_world_v1" / "config"
        config_dir.mkdir(parents=True)
        repo_config = Path(__file__).resolve().parents[1] / "product" / "inner_world_v1" / "config"
        shutil.copy(repo_config / "product_elements.json", config_dir / "product_elements.json")
        (config_dir / "runtime.json").write_text(
            json.dumps(
                {
                    "bridge": {
                        "enabled": False,
                        "tracking": {
                            "require_active_session": True,
                            "element_context": {
                                "min_capture_chars": 20,
                                "min_capture_confidence": 0.6,
                            },
                        },
                    }
                }
            ),
            encoding="utf-8",
        )
        runtime = self.root / "product" / "inner_world_v1" / "data" / "reasoning_runtime"
        runtime.mkdir(parents=True)

        holodeck_dir = self.root / "memory" / "workspaces" / "sol-frontend"
        holodeck_dir.mkdir(parents=True)
        (holodeck_dir / "manifest.json").write_text(
            json.dumps(
                {
                    "workspace_id": "sol-frontend",
                    "label": "SOL Frontend",
                    "status": "paused",
                    "goal": "Ship frontend surfaces",
                    "purpose": "Frontend element workspace",
                    "scope_in": ["product/mobile_surface_v1/"],
                }
            ),
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_should_capture_on_ingest_flag(self) -> None:
        should, trigger, confidence = should_capture_turn(
            raw_text="short",
            preview={"element_key": "frontend"},
            binding={"element_key": "frontend", "request_ingest": True},
        )
        self.assertTrue(should)
        self.assertEqual(trigger, "ingest")
        self.assertEqual(confidence, 1.0)

    @mock.patch("conversation_os.bridge_prepare.heuristic_classify_turn")
    def test_prepare_turn_creates_provisional_capture_for_ingest(self, classify_mock: mock.MagicMock) -> None:
        start_bridge_session(self.root, session_id="capture-session-001", element_key="frontend", surface="cursor")
        classify_mock.return_value = {
            "request_id": "req-capture-001",
            "active_topic": "frontend",
            "user_goal": "build",
            "reasoning_posture": "implementation",
            "depth_mode": "focused",
            "object_scope": "same_main",
            "attributes": {
                "routing_source": "heuristic",
                "bridge_behavior_ids": [],
                "context_policy": {},
                "steering_constraints": [],
                "control_packet_metadata": {},
            },
        }
        result = prepare_turn(
            self.root,
            raw_text="#ingest mobile feed should use bridge session context for continuity",
            session_id="capture-session-001",
            surface="cursor",
        )
        self.assertIsNotNone(result.get("element_capture"))
        captures = list_element_captures(self.root, "frontend", status=CAPTURE_STATUS_PROVISIONAL)
        self.assertEqual(captures["count"], 1)
        self.assertEqual(captures["captures"][0]["capture_trigger"], "ingest")

    @mock.patch("conversation_os.bridge_prepare.heuristic_classify_turn")
    def test_element_scoped_session_context_includes_holodeck_and_captures(self, classify_mock: mock.MagicMock) -> None:
        start_bridge_session(self.root, session_id="capture-session-002", element_key="frontend", surface="cursor")
        classify_mock.return_value = {
            "request_id": "req-capture-002",
            "active_topic": "frontend",
            "user_goal": "build",
            "reasoning_posture": "implementation",
            "depth_mode": "focused",
            "object_scope": "same_main",
            "attributes": {
                "routing_source": "heuristic",
                "bridge_behavior_ids": [],
                "context_policy": {},
                "steering_constraints": [],
                "control_packet_metadata": {},
            },
        }
        prepare_turn(
            self.root,
            raw_text="#ingest Decide that mobile capture should stay session-scoped by default for speed",
            session_id="capture-session-002",
            surface="cursor",
        )
        context = build_element_scoped_session_context(self.root, "capture-session-002")
        self.assertEqual(context["element_key"], "frontend")
        self.assertIn("element_context", context)
        self.assertIn("Provisional element captures", context["continuity_markdown"])
        self.assertIn("Element Holodeck", context["continuity_markdown"])

    @mock.patch("conversation_os.bridge_prepare.heuristic_classify_turn")
    def test_curator_promotes_ingest_capture_when_auto_apply(self, classify_mock: mock.MagicMock) -> None:
        start_bridge_session(
            self.root,
            session_id="capture-session-003",
            element_key="frontend",
            surface="cursor",
            auto_promote_review=True,
        )
        classify_mock.return_value = {
            "request_id": "req-capture-003",
            "active_topic": "frontend",
            "user_goal": "build",
            "reasoning_posture": "implementation",
            "depth_mode": "focused",
            "object_scope": "same_main",
            "attributes": {
                "routing_source": "heuristic",
                "bridge_behavior_ids": [],
                "context_policy": {},
                "steering_constraints": [],
                "control_packet_metadata": {},
            },
        }
        prepare_turn(
            self.root,
            raw_text="#ingest #promote We will keep frontend retrieval session-scoped unless the user asks for deep context",
            session_id="capture-session-003",
            surface="cursor",
        )
        review = review_session_for_promotion(self.root, "capture-session-003", auto_apply=True)
        self.assertGreaterEqual(review["capture_count"], 1)
        self.assertTrue(review["applied"])
        promoted = list_promoted_element_records(self.root, "frontend")
        self.assertGreaterEqual(promoted["count"], 1)

    def test_curator_rejects_low_signal_capture(self) -> None:
        from conversation_os.element_capture import append_element_capture

        start_bridge_session(self.root, session_id="capture-session-004", element_key="frontend", surface="cursor")
        capture = append_element_capture(
            self.root,
            element_key="frontend",
            raw_text="ok",
            session_id="capture-session-004",
            capture_trigger="ingest",
            confidence=1.0,
        )
        review = review_session_for_promotion(self.root, "capture-session-004")
        recommendation = review["recommendations"][0]
        self.assertTrue(recommendation["reject"])
        applied = apply_curator_recommendations(self.root, review["recommendations"])
        self.assertEqual(applied[0]["action"], "reject")
        rows = list_element_captures(self.root, "frontend", status="rejected")
        self.assertEqual(rows["captures"][0]["capture_id"], capture["capture_id"])


if __name__ == "__main__":
    unittest.main()
