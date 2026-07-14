from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from conversation_os.development_intake import record_development_idea
from conversation_os.element_capture import list_element_captures
from conversation_os.element_ingest import ingest_to_element_space
from conversation_os.product_inner_world import append_mobile_capture
from conversation_os.product_thoughtboard import ingest_pasted_conversation


class ElementIngestTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        config_dir = self.root / "product" / "inner_world_v1" / "config"
        config_dir.mkdir(parents=True)
        repo_config = Path(__file__).resolve().parents[1] / "product" / "inner_world_v1" / "config"
        shutil.copy(repo_config / "product_elements.json", config_dir / "product_elements.json")
        (config_dir / "runtime.json").write_text(
            json.dumps({"bridge": {"enabled": False, "tracking": {"element_context": {"min_capture_chars": 12}}}}),
            encoding="utf-8",
        )
        runtime = self.root / "product" / "inner_world_v1" / "data" / "reasoning_runtime"
        runtime.mkdir(parents=True)
        personal = self.root / "product" / "development_layer_v1" / "config"
        personal.mkdir(parents=True)
        (personal / "personal_interface_profile.json").write_text(
            json.dumps({"profile_id": "test", "communication_mode": "concept_translation"}),
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_manual_ingest_routes_marketing_text(self) -> None:
        result = ingest_to_element_space(
            self.root,
            raw_text="Our launch positioning should emphasize cognitive infrastructure for builders.",
            source_kind="manual_ingest",
            surface_hints=["marketing"],
        )
        self.assertTrue(result["captured"])
        self.assertEqual(result["element_binding"]["element_key"], "marketing")
        captures = list_element_captures(self.root, "marketing")
        self.assertEqual(captures["count"], 1)

    def test_mobile_capture_routes_to_frontend(self) -> None:
        result = append_mobile_capture(
            self.root,
            content="Mobile feed should reveal thought depth gradually instead of flattening everything at once.",
        )
        ingest = result["element_ingest"]
        self.assertTrue(ingest["captured"])
        self.assertEqual(ingest["element_binding"]["element_key"], "frontend")
        captures = list_element_captures(self.root, "frontend")
        self.assertGreaterEqual(captures["count"], 1)

    def test_thoughtboard_paste_routes_via_content(self) -> None:
        transcript = (
            "user: How should we price the pro tier?\n"
            "assistant: Start with a simple subscription and one premium workflow unlock."
        )
        result = ingest_pasted_conversation(self.root, "Pricing discussion", transcript)
        ingest = result["element_ingest"]
        self.assertTrue(ingest["captured"])
        self.assertEqual(ingest["element_binding"]["element_key"], "monetization")

    def test_development_idea_routes_bridge_work_to_backend(self) -> None:
        record = record_development_idea(
            self.root,
            "Improve bridge session tracking and MCP routing for tracked sessions.",
            desired_effect="Keep turns session-scoped and cheap.",
            surface_hints=["bridge"],
        )
        ingest = record["element_ingest"]
        self.assertTrue(ingest["captured"])
        self.assertEqual(ingest["element_binding"]["element_key"], "backend")


if __name__ == "__main__":
    unittest.main()
