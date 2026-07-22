from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import conversation_os.meta_layer as meta_layer_module
import conversation_os.models as models_module
from conversation_os.knowledge_layer import build_retrieval_bundle
from conversation_os.shape_candidate_retrieval import (
    build_shape_query,
    evaluate_anti_match,
    read_shape_retrieval_context,
)
from conversation_os.storage import append_jsonl, write_jsonl
from conversation_os.vault_ingest import ingest_text_content


class ShapeCandidateRetrievalTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        config_dir = self.root / "product" / "inner_world_v1" / "config"
        config_dir.mkdir(parents=True)
        (config_dir / "runtime.json").write_text(
            json.dumps(
                {
                    "knowledge": {
                        "fail_empty_admission_shadow_v1": True,
                        "fail_empty_admission_enforce_v1": True,
                        "shape_candidate_search_v1": True,
                        "shape_anti_match_enforcement_v1": True,
                    }
                }
            ),
            encoding="utf-8",
        )
        (self.root / "product" / "inner_world_v1" / "data").mkdir(parents=True)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _write_shape_signature(self, *, signature_id: str, source_ref: str, shape_name: str) -> None:
        evidence = models_module.EvidenceSpan(
            source_ref=source_ref,
            chunk_id=f"chunk-{signature_id}",
            text="Signal dilution through accumulation and hierarchy confusion in bounded systems.",
            kind="direct_quote",
        )
        signature = models_module.SystemDynamicSignature(
            signature_id=signature_id,
            source_ref=source_ref,
            source_kind="analysis_unit",
            source_anchor_id=f"unit-{signature_id}",
            title="Signal dilution signature",
            summary="Useful elements accumulate faster than hierarchy can coordinate.",
            system_boundary="Private cognitive layer under accumulation pressure",
            observer_lens="structural_interpretation",
            entities=[
                models_module.SignatureEntity(
                    entity_id=f"{signature_id}-receiver",
                    label="Receiver",
                    node_type="receiver",
                    role="limited_receiver_capacity",
                    confidence=0.8,
                    evidence=[evidence.to_dict()],
                ).to_dict()
            ],
            relations=[],
            feedback_loops=[],
            candidate_shapes=[
                models_module.CandidateShape(
                    shape_name=shape_name,
                    confidence=0.82,
                    rationale="Useful elements accumulate faster than hierarchy can coordinate.",
                ).to_dict()
            ],
            evidence_spans=[evidence.to_dict()],
            confidence=0.82,
            status="provisional",
            attributes={"scale": "local_interaction"},
        ).to_dict()
        write_jsonl(self.root / "product" / "inner_world_v1" / "data" / "shape_signatures.jsonl", [signature])

    def _write_capsules(self) -> None:
        source_ref = "fixture:shape-retrieval"
        ingest_text_content(
            self.root,
            title="shape-retrieval-fixture",
            content="# User\n\nPrivate cognitive layer under accumulation pressure.\n",
            source_ref=source_ref,
            source_type="chat_converter_conversation",
            metadata={"branch_id": "branch-shape-001", "scope_id": "scope-shape-001"},
        )
        self._write_shape_signature(
            signature_id="signature-signal-dilution",
            source_ref=source_ref,
            shape_name="Signal Dilution Through Accumulation",
        )
        append_jsonl(
            self.root / "product" / "inner_world_v1" / "data" / "semantic_capsules.jsonl",
            {
                "capsule_id": "capsule-lexical-distractor",
                "capsule_type": "concept",
                "label": "Accumulation hierarchy confusion noise",
                "summary": "Accumulation hierarchy confusion noise competes with attention and ranking.",
                "confidence": 0.96,
                "ref_type": "concept",
                "ref_id": "concept-distractor",
                "source_refs": ["docs/plans/distractor.md"],
                "attributes": {"domain": "bridge"},
            },
        )
        append_jsonl(
            self.root / "product" / "inner_world_v1" / "data" / "semantic_capsules.jsonl",
            {
                "capsule_id": "capsule-shape-correct",
                "capsule_type": "concept",
                "label": "Private cognitive layering",
                "summary": "A provisional receiver boundary under accumulation pressure.",
                "confidence": 0.41,
                "ref_type": "meta",
                "ref_id": "meta-shape-correct",
                "source_refs": [source_ref],
                "attributes": {
                    "shape_signature_id": "signature-signal-dilution",
                    "shape_name": "Signal Dilution Through Accumulation",
                    "meta_id": "meta-shape-correct",
                },
            },
        )

    def test_shape_assisted_retrieval_promotes_structural_candidate_above_lexical_distractor(self) -> None:
        self._write_capsules()
        query = "signal dilution accumulation hierarchy confusion private cognitive layer"
        bundle = build_retrieval_bundle(
            self.root,
            query,
            limit=4,
            neighbor_limit=0,
            envelope_mode="open",
            shape_search={
                "enabled": True,
                "branch_id": "branch-shape-001",
                "scope_id": "scope-shape-001",
                "source_refs": ["fixture:shape-retrieval"],
            },
        )
        self.assertEqual(bundle["shape_retrieval"]["result_status"], "ready")
        self.assertGreaterEqual(bundle["shape_retrieval"]["expansion_count"], 1)
        seed_ids = [row["capsule_id"] for row in bundle.get("seed_capsules", [])]
        self.assertIn("capsule-shape-correct", seed_ids)
        self.assertEqual(seed_ids[0], "capsule-shape-correct")
        decisions = {
            row["capsule_id"]: row
            for row in bundle.get("shadow_admission", {}).get("decisions", [])
        }
        self.assertIn("structural_shape_match", decisions["capsule-shape-correct"]["admission_signals"])

    def test_profile_unavailable_abstains_shape_search_without_lexical_widen(self) -> None:
        self._write_capsules()
        with mock.patch(
            "conversation_os.shape_projection_reader.read_shape_projections",
            return_value={
                "readiness_state": "unavailable",
                "retrieval_allowed": False,
                "legacy": {"candidate_projections": [], "anti_match_projections": []},
            },
        ):
            bundle = build_retrieval_bundle(
                self.root,
                "quantum gardening unrelated topic",
                limit=4,
                neighbor_limit=0,
                envelope_mode="open",
                shape_search={"enabled": True},
            )
        self.assertEqual(bundle["shape_retrieval"]["result_status"], "abstained_dependency_not_ready")
        self.assertEqual(bundle.get("count", 0), 0)

    def test_anti_match_hard_rejects_false_analogy_candidate(self) -> None:
        self._write_capsules()
        append_jsonl(
            self.root / "product" / "inner_world_v1" / "data" / "semantic_capsules.jsonl",
            {
                "capsule_id": "capsule-maze-analogy",
                "capsule_type": "concept",
                "label": "Maze confusion hidden route",
                "summary": "A receiver is delayed before reaching the intended goal through a hidden route.",
                "confidence": 0.88,
                "ref_type": "meta",
                "ref_id": "meta-maze-1",
                "source_refs": ["fixture:maze"],
                "attributes": {
                    "shape_signature_id": "signature-maze",
                    "shape_name": "Search Confusion Through Hidden Route",
                    "meta_id": "meta-maze-1",
                },
            },
        )
        meta_layer_module.record_shape_feedback(
            self.root,
            scope="project",
            scope_key="scope-shape-001",
            shape_name="Signal Dilution Through Accumulation",
            shape_definition="Useful elements accumulate faster than hierarchy.",
            feedback_type="rejected",
            rejected_candidate_id="meta-maze-1",
            anchor_meta_id="meta-shape-correct",
            anti_match_penalty=0.75,
        )
        bundle = build_retrieval_bundle(
            self.root,
            "hidden route maze confusion receiver delayed goal",
            limit=6,
            neighbor_limit=0,
            envelope_mode="open",
            shape_search={
                "enabled": True,
                "scope_id": "scope-shape-001",
                "enforce_anti_match": True,
            },
        )
        decisions = {
            row["capsule_id"]: row
            for row in bundle.get("shadow_admission", {}).get("decisions", [])
        }
        maze_decision = decisions.get("capsule-maze-analogy", {})
        self.assertFalse(maze_decision.get("admitted", True))
        self.assertEqual(maze_decision.get("rejection_reason"), "anti_match_blocked")
        seed_ids = [row["capsule_id"] for row in bundle.get("seed_capsules", [])]
        self.assertNotIn("capsule-maze-analogy", seed_ids)

    def test_unrelated_anti_match_has_no_effect(self) -> None:
        capsule = {
            "capsule_id": "capsule-safe",
            "ref_type": "meta",
            "ref_id": "meta-safe-1",
            "attributes": {"meta_id": "meta-safe-1"},
        }
        anti_matches = [
            {
                "projection_id": "anti-match:1",
                "candidate_meta_id": "meta-other",
                "anchor_meta_id": "meta-anchor-1",
                "anti_match_penalty": 0.9,
                "branch_id": "branch-shape-001",
                "scope_id": "scope-shape-001",
            }
        ]
        decision = evaluate_anti_match(
            capsule,
            anti_matches=anti_matches,
            branch_id="branch-shape-001",
            scope_id="scope-shape-001",
            structural_score=0.6,
        )
        self.assertEqual(decision.outcome, "not_applicable")

    def test_shape_query_reads_branch_scope_projections(self) -> None:
        self._write_capsules()
        shape_query = build_shape_query(
            "signal dilution accumulation",
            branch_id="branch-shape-001",
            scope_id="scope-shape-001",
            source_refs=["fixture:shape-retrieval"],
        )
        context = read_shape_retrieval_context(self.root, shape_query)
        self.assertEqual(context["result_status"], "ready")
        self.assertEqual(len(context["candidate_projections"]), 1)
        projection = context["candidate_projections"][0]
        self.assertEqual(projection["branch_id"], "branch-shape-001")
        self.assertEqual(projection["scope_id"], "scope-shape-001")
        self.assertEqual(projection["scale"], "local_interaction")

    def test_derive_pattern_from_declared_shape_population(self) -> None:
        from conversation_os.shape_candidate_retrieval import derive_pattern_from_shapes

        left = {
            "shape_id": "shape:forest-network",
            "title": "Mycorrhizal nutrient network",
            "summary": "Shared resource routing under receiver capacity limits",
            "system_boundary": "forest plot",
            "entities": [
                {"role": "limited_receiver_capacity", "label": "Tree"},
                {"role": "distributor", "label": "Fungal network"},
            ],
            "attributes": {"scale": "local_interaction"},
            "mechanism": "mycorrhizal_transfer",
        }
        right = {
            "shape_id": "shape:signal-dilution",
            "title": "Signal dilution through accumulation",
            "summary": "Useful elements accumulate faster than hierarchy can coordinate",
            "system_boundary": "cognitive layer",
            "entities": [
                {"role": "limited_receiver_capacity", "label": "Receiver"},
                {"role": "distributor", "label": "Queue"},
            ],
            "attributes": {"scale": "local_interaction"},
            "mechanism": "attention_queue",
        }
        pattern = derive_pattern_from_shapes(
            [left, right],
            pattern_id="pattern:receiver-overload",
            branch_id="branch-shape-001",
            scope_id="scope-shape-001",
        )
        self.assertEqual(pattern["pattern_id"], "pattern:receiver-overload")
        self.assertTrue(pattern["merge_shapes_forbidden"])
        self.assertEqual(
            set(pattern["shape_population_refs"]),
            {"shape:forest-network", "shape:signal-dilution"},
        )
        self.assertTrue(any(item["role"] == "limited_receiver_capacity" for item in pattern["role_mappings"]))
        self.assertTrue(pattern["invariants"])
        self.assertIn("shape_identity_merge", pattern["transfer_limits"])

    def test_classify_recovers_low_vocab_structural_pair_and_rejects_lexical_distractor(self) -> None:
        from conversation_os.shape_candidate_retrieval import (
            classify_shape_pair,
            derive_pattern_from_shapes,
            revise_anti_match_record,
        )

        structural_a = {
            "shape_id": "shape:ecosystem-routing",
            "title": "Nutrient routing under scarcity",
            "summary": "Distributor reallocates under receiver limits",
            "entities": [{"role": "limited_receiver_capacity"}, {"role": "distributor"}],
            "system_boundary": "plot",
            "attributes": {"scale": "local_interaction"},
            "mechanism": "biological_transfer",
        }
        structural_b = {
            "shape_id": "shape:inbox-overflow",
            "title": "Attention queue saturation",
            "summary": "Coordinator fails when inputs accumulate beyond hierarchy",
            "entities": [{"role": "limited_receiver_capacity"}, {"role": "distributor"}],
            "system_boundary": "workspace",
            "attributes": {"scale": "local_interaction"},
            "mechanism": "attention_queue",
        }
        lexical_distractor = {
            "shape_id": "shape:signal-noise-lab",
            "title": "Signal dilution through accumulation",
            "summary": "Signal dilution through accumulation hierarchy confusion",
            "entities": [{"role": "sensor"}, {"role": "amplifier"}],
            "system_boundary": "lab bench",
            "attributes": {"scale": "instrument"},
            "mechanism": "electrical_noise",
        }

        pattern = derive_pattern_from_shapes(
            [structural_a, structural_b],
            pattern_id="pattern:receiver-capacity",
            branch_id="branch-a",
            scope_id="scope-a",
        )
        transfer = classify_shape_pair(
            structural_a,
            structural_b,
            pattern=pattern,
            branch_id="branch-a",
            scope_id="scope-a",
        )
        self.assertIn(transfer["record_kind"], {"candidate_match", "transfer_hypothesis", "validated_membership"})
        self.assertTrue(transfer["merge_shapes_forbidden"])
        self.assertLess(transfer["vocabulary_overlap"], 0.55)
        self.assertIn("shared_roles", transfer["holds_where"])
        self.assertTrue(transfer["revisable"])

        anti = classify_shape_pair(
            structural_b,
            lexical_distractor,
            pattern=pattern,
            branch_id="branch-a",
            scope_id="scope-a",
        )
        self.assertEqual(anti["record_kind"], "anti_match")
        self.assertIn("anti_match_projection", anti)
        self.assertEqual(anti["anti_match_projection"]["branch_id"], "branch-a")
        self.assertEqual(anti["anti_match_projection"]["scope_id"], "scope-a")

        revised = revise_anti_match_record(
            anti,
            disposition="withdrawn",
            reason="human_override_after_review",
            branch_id="branch-a",
            scope_id="scope-a",
        )
        self.assertEqual(revised["disposition"], "withdrawn")
        self.assertEqual(revised["reason"], "human_override_after_review")
        self.assertTrue(revised["merge_shapes_forbidden"])
        self.assertEqual(revised["anti_match_projection"]["disposition"], "withdrawn")

    def test_pattern_never_allows_shape_merge_flag(self) -> None:
        from conversation_os.shape_candidate_retrieval import PatternRecord

        with self.assertRaises(ValueError):
            PatternRecord(
                pattern_id="pattern:bad",
                shape_population_refs=["shape:a", "shape:b"],
                merge_shapes_forbidden=False,
            ).to_dict()


if __name__ == "__main__":
    unittest.main()
