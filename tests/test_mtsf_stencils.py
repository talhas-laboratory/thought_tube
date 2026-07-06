import json
import unittest
from pathlib import Path

from conversation_os.mtsf_stencils import (
    compute_structural_fingerprint,
    default_seed_stencils_path,
    default_stencil_role_types_path,
    load_seed_stencils,
    load_stencil_role_types,
    validate_seed_library,
    validate_stencil_record,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


class MtsfStencilsTestCase(unittest.TestCase):
    def test_seed_artifact_files_exist(self) -> None:
        self.assertTrue(default_seed_stencils_path(REPO_ROOT).exists())
        self.assertTrue(default_stencil_role_types_path(REPO_ROOT).exists())
        draft_schema = (
            REPO_ROOT
            / "docs"
            / "frameworks"
            / "metaphysical-thought-space"
            / "schemas"
            / "stencil-draft.schema.json"
        )
        self.assertTrue(draft_schema.exists())

    def test_role_types_closed_vocabulary(self) -> None:
        role_types = load_stencil_role_types(REPO_ROOT)
        self.assertIn("field", role_types)
        self.assertIn("bridge", role_types)
        self.assertGreaterEqual(len(role_types), 10)

    def test_seed_library_has_six_exemplars(self) -> None:
        stencils = load_seed_stencils(REPO_ROOT)
        self.assertEqual(len(stencils), 6)
        ids = {row["id"] for row in stencils}
        self.assertIn("stencil-context-warps-topology", ids)
        self.assertIn("stencil-symmetric-blueprint", ids)
        self.assertIn("stencil-antisymmetric-guardrail", ids)
        self.assertIn("stencil-phase-transition-bridge", ids)
        self.assertIn("stencil-hardening-loop", ids)
        self.assertIn("stencil-reservoir-depletion", ids)

    def test_seed_library_validation_passes(self) -> None:
        report = validate_seed_library(REPO_ROOT)
        self.assertEqual(report["failed"], 0, json.dumps(report["rows"], indent=2))
        self.assertEqual(report["passed"], 6)

    def test_fingerprints_are_unique(self) -> None:
        stencils = load_seed_stencils(REPO_ROOT)
        fingerprints = [compute_structural_fingerprint(row) for row in stencils]
        self.assertEqual(len(fingerprints), len(set(fingerprints)))

    def test_each_seed_has_agent_views(self) -> None:
        for stencil in load_seed_stencils(REPO_ROOT):
            views = stencil.get("views", {})
            self.assertTrue(views.get("gist"), stencil["id"])
            self.assertTrue(views.get("mermaid_topology"), stencil["id"])
            self.assertTrue(len(views.get("slot_table", [])) >= 2, stencil["id"])

    def test_causal_geometry_is_minimum_facet(self) -> None:
        for stencil in load_seed_stencils(REPO_ROOT):
            facet = stencil.get("facet_completeness", {})
            self.assertTrue(facet.get("causal_geometry"), stencil["id"])

    def test_validate_stencil_record_catches_missing_topology(self) -> None:
        role_types = load_stencil_role_types(REPO_ROOT)
        errors = validate_stencil_record(
            {
                "id": "stencil-test",
                "name": "test",
                "role_entities": [{"role_id": "r-a", "role_type": "source"}],
                "relation_topology": [],
                "facet_completeness": {"causal_geometry": True},
                "evidence": {"source_refs": ["test"]},
                "views": {
                    "gist": "x",
                    "mermaid_topology": "flowchart LR",
                    "slot_table": [{"slot_id": "r-a", "role_type": "source"}],
                },
            },
            allowed_role_types=role_types,
        )
        self.assertTrue(any("at least 2 roles" in err for err in errors))
        self.assertTrue(any("at least 1 edge" in err for err in errors))


if __name__ == "__main__":
    unittest.main()
