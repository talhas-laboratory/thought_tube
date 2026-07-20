from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import conversation_os.meta_layer as meta_layer_module
import conversation_os.models as models_module
from conversation_os.shape_projection_reader import (
    CANONICAL_SHAPE_PROFILE_ID,
    CONTRACT_VERSION,
    LEGACY_ADAPTER_VERSION,
    MIGRATION_DECISION_ID,
    migration_decision,
    read_shape_projections,
)
from conversation_os.storage import write_jsonl
from conversation_os.vault_ingest import ingest_text_content


class ShapeProjectionReaderTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        (self.root / "product" / "inner_world_v1" / "data").mkdir(parents=True, exist_ok=True)
        (self.root / "product" / "inner_world_v1" / "config").mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _legacy_data_dir(self) -> Path:
        path = self.root / "product" / "inner_world_v1" / "data"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _write_signature(self, *, signature_id: str, source_ref: str, system_boundary: str) -> dict:
        evidence = models_module.EvidenceSpan(
            source_ref=source_ref,
            chunk_id=f"chunk-{signature_id}",
            text="Synthetic structural evidence for Shape read adapter tests.",
            kind="direct_quote",
        )
        signature = models_module.SystemDynamicSignature(
            signature_id=signature_id,
            source_ref=source_ref,
            source_kind="analysis_unit",
            source_anchor_id=f"unit-{signature_id}",
            title="Fixture structural signature",
            summary="A receiver is delayed before reaching a goal.",
            system_boundary=system_boundary,
            observer_lens="structural_interpretation",
            entities=[
                models_module.SignatureEntity(
                    entity_id=f"{signature_id}-receiver",
                    label="Receiver",
                    node_type="receiver",
                    role="receiver",
                    confidence=0.8,
                    evidence=[evidence.to_dict()],
                ).to_dict()
            ],
            relations=[],
            feedback_loops=[],
            candidate_shapes=[
                models_module.CandidateShape(
                    shape_name="Route Confusion Through Blocked Transition",
                    confidence=0.75,
                    rationale="A receiver is delayed or blocked before reaching the intended goal.",
                ).to_dict()
            ],
            evidence_spans=[evidence.to_dict()],
            confidence=0.75,
            status="provisional",
            attributes={"scale": "local_interaction"},
        ).to_dict()
        write_jsonl(self._legacy_data_dir() / "shape_signatures.jsonl", [signature])
        return signature

    def test_canonical_profile_unavailable_abstains_without_legacy(self) -> None:
        payload = read_shape_projections(self.root)

        self.assertEqual(payload["schema_version"], CONTRACT_VERSION)
        self.assertFalse(payload["canonical"]["available"])
        self.assertEqual(payload["canonical"]["profile_id"], CANONICAL_SHAPE_PROFILE_ID)
        self.assertFalse(payload["retrieval_allowed"])
        self.assertIn(payload["readiness_state"], {"unavailable", "abstained"})
        self.assertIn("not registered", str(payload["abstention_reason"]))
        self.assertFalse(payload["legacy"]["promotion_allowed"])
        self.assertEqual(payload["migration_decision"]["decision_id"], MIGRATION_DECISION_ID)

    def test_legacy_candidate_preserves_branch_scope_boundary_and_provenance(self) -> None:
        source_ref = "fixture:cae014-shape"
        ingest_text_content(
            self.root,
            title="cae014-shape-fixture",
            content="# User\n\nSynthetic Shape read fixture.\n",
            source_ref=source_ref,
            source_type="chat_converter_conversation",
            source_family="chat_converter",
            metadata={
                "branch_id": "branch-cae014-fixture",
                "scope_id": "scope-stage-a",
                "fixture_only": True,
            },
        )
        boundary = "User interpretation flow under bounded aperture"
        self._write_signature(
            signature_id="signature-cae014-fixture",
            source_ref=source_ref,
            system_boundary=boundary,
        )

        payload = read_shape_projections(
            self.root,
            branch_id="branch-cae014-fixture",
            scope_id="scope-stage-a",
            source_refs=[source_ref],
        )
        candidates = payload["legacy"]["candidate_projections"]

        self.assertEqual(payload["readiness_state"], "legacy_only")
        self.assertTrue(payload["retrieval_allowed"])
        self.assertEqual(len(candidates), 1)
        candidate = candidates[0]
        self.assertEqual(candidate["kind"], "candidate")
        self.assertEqual(candidate["maturity_status"], "candidate")
        self.assertFalse(candidate["promotion_allowed"])
        self.assertFalse(candidate["pattern_membership"])
        self.assertEqual(candidate["branch_id"], "branch-cae014-fixture")
        self.assertEqual(candidate["scope_id"], "scope-stage-a")
        self.assertEqual(candidate["system_boundary"], boundary)
        self.assertIn("structural_interpretation", candidate["abstraction_contract"])
        self.assertEqual(candidate["scale"], "local_interaction")
        self.assertGreaterEqual(len(candidate["evidence_spans"]), 1)
        self.assertTrue(candidate["provenance"]["content_hash"])
        self.assertEqual(candidate["adapter_version"], LEGACY_ADAPTER_VERSION)

    def test_legacy_anti_match_projection_is_distinct_and_non_promotable(self) -> None:
        self._write_signature(
            signature_id="signature-anchor",
            source_ref="fixture:cae014-anchor",
            system_boundary="Anchor boundary",
        )
        meta_layer_module.record_shape_feedback(
            self.root,
            scope="project",
            scope_key="scope-stage-a",
            shape_name="Signal Dilution Through Accumulation",
            shape_definition="Useful elements accumulate faster than hierarchy.",
            feedback_type="rejected",
            rejected_candidate_id="meta-maze-1",
            anchor_meta_id="meta-anchor-1",
            anti_match_penalty=0.25,
        )

        payload = read_shape_projections(self.root, scope_id="scope-stage-a")
        anti_matches = payload["legacy"]["anti_match_projections"]

        self.assertGreaterEqual(len(anti_matches), 1)
        anti_match = anti_matches[0]
        self.assertEqual(anti_match["kind"], "anti_match")
        self.assertFalse(anti_match["promotion_allowed"])
        self.assertEqual(anti_match["anchor_meta_id"], "meta-anchor-1")
        self.assertEqual(anti_match["candidate_meta_id"], "meta-maze-1")
        self.assertGreater(anti_match["anti_match_penalty"], 0.0)

    def test_branch_scope_filter_excludes_out_of_scope_candidates(self) -> None:
        source_ref = "fixture:cae014-filter"
        ingest_text_content(
            self.root,
            title="cae014-filter",
            content="# User\n\nFilter fixture.\n",
            source_ref=source_ref,
            source_type="chat_converter_conversation",
            metadata={"branch_id": "branch-a", "scope_id": "scope-a"},
        )
        self._write_signature(
            signature_id="signature-filter",
            source_ref=source_ref,
            system_boundary="Boundary A",
        )

        included = read_shape_projections(self.root, branch_id="branch-a", scope_id="scope-a")
        excluded = read_shape_projections(self.root, branch_id="branch-b", scope_id="scope-b")

        self.assertEqual(len(included["legacy"]["candidate_projections"]), 1)
        self.assertEqual(len(excluded["legacy"]["candidate_projections"]), 0)
        self.assertFalse(excluded["retrieval_allowed"])

    def test_migration_decision_records_legacy_retention_without_promotion(self) -> None:
        decision = migration_decision()

        self.assertEqual(decision["decision_id"], MIGRATION_DECISION_ID)
        self.assertFalse(decision["promotion_allowed"])
        self.assertIn("profile:shape_and_semantic_addressing", decision["retirement_trigger"])


if __name__ == "__main__":
    unittest.main()
