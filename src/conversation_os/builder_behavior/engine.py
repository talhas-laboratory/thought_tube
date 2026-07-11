from __future__ import annotations

from copy import deepcopy
import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict

from ..self_improvement_domains import DOMAIN_RISK, DOMAIN_TESTS, classify_feedback_domain


ROOT = Path(__file__).resolve().parents[3]
IDENTITY_CONFIG_PATH = ROOT / "product" / "inner_world_v1" / "config" / "agent_configs" / "inner_space_meta.json"

DEFAULT_STATE: Dict[str, Any] = {
    "phase": "intake",
    "candidate_objective": "",
    "confirmed_objective": "",
    "objective_confirmed": False,
    "pending_question": "",
    "acceptance_criteria": "",
    "target_meta_state": "discuss",
    "workspace_task_id": "",
    "claim_status": "",
    "pending_completion_field": "",
    "completion_draft": {},
    "conversation_view": {
        "turn_history": [],
        "working_intent": "",
        "missing_information": ["objective"],
        "open_questions": [],
        "needs_analysis": False,
    },
}

AFFIRMATIVE_WORDS = {"yes", "yep", "yeah", "correct", "that is right", "thats right", "exactly", "confirm"}
NEGATIVE_WORDS = {"no", "not quite", "incorrect", "wrong"}
GREETING_WORDS = {"hi", "hello", "hey", "yo", "sup"}
RESTART_WORDS = {"hi", "hello", "hey", "yo", "sup", "okay", "ok"}


@lru_cache(maxsize=1)
def _identity_config() -> Dict[str, Any]:
    fallback = {
        "agent_id": "inner_space_meta",
        "conversation_profile": {
            "opening_prompt": "What do you want to work on or figure out?",
            "restart_prompt": "We can start fresh or keep going on the previous thread. What do you want to work on right now?",
            "objective_confirmation_prefix": "I think you're trying to",
            "acceptance_question": "What should count as done if we turn that into work?",
            "analysis_transition": "I can think through the current state with you first, then turn that into scoped work once the goal is clearer.",
            "analysis_without_context": "My current read is still broad. I do not have enough concrete product context yet to judge the current state directly, so I want to narrow it first.",
            "analysis_follow_up_ui": "If this is about the UI, which part should we look at first: capture, reading, navigation, or overall feel?",
            "fallback_continue": "I can keep talking this through with you. Tell me what feels off, what outcome you want, or what part you want me to judge first.",
        },
    }
    if not IDENTITY_CONFIG_PATH.exists():
        return fallback
    try:
        payload = json.loads(IDENTITY_CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return fallback
    merged = deepcopy(fallback)
    merged.update({key: value for key, value in payload.items() if key != "conversation_profile"})
    if isinstance(payload.get("conversation_profile"), dict):
        merged["conversation_profile"].update(payload["conversation_profile"])
    return merged


def _normalized_state(builder_state: Dict[str, Any] | None) -> Dict[str, Any]:
    state = deepcopy(DEFAULT_STATE)
    if isinstance(builder_state, dict):
        for key, value in builder_state.items():
            if key not in state:
                continue
            if key == "conversation_view" and isinstance(value, dict):
                state[key].update(value)
            else:
                state[key] = value
    return state


def _clean_text(text: str) -> str:
    return " ".join(str(text or "").strip().split())


def _is_affirmative(text: str) -> bool:
    lowered = _clean_text(text).lower()
    return lowered in AFFIRMATIVE_WORDS


def _is_negative(text: str) -> bool:
    lowered = _clean_text(text).lower()
    return lowered in NEGATIVE_WORDS


def _is_greeting(text: str) -> bool:
    lowered = _clean_text(text).lower()
    return lowered in GREETING_WORDS


def _is_restart_signal(text: str) -> bool:
    lowered = _clean_text(text).lower()
    return lowered in RESTART_WORDS


def _is_question(text: str) -> bool:
    lowered = _clean_text(text).lower()
    if "?" in text:
        return True
    return lowered.startswith(
        (
            "what ",
            "why ",
            "how ",
            "should ",
            "could ",
            "would ",
            "do you ",
            "can you ",
            "is it ",
            "what's ",
        )
    )


def _is_analysis_request(text: str) -> bool:
    lowered = _clean_text(text).lower()
    return _is_question(text) and any(
        token in lowered
        for token in ("opinion", "think", "current ui", "current ux", "current design", "assessment", "evaluate", "critique")
    )


def _is_opinion_prompt(text: str) -> bool:
    lowered = _clean_text(text).lower()
    return any(
        phrase in lowered
        for phrase in ("what do you think", "thoughts", "your opinion", "opinion on", "how does it feel", "what is your read")
    )


def _strip_leading_affirmation(text: str) -> str:
    lowered = _clean_text(text).lower()
    for token in sorted(AFFIRMATIVE_WORDS, key=len, reverse=True):
        if lowered == token:
            return ""
        prefix = token + " "
        if lowered.startswith(prefix):
            return _clean_text(text[len(prefix) :])
    return _clean_text(text)


def _workspace_summary(workspace_context: Dict[str, Any] | None) -> str:
    if not isinstance(workspace_context, dict) or not workspace_context:
        return ""
    workspace_id = str(workspace_context.get("workspace_id") or "").strip()
    repository = workspace_context.get("repository", {}) or {}
    orientation = workspace_context.get("orientation", {}) or {}
    changed_files = len(repository.get("changed_files", []) or [])
    blockers = len(orientation.get("blockers", []) or [])
    open_threads = len(orientation.get("open_threads", []) or [])
    revision = str(repository.get("source_revision") or "").strip() or "not observed"
    if not workspace_id:
        return ""
    return (
        f"I checked the current workspace context for {workspace_id}: "
        f"{changed_files} changed files, {blockers} active blockers, {open_threads} open threads, revision {revision}."
    )


def _scope_for_objective(objective: str, acceptance_criteria: str) -> Dict[str, Any]:
    domain = classify_feedback_domain(objective)
    tests = list(DOMAIN_TESTS.get(domain, []))
    summary = f"Define the minimal change for '{objective}', implement it, then verify it against the accepted outcome."
    if acceptance_criteria:
        summary = f"{summary} Acceptance criteria: {acceptance_criteria}"
    return {
        "domain": domain,
        "risk": DOMAIN_RISK.get(domain, "high"),
        "summary": summary,
        "tests": tests,
    }


def _suggest_claim_paths(domain: str, workspace_context: Dict[str, Any] | None) -> list[str]:
    workspace = (workspace_context or {}).get("workspace", {}) or {}
    artifact_roots = [str(item).strip() for item in list(workspace.get("artifact_roots", []) or []) if str(item).strip()]
    if not artifact_roots:
        return []
    preferred_by_domain = {
        "ui_ux": ("product/thought_capture_pwa/", "product/mobile_surface_v1/", "product/inner_world_v1/"),
        "agent_behavior": ("src/conversation_os/", "product/inner_world_v1/config/", "tools/"),
        "backend_setup": ("src/conversation_os/", "tools/", "ops/"),
        "tool_creation": ("tools/", "src/conversation_os/"),
        "thought_pipeline_config": ("src/conversation_os/", "product/inner_world_v1/"),
        "bridge_work": ("src/conversation_os/", "product/inner_world_v1/config/", "tools/"),
        "deployment_release": ("tools/", "ops/", "product/inner_world_v1/releases/"),
    }
    preferred = preferred_by_domain.get(domain, ())
    selected = [path for path in artifact_roots if any(path.startswith(prefix) for prefix in preferred)]
    return selected[:2] if selected else artifact_roots[:1]


def _conversation_view(state: Dict[str, Any]) -> Dict[str, Any]:
    view = state.get("conversation_view")
    if not isinstance(view, dict):
        view = deepcopy(DEFAULT_STATE["conversation_view"])
        state["conversation_view"] = view
    return view


def _remember_turn(state: Dict[str, Any], text: str) -> Dict[str, Any]:
    view = _conversation_view(state)
    history = list(view.get("turn_history", []) or [])
    if text:
        history.append(text)
    view["turn_history"] = history[-6:]
    return view


def _sync_view_from_state(state: Dict[str, Any]) -> None:
    view = _conversation_view(state)
    objective = _clean_text(state.get("confirmed_objective") or state.get("candidate_objective") or "")
    view["working_intent"] = objective
    missing: list[str] = []
    if not objective:
        missing.append("objective")
    if state.get("objective_confirmed") and not _clean_text(state.get("acceptance_criteria") or "") and not view.get("needs_analysis"):
        missing.append("acceptance_criteria")
    view["missing_information"] = missing
    questions: list[str] = []
    if missing:
        if "objective" in missing:
            questions.append("What are we trying to accomplish?")
        if "acceptance_criteria" in missing:
            questions.append("What should count as done?")
    if view.get("needs_analysis"):
        questions.append("Should I evaluate the current state first before turning it into scoped work?")
    view["open_questions"] = questions


def _set_candidate_objective(state: Dict[str, Any], objective: str, *, confirmed: bool = False) -> None:
    state["candidate_objective"] = _clean_text(objective)
    if confirmed:
        state["confirmed_objective"] = state["candidate_objective"]
        state["objective_confirmed"] = True
    _sync_view_from_state(state)


def _analysis_reframe(state: Dict[str, Any], text: str) -> str:
    prior = _clean_text(state.get("candidate_objective") or "")
    lowered = text.lower()
    if "ui" in lowered or "ux" in lowered or "design" in lowered:
        updated = "evaluate the current UI and discuss improvements before deciding what to change"
    elif prior:
        updated = f"{prior}, starting with an assessment of the current state"
    else:
        updated = "evaluate the current state before deciding what to build"
    _set_candidate_objective(state, updated)
    _conversation_view(state)["needs_analysis"] = True
    state["phase"] = "discovery"
    state["pending_question"] = "objective_confirmation"
    _sync_view_from_state(state)
    return updated


def _conversation_profile() -> Dict[str, Any]:
    return _identity_config().get("conversation_profile", {}) or {}


def _soft_reset_state(state: Dict[str, Any]) -> str:
    previous_intent = _clean_text(state.get("confirmed_objective") or state.get("candidate_objective") or "")
    state["phase"] = "discovery"
    state["candidate_objective"] = ""
    state["confirmed_objective"] = ""
    state["objective_confirmed"] = False
    state["pending_question"] = "objective_discovery"
    state["acceptance_criteria"] = ""
    view = _conversation_view(state)
    view["needs_analysis"] = False
    if previous_intent:
        view["last_stable_intent"] = previous_intent
    _sync_view_from_state(state)
    return previous_intent


def _objective_confirmation_text(objective: str) -> str:
    prefix = str(_conversation_profile().get("objective_confirmation_prefix") or "I think you're trying to").strip()
    return f"{prefix} {objective}. Is that right?"


def _acceptance_question_text() -> str:
    return str(_conversation_profile().get("acceptance_question") or "What should count as done if we turn that into work?").strip()


def _restart_prompt_text(previous_intent: str) -> str:
    template = str(_conversation_profile().get("restart_prompt") or "").strip()
    if previous_intent:
        return f"{template} We were previously on: {previous_intent}."
    return template or "What do you want to work on right now?"


def _analysis_reply(state: Dict[str, Any], text: str) -> str:
    profile = _conversation_profile()
    intent = _clean_text(state.get("confirmed_objective") or state.get("candidate_objective") or text)
    lowered = f"{intent} {text}".lower()
    base = str(profile.get("analysis_without_context") or "").strip()
    if any(token in lowered for token in ("ui", "ux", "design", "screen", "interface")):
        follow_up = str(profile.get("analysis_follow_up_ui") or "Which part should we look at first?").strip()
        return f"{base} {follow_up}".strip()
    return f"{base} What part do you want me to judge first?".strip()


def compose_builder_packet_input(raw_text: str, builder_state: Dict[str, Any], builder_scope: Dict[str, Any] | None) -> str:
    objective = _clean_text(builder_state.get("confirmed_objective") or builder_state.get("candidate_objective") or raw_text)
    acceptance_criteria = _clean_text(builder_state.get("acceptance_criteria") or "")
    parts = [f"Objective: {objective}"]
    if acceptance_criteria:
        parts.append(f"Acceptance criteria: {acceptance_criteria}")
    if isinstance(builder_scope, dict) and builder_scope.get("summary"):
        parts.append(f"Planned scope: {builder_scope['summary']}")
    return "\n".join(parts)


def build_builder_chat_response(
    raw_text: str,
    *,
    requested_meta_state: str = "",
    builder_state: Dict[str, Any] | None = None,
    workspace_context: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    text = _clean_text(raw_text)
    state = _normalized_state(builder_state)
    view = _remember_turn(state, text)
    requested_meta_state = requested_meta_state.strip().lower()
    persisted_meta_state = str(state.get("target_meta_state") or "discuss")
    meta_state = requested_meta_state or persisted_meta_state
    if requested_meta_state == "discuss" and persisted_meta_state == "operate" and state.get("pending_question"):
        meta_state = "operate"
    if meta_state not in {"discuss", "operate"}:
        meta_state = "discuss"
    state["target_meta_state"] = meta_state
    workspace_summary = _workspace_summary(workspace_context)
    profile = _conversation_profile()

    builder_scope = None
    should_create_packet = False

    if state["pending_question"] == "objective_discovery":
        if _is_greeting(text):
            assistant_text = str(profile.get("opening_prompt") or "What do you want to work on or figure out?")
        elif _is_analysis_request(text):
            updated = _analysis_reframe(state, text)
            state["pending_question"] = "analysis_focus"
            assistant_text = f"{_analysis_reply(state, text)} I read this as: {updated}. Is that the direction you want?"
        else:
            state["phase"] = "objective_confirmation"
            state["pending_question"] = "objective_confirmation"
            _set_candidate_objective(state, _strip_leading_affirmation(text) or text)
            assistant_text = _objective_confirmation_text(state["candidate_objective"])
    elif not state["candidate_objective"]:
        if _is_greeting(text):
            state["phase"] = "discovery"
            state["pending_question"] = "objective_discovery"
            assistant_text = str(profile.get("opening_prompt") or "What do you want to work on or figure out?")
        elif _is_analysis_request(text):
            updated = _analysis_reframe(state, text)
            state["pending_question"] = "analysis_focus"
            assistant_text = f"{_analysis_reply(state, text)} I read this as: {updated}. Is that the direction you want?"
        else:
            state["phase"] = "objective_confirmation"
            state["pending_question"] = "objective_confirmation"
            _set_candidate_objective(state, text)
            assistant_text = _objective_confirmation_text(state["candidate_objective"])
    elif state["pending_question"] == "objective_confirmation":
        refinement = _strip_leading_affirmation(text)
        if _is_negative(text):
            state["phase"] = "objective_confirmation"
            state["pending_question"] = "objective_confirmation"
            _set_candidate_objective(state, text)
            assistant_text = f"Then let me restate it: {state['candidate_objective']}. Is that right?"
        elif _is_affirmative(text):
            state["phase"] = "clarification"
            state["confirmed_objective"] = state["candidate_objective"]
            state["objective_confirmed"] = True
            if view.get("needs_analysis"):
                state["pending_question"] = "analysis_first"
                assistant_text = str(
                    profile.get("analysis_transition")
                    or "I can think through the current state with you first, then turn that into scoped work once the goal is clearer."
                )
            else:
                state["pending_question"] = "acceptance_criteria"
                assistant_text = (f"{workspace_summary} " if workspace_summary else "") + _acceptance_question_text()
            _sync_view_from_state(state)
        elif refinement != text and refinement:
            _set_candidate_objective(state, refinement)
            assistant_text = _objective_confirmation_text(state["candidate_objective"])
        elif _is_analysis_request(text):
            updated = _analysis_reframe(state, text)
            state["pending_question"] = "analysis_focus"
            assistant_text = f"{_analysis_reply(state, text)} I read this as: {updated}. Is that the direction you want?"
        else:
            _set_candidate_objective(state, text)
            assistant_text = f"I'll treat that as the revised direction: {state['candidate_objective']}. Is that right?"
    elif state["pending_question"] == "analysis_focus":
        if _is_affirmative(text):
            state["pending_question"] = "objective_confirmation"
            assistant_text = _objective_confirmation_text(state["candidate_objective"])
        elif _is_negative(text):
            state["phase"] = "discovery"
            state["pending_question"] = "objective_discovery"
            state["candidate_objective"] = ""
            state["confirmed_objective"] = ""
            state["objective_confirmed"] = False
            _conversation_view(state)["needs_analysis"] = False
            _sync_view_from_state(state)
            assistant_text = str(profile.get("opening_prompt") or "What do you want to work on or figure out?")
        else:
            assistant_text = _analysis_reply(state, text)
    elif state["pending_question"] == "analysis_first":
        if _is_affirmative(text):
            state["phase"] = "discovery"
            state["pending_question"] = "analysis_result_ack"
            assistant_text = (
                "My read is that the current state should be assessed before we commit to implementation details. "
                "Once we agree on the critique, I can turn it into scoped work."
            )
        elif _is_negative(text):
            _conversation_view(state)["needs_analysis"] = False
            state["pending_question"] = "acceptance_criteria"
            state["phase"] = "clarification"
            _sync_view_from_state(state)
            assistant_text = "Then tell me what should count as done when I make that change."
        else:
            updated = _analysis_reframe(state, text)
            state["pending_question"] = "analysis_focus"
            assistant_text = f"{_analysis_reply(state, text)} I read this as: {updated}. Is that the direction you want?"
    elif state["pending_question"] == "acceptance_criteria":
        if _is_analysis_request(text):
            _conversation_view(state)["needs_analysis"] = True
            state["phase"] = "discovery"
            state["pending_question"] = "analysis_focus"
            _sync_view_from_state(state)
            assistant_text = _analysis_reply(state, text)
        else:
            state["acceptance_criteria"] = text
            state["pending_question"] = ""
            state["phase"] = "scoping"
            builder_scope = _scope_for_objective(state["confirmed_objective"], state["acceptance_criteria"])
            builder_scope["claimed_paths"] = _suggest_claim_paths(builder_scope["domain"], workspace_context)
            should_create_packet = meta_state == "operate"
            assistant_text = (
                f"{workspace_summary}\n\n" if workspace_summary else ""
            ) + (
                "Scope:\n"
                f"- Objective: {state['confirmed_objective']}\n"
                f"- Done means: {state['acceptance_criteria']}\n"
                f"- Likely paths: {', '.join(builder_scope['claimed_paths']) or 'none yet'}\n"
                f"- Tests: {', '.join(builder_scope['tests']) or 'none'}\n"
                "I can turn this into governed work and start execution."
            )
            _sync_view_from_state(state)
    else:
        if _is_restart_signal(text):
            previous_intent = _soft_reset_state(state)
            assistant_text = _restart_prompt_text(previous_intent)
        elif _is_analysis_request(text) or _is_opinion_prompt(text):
            if not state.get("candidate_objective") and any(token in text.lower() for token in ("ui", "ux", "design")):
                _set_candidate_objective(
                    state,
                    "evaluate the current UI and discuss improvements before deciding what to change",
                )
            _conversation_view(state)["needs_analysis"] = True
            state["phase"] = "discovery"
            state["pending_question"] = "analysis_focus"
            _sync_view_from_state(state)
            assistant_text = _analysis_reply(state, text)
        else:
            builder_scope = _scope_for_objective(
                state["confirmed_objective"] or state["candidate_objective"] or text,
                state["acceptance_criteria"],
            )
            should_create_packet = meta_state == "operate" and state["objective_confirmed"] and not view.get("needs_analysis")
            assistant_text = str(
                profile.get("fallback_continue")
                or "I can keep talking this through with you. Tell me what feels off, what outcome you want, or what part you want me to judge first."
            )

    _sync_view_from_state(state)
    domain = classify_feedback_domain(state["confirmed_objective"] or state["candidate_objective"] or text)
    interpretation = {
        "surface_mode": "meta",
        "meta_state": meta_state,
        "domain": domain,
        "risk": DOMAIN_RISK.get(domain, "high") if meta_state == "operate" else "none",
        "should_create_packet": should_create_packet,
        "summary": f"Builder phase: {state['phase']}",
        "next_action": state["pending_question"] or ("create_scoped_packet" if should_create_packet else "continue_conversation"),
        "builder_phase": state["phase"],
        "objective_confirmed": bool(state["objective_confirmed"]),
    }
    return {
        "interpretation": interpretation,
        "assistant_text": assistant_text,
        "packet": None,
        "builder_state": state,
        "builder_scope": builder_scope,
    }
