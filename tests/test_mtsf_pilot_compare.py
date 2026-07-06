import unittest

from conversation_os.mtsf_pilot_compare import compare_extractions


class MtsfPilotCompareTestCase(unittest.TestCase):
    def test_compare_extractions_reports_overlap(self) -> None:
        baseline = {
            "artifact_type": "third_space",
            "entity_ids": ["entity-context-field", "entity-latent-manifold", "entity-hardened-idea"],
            "entity_names": ["context field", "latent manifold", "hardened idea"],
            "entity_count": 3,
            "relation_count": 2,
            "relation_signatures": [
                "entity-context-field|modulates|entity-latent-manifold",
                "entity-latent-manifold|contains|entity-agent-path",
            ],
            "activation_snapshot_count": 2,
            "candidate_pattern_id": "cand-synthetic-subconscious",
            "candidate_pattern_names": ["synthetic subconscious"],
            "stencil_count": 0,
        }
        pipeline = {
            "artifact_type": "mtsf_pipeline",
            "capture_mode": "deep",
            "extraction_source": "mtsf_ingest.deep_heuristic",
            "entity_ids": ["entity-context-field", "entity-latent-manifold"],
            "entity_names": ["context field", "latent manifold"],
            "entity_count": 2,
            "relation_count": 1,
            "relation_signatures": ["entity-context-field|modulates|entity-latent-manifold"],
            "quality_count": 1,
            "quality_role_count": 1,
            "candidate_shape_ids": ["cand-context-triangulation"],
            "candidate_shape_names": ["context triangulation"],
            "stencil_draft_count": 1,
            "active_stencil_ids": ["stencil-context-warps-topology"],
            "stencil_count": 1,
            "shape_instance_count": 1,
            "confidence": 0.9,
            "promotion_ready": True,
            "validation_ok": True,
        }
        result = compare_extractions(baseline, pipeline)
        self.assertEqual(result["entities"]["id_overlap_count"], 2)
        self.assertEqual(result["relations"]["overlap_count"], 1)
        self.assertIn("machine_readable_stencil_schema", result["gaps_closed"])


if __name__ == "__main__":
    unittest.main()
