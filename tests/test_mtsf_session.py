import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from conversation_os.cli import init_repo, session_append, session_close, session_start
from conversation_os.mtsf_session import (
    infer_session_signals,
    load_entity_catalog,
    materialize_session_mtsf,
)
from conversation_os.storage import read_json, session_dir

REPO_ROOT = Path(__file__).resolve().parents[1]


class MtsfSessionTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        for filename in ("AGENTS.md", "SESSION_PROTOCOL.md", "README.md"):
            if (REPO_ROOT / filename).exists():
                shutil.copy(REPO_ROOT / filename, self.root / filename)
        os.symlink(REPO_ROOT / "docs", self.root / "docs", target_is_directory=True)
        os.symlink(REPO_ROOT / "src", self.root / "src", target_is_directory=True)
        os.symlink(REPO_ROOT / "tools", self.root / "tools", target_is_directory=True)
        init_repo(self.root)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_entity_catalog_loads_activatable_entities(self) -> None:
        entities = load_entity_catalog(self.root)
        entity_ids = {entity.id for entity in entities}
        self.assertIn("entity-context-field", entity_ids)
        self.assertIn("entity-symmetry-engine", entity_ids)
        self.assertGreaterEqual(len(entities), 4)

    def test_infer_triangulation_signals(self) -> None:
        events = [
            {
                "actor": "user",
                "content": (
                    "Explain how the same query would be processed by an agent without any prior "
                    "context, with relevant prior context, and with unrelated prior context."
                ),
            }
        ]
        signals = infer_session_signals(events, domains=["research"])
        self.assertTrue(signals.context_absent or signals.context_domain_orthogonal >= 0.6)

    def test_infer_formalizing_and_symmetry_signals(self) -> None:
        events = [
            {
                "actor": "user",
                "content": (
                    "Formalize the structural skeleton schema and find a symmetric isomorph blueprint."
                ),
            },
            {
                "actor": "user",
                "content": "Now test inversion and antisymmetric guardrails via negativa.",
            },
        ]
        signals = infer_session_signals(events)
        self.assertEqual(signals.meta_shape_id, "meta-shape-formalizing")
        self.assertIn(signals.meta_move_id, {"move-symmetry-extension", "move-inversion"})

    def test_session_close_writes_mtsf_artifacts(self) -> None:
        session_start(
            self.root,
            type(
                "Args",
                (),
                {
                    "session_id": "mtsf-session-test",
                    "title": "Topology activation test",
                    "participants": "user,assistant",
                    "source_type": "live_session",
                    "domains": "research,topology",
                },
            )(),
        )
        session_append(
            self.root,
            type(
                "Args",
                (),
                {
                    "session_id": "mtsf-session-test",
                    "actor": "user",
                    "kind": "request",
                    "content": (
                        "With relevant prior context on latent topology and symmetry, formalize "
                        "the structural skeleton and seek a symmetric isomorph blueprint."
                    ),
                    "attachments": "",
                    "tags": "meta-shape-formalizing",
                    "source_ref": None,
                },
            )(),
        )
        session_append(
            self.root,
            type(
                "Args",
                (),
                {
                    "session_id": "mtsf-session-test",
                    "actor": "assistant",
                    "kind": "response",
                    "content": "The structural skeleton layer becomes stencil-ready.",
                    "attachments": "",
                    "tags": "",
                    "source_ref": None,
                },
            )(),
        )

        result = session_close(
            self.root,
            type(
                "Args",
                (),
                {
                    "session_id": "mtsf-session-test",
                    "task_id": None,
                    "request": None,
                    "task_type": None,
                },
            )(),
        )

        snapshot_path = self.root / "memory" / "sessions" / "mtsf-session-test" / "mtsf" / "activation_snapshot.json"
        graph_path = self.root / "memory" / "sessions" / "mtsf-session-test" / "mtsf" / "graph.json"
        self.assertTrue(snapshot_path.exists())
        self.assertTrue(graph_path.exists())
        self.assertIn("mtsf_activation_snapshot", result["artifact_refs"])
        self.assertIn("mtsf_graph", result["artifact_refs"])

        snapshot = read_json(snapshot_path)
        graph = read_json(graph_path)
        self.assertEqual(snapshot["session_id"], "mtsf-session-test")
        self.assertEqual(graph["session_id"], "mtsf-session-test")
        self.assertGreaterEqual(len(snapshot["shape_activation_results"]), 4)
        self.assertGreaterEqual(len(graph["entities"]), 4)
        seed_ids = {"entity-context-field", "entity-thought-ocean", "entity-symmetry-engine", "entity-hardened-idea"}
        self.assertTrue(seed_ids.issubset({row["entity_id"] for row in snapshot["shape_activation_results"]}))

        context_result = next(
            row for row in snapshot["shape_activation_results"] if row["entity_id"] == "entity-context-field"
        )
        ocean_result = next(
            row for row in snapshot["shape_activation_results"] if row["entity_id"] == "entity-thought-ocean"
        )
        self.assertIsNotNone(context_result["dominant_shape_id"])
        self.assertIn(
            ocean_result["dominant_shape_id"],
            {"shape-structural-skeleton", "shape-raw-manifold", "shape-knowledge-reef"},
        )

        manifest = read_json(session_dir(self.root, "mtsf-session-test") / "manifest.json")
        self.assertIn("mtsf_activation_snapshot", manifest["artifact_refs"])

    def test_materialize_session_mtsf_is_idempotent_on_rerun(self) -> None:
        session_start(
            self.root,
            type(
                "Args",
                (),
                {
                    "session_id": "mtsf-rerun-test",
                    "title": "Rerun test",
                    "participants": "user",
                    "source_type": "live_session",
                    "domains": "",
                },
            )(),
        )
        session_append(
            self.root,
            type(
                "Args",
                (),
                {
                    "session_id": "mtsf-rerun-test",
                    "actor": "user",
                    "kind": "request",
                    "content": "Cold start with no prior context on latent space.",
                    "attachments": "",
                    "tags": "",
                    "source_ref": None,
                },
            )(),
        )
        refs_first = materialize_session_mtsf(self.root, "mtsf-rerun-test")
        refs_second = materialize_session_mtsf(self.root, "mtsf-rerun-test")
        self.assertEqual(refs_first.keys(), refs_second.keys())
        first_snapshot = json.loads(Path(refs_first["mtsf_activation_snapshot"]).read_text(encoding="utf-8"))
        second_snapshot = json.loads(Path(refs_second["mtsf_activation_snapshot"]).read_text(encoding="utf-8"))
        self.assertEqual(
            first_snapshot["shape_activation_results"],
            second_snapshot["shape_activation_results"],
        )

    def test_materialize_session_mtsf_includes_discovered_entities_from_draft(self) -> None:
        session_id = "mtsf-discovered-entity-test"
        session_start(
            self.root,
            type(
                "Args",
                (),
                {
                    "session_id": session_id,
                    "title": "Discovered entity test",
                    "participants": "user",
                    "source_type": "imported_transcript",
                    "domains": "research,brainwalk",
                },
            )(),
        )
        from conversation_os.cli import session_append
        from conversation_os.mtsf_ingest import materialize_session_mtsf_ingest

        session_append(
            self.root,
            type(
                "Args",
                (),
                {
                    "session_id": session_id,
                    "actor": "assistant",
                    "kind": "response",
                    "content": (
                        "Closest to Backrooms / liminal-space horror. Architecture behaves like a subconscious maze. "
                        "This stack is for Thought Tube."
                    ),
                    "attachments": "",
                    "tags": "brainwalk",
                    "source_ref": None,
                },
            )(),
        )
        materialize_session_mtsf_ingest(self.root, session_id, "deep", llm_preference="auto")
        refs = materialize_session_mtsf(self.root, session_id)
        snapshot = read_json(Path(refs["mtsf_activation_snapshot"]))
        entity_ids = {row["entity_id"] for row in snapshot["shape_activation_results"]}
        self.assertIn("entity-liminal-space", entity_ids)
        self.assertIn("entity-thought-tube", entity_ids)
        liminal = next(row for row in snapshot["shape_activation_results"] if row["entity_id"] == "entity-liminal-space")
        self.assertEqual(liminal["dominant_shape_id"], "shape-liminal-trap")
        self.assertGreaterEqual(liminal["confidence"], 0.4)
        cohesion_path = session_dir(self.root, session_id) / "mtsf" / "shape_cluster_cohesion.json"
        self.assertTrue(cohesion_path.exists())
        cohesion = read_json(cohesion_path, default={})
        self.assertGreaterEqual(float(cohesion.get("score", 0.0)), 0.7)


if __name__ == "__main__":
    unittest.main()
