from __future__ import annotations

import json
import unittest
from pathlib import Path

from conversation_os.metaphysical_kernel_contracts import validate_fixture_bundle
from conversation_os.metaphysical_kernel_migration import (
    MAPPING_AUTHORITY,
    MappingRule,
    SOURCE_FAMILIES,
    migrate_source_fixture,
    validate_migration_fixture,
    validate_migration_result,
    _analogy_identity_violations,
    _referent_collapse_violations,
    _states_without_commitment,
)


FIXTURES_DIR = Path(__file__).parent / "fixtures" / "migration"
VALID_FIXTURES = [
    "mtsf_minimal_assertion.json",
    "mtsf_uncertain_identity.json",
    "thoughtshape_stateclaim_hold.json",
    "sds_signal_dilution.json",
    "conversation_os_minimal_session.json",
]


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURES_DIR / name).read_text(encoding="utf-8"))


class MetaphysicalKernelMigrationTestCase(unittest.TestCase):
    def test_mapping_authority_points_at_appendix_f(self) -> None:
        self.assertIn("appendix-f", MAPPING_AUTHORITY.lower())

    def test_source_families_cover_task002_scope(self) -> None:
        required = {"mtsf", "thoughtshape", "sds", "conversation_os"}
        self.assertTrue(required.issubset(SOURCE_FAMILIES))

    def test_valid_migration_fixtures_pass_gate_f1(self) -> None:
        for name in VALID_FIXTURES:
            with self.subTest(fixture=name):
                errors = validate_migration_fixture(_load_fixture(name))
                self.assertEqual(errors, [], msg=f"{name}: {errors}")

    def test_migrated_bundles_never_include_uncommitted_states(self) -> None:
        for name in VALID_FIXTURES:
            with self.subTest(fixture=name):
                result = migrate_source_fixture(_load_fixture(name))
                self.assertEqual(_states_without_commitment(result.kernel_bundle), [])

    def test_mtsf_assertion_maps_to_claim_not_state(self) -> None:
        result = migrate_source_fixture(_load_fixture("mtsf_minimal_assertion.json"))
        claim_kinds = [item["envelope"]["record_kind"] for item in result.kernel_bundle["claims"]]
        self.assertEqual(claim_kinds, ["claim"])
        self.assertEqual(result.kernel_bundle["states"], [])
        assertion_rules = [r for r in result.mapping_rules if r.source_type == "Assertion"]
        self.assertEqual(len(assertion_rules), 1)
        self.assertEqual(assertion_rules[0].target_record_kind, "claim")

    def test_thoughtshape_hold_preserves_held_source_fragment(self) -> None:
        result = migrate_source_fixture(_load_fixture("thoughtshape_stateclaim_hold.json"))
        fragment = result.kernel_bundle["source_fragments"][0]
        self.assertEqual(fragment["envelope"]["maturity_status"], "held")
        self.assertEqual(result.kernel_bundle["states"], [])

    def test_sds_signature_preserves_source_ids_in_mapping_rules(self) -> None:
        result = migrate_source_fixture(_load_fixture("sds_signal_dilution.json"))
        source_ids = {rule.source_id for rule in result.mapping_rules}
        self.assertIn("entity-features", source_ids)
        self.assertIn("state-unclear-value", source_ids)
        self.assertIn("rel-features-hide-value", source_ids)
        self.assertIn("analogy-overproduced-song", source_ids)

    def test_sds_analogy_maps_to_claim_not_referent(self) -> None:
        result = migrate_source_fixture(_load_fixture("sds_signal_dilution.json"))
        analogy_rules = [
            rule for rule in result.mapping_rules if rule.source_type == "AnalogyEvaluationPacket"
        ]
        self.assertEqual(len(analogy_rules), 1)
        self.assertEqual(analogy_rules[0].target_record_kind, "claim")
        self.assertIn("analogy preserved as transfer claim", analogy_rules[0].semantic_loss_warnings[0])

    def test_conversation_os_events_become_source_fragments(self) -> None:
        result = migrate_source_fixture(_load_fixture("conversation_os_minimal_session.json"))
        self.assertEqual(len(result.kernel_bundle["source_fragments"]), 2)
        event_rules = [
            rule for rule in result.mapping_rules if rule.source_type == "ConversationEvent"
        ]
        self.assertEqual(len(event_rules), 2)

    def test_conversation_os_workspace_knowledge_maps_to_claim(self) -> None:
        result = migrate_source_fixture(_load_fixture("conversation_os_minimal_session.json"))
        knowledge_rules = [
            rule for rule in result.mapping_rules if rule.source_type == "WorkspaceKnowledgeRecord"
        ]
        self.assertEqual(len(knowledge_rules), 1)
        self.assertEqual(knowledge_rules[0].target_record_kind, "claim")

    def test_analogy_identity_violation_is_detected(self) -> None:
        bad_rule = MappingRule(
            "sds",
            "AnalogyEvaluationPacket",
            "analogy-maze",
            "referent",
            "ref_analogy_maze",
            1.0,
        )
        violations = _analogy_identity_violations([bad_rule])
        self.assertEqual(len(violations), 1)
        self.assertIn("analogy", violations[0])

    def test_state_without_commitment_fails_kernel_validation(self) -> None:
        bundle = _load_fixture("invalid_claim_as_state.json")["inject_kernel_bundle"]
        errors = validate_fixture_bundle(bundle)
        self.assertTrue(any("StateCommitment" in error for error in errors))

    def test_migration_result_requires_mapping_rules(self) -> None:
        result = migrate_source_fixture(_load_fixture("mtsf_minimal_assertion.json"))
        result.mapping_rules = []
        errors = validate_migration_result(result)
        self.assertTrue(any("no mapping rules" in error for error in errors))

    def test_all_valid_fixtures_produce_reversible_loss_reports(self) -> None:
        for name in VALID_FIXTURES:
            with self.subTest(fixture=name):
                result = migrate_source_fixture(_load_fixture(name))
                self.assertTrue(result.reversible)
                self.assertTrue(result.loss_report or result.mapping_rules)

    def test_mtsf_uncertain_identity_preserves_two_referents(self) -> None:
        result = migrate_source_fixture(_load_fixture("mtsf_uncertain_identity.json"))
        referent_ids = [item["envelope"]["id"] for item in result.kernel_bundle["referents"]]
        self.assertEqual(len(referent_ids), 2)
        self.assertEqual(len(set(referent_ids)), 2)
        relations = result.kernel_bundle["relation_instances"]
        self.assertEqual(len(relations), 1)
        self.assertEqual(relations[0]["type_id"], "kernel:identity:possibly_same_as")
        identity_rules = [r for r in result.mapping_rules if r.source_type == "IdentityUncertainty"]
        self.assertEqual(len(identity_rules), 1)
        self.assertIn("§5.13", identity_rules[0].semantic_loss_warnings[0])

    def test_referent_collapse_violation_is_detected(self) -> None:
        rules = [
            MappingRule("mtsf", "IdeaEntity", "entity-a", "referent", "ref_shared", 1.0),
            MappingRule("mtsf", "IdeaEntity", "entity-b", "referent", "ref_shared", 1.0),
        ]
        violations = _referent_collapse_violations(rules)
        self.assertEqual(len(violations), 1)
        self.assertIn("collapsed", violations[0])

    def test_mtsf_uncertain_identity_rejects_unknown_relation_kind(self) -> None:
        fixture = _load_fixture("mtsf_uncertain_identity.json")
        fixture["source_records"]["identity_uncertainty"]["relation"] = "equivalent_to"

        with self.assertRaisesRegex(ValueError, "unsupported identity relation"):
            migrate_source_fixture(fixture)


if __name__ == "__main__":
    unittest.main()
