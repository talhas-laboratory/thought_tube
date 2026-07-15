"""KERNEL-001 atomic obligation matrix conformance tests."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from conversation_os.metaphysical_kernel import CONTRACT_VERSION, FRAMEWORK_SECTIONS, KERNEL_RECORD_KINDS
from conversation_os.metaphysical_kernel_contracts import CONTRACT_VERSION as CONTRACTS_VERSION


ROOT = Path(__file__).resolve().parents[1]
OBLIGATIONS_PATH = (
    ROOT
    / "docs"
    / "workspaces"
    / "metaphysical-kernel-ontology"
    / "derived"
    / "KERNEL_ATOMIC_OBLIGATIONS.json"
)

REQUIRED_OBLIGATION_KEYS = {
    "obligation_id",
    "source_section",
    "source_quote",
    "interpretation",
    "owner_module",
    "public_contract_version",
    "migration_impact",
    "tests_fixtures",
    "downstream_consumers",
    "completion_state",
    "unresolved_question",
}

ALLOWED_COMPLETION_STATES = {
    "verified",
    "phase1_minimal",
    "deferred",
    "gap",
    "implemented",
}


class KernelAtomicObligationsTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = json.loads(OBLIGATIONS_PATH.read_text(encoding="utf-8"))

    def test_obligations_file_exists(self) -> None:
        self.assertTrue(OBLIGATIONS_PATH.is_file())

    def test_contract_version_matches_code(self) -> None:
        self.assertEqual(self.payload["public_contract_version"], CONTRACT_VERSION)
        self.assertEqual(CONTRACTS_VERSION, CONTRACT_VERSION)

    def test_every_obligation_has_required_fields(self) -> None:
        for row in self.payload["obligations"]:
            missing = REQUIRED_OBLIGATION_KEYS - set(row)
            self.assertEqual(missing, set(), msg=f"{row.get('obligation_id')}: missing {missing}")

    def test_completion_states_are_allowed(self) -> None:
        for row in self.payload["obligations"]:
            self.assertIn(
                row["completion_state"],
                ALLOWED_COMPLETION_STATES,
                msg=row["obligation_id"],
            )

    def test_phase1_record_kinds_subset_of_kernel_record_kinds(self) -> None:
        implemented = set(self.payload["phase1_boundary"]["implemented_record_kinds"])
        self.assertTrue(implemented.issubset(KERNEL_RECORD_KINDS))

    def test_framework_sections_still_cover_task001_contracts(self) -> None:
        required = {
            "record_envelope",
            "source_fragment",
            "referent",
            "scope",
            "state",
            "claim",
            "relation_instance",
            "provenance",
            "model_branch",
            "branch_membership",
            "state_commitment",
            "lifecycle_axes",
            "profile_definition",
            "profile_conformance_result",
        }
        self.assertTrue(required.issubset(set(FRAMEWORK_SECTIONS)))

    def test_no_duplicate_obligation_ids(self) -> None:
        ids = [row["obligation_id"] for row in self.payload["obligations"]]
        self.assertEqual(len(ids), len(set(ids)))

    def test_gap_rows_have_unresolved_or_planned_fixture(self) -> None:
        planned = {item["gap_obligation_id"] for item in self.payload["validator_fixture_plan"]}
        for row in self.payload["obligations"]:
            if row["completion_state"] != "gap":
                continue
            has_question = bool(row.get("unresolved_question"))
            has_plan = row["obligation_id"] in planned
            self.assertTrue(
                has_question or has_plan,
                msg=f"{row['obligation_id']} gap without question or fixture plan",
            )

    def test_deferred_concepts_not_in_implemented_kinds(self) -> None:
        implemented = set(self.payload["phase1_boundary"]["implemented_record_kinds"])
        for item in self.payload["phase1_boundary"]["deferred_first_class_kernel_concepts"]:
            kind = item["concept"].lower().replace("typedefinition", "type_definition")
            if kind.endswith("definition"):
                continue
            self.assertNotIn(kind, implemented, msg=item["concept"])


if __name__ == "__main__":
    unittest.main()
