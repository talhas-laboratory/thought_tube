from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from conversation_os.metaphysical_kernel import KernelRecordEnvelope, ProfileDefinition
from conversation_os.metaphysical_kernel_profile_registry import (
    FIELD_FORMATION_PROFILE_ID,
    ProfileRegistry,
    ProfileRegistryError,
    build_field_formation_profile_v1,
)
from conversation_os.metaphysical_kernel_runtime import FoundationRuntime, run_vertical_slice


FIXTURES_DIR = Path(__file__).parent / "fixtures" / "metaphysical_kernel"


class MetaphysicalKernelProfileRegistryTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self._tmpdir.name)
        self.runtime = FoundationRuntime(self.root, actor="service:profile_registry")
        self.registry = ProfileRegistry(self.runtime)

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def _event(self) -> dict:
        return {
            "event_id": "event-profile-001",
            "session_id": "session-profile-001",
            "timestamp": "2026-07-12T13:00:00+00:00",
            "actor": "user:test",
            "kind": "request",
            "content": "Profile registry fixture event.",
        }

    def test_bootstrap_registers_field_formation_profile(self) -> None:
        profile = self.registry.bootstrap_field_formation_profile()
        self.assertEqual(profile["profile_id"], FIELD_FORMATION_PROFILE_ID)
        self.assertEqual(profile["profile_version"], "1.0.0")
        fetched = self.registry.get_profile(FIELD_FORMATION_PROFILE_ID)
        self.assertIsNotNone(fetched)
        assert fetched is not None
        self.assertIn("field", fetched.profile_record_types)

    def test_profile_cannot_redefine_kernel_semantics(self) -> None:
        fragment = self.runtime.capture_source_fragment(
            content_pointer="memory://test",
            author_or_origin="test",
            integrity_hash="sha256:test",
        )
        profile = build_field_formation_profile_v1(
            envelope_id="profile_bad",
            provenance_id=fragment["envelope"]["provenance_id"],
        )
        profile.forbidden_kernel_redefinitions = ["claim_is_state"]
        errors = self.registry.validate_registration(profile)
        self.assertTrue(any("redefines kernel semantics" in error for error in errors))

    def test_profile_record_types_cannot_duplicate_kernel_kinds(self) -> None:
        fragment = self.runtime.capture_source_fragment(
            content_pointer="memory://test",
            author_or_origin="test",
            integrity_hash="sha256:test2",
        )
        profile = build_field_formation_profile_v1(
            envelope_id="profile_parallel",
            provenance_id=fragment["envelope"]["provenance_id"],
        )
        profile.profile_record_types = ["claim", "field"]
        errors = self.registry.validate_registration(profile)
        self.assertTrue(any("duplicate kernel record kinds" in error for error in errors))

    def test_dependency_cycle_is_rejected(self) -> None:
        self.registry.bootstrap_field_formation_profile()
        fragment = self.runtime.capture_source_fragment(
            content_pointer="memory://cycle",
            author_or_origin="test",
            integrity_hash="sha256:cycle",
        )
        prov_id = fragment["envelope"]["provenance_id"]

        profile_a = ProfileDefinition(
            envelope=KernelRecordEnvelope(
                id="profile_a",
                record_kind="profile_definition",
                type_id="profile:a",
                created_at="2026-07-12T00:00:00Z",
                created_by="test",
                provenance_id=prov_id,
                maturity_status="structured",
                epistemic_status="not_applicable",
                governance_status="review_required",
            ),
            profile_id="profile:a",
            profile_version="1.0.0",
            purpose="a",
            kernel_records_used=["source_fragment"],
            profile_record_types=["a_record"],
            profile_dependencies=["profile:b"],
            invariants=[],
            steward="test",
        )
        profile_b = ProfileDefinition(
            envelope=KernelRecordEnvelope(
                id="profile_b",
                record_kind="profile_definition",
                type_id="profile:b",
                created_at="2026-07-12T00:00:00Z",
                created_by="test",
                provenance_id=prov_id,
                maturity_status="structured",
                epistemic_status="not_applicable",
                governance_status="review_required",
            ),
            profile_id="profile:b",
            profile_version="1.0.0",
            purpose="b",
            kernel_records_used=["source_fragment"],
            profile_record_types=["b_record"],
            profile_dependencies=[],
            invariants=[],
            steward="test",
        )
        self.registry.register(profile_b)
        self.registry.register(profile_a)
        profile_b_cycle = ProfileDefinition(
            envelope=profile_b.envelope,
            profile_id="profile:b",
            profile_version="1.1.0",
            purpose="b",
            kernel_records_used=["source_fragment"],
            profile_record_types=["b_record"],
            profile_dependencies=["profile:a"],
            invariants=[],
            steward="test",
        )
        errors = self.registry.validate_registration(profile_b_cycle)
        self.assertTrue(any("cycle" in error for error in errors))

    def test_application_binding_requires_profile_invariants(self) -> None:
        self.registry.bootstrap_field_formation_profile()
        with self.assertRaises(ProfileRegistryError):
            self.registry.bind_application(
                application_id="app:inner_world",
                profile_id=FIELD_FORMATION_PROFILE_ID,
                profile_version="1.0.0",
                required_invariants=["no_claim_without_branch_membership", "nonexistent_invariant"],
            )

    def test_application_binding_cannot_weaken_invariants(self) -> None:
        self.registry.bootstrap_field_formation_profile()
        with self.assertRaises(ProfileRegistryError):
            self.registry.bind_application(
                application_id="app:weak",
                profile_id=FIELD_FORMATION_PROFILE_ID,
                profile_version="1.0.0",
                required_invariants=[],
            )

    def test_conformance_passes_after_valid_vertical_slice(self) -> None:
        self.registry.bootstrap_field_formation_profile()
        run_vertical_slice(
            self.root,
            session_event=self._event(),
            referent_label="Profile subject",
            claim_predicate="relates",
            claim_arguments=["profile"],
        )
        binding = self.registry.bind_application(
            application_id="app:world_studio",
            profile_id=FIELD_FORMATION_PROFILE_ID,
            profile_version="1.0.0",
            required_invariants=[
                "no_claim_without_branch_membership",
                "no_state_without_state_commitment",
            ],
        )
        result = self.registry.evaluate_conformance(profile_id=FIELD_FORMATION_PROFILE_ID)
        self.assertTrue(result.passed)
        self.assertEqual(binding.profile_id, FIELD_FORMATION_PROFILE_ID)

    def test_profile_upgrade_identifies_stale_records(self) -> None:
        self.registry.bootstrap_field_formation_profile()
        fragment = self.runtime.capture_source_fragment(
            content_pointer="memory://upgrade",
            author_or_origin="test",
            integrity_hash="sha256:upgrade",
        )
        prov_id = fragment["envelope"]["provenance_id"]
        v1_1 = build_field_formation_profile_v1(
            envelope_id="profile_ff_v1_1",
            provenance_id=prov_id,
        )
        v1_1.profile_version = "1.1.0"
        v1_1.profile_record_types = ["field", "formation"]
        self.registry.register(v1_1)

        report = self.registry.plan_upgrade(
            profile_id=FIELD_FORMATION_PROFILE_ID,
            from_version="1.0.0",
            to_version="1.1.0",
            active_profile_records={
                "hold-001": "hold",
                "formation-001": "formation",
            },
        )
        self.assertIn("hold", report.removed_record_types)
        self.assertIn("hold-001", report.stale_record_ids)
        self.assertNotIn("formation-001", report.stale_record_ids)

    def test_fixture_metadata_matches_builtin_profile(self) -> None:
        metadata = json.loads(
            (FIXTURES_DIR / "profile_field_formation_v1_0_0.json").read_text(encoding="utf-8")
        )
        self.registry.bootstrap_field_formation_profile()
        profile = self.registry.get_profile(FIELD_FORMATION_PROFILE_ID)
        assert profile is not None
        self.assertEqual(profile.profile_id, metadata["profile_id"])
        self.assertEqual(profile.profile_version, metadata["profile_version"])
        self.assertEqual(profile.profile_record_types, metadata["profile_record_types"])


if __name__ == "__main__":
    unittest.main()
