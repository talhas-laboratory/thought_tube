import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from conversation_os.cli import init_repo
from conversation_os.mtsf_discovery import cross_session_shapes_path, materialize_cross_session_shapes
from conversation_os.mtsf_gap_eval import _ingest_session
from conversation_os.mtsf_graph import rebuild_global_content_graph, resolve_traversal_intent
from conversation_os.storage import read_json

REPO_ROOT = Path(__file__).resolve().parents[1]


class MtsfDiscoveryTestCase(unittest.TestCase):
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

    def test_cross_session_shapes_written_on_rebuild(self) -> None:
        sessions = [
            (
                "discover-a",
                "Wrong-familiar corridor with fluorescent hum and no exit.",
            ),
            (
                "discover-b",
                "Synthetic suburb loops forever; the architecture feels liminal and trapped.",
            ),
        ]
        for session_id, content in sessions:
            _ingest_session(
                self.root,
                session_id=session_id,
                events=[{"actor": "user", "content": content}],
                mtsf_mode="deep",
                llm_preference="auto",
            )
        rebuild_global_content_graph(self.root, session_ids=[sid for sid, _ in sessions])
        artifact_path = cross_session_shapes_path(self.root)
        self.assertTrue(artifact_path.exists())
        payload = read_json(artifact_path, default={})
        self.assertGreaterEqual(len(payload.get("cross_session_refs", [])), 1)

    def test_materialize_cross_session_shapes_finds_liminal_fragment(self) -> None:
        for session_id, content in [
            ("frag-a", "Wrong-familiar corridor with fluorescent hum and no exit."),
            ("frag-b", "Synthetic suburb loops forever; the architecture feels liminal and trapped."),
        ]:
            _ingest_session(
                self.root,
                session_id=session_id,
                events=[{"actor": "user", "content": content}],
                mtsf_mode="deep",
                llm_preference="auto",
            )
        materialize_cross_session_shapes(self.root, session_ids=["frag-a", "frag-b"])
        payload = read_json(cross_session_shapes_path(self.root), default={})
        fragments = {
            str(ref.get("shared_fragment", "")).lower()
            for ref in payload.get("cross_session_refs", [])
        }
        self.assertIn("liminal", fragments)


class MtsfTraversalIntentTestCase(unittest.TestCase):
    def test_resolve_traversal_intent_prefers_alias_mode(self) -> None:
        plan = resolve_traversal_intent(
            "follow:alias",
            graph={"nodes": {"entity-a": {"name": "context field", "kind": "entity"}}},
            start_id="entity-a",
        )
        self.assertEqual(plan["mode"], "alias")
        self.assertEqual(plan["neighbor_filter"], "alias")


if __name__ == "__main__":
    unittest.main()
