"""BRANCH-002/003 table-driven semantics tests."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from conversation_os.metaphysical_branch_reasoning import (
    InvalidContradictionPolicyError,
    InvalidInferenceOutputStatusError,
    assess_merge,
    assess_support,
    classify_conflict,
    resolve_inheritance,
    run_inference,
)


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "metaphysical_branch"

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


class MetaphysicalBranchReasoningTestCase(unittest.TestCase):
    def test_inheritance_outcome_table(self) -> None:
        table = _load("inheritance_outcome_table.json")
        for case in table["cases"]:
            with self.subTest(case_id=case["case_id"]):
                result = resolve_inheritance(
                    child_branch_id=case["child_branch_id"],
                    record_id=case["record_id"],
                    record_kind=case["record_kind"],
                    branch_ancestry=case["branch_ancestry"],
                    membership_entries=case["membership_entries"],
                )
                expected = case["expected"]
                self.assertEqual(result.visibility, expected["visibility"])
                self.assertEqual(result.effective_membership_kind, expected["effective_membership_kind"])
                self.assertEqual(result.resolved_in_branch_id, expected["resolved_in_branch_id"])

    def test_support_outcome_table(self) -> None:
        table = _load("support_outcome_table.json")
        for case in table["cases"]:
            with self.subTest(case_id=case["case_id"]):
                ancestry = case.get("branch_ancestry")
                if ancestry is None and case.get("include_inherited"):
                    ancestry = [
                        {"branch_id": case["branch_id"], "parent_branch_id": "branch_main"},
                        {"branch_id": "branch_main", "parent_branch_id": ""},
                    ]
                result = assess_support(
                    branch_id=case["branch_id"],
                    scope_id=case["scope_id"],
                    claim_proposition=case["claim_proposition"],
                    evidence_claims=case["evidence_claims"],
                    include_inherited=bool(case.get("include_inherited", False)),
                    branch_ancestry=ancestry,
                )
                expected = case["expected"]
                self.assertEqual(result.support_value, expected["support_value"])
                self.assertEqual(result.affirmative_claim_ids, expected["affirmative_claim_ids"])
                self.assertEqual(result.negative_claim_ids, expected["negative_claim_ids"])

    def test_cross_branch_claims_do_not_leak_without_inheritance(self) -> None:
        result = assess_support(
            branch_id="branch_a",
            scope_id="scope_org",
            claim_proposition={"predicate": "p", "arguments": ["x"]},
            evidence_claims=[
                {
                    "id": "cl_other",
                    "branch_id": "branch_b",
                    "scope_id": "scope_org",
                    "polarity": "affirmative",
                    "proposition": {"predicate": "p", "arguments": ["x"]},
                }
            ],
            include_inherited=False,
        )
        self.assertEqual(result.support_value, "unresolved")

    def test_conflict_outcome_table(self) -> None:
        table = _load("conflict_outcome_table.json")
        for case in table["cases"]:
            with self.subTest(case_id=case["case_id"]):
                result = classify_conflict(
                    claim_a=case["claim_a"],
                    claim_b=case["claim_b"],
                    context_notes=str(case.get("context_notes", "")),
                )
                expected = case["expected"]
                self.assertEqual(result.conflict_kind, expected["conflict_kind"])
                self.assertEqual(result.is_logical_contradiction, expected["is_logical_contradiction"])

    def test_merge_outcome_table(self) -> None:
        table = _load("merge_outcome_table.json")
        for case in table["cases"]:
            with self.subTest(case_id=case["case_id"]):
                result = assess_merge(
                    branch_a_id=case["branch_a_id"],
                    branch_b_id=case["branch_b_id"],
                    records_a=case["records_a"],
                    records_b=case["records_b"],
                    branch_a_assumptions=case.get("branch_a_assumptions"),
                    branch_b_assumptions=case.get("branch_b_assumptions"),
                )
                expected = case["expected"]
                self.assertEqual(result.shared_record_ids, expected["shared_record_ids"])
                self.assertEqual(result.compatible_additions, expected["compatible_additions"])
                self.assertEqual(result.divergent_assumptions, expected["divergent_assumptions"])
                self.assertEqual(result.scope_differences, expected["scope_differences"])
                self.assertEqual(result.unresolved_identity_mappings, expected["unresolved_identity_mappings"])
                self.assertEqual(result.merge_verdict, expected["merge_verdict"])
                self.assertEqual(
                    [entry.to_dict() for entry in result.conflicts],
                    expected["conflicts"],
                )

    def test_inference_outcome_table(self) -> None:
        table = _load("inference_outcome_table.json")
        for case in table["cases"]:
            with self.subTest(case_id=case["case_id"]):
                if case.get("expected_error"):
                    with self.assertRaises(InvalidInferenceOutputStatusError):
                        run_inference(
                            inference_context=case["inference_context"],
                            input_claims=case.get("input_claims", []),
                        )
                    continue

                input_claims = case.get("input_claims")
                if input_claims is None and "both" in case["inference_context"].get(
                    "accepted_epistemic_statuses", []
                ):
                    input_claims = DEFAULT_BOTH_CLAIMS

                result = run_inference(
                    inference_context=case["inference_context"],
                    input_claims=input_claims or [],
                )
                expected = case["expected"]

                if "output_claims_count" in expected:
                    self.assertEqual(len(result.output_claims), expected["output_claims_count"])
                    polarities = sorted(claim.polarity for claim in result.output_claims)
                    self.assertEqual(polarities, sorted(expected["output_claims_polarities"]))
                elif "output_claims" in expected:
                    self.assertEqual(len(result.output_claims), len(expected["output_claims"]))
                    for actual, exp in zip(result.output_claims, expected["output_claims"]):
                        self.assertEqual(actual.epistemic_status, exp["epistemic_status"])
                        if "polarity" in exp:
                            self.assertEqual(actual.polarity, exp["polarity"])
                        if "source_claim_ids" in exp:
                            self.assertEqual(actual.source_claim_ids, exp["source_claim_ids"])

                if "branched_sub_contexts_count" in expected:
                    self.assertEqual(len(result.branched_sub_contexts), expected["branched_sub_contexts_count"])
                elif "branched_sub_contexts" in expected:
                    self.assertEqual(result.branched_sub_contexts, expected["branched_sub_contexts"])

                if expected.get("abstention") is None:
                    self.assertIsNone(result.abstention)
                elif expected.get("abstention"):
                    self.assertIsNotNone(result.abstention)
                    abstention = result.abstention
                    assert abstention is not None
                    self.assertEqual(abstention.reason, expected["abstention"]["reason"])
                    if expected["abstention"].get("unresolved_claim_ids_nonempty"):
                        self.assertTrue(abstention.unresolved_claim_ids)

                if expected.get("clarification_request") is None:
                    self.assertIsNone(result.clarification_request)
                elif expected.get("clarification_request"):
                    self.assertIsNotNone(result.clarification_request)
                    clarification = result.clarification_request
                    assert clarification is not None
                    if expected["clarification_request"].get("unresolved_claim_ids_nonempty"):
                        self.assertTrue(clarification.unresolved_claim_ids)

    def test_inference_rejects_unknown_contradiction_policy(self) -> None:
        with self.assertRaises(InvalidContradictionPolicyError):
            run_inference(
                inference_context={
                    "branches": ["branch_main"],
                    "scope_id": "scope_org",
                    "contradiction_policy": "select_best",
                    "output_status": "candidate",
                    "inference_kind": "structural",
                    "max_depth": 1,
                },
                input_claims=DEFAULT_BOTH_CLAIMS,
            )

    def test_later_contradictory_proposition_applies_clarify_policy(self) -> None:
        result = run_inference(
            inference_context={
                "branches": ["branch_main"],
                "scope_id": "scope_org",
                "contradiction_policy": "clarify",
                "output_status": "candidate",
                "inference_kind": "structural",
                "max_depth": 1,
            },
            input_claims=[
                {"id": "cl_single", "scope_id": "scope_org", "polarity": "affirmative", "proposition": {"predicate": "p", "arguments": ["x"]}},
                *DEFAULT_BOTH_CLAIMS,
            ],
        )
        self.assertEqual(result.output_claims, [])
        self.assertIsNotNone(result.clarification_request)

    def test_preserve_policy_keeps_unrelated_candidates_with_both(self) -> None:
        result = run_inference(
            inference_context={
                "branches": ["branch_main"],
                "scope_id": "scope_org",
                "contradiction_policy": "preserve",
                "output_status": "candidate",
                "inference_kind": "structural",
                "max_depth": 1,
            },
            input_claims=[
                *DEFAULT_BOTH_CLAIMS,
                {"id": "cl_other", "scope_id": "scope_org", "polarity": "affirmative", "proposition": {"predicate": "q", "arguments": ["y"]}},
            ],
        )
        self.assertEqual(
            sorted(claim.source_claim_ids[0] for claim in result.output_claims),
            ["cl_aff_001", "cl_neg_001", "cl_other"],
        )


if __name__ == "__main__":
    unittest.main()
