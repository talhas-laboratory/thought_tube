from __future__ import annotations

import ast
import json
import tempfile
import unittest
from pathlib import Path

from conversation_os.holodeck import _collect_contextualization_candidates, _seed_bundle
from conversation_os.holodeck_disclosure_adapter import (
    build_contextualization_query,
    collect_disclosure_knowledge_candidates,
    holodeck_disclosure_service_enabled,
    load_holodeck_disclosure_config,
    map_retrieval_bundle_to_candidates,
    retrieval_decision_subset,
)
from conversation_os.knowledge_layer import build_retrieval_bundle
from conversation_os.storage import append_jsonl


class HolodeckDisclosureParityTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        config_dir = self.root / "product" / "inner_world_v1" / "config"
        config_dir.mkdir(parents=True)
        (config_dir / "runtime.json").write_text(
            json.dumps(
                {
                    "holodeck": {"disclosure_service_v1": True},
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

    def _seed_bundle(self) -> dict:
        manifest = {
            "label": "Chat Bridge",
            "goal": "Bridge integration",
            "purpose": "Preserve bounded semantic assist",
            "success_condition": "",
            "scope_in": [],
            "scope_out": [],
            "domain_overlays": ["bridge"],
            "template_fields": {},
        }
        artifacts = [
            {
                "title": "Bridge plan",
                "summary": "Ground bridge integration in bounded semantic assist.",
                "source_ref": "docs/plans/chat-bridge.md",
            }
        ]
        return _seed_bundle(self.root, "ws-holodeck-001", manifest, artifacts, [])

    def _write_capsule(self) -> None:
        append_jsonl(
            self.root / "product" / "inner_world_v1" / "data" / "semantic_capsules.jsonl",
            {
                "capsule_id": "capsule-holodeck-1",
                "capsule_type": "concept",
                "label": "Bridge integration",
                "summary": "A bridge path with inspectable context assembly and bounded semantic assist.",
                "confidence": 0.91,
                "ref_type": "concept",
                "ref_id": "concept-bridge-holodeck",
                "source_refs": ["docs/plans/chat-bridge.md"],
                "attributes": {"domain": "bridge"},
            },
        )

    def test_knowledge_candidates_match_bridge_retrieval(self) -> None:
        self._write_capsule()
        seed = self._seed_bundle()
        query = build_contextualization_query(seed)
        bridge_bundle = build_retrieval_bundle(
            self.root,
            query,
            limit=6,
            neighbor_limit=4,
            include_cross_pond=False,
        )
        holodeck_candidates, layers = collect_disclosure_knowledge_candidates(
            self.root,
            seed,
            max_source_refs=6,
        )
        mapped = map_retrieval_bundle_to_candidates(bridge_bundle, seed)
        bridge_subset = retrieval_decision_subset(bridge_bundle)
        holodeck_subset = {
            "count": bridge_subset["count"],
            "result_status": bridge_subset["result_status"],
            "capsule_ids": sorted(row.get("capsule_id", "") for row in holodeck_candidates if row.get("capsule_id")),
            "source_refs": sorted(
                {
                    str(row.get("source_ref", "")).strip()
                    for row in holodeck_candidates
                    if str(row.get("source_ref", "")).strip()
                }
            ),
        }
        self.assertEqual(bridge_subset, holodeck_subset)
        self.assertEqual(mapped, holodeck_candidates)
        self.assertIn("disclosure_service", layers)

    def test_collect_contextualization_routes_knowledge_through_disclosure(self) -> None:
        self._write_capsule()
        seed = self._seed_bundle()
        artifacts = [
            {
                "title": "Bridge plan",
                "summary": "Ground bridge integration in bounded semantic assist.",
                "source_ref": "docs/plans/chat-bridge.md",
            }
        ]
        plan_path = self.root / "docs" / "plans" / "chat-bridge.md"
        plan_path.parent.mkdir(parents=True)
        plan_path.write_text(
            "# Chat Bridge\n\nGround bridge integration in bounded semantic assist and holodeck contextualization.\n",
            encoding="utf-8",
        )
        candidates, layers = _collect_contextualization_candidates(
            self.root,
            "ws-holodeck-001",
            seed,
            artifacts,
            max_source_refs=6,
        )
        self.assertTrue(holodeck_disclosure_service_enabled(self.root))
        self.assertIn("disclosure_service", layers)
        knowledge_layers = {row.get("source_layer", "") for row in candidates if row.get("candidate_kind") == "knowledge"}
        self.assertIn("disclosure_semantic", knowledge_layers)
        self.assertTrue(
            any(row.get("source_layer") in {"plan_doc", "artifact_doc"} for row in candidates)
        )

    def test_legacy_meta_scorer_isolated_when_flag_disabled(self) -> None:
        config_path = self.root / "product" / "inner_world_v1" / "config" / "runtime.json"
        runtime = json.loads(config_path.read_text(encoding="utf-8"))
        runtime["holodeck"]["disclosure_service_v1"] = False
        config_path.write_text(json.dumps(runtime), encoding="utf-8")
        self.assertFalse(holodeck_disclosure_service_enabled(self.root))

        from conversation_os.meta_layer import meta_layer_dir, META_LAYER_FILES, write_jsonl

        meta_dir = meta_layer_dir(self.root)
        meta_dir.mkdir(parents=True)
        write_jsonl(
            meta_dir / META_LAYER_FILES["guardrail"],
            [
                {
                    "meta_id": "guardrail-bounded-assist",
                    "kind": "guardrail",
                    "label": "Bounded Semantic Assist",
                    "summary": "Models may improve surfaced semantics, but they must not control core retrieval truth.",
                    "status": "approved_for_surface",
                    "confidence": 0.92,
                    "source_refs": ["docs/plans/bounded-assist.md"],
                    "chunk_ids": [],
                    "evidence": [],
                    "attributes": {},
                }
            ],
        )
        seed = self._seed_bundle()
        candidates, layers = _collect_contextualization_candidates(
            self.root,
            "ws-holodeck-001",
            seed,
            [],
            max_source_refs=6,
        )
        self.assertIn("meta_layer", layers)
        self.assertNotIn("disclosure_service", layers)
        self.assertTrue(any(str(row.get("source_layer", "")).startswith("meta_") for row in candidates))

    def test_adapter_avoids_product_surface_imports(self) -> None:
        adapter_path = Path(__file__).resolve().parents[1] / "src" / "conversation_os" / "holodeck_disclosure_adapter.py"
        tree = ast.parse(adapter_path.read_text(encoding="utf-8"))
        imports = {
            (node.module or "")
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module
        }
        for token in ("chat_backends", "holodeck", "worldbuilding_studio", "product_inner_world"):
            self.assertFalse(any(token in item for item in imports), token)

    def test_runtime_config_defaults_flag_off(self) -> None:
        bare_root = Path(tempfile.mkdtemp())
        try:
            config = load_holodeck_disclosure_config(bare_root)
            self.assertFalse(config["disclosure_service_v1"])
        finally:
            import shutil

            shutil.rmtree(bare_root)


if __name__ == "__main__":
    unittest.main()
