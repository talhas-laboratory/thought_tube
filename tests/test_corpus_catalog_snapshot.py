from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from conversation_os.corpus_catalog_snapshot import (
    compute_generation_marker,
    corpus_catalog_snapshot_path,
    invalidate_corpus_catalog_cache,
    load_corpus_catalog_for_request,
    publish_corpus_catalog_snapshot,
)
from conversation_os.disclosure_ports import build_inner_world_ports
from conversation_os.library_tracker import build_corpus_catalog
from conversation_os.runtime_layout import product_runtime_dir
from conversation_os.storage import read_json, read_jsonl, write_json, write_jsonl
from conversation_os.vault_ingest import ingest_text_content


class CorpusCatalogSnapshotTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        (self.root / "product" / "inner_world_v1" / "data").mkdir(parents=True)
        invalidate_corpus_catalog_cache()

    def tearDown(self) -> None:
        invalidate_corpus_catalog_cache()
        self.tempdir.cleanup()

    def _write_ready_fixture(self) -> None:
        ingest_text_content(
            self.root,
            title="snapshot-ready-fixture",
            content="# User\n\nSynthetic snapshot readiness fixture.\n",
            source_ref="fixture:snapshot-ready",
            source_type="chat_converter_conversation",
            metadata={"branch_id": "branch-snapshot", "scope_id": "scope-snapshot"},
        )
        data_dir = product_runtime_dir(self.root, "inner_world_v1", "data")
        sources = read_jsonl(data_dir / "source_registry.jsonl")
        chunks = read_jsonl(data_dir / "chunk_index.jsonl")
        for row in sources:
            row["branch_id"] = "branch-snapshot"
            row["scope_id"] = "scope-snapshot"
        for row in chunks:
            row["branch_id"] = "branch-snapshot"
            row["scope_id"] = "scope-snapshot"
        write_jsonl(data_dir / "source_registry.jsonl", sources)
        write_jsonl(data_dir / "chunk_index.jsonl", chunks)
        write_jsonl(
            data_dir / "knowledge_nodes.jsonl",
            [{"node_id": "kn-snapshot", "label": "fixture", "source_refs": ["fixture:snapshot-ready"]}],
        )

    def test_publish_and_request_path_serves_snapshot(self) -> None:
        self._write_ready_fixture()
        published = publish_corpus_catalog_snapshot(self.root)
        self.assertTrue(corpus_catalog_snapshot_path(self.root).is_file())
        self.assertEqual(published["catalog"]["readiness_state"], "ready")

        served = load_corpus_catalog_for_request(self.root)
        self.assertTrue(served["snapshot"]["served_from_snapshot"])
        self.assertEqual(served["readiness_state"], "ready")
        self.assertEqual(served["corpus_revision"], published["catalog"]["corpus_revision"])

    def test_request_path_abstains_when_snapshot_missing(self) -> None:
        catalog = load_corpus_catalog_for_request(self.root)
        self.assertEqual(catalog["readiness_state"], "stale")
        self.assertEqual(catalog["abstention_reason"], "corpus_catalog_snapshot_missing")
        self.assertFalse(catalog["retrieval_allowed"])

    def test_request_path_abstains_when_snapshot_stale(self) -> None:
        self._write_ready_fixture()
        publish_corpus_catalog_snapshot(self.root)
        data_dir = product_runtime_dir(self.root, "inner_world_v1", "data")
        sources = read_jsonl(data_dir / "source_registry.jsonl")
        sources.append(dict(sources[0], source_id="source-stale-mutation", source_ref="fixture:stale"))
        write_jsonl(data_dir / "source_registry.jsonl", sources)
        invalidate_corpus_catalog_cache(self.root)

        catalog = load_corpus_catalog_for_request(self.root)
        self.assertEqual(catalog["abstention_reason"], "corpus_catalog_snapshot_stale")
        self.assertFalse(catalog["retrieval_allowed"])

    def test_request_path_uses_in_process_cache(self) -> None:
        self._write_ready_fixture()
        publish_corpus_catalog_snapshot(self.root)
        load_corpus_catalog_for_request(self.root)

        with mock.patch(
            "conversation_os.corpus_catalog_snapshot.read_json",
            side_effect=AssertionError("snapshot file should not be re-read while cache is warm"),
        ):
            cached = load_corpus_catalog_for_request(self.root)
        self.assertTrue(cached["snapshot"]["served_from_snapshot"])

    def test_request_path_avoids_corpus_loader_calls(self) -> None:
        self._write_ready_fixture()
        publish_corpus_catalog_snapshot(self.root)

        with (
            mock.patch("conversation_os.vault_ingest.load_source_registry_raw") as source_mock,
            mock.patch("conversation_os.vault_ingest.load_chunk_index_raw") as chunk_mock,
        ):
            catalog = load_corpus_catalog_for_request(self.root)

        source_mock.assert_not_called()
        chunk_mock.assert_not_called()
        self.assertEqual(catalog["readiness_state"], "ready")

    def test_ports_catalog_uses_snapshot_request_path(self) -> None:
        self._write_ready_fixture()
        publish_corpus_catalog_snapshot(self.root)
        ports = build_inner_world_ports()

        with mock.patch("conversation_os.library_tracker.build_corpus_catalog") as build_mock:
            catalog = ports.catalog.build_corpus_catalog(self.root)
        build_mock.assert_not_called()
        self.assertEqual(catalog["readiness_state"], "ready")
        self.assertTrue(catalog["snapshot"]["served_from_snapshot"])

    def test_atomic_publish_preserves_last_valid_snapshot_on_failure(self) -> None:
        self._write_ready_fixture()
        publish_corpus_catalog_snapshot(self.root)
        before = read_json(corpus_catalog_snapshot_path(self.root), default={}) or {}

        with mock.patch(
            "conversation_os.library_tracker.build_corpus_catalog",
            side_effect=RuntimeError("simulated publish failure"),
        ):
            with self.assertRaises(RuntimeError):
                publish_corpus_catalog_snapshot(self.root)

        after = read_json(corpus_catalog_snapshot_path(self.root), default={}) or {}
        self.assertEqual(after.get("generation_marker"), before.get("generation_marker"))
        self.assertEqual(after.get("catalog", {}).get("readiness_state"), "ready")

    def test_generation_marker_changes_when_index_files_change(self) -> None:
        marker_before = compute_generation_marker(self.root)
        self._write_ready_fixture()
        marker_after = compute_generation_marker(self.root)
        self.assertNotEqual(marker_before, marker_after)

    def test_pipeline_completion_publishes_snapshot(self) -> None:
        from conversation_os.runtime_pipeline import execute_runtime_pipeline

        self._write_ready_fixture()
        registry = {
            "bootstrap_legacy_sources": {
                "label": "Bootstrap",
                "requires": [],
                "run": lambda: {"status": "completed"},
            }
        }
        execute_runtime_pipeline(
            self.root,
            registry,
            config={
                "version": 1,
                "selection_mode": "dependency_weighted",
                "components": [
                    {
                        "component_id": "bootstrap_legacy_sources",
                        "label": "Bootstrap",
                        "enabled": True,
                        "order": 10,
                        "weight": 1.0,
                    }
                ],
            },
        )
        snapshot = read_json(corpus_catalog_snapshot_path(self.root), default=None)
        self.assertIsInstance(snapshot, dict)
        self.assertEqual(snapshot.get("catalog", {}).get("readiness_state"), "ready")

    def test_direct_builder_still_available_for_pipeline_publish(self) -> None:
        self._write_ready_fixture()
        direct = build_corpus_catalog(self.root)
        published = publish_corpus_catalog_snapshot(self.root)
        self.assertEqual(direct["readiness_state"], published["catalog"]["readiness_state"])
