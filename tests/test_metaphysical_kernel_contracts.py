from __future__ import annotations

import json
import unittest
from pathlib import Path

from conversation_os.metaphysical_kernel import (
    FRAMEWORK_SECTIONS,
    BranchMembership,
    Claim,
    ClaimProposition,
    KernelRecordEnvelope,
    ProfileConformanceResult,
    ProfileDefinition,
    State,
    StateCommitment,
)
from conversation_os.metaphysical_kernel_contracts import (
    validate_claim,
    validate_envelope,
    validate_fixture_bundle,
    validate_lifecycle_independence,
    validate_profile_conformance,
    validate_profile_definition,
    validate_state,
    validate_state_commitment,
)


FIXTURES_DIR = Path(__file__).parent / "fixtures" / "metaphysical_kernel"


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURES_DIR / name).read_text(encoding="utf-8"))


class MetaphysicalKernelContractTestCase(unittest.TestCase):
    def test_framework_sections_cover_task001_contracts(self) -> None:
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

    def test_valid_minimal_capture_fixture(self) -> None:
        errors = validate_fixture_bundle(_load_fixture("valid_minimal_capture.json"))
        self.assertEqual(errors, [])

    def test_valid_state_commitment_path_fixture(self) -> None:
        errors = validate_fixture_bundle(_load_fixture("valid_state_commitment_path.json"))
        self.assertEqual(errors, [])

    def test_invalid_claim_without_membership_fixture(self) -> None:
        errors = validate_fixture_bundle(_load_fixture("invalid_claim_without_membership.json"))
        self.assertTrue(any("BranchMembership" in error for error in errors))

    def test_invalid_state_without_commitment_fixture(self) -> None:
        errors = validate_fixture_bundle(_load_fixture("invalid_state_without_commitment.json"))
        self.assertTrue(any("StateCommitment" in error for error in errors))

    def test_invalid_profile_redefines_kernel_fixture(self) -> None:
        errors = validate_fixture_bundle(_load_fixture("invalid_profile_redefines_kernel.json"))
        self.assertTrue(any("redefines kernel semantics" in error for error in errors))

    def test_lifecycle_axes_must_remain_orthogonal(self) -> None:
        envelope = KernelRecordEnvelope(
            id="env_bad",
            record_kind="claim",
            type_id="core:claim",
            created_at="2026-07-12T00:00:00Z",
            created_by="test",
            provenance_id="prov_1",
            maturity_status="candidate",
            epistemic_status="candidate",
            governance_status="local",
        )
        errors = validate_lifecycle_independence(envelope)
        self.assertTrue(errors)

    def test_state_requires_explicit_commitment(self) -> None:
        state = State(
            envelope=KernelRecordEnvelope(
                id="st_1",
                record_kind="state",
                type_id="workspace:initiative",
                created_at="2026-07-12T00:00:00Z",
                created_by="test",
                provenance_id="prov_1",
                maturity_status="structured",
                epistemic_status="supported",
                governance_status="local",
            ),
            subject_refs=["ref_1"],
            state_type="workspace:initiative",
            value="low",
            value_type="ordinal",
            valid_scope_id="scope_1",
        )
        membership = BranchMembership(
            envelope=KernelRecordEnvelope(
                id="bm_1",
                record_kind="branch_membership",
                type_id="core:branch_membership",
                created_at="2026-07-12T00:00:00Z",
                created_by="test",
                provenance_id="prov_1",
                maturity_status="structured",
                epistemic_status="not_applicable",
                governance_status="local",
            ),
            record_id="st_1",
            branch_id="branch_a",
            membership_kind="asserted",
            effective_scope_id="scope_1",
            introduced_by="test",
            membership_provenance_id="prov_1",
        )
        errors = validate_state(state, commitments=[], memberships=[membership])
        self.assertTrue(any("StateCommitment" in error for error in errors))

    def test_profile_conformance_failed_result_requires_violations(self) -> None:
        result = ProfileConformanceResult(
            envelope=KernelRecordEnvelope(
                id="pcr_1",
                record_kind="profile_conformance_result",
                type_id="core:profile_conformance_result",
                created_at="2026-07-12T00:00:00Z",
                created_by="test",
                provenance_id="prov_1",
                maturity_status="structured",
                epistemic_status="not_applicable",
                governance_status="local",
            ),
            profile_definition_id="profile:field",
            profile_version="1.0.0",
            evaluated_record_id="record_1",
            passed=False,
            violations=[],
        )
        errors = validate_profile_conformance(result)
        self.assertTrue(any("failed result must include violations" in error for error in errors))

    def test_claim_and_state_record_kinds_are_distinct(self) -> None:
        claim = Claim(
            envelope=KernelRecordEnvelope(
                id="cl_1",
                record_kind="claim",
                type_id="core:claim",
                created_at="2026-07-12T00:00:00Z",
                created_by="test",
                provenance_id="prov_1",
                maturity_status="differentiating",
                epistemic_status="candidate",
                governance_status="local",
            ),
            proposition=ClaimProposition(predicate="inhibits", arguments=["a", "b"]),
            claimant="test",
            branch_id="branch_a",
            scope_id="scope_a",
        )
        membership = BranchMembership(
            envelope=KernelRecordEnvelope(
                id="bm_claim",
                record_kind="branch_membership",
                type_id="core:branch_membership",
                created_at="2026-07-12T00:00:00Z",
                created_by="test",
                provenance_id="prov_1",
                maturity_status="structured",
                epistemic_status="not_applicable",
                governance_status="local",
            ),
            record_id="cl_1",
            branch_id="branch_a",
            membership_kind="asserted",
            effective_scope_id="scope_a",
            introduced_by="test",
            membership_provenance_id="prov_1",
        )
        self.assertEqual(validate_claim(claim, [membership]), [])

        commitment = StateCommitment(
            envelope=KernelRecordEnvelope(
                id="sc_1",
                record_kind="state_commitment",
                type_id="core:state_commitment",
                created_at="2026-07-12T00:00:00Z",
                created_by="test",
                provenance_id="prov_1",
                maturity_status="structured",
                epistemic_status="supported",
                governance_status="review_required",
            ),
            source_claim_ids=["cl_1"],
            resulting_state_id="st_1",
            branch_id="branch_a",
            scope_id="scope_a",
            commitment_kind="user_confirmed",
            responsible_actor="test",
            commitment_provenance_id="prov_1",
        )
        self.assertEqual(validate_state_commitment(commitment), [])

    def test_profile_definition_rejects_kernel_redefinition(self) -> None:
        profile = ProfileDefinition(
            envelope=KernelRecordEnvelope(
                id="profile_1",
                record_kind="profile_definition",
                type_id="profile:field",
                created_at="2026-07-12T00:00:00Z",
                created_by="test",
                provenance_id="prov_1",
                maturity_status="structured",
                epistemic_status="not_applicable",
                governance_status="review_required",
            ),
            profile_id="profile:field",
            profile_version="1.0.0",
            purpose="test",
            kernel_records_used=["source_fragment"],
            profile_record_types=["field_record"],
            profile_dependencies=[],
            invariants=[],
            steward="test",
            forbidden_kernel_redefinitions=["claim_is_state"],
        )
        errors = validate_profile_definition(profile)
        self.assertTrue(errors)

    def test_envelope_requires_provenance_id(self) -> None:
        envelope = KernelRecordEnvelope(
            id="env_1",
            record_kind="source_fragment",
            type_id="core:source_fragment",
            created_at="2026-07-12T00:00:00Z",
            created_by="test",
            provenance_id="",
            maturity_status="raw",
            epistemic_status="not_applicable",
            governance_status="local",
        )
        errors = validate_envelope(envelope)
        self.assertTrue(any("provenance_id is required" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
