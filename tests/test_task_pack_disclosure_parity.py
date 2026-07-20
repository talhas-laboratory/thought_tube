from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from conversation_os.knowledge_layer import build_retrieval_bundle
from conversation_os.storage import append_jsonl
from conversation_os.task_pack_disclosure_adapter import (
    collect_task_pack_evidence,
    enrich_task_pack_with_bounded_evidence,
    load_task_pack_disclosure_config,
    map_retrieval_bundle_to_evidence_blocks,
    task_pack_disclosure_service_enabled,
)


class TaskPackDisclosureParityTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        config_dir = self.root / "product" / "inner_world_v1" / "config"
        config_dir.mkdir(parents=True)
        (config_dir / "runtime.json").write_text(
            json.dumps(
                {
                    "task_pack": {"disclosure_service_v1": True},
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
                "capsule_id": "capsule-task-pack-left",
                "capsule_type": "concept",
                "label": "Research insight",
                "summary": "Research insight about progressive disclosure and bounded task-pack evidence.",
                "confidence": 0.9,
                "ref_type": "concept",
                "ref_id": "concept-task-pack-left",
                "source_refs": ["fixture:research-insight.md"],
            },
            {
                "capsule_id": "capsule-task-pack-right",
                "capsule_type": "concept",
                "label": "Product design tension",
                "summary": "Product design tension between surprise and bounded evidence selection.",
                "confidence": 0.88,
                "ref_type": "concept",
                "ref_id": "concept-task-pack-right",
                "source_refs": ["fixture:product-design.md"],
            },
        ]
        for row in rows:
            append_jsonl(path, row)

    def test_evidence_blocks_match_bridge_retrieval_subset(self) -> None:
        self._write_capsules()
        evidence = collect_task_pack_evidence(
            self.root,
            "research progressive disclosure",
            domain_overlays=["research"],
        )
        bridge_bundle = build_retrieval_bundle(
            self.root,
            "research progressive disclosure research",
            limit=6,
            neighbor_limit=4,
            include_cross_pond=False,
        )
        bridge_blocks = map_retrieval_bundle_to_evidence_blocks(
            bridge_bundle,
            query="research progressive disclosure research",
            max_blocks=4,
        )
        admitted_refs = sorted(block["source_ref"] for block in evidence["blocks"])
        bridge_refs = sorted(block["source_ref"] for block in bridge_blocks)
        self.assertEqual(admitted_refs, bridge_refs)
        self.assertTrue(evidence["blocks"])
        self.assertEqual(evidence["blocks"][0]["provenance"]["surface"], "task_pack")

    def test_unrelated_request_does_not_receive_fallback_filler(self) -> None:
        self._write_capsules()
        evidence = collect_task_pack_evidence(self.root, "quantum entanglement topology")
        self.assertEqual(evidence["count"], 0)
        self.assertEqual(evidence["blocks"], [])

    def test_enrich_task_pack_adds_bounded_evidence_when_enabled(self) -> None:
        self._write_capsules()
        pack = {"task_id": "task-evidence-001", "request": "research progressive disclosure"}
        enriched = enrich_task_pack_with_bounded_evidence(
            self.root,
            pack,
            request="research progressive disclosure",
            domain_overlays=["research"],
        )
        self.assertIn("bounded_evidence", enriched)
        self.assertGreater(enriched["bounded_evidence"]["count"], 0)
        self.assertTrue(enriched["bounded_evidence"]["blocks"])

    def test_enrich_task_pack_skips_evidence_when_flag_disabled(self) -> None:
        self._write_capsules()
        config_path = self.root / "product" / "inner_world_v1" / "config" / "runtime.json"
        runtime = json.loads(config_path.read_text(encoding="utf-8"))
        runtime["task_pack"]["disclosure_service_v1"] = False
        config_path.write_text(json.dumps(runtime), encoding="utf-8")
        pack = {"task_id": "task-evidence-002", "request": "research progressive disclosure"}
        enriched = enrich_task_pack_with_bounded_evidence(
            self.root,
            pack,
            request="research progressive disclosure",
            domain_overlays=["research"],
        )
        self.assertNotIn("bounded_evidence", enriched)
        self.assertFalse(task_pack_disclosure_service_enabled(self.root))

    def test_enrich_task_pack_omits_empty_evidence_section(self) -> None:
        self._write_capsules()
        pack = {"task_id": "task-evidence-003", "request": "quantum entanglement topology"}
        enriched = enrich_task_pack_with_bounded_evidence(
            self.root,
            pack,
            request="quantum entanglement topology",
        )
        self.assertNotIn("bounded_evidence", enriched)

    def test_runtime_config_defaults_off(self) -> None:
        config_path = self.root / "product" / "inner_world_v1" / "config" / "runtime.json"
        config_path.write_text(json.dumps({"task_pack": {}}), encoding="utf-8")
        config = load_task_pack_disclosure_config(self.root)
        self.assertFalse(config["disclosure_service_v1"])
        self.assertEqual(config["max_evidence_blocks"], 4)


if __name__ == "__main__":
    unittest.main()
