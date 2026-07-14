import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from conversation_os.bridge_prepare import prepare_turn, render_steering_markdown
from conversation_os.bridge_session_tracking import get_bridge_session, start_bridge_session
from conversation_os.element_routing import (
    load_product_elements,
    parse_turn_hashtags,
    resolve_element_binding,
)


class ElementRoutingTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        config_dir = self.root / "product" / "inner_world_v1" / "config"
        config_dir.mkdir(parents=True)
        shutil.copy(
            Path(__file__).resolve().parents[1]
            / "product"
            / "inner_world_v1"
            / "config"
            / "product_elements.json",
            config_dir / "product_elements.json",
        )
        (config_dir / "runtime.json").write_text(
            json.dumps({"bridge": {"enabled": False, "tracking": {"require_active_session": True}}}),
            encoding="utf-8",
        )
        runtime = self.root / "product" / "inner_world_v1" / "data" / "reasoning_runtime"
        runtime.mkdir(parents=True)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_parse_turn_hashtags(self) -> None:
        parsed = parse_turn_hashtags("#frontend #sidecar — polish mobile feed")
        self.assertEqual(parsed["element_key"], "frontend")
        self.assertEqual(parsed["topology_mode"], "sidecar")
        self.assertTrue(parsed["request_promote"] is False)

    def test_resolve_element_binding_from_hashtag(self) -> None:
        binding = resolve_element_binding(
            self.root,
            session={},
            caller_hints={},
            raw_text="#frontend mobile layout",
        )
        self.assertEqual(binding["element_key"], "frontend")
        self.assertEqual(binding["holodeck_id"], "sol-frontend")
        self.assertEqual(binding["element_method"], "hashtag")

    def test_start_session_with_element_key(self) -> None:
        session = start_bridge_session(
            self.root,
            session_id="element-session-001",
            element_key="frontend",
            surface="cursor",
        )
        self.assertEqual(session["element_key"], "frontend")
        self.assertEqual(session["holodeck_id"], "sol-frontend")
        self.assertEqual(session["topology_mode"], "spine")

    @mock.patch("conversation_os.bridge_prepare.heuristic_classify_turn")
    def test_prepare_turn_binds_frontend_hashtag_to_session(self, classify_mock: mock.MagicMock) -> None:
        start_bridge_session(self.root, session_id="element-session-002", surface="cursor")
        classify_mock.return_value = {
            "request_id": "req-element-001",
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
            raw_text="#frontend — improve mobile capture flow",
            session_id="element-session-002",
            surface="cursor",
        )
        self.assertEqual(result["element_binding"]["element_key"], "frontend")
        self.assertEqual(result["control_packet"]["element_key"], "frontend")
        self.assertIn("Product element", result["steering_markdown"])
        self.assertIn("`frontend`", result["steering_markdown"])

        session = get_bridge_session(self.root, "element-session-002")
        self.assertEqual(session["element_key"], "frontend")
        self.assertEqual(session["holodeck_id"], "sol-frontend")

    def test_render_steering_markdown_includes_product_element(self) -> None:
        markdown = render_steering_markdown(
            {
                "routing_source": "heuristic",
                "active_topic": "frontend",
                "user_goal": "build",
                "reasoning_posture": "implementation",
                "depth_mode": "focused",
                "object_scope": "same_main",
                "pipeline_id": "",
                "bridge_behavior_ids": [],
                "context_policy": {},
                "steering_constraints": [],
                "element_key": "frontend",
                "element_label": "Frontend",
                "topology_mode": "spine",
                "holodeck_id": "sol-frontend",
                "element_method": "hashtag",
                "element_confidence": 1.0,
            },
            session_id="session-element",
            surface="cursor",
        )
        self.assertIn("## Product element", markdown)
        self.assertIn("sol-frontend", markdown)

    def test_load_product_elements(self) -> None:
        payload = load_product_elements(self.root)
        keys = {row["element_key"] for row in payload["elements"]}
        self.assertEqual(keys, {"frontend", "backend", "marketing", "monetization"})


if __name__ == "__main__":
    unittest.main()
