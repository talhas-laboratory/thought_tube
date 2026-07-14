from __future__ import annotations

from conversation_os.builder_behavior import (
    build_builder_chat_response,
    compose_builder_packet_input,
)


def test_builder_behavior_starts_discovery_for_greeting_only() -> None:
    response = build_builder_chat_response(
        "hi",
        requested_meta_state="operate",
    )

    assert response["builder_state"]["phase"] == "discovery"
    assert response["builder_state"]["candidate_objective"] == ""
    assert response["builder_state"]["pending_question"] == "objective_discovery"
    assert response["interpretation"]["should_create_packet"] is False
    assert "What do you want to work on" in response["assistant_text"]


def test_builder_behavior_starts_with_objective_confirmation_for_direct_request() -> None:
    response = build_builder_chat_response(
        "make the notes app reply less verbose",
        requested_meta_state="operate",
    )

    assert response["builder_state"]["phase"] == "objective_confirmation"
    assert response["builder_state"]["candidate_objective"] == "make the notes app reply less verbose"
    assert response["interpretation"]["should_create_packet"] is False
    assert "I think you're trying to" in response["assistant_text"]


def test_builder_behavior_accumulates_conversation_and_reframes_analysis_request() -> None:
    response = build_builder_chat_response(
        "yes lets have a conversation about the UI",
        requested_meta_state="operate",
        builder_state={
            "phase": "discovery",
            "pending_question": "objective_discovery",
            "conversation_view": {"turn_history": ["hi"]},
        },
    )
    assert response["builder_state"]["candidate_objective"] == "lets have a conversation about the UI"
    assert response["builder_state"]["pending_question"] == "objective_confirmation"

    response = build_builder_chat_response(
        "what is your opinion on the current ui",
        requested_meta_state="operate",
        builder_state=response["builder_state"],
    )

    assert response["builder_state"]["phase"] == "discovery"
    assert response["builder_state"]["pending_question"] == "analysis_focus"
    assert response["builder_state"]["conversation_view"]["needs_analysis"] is True
    assert "evaluate the current UI and discuss improvements" in response["builder_state"]["candidate_objective"]
    assert "which part should we look at first" in response["assistant_text"].lower()
    assert response["interpretation"]["should_create_packet"] is False


def test_builder_behavior_confirms_then_requests_missing_acceptance_criteria() -> None:
    response = build_builder_chat_response(
        "yes",
        requested_meta_state="operate",
        builder_state={
            "phase": "objective_confirmation",
            "candidate_objective": "make the notes app reply less verbose",
            "confirmed_objective": "",
            "objective_confirmed": False,
            "pending_question": "objective_confirmation",
            "acceptance_criteria": "",
        },
        workspace_context={
            "workspace_id": "inner-world",
            "repository": {"changed_files": ["product/thought_capture_pwa/src/app.tsx"], "source_revision": "abc123"},
            "orientation": {"blockers": [], "open_threads": ["capture reply length"]},
        },
    )

    assert response["builder_state"]["phase"] == "clarification"
    assert response["builder_state"]["objective_confirmed"] is True
    assert response["interpretation"]["should_create_packet"] is False
    assert "I checked the current workspace context" in response["assistant_text"]
    assert "What should count as done" in response["assistant_text"]


def test_builder_behavior_analysis_request_does_not_become_acceptance_criteria() -> None:
    response = build_builder_chat_response(
        "what is your opinion on the current ui",
        requested_meta_state="operate",
        builder_state={
            "phase": "clarification",
            "candidate_objective": "evaluate the current UI and discuss improvements before deciding what to change",
            "confirmed_objective": "evaluate the current UI and discuss improvements before deciding what to change",
            "objective_confirmed": True,
            "pending_question": "acceptance_criteria",
            "acceptance_criteria": "",
        },
    )

    assert response["builder_state"]["phase"] == "discovery"
    assert response["builder_state"]["pending_question"] == "analysis_focus"
    assert response["builder_state"]["acceptance_criteria"] == ""
    assert response["interpretation"]["should_create_packet"] is False
    assert "which part should we look at first" in response["assistant_text"].lower()


def test_builder_behavior_soft_resets_stale_session_on_greeting() -> None:
    response = build_builder_chat_response(
        "hi",
        requested_meta_state="operate",
        builder_state={
            "phase": "scoping",
            "candidate_objective": "evaluate the current UI and discuss improvements before deciding what to change",
            "confirmed_objective": "evaluate the current UI and discuss improvements before deciding what to change",
            "objective_confirmed": True,
            "pending_question": "",
            "acceptance_criteria": "identify the strongest UI issues",
        },
    )

    assert response["builder_state"]["phase"] == "discovery"
    assert response["builder_state"]["pending_question"] == "objective_discovery"
    assert response["builder_state"]["candidate_objective"] == ""
    assert response["builder_state"]["conversation_view"]["last_stable_intent"] == (
        "evaluate the current UI and discuss improvements before deciding what to change"
    )
    assert "start fresh" in response["assistant_text"].lower()


def test_builder_behavior_stale_session_analysis_request_stays_conversational() -> None:
    response = build_builder_chat_response(
        "what is your opinion on the current ui",
        requested_meta_state="operate",
        builder_state={
            "phase": "scoping",
            "candidate_objective": "evaluate the current UI and discuss improvements before deciding what to change",
            "confirmed_objective": "evaluate the current UI and discuss improvements before deciding what to change",
            "objective_confirmed": True,
            "pending_question": "",
            "acceptance_criteria": "identify the strongest UI issues",
        },
    )

    assert response["builder_state"]["phase"] == "discovery"
    assert response["builder_state"]["pending_question"] == "analysis_focus"
    assert response["builder_state"]["conversation_view"]["needs_analysis"] is True
    assert response["interpretation"]["should_create_packet"] is False
    assert "which part should we look at first" in response["assistant_text"].lower()


def test_builder_behavior_scopes_work_after_missing_information_is_supplied() -> None:
    response = build_builder_chat_response(
        "Keep replies short, but preserve action items and concrete next steps.",
        requested_meta_state="operate",
        builder_state={
            "phase": "clarification",
            "candidate_objective": "make the notes app reply less verbose",
            "confirmed_objective": "make the notes app reply less verbose",
            "objective_confirmed": True,
            "pending_question": "acceptance_criteria",
            "acceptance_criteria": "",
        },
        workspace_context={
            "workspace_id": "inner-world",
            "repository": {"changed_files": ["product/thought_capture_pwa/src/app.tsx"], "source_revision": "abc123"},
            "orientation": {"blockers": [], "open_threads": ["capture reply length"]},
        },
    )

    assert response["builder_state"]["phase"] == "scoping"
    assert response["builder_state"]["acceptance_criteria"] == "Keep replies short, but preserve action items and concrete next steps."
    assert response["interpretation"]["should_create_packet"] is True
    assert response["builder_scope"]["tests"] == ["golden_conversation_examples", "prompt_diff", "bridge_trace_review"]
    assert "Scope" in response["assistant_text"]


def test_compose_builder_packet_input_uses_confirmed_objective_and_scope() -> None:
    text = compose_builder_packet_input(
        "fallback raw text",
        {
            "confirmed_objective": "make the notes app reply less verbose",
            "acceptance_criteria": "Keep replies short and preserve action items.",
        },
        {
            "summary": "Update capture reply behavior and test the shorter response path.",
            "tests": ["golden_conversation_examples"],
        },
    )

    assert "Objective: make the notes app reply less verbose" in text
    assert "Acceptance criteria: Keep replies short and preserve action items." in text
    assert "Planned scope: Update capture reply behavior and test the shorter response path." in text
