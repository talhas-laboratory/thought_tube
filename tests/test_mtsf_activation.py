import json
import unittest
from pathlib import Path

from conversation_os.mtsf_kernel import (
    ActivationContext,
    ActivationCondition,
    EntityActivationRecord,
    activate,
    build_activation_snapshot,
    default_seed_conditions_path,
    evaluate_predicate,
    load_seed_conditions,
    replay_pilot_002_scenarios,
    run_replay_scenarios,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


class MtsfActivationTestCase(unittest.TestCase):
    def test_seed_conditions_file_exists(self) -> None:
        path = default_seed_conditions_path(REPO_ROOT)
        self.assertTrue(path.exists())
        payload = json.loads(path.read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(payload.get("conditions", [])), 7)

    def test_evaluate_context_predicates(self) -> None:
        ctx_overlap = ActivationContext(
            entity_id="entity-context-field",
            context_domain_overlap=0.72,
        )
        self.assertTrue(
            evaluate_predicate(
                {"type": "context_domain_overlap", "min_overlap_score": 0.6},
                ctx_overlap,
            )
        )
        ctx_orthogonal = ActivationContext(
            entity_id="entity-context-field",
            context_domain_orthogonal=0.8,
        )
        self.assertTrue(
            evaluate_predicate(
                {"type": "context_domain_orthogonal", "min_overlap_score": 0.6},
                ctx_orthogonal,
            )
        )

    def test_explicit_lens_beats_meta_move(self) -> None:
        conditions = load_seed_conditions(REPO_ROOT)
        entity = EntityActivationRecord(
            id="entity-symmetry-engine",
            shape_state_ids=["shape-positive-isomorph", "shape-negative-shadow"],
        )
        ctx = ActivationContext(
            entity_id="entity-symmetry-engine",
            meta_move_id="move-inversion",
            explicit_lens="structural_isomorph",
        )
        result = activate(entity, ctx, conditions)
        self.assertEqual(result.dominant_shape_id, "shape-positive-isomorph")
        self.assertIn("cond-explicit-structural-lens", result.matched_conditions)

    def test_build_activation_snapshot(self) -> None:
        conditions = load_seed_conditions(REPO_ROOT)
        entity = EntityActivationRecord(
            id="entity-context-field",
            shape_state_ids=["shape-cold-start", "shape-anchored-start", "shape-polluted-start"],
        )
        ctx = ActivationContext(
            entity_id="entity-context-field",
            context_domain_overlap=0.7,
        )
        result = activate(entity, ctx, conditions)
        snapshot = build_activation_snapshot(
            snapshot_id="snap-test-01",
            session_id="import-69ea1f64f744",
            subgraph_id="pilot-002",
            formation_phase="partial_population",
            meta_shape_id=None,
            results=[result],
        )
        self.assertIn("cond-anchored-start", snapshot["matched_conditions"])
        self.assertEqual(len(snapshot["shape_activation_results"]), 1)

    def test_pilot_002_replay_all_pass(self) -> None:
        report = run_replay_scenarios(REPO_ROOT)
        self.assertEqual(report["failed"], 0, json.dumps(report["runs"], indent=2))
        self.assertEqual(report["passed"], len(replay_pilot_002_scenarios()))

    def test_custom_condition_applies(self) -> None:
        custom = ActivationCondition(
            id="cond-test-phase",
            entity_id="entity-test",
            activates_shape_id="shape-forming",
            predicate={"type": "formation_phase", "formation_phase": "structural_binding"},
            priority=0.9,
            weight=0.9,
        )
        entity = EntityActivationRecord(
            id="entity-test",
            shape_state_ids=["shape-forming", "shape-vague"],
        )
        ctx = ActivationContext(
            entity_id="entity-test",
            formation_phase="structural_binding",
        )
        result = activate(entity, ctx, [custom])
        self.assertEqual(result.dominant_shape_id, "shape-forming")
        self.assertEqual(result.matched_conditions, ["cond-test-phase"])


if __name__ == "__main__":
    unittest.main()
