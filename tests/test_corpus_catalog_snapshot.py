from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from conversation_os.corpus_catalog_snapshot import (
    INDEX_CONTRACTS_VERSION,
    INDEX_PORT_IDS,
    LEGACY_DETERMINISTIC_SIGNATURE_TARGET,
    OCEAN_READINESS_CONTRACT_VERSION,
    SNAPSHOT_SCHEMA_VERSION,
    TEMPORAL_REVISION_CONTRACT_VERSION,
    compute_generation_marker,
    corpus_catalog_snapshot_path,
    enrich_catalog_ocean_readiness,
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

    def test_publish_attaches_ocean_readiness_contract(self) -> None:
        self._write_ready_fixture()
        published = publish_corpus_catalog_snapshot(self.root)
        self.assertEqual(published["schema_version"], SNAPSHOT_SCHEMA_VERSION)
        ocean = published["catalog"]["ocean_readiness"]
        self.assertEqual(ocean["contract_version"], OCEAN_READINESS_CONTRACT_VERSION)
        self.assertTrue(ocean["complete"])
        self.assertTrue(ocean["family_inventory"]["inventory_digest"])
        self.assertIn("sources", ocean["family_inventory"]["families"])
        self.assertFalse(ocean["ambiguous_placement"]["review_required"])
        self.assertEqual(ocean["ambiguous_placement"]["policy"], "do_not_invent_branch_or_scope")
        self.assertTrue(ocean["legacy_signatures"]["candidate_only"])
        self.assertTrue(ocean["legacy_signatures"]["promotion_forbidden"])
        self.assertEqual(
            ocean["legacy_signatures"]["target_inventory_count"],
            LEGACY_DETERMINISTIC_SIGNATURE_TARGET,
        )
        self.assertTrue(ocean["dependency_indexes"]["indexed"])
        self.assertTrue(ocean["dependency_indexes"]["withdrawal"]["edges"])
        self.assertEqual(ocean["seed_pilot"]["pilot_id"], "chat_converter_seed_v1")
        self.assertTrue(ocean["rebuild"]["reproducible"])
        self.assertTrue(ocean["rebuild"]["content_digest"])

        served = load_corpus_catalog_for_request(self.root)
        self.assertTrue(served["ocean_readiness"]["complete"])
        self.assertEqual(served["readiness_state"], "ready")

    def test_ambiguous_branch_scope_fails_closed_without_inventing(self) -> None:
        ingest_text_content(
            self.root,
            title="ambiguous-placement",
            content="# User\n\nMissing branch and scope on purpose.\n",
            source_ref="fixture:ambiguous",
            source_type="chat_converter_conversation",
        )
        data_dir = product_runtime_dir(self.root, "inner_world_v1", "data")
        write_jsonl(
            data_dir / "knowledge_nodes.jsonl",
            [{"node_id": "kn-ambiguous", "label": "fixture", "source_refs": ["fixture:ambiguous"]}],
        )
        published = publish_corpus_catalog_snapshot(self.root)
        catalog = published["catalog"]
        self.assertEqual(catalog["readiness_state"], "stale")
        self.assertEqual(catalog["abstention_reason"], "corpus_ocean_ambiguous_placement")
        self.assertFalse(catalog["retrieval_allowed"])
        ambiguous = catalog["ocean_readiness"]["ambiguous_placement"]
        self.assertTrue(ambiguous["review_required"])
        self.assertIn("ambiguous_source_branch", ambiguous["reasons"])
        self.assertIn("ambiguous_source_scope", ambiguous["reasons"])
        self.assertEqual(ambiguous["routing"], "review_queue")
        # Enrichment must not invent branch/scope onto the catalog coverage.
        self.assertLess(catalog["coverage"]["branch_coverage"], 1.0)
        self.assertLess(catalog["coverage"]["scope_coverage"], 1.0)

    def test_request_path_abstains_when_ocean_readiness_incomplete(self) -> None:
        self._write_ready_fixture()
        publish_corpus_catalog_snapshot(self.root)
        path = corpus_catalog_snapshot_path(self.root)
        payload = read_json(path, default={}) or {}
        catalog = dict(payload.get("catalog") or {})
        catalog.pop("ocean_readiness", None)
        payload["catalog"] = catalog
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        invalidate_corpus_catalog_cache(self.root)

        served = load_corpus_catalog_for_request(self.root)
        self.assertEqual(served["abstention_reason"], "corpus_ocean_not_ready")
        self.assertFalse(served["retrieval_allowed"])
        self.assertFalse(served["ocean_readiness"]["complete"])

    def test_enrich_helper_is_idempotent_for_ready_catalog(self) -> None:
        self._write_ready_fixture()
        base = build_corpus_catalog(self.root)
        first = enrich_catalog_ocean_readiness(self.root, base)
        second = enrich_catalog_ocean_readiness(self.root, first)
        self.assertEqual(
            first["ocean_readiness"]["rebuild"]["content_digest"],
            second["ocean_readiness"]["rebuild"]["content_digest"],
        )
        self.assertEqual(first["readiness_state"], "ready")

    def test_publish_attaches_index_contracts(self) -> None:
        self._write_ready_fixture()
        published = publish_corpus_catalog_snapshot(self.root)
        indexes = published["catalog"]["ocean_readiness"]["index_contracts"]
        self.assertEqual(indexes["contract_version"], INDEX_CONTRACTS_VERSION)
        self.assertTrue(indexes["complete"])
        self.assertTrue(indexes["policy"]["no_full_ocean_scan"])
        self.assertTrue(indexes["policy"]["stale_or_corrupt_abstain"])
        self.assertTrue(indexes["policy"]["similarity_alone_cannot_merge_or_promote"])
        for port_id in INDEX_PORT_IDS:
            self.assertIn(port_id, indexes["ports"])
            port = indexes["ports"][port_id]
            self.assertTrue(port["replaceable"])
            self.assertFalse(port["widens_retrieval_when_stale"])
            self.assertTrue(port["incremental_ops"]["tombstone"])
            self.assertIn("authorization", port["filters_before_evidence"])
            self.assertFalse(port["source_bytes"]["copied_into_index"])
            self.assertFalse(port["latency"]["published"])
        self.assertEqual(indexes["ports"]["exact"]["status"], "ready")
        self.assertEqual(indexes["ports"]["lexical"]["status"], "ready")
        self.assertEqual(indexes["required_not_ready"], [])
        self.assertEqual(published["catalog"]["readiness_state"], "ready")

    def test_request_path_abstains_when_index_contracts_incomplete(self) -> None:
        self._write_ready_fixture()
        publish_corpus_catalog_snapshot(self.root)
        path = corpus_catalog_snapshot_path(self.root)
        payload = read_json(path, default={}) or {}
        catalog = dict(payload.get("catalog") or {})
        ocean = dict(catalog.get("ocean_readiness") or {})
        ocean.pop("index_contracts", None)
        catalog["ocean_readiness"] = ocean
        payload["catalog"] = catalog
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        invalidate_corpus_catalog_cache(self.root)

        served = load_corpus_catalog_for_request(self.root)
        self.assertEqual(served["abstention_reason"], "corpus_ocean_not_ready")
        self.assertFalse(served["retrieval_allowed"])

    def test_publish_attaches_temporal_revision_contract(self) -> None:
        self._write_ready_fixture()
        first = publish_corpus_catalog_snapshot(self.root)
        temporal = first["catalog"]["ocean_readiness"]["temporal_revision"]
        self.assertEqual(temporal["contract_version"], TEMPORAL_REVISION_CONTRACT_VERSION)
        self.assertTrue(temporal["complete"])
        self.assertTrue(temporal["revision_identity"]["revision_id"])
        self.assertTrue(temporal["revision_identity"]["no_silent_time_defaults"])
        self.assertEqual(temporal["revision_identity"]["kind"], "content_addressed")
        self.assertTrue(temporal["corpus_epoch"]["epoch_id"])
        self.assertIn("source_withdrawal", temporal["corpus_epoch"]["advances_on"])
        self.assertIn("snapshot_rebuild", temporal["corpus_epoch"]["advances_on"])
        self.assertTrue(temporal["stale_projection_rules"])
        self.assertEqual(
            temporal["contradictions"]["resolution_policy"],
            "surface_explicitly_do_not_auto_reconcile",
        )
        epoch_before = temporal["corpus_epoch"]["epoch_id"]

        data_dir = product_runtime_dir(self.root, "inner_world_v1", "data")
        sources = read_jsonl(data_dir / "source_registry.jsonl")
        sources.append(dict(sources[0], source_id="source-epoch-advance", source_ref="fixture:epoch"))
        write_jsonl(data_dir / "source_registry.jsonl", sources)
        invalidate_corpus_catalog_cache(self.root)
        second = publish_corpus_catalog_snapshot(self.root)
        epoch_after = second["catalog"]["ocean_readiness"]["temporal_revision"]["corpus_epoch"]["epoch_id"]
        self.assertNotEqual(epoch_before, epoch_after)

    def test_request_path_abstains_when_temporal_revision_incomplete(self) -> None:
        self._write_ready_fixture()
        publish_corpus_catalog_snapshot(self.root)
        path = corpus_catalog_snapshot_path(self.root)
        payload = read_json(path, default={}) or {}
        catalog = dict(payload.get("catalog") or {})
        ocean = dict(catalog.get("ocean_readiness") or {})
        ocean.pop("temporal_revision", None)
        catalog["ocean_readiness"] = ocean
        payload["catalog"] = catalog
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        invalidate_corpus_catalog_cache(self.root)

        served = load_corpus_catalog_for_request(self.root)
        self.assertEqual(served["abstention_reason"], "corpus_ocean_not_ready")
        self.assertFalse(served["retrieval_allowed"])
