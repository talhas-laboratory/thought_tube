"""KERNEL-004 kernel conformance suite — obligation coverage and adversarial inventory."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from conversation_os.metaphysical_kernel_contracts import validate_fixture_bundle


ROOT = Path(__file__).resolve().parents[1]
FIXTURES_DIR = ROOT / "tests" / "fixtures" / "metaphysical_kernel"
MIGRATION_FIXTURES_DIR = ROOT / "tests" / "fixtures" / "migration"
OBLIGATIONS_PATH = (
    ROOT
    / "docs"
    / "workspaces"
    / "metaphysical-kernel-ontology"
    / "derived"
    / "KERNEL_ATOMIC_OBLIGATIONS.json"
)
COVERAGE_PATH = (
    ROOT
    / "docs"
    / "workspaces"
    / "metaphysical-kernel-ontology"
    / "derived"
    / "KERNEL_CONFORMANCE_COVERAGE.json"
)

REJECTED_KERNEL_FIXTURES = [
    "invalid_claim_without_membership.json",
    "invalid_state_branch_membership_mismatch.json",
    "invalid_state_scope_membership_mismatch.json",
    "invalid_state_missing_commitment_link.json",
    "invalid_state_unknown_source_claim.json",
    "invalid_state_without_commitment.json",
    "invalid_profile_redefines_kernel.json",
    "invalid_provenance_no_source.json",
    "invalid_lifecycle_axis_collapse.json",
]

GAP_KERNEL_FIXTURES = {
    "invalid_maturity_transition.json": "KERNEL-22-LIFECYCLE-TRANSITIONS",
    "commitment_revocation_staleness.json": "KERNEL-5.16-STALENESS-PROPAGATION",
}

FORBIDDEN_INTERPRETATION_FIXTURES = {
    "claim_is_state": ["invalid_profile_redefines_kernel.json", "invalid_state_without_commitment.json"],
    "state_is_claim": ["invalid_state_without_commitment.json"],
    "universal_branch_id": [],
    "single_status_field": ["invalid_lifecycle_axis_collapse.json"],
    "product_specific_kernel_fields": [],
    "parallel_canonical_store": [],
}

SUITE_MODULES = [
    "tests.test_kernel_atomic_obligations",
    "tests.test_kernel_conformance_suite",
    "tests.test_metaphysical_kernel_contracts",
    "tests.test_metaphysical_kernel_migration",
    "tests.test_metaphysical_kernel_runtime",
    "tests.test_metaphysical_kernel_profile_registry",
    "tests.test_metaphysical_kernel_application_sdk",
]


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _bundle_payload(fixture: dict) -> dict:
    return {key: value for key, value in fixture.items() if not key.startswith("_")}


class KernelConformanceSuiteTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.obligations = _load_json(OBLIGATIONS_PATH)
        cls.coverage = _load_json(COVERAGE_PATH)

    def test_coverage_index_matches_obligation_count(self) -> None:
        obligation_ids = {row["obligation_id"] for row in self.obligations["obligations"]}
        covered_ids = {row["obligation_id"] for row in self.coverage["obligations"]}
        self.assertEqual(obligation_ids, covered_ids)

    def test_verified_obligations_have_evidence(self) -> None:
        for row in self.obligations["obligations"]:
            if row["completion_state"] not in {"verified", "phase1_minimal", "implemented"}:
                continue
            self.assertTrue(
                row.get("tests_fixtures"),
                msg=f"{row['obligation_id']} missing tests_fixtures",
            )

    def test_gap_obligations_have_fixture_plan(self) -> None:
        planned = {item["gap_obligation_id"] for item in self.obligations["validator_fixture_plan"]}
        for row in self.obligations["obligations"]:
            if row["completion_state"] != "gap":
                continue
            self.assertIn(row["obligation_id"], planned)

    def test_adversarial_kernel_fixtures_are_rejected(self) -> None:
        for name in REJECTED_KERNEL_FIXTURES:
            errors = validate_fixture_bundle(_bundle_payload(_load_json(FIXTURES_DIR / name)))
            self.assertTrue(errors, msg=f"{name} should be rejected: {errors}")

    def test_gap_fixtures_document_known_limits(self) -> None:
        for name, obligation_id in GAP_KERNEL_FIXTURES.items():
            fixture = _load_json(FIXTURES_DIR / name)
            gap = fixture.get("_conformance_gap", {})
            self.assertEqual(gap.get("obligation_id"), obligation_id)
            coverage_row = next(
                row for row in self.coverage["obligations"] if row["obligation_id"] == obligation_id
            )
            self.assertEqual(coverage_row["completion_state"], "gap")
            self.assertFalse(coverage_row["adversarial_reject_expected"])

    def test_forbidden_interpretations_have_regression_fixtures(self) -> None:
        forbidden = set(self.obligations["forbidden_interpretations"])
        for key, fixtures in FORBIDDEN_INTERPRETATION_FIXTURES.items():
            self.assertIn(key, forbidden)
            if fixtures:
                for name in fixtures:
                    self.assertTrue((FIXTURES_DIR / name).is_file(), msg=name)

    def test_migration_invalid_fixture_rejected(self) -> None:
        bundle = _load_json(MIGRATION_FIXTURES_DIR / "invalid_claim_as_state.json")["inject_kernel_bundle"]
        errors = validate_fixture_bundle(bundle)
        self.assertTrue(errors)
        self.assertTrue(any("StateCommitment" in error for error in errors))

    def test_suite_module_inventory(self) -> None:
        self.assertEqual(self.coverage["suite_modules"], SUITE_MODULES)


if __name__ == "__main__":
    unittest.main()
