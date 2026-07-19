from __future__ import annotations

import ast
import json
import tempfile
import unittest
from pathlib import Path

from conversation_os.feed_disclosure_adapter import (
    build_feed_effective_grant,
    collect_feed_evidence_pairs,
    feed_disclosure_service_enabled,
    feed_evidence_decision_subset,
    load_feed_disclosure_config,
    map_retrieval_bundle_to_feed_pairs,
    record_feed_disclosure_receipt,
)
from conversation_os.knowledge_layer import build_retrieval_bundle
from conversation_os.product_inner_world import _select_contextual_candidate_pairs
from conversation_os.storage import append_jsonl


class FeedDisclosureParityTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        config_dir = self.root / "product" / "inner_world_v1" / "config"
        config_dir.mkdir(parents=True)
        (config_dir / "runtime.json").write_text(
            json.dumps(
                {
                    "feed": {"disclosure_service_v1": True},
                    "knowledge": {
                        "fail_empty_admission_shadow_v1": True,
                        "fail_empty_admission_enforce_v1": True,
                    },
                }
            ),
            encoding="utf-8",
        )
        runtime = self.root / "product" / "inner_world_v1" / "data" / "reasoning_runtime"
        runtime.mkdir(parents=True)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _write_capsules(self) -> None:
        path = self.root / "product" / "inner_world_v1" / "data" / "semantic_capsules.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        rows = [
            {
                "capsule_id": "capsule-feed-left",
                "capsule_type": "concept",
                "label": "Research insight",
                "summary": "Research insight about progressive disclosure and bounded feed evidence.",
                "confidence": 0.9,
                "ref_type": "concept",
                "ref_id": "concept-feed-left",
                "source_refs": ["fixture:research-insight.md"],
            },
            {
                "capsule_id": "capsule-feed-right",
                "capsule_type": "concept",
                "label": "Product design tension",
                "summary": "Product design tension between surprise and bounded evidence selection.",
                "confidence": 0.88,
                "ref_type": "concept",
                "ref_id": "concept-feed-right",
                "source_refs": ["fixture:product-design.md"],
            },
        ]
        for row in rows:
            append_jsonl(path, row)

    def test_feed_pairs_match_bridge_retrieval_subset(self) -> None:
        self._write_capsules()
        pairs, retrieval_bundle, layers = collect_feed_evidence_pairs(
            self.root,
            limit=4,
            domain_overlays=["research"],
        )
        bridge_bundle = build_retrieval_bundle(
            self.root,
            "research",
            limit=8,
            neighbor_limit=4,
            include_cross_pond=False,
        )
        bridge_subset = feed_evidence_decision_subset(bridge_bundle)
        admitted_refs = sorted(
            {
                str(source_ref).strip()
                for pair in pairs
                for source_ref in pair.get("evidence_refs", []) or []
                if str(source_ref).strip()
            }
        )
        self.assertEqual(bridge_subset["source_refs"], admitted_refs)
        self.assertIn("disclosure_service", layers)
        self.assertTrue(pairs)
        self.assertEqual(pairs[0]["edge_kind"], "disclosure_semantic")
        self.assertIn("disclosure_grant", pairs[0])
        self.assertIn("disclosure_provenance", pairs[0])
        self.assertEqual(pairs[0]["disclosure_provenance"]["surface"], "feed")

    def test_select_contextual_candidate_pairs_routes_through_disclosure(self) -> None:
        self._write_capsules()
        pairs = _select_contextual_candidate_pairs(
            self.root,
            limit=6,
            domain_overlays=["research"],
        )
        self.assertTrue(feed_disclosure_service_enabled(self.root))
        disclosure_pairs = [row for row in pairs if row.get("edge_kind") == "disclosure_semantic"]
        self.assertTrue(disclosure_pairs)
        self.assertTrue(all(row.get("disclosure_provenance") for row in disclosure_pairs))

    def test_legacy_meta_edge_selection_when_flag_disabled(self) -> None:
        config_path = self.root / "product" / "inner_world_v1" / "config" / "runtime.json"
        runtime = json.loads(config_path.read_text(encoding="utf-8"))
        runtime["feed"]["disclosure_service_v1"] = False
        config_path.write_text(json.dumps(runtime), encoding="utf-8")
        self.assertFalse(feed_disclosure_service_enabled(self.root))

        from conversation_os.meta_layer import meta_layer_dir, META_LAYER_FILES, write_jsonl

        meta_dir = meta_layer_dir(self.root)
        meta_dir.mkdir(parents=True)
        write_jsonl(
            meta_dir / META_LAYER_FILES["guardrail"],
            [
                {
                    "meta_id": "meta-feed-left",
                    "kind": "signal_frame",
                    "label": "Research signal",
                    "summary": "Research signal about progressive disclosure.",
                    "status": "approved_for_surface",
                    "confidence": 0.9,
                    "source_refs": ["fixture:research-insight.md"],
                    "chunk_ids": ["chunk-left"],
                    "evidence": ["Research signal about progressive disclosure."],
                    "attributes": {"tokens": ["research", "disclosure"]},
                },
                {
                    "meta_id": "meta-feed-right",
                    "kind": "direction",
                    "label": "Product direction",
                    "summary": "Product direction for bounded feed evidence.",
                    "status": "approved_for_surface",
                    "confidence": 0.88,
                    "source_refs": ["fixture:product-design.md"],
                    "chunk_ids": ["chunk-right"],
                    "evidence": ["Product direction for bounded feed evidence."],
                    "attributes": {"tokens": ["product", "evidence"]},
                },
            ],
        )
        from conversation_os.storage import append_jsonl as append_data_jsonl

        append_data_jsonl(
            self.root / "product" / "inner_world_v1" / "data" / "knowledge_edges.jsonl",
            {
                "edge_id": "edge-feed-legacy",
                "from_id": "meta-node-meta-feed-left",
                "to_id": "meta-node-meta-feed-right",
                "kind": "relates_to",
                "confidence": 0.82,
                "attributes": {"shared_tokens": ["research", "evidence"]},
                "evidence_refs": ["fixture:research-insight.md"],
            },
        )
        pairs = _select_contextual_candidate_pairs(self.root, limit=6, domain_overlays=["research"])
        self.assertTrue(any(row.get("edge_kind") != "disclosure_semantic" for row in pairs))

    def test_effective_grant_is_bounded(self) -> None:
        grant = build_feed_effective_grant(self.root, ["research"])
        self.assertEqual(grant.envelope, "bounded")
        self.assertIn("research", grant.dimensions)

    def test_record_feed_receipt_when_persistence_enabled(self) -> None:
        self._write_capsules()
        config_path = self.root / "product" / "inner_world_v1" / "config" / "runtime.json"
        runtime = json.loads(config_path.read_text(encoding="utf-8"))
        runtime["disclosure"] = {"receipts": {"persistent_receipts_v1": True}}
        config_path.write_text(json.dumps(runtime), encoding="utf-8")

        pairs, retrieval_bundle, _layers = collect_feed_evidence_pairs(self.root, limit=2)
        grant = pairs[0]["disclosure_grant"]
        receipt = record_feed_disclosure_receipt(
            self.root,
            retrieval_bundle=retrieval_bundle,
            effective_grant=grant,
            pair_count=len(pairs),
        )
        self.assertIsNotNone(receipt)
        self.assertEqual(receipt.get("surface"), "feed")

    def test_adapter_avoids_product_surface_imports(self) -> None:
        adapter_path = Path(__file__).resolve().parents[1] / "src" / "conversation_os" / "feed_disclosure_adapter.py"
        tree = ast.parse(adapter_path.read_text(encoding="utf-8"))
        imports = {
            (node.module or "")
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module
        }
        for token in ("chat_backends", "holodeck_disclosure_adapter", "worldbuilding_studio", "product_inner_world", "miniapp"):
            self.assertFalse(any(token in item for item in imports), token)

    def test_runtime_config_defaults_flag_off(self) -> None:
        bare_root = Path(tempfile.mkdtemp())
        try:
            config = load_feed_disclosure_config(bare_root)
            self.assertFalse(config["disclosure_service_v1"])
        finally:
            import shutil

            shutil.rmtree(bare_root)

    def test_map_retrieval_bundle_to_feed_pairs_single_capsule(self) -> None:
        grant = build_feed_effective_grant(self.root, ["research"])
        bundle = {
            "seed_capsules": [
                {
                    "capsule_id": "capsule-single",
                    "label": "Single admitted capsule",
                    "summary": "One admitted capsule for feed evidence.",
                    "confidence": 0.9,
                    "source_refs": ["fixture:single.md"],
                }
            ],
            "related_capsules": [],
            "count": 1,
            "result_status": "disclosed",
        }
        pairs = map_retrieval_bundle_to_feed_pairs(bundle, effective_grant=grant)
        self.assertEqual(len(pairs), 1)
        self.assertNotEqual(pairs[0]["left"]["meta_id"], pairs[0]["right"]["meta_id"])


if __name__ == "__main__":
    unittest.main()
