"""BRANCH-002 table-driven semantics tests."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from conversation_os.metaphysical_branch_reasoning import assess_support, resolve_inheritance


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "metaphysical_branch"


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

    def test_inherited_support_excludes_sibling_branch_evidence(self) -> None:
        result = assess_support(
            branch_id="branch_a",
            scope_id="scope_org",
            claim_proposition={"predicate": "p", "arguments": ["x"]},
            evidence_claims=[
                {
                    "id": "cl_sibling",
                    "branch_id": "branch_b",
                    "scope_id": "scope_org",
                    "polarity": "affirmative",
                    "proposition": {"predicate": "p", "arguments": ["x"]},
                }
            ],
            include_inherited=True,
            branch_ancestry=[
                {"branch_id": "branch_main", "parent_branch_id": ""},
                {"branch_id": "branch_a", "parent_branch_id": "branch_main"},
                {"branch_id": "branch_b", "parent_branch_id": "branch_main"},
            ],
        )
        self.assertEqual(result.support_value, "unresolved")


if __name__ == "__main__":
    unittest.main()
