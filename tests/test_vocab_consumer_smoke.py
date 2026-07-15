"""VOCAB-005 consumer smoke proofs."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from conversation_os.metaphysical_vocabulary_governance import (
    VOCAB_CONTRACT_VERSION,
    assess_mapping,
    capture_raw_expression,
    lookup_with_mapping,
)


ROOT = Path(__file__).resolve().parents[1]
RELEASE_PATH = (
    ROOT
    / "docs"
    / "workspaces"
    / "metaphysical-vocabulary-governance"
    / "derived"
    / "VOCAB_RELEASE_DEPENDENCY_CONTRACT.json"
)


class VocabConsumerSmokeTestCase(unittest.TestCase):
    def test_application_consumer_renders_mapping_without_mutation(self) -> None:
        """Application consumer: canonical view is rendered; raw text and mapping record stay intact."""
        raw_text = "heavy (computational)"
        raw = capture_raw_expression(
            expression_id="raw_heavy_comp",
            text=raw_text,
            source_fragment_id="sf_legacy_glossary",
        )
        mapping = {
            "mapping_id": "map_heavy_analogy",
            "source_type_or_expression": f"raw:{raw_text}",
            "target_type": "shared:computational_load",
            "mapping_kind": "analogous",
            "scope_id": "scope_glossary",
            "branch_context": "branch_vocab_a",
            "confidence": 0.7,
        }

        result = lookup_with_mapping(
            expression=f"raw:{raw_text}",
            scope_id="scope_glossary",
            branch_context="branch_vocab_a",
            mappings=[mapping],
            raw_expressions=[raw.to_dict()],
        )

        self.assertEqual(result.source_expression, f"raw:{raw_text}")
        self.assertIsNotNone(result.mapping)
        assert result.mapping is not None
        self.assertEqual(result.mapping.mapping_kind, "analogous")
        self.assertEqual(result.raw_expression.text if result.raw_expression else "", raw_text)
        self.assertEqual(result.canonical_view_label, "shared:computational_load")
        assessment = assess_mapping(mapping)
        self.assertFalse(assessment.implies_identity)

    def test_consumer_pins_released_contract_versions(self) -> None:
        release = json.loads(RELEASE_PATH.read_text(encoding="utf-8"))
        self.assertEqual(release["provider_contract_version"], VOCAB_CONTRACT_VERSION)


if __name__ == "__main__":
    unittest.main()
