from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from conversation_os.bridge_prepare import prepare_turn
from conversation_os.bridge_session_tracking import start_bridge_session
from conversation_os.element_workspace_binding import build_workspace_binding_bundle
from conversation_os.storage import ensure_dir


class ElementWorkspaceBindingTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        config_dir = self.root / "product" / "inner_world_v1" / "config"
        config_dir.mkdir(parents=True)
        repo_config = Path(__file__).resolve().parents[1] / "product" / "inner_world_v1" / "config"
        shutil.copy(repo_config / "product_elements.json", config_dir / "product_elements.json")
        shutil.copy(repo_config / "workspace_subprojects.json", config_dir / "workspace_subprojects.json")
        (config_dir / "runtime.json").write_text(
            json.dumps(
                {
                    "bridge": {
                        "enabled": False,
                        "tracking": {
                            "require_active_session": True,
                            "default_session_binding": {
                                "element_key": "frontend",
                                "holodeck_id": "sol-frontend",
                                "subproject_id": "sol-frontend-mobile-capture",
                            },
                        },
                    }
                }
            ),
            encoding="utf-8",
        )
        holodeck_dir = self.root / "memory" / "workspaces" / "sol-frontend"
        ensure_dir(holodeck_dir)
        holodeck_dir.joinpath("manifest.json").write_text(
            json.dumps(
                {
                    "workspace_id": "sol-frontend",
                    "goal": "Ship frontend surfaces",
                    "scope_in": ["product/thought_capture_pwa/"],
                    "scope_out": ["backend internals"],
                    "workboard_ref": "docs/workboards/sol-frontend/README.md",
                    "pillars_ref": "docs/workboards/sol-frontend/PILLARS.md",
                    "active_subproject_id": "sol-frontend-mobile-capture",
                    "primary_artifact_root": "product/thought_capture_pwa/",
                }
            ),
            encoding="utf-8",
        )
        runtime = self.root / "product" / "inner_world_v1" / "data" / "reasoning_runtime"
        runtime.mkdir(parents=True)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_build_workspace_binding_bundle(self) -> None:
        bundle = build_workspace_binding_bundle(
            self.root,
            element_key="frontend",
            holodeck_id="sol-frontend",
            subproject_id="sol-frontend-mobile-capture",
        )
        self.assertEqual(bundle["primary_artifact_root"], "product/thought_capture_pwa/")
        self.assertIn("product/thought_capture_pwa/", bundle["artifact_roots"])
        self.assertTrue(any("primary artifact root" in c for c in bundle["workspace_steering_constraints"]))
        self.assertIn("Workspace binding", bundle["workspace_binding_markdown"])
        self.assertIn("SCROLL.md", bundle["workspace_binding_markdown"])

    def test_build_workspace_binding_bundle_ignores_prose_objectives_as_artifact_roots(self) -> None:
        holodeck_dir = self.root / "memory" / "workspaces" / "sol-prose"
        ensure_dir(holodeck_dir)
        holodeck_dir.joinpath("manifest.json").write_text(
            json.dumps(
                {
                    "workspace_id": "sol-prose",
                    "goal": "Ship frontend surfaces",
                    "scope_in": [
                        "product/thought_capture_pwa/",
                        "Fix bridge retrieval candidate timing.",
                    ],
                    "scope_out": ["backend internals"],
                    "active_subproject_id": "sol-frontend-mobile-capture",
                }
            ),
            encoding="utf-8",
        )

        bundle = build_workspace_binding_bundle(
            self.root,
            element_key="frontend",
            holodeck_id="sol-prose",
            subproject_id="sol-frontend-mobile-capture",
        )

        self.assertIn("product/thought_capture_pwa/", bundle["artifact_roots"])
        self.assertNotIn("Fix bridge retrieval candidate timing.", bundle["artifact_roots"])

    def test_prepare_turn_injects_workspace_binding(self) -> None:
        session_id = "test-workspace-binding"
        start_bridge_session(
            self.root,
            session_id=session_id,
            surface="cursor",
            element_key="frontend",
            holodeck_id="sol-frontend",
        )
        result = prepare_turn(
            self.root,
            raw_text="#frontend build the PWA capture shell",
            session_id=session_id,
            surface="cursor",
            caller_hints={"subproject_id": "sol-frontend-mobile-capture"},
            write_steering_file=False,
        )
        steering = str(result.get("steering_markdown", "") or "")
        self.assertIn("primary_artifact_root", steering)
        self.assertIn("product/thought_capture_pwa/", steering)
        self.assertIn("Workspace binding", steering)
        constraints = list(result.get("control_packet", {}).get("steering_constraints", []) or [])
        self.assertTrue(any("primary artifact root" in item for item in constraints))


if __name__ == "__main__":
    unittest.main()
