import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from conversation_os.cli import init_repo, session_append, session_close, session_start
from conversation_os.mtsf_extraction import materialize_extraction_draft
from conversation_os.mtsf_graph import (
    append_graph_event,
    apply_substrate_refs_to_draft,
    build_assertion_store_from_draft,
    default_global_content_graph_path,
    default_graph_events_path,
    expand_node,
    follow_traversal,
    load_assertion_store,
    load_content_graph,
    load_global_content_graph,
    materialize_session_graph,
    merge_session_graph_into_global,
    project_content_graph,
    promote_session_graph_to_global,
    read_graph_events,
    rebuild_global_content_graph,
    refresh_global_alias_adjacency,
    resolve_activation_bindings,
    resolve_global_node_id,
    substrate_ref_fields,
    sync_activation_to_content_graph,
)
from conversation_os.storage import append_jsonl, read_json, session_events_path, write_json

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

    def test_substrate_ref_fields_anchor_events(self) -> None:
        refs = substrate_ref_fields(self.root, "graph-test", SAMPLE_EVENTS)
        self.assertEqual(refs["raw_content_ref"], str(session_events_path(self.root, "graph-test")))
        self.assertGreaterEqual(len(refs["substrate_offsets"]), 2)
        self.assertIn("latent manifold", refs["raw_content_preview"])

    def test_apply_substrate_refs_replaces_inline_raw_content(self) -> None:
        draft = dict(SAMPLE_DRAFT)
        apply_substrate_refs_to_draft(self.root, "graph-test", SAMPLE_EVENTS, draft)
        self.assertEqual(draft["raw_content_ref"], str(session_events_path(self.root, "graph-test")))
        self.assertLessEqual(len(draft["raw_content"]), 500)

    def test_promote_session_graph_writes_global_graph_and_event(self) -> None:
        materialize_session_graph(self.root, "graph-test", SAMPLE_DRAFT)
        result = promote_session_graph_to_global(self.root, "graph-test", mode="force")
        self.assertTrue(result["promoted"])
        global_path = default_global_content_graph_path(self.root)
        self.assertTrue(global_path.exists())
        global_graph = load_global_content_graph(self.root)
        self.assertIn("graph-test::entity-latent-manifold", global_graph["nodes"])
        events = read_graph_events(self.root, kinds=["session_promoted"])
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["session_id"], "graph-test")

    def test_rebuild_global_content_graph_merges_sessions(self) -> None:
        materialize_session_graph(self.root, "graph-test", SAMPLE_DRAFT)
        result = rebuild_global_content_graph(self.root, session_ids=["graph-test"])
        self.assertTrue(result["rebuilt"])
        self.assertEqual(result["merged_session_count"], 1)
        global_graph = load_global_content_graph(self.root)
        self.assertGreaterEqual(len(global_graph["nodes"]), 3)
        events_path = default_graph_events_path(self.root)
        self.assertTrue(events_path.exists())

    def test_merge_session_graph_namespaces_node_ids(self) -> None:
        store = build_assertion_store_from_draft(self.root, "graph-test", SAMPLE_DRAFT)
        session_graph = project_content_graph(store)
        merged = merge_session_graph_into_global(
            load_global_content_graph(self.root),
            session_graph,
            store,
            session_id="graph-test",
            promotion_mode="test",
        )
        self.assertIn("graph-test::entity-context-field", merged["nodes"])
        semantic = merged["adjacency"]["semantic"]
        self.assertIn(
            "graph-test::entity-latent-manifold",
            semantic["graph-test::entity-context-field"],
        )

    def _write_activation_snapshot(self) -> None:
        snapshot_path = self.root / "memory" / "sessions" / "graph-test" / "mtsf" / "activation_snapshot.json"
        write_json(
            snapshot_path,
            {
                "id": "mtsf-snap-test",
                "session_id": "graph-test",
                "subgraph_id": "research",
                "active_stencil_ids": ["stencil-latent-triangulation"],
                "shape_activation_results": [
                    {
                        "entity_id": "entity-context-field",
                        "dominant_shape_id": "shape-anchored-start",
                        "secondary_shape_ids": [],
                        "confidence": 0.72,
                        "matched_conditions": ["cond-anchored-start"],
                    },
                    {
                        "entity_id": "entity-thought-ocean",
                        "dominant_shape_id": "shape-raw-manifold",
                        "secondary_shape_ids": [],
                        "confidence": 0.68,
                        "matched_conditions": [],
                    },
                ],
            },
        )

    def test_resolve_activation_bindings_matches_catalog_to_content_nodes(self) -> None:
        materialize_session_graph(self.root, "graph-test", SAMPLE_DRAFT)
        self._write_activation_snapshot()
        resolution = resolve_activation_bindings(self.root, "graph-test")
        bindings = resolution["bindings"]
        self.assertEqual(bindings["entity-context-field"]["content_node_id"], "entity-context-field")
        self.assertEqual(bindings["entity-context-field"]["match_method"], "exact_id")
        self.assertEqual(bindings["entity-thought-ocean"]["content_node_id"], "entity-thought-ocean")
        self.assertEqual(bindings["entity-thought-ocean"]["match_method"], "exact_id")

    def test_sync_activation_writes_overlay_and_activation_adjacency(self) -> None:
        materialize_session_graph(self.root, "graph-test", SAMPLE_DRAFT)
        self._write_activation_snapshot()
        result = sync_activation_to_content_graph(self.root, "graph-test")
        self.assertTrue(result["synced"])
        graph = load_content_graph(self.root, "graph-test")
        overlay = graph["overlays"]["activation"]
        self.assertIn("entity-context-field", overlay["bindings"])
        self.assertIn("entity-context-field", overlay["dominant_content_nodes"])
        self.assertIn("entity-thought-ocean", graph["adjacency"]["activation"])
        self.assertIn("entity-thought-ocean", graph["adjacency"]["activation"]["entity-context-field"])

        snapshot = read_json(self.root / "memory" / "sessions" / "graph-test" / "mtsf" / "activation_snapshot.json")
        self.assertEqual(snapshot["content_graph_bindings"]["entity-context-field"], "entity-context-field")

        events = read_graph_events(self.root, kinds=["activation_synced"])
        self.assertEqual(len(events), 1)

    def test_follow_activation_traversal_uses_synced_adjacency(self) -> None:
        materialize_session_graph(self.root, "graph-test", SAMPLE_DRAFT)
        self._write_activation_snapshot()
        sync_activation_to_content_graph(self.root, "graph-test")
        walk = follow_traversal(
            self.root,
            "graph-test",
            start="entity-context-field",
            mode="activation",
            depth=1,
        )
        visited = set(walk["visited"])
        self.assertIn("entity-context-field", visited)
        self.assertIn("entity-thought-ocean", visited)

    def _ensure_session_events(self, session_id: str) -> None:
        session_path = self.root / "memory" / "sessions" / session_id
        session_path.mkdir(parents=True, exist_ok=True)
        if not (session_path / "manifest.json").exists():
            (session_path / "manifest.json").write_text(
                json.dumps(
                    {
                        "session_id": session_id,
                        "title": f"Graph test {session_id}",
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
        events_path = session_events_path(self.root, session_id)
        if not events_path.exists():
            for event in SAMPLE_EVENTS:
                append_jsonl(
                    events_path,
                    {**event, "session_id": session_id, "timestamp": "2026-07-06T15:00:00+00:00"},
                )

    def test_global_alias_links_same_entity_across_sessions(self) -> None:
        draft_b = dict(SAMPLE_DRAFT)
        draft_b["session_id"] = "graph-test-b"
        draft_b["draft_id"] = "mtsf-draft-graph-test-b"
        self._ensure_session_events("graph-test-b")
        materialize_session_graph(self.root, "graph-test", SAMPLE_DRAFT)
        materialize_session_graph(self.root, "graph-test-b", draft_b)
        rebuild_global_content_graph(self.root, session_ids=["graph-test", "graph-test-b"])

        node_a = resolve_global_node_id("graph-test", "entity-context-field")
        node_b = resolve_global_node_id("graph-test-b", "entity-context-field")
        global_graph = load_global_content_graph(self.root)
        self.assertIn(node_b, global_graph["adjacency"]["alias"][node_a])

    def test_global_follow_alias_crosses_sessions(self) -> None:
        draft_b = dict(SAMPLE_DRAFT)
        draft_b["session_id"] = "graph-test-b"
        draft_b["draft_id"] = "mtsf-draft-graph-test-b"
        self._ensure_session_events("graph-test-b")
        materialize_session_graph(self.root, "graph-test", SAMPLE_DRAFT)
        materialize_session_graph(self.root, "graph-test-b", draft_b)
        rebuild_global_content_graph(self.root, session_ids=["graph-test", "graph-test-b"])

        node_a = resolve_global_node_id("graph-test", "entity-context-field")
        walk = follow_traversal(
            self.root,
            start=node_a,
            mode="alias",
            depth=1,
            scope="global",
        )
        node_b = resolve_global_node_id("graph-test-b", "entity-context-field")
        self.assertEqual(walk["scope"], "global")
        self.assertIn(node_b, walk["visited"])

    def test_global_expand_hydrates_from_source_session(self) -> None:
        materialize_session_graph(self.root, "graph-test", SAMPLE_DRAFT)
        rebuild_global_content_graph(self.root, session_ids=["graph-test"])
        global_id = resolve_global_node_id("graph-test", "entity-latent-manifold")
        expanded = expand_node(
            self.root,
            node_id=global_id,
            facets=["identity", "evidence"],
            scope="global",
        )
        self.assertEqual(expanded["scope"], "global")
        self.assertEqual(expanded["global_node_id"], global_id)
        self.assertEqual(expanded["source_session_id"], "graph-test")
        self.assertEqual(expanded["identity"]["name"], "latent manifold")
        self.assertIn("Agents move through a latent manifold", expanded["evidence"]["spans"][0])


if __name__ == "__main__":
    unittest.main()
