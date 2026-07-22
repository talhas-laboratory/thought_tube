from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from conversation_os.holodeck import (
    _collect_workspace_projection_candidates,
    _relative_workspace_path,
    _workspace_source_ref_display,
)


class HolodeckSourceRefPortabilityTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.base = Path(self.tempdir.name)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _seed_terms(self) -> list[str]:
        return ["bridge", "holodeck", "contextualization", "integration", "bounded"]

    def test_explicit_source_ref_is_preserved_when_path_aliases_differ(self) -> None:
        private_root = self.base / "private_var" / "workspace"
        private_root.mkdir(parents=True)
        public_root = self.base / "var" / "workspace"
        public_root.parent.mkdir(parents=True)
        os.symlink(private_root, public_root, target_is_directory=True)

        doc_path = private_root / "docs" / "plans" / "chat-bridge.md"
        doc_path.parent.mkdir(parents=True)
        doc_path.write_text(
            "# Chat Bridge\n\nGround bridge integration in bounded holodeck contextualization.\n",
            encoding="utf-8",
        )
        explicit_ref = "docs/plans/chat-bridge.md"
        artifacts = [
            {
                "artifact_id": "artifact-001",
                "title": "Bridge plan",
                "summary": "Ground bridge integration.",
                "source_ref": explicit_ref,
            }
        ]

        candidates, layers = _collect_workspace_projection_candidates(
            public_root,
            self._seed_terms(),
            artifacts,
            max_source_refs=6,
        )

        self.assertIn("artifact_docs", layers)
        artifact_candidates = [row for row in candidates if row.get("source_layer") == "artifact_doc"]
        self.assertEqual(len(artifact_candidates), 1)
        self.assertEqual(artifact_candidates[0]["source_ref"], explicit_ref)

    def test_plan_doc_source_ref_survives_root_alias_mismatch(self) -> None:
        private_root = self.base / "private_var" / "workspace"
        private_root.mkdir(parents=True)
        public_root = self.base / "var" / "workspace"
        public_root.parent.mkdir(parents=True)
        os.symlink(private_root, public_root, target_is_directory=True)

        doc_path = private_root / "docs" / "plans" / "alias-plan.md"
        doc_path.parent.mkdir(parents=True)
        doc_path.write_text(
            "# Alias Plan\n\nHolodeck contextualization bridge integration notes.\n",
            encoding="utf-8",
        )

        candidates, layers = _collect_workspace_projection_candidates(
            public_root,
            self._seed_terms(),
            [],
            max_source_refs=6,
        )

        self.assertIn("plan_docs", layers)
        plan_candidates = [row for row in candidates if row.get("source_layer") == "plan_doc"]
        self.assertEqual(len(plan_candidates), 1)
        self.assertEqual(plan_candidates[0]["source_ref"], "docs/plans/alias-plan.md")

    def test_relative_workspace_path_uses_resolved_roots(self) -> None:
        private_root = self.base / "private_var" / "workspace"
        private_root.mkdir(parents=True)
        public_root = self.base / "var" / "workspace"
        public_root.parent.mkdir(parents=True)
        os.symlink(private_root, public_root, target_is_directory=True)

        doc_path = private_root / "docs" / "plans" / "note.md"
        doc_path.parent.mkdir(parents=True)
        doc_path.write_text("note\n", encoding="utf-8")

        unresolved = public_root / "docs" / "plans" / "note.md"
        self.assertEqual(_relative_workspace_path(public_root, unresolved), "docs/plans/note.md")

    def test_outside_root_path_returns_external_reference(self) -> None:
        root = self.base / "workspace"
        root.mkdir()
        outside = self.base / "outside.md"
        outside.write_text("outside\n", encoding="utf-8")

        self.assertTrue(_workspace_source_ref_display(root, outside).startswith("external:"))

    def test_missing_explicit_ref_falls_back_to_relative_path(self) -> None:
        root = self.base / "workspace"
        doc_path = root / "docs" / "plans" / "fallback.md"
        doc_path.parent.mkdir(parents=True)
        doc_path.write_text("fallback\n", encoding="utf-8")

        self.assertEqual(_workspace_source_ref_display(root, doc_path), "docs/plans/fallback.md")


if __name__ == "__main__":
    unittest.main()
