"""VOCAB-002/003 table-driven semantics tests."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from conversation_os.metaphysical_vocabulary_governance import (
    assess_branch_mapping_separation,
    assess_mapping,
    assess_promotion_policy,
    capture_raw_expression,
    classify_vocabulary_level,
    create_term_mapping,
    lookup_with_mapping,
    publish_evolution_report,
    record_deprecation,
    record_evolution_reversal,
    review_promotion,
    validate_type_extension,
)


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "metaphysical_vocabulary"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class MetaphysicalVocabularyGovernanceTestCase(unittest.TestCase):
    def test_level_classification_outcome_table(self) -> None:
        table = _load("level_classification_outcome_table.json")
        for case in table["cases"]:
            with self.subTest(case_id=case["case_id"]):
                result = classify_vocabulary_level(case["term"])
                expected = case["expected"]
                self.assertEqual(result.level, expected["level"])
                self.assertEqual(result.name, expected["name"])
                if "promotion_authority" in expected:
                    self.assertEqual(result.promotion_authority, expected["promotion_authority"])
                if "promotion_required" in expected:
                    self.assertEqual(result.promotion_required, expected["promotion_required"])
                if "default_exposure" in expected:
                    self.assertEqual(result.default_exposure, expected["default_exposure"])
                if "global_exposure" in expected:
                    self.assertEqual(result.global_exposure, expected["global_exposure"])
                if "forced_normalization" in expected:
                    self.assertEqual(result.forced_normalization, expected["forced_normalization"])

    def test_mapping_outcome_table(self) -> None:
        table = _load("mapping_outcome_table.json")
        for case in table["cases"]:
            with self.subTest(case_id=case["case_id"]):
                if "mapping_a" in case:
                    result = assess_branch_mapping_separation(case["mapping_a"], case["mapping_b"])
                    expected = case["expected"]
                    self.assertEqual(result.exposed_as_global, expected["exposed_as_global"])
                    self.assertEqual(result.distinct_target_types, expected["distinct_target_types"])
                    self.assertEqual(result.preserves_source_expression, expected["preserves_source_expression"])
                    continue

                result = assess_mapping(case["mapping"])
                expected = case["expected"]
                if "implies_identity" in expected:
                    self.assertEqual(result.implies_identity, expected["implies_identity"])
                if "allows_canonical_substitution" in expected:
                    self.assertEqual(
                        result.allows_canonical_substitution,
                        expected["allows_canonical_substitution"],
                    )
                if "preserves_source_expression" in expected:
                    self.assertEqual(result.preserves_source_expression, expected["preserves_source_expression"])
                if "identity_confirmation_required" in expected:
                    self.assertEqual(
                        result.identity_confirmation_required,
                        expected["identity_confirmation_required"],
                    )
                if "implies_equivalence" in expected:
                    self.assertEqual(result.implies_equivalence, expected["implies_equivalence"])
                if "abstention_required" in expected:
                    self.assertEqual(result.abstention_required, expected["abstention_required"])

    def test_extension_safety_outcome_table(self) -> None:
        table = _load("extension_safety_outcome_table.json")
        for case in table["cases"]:
            with self.subTest(case_id=case["case_id"]):
                result = validate_type_extension(case["extension"])
                expected = case["expected"]
                self.assertEqual(result.validation_result, expected["validation_result"])
                if "error_code" in expected:
                    self.assertEqual(result.error_code, expected["error_code"])
                if "specializes_kernel" in expected:
                    self.assertEqual(result.specializes_kernel, expected["specializes_kernel"])

    def test_preservation_outcome_table(self) -> None:
        table = _load("preservation_outcome_table.json")
        for case in table["cases"]:
            with self.subTest(case_id=case["case_id"]):
                expected = case["expected"]

                if "raw_expression" in case:
                    raw = capture_raw_expression(
                        expression_id=str(case["raw_expression"]["id"]),
                        text=str(case["raw_expression"]["text"]),
                        source_fragment_id=str(case["raw_expression"].get("source_fragment_id", "")),
                        alias_of=str(case["raw_expression"].get("alias_of", "")),
                    )
                    if "retrieved_raw_text" in expected:
                        self.assertEqual(raw.text, expected["retrieved_raw_text"])
                    if expected.get("alias_link_preserved"):
                        self.assertEqual(raw.alias_of, case["raw_expression"].get("alias_of", ""))

                if "mapping" in case and "scope_id_preserved" in expected:
                    mapping = create_term_mapping(
                        {
                            **case["mapping"],
                            "id": "map_pres_test",
                        }
                    )
                    self.assertEqual(mapping.scope_id, expected["scope_id_preserved"])
                    self.assertEqual(mapping.confidence, expected["confidence_preserved"])
                    self.assertEqual(mapping.provenance_id, expected["provenance_id_preserved"])

                if "lookup_request" in case:
                    lookup = lookup_with_mapping(
                        expression=case["lookup_request"]["expression"],
                        scope_id=case["lookup_request"]["scope_id"],
                        branch_context=case["lookup_request"].get("branch_context", ""),
                        mappings=[
                            {
                                "id": "map_branch_a",
                                "source_type_or_expression": "raw:heavy",
                                "target_type": "workspace:computational_load",
                                "mapping_kind": "narrower",
                                "scope_id": "scope_glossary",
                                "confidence": 0.8,
                                "branch_context": "branch_vocab_a",
                            }
                        ],
                    )
                    self.assertTrue(expected["returns_source_expression"])
                    self.assertIsNotNone(lookup.mapping)
                    self.assertFalse(expected["substitutes_canonical_only"])
                    self.assertEqual(lookup.source_expression, case["lookup_request"]["expression"])

    def test_promotion_outcome_table(self) -> None:
        table = _load("promotion_outcome_table.json")
        for case in table["cases"]:
            with self.subTest(case_id=case["case_id"]):
                expected = case["expected"]
                if case.get("proposal") is None:
                    policy = assess_promotion_policy()
                    self.assertEqual(policy.promotion_required, expected["promotion_required"])
                    self.assertEqual(policy.local_vocabulary_usable, expected["local_vocabulary_usable"])
                    continue

                result = review_promotion(case["proposal"])
                self.assertEqual(result.promotion_status, expected["promotion_status"])
                if "source_term_still_addressable" in expected:
                    self.assertEqual(result.source_term_still_addressable, expected["source_term_still_addressable"])
                if "prior_level_retained_in_provenance" in expected:
                    self.assertEqual(
                        result.prior_level_retained_in_provenance,
                        expected["prior_level_retained_in_provenance"],
                    )
                if "local_term_usable" in expected:
                    self.assertEqual(result.local_term_usable, expected["local_term_usable"])
                if "not_invalidated" in expected:
                    self.assertEqual(result.not_invalidated, expected["not_invalidated"])
                if "exposed_as_global" in expected:
                    self.assertEqual(result.exposed_as_global, expected["exposed_as_global"])
                if "governance_status" in expected:
                    self.assertEqual(result.governance_status, expected["governance_status"])
                if "epistemic_status_unchanged" in expected:
                    self.assertEqual(result.epistemic_status_unchanged, expected["epistemic_status_unchanged"])

    def test_evolution_outcome_table(self) -> None:
        table = _load("evolution_outcome_table.json")
        for case in table["cases"]:
            with self.subTest(case_id=case["case_id"]):
                expected = case["expected"]

                if "report" in case:
                    result = publish_evolution_report(case["report"])
                    if "validation_result" in expected:
                        self.assertEqual(result.validation_result, expected["validation_result"])
                    if "error_code" in expected:
                        self.assertEqual(result.error_code, expected["error_code"])
                    if "prior_definition_addressable" in expected:
                        self.assertEqual(result.prior_definition_addressable, expected["prior_definition_addressable"])
                    if "stale_dependents_listed" in expected:
                        self.assertEqual(result.stale_dependents_listed, expected["stale_dependents_listed"])
                    if "reversible" in expected:
                        self.assertEqual(result.reversible, expected["reversible"])
                    if "semantic_loss_warnings_nonempty" in expected:
                        self.assertEqual(
                            result.semantic_loss_warnings_nonempty,
                            expected["semantic_loss_warnings_nonempty"],
                        )

                if "deprecation" in case:
                    record = record_deprecation(case["deprecation"])
                    if expected.get("deprecated_term_preserved"):
                        self.assertEqual(record.deprecated_term, case["deprecation"]["deprecated_term"])
                    if expected.get("migration_explicit"):
                        self.assertTrue(record.migration_plan)
                    if "reversible" in expected:
                        self.assertEqual(record.reversible, expected["reversible"])

                if "reversal" in case:
                    result = record_evolution_reversal(case["reversal"])
                    self.assertEqual(result.reversal_recorded, expected["reversal_recorded"])
                    self.assertEqual(
                        result.restored_definition_addressable,
                        expected["restored_definition_addressable"],
                    )


if __name__ == "__main__":
    unittest.main()
