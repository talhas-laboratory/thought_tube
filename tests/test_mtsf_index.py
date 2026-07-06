import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from conversation_os.cli import init_repo
from conversation_os.mtsf_extraction import default_extraction_evals_dir, materialize_extraction_draft
from conversation_os.mtsf_index import (
    bootstrap_global_from_seed,
    default_shape_index_path,
    find_wormhole_links,
    load_shape_index,
    promote_projection_to_global,
    promote_session_to_global,
    query_shape_index,
    rebuild_global_index,
    validate_shape_index,
)
from conversation_os.mtsf_projector import project_extraction_draft, session_shape_index_path
from conversation_os.storage import read_json

REPO_ROOT = Path(__file__).resolve().parents[1]


class MtsfIndexTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        init_repo(self.root)
        docs_link = self.root / "docs"
        if docs_link.exists() or docs_link.is_symlink():
            if docs_link.is_symlink() or docs_link.is_file():
                docs_link.unlink()
            else:
                shutil.rmtree(docs_link)
        os.symlink(REPO_ROOT / "docs", docs_link, target_is_directory=True)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _write_session_manifest(self, session_id: str) -> None:
        session_dir_path = self.root / "memory" / "sessions" / session_id
        session_dir_path.mkdir(parents=True)
        (session_dir_path / "manifest.json").write_text(
            json.dumps(
                {
                    "session_id": session_id,
                    "title": "Index test",
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

    def test_bootstrap_global_from_seed_loads_seed_stencils(self) -> None:
        index = bootstrap_global_from_seed(self.root)
        self.assertEqual(index["scope"], "global")
        self.assertIn("stencil-context-warps-topology", index["stencils"])
        self.assertGreaterEqual(len(index["fingerprints"]), 6)

    def test_promote_projection_to_global_writes_stats_and_events(self) -> None:
        draft_path = (
            default_extraction_evals_dir(REPO_ROOT)
            / "drafts"
            / "hallway-uncanny.reference.json"
        )
        draft = json.loads(draft_path.read_text(encoding="utf-8"))
        session_id = "index-promote-session"
        draft["session_id"] = session_id
        projection = project_extraction_draft(self.root, draft)

        result = promote_projection_to_global(
            self.root,
            projection,
            promotion_mode="explicit",
            validation_quarantine=False,
        )
        self.assertTrue(result["promoted"])
        self.assertIn("mtsf_global_shape_index", result["artifact_refs"])

        global_index = read_json(default_shape_index_path(self.root))
        self.assertEqual(global_index["scope"], "global")
        self.assertIn(session_id, global_index["sessions_contributed"])
        stats = global_index["stencil_stats"]["stencil-context-warps-topology"]
        self.assertEqual(stats["recurrence_count"], 1)
        self.assertIn(session_id, stats["session_ids"])

    def test_promote_session_to_global_from_session_artifacts(self) -> None:
        session_id = "index-session-artifacts"
        self._write_session_manifest(session_id)
        draft_path = (
            default_extraction_evals_dir(REPO_ROOT)
            / "drafts"
            / "latent-triangulation.reference.json"
        )
        draft = json.loads(draft_path.read_text(encoding="utf-8"))
        draft["session_id"] = session_id
        materialize_extraction_draft(self.root, session_id, draft)

        result = promote_session_to_global(self.root, session_id, mode="force")
        self.assertTrue(result["promoted"])
        global_index = read_json(default_shape_index_path(self.root))
        self.assertGreaterEqual(len(global_index["instances"]), 1)

    def test_rebuild_global_index_merges_multiple_sessions(self) -> None:
        for session_id, draft_name in (
            ("index-rebuild-a", "hallway-uncanny.reference.json"),
            ("index-rebuild-b", "latent-triangulation.reference.json"),
        ):
            self._write_session_manifest(session_id)
            draft_path = default_extraction_evals_dir(REPO_ROOT) / "drafts" / draft_name
            draft = json.loads(draft_path.read_text(encoding="utf-8"))
            draft["session_id"] = session_id
            materialize_extraction_draft(self.root, session_id, draft)

        result = rebuild_global_index(self.root)
        self.assertTrue(result["rebuilt"])
        self.assertEqual(result["merged_session_count"], 2)
        global_index = read_json(default_shape_index_path(self.root))
        self.assertIn("index-rebuild-a", global_index["sessions_contributed"])
        self.assertIn("index-rebuild-b", global_index["sessions_contributed"])

    def test_find_wormhole_links_across_subgraphs(self) -> None:
        index = bootstrap_global_from_seed(self.root)
        index["instances"] = [
            {
                "id": "shape-inst-a",
                "entity_id": "entity-work",
                "stencil_id": "stencil-context-warps-topology",
                "subgraph_id": "work",
                "status": "provisional",
            },
            {
                "id": "shape-inst-b",
                "entity_id": "entity-personal",
                "stencil_id": "stencil-context-warps-topology",
                "subgraph_id": "personal",
                "status": "provisional",
            },
        ]
        links = find_wormhole_links(index, stencil_id="stencil-context-warps-topology")
        self.assertEqual(len(links), 1)
        self.assertEqual(links[0]["subgraph_count"], 2)
        self.assertEqual(len(links[0]["pairs"]), 1)

    def test_query_shape_index_returns_orthogonal_candidates(self) -> None:
        global_index = bootstrap_global_from_seed(self.root)
        global_index_path = default_shape_index_path(self.root)
        global_index_path.parent.mkdir(parents=True, exist_ok=True)
        from conversation_os.storage import write_json

        write_json(global_index_path, global_index)
        result = query_shape_index(
            self.root,
            stencil_id="stencil-context-warps-topology",
            scope="global",
        )
        self.assertTrue(result["validation_ok"])
        self.assertIn("orthogonal_candidates", result)

    def test_validate_shape_index_flags_missing_stencil_refs(self) -> None:
        report = validate_shape_index(
            {
                "version": "1.2.0",
                "scope": "global",
                "stencils": {},
                "fingerprints": {"abc": "missing-stencil"},
                "instances": [],
            }
        )
        self.assertTrue(report.ok)
        self.assertTrue(any("missing stencil" in warning for warning in report.warnings))


if __name__ == "__main__":
    unittest.main()
