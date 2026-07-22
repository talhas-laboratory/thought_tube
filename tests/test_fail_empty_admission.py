from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from conversation_os.candidate_admission import (
    evaluate_capsule_admission,
    fail_empty_admission_enforce_enabled,
)
from conversation_os.knowledge_layer import add_alias_resolution, build_retrieval_bundle


def _write_runtime(root: Path, *, enforce: bool = True, shadow: bool = True) -> None:
    config_dir = root / "product" / "inner_world_v1" / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "runtime.json").write_text(
        json.dumps(
            {
                "knowledge": {
                    "fail_empty_admission_shadow_v1": shadow,
                    "fail_empty_admission_enforce_v1": enforce,
                }
            }
        ),
        encoding="utf-8",
    )


def _write_capsules(root: Path, rows: list[dict]) -> None:
    data_dir = root / "runtime" / "product_state" / "inner_world_v1" / "data"
    data_dir.mkdir(parents=True)
    (data_dir / "semantic_capsules.jsonl").write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n",
        encoding="utf-8",
    )
    (data_dir / "context_links.jsonl").write_text("", encoding="utf-8")
    (data_dir / "link_governance.json").write_text(
        json.dumps({"link_policies": [], "alias_resolutions": []}),
        encoding="utf-8",
    )


class FailEmptyAdmissionTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        _write_runtime(self.root, enforce=True, shadow=True)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_unrelated_query_returns_empty_when_enforced(self) -> None:
        _write_capsules(
            self.root,
            [
                {
                    "capsule_id": "cap-high-confidence",
                    "capsule_type": "meta",
                    "ref_type": "meta",
                    "ref_id": "meta-001",
                    "label": "agent memory architecture",
                    "summary": "recursive self-modeling for agents",
                    "confidence": 0.95,
                    "source_refs": ["sources/agent-memory.md"],
                    "attributes": {},
                }
            ],
        )
        bundle = build_retrieval_bundle(
            self.root,
            "quantum gardening extraterrestrial crops hydroponics",
            envelope_mode="bounded",
        )
        self.assertEqual(bundle["count"], 0)
        self.assertEqual(bundle["result_status"], "empty_no_positive_match")
        self.assertEqual(bundle["seed_capsules"], [])

    def test_confidence_only_candidate_is_rejected(self) -> None:
        capsule = {
            "capsule_id": "cap-confidence-only",
            "capsule_type": "meta",
            "ref_type": "meta",
            "ref_id": "meta-002",
            "label": "unrelated topic",
            "summary": "no query overlap here",
            "confidence": 0.99,
            "source_refs": [],
            "attributes": {},
        }
        decision = evaluate_capsule_admission(
            capsule,
            query_tokens={"quantum", "gardening"},
            index_tokens={"label": {"unrelated", "topic"}, "summary": {"no", "query"}, "attrs": set()},
        )
        self.assertFalse(decision["admitted"])
        self.assertEqual(decision["rejection_reason"], "confidence_only")

    def test_alias_hit_preserves_recall(self) -> None:
        _write_capsules(
            self.root,
            [
                {
                    "capsule_id": "cap-alias-target",
                    "capsule_type": "concept",
                    "ref_type": "concept",
                    "ref_id": "concept-001",
                    "label": "formal ontology",
                    "summary": "semantic addressing for knowledge graphs",
                    "confidence": 0.4,
                    "source_refs": ["sources/semantic-addressing.md"],
                    "attributes": {},
                }
            ],
        )
        add_alias_resolution(
            self.root,
            "semantic address graph",
            ref_type="concept",
            ref_id="concept-001",
        )
        bundle = build_retrieval_bundle(
            self.root,
            "semantic address graph routing",
            envelope_mode="open",
        )
        self.assertEqual(bundle["result_status"], "disclosed")
        self.assertEqual(bundle["seed_capsules"][0]["capsule_id"], "cap-alias-target")
        self.assertTrue(bundle["alias_hits"])

    def test_bounded_missing_pond_metadata_fails_closed(self) -> None:
        _write_capsules(
            self.root,
            [
                {
                    "capsule_id": "cap-missing-pond",
                    "capsule_type": "meta",
                    "ref_type": "meta",
                    "ref_id": "meta-003",
                    "label": "hybrid retrieval extraction",
                    "summary": "graph traversal information extraction",
                    "confidence": 0.7,
                    "source_refs": ["sources/hybrid-rag.md"],
                    "attributes": {},
                }
            ],
        )
        bundle = build_retrieval_bundle(
            self.root,
            "hybrid retrieval extraction",
            envelope_mode="strict",
        )
        self.assertEqual(bundle["result_status"], "empty_no_positive_match")
        self.assertEqual(bundle["count"], 0)

    def test_shadow_records_decisions_when_enforce_disabled(self) -> None:
        _write_runtime(self.root, enforce=False, shadow=True)
        _write_capsules(
            self.root,
            [
                {
                    "capsule_id": "cap-shadow",
                    "capsule_type": "meta",
                    "ref_id": "meta-004",
                    "ref_type": "meta",
                    "label": "high confidence only",
                    "summary": "still no overlap",
                    "confidence": 0.91,
                    "source_refs": [],
                    "attributes": {},
                }
            ],
        )
        bundle = build_retrieval_bundle(self.root, "quantum gardening", envelope_mode="open")
        self.assertIn("shadow_admission", bundle)
        self.assertGreater(bundle["shadow_admission"]["rejected_count"], 0)
        self.assertTrue(fail_empty_admission_enforce_enabled(self.root) is False)

    def test_explicit_pin_admits_candidate(self) -> None:
        _write_capsules(
            self.root,
            [
                {
                    "capsule_id": "cap-pin",
                    "capsule_type": "bubble",
                    "ref_type": "bubble",
                    "ref_id": "bubble-001",
                    "label": "pinned evidence bubble",
                    "summary": "operator pinned source",
                    "confidence": 0.2,
                    "source_refs": ["sources/pinned.md"],
                    "attributes": {},
                }
            ],
        )
        bundle = build_retrieval_bundle(
            self.root,
            "unrelated operator request",
            explicit_pins=["bubble:bubble-001"],
            envelope_mode="open",
        )
        self.assertEqual(bundle["result_status"], "disclosed")
        self.assertEqual(bundle["seed_capsules"][0]["capsule_id"], "cap-pin")


if __name__ == "__main__":
    unittest.main()
