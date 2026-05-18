import asyncio
import importlib.util
import io
import json
import os
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from conversation_os.cli import init_repo, main
from conversation_os.personal_interface import (
    CALIBRATION_INTERVIEW,
    PersonalInterfaceError,
    answer_calibration_question,
    build_personal_interface_profile,
    compile_turn_policy,
    ingest_learning_conversation,
    identify_communication_mode,
    load_personal_interface_policy_snapshot,
    load_personal_interface_profile,
    record_rewrite_feedback,
    rewrite_conversation_turn,
    rewrite_outgoing_message,
    start_calibration_interview,
)
from conversation_os.personal_interface_mcp import build_personal_interface_mcp_server
from conversation_os.storage import read_json, read_jsonl, session_events_path


REPO_ROOT = Path(__file__).resolve().parents[1]


class PersonalInterfaceTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        for filename in [
            "TENETS.md",
            "AGENTS.md",
            "SESSION_PROTOCOL.md",
            "CONTEXT_ROUTING.md",
            "PRODUCT_THESIS.md",
            "pyproject.toml",
        ]:
            shutil.copy(REPO_ROOT / filename, self.root / filename)
        init_repo(self.root)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _run_cli(self, args: list[str]) -> tuple[int, dict]:
        output = io.StringIO()
        old = os.getcwd()
        os.chdir(self.root)
        try:
            with redirect_stdout(output):
                exit_code = main(args)
        finally:
            os.chdir(old)
        return exit_code, json.loads(output.getvalue())

    def _complete_calibration(self) -> dict:
        started = start_calibration_interview(self.root)
        current = started
        scripted_answers = {
            "recent_moment": "slowed_me_down",
            "reply_shape": "push_forward",
            "interruption_tolerance": "flag_gently",
            "annoyances": "too_long,too_many_options,soft_prefacing",
            "decision_mode": "clear_recommendation",
            "energy": "direct_plain",
            "anchor_example": "Walls of text break momentum.",
        }
        while not current["completed"]:
            current = answer_calibration_question(
                self.root,
                current["session_id"],
                scripted_answers[current["question_id"]],
            )
        return current

    def test_calibration_starts_with_recognition_heavy_question(self) -> None:
        started = start_calibration_interview(self.root)

        self.assertEqual(started["question_id"], "recent_moment")
        self.assertEqual(started["selection_mode"], "single")
        self.assertTrue(started["allow_free_text"])
        self.assertTrue(started["response_options"])
        self.assertIn("why_this_matters", started)
        self.assertIn("progress", started)
        self.assertEqual(started["progress"]["minimum_questions"], 5)
        self.assertEqual(started["progress"]["maximum_questions"], 7)

    def test_calibration_adapts_and_can_finish_early(self) -> None:
        current = start_calibration_interview(self.root)
        answers = {
            "recent_moment": "slowed_me_down",
            "reply_shape": "push_forward",
            "interruption_tolerance": "flag_gently",
            "annoyances": "too_long,too_many_options",
            "decision_mode": "clear_recommendation",
        }

        asked = []
        while not current["completed"]:
            asked.append(current["question_id"])
            current = answer_calibration_question(self.root, current["session_id"], answers[current["question_id"]])

        self.assertLessEqual(len(asked), 5)
        self.assertEqual(asked, ["recent_moment", "reply_shape", "interruption_tolerance", "annoyances", "decision_mode"])

    def _write_rewrite_backend(self, body: str) -> Path:
        path = self.root / "rewrite_backend.py"
        path.write_text(body, encoding="utf-8")
        return path

    def test_calibration_interview_materializes_profile(self) -> None:
        result = self._complete_calibration()

        self.assertTrue(result["completed"])
        profile = load_personal_interface_profile(self.root)
        self.assertEqual(profile["profile_version"], 1)
        self.assertIn("baseline_preferences", profile)
        self.assertIn("rhetorical_preferences", profile)
        self.assertIn("mode_preferences", profile)
        self.assertIn("guardrails", profile)
        self.assertIn("interview_metadata", profile)
        self.assertTrue(session_events_path(self.root, result["session_id"]).exists())
        self.assertTrue(read_json(self.root / "product" / "personal_interface_v1" / "data" / "profile.json"))

    def test_rewrite_requires_profile(self) -> None:
        with self.assertRaises(PersonalInterfaceError) as ctx:
            rewrite_outgoing_message(
                self.root,
                draft_text="Long answer that might interrupt the user.",
                user_message="help me think this through",
            )

        self.assertEqual(ctx.exception.code, "profile_missing")

    def test_rewrite_uses_declared_mode_and_records_event(self) -> None:
        self._complete_calibration()
        backend = self._write_rewrite_backend(
            """
import json, sys
payload = json.loads(sys.stdin.read())
print(json.dumps({
    "adapted_text": "Short answer. Keep going.",
    "backend_metadata": {
        "echo_mode": payload["policy"]["mode"],
        "compiled_turn_policy": payload["compiled_turn_policy"],
        "rewrite_prompt": payload["rewrite_prompt"]
    }
}))
"""
        )
        runtime_path = self.root / "product" / "personal_interface_v1" / "data" / "runtime.json"
        runtime_path.parent.mkdir(parents=True, exist_ok=True)
        runtime_path.write_text(
            json.dumps(
                {
                    "rewrite_backend": {
                        "id": "command_json",
                        "command": ["python3", str(backend)],
                        "timeout_seconds": 10,
                    }
                }
            ),
            encoding="utf-8",
        )

        rewritten = rewrite_outgoing_message(
            self.root,
            draft_text="Here are several options, multiple tangents, and a long explanation.",
            user_message="I am brain dumping, do not slow me down",
            caller_hints={"declared_mode": "capture_flow"},
        )

        self.assertEqual(rewritten["policy_metadata"]["mode"], "capture_flow")
        self.assertEqual(rewritten["policy_metadata"]["communication_mode"], "scaffolded_guidance")
        self.assertEqual(rewritten["policy_metadata"]["communication_axes"]["directionality"], "guiding")
        self.assertIn("reduce_branching", rewritten["policy_metadata"]["applied_tactics"])
        self.assertEqual(rewritten["adapted_text"], "Short answer. Keep going.")
        self.assertIn("Communication mode: scaffolded_guidance.", rewritten["policy_metadata"]["compiled_turn_policy"])
        self.assertIn("Write a concise reply that keeps the user moving.", rewritten["policy_metadata"]["compiled_turn_policy"])
        self.assertIn("instruction_bundle", rewritten["policy_metadata"])
        self.assertIn("suppressed_instruction_keys", rewritten["policy_metadata"])
        events = read_jsonl(self.root / "product" / "personal_interface_v1" / "data" / "rewrite_events.jsonl")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["policy"]["mode"], "capture_flow")
        self.assertEqual(events[0]["policy"]["communication_mode"], "scaffolded_guidance")
        self.assertIn("compiled_turn_policy", events[0])
        self.assertIn("rewrite_prompt", events[0])
        self.assertIn("instruction_bundle", events[0]["compiled_turn_policy"])
        self.assertNotIn('reply_shape = "push_forward"', events[0]["backend_metadata"]["rewrite_prompt"])
        self.assertIn("Current mode: capture_flow.", events[0]["backend_metadata"]["rewrite_prompt"])

    def test_feedback_updates_policy_snapshot(self) -> None:
        self.test_rewrite_uses_declared_mode_and_records_event()
        events = read_jsonl(self.root / "product" / "personal_interface_v1" / "data" / "rewrite_events.jsonl")
        result = record_rewrite_feedback(self.root, events[0]["rewrite_event_id"], "too_interruptive")

        self.assertEqual(result["feedback_state"], "too_interruptive")
        snapshot = load_personal_interface_policy_snapshot(self.root)
        self.assertEqual(snapshot["feedback_count"], 1)
        self.assertEqual(snapshot["too_interruptive_count"], 1)
        self.assertGreater(snapshot["tactic_penalties"]["reduce_branching"], 0)

    def test_ingest_learning_conversation_updates_profile_from_raw_text(self) -> None:
        self._complete_calibration()

        result = ingest_learning_conversation(
            self.root,
            source_text=(
                "User: What does this architecture mean in practice?\n"
                "Assistant: It means...\n"
                "User: Can you give me a concrete product example?\n"
                "Assistant: Example...\n"
                "User: Can you show how that becomes code modules or interfaces?\n"
            ),
            source_label="uploaded-conversation",
        )

        self.assertGreaterEqual(result["analysis"]["user_question_count"], 3)
        self.assertIn("concrete_example", result["analysis"]["example_preferences"])
        self.assertIn("technical_mapping", result["analysis"]["followup_preferences"])
        profile = load_personal_interface_profile(self.root)
        self.assertIn("learned_from_conversations", profile["learning_preferences"])
        learned = profile["learning_preferences"]["learned_from_conversations"]
        self.assertTrue(learned["enabled"])
        self.assertIn("concrete_example", learned["example_preferences"])
        self.assertIn("pattern_to_example_to_implementation", learned["guiding_path"])
        self.assertIn("followup_dynamics", learned)

    def test_ingest_learning_conversation_reads_followup_dynamics_and_answer_relevance(self) -> None:
        self._complete_calibration()

        result = ingest_learning_conversation(
            self.root,
            source_text=(
                "User: What does this architecture mean in practice?\n"
                "Assistant: It means the system separates capture from derived processing.\n"
                "User: When you say separate capture from derived processing, do you mean different modules?\n"
                "Assistant: Yes, likely separate modules.\n"
                "User: Going back to my original question, what does that change in the product experience?\n"
            ),
            source_label="followup-dynamics",
        )

        dynamics = result["analysis"]["followup_dynamics"]
        self.assertGreaterEqual(dynamics["answer_reference_count"], 1)
        self.assertGreaterEqual(dynamics["self_reference_count"], 1)
        self.assertIn("clarification", dynamics["intent_types"])
        self.assertIn("return_to_user_goal", dynamics["intent_types"])
        self.assertIn(result["analysis"]["answer_relevance_signal"], {"high", "medium"})

    def test_ingest_learning_conversation_accepts_file_url(self) -> None:
        self._complete_calibration()
        source = self.root / "learning-source.txt"
        source.write_text(
            (
                "User: Why does this abstraction matter?\n"
                "Assistant: Because...\n"
                "User: Give me a code example.\n"
                "Assistant: Example...\n"
            ),
            encoding="utf-8",
        )

        result = ingest_learning_conversation(
            self.root,
            source_url=source.resolve().as_uri(),
            source_label="shared-link",
        )

        self.assertEqual(result["source"]["kind"], "url")
        self.assertIn("code_example", result["analysis"]["example_preferences"])

    def test_compile_turn_policy_uses_learned_followup_path_for_learning_mode(self) -> None:
        self._complete_calibration()
        ingest_learning_conversation(
            self.root,
            source_text=(
                "User: What pattern is this?\n"
                "Assistant: Pattern...\n"
                "User: Give me a concrete example.\n"
                "Assistant: Example...\n"
                "User: Now map that into modules and interfaces.\n"
            ),
            source_label="learning-seed",
        )
        profile = load_personal_interface_profile(self.root)

        compiled = compile_turn_policy(
            profile=profile,
            mode="development_flow",
            confidence=0.84,
            communication_mode="concept_translation",
            communication_axes={
                "primary_function": "translate",
                "directionality": "guiding",
                "stance": "precise",
            },
            caller_hints={"goal": "teach_user"},
            policy_snapshot={"tactic_penalties": {}},
        )

        joined = "\n".join(compiled["instruction_lines"])
        self.assertIn("Follow the user's learned path when teaching: pattern_to_example_to_implementation.", joined)
        self.assertIn("Prefer these observed example types when they fit: concrete_example.", joined)
        self.assertIn("End with the next technical mapping step when possible.", joined)

    def test_compile_turn_policy_uses_learned_followup_dynamics_for_teaching(self) -> None:
        self._complete_calibration()
        ingest_learning_conversation(
            self.root,
            source_text=(
                "User: What does this architecture mean in practice?\n"
                "Assistant: It means the system separates capture from derived processing.\n"
                "User: When you say separate capture from derived processing, do you mean different modules?\n"
                "Assistant: Yes, separate modules.\n"
                "User: Going back to my original question, what does that change in the product experience?\n"
            ),
            source_label="followup-style-seed",
        )
        profile = load_personal_interface_profile(self.root)

        compiled = compile_turn_policy(
            profile=profile,
            mode="development_flow",
            confidence=0.82,
            communication_mode="concept_translation",
            communication_axes={
                "primary_function": "translate",
                "directionality": "guiding",
                "stance": "precise",
            },
            caller_hints={"goal": "teach_user"},
            policy_snapshot={"tactic_penalties": {}},
        )

        joined = "\n".join(compiled["instruction_lines"])
        self.assertIn("Make key terms easy to point back to because the user often follows up on your exact wording.", joined)
        self.assertIn("Reconnect explanations to the user's original question after local clarifications.", joined)

    def test_rewrite_conversation_turn_derives_context_from_conversation(self) -> None:
        self._complete_calibration()
        backend = self._write_rewrite_backend(
            """
import json, sys
payload = json.loads(sys.stdin.read())
print(json.dumps({
    "adapted_text": "Translated response.",
    "backend_metadata": {
        "user_message": payload["user_message"],
        "conversation_window": payload["conversation_window"],
        "client_context": payload["client_context"]
    }
}))
"""
        )
        runtime_path = self.root / "product" / "personal_interface_v1" / "data" / "runtime.json"
        runtime_path.parent.mkdir(parents=True, exist_ok=True)
        runtime_path.write_text(
            json.dumps(
                {
                    "rewrite_backend": {
                        "id": "command_json",
                        "command": ["python3", str(backend)],
                        "timeout_seconds": 10,
                    }
                }
            ),
            encoding="utf-8",
        )

        rewritten = rewrite_conversation_turn(
            self.root,
            draft_text="Here is a long answer with too much framing.",
            conversation=[
                {"role": "system", "content": "You are a coding agent."},
                {"role": "user", "content": "I am thinking out loud about the product direction.", "turn_id": "turn-1"},
                {"role": "assistant", "content": "What direction are you considering?", "turn_id": "turn-2"},
                {"role": "user", "content": "I want a translation layer from abstract concepts into technical modules.", "turn_id": "turn-3"},
            ],
            caller_hints={"goal": "translate_concepts_to_technical"},
            client_context={"conversation_id": "conv-123"},
            window_size=3,
        )

        self.assertEqual(rewritten["adapted_text"], "Translated response.")
        self.assertEqual(rewritten["policy_metadata"]["communication_mode"], "concept_translation")
        events = read_jsonl(self.root / "product" / "personal_interface_v1" / "data" / "rewrite_events.jsonl")
        backend_metadata = events[0]["backend_metadata"]
        self.assertEqual(backend_metadata["user_message"], "I want a translation layer from abstract concepts into technical modules.")
        self.assertEqual(len(backend_metadata["conversation_window"]), 3)
        self.assertEqual(backend_metadata["client_context"]["conversation_id"], "conv-123")
        self.assertEqual(backend_metadata["client_context"]["latest_user_turn_id"], "turn-3")
        self.assertEqual(backend_metadata["client_context"]["conversation_turn_count"], 4)

    def test_cli_rewrite_turn_accepts_conversation_json(self) -> None:
        self._complete_calibration()
        backend = self._write_rewrite_backend(
            """
import json, sys
payload = json.loads(sys.stdin.read())
print(json.dumps({
    "adapted_text": payload["user_message"],
    "backend_metadata": payload["client_context"]
}))
"""
        )
        runtime_path = self.root / "product" / "personal_interface_v1" / "data" / "runtime.json"
        runtime_path.parent.mkdir(parents=True, exist_ok=True)
        runtime_path.write_text(
            json.dumps(
                {
                    "rewrite_backend": {
                        "id": "command_json",
                        "command": ["python3", str(backend)],
                        "timeout_seconds": 10,
                    }
                }
            ),
            encoding="utf-8",
        )

        exit_code, result = self._run_cli(
            [
                "personal-interface",
                "rewrite-turn",
                "--draft-text",
                "Draft reply",
                "--conversation-json",
                json.dumps(
                    [
                        {"role": "user", "content": "First"},
                        {"role": "assistant", "content": "Second"},
                        {"role": "user", "content": "Latest abstract product thought", "turn_id": "u-2"},
                    ]
                ),
                "--caller-hints-json",
                json.dumps({"goal": "translate_concepts_to_technical"}),
                "--client-context-json",
                json.dumps({"conversation_id": "cli-conv"}),
            ]
        )

        self.assertEqual(exit_code, 0)
        self.assertEqual(result["adapted_text"], "Latest abstract product thought")
        self.assertEqual(result["policy_metadata"]["communication_mode"], "concept_translation")

    def test_cli_personal_interface_flow(self) -> None:
        exit_code, started = self._run_cli(["personal-interface", "calibrate-start"])
        self.assertEqual(exit_code, 0)
        self.assertIn("session_id", started)

        current = started
        scripted_answers = {
            "recent_moment": "slowed_me_down",
            "reply_shape": "push_forward",
            "interruption_tolerance": "flag_gently",
            "annoyances": "too_long,too_many_options",
            "decision_mode": "clear_recommendation",
        }
        while not current["completed"]:
            exit_code, current = self._run_cli(
                [
                    "personal-interface",
                    "calibrate-answer",
                    "--session-id",
                    current["session_id"],
                    "--answer",
                    scripted_answers[current["question_id"]],
                ]
            )
            self.assertEqual(exit_code, 0)

        exit_code, profile = self._run_cli(["personal-interface", "profile"])
        self.assertEqual(exit_code, 0)
        self.assertIn("baseline_preferences", profile)

    def test_cli_personal_interface_learning_import(self) -> None:
        self._complete_calibration()
        exit_code, result = self._run_cli(
            [
                "personal-interface",
                "learn",
                "--source-text",
                "User: What is the concept?\\nAssistant: ...\\nUser: Give me a concrete example.\\nAssistant: ...\\nUser: How does it become code?",
                "--source-label",
                "cli-learning",
            ]
        )
        self.assertEqual(exit_code, 0)
        self.assertIn("analysis", result)
        self.assertIn("concrete_example", result["analysis"]["example_preferences"])

    def test_cli_personal_interface_doctor_reports_readiness(self) -> None:
        backend = self._write_rewrite_backend(
            """
import json, sys
payload = json.loads(sys.stdin.read())
print(json.dumps({\"adapted_text\": payload[\"draft_text\"], \"backend_metadata\": {}}))
"""
        )
        runtime_path = self.root / "product" / "personal_interface_v1" / "data" / "runtime.json"
        runtime_path.parent.mkdir(parents=True, exist_ok=True)
        runtime_path.write_text(
            json.dumps(
                {
                    "rewrite_backend": {
                        "id": "command_json",
                        "command": ["python3", str(backend)],
                        "timeout_seconds": 10,
                    }
                }
            ),
            encoding="utf-8",
        )
        self._complete_calibration()

        exit_code, doctor = self._run_cli(["personal-interface", "doctor"])
        self.assertEqual(exit_code, 0)
        self.assertTrue(doctor["ready"])
        self.assertEqual(doctor["checks"]["profile"]["status"], "ok")
        self.assertEqual(doctor["checks"]["runtime"]["status"], "ok")

    def test_profile_builder_uses_descriptive_choices(self) -> None:
        profile = build_personal_interface_profile(
            {
                "recent_moment": {"choice": "slowed_me_down", "note": "Long replies make me lose the thread."},
                "reply_shape": {"choice": "push_forward", "note": ""},
                "interruption_tolerance": {"choice": "flag_gently", "note": ""},
                "annoyances": {"choice": ["too_long", "too_many_options", "soft_prefacing"], "note": ""},
                "decision_mode": {"choice": "clear_recommendation", "note": ""},
            }
        )

        self.assertEqual(profile["baseline_preferences"]["verbosity"], "concise")
        self.assertEqual(profile["baseline_preferences"]["branching_tolerance"], "low")
        self.assertEqual(profile["baseline_preferences"]["challenge_tolerance"], "medium")
        self.assertIn("too many options", profile["rhetorical_preferences"]["disliked_patterns"])
        self.assertEqual(profile["mode_preferences"]["decision_style"], "clear_recommendation")
        self.assertIn("communication_preferences", profile)
        self.assertEqual(profile["communication_preferences"]["directionality_preference"], "guiding")
        self.assertEqual(profile["communication_preferences"]["stance_preference"], "balanced")
        self.assertEqual(profile["communication_preferences"]["default_mode"], "scaffolded_guidance")

    def test_identify_communication_mode_prefers_decisive_direction_for_fast_decisions(self) -> None:
        profile = build_personal_interface_profile(
            {
                "recent_moment": {"choice": "slowed_me_down", "note": "Long replies make me lose the thread."},
                "reply_shape": {"choice": "push_forward", "note": ""},
                "interruption_tolerance": {"choice": "challenge_if_high_stakes", "note": ""},
                "annoyances": {"choice": ["too_long", "too_many_options"], "note": ""},
                "decision_mode": {"choice": "clear_recommendation", "note": ""},
                "energy": {"choice": "direct_plain", "note": ""},
            }
        )

        communication = identify_communication_mode(
            user_message="Which option should I choose? I need the fastest call.",
            draft_text="I recommend option A. Here is the shortest justification.",
            flow_mode="decision_flow",
            caller_hints={"goal": "choose_best_option", "desired_depth": "short", "urgency": "high"},
            profile=profile,
        )

        self.assertEqual(communication["mode"], "decisive_direction")
        self.assertEqual(communication["axes"]["primary_function"], "recommend")
        self.assertEqual(communication["axes"]["directionality"], "directing")
        self.assertGreaterEqual(communication["confidence"], 0.7)

    def test_identify_communication_mode_prefers_exploratory_probe_when_generating_options(self) -> None:
        profile = build_personal_interface_profile(
            {
                "recent_moment": {"choice": "mixed", "note": "It depends on whether I am opening the space or closing it."},
                "reply_shape": {"choice": "tight_scaffold", "note": ""},
                "interruption_tolerance": {"choice": "flag_gently", "note": ""},
                "annoyances": {"choice": ["too_long"], "note": ""},
                "decision_mode": {"choice": "compare_tradeoffs", "note": ""},
            }
        )

        communication = identify_communication_mode(
            user_message="Let's explore a few directions before we decide.",
            draft_text="A few sharp questions may open the space: what constraint matters most, what would we test first?",
            flow_mode="exploratory_flow",
            caller_hints={"goal": "generate_options", "desired_depth": "deep"},
            profile=profile,
        )

        self.assertEqual(communication["mode"], "exploratory_probe")
        self.assertEqual(communication["axes"]["primary_function"], "probe")
        self.assertEqual(communication["axes"]["directionality"], "guiding")
        self.assertGreaterEqual(communication["confidence"], 0.65)

    def test_profile_builder_includes_translation_preferences_for_product_ideation(self) -> None:
        profile = build_personal_interface_profile(
            {
                "recent_moment": {"choice": "kept_momentum", "note": "The best replies translated the product idea into real system pieces."},
                "reply_shape": {"choice": "principle_first", "note": ""},
                "interruption_tolerance": {"choice": "flag_gently", "note": ""},
                "annoyances": {"choice": ["generic_rephrasing", "abstract_without_grounding"], "note": ""},
                "decision_mode": {"choice": "compare_tradeoffs", "note": ""},
                "energy": {"choice": "skeptical_precise", "note": ""},
            }
        )

        self.assertIn("translation_preferences", profile)
        self.assertTrue(profile["translation_preferences"]["enabled"])
        self.assertEqual(profile["translation_preferences"]["preferred_mode"], "concept_translation")
        self.assertIn("components", profile["translation_preferences"]["target_artifacts"])
        self.assertIn("confirmed_intent", profile["translation_preferences"]["output_contract"])
        self.assertIn("inferred_mapping", profile["translation_preferences"]["output_contract"])

    def test_identify_communication_mode_prefers_concept_translation_for_abstract_product_language(self) -> None:
        profile = build_personal_interface_profile(
            {
                "recent_moment": {"choice": "kept_momentum", "note": "Translate my abstract product thoughts into a technical frame."},
                "reply_shape": {"choice": "principle_first", "note": ""},
                "interruption_tolerance": {"choice": "flag_gently", "note": ""},
                "annoyances": {"choice": ["generic_rephrasing", "abstract_without_grounding"], "note": ""},
                "decision_mode": {"choice": "compare_tradeoffs", "note": ""},
                "energy": {"choice": "skeptical_precise", "note": ""},
            }
        )

        communication = identify_communication_mode(
            user_message="I'm thinking out loud about the product architecture and trying to connect overarching concepts and patterns.",
            draft_text="This probably wants a translation layer that maps the abstract product language into modules, contracts, and stateful workflows.",
            flow_mode="development_flow",
            caller_hints={"goal": "translate_concepts_to_technical"},
            profile=profile,
        )

        self.assertEqual(communication["mode"], "concept_translation")
        self.assertEqual(communication["axes"]["primary_function"], "translate")
        self.assertEqual(communication["axes"]["stance"], "precise")
        self.assertGreaterEqual(communication["confidence"], 0.7)

    def test_compile_turn_policy_returns_behavioral_guidance_not_raw_tags(self) -> None:
        profile = build_personal_interface_profile(
            {
                "recent_moment": {"choice": "slowed_me_down", "note": "Long replies make me lose the thread."},
                "reply_shape": {"choice": "push_forward", "note": ""},
                "interruption_tolerance": {"choice": "flag_gently", "note": ""},
                "annoyances": {"choice": ["too_long", "too_many_options"], "note": ""},
                "decision_mode": {"choice": "clear_recommendation", "note": ""},
            }
        )

        compiled = compile_turn_policy(
            profile=profile,
            mode="capture_flow",
            confidence=0.91,
            communication_mode="scaffolded_guidance",
            communication_axes={
                "primary_function": "guide",
                "directionality": "guiding",
                "stance": "balanced",
            },
            caller_hints={},
            policy_snapshot={"tactic_penalties": {}},
        )

        self.assertEqual(compiled["mode"], "capture_flow")
        self.assertEqual(compiled["communication_mode"], "scaffolded_guidance")
        self.assertIn("Communication mode: scaffolded_guidance.", compiled["instruction_lines"])
        self.assertIn("Write a concise reply that keeps the user moving.", compiled["instruction_lines"])
        self.assertIn("Do not branch into multiple options unless necessary.", compiled["instruction_lines"])
        self.assertIn("If you flag a weak assumption, do it briefly without derailing the thread.", compiled["instruction_lines"])
        joined = "\n".join(compiled["instruction_lines"])
        self.assertNotIn('reply_shape = "push_forward"', joined)
        self.assertNotIn('branching_tolerance = "low"', joined)
        self.assertIn("instruction_bundle", compiled)
        self.assertLessEqual(len(compiled["instruction_lines"]), 8)

    def test_compile_turn_policy_includes_translation_layer_guidance_for_concept_translation(self) -> None:
        profile = build_personal_interface_profile(
            {
                "recent_moment": {"choice": "kept_momentum", "note": "Translate the product idea into technical language."},
                "reply_shape": {"choice": "principle_first", "note": ""},
                "interruption_tolerance": {"choice": "flag_gently", "note": ""},
                "annoyances": {"choice": ["generic_rephrasing", "abstract_without_grounding"], "note": ""},
                "decision_mode": {"choice": "compare_tradeoffs", "note": ""},
                "energy": {"choice": "skeptical_precise", "note": ""},
            }
        )

        compiled = compile_turn_policy(
            profile=profile,
            mode="development_flow",
            confidence=0.87,
            communication_mode="concept_translation",
            communication_axes={
                "primary_function": "translate",
                "directionality": "guiding",
                "stance": "precise",
            },
            caller_hints={"goal": "translate_concepts_to_technical"},
            policy_snapshot={"tactic_penalties": {}},
        )

        joined = "\n".join(compiled["instruction_lines"])
        self.assertEqual(compiled["communication_mode"], "concept_translation")
        self.assertIn("Communication mode: concept_translation.", compiled["instruction_lines"])
        self.assertIn("Translate abstract product language into explicit software constructs and engineering terms.", joined)
        self.assertIn("Separate confirmed intent from inferred implementation mapping whenever the translation is not fully certain.", joined)

    def test_compile_turn_policy_ranks_goal_and_depth_specific_instructions(self) -> None:
        profile = build_personal_interface_profile(
            {
                "recent_moment": {"choice": "slowed_me_down", "note": "Long replies make me lose the thread."},
                "reply_shape": {"choice": "tight_scaffold", "note": ""},
                "interruption_tolerance": {"choice": "flag_gently", "note": ""},
                "annoyances": {"choice": ["too_long"], "note": ""},
                "decision_mode": {"choice": "clear_recommendation", "note": ""},
            }
        )

        compiled = compile_turn_policy(
            profile=profile,
            mode="decision_flow",
            confidence=0.88,
            communication_mode="decisive_direction",
            communication_axes={
                "primary_function": "recommend",
                "directionality": "directing",
                "stance": "assertive",
            },
            caller_hints={"goal": "choose_best_option", "desired_depth": "short", "urgency": "high"},
            policy_snapshot={"tactic_penalties": {}},
        )

        self.assertEqual(compiled["instruction_lines"][0], "Current mode: decision_flow.")
        self.assertIn("Communication mode: decisive_direction.", compiled["instruction_lines"])
        self.assertIn("Give a clear recommendation once the main tradeoff is understood.", compiled["instruction_lines"])
        self.assertIn("Bias toward the shortest useful reply.", compiled["instruction_lines"])
        self.assertIn("Optimize for a fast decision rather than broad exploration.", compiled["instruction_lines"])
        self.assertIn("Lead with the answer before supporting detail.", compiled["instruction_lines"])
        self.assertGreaterEqual(compiled["instruction_bundle"][0]["priority"], compiled["instruction_bundle"][-1]["priority"])

    def test_compile_turn_policy_uses_feedback_penalties_to_suppress_low_value_instructions(self) -> None:
        profile = build_personal_interface_profile(
            {
                "recent_moment": {"choice": "slowed_me_down", "note": "Walls of text break momentum."},
                "reply_shape": {"choice": "push_forward", "note": ""},
                "interruption_tolerance": {"choice": "flag_gently", "note": ""},
                "annoyances": {"choice": ["too_long", "heavy_formatting"], "note": ""},
                "decision_mode": {"choice": "compare_tradeoffs", "note": ""},
            }
        )

        compiled = compile_turn_policy(
            profile=profile,
            mode="capture_flow",
            confidence=0.8,
            communication_mode="scaffolded_guidance",
            communication_axes={
                "primary_function": "guide",
                "directionality": "guiding",
                "stance": "balanced",
            },
            caller_hints={},
            policy_snapshot={"tactic_penalties": {"reduce_branching": 0.35, "compress_response": 0.05}},
        )

        self.assertIn("Write a concise reply that keeps the user moving.", compiled["instruction_lines"])
        self.assertNotIn("Do not branch into multiple options unless necessary.", compiled["instruction_lines"])
        self.assertIn("suppressed_instruction_keys", compiled)
        self.assertIn("reduce_branching", compiled["suppressed_instruction_keys"])

    def test_mcp_server_registers_tools(self) -> None:
        if importlib.util.find_spec("mcp") is None:
            self.skipTest("mcp SDK not installed in active interpreter")
        server = build_personal_interface_mcp_server(self.root)
        tool_names = [tool.name for tool in asyncio.run(server.list_tools())]
        self.assertEqual(
            tool_names,
            [
                "start_calibration_interview",
                "answer_calibration_question",
                "get_profile_snapshot",
                "ingest_learning_conversation",
                "rewrite_conversation_turn",
                "rewrite_outgoing_message",
                "record_rewrite_feedback",
            ],
        )


if __name__ == "__main__":
    unittest.main()
