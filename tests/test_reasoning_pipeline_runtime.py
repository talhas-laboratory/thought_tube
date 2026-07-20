from __future__ import annotations

import argparse
import tempfile
import unittest
from pathlib import Path

from conversation_os.active_field import build_active_field
from conversation_os.cli import build_parser, reasoning_run
from conversation_os.corpus_catalog_snapshot import publish_corpus_catalog_snapshot
from conversation_os.models import (
    ActiveFieldState,
    ContextState,
    ReasoningLearningEvent,
    ReasoningRequest,
    ReasoningResult,
)
from conversation_os.personal_interface import load_bridge_state
from conversation_os.reasoning_evaluator import evaluate_reasoning_packet
from conversation_os.reasoning_bridge import (
    classify_turn,
    get_context_bundle,
    load_context_switch_events,
    record_context_switch,
)
from conversation_os.reasoning_learning import (
    load_learning_events,
    persist_bridge_behavior_preferences,
    record_learning_event,
)
from conversation_os.reasoning_router import route_reasoning
from conversation_os.reasoning_runtime import run_reasoning
from conversation_os.storage import append_jsonl, read_jsonl


def _runtime_dir(root: Path) -> Path:
    return root / "product" / "inner_world_v1" / "data" / "reasoning_runtime"


class ReasoningRuntimeContractsTestCase(unittest.TestCase):
    def test_reasoning_request_to_dict_round_trips(self) -> None:
        packet = ReasoningRequest(
            request_id="req-001",
            session_id="session-001",
            surface="chat",
            raw_text="We need a layer between raw intelligence and the user.",
            source_refs=["memory/sessions/session-001/ordered_transcript.md"],
            timestamp="2026-06-10T12:00:00+00:00",
            domain_hints=["product", "reasoning"],
            caller_hints={"origin": "unit-test"},
        )

        self.assertEqual(packet.to_dict()["request_id"], "req-001")
        self.assertEqual(packet.to_dict()["caller_hints"]["origin"], "unit-test")

    def test_context_state_defaults_and_optional_fields_round_trip(self) -> None:
        packet = ContextState(
            context_id="ctx-001",
            request_id="req-001",
            active_topic="reasoning runtime",
            object_scope="same_main",
            object_id="obj-main-001",
            user_goal="build an MVP",
            current_tension="speed vs depth",
            answer_shape="scaffold",
            active_workspace_id="workspace-main",
            depth_mode="contextual",
            confidence=0.72,
            bundle_layers=["session", "workspace", "user"],
            source_refs=["memory/events/session-001.jsonl"],
        )

        payload = packet.to_dict()
        self.assertIsNone(payload["parent_object_id"])
        self.assertEqual(payload["dimension_axis"], "")
        self.assertEqual(payload["reasoning_posture"], "")
        self.assertEqual(payload["factual_anchor_level"], "")
        self.assertEqual(payload["bridge_behaviors"], [])
        self.assertEqual(payload["attributes"], {})

    def test_active_field_state_defaults_are_json_serializable(self) -> None:
        packet = ActiveFieldState(
            field_id="field-001",
            request_id="req-001",
            context_id="ctx-001",
            fragment_role="idea_fragment",
            candidate_parent_ideas=[{"object_id": "obj-main-001", "score": 0.91}],
            active_dimensions=["architecture", "product"],
            active_tensions=["clarity vs depth"],
            constraints=["keep it small"],
            ambiguity_level=0.48,
            fixation_risk=0.22,
            novelty_confidence=0.61,
            fit_targets=["obj-main-001"],
            suggested_reasoning_family="idea_embedding_v1",
            source_refs=["memory/events/session-001.jsonl"],
            retrieval_bundle_summary={"capsule_count": 3},
        )

        payload = packet.to_dict()
        self.assertEqual(payload["bridge_behaviors"], [])
        self.assertEqual(payload["perturbation_markers"], [])
        self.assertEqual(payload["state_update_scope"], "local_adjustment")
        self.assertEqual(payload["attributes"], {})

    def test_reasoning_result_to_dict_round_trips(self) -> None:
        packet = ReasoningResult(
            result_id="result-001",
            request_id="req-001",
            field_id="field-001",
            pipeline_id="idea_embedding_v1",
            response_text="This fragment belongs to the same main object.",
            integration_verdict="integrate",
            fit_score=0.83,
            novelty_score=0.57,
            confidence=0.79,
            recommended_next_action="store_context_state",
            operator_trace=["classify_fragment_role", "identify_parent_ideas"],
        )

        payload = packet.to_dict()
        self.assertEqual(payload["pipeline_id"], "idea_embedding_v1")
        self.assertEqual(payload["operator_trace"][0], "classify_fragment_role")

    def test_learning_event_defaults_and_evidence_round_trip(self) -> None:
        packet = ReasoningLearningEvent(
            learning_event_id="learn-001",
            request_id="req-001",
            result_id="result-001",
            feedback_kind="reframe",
            accepted_framing="same main object",
            rejected_framing="new object",
            reframing_text="Keep it under the same idea but switch dimension.",
            preferred_abstraction_shift="deeper",
            evidence_refs=["memory/events/session-001.jsonl#turn-12"],
            sequence_signature=["fragment", "correction", "accepted_reframe"],
            timestamp="2026-06-10T12:05:00+00:00",
        )

        payload = packet.to_dict()
        self.assertEqual(payload["evidence_refs"][0], "memory/events/session-001.jsonl#turn-12")
        self.assertEqual(payload["attributes"], {})


class ReasoningRuntimePersistenceTestCase(unittest.TestCase):
    def test_reasoning_runtime_artifacts_can_be_persisted_with_existing_jsonl_storage(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            request = ReasoningRequest(
                request_id="req-001",
                session_id="session-001",
                surface="chat",
                raw_text="Build the layer first.",
                source_refs=["memory/events/session-001.jsonl"],
                timestamp="2026-06-10T12:00:00+00:00",
                domain_hints=["runtime"],
            )
            context = ContextState(
                context_id="ctx-001",
                request_id="req-001",
                active_topic="runtime contracts",
                object_scope="same_main",
                object_id="obj-main-001",
                user_goal="scaffold run 1",
                current_tension="completeness vs speed",
                answer_shape="typed_contract",
                active_workspace_id="workspace-main",
                depth_mode="focused",
                confidence=0.66,
                bundle_layers=["session"],
                source_refs=["memory/events/session-001.jsonl"],
            )
            field = ActiveFieldState(
                field_id="field-001",
                request_id="req-001",
                context_id="ctx-001",
                fragment_role="request",
                candidate_parent_ideas=[{"object_id": "obj-main-001", "score": 0.88}],
                active_dimensions=["implementation"],
                active_tensions=["speed vs depth"],
                constraints=["typed only"],
                ambiguity_level=0.31,
                fixation_risk=0.17,
                novelty_confidence=0.52,
                fit_targets=["obj-main-001"],
                suggested_reasoning_family="idea_embedding_v1",
                source_refs=["memory/events/session-001.jsonl"],
                retrieval_bundle_summary={"capsule_count": 1},
            )
            result = ReasoningResult(
                result_id="result-001",
                request_id="req-001",
                field_id="field-001",
                pipeline_id="idea_embedding_v1",
                response_text="Treat this as the same main object.",
                integration_verdict="integrate",
                fit_score=0.81,
                novelty_score=0.49,
                confidence=0.73,
                recommended_next_action="persist",
                operator_trace=["classify_fragment_role"],
            )
            learning = ReasoningLearningEvent(
                learning_event_id="learn-001",
                request_id="req-001",
                result_id="result-001",
                feedback_kind="accept",
                accepted_framing="same main object",
                rejected_framing="",
                reframing_text="",
                preferred_abstraction_shift="same",
                evidence_refs=["memory/events/session-001.jsonl#turn-1"],
                sequence_signature=["fragment", "accept"],
                timestamp="2026-06-10T12:02:00+00:00",
            )

            append_jsonl(_runtime_dir(root) / "reasoning_requests.jsonl", request.to_dict())
            append_jsonl(_runtime_dir(root) / "context_states.jsonl", context.to_dict())
            append_jsonl(_runtime_dir(root) / "active_fields.jsonl", field.to_dict())
            append_jsonl(_runtime_dir(root) / "reasoning_results.jsonl", result.to_dict())
            append_jsonl(
                _runtime_dir(root) / "reasoning_learning_events.jsonl",
                learning.to_dict(),
            )

            self.assertEqual(len(read_jsonl(_runtime_dir(root) / "reasoning_requests.jsonl")), 1)
            self.assertEqual(len(read_jsonl(_runtime_dir(root) / "context_states.jsonl")), 1)
            self.assertEqual(len(read_jsonl(_runtime_dir(root) / "active_fields.jsonl")), 1)
            self.assertEqual(len(read_jsonl(_runtime_dir(root) / "reasoning_results.jsonl")), 1)
            self.assertEqual(
                len(read_jsonl(_runtime_dir(root) / "reasoning_learning_events.jsonl")),
                1,
            )


class ReasoningRuntimeBridgeAndFieldTestCase(unittest.TestCase):
    def test_classify_turn_prefers_same_main_and_contextual_depth_for_build_request(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            request = ReasoningRequest(
                request_id="req-bridge-001",
                session_id="session-bridge-001",
                surface="chat",
                raw_text="How should we build the reasoning runtime MVP?",
                source_refs=["memory/events/session-bridge-001.jsonl"],
                timestamp="2026-06-10T12:10:00+00:00",
                domain_hints=["runtime", "product"],
            )

            payload = classify_turn(root, request.to_dict())
            self.assertEqual(payload["active_topic"], "should build reasoning runtime")
            self.assertEqual(payload["object_scope"], "same_main")
            self.assertEqual(payload["user_goal"], "build")
            self.assertEqual(payload["depth_mode"], "contextual")
            self.assertEqual(payload["answer_shape"], "implementation_scaffold")

    def test_get_context_bundle_uses_session_user_and_global_layers(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            append_jsonl(
                root / "memory" / "events" / "session-bridge-002.jsonl",
                {
                    "event_id": "event-1",
                    "session_id": "session-bridge-002",
                    "timestamp": "2026-06-10T12:11:00+00:00",
                    "actor": "user",
                    "kind": "message",
                    "content": "We need a reasoning runtime for product concept formation.",
                    "attachments": [],
                    "tags": [],
                    "source_ref": None,
                },
            )
            append_jsonl(
                root / "product" / "inner_world_v1" / "data" / "semantic_capsules.jsonl",
                {
                    "capsule_id": "capsule-1",
                    "capsule_type": "concept",
                    "label": "Reasoning runtime",
                    "summary": "A runtime layer for bounded context selection.",
                    "confidence": 0.91,
                    "ref_type": "concept",
                    "ref_id": "concept-runtime",
                    "source_refs": ["memory/events/session-bridge-002.jsonl"],
                    "attributes": {"domain": "runtime"},
                },
            )
            publish_corpus_catalog_snapshot(root)
            request = ReasoningRequest(
                request_id="req-bridge-002",
                session_id="session-bridge-002",
                surface="chat",
                raw_text="Build the reasoning runtime layer.",
                source_refs=["memory/events/session-bridge-002.jsonl"],
                timestamp="2026-06-10T12:12:00+00:00",
                domain_hints=["runtime"],
            )

            context_state = classify_turn(root, request.to_dict())
            bundle = get_context_bundle(root, context_state)

            self.assertEqual(len(bundle["session_local"]), 1)
            self.assertEqual(bundle["global_fallback"]["count"], 1)
            self.assertIn("session", bundle["context_state"]["bundle_layers"])
            self.assertIn("global", bundle["context_state"]["bundle_layers"])
            self.assertIn("user", bundle["context_state"]["bundle_layers"])

    def test_record_context_switch_persists_event(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            event = {
                "event_id": "ctx-switch-001",
                "request_id": "req-bridge-003",
                "previous_context_id": "ctx-old",
                "new_context_id": "ctx-new",
                "trigger": "turn_classification",
                "switch_kind": "object_shift",
                "confidence": 0.71,
                "retrieval_sources": [],
                "rollback_path": "ctx-old",
                "timestamp": "2026-06-10T12:13:00+00:00",
                "attributes": {},
            }

            record_context_switch(root, event)
            self.assertEqual(load_context_switch_events(root)[0]["switch_kind"], "object_shift")

    def test_build_active_field_produces_parent_ideas_from_retrieval_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            append_jsonl(
                root / "product" / "inner_world_v1" / "data" / "semantic_capsules.jsonl",
                {
                    "capsule_id": "capsule-2",
                    "capsule_type": "concept",
                    "label": "Context refinery",
                    "summary": "A layer that refines raw model intelligence through context.",
                    "confidence": 0.93,
                    "ref_type": "concept",
                    "ref_id": "concept-refinery",
                    "source_refs": ["memory/sessions/session-001/ordered_transcript.md"],
                    "attributes": {"domain": "product"},
                },
            )
            append_jsonl(
                root / "product" / "inner_world_v1" / "data" / "semantic_capsules.jsonl",
                {
                    "capsule_id": "capsule-3",
                    "capsule_type": "concept",
                    "label": "Reasoning pipeline",
                    "summary": "A structured transformation path for thought fragments.",
                    "confidence": 0.87,
                    "ref_type": "concept",
                    "ref_id": "concept-pipeline",
                    "source_refs": ["memory/sessions/session-001/ordered_transcript.md"],
                    "attributes": {"domain": "runtime"},
                },
            )
            publish_corpus_catalog_snapshot(root)
            request = ReasoningRequest(
                request_id="req-field-001",
                session_id="session-field-001",
                surface="chat",
                raw_text="Build a context refinery reasoning runtime.",
                source_refs=["memory/events/session-field-001.jsonl"],
                timestamp="2026-06-10T12:14:00+00:00",
                domain_hints=["product", "runtime"],
                caller_hints={"constraints": ["keep it modular"]},
            )

            field = build_active_field(root, request.to_dict())
            self.assertEqual(field["fragment_role"], "implementation_request")
            self.assertEqual(field["suggested_reasoning_family"], "idea_embedding_v1")
            self.assertGreaterEqual(len(field["candidate_parent_ideas"]), 2)
            self.assertIn("product", field["active_dimensions"])
            self.assertEqual(field["constraints"], ["keep it modular"])

    def test_build_active_field_handles_ambiguous_request_without_retrieval(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            request = ReasoningRequest(
                request_id="req-field-002",
                session_id="session-field-002",
                surface="chat",
                raw_text="I feel like something is happening here but I am not sure what it belongs to.",
                source_refs=["memory/events/session-field-002.jsonl"],
                timestamp="2026-06-10T12:15:00+00:00",
            )

            field = build_active_field(root, request.to_dict())
            self.assertEqual(field["fragment_role"], "idea_fragment")
            self.assertGreaterEqual(field["ambiguity_level"], 0.5)
            self.assertEqual(field["suggested_reasoning_family"], "problem_reframing_v1")
            self.assertEqual(field["state_update_scope"], "local_adjustment")

    def test_classify_turn_applies_creative_expansion_bridge_behavior_for_metathought(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            request = ReasoningRequest(
                request_id="req-bridge-creative-001",
                session_id="session-bridge-creative-001",
                surface="chat",
                raw_text="Could this represent the subconscious in a symbolic way?",
                source_refs=["memory/events/session-bridge-creative-001.jsonl"],
                timestamp="2026-06-10T12:16:00+00:00",
                caller_hints={"routing_tags": ["metathought"]},
            )

            payload = classify_turn(root, request.to_dict())
            self.assertEqual(payload["reasoning_posture"], "expansive")
            self.assertEqual(payload["factual_anchor_level"], "low")
            self.assertEqual(payload["bridge_behaviors"][0]["behavior_id"], "creative_expansion")

    def test_build_active_field_prefers_intuition_expansion_pipeline_when_bridge_behavior_matches(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            request = ReasoningRequest(
                request_id="req-field-creative-001",
                session_id="session-field-creative-001",
                surface="chat",
                raw_text="Could this represent the subconscious in a symbolic way?",
                source_refs=["memory/events/session-field-creative-001.jsonl"],
                timestamp="2026-06-10T12:17:00+00:00",
                caller_hints={"routing_tags": ["metathought"]},
            )

            field = build_active_field(root, request.to_dict())
            self.assertEqual(field["suggested_reasoning_family"], "intuition_expansion_v1")
            self.assertEqual(field["bridge_behaviors"][0]["behavior_id"], "creative_expansion")

    def test_classify_turn_applies_objective_evaluation_behavior(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            request = ReasoningRequest(
                request_id="req-bridge-eval-001",
                session_id="session-bridge-eval-001",
                surface="chat",
                raw_text="Evaluate this objectively for novelty and risk.",
                source_refs=["memory/events/session-bridge-eval-001.jsonl"],
                timestamp="2026-06-10T12:18:00+00:00",
            )

            payload = classify_turn(root, request.to_dict())
            self.assertEqual(payload["reasoning_posture"], "evaluative")
            self.assertEqual(payload["bridge_behaviors"][0]["behavior_id"], "objective_evaluation")

    def test_classify_turn_applies_implementation_scaffold_behavior(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            request = ReasoningRequest(
                request_id="req-bridge-build-001",
                session_id="session-bridge-build-001",
                surface="chat",
                raw_text="Build the next MVP scaffold for this runtime.",
                source_refs=["memory/events/session-bridge-build-001.jsonl"],
                timestamp="2026-06-10T12:19:00+00:00",
            )

            payload = classify_turn(root, request.to_dict())
            behavior_ids = [behavior["behavior_id"] for behavior in payload["bridge_behaviors"]]
            self.assertIn("implementation_scaffold", behavior_ids)

    def test_classify_turn_applies_symbolic_interpretation_behavior(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            request = ReasoningRequest(
                request_id="req-bridge-symbolic-001",
                session_id="session-bridge-symbolic-001",
                surface="chat",
                raw_text="What is the deeper symbolic meaning of this image?",
                source_refs=["memory/events/session-bridge-symbolic-001.jsonl"],
                timestamp="2026-06-10T12:20:00+00:00",
            )

            payload = classify_turn(root, request.to_dict())
            behavior_ids = [behavior["behavior_id"] for behavior in payload["bridge_behaviors"]]
            self.assertIn("symbolic_interpretation", behavior_ids)


class ReasoningRuntimeExecutionTestCase(unittest.TestCase):
    def test_route_reasoning_prefers_candidate_evaluation_when_fragment_role_demands_it(self) -> None:
        route = route_reasoning(
            {
                "fragment_role": "candidate_evaluation",
                "suggested_reasoning_family": "idea_embedding_v1",
                "ambiguity_level": 0.22,
                "candidate_parent_ideas": [{"object_id": "obj-1"}],
            }
        )
        self.assertEqual(route["pipeline_id"], "candidate_evaluation_v1")

    def test_route_reasoning_prefers_bridge_behavior_override_pipeline(self) -> None:
        route = route_reasoning(
            {
                "fragment_role": "question",
                "suggested_reasoning_family": "idea_embedding_v1",
                "ambiguity_level": 0.34,
                "candidate_parent_ideas": [{"object_id": "obj-1"}],
                "bridge_behaviors": [
                    {
                        "behavior_id": "creative_expansion",
                        "priority": 90,
                        "preferred_pipeline": "intuition_expansion_v1",
                        "routing_mode": "override",
                    }
                ],
            }
        )
        self.assertEqual(route["pipeline_id"], "intuition_expansion_v1")

    def test_evaluate_reasoning_packet_returns_integrate_for_strong_fit(self) -> None:
        evaluation = evaluate_reasoning_packet(
            {
                "active_field": {
                    "ambiguity_level": 0.22,
                    "fixation_risk": 0.11,
                    "novelty_confidence": 0.58,
                    "active_tensions": [],
                },
                "reasoning": {
                    "selected_transformation": {
                        "fit_score": 0.82,
                        "integrate": True,
                    }
                },
                "user_response": {"text": "This belongs under the main runtime idea."},
            }
        )
        self.assertEqual(evaluation["integration_verdict"], "integrate")
        self.assertEqual(evaluation["recommended_next_action"], "persist")

    def test_record_learning_event_persists_feedback(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            record_learning_event(
                root,
                {
                    "learning_event_id": "learn-123",
                    "request_id": "req-123",
                    "result_id": "result-123",
                    "feedback_kind": "accept",
                    "accepted_framing": "same main object",
                    "rejected_framing": "",
                    "reframing_text": "",
                    "preferred_abstraction_shift": "same",
                    "evidence_refs": ["memory/events/session-1.jsonl#1"],
                    "sequence_signature": ["fragment", "accept"],
                    "timestamp": "2026-06-10T12:20:00+00:00",
                    "attributes": {},
                },
            )
            self.assertEqual(load_learning_events(root)[0]["feedback_kind"], "accept")

    def test_persist_bridge_behavior_preferences_updates_bridge_state(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            persisted = persist_bridge_behavior_preferences(
                root,
                {
                    "learning_event_id": "learn-creative-1",
                    "request_id": "req-creative-1",
                    "result_id": "result-creative-1",
                    "feedback_kind": "accept",
                    "evidence_refs": ["memory/events/session-creative-1.jsonl#1"],
                    "timestamp": "2026-06-10T12:21:00+00:00",
                    "attributes": {},
                },
                context_state={
                    "bridge_behaviors": [
                        {
                            "behavior_id": "creative_expansion",
                        }
                    ]
                },
                result={"pipeline_id": "intuition_expansion_v1"},
            )
            self.assertEqual(persisted[0]["pattern_key"], "bridge_behavior:creative_expansion")
            state = load_bridge_state(root)
            self.assertEqual(state["behavior_patterns"][0]["pattern_key"], "bridge_behavior:creative_expansion")

    def test_classify_turn_uses_confirmed_bridge_behavior_from_bridge_state(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            persist_bridge_behavior_preferences(
                root,
                {
                    "learning_event_id": "learn-symbolic-1",
                    "request_id": "req-symbolic-1",
                    "result_id": "result-symbolic-1",
                    "feedback_kind": "accept",
                    "evidence_refs": ["memory/events/session-symbolic-1.jsonl#1"],
                    "timestamp": "2026-06-10T12:22:00+00:00",
                    "attributes": {"accepted_bridge_behaviors": ["symbolic_interpretation"]},
                },
                context_state={},
                result={"pipeline_id": "symbolic_interpretation_v1"},
            )
            request = ReasoningRequest(
                request_id="req-symbolic-2",
                session_id="session-symbolic-2",
                surface="chat",
                raw_text="What does this represent at a deeper level?",
                source_refs=["memory/events/session-symbolic-2.jsonl"],
                timestamp="2026-06-10T12:23:00+00:00",
            )

            payload = classify_turn(root, request.to_dict())
            behavior_ids = [behavior["behavior_id"] for behavior in payload["bridge_behaviors"]]
            self.assertIn("symbolic_interpretation", behavior_ids)

    def test_run_reasoning_executes_end_to_end_and_persists_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            append_jsonl(
                root / "product" / "inner_world_v1" / "data" / "semantic_capsules.jsonl",
                {
                    "capsule_id": "capsule-e2e-1",
                    "capsule_type": "concept",
                    "label": "Reasoning runtime",
                    "summary": "A bounded runtime that routes fragments through structured reasoning.",
                    "confidence": 0.92,
                    "ref_type": "concept",
                    "ref_id": "concept-runtime",
                    "source_refs": ["memory/sessions/session-e2e/ordered_transcript.md"],
                    "attributes": {"domain": "runtime"},
                },
            )
            append_jsonl(
                root / "product" / "inner_world_v1" / "data" / "semantic_capsules.jsonl",
                {
                    "capsule_id": "capsule-e2e-2",
                    "capsule_type": "concept",
                    "label": "Context refinery",
                    "summary": "A layer that refines raw model intelligence through context.",
                    "confidence": 0.88,
                    "ref_type": "concept",
                    "ref_id": "concept-refinery",
                    "source_refs": ["memory/sessions/session-e2e/ordered_transcript.md"],
                    "attributes": {"domain": "product"},
                },
            )
            request = ReasoningRequest(
                request_id="req-e2e-001",
                session_id="session-e2e-001",
                surface="chat",
                raw_text="Build the first MVP layer for the context refinery reasoning runtime.",
                source_refs=["memory/events/session-e2e-001.jsonl"],
                timestamp="2026-06-10T12:21:00+00:00",
                domain_hints=["runtime", "product"],
                caller_hints={
                    "constraints": ["keep it modular"],
                    "feedback_kind": "accept",
                    "accepted_framing": "same main object",
                    "preferred_abstraction_shift": "same",
                },
            )

            outcome = run_reasoning(root, request)

            self.assertEqual(outcome["route"]["pipeline_id"], "idea_embedding_v1")
            self.assertTrue(outcome["result"]["response_text"])
            self.assertIn(outcome["result"]["integration_verdict"], {"integrate", "suspend", "needs_more_probe", "preserve_tension"})
            self.assertEqual(len(read_jsonl(_runtime_dir(root) / "context_states.jsonl")), 1)
            self.assertEqual(len(read_jsonl(_runtime_dir(root) / "active_fields.jsonl")), 1)
            self.assertEqual(len(read_jsonl(_runtime_dir(root) / "reasoning_results.jsonl")), 1)
            self.assertEqual(len(read_jsonl(_runtime_dir(root) / "reasoning_evaluations.jsonl")), 1)
            self.assertEqual(len(read_jsonl(_runtime_dir(root) / "reasoning_learning_events.jsonl")), 1)

    def test_run_reasoning_uses_intuition_expansion_for_metathought_queries(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            append_jsonl(
                root / "product" / "inner_world_v1" / "data" / "semantic_capsules.jsonl",
                {
                    "capsule_id": "capsule-intuition-1",
                    "capsule_type": "concept",
                    "label": "Subconscious mapping",
                    "summary": "A way to read symbolic material as latent internal structure.",
                    "confidence": 0.84,
                    "ref_type": "concept",
                    "ref_id": "concept-subconscious-mapping",
                    "source_refs": ["memory/sessions/session-intuition/ordered_transcript.md"],
                    "attributes": {"domain": "symbolic"},
                },
            )
            request = ReasoningRequest(
                request_id="req-intuition-001",
                session_id="session-intuition-001",
                surface="chat",
                raw_text="Could this represent the subconscious in a symbolic way?",
                source_refs=["memory/events/session-intuition-001.jsonl"],
                timestamp="2026-06-10T12:22:00+00:00",
                caller_hints={"routing_tags": ["metathought"]},
            )

            outcome = run_reasoning(root, request)

            self.assertEqual(outcome["route"]["pipeline_id"], "intuition_expansion_v1")
            self.assertIn("The intuition already has a real shape.", outcome["result"]["response_text"])
            self.assertIn("creative_expansion", outcome["route"]["routing_factors"]["bridge_behavior_ids"])

    def test_run_reasoning_persists_confirmed_bridge_behavior_patterns(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            request = ReasoningRequest(
                request_id="req-learning-001",
                session_id="session-learning-001",
                surface="chat",
                raw_text="Could this represent the subconscious in a symbolic way?",
                source_refs=["memory/events/session-learning-001.jsonl"],
                timestamp="2026-06-10T12:24:00+00:00",
                caller_hints={
                    "routing_tags": ["metathought"],
                    "feedback_kind": "accept",
                    "accepted_framing": "expansive interpretation",
                },
            )

            outcome = run_reasoning(root, request)

            self.assertIn("persisted_bridge_behavior_patterns", outcome["result"]["attributes"])
            bridge_state = load_bridge_state(root)
            pattern_keys = [row["pattern_key"] for row in bridge_state["behavior_patterns"]]
            self.assertIn("bridge_behavior:creative_expansion", pattern_keys)

    def test_run_reasoning_uses_symbolic_interpretation_pipeline(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            request = ReasoningRequest(
                request_id="req-symbolic-runtime-001",
                session_id="session-symbolic-runtime-001",
                surface="chat",
                raw_text="What is the deeper symbolic meaning of this image?",
                source_refs=["memory/events/session-symbolic-runtime-001.jsonl"],
                timestamp="2026-06-10T12:25:00+00:00",
            )

            outcome = run_reasoning(root, request)

            self.assertEqual(outcome["route"]["pipeline_id"], "symbolic_interpretation_v1")
            self.assertIn("symbolically rather than literally", outcome["result"]["response_text"])

    def test_run_reasoning_uses_objective_evaluation_pipeline(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            request = ReasoningRequest(
                request_id="req-eval-runtime-001",
                session_id="session-eval-runtime-001",
                surface="chat",
                raw_text="Evaluate this objectively for novelty and risk.",
                source_refs=["memory/events/session-eval-runtime-001.jsonl"],
                timestamp="2026-06-10T12:26:00+00:00",
            )

            outcome = run_reasoning(root, request)

            self.assertEqual(outcome["route"]["pipeline_id"], "candidate_evaluation_v1")
            self.assertIn("Objective assessment:", outcome["result"]["response_text"])

    def test_reasoning_run_cli_executes_end_to_end(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            append_jsonl(
                root / "product" / "inner_world_v1" / "data" / "semantic_capsules.jsonl",
                {
                    "capsule_id": "capsule-cli-1",
                    "capsule_type": "concept",
                    "label": "Context refinery",
                    "summary": "A product layer that refines raw intelligence through context.",
                    "confidence": 0.9,
                    "ref_type": "concept",
                    "ref_id": "concept-refinery",
                    "source_refs": ["memory/sessions/session-cli/ordered_transcript.md"],
                    "attributes": {"domain": "product"},
                },
            )

            outcome = reasoning_run(
                root,
                argparse.Namespace(
                    text="Build the first modular runtime layer.",
                    session_id="session-cli-001",
                    request_id="",
                    surface="chat",
                    domains="product,runtime",
                    source_refs="memory/events/session-cli-001.jsonl",
                    constraints="keep it modular",
                    caller_hints_json='{"feedback_kind":"accept","accepted_framing":"same main object"}',
                ),
            )

            self.assertEqual(outcome["route"]["pipeline_id"], "idea_embedding_v1")
            self.assertTrue(outcome["result"]["response_text"])
            self.assertEqual(len(read_jsonl(_runtime_dir(root) / "context_states.jsonl")), 1)
            self.assertEqual(len(read_jsonl(_runtime_dir(root) / "reasoning_results.jsonl")), 1)

    def test_reasoning_run_cli_treats_meta_tag_as_product_scope(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            outcome = reasoning_run(
                root,
                argparse.Namespace(
                    text="#meta build the runtime layer for this product",
                    session_id="session-meta-001",
                    request_id="",
                    surface="chat",
                    domains="runtime",
                    source_refs="memory/events/session-meta-001.jsonl",
                    constraints="",
                    caller_hints_json="",
                ),
            )

            self.assertEqual(outcome["context_state"]["active_topic"], "product")
            self.assertEqual(outcome["context_state"]["active_workspace_id"], "product")
            self.assertIn("product", outcome["context_state"]["attributes"]["domain_hints"])
            self.assertIn("meta", outcome["context_state"]["attributes"]["caller_hints"]["routing_tags"])

    def test_reasoning_run_cli_treats_metathought_tag_as_creative_bridge_signal(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            outcome = reasoning_run(
                root,
                argparse.Namespace(
                    text="#metathought could this represent the subconscious in a symbolic way?",
                    session_id="session-metathought-001",
                    request_id="",
                    surface="chat",
                    domains="",
                    source_refs="memory/events/session-metathought-001.jsonl",
                    constraints="",
                    caller_hints_json="",
                ),
            )

            self.assertEqual(outcome["route"]["pipeline_id"], "intuition_expansion_v1")
            self.assertEqual(outcome["context_state"]["reasoning_posture"], "expansive")
            self.assertEqual(outcome["context_state"]["bridge_behaviors"][0]["behavior_id"], "creative_expansion")

    def test_build_parser_accepts_reasoning_run_command(self) -> None:
        args = build_parser().parse_args(
            [
                "reasoning",
                "run",
                "--text",
                "#meta map this fragment",
                "--domains",
                "runtime",
            ]
        )

        self.assertEqual(args.command, "reasoning")
        self.assertEqual(args.reasoning_command, "run")
        self.assertEqual(args.text, "#meta map this fragment")


if __name__ == "__main__":
    unittest.main()
