import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from conversation_os.cli import init_repo, session_append, session_close, session_start
from conversation_os.mtsf_extraction import materialize_extraction_draft
from conversation_os.mtsf_graph import (
    build_assertion_store_from_draft,
    expand_node,
    follow_traversal,
    load_assertion_store,
    load_content_graph,
    materialize_session_graph,
    project_content_graph,
)
from conversation_os.storage import append_jsonl, read_json, session_events_path

REPO_ROOT = Path(__file__).resolve().parents[1]

SAMPLE_EVENTS = [
    {
        "event_id": "ev-user-1",
        "actor": "user",
        "kind": "request",
        "content": (
            "Agents move through a latent manifold. Context warps effective topology "
            "and steers the inference path across hidden states."
        ),
    },
    {
        "event_id": "ev-assistant-1",
        "actor": "assistant",
        "kind": "response",
        "content": (
            "The symmetry engine finds structural isomorphs while the synthetic subconscious "
            "performs spreading activation across the thought ocean."
        ),
    },
]

SAMPLE_DRAFT = {
    "draft_id": "mtsf-draft-graph-test",
    "input_id": "session:graph-test",
    "input_type": "import",
    "capture_mode": "deep",
    "session_id": "graph-test",
    "subgraph_id": "research",
    "scope": "session",
    "raw_content": "\n".join(event["content"] for event in SAMPLE_EVENTS),
    "context": {"project": "graph test", "domain": "research", "tags": []},
    "ontology_refs": {},
    "provenance": {
        "skill_id": "semantic-shape-extraction",
        "skill_version": "1.0.0",
        "model_id": "test",
        "stages_completed": ["entities", "relations", "qualities"],
    },
    "entities": [
        {
            "proposed_id": "entity-latent-manifold",
            "name": "latent manifold",
            "type": "composite",
            "stable_identity": ["fixed semantic geometry"],
            "confidence": 0.9,
            "evidence": {"spans": ["Agents move through a latent manifold"]},
        },
        {
            "proposed_id": "entity-context-field",
            "name": "context field",
            "type": "composite",
            "stable_identity": ["prior runs as coordinate shift"],
            "confidence": 0.88,
            "evidence": {"spans": ["Context warps effective topology"]},
        },
        {
            "proposed_id": "entity-thought-ocean",
            "name": "thought ocean",
            "type": "composite",
            "stable_identity": ["personal note library"],
            "confidence": 0.86,
            "evidence": {"spans": ["spreading activation across the thought ocean"]},
        },
    ],
    "qualities": [],
    "quality_roles": [],
    "relations": [
        {
            "source_ref": "entity-context-field",
            "target_ref": "entity-latent-manifold",
            "level": "entity_entity",
            "relation_type": "warps",
            "primitive": "modulates",
            "domain_expression": "context warps topology",
            "confidence": 0.85,
            "evidence": {"spans": ["Context warps effective topology"]},
        }
    ],
    "candidate_shapes": [],
    "stencil_drafts": [],
    "confidence": 0.85,
    "status": "proposed",
}


class MtsfGraphTestCase(unittest.TestCase):
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

        session_id = "graph-test"
        session_dir = self.root / "memory" / "sessions" / session_id
        session_dir.mkdir(parents=True)
        (session_dir / "manifest.json").write_text(
            json.dumps(
                {
                    "session_id": session_id,
                    "title": "Graph test",
                    "started_at": "2026-07-06T15:00:00+00:00",
                    "ended_at": None,
                    "participants": ["user", "assistant"],
                    "source_type": "imported_transcript",
                    "status": "open",
                    "artifact_refs": {},
                    "domains": ["research"],
                }
            ),
            encoding="utf-8",
        )
        for event in SAMPLE_EVENTS:
            append_jsonl(
                session_events_path(self.root, session_id),
                {**event, "session_id": session_id, "timestamp": "2026-07-06T15:00:00+00:00"},
            )

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_assertion_store_anchors_spans_to_events(self) -> None:
        store = build_assertion_store_from_draft(self.root, "graph-test", SAMPLE_DRAFT)
        entity_assertions = [row for row in store["assertions"] if row["kind"] == "entity"]
        self.assertGreaterEqual(len(entity_assertions), 3)
        bundles = store["evidence_bundles"]
        anchored = [
            bundle
            for bundle in bundles.values()
            if bundle.get("anchors") and bundle["anchors"][0].get("event_id") == "ev-user-1"
        ]
        self.assertGreaterEqual(len(anchored), 1)

    def test_content_graph_builds_semantic_adjacency(self) -> None:
        store = build_assertion_store_from_draft(self.root, "graph-test", SAMPLE_DRAFT)
        graph = project_content_graph(store)
        semantic = graph["adjacency"]["semantic"]
        self.assertIn("entity-context-field", semantic["entity-latent-manifold"])
        self.assertIn("entity-latent-manifold", semantic["entity-context-field"])

    def test_materialize_and_expand_progressive_facets(self) -> None:
        result = materialize_session_graph(self.root, "graph-test", SAMPLE_DRAFT)
        self.assertGreaterEqual(result["assertion_count"], 4)
        self.assertTrue(load_assertion_store(self.root, "graph-test"))
        self.assertTrue(load_content_graph(self.root, "graph-test"))

        identity = expand_node(self.root, "graph-test", "entity-latent-manifold", facets=["identity"])
        self.assertEqual(identity["identity"]["name"], "latent manifold")

        evidence = expand_node(
            self.root,
            "graph-test",
            "entity-latent-manifold",
            facets=["evidence", "substrate"],
        )
        self.assertIn("Agents move through a latent manifold", evidence["evidence"]["spans"][0])
        self.assertGreaterEqual(len(evidence["substrate"]["anchors"]), 1)
        self.assertEqual(evidence["substrate"]["anchors"][0]["event_id"], "ev-user-1")

    def test_follow_semantic_traversal(self) -> None:
        materialize_session_graph(self.root, "graph-test", SAMPLE_DRAFT)
        walk = follow_traversal(
            self.root,
            "graph-test",
            start="entity-context-field",
            mode="semantic",
            depth=1,
        )
        visited = set(walk["visited"])
        self.assertIn("entity-context-field", visited)
        self.assertIn("entity-latent-manifold", visited)

    def test_materialize_extraction_writes_graph_artifacts(self) -> None:
        result = materialize_extraction_draft(self.root, "graph-test", SAMPLE_DRAFT)
        self.assertIn("mtsf_assertion_store", result["artifact_refs"])
        self.assertIn("mtsf_content_graph", result["artifact_refs"])
        graph_path = self.root / "memory" / "sessions" / "graph-test" / "mtsf" / "content_graph.json"
        self.assertTrue(graph_path.exists())

    def test_session_close_materializes_graph(self) -> None:
        session_id = "graph-close-test"
        session_start(
            self.root,
            type(
                "Args",
                (),
                {
                    "session_id": session_id,
                    "title": "Graph close",
                    "participants": "user,assistant",
                    "source_type": "imported_transcript",
                    "domains": "research",
                },
            )(),
        )
        session_append(
            self.root,
            type(
                "Args",
                (),
                {
                    "session_id": session_id,
                    "actor": "user",
                    "kind": "request",
                    "content": SAMPLE_EVENTS[0]["content"],
                    "attachments": "",
                    "tags": "",
                    "source_ref": None,
                },
            )(),
        )
        session_close(
            self.root,
            type(
                "Args",
                (),
                {
                    "session_id": session_id,
                    "task_id": None,
                    "request": None,
                    "task_type": None,
                    "mtsf_mode": "fast",
                    "mtsf_llm": "off",
                },
            )(),
        )
        graph_path = self.root / "memory" / "sessions" / session_id / "mtsf" / "content_graph.json"
        self.assertTrue(graph_path.exists())


if __name__ == "__main__":
    unittest.main()
