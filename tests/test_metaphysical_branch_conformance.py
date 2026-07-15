"""BRANCH-004 adversarial conformance and acceptance regression tests."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from conversation_os.metaphysical_branch_reasoning import (
    InvalidInferenceOutputStatusError,
    SelfConflictError,
    assess_merge,
    assess_support,
    classify_conflict,
    run_inference,
)


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "metaphysical_branch"
ACCEPTANCE_TABLES = {
    "BRANCH-ACC-001": ("inheritance_outcome_table.json", "inherit-001"),
    "BRANCH-ACC-002": ("inheritance_outcome_table.json", "inherit-003"),
    "BRANCH-ACC-003": ("support_outcome_table.json", "support-003"),
    "BRANCH-ACC-004": ("conflict_outcome_table.json", "conflict-002"),
    "BRANCH-ACC-005": ("conflict_outcome_table.json", "conflict-003"),
    "BRANCH-ACC-006": ("merge_outcome_table.json", "merge-003"),
    "BRANCH-ACC-007": ("inference_outcome_table.json", "infer-005"),
    "BRANCH-ACC-008": ("merge_outcome_table.json", "merge-006"),
}


DEFAULT_BOTH_CLAIMS = [
    {
        "id": "cl_aff_001",
        "polarity": "affirmative",
        "scope_id": "scope_org",
        "proposition": {"predicate": "causes", "arguments": ["x", "y"]},
    },
    {
        "id": "cl_neg_001",
        "polarity": "negative",
        "scope_id": "scope_org",
        "proposition": {"predicate": "causes", "arguments": ["x", "y"]},
    },
]


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _case_by_id(table: dict, case_id: str) -> dict:
    for case in table["cases"]:
        if case["case_id"] == case_id:
            return case
    raise KeyError(case_id)


class MetaphysicalBranchConformanceTestCase(unittest.TestCase):
    def test_required_acceptance_scenarios(self) -> None:
        for acceptance_id, (table_name, case_id) in ACCEPTANCE_TABLES.items():
            with self.subTest(acceptance_id=acceptance_id, case_id=case_id):
                case = _case_by_id(_load(table_name), case_id)
                if table_name.startswith("inheritance"):
                    from conversation_os.metaphysical_branch_reasoning import resolve_inheritance

                    result = resolve_inheritance(
                        child_branch_id=case["child_branch_id"],
                        record_id=case["record_id"],
                        record_kind=case["record_kind"],
                        branch_ancestry=case["branch_ancestry"],
                        membership_entries=case["membership_entries"],
                    )
                    self.assertEqual(result.visibility, case["expected"]["visibility"])
                elif table_name.startswith("support"):
                    result = assess_support(
                        branch_id=case["branch_id"],
                        scope_id=case["scope_id"],
                        claim_proposition=case["claim_proposition"],
                        evidence_claims=case["evidence_claims"],
                        include_inherited=bool(case.get("include_inherited", False)),
                        branch_ancestry=case.get("branch_ancestry"),
                    )
                    self.assertEqual(result.support_value, case["expected"]["support_value"])
                elif table_name.startswith("conflict"):
                    result = classify_conflict(
                        claim_a=case["claim_a"],
                        claim_b=case["claim_b"],
                        context_notes=str(case.get("context_notes", "")),
                    )
                    self.assertEqual(result.conflict_kind, case["expected"]["conflict_kind"])
                    self.assertEqual(
                        result.is_logical_contradiction,
                        case["expected"]["is_logical_contradiction"],
                    )
                elif table_name.startswith("merge"):
                    result = assess_merge(
                        branch_a_id=case["branch_a_id"],
                        branch_b_id=case["branch_b_id"],
                        records_a=case["records_a"],
                        records_b=case["records_b"],
                        branch_a_assumptions=case.get("branch_a_assumptions"),
                        branch_b_assumptions=case.get("branch_b_assumptions"),
                    )
                    self.assertEqual(result.merge_verdict, case["expected"]["merge_verdict"])
                elif table_name.startswith("inference"):
                    input_claims = case.get("input_claims")
                    if input_claims is None and "both" in case["inference_context"].get(
                        "accepted_epistemic_statuses", []
                    ):
                        input_claims = DEFAULT_BOTH_CLAIMS
                    result = run_inference(
                        inference_context=case["inference_context"],
                        input_claims=input_claims or [],
                    )
                    self.assertIsNotNone(result.abstention)
                    assert result.abstention is not None
                    self.assertEqual(
                        result.abstention.reason,
                        case["expected"]["abstention"]["reason"],
                    )

    def test_adversarial_suite(self) -> None:
        suite = _load("adversarial_suite.json")
        for case in suite["cases"]:
            with self.subTest(case_id=case["case_id"], category=case["category"]):
                operation = case["operation"]
                inputs = case["inputs"]

                if case.get("expected_error"):
                    with self.assertRaises(SelfConflictError):
                        classify_conflict(
                            claim_a=inputs["claim_a"],
                            claim_b=inputs["claim_b"],
                        )
                    continue

                expected = case["expected"]

                if operation == "assess_support":
                    result = assess_support(
                        branch_id=inputs["branch_id"],
                        scope_id=inputs["scope_id"],
                        claim_proposition=inputs["claim_proposition"],
                        evidence_claims=inputs["evidence_claims"],
                        include_inherited=bool(inputs.get("include_inherited", False)),
                        branch_ancestry=inputs.get("branch_ancestry"),
                    )
                    self.assertEqual(result.support_value, expected["support_value"])
                    self.assertEqual(result.affirmative_claim_ids, expected["affirmative_claim_ids"])
                    self.assertEqual(result.negative_claim_ids, expected["negative_claim_ids"])
                    if "max_total_ids" in expected:
                        total = len(result.affirmative_claim_ids) + len(result.negative_claim_ids)
                        self.assertLessEqual(total, expected["max_total_ids"])

                elif operation == "classify_conflict":
                    result = classify_conflict(
                        claim_a=inputs["claim_a"],
                        claim_b=inputs["claim_b"],
                        context_notes=str(inputs.get("context_notes", "")),
                    )
                    self.assertEqual(result.conflict_kind, expected["conflict_kind"])
                    self.assertEqual(
                        result.is_logical_contradiction,
                        expected["is_logical_contradiction"],
                    )

                elif operation == "assess_merge":
                    result = assess_merge(
                        branch_a_id=inputs["branch_a_id"],
                        branch_b_id=inputs["branch_b_id"],
                        records_a=inputs["records_a"],
                        records_b=inputs["records_b"],
                        branch_a_assumptions=inputs.get("branch_a_assumptions"),
                        branch_b_assumptions=inputs.get("branch_b_assumptions"),
                    )
                    self.assertEqual(result.merge_verdict, expected["merge_verdict"])
                    if "shared_record_ids" in expected:
                        self.assertEqual(result.shared_record_ids, expected["shared_record_ids"])
                    if "compatible_additions" in expected:
                        self.assertEqual(result.compatible_additions, expected["compatible_additions"])
                    if "conflict_claim_ids" in expected:
                        conflict_ids = {
                            entry.claim_a_id for entry in result.conflicts
                        } | {entry.claim_b_id for entry in result.conflicts}
                        self.assertEqual(conflict_ids, set(expected["conflict_claim_ids"]))

                elif operation == "run_inference":
                    result = run_inference(
                        inference_context=inputs["inference_context"],
                        input_claims=inputs.get("input_claims", []),
                    )
                    self.assertEqual(len(result.output_claims), expected["output_claims_count"])
                    if expected.get("all_epistemic_status"):
                        for claim in result.output_claims:
                            self.assertEqual(claim.epistemic_status, expected["all_epistemic_status"])
                    if "polarities" in expected:
                        self.assertEqual(
                            sorted(claim.polarity for claim in result.output_claims),
                            sorted(expected["polarities"]),
                        )
                    if expected.get("abstention_reason"):
                        self.assertIsNotNone(result.abstention)
                        abstention = result.abstention
                        assert abstention is not None
                        self.assertEqual(abstention.reason, expected["abstention_reason"])
                    if "unresolved_claim_ids" in expected:
                        self.assertIsNotNone(result.abstention)
                        abstention = result.abstention
                        assert abstention is not None
                        self.assertEqual(
                            sorted(abstention.unresolved_claim_ids),
                            sorted(expected["unresolved_claim_ids"]),
                        )

    def test_invalid_inference_output_status_rejected(self) -> None:
        with self.assertRaises(InvalidInferenceOutputStatusError):
            run_inference(
                inference_context={
                    "branches": ["branch_main"],
                    "scope_id": "scope_org",
                    "accepted_maturity_statuses": ["structured"],
                    "accepted_epistemic_statuses": ["supported"],
                    "accepted_governance_statuses": ["local"],
                    "contradiction_policy": "preserve",
                    "output_status": "supported",
                    "inference_kind": "structural",
                    "max_depth": 2,
                },
                input_claims=[],
            )

    def test_continuity_preserves_input_claim_ids(self) -> None:
        claim_id = "cl_continuity_001"
        result = run_inference(
            inference_context={
                "branches": ["branch_main"],
                "scope_id": "scope_org",
                "accepted_maturity_statuses": ["structured"],
                "accepted_epistemic_statuses": ["supported"],
                "accepted_governance_statuses": ["local"],
                "contradiction_policy": "preserve",
                "output_status": "candidate",
                "inference_kind": "structural",
                "max_depth": 2,
            },
            input_claims=[
                {
                    "id": claim_id,
                    "polarity": "affirmative",
                    "scope_id": "scope_org",
                    "proposition": {"predicate": "causes", "arguments": ["kernel", "branch"]},
                }
            ],
        )
        self.assertEqual(len(result.output_claims), 1)
        self.assertIn(claim_id, result.output_claims[0].source_claim_ids)
        self.assertTrue(result.output_claims[0].provenance_id)


if __name__ == "__main__":
    unittest.main()
