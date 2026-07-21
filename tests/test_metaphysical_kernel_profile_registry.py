from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from conversation_os.metaphysical_kernel import KernelRecordEnvelope, ProfileDefinition
from conversation_os.metaphysical_kernel_profile_registry import (
    COMPOSITION_PROFILE_ID,
    FIELD_FORMATION_PROFILE_ID,
    ProfileRegistry,
    ProfileRegistryError,
    QUALITY_INSTANCE_PROFILE_ID,
    build_field_formation_profile_v1,
    validate_quality_instance_contract,
    validate_quality_refinement_contract,
    validate_composition_bundle_contract,
    validate_composition_assertion_contract,
    validate_system_boundary_contract,
    validate_role_assignment_contract,
    validate_influence_assessment_contract,
    validate_role_influence_bundle_contract,
    validate_shape_contract,
    validate_cybernetic_contract,
    validate_cybernetic_bundle_contract,
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

    def test_bootstrap_registers_quality_instance_profile(self) -> None:
        profile = self.registry.bootstrap_quality_instance_profile()
        self.assertEqual(profile["profile_id"], QUALITY_INSTANCE_PROFILE_ID)
        self.assertEqual(profile["profile_record_types"], ["quality_instance", "quality_refinement"])
        self.assertIn("relation_instance", profile["kernel_records_used"])
        self.assertNotIn("type_definition", profile["kernel_records_used"])

    def test_quality_instance_contract_requires_grounded_basis(self) -> None:
        valid = {
            "record_type": "quality_instance",
            "id": "quality-instance:clarity",
            "bearer_referent_id": "referent:organism",
            "quality_definition_id": "type:clarity",
            "scope_id": "scope:present",
            "branch_id": "branch:main",
            "provenance_id": "provenance:observation",
            "basis_kind": "claim",
            "basis_record_id": "claim:clarity",
        }
        self.assertEqual(validate_quality_instance_contract(valid), [])
        invalid = dict(valid)
        invalid["basis_kind"] = "value"
        invalid["bearer_referent_id"] = ""
        errors = validate_quality_instance_contract(invalid)
        self.assertTrue(any("basis_kind" in error for error in errors))
        self.assertTrue(any("bearer_referent_id" in error for error in errors))

    def test_optional_quality_refinement_contract_preserves_lineage(self) -> None:
        refinement = {
            "record_type": "quality_refinement",
            "id": "quality-refinement:clarity-to-subsystem",
            "source_quality_instance_id": "quality-instance:clarity",
            "relation_instance_id": "relation:refines-to",
            "relation_type": "refines_to",
            "reified_referent_id": "referent:clarity-subsystem",
        }
        self.assertEqual(validate_quality_refinement_contract(refinement), [])
        broken = dict(refinement)
        broken["relation_instance_id"] = ""
        self.assertTrue(any("relation_instance_id" in error for error in validate_quality_refinement_contract(broken)))

    def test_quality_instance_fixture_matches_contracts(self) -> None:
        metadata = json.loads(
            (FIXTURES_DIR / "profile_quality_instance_v1_0_0.json").read_text(encoding="utf-8")
        )
        profile = self.registry.bootstrap_quality_instance_profile()
        for key in (
            "profile_id",
            "profile_version",
            "kernel_records_used",
            "profile_record_types",
            "profile_dependencies",
            "invariants",
            "steward",
        ):
            self.assertEqual(profile[key], metadata[key])
        instances = metadata["quality_instances"]
        self.assertEqual(len(instances), 2)
        self.assertEqual(instances[0]["quality_definition_id"], instances[1]["quality_definition_id"])
        self.assertNotEqual(instances[0]["scope_id"], instances[1]["scope_id"])
        self.assertNotEqual(instances[0]["branch_id"], instances[1]["branch_id"])
        self.assertNotEqual(instances[0]["basis_kind"], instances[1]["basis_kind"])
        for instance in instances:
            self.assertEqual(validate_quality_instance_contract(instance), [])
        self.assertEqual(validate_quality_refinement_contract(metadata["quality_refinement"]), [])

    def test_bootstrap_registers_composition_profile_after_quality_profile(self) -> None:
        profile = self.registry.bootstrap_composition_profile()
        self.assertEqual(profile["profile_id"], COMPOSITION_PROFILE_ID)
        self.assertEqual(profile["profile_record_types"], ["system_boundary", "composition_assertion"])
        self.assertEqual(profile["profile_dependencies"], [QUALITY_INSTANCE_PROFILE_ID])
        self.assertIsNotNone(self.registry.get_profile(QUALITY_INSTANCE_PROFILE_ID))

    def test_composition_contract_requires_bounded_non_self_relation(self) -> None:
        boundary = {
            "record_type": "system_boundary",
            "id": "boundary:forest-functional",
            "whole_referent_id": "referent:forest",
            "boundary_rule": "functional",
            "identity_rule": "whole_preserved",
            "scale": "ecosystem",
            "scope_id": "scope:seasonal-forest",
            "branch_id": "branch:field-observation",
            "provenance_id": "provenance:field-observation",
        }
        assertion = {
            "record_type": "composition_assertion",
            "id": "composition:forest-mycorrhiza",
            "whole_referent_id": "referent:forest",
            "constituent_referent_id": "referent:mycorrhizal-network",
            "composition_kind": "functional_component",
            "boundary_id": boundary["id"],
            "scope_id": boundary["scope_id"],
            "branch_id": boundary["branch_id"],
            "provenance_id": boundary["provenance_id"],
            "relation_instance_id": "relation:forest-mycorrhiza",
            "source_quality_instance_id": "quality-instance:immune-response-observed",
        }
        self.assertEqual(validate_system_boundary_contract(boundary), [])
        self.assertEqual(validate_composition_assertion_contract(assertion), [])
        invalid = dict(assertion)
        invalid["constituent_referent_id"] = invalid["whole_referent_id"]
        self.assertTrue(any("own constituent" in error for error in validate_composition_assertion_contract(invalid)))

    def test_composition_fixture_supports_multiple_kinds_and_recursive_systemhood(self) -> None:
        metadata = json.loads(
            (FIXTURES_DIR / "profile_composition_v1_0_0.json").read_text(encoding="utf-8")
        )
        profile = self.registry.bootstrap_composition_profile()
        for key in ("profile_id", "profile_version", "kernel_records_used", "profile_record_types", "profile_dependencies", "invariants", "steward"):
            self.assertEqual(profile[key], metadata[key])
        for boundary in metadata["system_boundaries"]:
            self.assertEqual(validate_system_boundary_contract(boundary), [])
        for assertion in metadata["composition_assertions"]:
            self.assertEqual(validate_composition_assertion_contract(assertion), [])
        self.assertEqual(
            validate_composition_bundle_contract(
                metadata["system_boundaries"], metadata["composition_assertions"]
            ),
            [],
        )
        self.assertEqual(
            {assertion["composition_kind"] for assertion in metadata["composition_assertions"]},
            {"material_part", "functional_component", "membership", "social_constitution"},
        )
        self.assertTrue(any(boundary["whole_referent_id"] == "referent:mycorrhizal-network" for boundary in metadata["system_boundaries"]))
        self.assertTrue(any(assertion.get("source_quality_instance_id") for assertion in metadata["composition_assertions"]))

    def test_composition_bundle_rejects_cycles_and_boundary_mismatches(self) -> None:
        boundaries = [
            {
                "record_type": "system_boundary", "id": "boundary:a", "whole_referent_id": "referent:a",
                "boundary_rule": "functional", "identity_rule": "whole_preserved", "scale": "system",
                "scope_id": "scope:one", "branch_id": "branch:one", "provenance_id": "provenance:one",
            },
            {
                "record_type": "system_boundary", "id": "boundary:b", "whole_referent_id": "referent:b",
                "boundary_rule": "functional", "identity_rule": "whole_preserved", "scale": "subsystem",
                "scope_id": "scope:one", "branch_id": "branch:one", "provenance_id": "provenance:one",
            },
        ]
        assertions = [
            {
                "record_type": "composition_assertion", "id": "composition:a-b", "whole_referent_id": "referent:a",
                "constituent_referent_id": "referent:b", "composition_kind": "functional_component",
                "boundary_id": "boundary:a", "scope_id": "scope:one", "branch_id": "branch:one",
                "provenance_id": "provenance:one", "relation_instance_id": "relation:a-b",
            },
            {
                "record_type": "composition_assertion", "id": "composition:b-a", "whole_referent_id": "referent:b",
                "constituent_referent_id": "referent:a", "composition_kind": "functional_component",
                "boundary_id": "boundary:b", "scope_id": "scope:wrong", "branch_id": "branch:one",
                "provenance_id": "provenance:one", "relation_instance_id": "relation:b-a",
            },
        ]
        errors = validate_composition_bundle_contract(boundaries, assertions)
        self.assertTrue(any("cycle" in error for error in errors))
        self.assertTrue(any("scope" in error for error in errors))

    def test_role_and_weighted_influence_contracts(self) -> None:
        role = {"record_type":"role_assignment","id":"role:network","participant_ref":"referent:network","host_ref":"referent:forest","role_type":"regulator","mechanism":"nutrient-signaling","scope_id":"scope:forest","temporal_scope":"seasonal","branch_id":"branch:observed","provenance_id":"provenance:field"}
        assessment = {"record_type":"influence_assessment","id":"influence:network","role_assignment_id":"role:network","target_ref":"quality:resilience","direction":"stabilizes","mechanism":"nutrient-signaling","assessment_basis":"estimated","uncertainty":"interval","confidence":0.8,"scope_id":"scope:forest","temporal_scope":"seasonal","branch_id":"branch:observed","provenance_id":"provenance:field","magnitude":0.4,"magnitude_scale":"normalized","magnitude_unit":"unitless"}
        self.assertEqual(validate_role_assignment_contract(role), [])
        self.assertEqual(validate_influence_assessment_contract(assessment), [])
        self.assertEqual(validate_role_influence_bundle_contract([role], [assessment]), [])
        broken = dict(assessment); broken["magnitude_unit"] = ""
        self.assertTrue(any("magnitude_unit" in e for e in validate_influence_assessment_contract(broken)))

    def test_role_fixture_preserves_identity_across_time_and_scope(self) -> None:
        fixture = json.loads((FIXTURES_DIR / "profile_role_assignment_v1_0_0.json").read_text())
        roles = fixture["role_assignments"]
        self.assertEqual(roles[0]["participant_ref"], roles[1]["participant_ref"])
        self.assertEqual(roles[0]["host_ref"], roles[1]["host_ref"])
        self.assertNotEqual(roles[0]["scope_id"], roles[1]["scope_id"])
        self.assertNotEqual(roles[0]["temporal_scope"], roles[1]["temporal_scope"])
        self.assertEqual(validate_role_influence_bundle_contract(roles, fixture["influence_assessments"]), [])

    def test_shape_contract_includes_relations_projection_and_signature(self) -> None:
        core={"record_type":"shape_core","id":"core","focal_ref":"referent:forest","scope_id":"scope:forest","branch_id":"branch:one","provenance_id":"prov","relation_refs":["rel:one"]}
        view={"record_type":"shape_view","id":"view","shape_core_id":"core","semantic_address":{"dimension":"functional"},"abstraction_contract":"roles only","relation_refs":["rel:one"],"projection":{"nodes":["forest"],"edges":["rel:one"],"groups":["forest"]},"comparison_signature":{"role_relation_summary":["regulator->stabilizes"]}}
        record={"record_type":"shape_record","id":"record","shape_core_id":"core","shape_view_id":"view","input_refs":["role:one"],"derivation_method":"manual","provenance_id":"prov","reproducibility":"interpretative"}
        composite={"record_type":"composite_shape","id":"composite","dimensional_shape_refs":["record"],"coupling_refs":["rel:one"],"provenance_id":"prov"}
        for payload,kind in ((core,"shape_core"),(view,"shape_view"),(record,"shape_record"),(composite,"composite_shape")):
            self.assertEqual(validate_shape_contract(payload,kind), [])

    def _cybernetic_records(self) -> list[dict]:
        context = {"scope_id": "scope:forest", "temporal_scope": "seasonal", "branch_id": "branch:observed", "provenance_id": "provenance:field"}
        return [
            {"record_type": "state_variable", "id": "variable:resilience", "target_ref": "quality:resilience", "value_type": "number", "value_domain": "normalized_index", "unit": "index", "observation_basis": "canopy-survey", "sampling_interval": "P7D", "epistemic_status": "estimated", "lower_bound": 0.0, "upper_bound": 1.0, **context},
            {"record_type": "signal", "id": "signal:nutrient", "source_ref": "referent:network", "target_ref": "variable:resilience", "payload_type": "nutrient_access", "payload_unit": "index", "mechanism": "mycorrhizal_transfer", "delay": "P1D", "epistemic_status": "hypothesized", **context},
            {"record_type": "setpoint", "id": "setpoint:resilience", "variable_ref": "variable:resilience", "target_range": "[0.6,1.0]", "priority": 1, **context},
            {"record_type": "regulator", "id": "regulator:network", "controller_ref": "referent:network", "observed_variable_refs": ["variable:resilience"], "action_channel_refs": ["signal:nutrient"], "setpoint_refs": ["setpoint:resilience"], "policy_ref": "policy:local-response", "authority_scope": "scope:forest", **context},
            {"record_type": "feedback_loop", "id": "loop:resource-compensation", "variable_refs": ["variable:resilience"], "signal_refs": ["signal:nutrient"], "regulator_refs": ["regulator:network"], "polarity": "negative", "mechanism": "resource compensation", "constraint_ref": "constraint:water", "oscillation_risk": "medium", **context},
            {"record_type": "disturbance", "id": "disturbance:drought", "target_variable_refs": ["variable:resilience"], "mechanism": "water deficit", "magnitude_basis": "rainfall anomaly", **context},
            {"record_type": "viability_condition", "id": "viability:resilience", "variable_ref": "variable:resilience", "threshold_or_range": "[0.4,1.0]", "recovery_condition": "three consecutive adequate-water intervals", "failure_interpretation": "loss of canopy function", **context},
            {"record_type": "dynamic_model_extension", "id": "extension:resilience", "shape_ref": "shape:forest-regulation", "input_variable_refs": ["variable:resilience"], "output_variable_refs": ["variable:resilience"], "timing_model_ref": "timing:daily", "uncertainty_model_ref": "uncertainty:interval", "execution_status": "approved", "equation_refs": ["equation:one"], "update_rule_refs": ["rule:one"], "compiler_ref": "compiler:future", "validation_ref": "validation:scenario-set", "approval_ref": "approval:human", "provenance_id": "provenance:field"},
        ]

    def test_cybernetics_bundle_describes_closed_regulation_without_simulating(self) -> None:
        rows = self._cybernetic_records()
        for row in rows:
            self.assertEqual(validate_cybernetic_contract(row, row["record_type"]), [])
        self.assertEqual(validate_cybernetic_bundle_contract(rows), [])

    def test_cybernetics_fixture_matches_registered_contract(self) -> None:
        fixture = json.loads((FIXTURES_DIR / "profile_cybernetics_v1_0_0.json").read_text())
        profile = self.registry.bootstrap_cybernetics_profile()
        for key in ("profile_id", "profile_version", "kernel_records_used", "profile_record_types", "profile_dependencies", "invariants", "steward"):
            self.assertEqual(profile[key], fixture[key])

    def test_cybernetics_bundle_rejects_open_loops_unit_conflicts_and_unapproved_execution(self) -> None:
        rows = self._cybernetic_records()
        rows[1]["payload_unit"] = "mg"
        rows[1]["delay"] = "-1"
        rows[3]["action_channel_refs"] = ["signal:missing"]
        rows[-1].pop("approval_ref")
        errors = validate_cybernetic_bundle_contract(rows)
        self.assertTrue(any("delay" in error for error in errors))
        self.assertTrue(any("unknown signal" in error for error in errors))
        self.assertTrue(any("closed observation-action" in error for error in errors))
        self.assertTrue(any("approval_ref" in error for error in errors))

    def test_cybernetics_bundle_rejects_context_drift_and_conflicting_setpoints(self) -> None:
        rows = self._cybernetic_records()
        second_setpoint = dict(rows[2])
        second_setpoint["id"] = "setpoint:resilience-conflict"
        second_setpoint["target_range"] = "[0.1,0.3]"
        rows.append(second_setpoint)
        rows[1]["branch_id"] = "branch:simulated"
        errors = validate_cybernetic_bundle_contract(rows)
        self.assertTrue(any("branch_id conflicts" in error for error in errors))
        self.assertTrue(any("setpoints conflict" in error for error in errors))

    def test_cybernetics_bundle_reports_invalid_setpoint_priority_without_crashing(self) -> None:
        rows = self._cybernetic_records()
        rows[2]["priority"] = "urgent"
        errors = validate_cybernetic_bundle_contract(rows)
        self.assertTrue(any("priority" in error for error in errors))

    def test_cybernetics_bundle_rejects_regulator_context_drift_from_observation_and_goal(self) -> None:
        rows = self._cybernetic_records()
        rows[3]["branch_id"] = "branch:simulated"
        errors = validate_cybernetic_bundle_contract(rows)
        self.assertTrue(any("regulator:network branch_id conflicts with state_variable" in error for error in errors))
        self.assertTrue(any("regulator:network branch_id conflicts with setpoint" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
