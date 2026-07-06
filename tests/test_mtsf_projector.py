import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from conversation_os.cli import init_repo
from conversation_os.mtsf_extraction import (
    default_extraction_evals_dir,
    materialize_extraction_draft,
)
from conversation_os.mtsf_projector import (
    materialize_stencil_projection,
    project_extraction_draft,
    resolve_stencil_projections,
    session_shape_index_path,
)
from conversation_os.mtsf_stencils import normalize_stencil_draft
from conversation_os.storage import read_json

REPO_ROOT = Path(__file__).resolve().parents[1]


class MtsfProjectorTestCase(unittest.TestCase):
    def test_hallway_projection_merges_declared_seed(self) -> None:
        draft_path = (
            default_extraction_evals_dir(REPO_ROOT)
            / "drafts"
            / "hallway-uncanny.reference.json"
        )
        draft = json.loads(draft_path.read_text(encoding="utf-8"))
        projections = resolve_stencil_projections(REPO_ROOT, draft["stencil_drafts"])
        self.assertEqual(len(projections), 1)
        self.assertEqual(projections[0].action, "merge_declared_seed")
        self.assertEqual(projections[0].stencil_id, "stencil-context-warps-topology")
        self.assertFalse(projections[0].quarantine)

    def test_latent_triangulation_projection_matches_seed(self) -> None:
        draft_path = (
            default_extraction_evals_dir(REPO_ROOT)
            / "drafts"
            / "latent-triangulation.reference.json"
        )
        draft = json.loads(draft_path.read_text(encoding="utf-8"))
        result = project_extraction_draft(REPO_ROOT, draft)
        self.assertIn("stencil-context-warps-topology", result.active_stencil_ids)
        self.assertEqual(len(result.shape_instances), 1)
        self.assertEqual(result.shape_instances[0]["entity_id"], "entity-context-field")

    def test_novel_stencil_registers_provisional(self) -> None:
        projections = resolve_stencil_projections(
            REPO_ROOT,
            [
                {
                    "proposed_name": "novel loop",
                    "role_entities": [
                        {"role_type": "controller"},
                        {"role_type": "buffer"},
                        {"role_type": "sink"},
                    ],
                    "relation_topology": [
                        {
                            "source_role_ref": "controller",
                            "target_role_ref": "buffer",
                            "primitive": "modulates",
                        },
                        {
                            "source_role_ref": "buffer",
                            "target_role_ref": "sink",
                            "primitive": "enables",
                        },
                    ],
                    "dynamics_class": "oscillation",
                    "symmetry_profile": "mixed",
                    "facet_completeness": {"causal_geometry": True},
                    "confidence": 0.7,
                    "evidence": {"spans": ["test only"]},
                }
            ],
        )
        self.assertEqual(projections[0].action, "register_provisional")
        self.assertTrue(projections[0].quarantine)
        self.assertTrue(projections[0].stencil_id.startswith("stencil-proj-"))

    def test_materialize_extraction_writes_shape_index(self) -> None:
        tempdir = tempfile.TemporaryDirectory()
        root = Path(tempdir.name)
        init_repo(root)
        docs_link = root / "docs"
        if docs_link.exists() or docs_link.is_symlink():
            if docs_link.is_symlink() or docs_link.is_file():
                docs_link.unlink()
            else:
                shutil.rmtree(docs_link)
        os.symlink(REPO_ROOT / "docs", docs_link, target_is_directory=True)

        session_id = "projection-session-test"
        session_dir_path = root / "memory" / "sessions" / session_id
        session_dir_path.mkdir(parents=True)
        (session_dir_path / "manifest.json").write_text(
            json.dumps(
                {
                    "session_id": session_id,
                    "title": "Projection test",
                    "started_at": "2026-07-06T12:00:00+00:00",
                    "ended_at": None,
                    "participants": ["user"],
                    "source_type": "live_session",
                    "status": "open",
                    "artifact_refs": {},
                    "domains": [],
                }
            ),
            encoding="utf-8",
        )

        draft_path = (
            default_extraction_evals_dir(REPO_ROOT)
            / "drafts"
            / "hallway-uncanny.reference.json"
        )
        draft = json.loads(draft_path.read_text(encoding="utf-8"))
        draft["session_id"] = session_id
        result = materialize_extraction_draft(root, session_id, draft)
        self.assertTrue(result["validation_ok"])
        self.assertIn("projection", result)
        self.assertIn("mtsf_shape_index", result["artifact_refs"])

        index = read_json(session_shape_index_path(root, session_id))
        self.assertIn("stencil-context-warps-topology", index["stencils"])
        self.assertEqual(len(index["instances"]), 1)
        projection = read_json(session_dir_path / "mtsf" / "stencil_projection.json")
        self.assertEqual(projection["active_stencil_ids"], ["stencil-context-warps-topology"])
        tempdir.cleanup()

    def test_normalize_stencil_draft_still_available(self) -> None:
        normalized = normalize_stencil_draft(
            {
                "role_entities": [{"role_type": "field"}],
                "relation_topology": [],
            }
        )
        self.assertTrue(normalized["role_entities"][0]["role_id"].startswith("r-field-"))


if __name__ == "__main__":
    unittest.main()
