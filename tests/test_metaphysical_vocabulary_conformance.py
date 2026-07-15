"""VOCAB-004 adversarial conformance and acceptance regression tests."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from conversation_os.metaphysical_vocabulary_governance import (
    VOCAB_CONTRACT_VERSION,
    assess_branch_mapping_separation,
    assess_mapping,
    capture_raw_expression,
    classify_vocabulary_level,
    lookup_with_mapping,
    publish_evolution_report,
    review_promotion,
    validate_type_extension,
)


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "metaphysical_vocabulary"
ACCEPTANCE_TABLES = {
    "VOCAB-ACC-001": ("mapping_outcome_table.json", "map-001"),
    "VOCAB-ACC-002": ("mapping_outcome_table.json", "map-004"),
    "VOCAB-ACC-003": ("promotion_outcome_table.json", "promo-002"),
    "VOCAB-ACC-004": ("extension_safety_outcome_table.json", "ext-002"),
    "VOCAB-ACC-005": ("preservation_outcome_table.json", "pres-001"),
}


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _case_by_id(table: dict, case_id: str) -> dict:
    for case in table["cases"]:
        if case["case_id"] == case_id:
            return case
    raise KeyError(case_id)


class MetaphysicalVocabularyConformanceTestCase(unittest.TestCase):
    def test_required_acceptance_scenarios(self) -> None:
        for acceptance_id, (table_name, case_id) in ACCEPTANCE_TABLES.items():
            with self.subTest(acceptance_id=acceptance_id, case_id=case_id):
                case = _case_by_id(_load(table_name), case_id)
                if table_name.startswith("mapping"):
                    if "mapping_a" in case:
                        result = assess_branch_mapping_separation(case["mapping_a"], case["mapping_b"])
                        self.assertEqual(result.exposed_as_global, case["expected"]["exposed_as_global"])
                    else:
                        result = assess_mapping(case["mapping"])
                        self.assertEqual(result.implies_identity, case["expected"]["implies_identity"])
                elif table_name.startswith("promotion"):
                    result = review_promotion(case["proposal"])
                    self.assertEqual(result.promotion_status, case["expected"]["promotion_status"])
                    if "local_term_usable" in case["expected"]:
                        self.assertEqual(result.local_term_usable, case["expected"]["local_term_usable"])
                elif table_name.startswith("extension"):
                    result = validate_type_extension(case["extension"])
                    self.assertEqual(result.validation_result, case["expected"]["validation_result"])
                elif table_name.startswith("preservation"):
                    raw = capture_raw_expression(
                        expression_id=str(case["raw_expression"]["id"]),
                        text=str(case["raw_expression"]["text"]),
                        source_fragment_id=str(case["raw_expression"].get("source_fragment_id", "")),
                    )
                    self.assertEqual(raw.text, case["expected"]["retrieved_raw_text"])

    def test_adversarial_suite(self) -> None:
        suite = _load("adversarial_suite.json")
        for case in suite["cases"]:
            with self.subTest(case_id=case["case_id"], category=case["category"]):
                operation = case["operation"]
                inputs = case["inputs"]
                expected = case["expected"]

                if operation == "assess_mapping":
                    result = assess_mapping(inputs["mapping"])
                    if "implies_identity" in expected:
                        self.assertEqual(result.implies_identity, expected["implies_identity"])
                    if "allows_canonical_substitution" in expected:
                        self.assertEqual(
                            result.allows_canonical_substitution,
                            expected["allows_canonical_substitution"],
                        )
                    if "implies_equivalence" in expected:
                        self.assertEqual(result.implies_equivalence, expected["implies_equivalence"])

                elif operation == "assess_branch_mapping_separation":
                    result = assess_branch_mapping_separation(inputs["mapping_a"], inputs["mapping_b"])
                    self.assertEqual(result.exposed_as_global, expected["exposed_as_global"])
                    if "distinct_target_types" in expected:
                        self.assertEqual(result.distinct_target_types, expected["distinct_target_types"])

                elif operation == "review_promotion":
                    result = review_promotion(inputs["proposal"])
                    self.assertEqual(result.promotion_status, expected["promotion_status"])
                    if "local_term_usable" in expected:
                        self.assertEqual(result.local_term_usable, expected["local_term_usable"])
                    if "not_invalidated" in expected:
                        self.assertEqual(result.not_invalidated, expected["not_invalidated"])
                    if "epistemic_status_unchanged" in expected:
                        self.assertEqual(
                            result.epistemic_status_unchanged,
                            expected["epistemic_status_unchanged"],
                        )

                elif operation == "validate_type_extension":
                    result = validate_type_extension(inputs["extension"])
                    self.assertEqual(result.validation_result, expected["validation_result"])
                    if "error_code" in expected:
                        self.assertEqual(result.error_code, expected["error_code"])

                elif operation == "publish_evolution_report":
                    result = publish_evolution_report(inputs["report"])
                    self.assertEqual(result.validation_result, expected["validation_result"])
                    if "prior_definition_addressable" in expected:
                        self.assertEqual(
                            result.prior_definition_addressable,
                            expected["prior_definition_addressable"],
                        )
                    if "stale_dependents_listed" in expected:
                        self.assertEqual(result.stale_dependents_listed, expected["stale_dependents_listed"])
                    if "semantic_loss_warnings_nonempty" in expected:
                        self.assertEqual(
                            result.semantic_loss_warnings_nonempty,
                            expected["semantic_loss_warnings_nonempty"],
                        )
                    if "error_code" in expected:
                        self.assertEqual(result.error_code, expected["error_code"])

                elif operation == "capture_raw_expression":
                    raw = capture_raw_expression(
                        expression_id=inputs["expression_id"],
                        text=inputs["text"],
                        source_fragment_id=inputs.get("source_fragment_id", ""),
                    )
                    self.assertEqual(raw.text, expected["retrieved_raw_text"])

                elif operation == "lookup_with_mapping":
                    result = lookup_with_mapping(
                        expression=inputs["expression"],
                        scope_id=inputs["scope_id"],
                        branch_context=inputs.get("branch_context", ""),
                        mappings=inputs.get("mappings", []),
                    )
                    self.assertTrue(expected["returns_source_expression"])
                    self.assertIsNotNone(result.mapping)
                    self.assertFalse(expected["substitutes_canonical_only"])

    def test_model_local_terms_not_globally_exposed(self) -> None:
        level = classify_vocabulary_level(
            {
                "type_id": "model_local:private_label",
                "namespace_level": "model_local",
                "branch_context": "branch_hyp_a",
            }
        )
        self.assertEqual(level.name, "model_local")
        self.assertFalse(level.global_exposure)

    def test_consumer_pins_vocab_contract_version(self) -> None:
        release = json.loads(
            (
                ROOT
                / "docs"
                / "workspaces"
                / "metaphysical-vocabulary-governance"
                / "derived"
                / "VOCABULARY_ATOMIC_OBLIGATIONS.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(release["public_contract_version"], VOCAB_CONTRACT_VERSION)


if __name__ == "__main__":
    unittest.main()
