"""Personal Interface surface.

This module remains a concrete surface family in the layered architecture.
Future development-layer workflows may target it when an idea maps to
calibration, communication-profile shaping, learning from rewrite feedback, or
surface-specific adaptation behavior. The development layer should compose or
variant this surface without moving rewrite or calibration behavior into the
kernel.

Personal Interface-specific adaptation therefore stays owned by this surface
boundary and its adapters, while reusable analysis, synthesis, routing, and
governance primitives remain in the kernel and builder-support layers.
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from .analysis import (
    analyze_session,
    materialize_cards,
    materialize_transcript,
    refresh_indexes,
    update_manifest,
)
from .conversation_learning import analyze_conversation_turns, parse_conversation_transcript
from .models import ConversationEvent, SessionManifest
from .storage import (
    append_jsonl,
    ensure_dir,
    make_id,
    read_json,
    read_jsonl,
    session_dir,
    session_events_path,
    utc_now,
    write_json,
)


MODULE_ID = "surface.personal.personal_interface"
CONTRACT_VERSION = "1.0"
_CALIBRATION_AND_PROFILE_API = (
    "CALIBRATION_INTERVIEW",
    "PersonalInterfaceError",
    "ensure_surface_recipe",
    "load_surface_recipe",
    "build_personal_interface_profile",
    "translate_idea_to_technical_framing",
    "start_calibration_interview",
    "answer_calibration_question",
    "get_profile_snapshot",
    "identify_communication_mode",
    "compile_turn_policy",
)
_LEARNING_AND_REWRITE_API = (
    "ingest_learning_conversation",
    "doctor_personal_interface",
    "rewrite_conversation_turn",
    "rewrite_outgoing_message",
    "record_rewrite_feedback",
)
PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    *_CALIBRATION_AND_PROFILE_API,
    *_LEARNING_AND_REWRITE_API,
)
__all__ = list(PUBLIC_API)


FLOW_MODES = [
    "capture_flow",
    "development_flow",
    "exploratory_flow",
    "synthesis_flow",
    "decision_flow",
]

COMMUNICATION_MODE_SPECS = {
    "attuned_reflection": {
        "axes": {
            "primary_function": "reflect",
            "directionality": "following",
            "stance": "warm",
        },
        "flow_modes": {"capture_flow", "development_flow"},
        "goal_signals": {"clarify_thinking"},
        "text_signals": ["track", "stay with", "follow", "reflect", "hear you", "hold the thread"],
        "instructions": [
            "Track the user's line before adding interpretation or redirection.",
            "Reflect the core thread in a way that lowers friction for the next thought.",
        ],
    },
    "scaffolded_guidance": {
        "axes": {
            "primary_function": "guide",
            "directionality": "guiding",
            "stance": "balanced",
        },
        "flow_modes": {"capture_flow", "development_flow"},
        "goal_signals": {"clarify_thinking"},
        "text_signals": ["next step", "keep going", "scaffold", "shape", "clarify", "work this through"],
        "instructions": [
            "Guide with a light scaffold and a visible next step.",
            "Organize only enough to reduce friction; do not over-structure the turn.",
        ],
    },
    "exploratory_probe": {
        "axes": {
            "primary_function": "probe",
            "directionality": "guiding",
            "stance": "open",
        },
        "flow_modes": {"exploratory_flow"},
        "goal_signals": {"generate_options", "clarify_thinking"},
        "text_signals": ["explore", "what if", "possibility", "alternatives", "question", "could"],
        "instructions": [
            "Use one or two sharp questions to open the space without sprawling.",
            "Keep exploration bounded and relevant to the current thread.",
        ],
    },
    "structured_synthesis": {
        "axes": {
            "primary_function": "synthesize",
            "directionality": "guiding",
            "stance": "precise",
        },
        "flow_modes": {"synthesis_flow", "development_flow"},
        "goal_signals": {"clarify_thinking"},
        "text_signals": ["pattern", "connect", "synthesis", "summarize", "what ties", "compress"],
        "instructions": [
            "Compress the pattern and name the structure clearly.",
            "Surface the connective tissue rather than enumerating every detail.",
        ],
    },
    "decisive_direction": {
        "axes": {
            "primary_function": "recommend",
            "directionality": "directing",
            "stance": "assertive",
        },
        "flow_modes": {"decision_flow"},
        "goal_signals": {"choose_best_option"},
        "text_signals": ["recommend", "should", "best option", "choose", "fastest call", "do this"],
        "instructions": [
            "Lead with the answer or recommendation when the turn is ready for it.",
            "Take ownership of a recommendation without becoming coercive.",
        ],
    },
    "analytic_challenge": {
        "axes": {
            "primary_function": "challenge",
            "directionality": "guiding",
            "stance": "precise",
        },
        "flow_modes": {"development_flow", "decision_flow"},
        "goal_signals": {"stress_test", "debug_reasoning", "critique"},
        "text_signals": ["assumption", "risk", "weak point", "counterexample", "doesn't follow", "stress test"],
        "instructions": [
            "Test weak assumptions directly, but keep the critique specific and useful.",
            "Challenge the load-bearing point first instead of attacking every edge at once.",
        ],
    },
    "concept_translation": {
        "axes": {
            "primary_function": "translate",
            "directionality": "guiding",
            "stance": "precise",
        },
        "flow_modes": {"development_flow", "exploratory_flow", "synthesis_flow"},
        "goal_signals": {"translate_concepts_to_technical", "technical_framing", "operationalize_ideas"},
        "text_signals": [
            "product",
            "idea",
            "abstract",
            "concept",
            "pattern",
            "translate",
            "technical",
            "architecture",
            "layer",
            "model",
            "system",
            "overarching",
        ],
        "instructions": [
            "Translate abstract product language into explicit software constructs and engineering terms.",
            "Map concepts to likely artifacts such as modules, interfaces, schemas, policies, workflows, or state transitions.",
            "Separate confirmed intent from inferred implementation mapping whenever the translation is not fully certain.",
        ],
    },
}

COMMUNICATION_MODES = list(COMMUNICATION_MODE_SPECS.keys())

CALIBRATION_INTERVIEW = [
    {
        "question_id": "recent_moment",
        "prompt": "Think about the last time an AI reply either kept your flow or broke it. Which was closer?",
        "selection_mode": "single",
        "allow_free_text": True,
        "why_this_matters": "Concrete recent moments are more reliable than abstract self-description.",
        "required": True,
        "response_options": [
            {
                "id": "kept_momentum",
                "label": "It kept me moving",
                "description": "The reply fit my pace and did not pull me out of the thought.",
            },
            {
                "id": "slowed_me_down",
                "label": "It slowed me down",
                "description": "The reply broke the thread with too much content, structure, or friction.",
            },
            {
                "id": "mixed",
                "label": "It was mixed",
                "description": "Some parts helped and some parts disrupted my flow.",
            },
            {
                "id": "not_sure",
                "label": "Not sure",
                "description": "I cannot easily recall a clear example right now.",
            },
        ],
    },
    {
        "question_id": "reply_shape",
        "prompt": "When you are mid-thought, which reply shape usually helps most?",
        "selection_mode": "single",
        "allow_free_text": False,
        "why_this_matters": "Recognition-based examples surface preferences with less cognitive effort than abstract labels.",
        "required": True,
        "response_options": [
            {
                "id": "push_forward",
                "label": "Short push-forward",
                "description": "Names the core point fast and keeps me moving.",
            },
            {
                "id": "tight_scaffold",
                "label": "Light scaffold",
                "description": "Gives 2–3 clean points without a long detour.",
            },
            {
                "id": "example_first",
                "label": "Example first",
                "description": "Starts with something concrete before abstracting.",
            },
            {
                "id": "principle_first",
                "label": "Principle first",
                "description": "Starts with the underlying pattern or abstraction.",
            },
            {
                "id": "depends",
                "label": "Depends",
                "description": "It varies a lot with context.",
            },
        ],
    },
    {
        "question_id": "interruption_tolerance",
        "prompt": "If the system notices a weak assumption while you are in motion, what should it do?",
        "selection_mode": "single",
        "allow_free_text": False,
        "why_this_matters": "This captures challenge timing without forcing you to invent your own taxonomy.",
        "required": True,
        "response_options": [
            {
                "id": "let_me_finish",
                "label": "Let me finish first",
                "description": "Do not interrupt the flow unless I ask for critique.",
            },
            {
                "id": "flag_gently",
                "label": "Flag it gently",
                "description": "Briefly mark the issue without derailing the current thread.",
            },
            {
                "id": "challenge_if_high_stakes",
                "label": "Challenge only if stakes are high",
                "description": "Interrupt when the cost of being wrong is high enough.",
            },
            {
                "id": "challenge_early",
                "label": "Challenge early",
                "description": "I would rather be stopped than build on a weak premise.",
            },
            {
                "id": "depends",
                "label": "Depends",
                "description": "It changes a lot with context.",
            },
        ],
    },
    {
        "question_id": "annoyances",
        "prompt": "Which reply habits break flow fastest for you? Pick up to 3.",
        "selection_mode": "multi",
        "allow_free_text": False,
        "why_this_matters": "Users often recognize anti-patterns more easily than ideal styles.",
        "required": True,
        "response_options": [
            {"id": "too_long", "label": "Too long", "description": "The reply is larger than the moment can support."},
            {"id": "too_many_options", "label": "Too many options", "description": "It branches before the main line is stable."},
            {"id": "soft_prefacing", "label": "Soft prefacing", "description": "Too much cushioning before the actual point."},
            {"id": "generic_rephrasing", "label": "Generic restating", "description": "It restates instead of moving the thought."},
            {"id": "heavy_formatting", "label": "Heavy formatting", "description": "The structure becomes louder than the content."},
            {"id": "premature_challenge", "label": "Premature challenge", "description": "It pushes back before tracking the thread."},
            {"id": "abstract_without_grounding", "label": "Abstract without grounding", "description": "It floats above the concrete situation too early."},
            {"id": "not_sure", "label": "Not sure", "description": "Nothing obvious comes to mind."},
        ],
    },
    {
        "question_id": "decision_mode",
        "prompt": "When you are deciding rather than exploring, what should the system switch to?",
        "selection_mode": "single",
        "allow_free_text": False,
        "why_this_matters": "Decision mode often needs a different shape than exploration mode.",
        "required": True,
        "response_options": [
            {
                "id": "clear_recommendation",
                "label": "Clear recommendation",
                "description": "Tell me what you think I should do.",
            },
            {
                "id": "compare_tradeoffs",
                "label": "Compare tradeoffs",
                "description": "Lay out the tradeoffs tightly and let me choose.",
            },
            {
                "id": "questions_first",
                "label": "Questions first",
                "description": "Ask for the missing thing before pushing a recommendation.",
            },
            {
                "id": "evidence_first",
                "label": "Evidence first",
                "description": "Ground me in the facts before you recommend.",
            },
            {
                "id": "depends",
                "label": "Depends",
                "description": "It changes a lot with context.",
            },
        ],
    },
    {
        "question_id": "energy",
        "prompt": "When the system gets it right, what tone feels most native?",
        "selection_mode": "single",
        "allow_free_text": False,
        "why_this_matters": "A small tone calibration helps avoid sounding off without needing a long style interview.",
        "required": False,
        "response_options": [
            {"id": "direct_plain", "label": "Direct and plain", "description": "Minimal ceremony, clear point."},
            {"id": "sharp_energetic", "label": "Sharp and energetic", "description": "Tight, lively, and moving."},
            {"id": "calm_reflective", "label": "Calm and reflective", "description": "Measured and spacious without being vague."},
            {"id": "skeptical_precise", "label": "Skeptical and precise", "description": "Careful, exact, and unsentimental."},
            {"id": "not_sure", "label": "Not sure", "description": "Tone matters less than structure and timing."},
        ],
    },
    {
        "question_id": "anchor_example",
        "prompt": "Optional: give one short example of a reply that felt especially right or wrong. A fragment is enough.",
        "selection_mode": "free_text",
        "allow_free_text": True,
        "why_this_matters": "A short concrete fragment can resolve ambiguity without a long interview.",
        "required": False,
        "response_options": [],
    },
]

CALIBRATION_INDEX = {question["question_id"]: question for question in CALIBRATION_INTERVIEW}
CALIBRATION_CORE_SEQUENCE = [
    "recent_moment",
    "reply_shape",
    "interruption_tolerance",
    "annoyances",
    "decision_mode",
]
CALIBRATION_MINIMUM_QUESTIONS = len(CALIBRATION_CORE_SEQUENCE)
CALIBRATION_MAXIMUM_QUESTIONS = len(CALIBRATION_INTERVIEW)

MODE_TACTICS = {
    "capture_flow": ["reduce_branching", "compress_response", "preserve_momentum", "avoid_heavy_structure"],
    "development_flow": ["stay_with_current_thread", "clarify_without_detour", "keep_next_step_local"],
    "exploratory_flow": ["allow_light_branching", "surface_neighbors", "keep_questions_open"],
    "synthesis_flow": ["compress_patterns", "highlight_connections", "reduce_repetition"],
    "decision_flow": ["prioritize_recommendation", "state_tradeoffs", "end_with_next_step"],
}

TACTIC_REACTIONS = {
    "accepted": {},
    "too_long": {"compress_response": 0.08, "avoid_heavy_structure": 0.04},
    "too_interruptive": {"reduce_branching": 0.08, "avoid_heavy_structure": 0.05},
    "too_soft": {"prioritize_recommendation": -0.04},
    "too_abstract": {"compress_patterns": -0.04},
    "preferred_original": {"compress_response": -0.06, "reduce_branching": -0.06},
}

MODE_KEYWORDS = {
    "capture_flow": ["brain dump", "capture", "fast", "quick", "keep going", "momentum"],
    "development_flow": ["shape", "develop", "refine", "clarify", "work this through"],
    "exploratory_flow": ["explore", "possibility", "what if", "branch", "alternatives"],
    "synthesis_flow": ["connect", "pattern", "synthesize", "summarize", "what ties"],
    "decision_flow": ["decide", "choose", "recommend", "next step", "what should"],
}

STRESSED_MARKERS = ["overwhelmed", "stressed", "anxious", "too much", "exhausted", "frazzled"]
FRUSTRATED_MARKERS = ["frustrated", "annoyed", "broken", "messy", "stupid", "wrong"]
EXPLORATORY_MARKERS = ["curious", "explore", "possibility", "possibilities", "what if", "wonder", "pattern"]
DECISIVE_MARKERS = ["decide", "choose", "recommend", "what should", "best option"]


@dataclass
class PersonalInterfaceError(RuntimeError):
    code: str
    message: str
    details: Dict[str, Any] | None = None

    def __str__(self) -> str:
        return self.message

    def to_dict(self) -> Dict[str, Any]:
        payload = {"error": self.code, "message": self.message}
        if self.details:
            payload["details"] = self.details
        return payload


def _product_dir(root: Path) -> Path:
    return root / "product" / "personal_interface_v1"


def _data_dir(root: Path) -> Path:
    return _product_dir(root) / "data"


def _profile_path(root: Path) -> Path:
    return _data_dir(root) / "profile.json"


def _runtime_path(root: Path) -> Path:
    return _data_dir(root) / "runtime.json"


def _surface_recipe_path(root: Path) -> Path:
    return _product_dir(root) / "config" / "surface_recipe.v1.json"


def _rewrite_events_path(root: Path) -> Path:
    return _data_dir(root) / "rewrite_events.jsonl"


def _feedback_events_path(root: Path) -> Path:
    return _data_dir(root) / "feedback_events.jsonl"


def _learning_events_path(root: Path) -> Path:
    return _data_dir(root) / "learning_events.jsonl"


def _policy_snapshot_path(root: Path) -> Path:
    return _data_dir(root) / "policy_snapshot.json"


def _bridge_state_path(root: Path) -> Path:
    return _data_dir(root) / "bridge_state.json"


def _calibration_state_path(root: Path, session_id: str) -> Path:
    return _data_dir(root) / "calibration" / f"{session_id}.json"


def _default_surface_recipe(root: Path) -> Dict[str, Any]:
    return {
        "recipe_id": "recipe.personal_interface.v1",
        "surface_id": "surface.personal_interface",
        "name": "Personal Interface v1 Reference Surface",
        "status": "transitional",
        "version": "0.1.0",
        "target_layer": "surface",
        "purpose": (
            "Adapt outgoing assistant replies through a calibrated local-first "
            "personalization surface over the conversation substrate."
        ),
        "module_refs": [
            {
                "module_id": "kernel.foundation.storage",
                "version_range": ">=0.1.0",
                "required": True,
                "notes": "Persists profile, calibration, and rewrite artifacts.",
            },
            {
                "module_id": "kernel.foundation.models",
                "version_range": ">=0.1.0",
                "required": True,
                "notes": "Provides shared conversation record shapes.",
            },
            {
                "module_id": "kernel.analysis.conversation_learning",
                "version_range": ">=0.1.0",
                "required": False,
                "notes": "Learns user explanation and follow-up preferences from conversation input.",
            },
        ],
        "adapter_refs": [
            {
                "adapter_id": "surface.personal.runtime_payloads",
                "repo_paths": ["src/conversation_os/personal_interface.py"],
                "purpose": (
                    "Drive calibration, profile compilation, learning ingestion, "
                    "and rewrite behavior for outgoing messages."
                ),
                "depends_on": [
                    "kernel.foundation.storage",
                    "kernel.foundation.models",
                    "kernel.analysis.conversation_learning",
                ],
            },
            {
                "adapter_id": "surface.personal.mcp_surface",
                "repo_paths": [
                    "src/conversation_os/personal_interface_mcp.py",
                    "tools/run_personal_interface_mcp.py",
                ],
                "purpose": "Expose Personal Interface rewrite operations to host chat systems.",
                "depends_on": ["surface.personal.runtime_payloads"],
            },
        ],
        "policy_defaults": {
            "rewrite_mode": "governed",
            "feedback_learning": "explicit_only",
        },
        "runtime_dependencies": [
            "product/personal_interface_v1/data/runtime.json",
        ],
        "state_dependencies": [
            "memory/events",
            "memory/sessions",
            "product/personal_interface_v1/data",
        ],
        "entrypoints": [
            "python3 tools/conversation_os.py personal-interface calibrate-start",
            "python3 tools/conversation_os.py personal-interface rewrite-turn --draft-text \"...\" --conversation-json \"[...]\"",
            "python3 tools/run_personal_interface_mcp.py",
        ],
        "config_path": str(_surface_recipe_path(root)),
    }


def ensure_surface_recipe(root: Path) -> Path:
    path = _surface_recipe_path(root)
    ensure_dir(path.parent)
    if not path.exists():
        write_json(path, _default_surface_recipe(root))
    return path


def load_surface_recipe(root: Path) -> Dict[str, Any]:
    path = ensure_surface_recipe(root)
    payload = read_json(path, default={}) or {}
    default_payload = _default_surface_recipe(root)
    recipe = dict(default_payload)
    recipe.update(payload)
    recipe["config_path"] = str(path)
    return recipe


def ensure_personal_interface_runtime(root: Path) -> None:
    ensure_dir(_data_dir(root))
    ensure_dir(_data_dir(root) / "calibration")
    bridge_state_path = _bridge_state_path(root)
    if not bridge_state_path.exists():
        write_json(bridge_state_path, _default_bridge_state())


def _default_bridge_state() -> Dict[str, Any]:
    return {
        "bridge_state_version": 1,
        "updated_at": "",
        "latest_rewrite_event_id": "",
        "current_mood": {
            "label": "neutral",
            "valence": "neutral",
            "energy": "steady",
            "confidence": 0.0,
            "evidence": [],
            "captured_at": "",
        },
        "mood_history": [],
        "context": {
            "user_message": "",
            "conversation_window_size": 0,
            "conversation_turn_count": 0,
            "active_terms": [],
            "caller_hints": {},
            "client_context": {},
        },
        "personalization": {
            "verbosity": "",
            "directness": "",
            "structure_density": "",
            "challenge_tolerance": "",
            "preferred_cadence": "",
        },
        "presentation": {
            "current_mode": "",
            "mode_confidence": 0.0,
            "communication_mode": "",
            "communication_confidence": 0.0,
            "applied_tactics": [],
            "rewrite_backend": "",
        },
        "behavior_patterns": [],
        "telemetry": {
            "rewrite_count": 0,
            "last_backend": "",
            "last_diff_summary": {},
        },
    }


def load_bridge_state(root: Path) -> Dict[str, Any]:
    ensure_personal_interface_runtime(root)
    state = read_json(_bridge_state_path(root), default={}) or {}
    default = _default_bridge_state()
    merged = dict(default)
    merged.update({key: value for key, value in state.items() if key not in {"current_mood", "context", "personalization", "presentation", "telemetry"}})
    for key in ["current_mood", "context", "personalization", "presentation", "telemetry"]:
        payload = state.get(key, {})
        merged[key] = {**default[key], **payload} if isinstance(payload, dict) else dict(default[key])
    merged["mood_history"] = state.get("mood_history", []) if isinstance(state.get("mood_history", []), list) else []
    merged["behavior_patterns"] = state.get("behavior_patterns", []) if isinstance(state.get("behavior_patterns", []), list) else []
    return merged


def _write_session_manifest(root: Path, manifest: SessionManifest) -> None:
    ensure_dir(session_dir(root, manifest.session_id))
    ensure_dir(session_events_path(root, manifest.session_id).parent)
    session_events_path(root, manifest.session_id).touch(exist_ok=True)
    update_manifest(root, manifest)


def _append_session_event(
    root: Path,
    session_id: str,
    actor: str,
    kind: str,
    content: str,
    tags: List[str] | None = None,
) -> Dict[str, Any]:
    event = ConversationEvent(
        event_id=make_id("event"),
        session_id=session_id,
        timestamp=utc_now(),
        actor=actor,
        kind=kind,
        content=content,
        attachments=[],
        tags=tags or [],
        source_ref=None,
    )
    append_jsonl(session_events_path(root, session_id), event.to_dict())
    return event.to_dict()


def _close_calibration_session(root: Path, session_id: str) -> None:
    checkpoint = materialize_transcript(root, session_id)
    analysis_refs = analyze_session(root, session_id)
    materialize_cards(root, session_id)
    refresh_indexes(root)
    manifest_payload = read_json(session_dir(root, session_id) / "manifest.json", default={})
    manifest = SessionManifest(**manifest_payload)
    manifest.ended_at = utc_now()
    manifest.status = "closed"
    manifest.artifact_refs.update(checkpoint)
    manifest.artifact_refs.update(analysis_refs)
    update_manifest(root, manifest)


def _coerce_answer_entry(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        choice = value.get("choice")
        note = value.get("note", "")
        raw = value.get("raw", "")
        return {"choice": choice, "note": note, "raw": raw}
    if isinstance(value, list):
        return {"choice": value, "note": "", "raw": ",".join(str(item) for item in value)}
    if isinstance(value, str):
        return {"choice": value, "note": "", "raw": value}
    return {"choice": value, "note": "", "raw": str(value)}


def _normalize_answer_map(answer_map: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {key: _coerce_answer_entry(value) for key, value in answer_map.items()}


def _choice(answer_map: Dict[str, Dict[str, Any]], key: str, default: Any = "") -> Any:
    return answer_map.get(key, {}).get("choice", default)


def _note(answer_map: Dict[str, Dict[str, Any]], key: str, default: str = "") -> str:
    return str(answer_map.get(key, {}).get("note", default) or default)


def _derive_profile_communication_preferences(normalized: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    reply_shape = _choice(normalized, "reply_shape", "tight_scaffold")
    interruption = _choice(normalized, "interruption_tolerance", "flag_gently")
    decision_mode = _choice(normalized, "decision_mode", "compare_tradeoffs")
    energy = _choice(normalized, "energy", "")

    default_mode = "scaffolded_guidance"
    if reply_shape == "principle_first":
        default_mode = "structured_synthesis"
    elif reply_shape == "example_first":
        default_mode = "attuned_reflection"
    elif interruption == "challenge_early":
        default_mode = "analytic_challenge"

    directionality_preference = "guiding"
    if interruption == "let_me_finish":
        directionality_preference = "following"
    elif interruption == "challenge_early":
        directionality_preference = "directing"

    stance_preference = "balanced"
    if energy == "calm_reflective":
        stance_preference = "warm"
    elif energy == "skeptical_precise":
        stance_preference = "precise"
    elif energy == "sharp_energetic":
        stance_preference = "assertive"

    decision_mode_map = {
        "clear_recommendation": "decisive_direction",
        "compare_tradeoffs": "structured_synthesis",
        "questions_first": "exploratory_probe",
        "evidence_first": "structured_synthesis",
        "depends": default_mode,
    }

    return {
        "default_mode": default_mode,
        "decision_communication_mode": decision_mode_map.get(decision_mode, default_mode),
        "challenge_communication_mode": "analytic_challenge" if interruption in {"challenge_if_high_stakes", "challenge_early"} else "scaffolded_guidance",
        "directionality_preference": directionality_preference,
        "stance_preference": stance_preference,
        "preferred_functions": [
            COMMUNICATION_MODE_SPECS[default_mode]["axes"]["primary_function"],
            COMMUNICATION_MODE_SPECS[decision_mode_map.get(decision_mode, default_mode)]["axes"]["primary_function"],
        ],
    }


def _derive_profile_translation_preferences(normalized: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    reply_shape = _choice(normalized, "reply_shape", "tight_scaffold")
    annoyances = _choice(normalized, "annoyances", [])
    annoyances = annoyances if isinstance(annoyances, list) else [annoyances]
    energy = _choice(normalized, "energy", "")
    recent_note = _note(normalized, "recent_moment")
    anchor_note = _note(normalized, "anchor_example")

    translation_bias = "medium"
    if reply_shape == "principle_first":
        translation_bias = "high"
    elif reply_shape == "example_first":
        translation_bias = "low"
    if "abstract_without_grounding" in annoyances:
        translation_bias = "high"

    target_artifacts = [
        "domain_terms",
        "components",
        "interfaces",
        "data_models",
        "policies",
        "workflows",
        "state_transitions",
    ]
    if energy == "skeptical_precise":
        target_artifacts.append("invariants")

    return {
        "enabled": True,
        "preferred_mode": "concept_translation",
        "translation_bias": translation_bias,
        "target_artifacts": target_artifacts,
        "output_contract": ["confirmed_intent", "inferred_mapping", "open_questions"],
        "preserve_uncertainty": True,
        "domain_anchor": recent_note or anchor_note or "",
    }


def _default_learned_conversation_preferences() -> Dict[str, Any]:
    return {
        "enabled": False,
        "source_count": 0,
        "question_path_types": [],
        "example_preferences": [],
        "followup_preferences": [],
        "guiding_path": "pattern_to_example_to_implementation",
        "followup_dynamics": {
            "answer_reference_count": 0,
            "self_reference_count": 0,
            "intent_types": [],
            "answer_relevance_signal": "medium",
        },
        "last_source_label": "",
    }


def build_personal_interface_profile(answer_map: Dict[str, Any], interview_metadata: Dict[str, Any] | None = None) -> Dict[str, Any]:
    normalized = _normalize_answer_map(answer_map)
    profile = {
        "profile_version": 1,
        "user_id": "default",
        "created_at": utc_now(),
        "baseline_preferences": {
            "verbosity": "concise",
            "branching_tolerance": "low",
            "structure_density": "light",
            "abstraction_preference": "mixed",
            "challenge_tolerance": "medium",
            "example_preference": "situational",
        },
        "rhetorical_preferences": {
            "directness": "high",
            "mirrored_lexicon_strength": "medium",
            "preferred_cadence": "tight",
            "disliked_patterns": [
                "generic reassurance",
                "premature expansion",
                "multiple nested options",
            ],
        },
        "mode_preferences": {
            "default_mode": "development_flow",
            "mode_signals": {
                "capture_flow": _note(normalized, "recent_moment"),
                "decision_flow": _choice(normalized, "decision_mode", ""),
            },
            "mode_overrides": {},
            "decision_style": _choice(normalized, "decision_mode", "compare_tradeoffs"),
        },
        "guardrails": {
            "protect_factual_fidelity": True,
            "avoid_unnecessary_branching": True,
            "avoid_performative_empathy": True,
        },
        "learning_preferences": {
            "teaching_priority": "secondary_to_flow",
            "starting_point": "mixed",
            "learned_from_conversations": _default_learned_conversation_preferences(),
        },
        "communication_preferences": _derive_profile_communication_preferences(normalized),
        "translation_preferences": _derive_profile_translation_preferences(normalized),
        "calibration_answers": normalized,
        "interview_metadata": interview_metadata or {},
        "interaction_preferences": {
            "interruption_style": _choice(normalized, "interruption_tolerance", "flag_gently"),
        },
    }

    reply_shape = _choice(normalized, "reply_shape", "tight_scaffold")
    if reply_shape == "push_forward":
        profile["baseline_preferences"]["verbosity"] = "concise"
        profile["baseline_preferences"]["structure_density"] = "light"
        profile["baseline_preferences"]["branching_tolerance"] = "low"
        profile["rhetorical_preferences"]["directness"] = "high"
        profile["rhetorical_preferences"]["preferred_cadence"] = "tight"
    elif reply_shape == "tight_scaffold":
        profile["baseline_preferences"]["verbosity"] = "concise"
        profile["baseline_preferences"]["structure_density"] = "medium"
        profile["baseline_preferences"]["branching_tolerance"] = "low"
    elif reply_shape == "example_first":
        profile["baseline_preferences"]["abstraction_preference"] = "concrete_first"
        profile["baseline_preferences"]["example_preference"] = "high"
        profile["learning_preferences"]["starting_point"] = "concrete_first"
    elif reply_shape == "principle_first":
        profile["baseline_preferences"]["abstraction_preference"] = "abstract_first"
        profile["baseline_preferences"]["example_preference"] = "low"
        profile["learning_preferences"]["starting_point"] = "abstract_first"

    interruption = _choice(normalized, "interruption_tolerance", "flag_gently")
    if interruption == "let_me_finish":
        profile["baseline_preferences"]["challenge_tolerance"] = "low"
    elif interruption == "flag_gently":
        profile["baseline_preferences"]["challenge_tolerance"] = "medium"
    elif interruption == "challenge_if_high_stakes":
        profile["baseline_preferences"]["challenge_tolerance"] = "medium"
        profile["guardrails"]["allow_stakes_based_interruptions"] = True
    elif interruption == "challenge_early":
        profile["baseline_preferences"]["challenge_tolerance"] = "high"

    annoyances = _choice(normalized, "annoyances", [])
    annoyances = annoyances if isinstance(annoyances, list) else [annoyances]
    disliked_patterns: List[str] = []
    for annoyance in annoyances:
        if annoyance == "too_long":
            profile["baseline_preferences"]["verbosity"] = "concise"
            disliked_patterns.append("too much length")
        elif annoyance == "too_many_options":
            profile["baseline_preferences"]["branching_tolerance"] = "low"
            disliked_patterns.append("too many options")
        elif annoyance == "soft_prefacing":
            profile["rhetorical_preferences"]["directness"] = "high"
            disliked_patterns.append("soft prefacing")
        elif annoyance == "generic_rephrasing":
            disliked_patterns.append("generic rephrasing")
        elif annoyance == "heavy_formatting":
            profile["baseline_preferences"]["structure_density"] = "light"
            disliked_patterns.append("heavy formatting")
        elif annoyance == "premature_challenge":
            profile["baseline_preferences"]["challenge_tolerance"] = "low"
            disliked_patterns.append("premature challenge")
        elif annoyance == "abstract_without_grounding":
            profile["baseline_preferences"]["abstraction_preference"] = "concrete_first"
            disliked_patterns.append("abstract without grounding")
    profile["rhetorical_preferences"]["disliked_patterns"] = disliked_patterns or profile["rhetorical_preferences"]["disliked_patterns"]

    energy = _choice(normalized, "energy", "")
    if energy == "direct_plain":
        profile["rhetorical_preferences"]["directness"] = "high"
        profile["rhetorical_preferences"]["preferred_cadence"] = "tight"
    elif energy == "sharp_energetic":
        profile["rhetorical_preferences"]["directness"] = "high"
        profile["rhetorical_preferences"]["preferred_cadence"] = "energetic"
    elif energy == "calm_reflective":
        profile["rhetorical_preferences"]["directness"] = "medium"
        profile["rhetorical_preferences"]["preferred_cadence"] = "calm"
    elif energy == "skeptical_precise":
        profile["rhetorical_preferences"]["directness"] = "high"
        profile["rhetorical_preferences"]["preferred_cadence"] = "precise"

    recent_note = _note(normalized, "recent_moment")
    anchor_note = _note(normalized, "anchor_example")
    recent_choice = _choice(normalized, "recent_moment", "")
    if recent_choice == "slowed_me_down":
        profile["mode_preferences"]["mode_signals"]["capture_flow"] = recent_note or "Flow breaks when the reply becomes too large or interruptive."
    elif recent_choice == "kept_momentum":
        profile["mode_preferences"]["mode_signals"]["capture_flow"] = recent_note or "Capture flow prefers responses that keep momentum."
    elif recent_choice == "mixed":
        profile["mode_preferences"]["mode_signals"]["capture_flow"] = recent_note or anchor_note or "Capture flow is context-dependent and benefits from low-friction replies."

    if anchor_note:
        profile["mode_preferences"]["example_anchor"] = anchor_note

    return profile


def load_personal_interface_profile(root: Path) -> Dict[str, Any]:
    profile = read_json(_profile_path(root), default=None)
    if profile is None:
        raise PersonalInterfaceError(
            "profile_missing",
            "Calibration profile missing. Start the guided calibration interview first.",
            {"next_action": "start_calibration_interview"},
        )
    return profile


def load_personal_interface_policy_snapshot(root: Path) -> Dict[str, Any]:
    return read_json(_policy_snapshot_path(root), default={"feedback_count": 0, "tactic_penalties": {}})


def _default_personal_interface_profile() -> Dict[str, Any]:
    return build_personal_interface_profile({})


def translate_idea_to_technical_framing(
    root: Path,
    idea_text: str,
    desired_effect: str = "",
    caller_hints: Dict[str, Any] | None = None,
    context_notes: List[str] | None = None,
) -> Dict[str, Any]:
    normalized_idea = str(idea_text or "").strip()
    if not normalized_idea:
        raise PersonalInterfaceError("idea_missing", "Idea text is required for technical framing.")

    try:
        profile = load_personal_interface_profile(root)
        profile_source = "saved_profile"
    except PersonalInterfaceError as exc:
        if exc.code != "profile_missing":
            raise
        profile = _default_personal_interface_profile()
        profile_source = "default_profile"

    merged_hints = dict(caller_hints or {})
    merged_hints.setdefault("goal", "translate_concepts_to_technical")
    merged_hints.setdefault("allow_branching", False)
    merged_hints.setdefault("desired_depth", "short")

    draft_text = str(desired_effect or normalized_idea)
    mode, confidence, inference_source = _infer_mode(normalized_idea, draft_text, merged_hints, profile)
    communication = identify_communication_mode(
        user_message=normalized_idea,
        draft_text=draft_text,
        flow_mode=mode,
        caller_hints=merged_hints,
        profile=profile,
    )
    compiled_turn_policy = compile_turn_policy(
        profile=profile,
        mode=mode,
        confidence=confidence,
        communication_mode=communication["mode"],
        communication_axes=communication["axes"],
        caller_hints=merged_hints,
        policy_snapshot=load_personal_interface_policy_snapshot(root),
    )

    translation_preferences = profile.get("translation_preferences", {})
    confirmed_intent = [normalized_idea]
    if desired_effect.strip():
        confirmed_intent.append(f"Desired effect: {desired_effect.strip()}")

    open_questions: List[str] = []
    if not desired_effect.strip():
        open_questions.append("What concrete user or system effect should this idea produce?")
    if not context_notes:
        open_questions.append("What existing surface, workflow, or module family does this idea seem closest to?")

    inferred_mapping_guidance = [
        {
            "artifact_type": artifact_type,
            "reason": "Preferred by the Personal Interface concept-translation profile for technical framing.",
        }
        for artifact_type in translation_preferences.get("target_artifacts", [])
    ]

    return {
        "idea_text": normalized_idea,
        "desired_effect": desired_effect.strip(),
        "profile_source": profile_source,
        "mode": mode,
        "mode_confidence": round(confidence, 2),
        "mode_inference_source": inference_source,
        "communication_mode": communication["mode"],
        "communication_axes": communication["axes"],
        "compiled_turn_policy": compiled_turn_policy,
        "confirmed_intent": confirmed_intent,
        "inferred_mapping_guidance": inferred_mapping_guidance,
        "target_artifacts": list(translation_preferences.get("target_artifacts", [])),
        "output_contract": list(translation_preferences.get("output_contract", [])),
        "preserve_uncertainty": bool(translation_preferences.get("preserve_uncertainty")),
        "domain_anchor": str(translation_preferences.get("domain_anchor", "") or ""),
        "context_notes": list(context_notes or []),
        "open_questions": open_questions,
    }


def _extract_text_from_html(text: str) -> str:
    without_scripts = re.sub(r"<script.*?>.*?</script>", " ", text, flags=re.DOTALL | re.IGNORECASE)
    without_styles = re.sub(r"<style.*?>.*?</style>", " ", without_scripts, flags=re.DOTALL | re.IGNORECASE)
    no_tags = re.sub(r"<[^>]+>", " ", without_styles)
    return re.sub(r"\s+", " ", no_tags).strip()


def _load_learning_source_text(source_text: str | None, source_path: str | None, source_url: str | None) -> tuple[str, Dict[str, Any]]:
    provided = [value for value in [source_text, source_path, source_url] if value]
    if len(provided) != 1:
        raise PersonalInterfaceError(
            "learning_source_invalid",
            "Provide exactly one of source_text, source_path, or source_url.",
        )
    if source_text:
        return source_text, {"kind": "text", "ref": "inline"}
    if source_path:
        path = Path(source_path).expanduser().resolve()
        if not path.exists():
            raise PersonalInterfaceError("learning_source_missing", "Learning source path does not exist.", {"source_path": str(path)})
        return path.read_text(encoding="utf-8"), {"kind": "path", "ref": str(path)}

    assert source_url is not None
    request = Request(source_url, headers={"User-Agent": "InnerSpacePersonalInterface/1.0"})
    with urlopen(request, timeout=20) as response:
        raw = response.read().decode("utf-8", errors="ignore")
        content_type = response.headers.get("Content-Type", "")
    text = _extract_text_from_html(raw) if "html" in content_type.lower() else raw
    return text, {"kind": "url", "ref": source_url}


def _parse_learning_transcript(text: str) -> List[Dict[str, str]]:
    return parse_conversation_transcript(text)


def _analyze_learning_turns(turns: List[Dict[str, str]]) -> Dict[str, Any]:
    return analyze_conversation_turns(turns)


def ingest_learning_conversation(
    root: Path,
    source_text: str | None = None,
    source_path: str | None = None,
    source_url: str | None = None,
    source_label: str | None = None,
) -> Dict[str, Any]:
    ensure_personal_interface_runtime(root)
    profile = load_personal_interface_profile(root)
    text, source = _load_learning_source_text(source_text, source_path, source_url)
    turns = _parse_learning_transcript(text)
    if not turns:
        raise PersonalInterfaceError("learning_source_unparseable", "Could not parse any conversation turns from the supplied learning source.")
    analysis = _analyze_learning_turns(turns)

    learned = profile.setdefault("learning_preferences", {}).setdefault("learned_from_conversations", _default_learned_conversation_preferences())
    learned["enabled"] = True
    learned["source_count"] = int(learned.get("source_count", 0)) + 1
    learned["question_path_types"] = sorted(set(learned.get("question_path_types", []) + analysis["question_path_types"]))
    learned["example_preferences"] = sorted(set(learned.get("example_preferences", []) + analysis["example_preferences"]))
    learned["followup_preferences"] = sorted(set(learned.get("followup_preferences", []) + analysis["followup_preferences"]))
    learned["guiding_path"] = analysis["guiding_path"]
    existing_dynamics = learned.get("followup_dynamics", _default_learned_conversation_preferences()["followup_dynamics"])
    analysis_dynamics = analysis["followup_dynamics"]
    learned["followup_dynamics"] = {
        "answer_reference_count": int(existing_dynamics.get("answer_reference_count", 0)) + int(analysis_dynamics.get("answer_reference_count", 0)),
        "self_reference_count": int(existing_dynamics.get("self_reference_count", 0)) + int(analysis_dynamics.get("self_reference_count", 0)),
        "intent_types": sorted(set(existing_dynamics.get("intent_types", []) + analysis_dynamics.get("intent_types", []))),
        "answer_relevance_signal": analysis_dynamics.get("answer_relevance_signal", existing_dynamics.get("answer_relevance_signal", "medium")),
    }
    learned["last_source_label"] = source_label or source["ref"]
    write_json(_profile_path(root), profile)

    event = {
        "learning_event_id": make_id("learning"),
        "created_at": utc_now(),
        "source": source,
        "source_label": source_label or source["ref"],
        "analysis": analysis,
    }
    append_jsonl(_learning_events_path(root), event)
    return {
        "learning_event_id": event["learning_event_id"],
        "source": source,
        "analysis": analysis,
        "profile_learning_preferences": learned,
    }


def doctor_personal_interface(root: Path) -> Dict[str, Any]:
    ensure_personal_interface_runtime(root)
    checks: Dict[str, Any] = {}

    profile = read_json(_profile_path(root), default=None)
    checks["profile"] = {
        "status": "ok" if profile else "missing",
        "path": str(_profile_path(root)),
    }

    runtime = _load_runtime(root)
    runtime_ok = bool(runtime and runtime.get("id"))
    checks["runtime"] = {
        "status": "ok" if runtime_ok else "missing",
        "path": str(_runtime_path(root)),
        "backend_id": runtime.get("id") if runtime else None,
    }

    backend_status = "missing"
    backend_detail = None
    if runtime_ok:
        if runtime["id"] == "command_json":
            command = runtime.get("command") or []
            backend_status = "ok" if command else "invalid"
            backend_detail = command
        elif runtime["id"] == "openclaw_local":
            backend_status = "ok"
            backend_detail = runtime.get("agent", "main")
        else:
            backend_status = "unsupported"
            backend_detail = runtime["id"]
    checks["rewrite_backend"] = {"status": backend_status, "detail": backend_detail}

    try:
        import importlib.util

        mcp_present = bool(importlib.util.find_spec("mcp"))
    except Exception:
        mcp_present = False
    if not mcp_present and (root / ".vendor" / "mcp_py").exists():
        mcp_present = True
    checks["mcp_sdk"] = {
        "status": "ok" if mcp_present else "missing",
        "required_for_stdio_server": True,
    }

    ready = all(checks[key]["status"] == "ok" for key in ["profile", "runtime", "rewrite_backend"])
    return {
        "ready": ready,
        "checks": checks,
    }


def _update_personal_interface_policy_snapshot(root: Path) -> Dict[str, Any]:
    events = read_jsonl(_feedback_events_path(root))
    snapshot = {
        "feedback_count": len(events),
        "accepted_count": sum(1 for row in events if row.get("feedback_state") == "accepted"),
        "too_long_count": sum(1 for row in events if row.get("feedback_state") == "too_long"),
        "too_interruptive_count": sum(1 for row in events if row.get("feedback_state") == "too_interruptive"),
        "too_soft_count": sum(1 for row in events if row.get("feedback_state") == "too_soft"),
        "too_abstract_count": sum(1 for row in events if row.get("feedback_state") == "too_abstract"),
        "preferred_original_count": sum(1 for row in events if row.get("feedback_state") == "preferred_original"),
        "tactic_penalties": {},
    }
    penalties: Dict[str, float] = {}
    for event in events:
        for tactic, delta in TACTIC_REACTIONS.get(event.get("feedback_state", ""), {}).items():
            penalties[tactic] = round(penalties.get(tactic, 0.0) + max(delta, 0.0), 3)
    snapshot["tactic_penalties"] = penalties
    write_json(_policy_snapshot_path(root), snapshot)
    return snapshot


def _question_payload(question_id: str, state: Dict[str, Any]) -> Dict[str, Any]:
    question = CALIBRATION_INDEX[question_id]
    return {
        "session_id": state["session_id"],
        "question_index": len(state.get("asked_question_ids", [])),
        "question_id": question_id,
        "question": question["prompt"],
        "selection_mode": question["selection_mode"],
        "allow_free_text": question["allow_free_text"],
        "response_options": question["response_options"],
        "why_this_matters": question["why_this_matters"],
        "progress": {
            "questions_asked": len(state.get("asked_question_ids", [])),
            "minimum_questions": CALIBRATION_MINIMUM_QUESTIONS,
            "maximum_questions": CALIBRATION_MAXIMUM_QUESTIONS,
        },
        "completed": False,
    }


def _parse_answer(question_id: str, answer: str) -> Dict[str, Any]:
    question = CALIBRATION_INDEX[question_id]
    response_options = {option["id"] for option in question["response_options"]}
    raw = answer.strip()
    if question["selection_mode"] == "multi":
        parts = [item.strip() for item in raw.split(",") if item.strip()]
        selected = [item for item in parts if item in response_options]
        note_parts = [item for item in parts if item not in response_options]
        if not selected and raw in response_options:
            selected = [raw]
        return {"choice": selected, "note": ", ".join(note_parts), "raw": raw}
    if question["selection_mode"] == "free_text":
        return {"choice": "", "note": raw, "raw": raw}
    if raw in response_options:
        return {"choice": raw, "note": "", "raw": raw}
    if "|" in raw:
        left, right = [part.strip() for part in raw.split("|", 1)]
        if left in response_options:
            return {"choice": left, "note": right, "raw": raw}
    return {"choice": raw if raw in response_options else "not_sure", "note": raw if raw not in response_options else "", "raw": raw}


def _needs_optional_question(state: Dict[str, Any], question_id: str) -> bool:
    answers = state["answers"]
    if question_id == "energy":
        return _choice(answers, "reply_shape", "") == "depends" or _choice(answers, "interruption_tolerance", "") == "depends"
    if question_id == "anchor_example":
        return (
            _choice(answers, "recent_moment", "") in {"mixed", "not_sure"}
            or _choice(answers, "reply_shape", "") == "depends"
            or _choice(answers, "interruption_tolerance", "") == "depends"
        )
    return False


def _next_question_id(state: Dict[str, Any]) -> str | None:
    for question_id in CALIBRATION_CORE_SEQUENCE:
        if question_id not in state["answers"]:
            return question_id
    for question_id in ["energy", "anchor_example"]:
        if question_id not in state["answers"] and _needs_optional_question(state, question_id):
            return question_id
    return None


def start_calibration_interview(root: Path) -> Dict[str, Any]:
    ensure_personal_interface_runtime(root)
    session_id = make_id("personal-calibration")
    manifest = SessionManifest(
        session_id=session_id,
        title="Personal Interface Calibration",
        started_at=utc_now(),
        ended_at=None,
        participants=["user", "agent"],
        source_type="personal_interface_calibration",
        status="active",
        artifact_refs={},
        domains=["personal_interface"],
    )
    _write_session_manifest(root, manifest)
    state = {
        "session_id": session_id,
        "answers": {},
        "asked_question_ids": [],
        "completed": False,
        "current_question_id": CALIBRATION_CORE_SEQUENCE[0],
    }
    write_json(_calibration_state_path(root, session_id), state)
    first = CALIBRATION_CORE_SEQUENCE[0]
    _append_session_event(root, session_id, "agent", "calibration_question", CALIBRATION_INDEX[first]["prompt"], ["personal_interface", "calibration", first])
    return _question_payload(first, state)


def answer_calibration_question(root: Path, session_id: str, answer: str) -> Dict[str, Any]:
    ensure_personal_interface_runtime(root)
    state = read_json(_calibration_state_path(root, session_id), default=None)
    if state is None:
        raise PersonalInterfaceError("calibration_session_missing", "Unknown calibration session.", {"session_id": session_id})
    if state.get("completed"):
        raise PersonalInterfaceError("calibration_already_complete", "Calibration session already completed.", {"session_id": session_id})

    question_id = state.get("current_question_id") or _next_question_id(state)
    if question_id is None:
        raise PersonalInterfaceError("calibration_state_invalid", "Calibration state has no pending question.", {"session_id": session_id})
    parsed_answer = _parse_answer(question_id, answer)
    state["answers"][question_id] = parsed_answer
    state["asked_question_ids"].append(question_id)
    _append_session_event(root, session_id, "user", "calibration_answer", answer, ["personal_interface", question_id])

    next_question_id = _next_question_id(state)

    if next_question_id is None:
        profile = build_personal_interface_profile(
            state["answers"],
            interview_metadata={
                "asked_question_ids": state["asked_question_ids"],
                "question_count": len(state["asked_question_ids"]),
                "adaptive": True,
                "minimum_questions": CALIBRATION_MINIMUM_QUESTIONS,
                "maximum_questions": CALIBRATION_MAXIMUM_QUESTIONS,
            },
        )
        write_json(_profile_path(root), profile)
        write_json(
            _policy_snapshot_path(root),
            {"feedback_count": 0, "tactic_penalties": {}, "accepted_count": 0, "too_interruptive_count": 0},
        )
        state["completed"] = True
        state["current_question_id"] = None
        write_json(_calibration_state_path(root, session_id), state)
        _append_session_event(
            root,
            session_id,
            "agent",
            "calibration_complete",
            "Calibration complete. Profile created for outgoing-message adaptation.",
            ["personal_interface", "calibration"],
        )
        _close_calibration_session(root, session_id)
        return {
            "session_id": session_id,
            "completed": True,
            "profile_summary": {
                "default_mode": profile["mode_preferences"]["default_mode"],
                "verbosity": profile["baseline_preferences"]["verbosity"],
                "branching_tolerance": profile["baseline_preferences"]["branching_tolerance"],
            },
        }

    state["current_question_id"] = next_question_id
    write_json(_calibration_state_path(root, session_id), state)
    _append_session_event(
        root,
        session_id,
        "agent",
        "calibration_question",
        CALIBRATION_INDEX[next_question_id]["prompt"],
        ["personal_interface", "calibration", next_question_id],
    )
    return _question_payload(next_question_id, state)


def get_profile_snapshot(root: Path) -> Dict[str, Any]:
    return load_personal_interface_profile(root)


def _count_keywords(text: str, keywords: List[str]) -> int:
    lower = text.lower()
    return sum(1 for keyword in keywords if keyword in lower)


def _infer_mode(user_message: str, draft_text: str, caller_hints: Dict[str, Any], profile: Dict[str, Any]) -> tuple[str, float, str]:
    declared = (caller_hints or {}).get("declared_mode")
    if declared in FLOW_MODES:
        return declared, 1.0, "caller_hint"

    combined = f"{user_message}\n{draft_text}"
    scores = {mode: _count_keywords(combined, keywords) for mode, keywords in MODE_KEYWORDS.items()}
    mode = max(scores, key=scores.get)
    score = scores[mode]
    if score <= 0:
        return profile["mode_preferences"].get("default_mode", "development_flow"), 0.4, "default_fallback"
    confidence = min(0.95, 0.45 + score * 0.12)
    if confidence < 0.55:
        return profile["mode_preferences"].get("default_mode", "development_flow"), confidence, "low_confidence_default"
    return mode, confidence, "keyword_inference"


def identify_communication_mode(
    user_message: str,
    draft_text: str,
    flow_mode: str,
    caller_hints: Dict[str, Any] | None,
    profile: Dict[str, Any],
) -> Dict[str, Any]:
    caller_hints = caller_hints or {}
    declared = caller_hints.get("declared_communication_mode")
    if declared in COMMUNICATION_MODES:
        spec = COMMUNICATION_MODE_SPECS[declared]
        return {
            "mode": declared,
            "confidence": 1.0,
            "inference_source": "caller_hint",
            "axes": dict(spec["axes"]),
            "matched_signals": ["declared_communication_mode"],
            "scorecard": {declared: 10.0},
        }

    combined = f"{user_message}\n{draft_text}".lower()
    communication_preferences = profile.get("communication_preferences", {})
    translation_preferences = profile.get("translation_preferences", {})
    default_mode = communication_preferences.get("default_mode", "scaffolded_guidance")
    profile_directionality = communication_preferences.get("directionality_preference", "guiding")
    profile_stance = communication_preferences.get("stance_preference", "balanced")
    goal = caller_hints.get("goal")
    desired_depth = caller_hints.get("desired_depth")
    urgency = caller_hints.get("urgency")
    interruption_style = profile.get("interaction_preferences", {}).get("interruption_style", "flag_gently")

    scorecard: Dict[str, float] = {}
    matched_signals: Dict[str, List[str]] = {}
    for mode_name, spec in COMMUNICATION_MODE_SPECS.items():
        score = 0.0
        reasons: List[str] = []

        if flow_mode in spec["flow_modes"]:
            score += 1.6
            reasons.append(f"flow:{flow_mode}")
        if goal in spec["goal_signals"]:
            score += 2.4
            reasons.append(f"goal:{goal}")
        if translation_preferences.get("enabled") and translation_preferences.get("preferred_mode") == mode_name:
            score += 0.4
            reasons.append("translation_profile")
        if default_mode == mode_name:
            score += 0.8
            reasons.append("profile_default")
        if flow_mode == "decision_flow" and communication_preferences.get("decision_communication_mode") == mode_name:
            score += 1.1
            reasons.append("profile_decision_mode")
        if interruption_style in {"challenge_if_high_stakes", "challenge_early"} and mode_name == communication_preferences.get("challenge_communication_mode"):
            score += 0.9
            reasons.append("challenge_preference")
        if spec["axes"]["directionality"] == profile_directionality:
            score += 0.35
            reasons.append("directionality_match")
        if spec["axes"]["stance"] == profile_stance:
            score += 0.35
            reasons.append("stance_match")

        for signal in spec["text_signals"]:
            if signal in combined:
                score += 0.45
                reasons.append(f"signal:{signal}")

        if "?" in user_message and spec["axes"]["primary_function"] == "probe":
            score += 0.35
            reasons.append("question_mark")
        if desired_depth == "short" and mode_name in {"scaffolded_guidance", "decisive_direction"}:
            score += 0.25
            reasons.append("short_depth")
        if desired_depth == "deep" and mode_name in {"exploratory_probe", "structured_synthesis", "analytic_challenge"}:
            score += 0.25
            reasons.append("deep_depth")
        if urgency == "high" and mode_name == "decisive_direction":
            score += 0.35
            reasons.append("high_urgency")
        if mode_name == "concept_translation":
            if translation_preferences.get("translation_bias") == "high":
                score += 0.7
                reasons.append("high_translation_bias")
            if flow_mode in {"development_flow", "synthesis_flow"}:
                score += 0.45
                reasons.append("translation_friendly_flow")
            if any(token in combined for token in ["product", "architecture", "concept", "pattern", "translate", "technical", "layer", "system"]):
                score += 1.0
                reasons.append("translation_keywords")

        scorecard[mode_name] = round(score, 3)
        matched_signals[mode_name] = reasons

    selected_mode = max(scorecard, key=scorecard.get)
    ranked = sorted(scorecard.values(), reverse=True)
    best_score = ranked[0]
    second_score = ranked[1] if len(ranked) > 1 else 0.0
    if best_score < 1.4:
        selected_mode = default_mode
        confidence = 0.46
        inference_source = "profile_default"
    else:
        margin = max(0.0, best_score - second_score)
        confidence = min(0.96, 0.52 + best_score * 0.06 + margin * 0.05)
        inference_source = "heuristic_inference"

    return {
        "mode": selected_mode,
        "confidence": round(confidence, 2),
        "inference_source": inference_source,
        "axes": dict(COMMUNICATION_MODE_SPECS[selected_mode]["axes"]),
        "matched_signals": matched_signals.get(selected_mode, []),
        "scorecard": scorecard,
    }


def _select_tactics(mode: str, profile: Dict[str, Any], policy_snapshot: Dict[str, Any]) -> List[str]:
    tactics = list(MODE_TACTICS.get(mode, MODE_TACTICS["development_flow"]))
    if profile["baseline_preferences"].get("branching_tolerance") == "low" and "reduce_branching" not in tactics:
        tactics.append("reduce_branching")
    if profile["baseline_preferences"].get("verbosity") == "concise" and "compress_response" not in tactics:
        tactics.append("compress_response")
    if profile["baseline_preferences"].get("abstraction_preference") == "concrete_first":
        tactics.append("ground_in_concrete")
    if profile["baseline_preferences"].get("challenge_tolerance") == "low":
        tactics.append("avoid_premature_challenge")
    if mode == "decision_flow":
        decision_style = profile.get("mode_preferences", {}).get("decision_style")
        if decision_style == "clear_recommendation":
            tactics.append("prioritize_recommendation")
        elif decision_style == "compare_tradeoffs":
            tactics.append("state_tradeoffs")
        elif decision_style == "evidence_first":
            tactics.append("lead_with_evidence")

    penalties = policy_snapshot.get("tactic_penalties", {})
    filtered = [
        tactic
        for tactic in tactics
        if penalties.get(tactic, 0.0) < 0.2 or tactic in {"reduce_branching", "compress_response"}
    ]
    return filtered or tactics


def _extract_code_blocks(text: str) -> List[str]:
    return re.findall(r"```.*?```", text, flags=re.DOTALL)


def _extract_urls(text: str) -> List[str]:
    return re.findall(r"https?://\S+", text)


def _extract_numbers(text: str) -> List[str]:
    return re.findall(r"\b\d+(?:\.\d+)?\b", text)


def _fidelity_warning(draft_text: str, adapted_text: str) -> str | None:
    if _extract_code_blocks(draft_text) != _extract_code_blocks(adapted_text):
        return "code_blocks_changed"
    if _extract_urls(draft_text) != _extract_urls(adapted_text):
        return "urls_changed"
    if _extract_numbers(draft_text) != _extract_numbers(adapted_text):
        return "numbers_changed"
    return None


def _diff_summary(draft_text: str, adapted_text: str) -> Dict[str, Any]:
    draft_tokens = len(draft_text.split())
    adapted_tokens = len(adapted_text.split())
    draft_bullets = draft_text.count("\n- ") + draft_text.count("\n* ")
    adapted_bullets = adapted_text.count("\n- ") + adapted_text.count("\n* ")
    return {
        "token_delta": adapted_tokens - draft_tokens,
        "branch_reduction": draft_bullets - adapted_bullets,
        "structure_delta": {
            "draft_lines": len(draft_text.splitlines()),
            "adapted_lines": len(adapted_text.splitlines()),
        },
    }


def compile_turn_policy(
    profile: Dict[str, Any],
    mode: str,
    confidence: float,
    communication_mode: str,
    communication_axes: Dict[str, Any],
    caller_hints: Dict[str, Any] | None,
    policy_snapshot: Dict[str, Any] | None,
) -> Dict[str, Any]:
    caller_hints = caller_hints or {}
    policy_snapshot = policy_snapshot or {}
    tactics = _select_tactics(mode, profile, policy_snapshot)
    penalties = policy_snapshot.get("tactic_penalties", {})
    suppressed_instruction_keys = {
        key for key, value in penalties.items() if isinstance(value, (int, float)) and value >= 0.3
    }
    communication_spec = COMMUNICATION_MODE_SPECS.get(communication_mode, COMMUNICATION_MODE_SPECS["scaffolded_guidance"])
    translation_preferences = profile.get("translation_preferences", {})
    learned_conversation_preferences = (
        profile.get("learning_preferences", {}).get("learned_from_conversations", {})
        if isinstance(profile.get("learning_preferences", {}), dict)
        else {}
    )

    instruction_bundle: List[Dict[str, Any]] = []

    def add_instruction(key: str, text: str, priority: int, source: str, suppress_key: str | None = None) -> None:
        if suppress_key and suppress_key in suppressed_instruction_keys and not caller_hints.get("force_policy"):
            return
        instruction_bundle.append(
            {
                "key": key,
                "text": text,
                "priority": priority,
                "source": source,
                "suppress_key": suppress_key,
            }
        )

    add_instruction("mode", f"Current mode: {mode}.", 100, "mode")
    add_instruction("communication_mode", f"Communication mode: {communication_mode}.", 96, "communication")

    directionality = communication_axes.get("directionality")
    if directionality == "following":
        add_instruction("communication_directionality", "Track the user's line before redirecting or adding structure.", 76, "communication")
    elif directionality == "guiding":
        add_instruction("communication_directionality", "Guide collaboratively and keep the next step visible.", 76, "communication")
    elif directionality == "directing":
        add_instruction("communication_directionality", "Be comfortable taking a position when the turn calls for it.", 76, "communication")

    stance = communication_axes.get("stance")
    if stance == "warm":
        add_instruction("communication_stance", "Sound attuned and low-friction rather than clinical.", 62, "communication")
    elif stance == "balanced":
        add_instruction("communication_stance", "Keep the tone direct and collaborative.", 62, "communication")
    elif stance == "open":
        add_instruction("communication_stance", "Keep the tone invitational and possibility-oriented.", 62, "communication")
    elif stance == "precise":
        add_instruction("communication_stance", "Prefer exact language over cushioning or flourish.", 62, "communication")
    elif stance == "assertive":
        add_instruction("communication_stance", "Sound decisive without becoming coercive.", 62, "communication")

    communication_priority_base = 92 if communication_mode == "concept_translation" else 74
    for index, text in enumerate(communication_spec["instructions"]):
        add_instruction(f"communication_behavior_{index}", text, communication_priority_base - index, "communication")

    if communication_mode == "concept_translation" and translation_preferences.get("enabled"):
        target_artifacts = translation_preferences.get("target_artifacts", [])
        output_contract = translation_preferences.get("output_contract", [])
        if target_artifacts:
            add_instruction(
                "translation_targets",
                f"Prefer mapping ideas onto these artifact types when relevant: {', '.join(target_artifacts)}.",
                73,
                "translation",
            )
        if output_contract:
            add_instruction(
                "translation_contract",
                f"When helpful, structure the translation around: {', '.join(output_contract)}.",
                72,
                "translation",
            )
        if translation_preferences.get("preserve_uncertainty"):
            add_instruction(
                "translation_uncertainty",
                "Make uncertainty explicit when the technical mapping is inferred rather than directly stated.",
                75,
                "translation",
            )

    if profile["baseline_preferences"].get("verbosity") == "concise":
        add_instruction("verbosity", "Write a concise reply that keeps the user moving.", 89, "profile", "compress_response")
    else:
        add_instruction("verbosity", "Keep the reply compact unless more detail is necessary for clarity.", 82, "profile")

    if caller_hints.get("allow_branching") is False:
        add_instruction("branching", "Do not branch into multiple options unless necessary.", 95, "caller_hint")
    elif profile["baseline_preferences"].get("branching_tolerance") == "low" or "reduce_branching" in tactics:
        add_instruction("branching", "Do not branch into multiple options unless necessary.", 83, "profile", "reduce_branching")

    if profile["baseline_preferences"].get("structure_density") == "light":
        add_instruction("structure", "Use minimal structure and avoid heavy formatting.", 72, "profile")
    elif profile["baseline_preferences"].get("structure_density") == "medium":
        add_instruction("structure", "Use only light structure that improves immediate comprehension.", 70, "profile")

    if profile["baseline_preferences"].get("abstraction_preference") == "concrete_first":
        add_instruction("abstraction", "Prefer grounding the reply in the concrete situation before abstracting.", 68, "profile")
    elif profile["baseline_preferences"].get("abstraction_preference") == "abstract_first":
        add_instruction("abstraction", "Lead with the core pattern before expanding into examples.", 68, "profile")

    interruption_style = profile.get("interaction_preferences", {}).get("interruption_style")
    if interruption_style == "flag_gently":
        add_instruction("challenge_timing", "If you flag a weak assumption, do it briefly without derailing the thread.", 78, "profile")
    elif profile["baseline_preferences"].get("challenge_tolerance") == "high":
        add_instruction("challenge_timing", "Do not avoid necessary challenge when a weak premise affects the answer.", 74, "profile")

    if mode == "capture_flow":
        add_instruction("mode_capture", "Optimize for continuity of thought over completeness.", 88, "mode")
    elif mode == "development_flow":
        add_instruction("mode_development", "Stay with the current thread and clarify without opening detours.", 86, "mode")
    elif mode == "exploratory_flow":
        add_instruction("mode_exploratory", "Allow light expansion, but keep the main line legible.", 84, "mode")
    elif mode == "synthesis_flow":
        add_instruction("mode_synthesis", "Compress patterns and highlight what connects the pieces.", 86, "mode")
    elif mode == "decision_flow":
        decision_style = profile.get("mode_preferences", {}).get("decision_style")
        if decision_style == "clear_recommendation":
            add_instruction("decision_style", "Give a clear recommendation once the main tradeoff is understood.", 90, "mode")
        elif decision_style == "compare_tradeoffs":
            add_instruction("decision_style", "State the tight tradeoff clearly before recommending.", 88, "mode")
        elif decision_style == "questions_first":
            add_instruction("decision_style", "Ask for the single missing thing before committing to a recommendation.", 87, "mode")
        elif decision_style == "evidence_first":
            add_instruction("decision_style", "Ground the decision in the key evidence before recommending.", 88, "mode")

    goal = caller_hints.get("goal")
    if goal == "choose_best_option":
        add_instruction("goal_choose", "Optimize for a fast decision rather than broad exploration.", 94, "caller_hint")
        add_instruction("goal_answer_first", "Lead with the answer before supporting detail.", 91, "caller_hint")
    elif goal == "clarify_thinking":
        add_instruction("goal_clarify", "Clarify the main line before adding secondary detail.", 88, "caller_hint")
    elif goal == "generate_options":
        add_instruction("goal_options", "Generate only the smallest useful set of options.", 84, "caller_hint")
    elif goal == "translate_concepts_to_technical":
        add_instruction("goal_translate", "Translate the product idea into a clean technical framing that can drive implementation.", 90, "caller_hint")
    elif goal == "teach_user":
        add_instruction("goal_teach", "Optimize the reply for understanding, retention, and the next useful question.", 90, "caller_hint")

    desired_depth = caller_hints.get("desired_depth")
    if desired_depth == "short":
        add_instruction("depth_short", "Bias toward the shortest useful reply.", 92, "caller_hint")
    elif desired_depth == "deep":
        add_instruction("depth_deep", "Add depth only where it directly helps the current objective.", 76, "caller_hint")

    urgency = caller_hints.get("urgency")
    if urgency == "high":
        add_instruction("urgency", "Prioritize speed and decisiveness over completeness.", 79, "caller_hint")

    disliked_patterns = profile["rhetorical_preferences"].get("disliked_patterns", [])
    if disliked_patterns:
        add_instruction("avoid_patterns", f"Avoid these patterns: {', '.join(disliked_patterns)}.", 58, "profile")

    if caller_hints.get("goal") == "teach_user" and learned_conversation_preferences.get("enabled"):
        guiding_path = learned_conversation_preferences.get("guiding_path")
        example_preferences = learned_conversation_preferences.get("example_preferences", [])
        followup_preferences = learned_conversation_preferences.get("followup_preferences", [])
        followup_dynamics = learned_conversation_preferences.get("followup_dynamics", {})
        if guiding_path:
            add_instruction(
                "learned_path",
                f"Follow the user's learned path when teaching: {guiding_path}.",
                95,
                "learning_profile",
            )
        if example_preferences:
            add_instruction(
                "learned_examples",
                f"Prefer these observed example types when they fit: {', '.join(example_preferences)}.",
                94,
                "learning_profile",
            )
        if "technical_mapping" in followup_preferences:
            add_instruction(
                "learned_followup",
                "End with the next technical mapping step when possible.",
                93,
                "learning_profile",
            )
        if int(followup_dynamics.get("answer_reference_count", 0)) > 0:
            add_instruction(
                "learned_answer_reference",
                "Make key terms easy to point back to because the user often follows up on your exact wording.",
                92,
                "learning_profile",
            )
        if int(followup_dynamics.get("self_reference_count", 0)) > 0:
            add_instruction(
                "learned_self_reference",
                "Reconnect explanations to the user's original question after local clarifications.",
                91,
                "learning_profile",
            )
        if "clarification" in followup_dynamics.get("intent_types", []):
            add_instruction(
                "learned_clarification",
                "Define the load-bearing term clearly before moving into deeper explanation.",
                90,
                "learning_profile",
            )

    add_instruction("safety_meaning", "Preserve factual meaning.", 98, "safety")
    add_instruction("safety_literals", "Do not introduce new URLs, numbers, commands, or constraints.", 97, "safety")

    deduped_by_key: Dict[str, Dict[str, Any]] = {}
    for item in sorted(instruction_bundle, key=lambda row: (row["priority"], row["source"] == "caller_hint"), reverse=True):
        deduped_by_key.setdefault(item["key"], item)

    ordered_bundle = sorted(deduped_by_key.values(), key=lambda row: row["priority"], reverse=True)
    max_instruction_lines = 11 if caller_hints.get("goal") == "teach_user" else 8
    instruction_lines = [item["text"] for item in ordered_bundle[:max_instruction_lines]]

    return {
        "mode": mode,
        "confidence": round(confidence, 2),
        "communication_mode": communication_mode,
        "communication_axes": communication_axes,
        "applied_tactics": tactics,
        "instruction_lines": instruction_lines,
        "instruction_bundle": ordered_bundle,
        "suppressed_instruction_keys": sorted(suppressed_instruction_keys),
    }


def _compose_rewrite_prompt(payload: Dict[str, Any]) -> str:
    compiled_turn_policy = payload["compiled_turn_policy"]
    return "\n".join(
        [
            "Rewrite the draft reply to preserve user momentum.",
            "",
            "Turn policy:",
            *[f"- {line}" for line in compiled_turn_policy["instruction_lines"]],
            "",
            "User message:",
            payload["user_message"],
            "",
            "Draft reply:",
            payload["draft_text"],
            "",
            "Requirements:",
            "- Match the turn policy exactly.",
            "- Return only the rewritten reply.",
        ]
    )


def _run_command_backend(root: Path, payload: Dict[str, Any], backend: Dict[str, Any]) -> Dict[str, Any]:
    command = backend.get("command")
    if not command:
        raise PersonalInterfaceError("rewrite_backend_unavailable", "No command configured for command_json rewrite backend.")
    completed = subprocess.run(
        command,
        cwd=root,
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=int(backend.get("timeout_seconds", 45)),
        check=False,
    )
    if completed.returncode != 0:
        raise PersonalInterfaceError(
            "rewrite_backend_failed",
            completed.stderr.strip() or completed.stdout.strip() or f"Rewrite backend exited with code {completed.returncode}.",
        )
    try:
        response = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise PersonalInterfaceError("rewrite_backend_invalid_json", "Rewrite backend returned invalid JSON.") from exc
    return response


def _run_openclaw_local_backend(root: Path, payload: Dict[str, Any], backend: Dict[str, Any]) -> Dict[str, Any]:
    command = [
        backend.get("command", "openclaw"),
        "agent",
        "--agent",
        backend.get("agent", "main"),
        "--thinking",
        backend.get("thinking", "minimal"),
        "--message",
        _compose_rewrite_prompt(payload),
        "--local",
        "--json",
    ]
    completed = subprocess.run(
        command,
        cwd=root,
        capture_output=True,
        text=True,
        timeout=int(backend.get("timeout_seconds", 60)),
        check=False,
    )
    if completed.returncode != 0:
        raise PersonalInterfaceError(
            "rewrite_backend_failed",
            completed.stderr.strip() or completed.stdout.strip() or f"openclaw exited with code {completed.returncode}.",
        )
    try:
        response = json.loads(completed.stdout)
    except json.JSONDecodeError:
        response = {"adapted_text": completed.stdout.strip()}
    return {
        "adapted_text": response.get("adapted_text")
        or response.get("reply")
        or response.get("text")
        or response.get("content")
        or "",
        "backend_metadata": {"backend": "openclaw_local"},
    }


def _load_runtime(root: Path) -> Dict[str, Any]:
    runtime = read_json(_runtime_path(root), default={})
    return runtime.get("rewrite_backend", runtime)


def _active_terms(user_message: str, draft_text: str) -> List[str]:
    counts: Dict[str, int] = {}
    for token in re.findall(r"[a-zA-Z][a-zA-Z_-]{2,}", f"{user_message} {draft_text}".lower()):
        if token in {"this", "that", "with", "from", "have", "just", "keep", "right", "into"}:
            continue
        counts[token] = counts.get(token, 0) + 1
    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return [token for token, _ in ranked[:8]]


def _infer_bridge_mood(
    user_message: str,
    caller_hints: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    caller_hints = caller_hints or {}
    lowered = user_message.lower()
    evidence: List[str] = []
    label = "focused"
    valence = "neutral"
    energy = "steady"
    confidence = 0.42

    for marker in STRESSED_MARKERS:
        if marker in lowered:
            evidence.append(marker)
    if evidence:
        label = "stressed"
        valence = "negative"
        energy = "low"
        confidence = 0.82
    else:
        for marker in FRUSTRATED_MARKERS:
            if marker in lowered:
                evidence.append(marker)
        if evidence:
            label = "frustrated"
            valence = "negative"
            energy = "high"
            confidence = 0.74
        else:
            for marker in EXPLORATORY_MARKERS:
                if marker in lowered:
                    evidence.append(marker)
            if caller_hints.get("goal") == "generate_options" and "generate_options" not in evidence:
                evidence.append("goal:generate_options")
            if evidence:
                label = "exploratory"
                valence = "positive"
                energy = "steady"
                confidence = 0.7
            else:
                for marker in DECISIVE_MARKERS:
                    if marker in lowered:
                        evidence.append(marker)
                if caller_hints.get("goal") == "choose_best_option" and "goal:choose_best_option" not in evidence:
                    evidence.append("goal:choose_best_option")
                if evidence:
                    label = "decisive"
                    valence = "neutral"
                    energy = "high"
                    confidence = 0.68

    return {
        "label": label,
        "valence": valence,
        "energy": energy,
        "confidence": round(confidence, 2),
        "evidence": evidence[:4],
        "captured_at": utc_now(),
    }


def _merge_behavior_patterns(
    existing_rows: List[Dict[str, Any]],
    incoming_rows: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    index = {
        str(row.get("pattern_key", "")).strip(): dict(row)
        for row in existing_rows
        if str(row.get("pattern_key", "")).strip()
    }
    for row in incoming_rows:
        pattern_key = str(row.get("pattern_key", "")).strip()
        if not pattern_key:
            continue
        existing = index.get(pattern_key)
        if existing is None:
            normalized = dict(row)
            normalized["count"] = int(normalized.get("count", 1))
            index[pattern_key] = normalized
            continue
        existing["count"] = int(existing.get("count", 1)) + 1
        existing["confidence"] = max(float(existing.get("confidence", 0.0)), float(row.get("confidence", 0.0)))
        existing["last_seen_at"] = row.get("last_seen_at", existing.get("last_seen_at", ""))
        existing_evidence = list(existing.get("evidence", []))
        for evidence in row.get("evidence", []):
            if evidence not in existing_evidence:
                existing_evidence.append(evidence)
        existing["evidence"] = existing_evidence[:6]
    return sorted(index.values(), key=lambda row: (-int(row.get("count", 1)), row.get("pattern_key", "")))


def _infer_behavior_patterns(
    user_message: str,
    caller_hints: Dict[str, Any],
    profile: Dict[str, Any],
    compiled_turn_policy: Dict[str, Any],
    communication_mode: str,
) -> List[Dict[str, Any]]:
    patterns: List[Dict[str, Any]] = []
    seen_at = utc_now()

    def add_pattern(pattern_key: str, label: str, confidence: float, evidence: List[str]) -> None:
        patterns.append(
            {
                "pattern_key": pattern_key,
                "label": label,
                "confidence": round(confidence, 2),
                "evidence": evidence[:4],
                "count": 1,
                "last_seen_at": seen_at,
            }
        )

    if profile.get("baseline_preferences", {}).get("verbosity") == "concise":
        add_pattern("prefers_concise_answers", "Prefers concise answers", 0.8, ["profile:verbosity=concise"])
    if profile.get("rhetorical_preferences", {}).get("directness") == "high":
        add_pattern("prefers_direct_language", "Prefers direct language", 0.78, ["profile:directness=high"])
    if caller_hints.get("desired_depth") == "short":
        add_pattern("requests_short_depth", "Requests short depth", 0.86, ["hint:desired_depth=short"])
    if caller_hints.get("desired_depth") == "deep":
        add_pattern("requests_deep_context", "Requests deep context", 0.82, ["hint:desired_depth=deep"])
    if "avoid_premature_challenge" in compiled_turn_policy.get("applied_tactics", []):
        add_pattern("low_challenge_tolerance", "Low challenge tolerance", 0.7, ["policy:avoid_premature_challenge"])
    if communication_mode == "concept_translation":
        add_pattern("asks_for_concept_translation", "Asks for concept translation", 0.88, ["communication:concept_translation"])
    if "?" in user_message:
        add_pattern("uses_question_driven_reasoning", "Uses question-driven reasoning", 0.58, ["message:question_mark"])
    return patterns


def _update_bridge_state(
    root: Path,
    *,
    rewrite_event_id: str,
    user_message: str,
    draft_text: str,
    conversation_window: List[Dict[str, Any]],
    caller_hints: Dict[str, Any],
    client_context: Dict[str, Any],
    profile: Dict[str, Any],
    mode: str,
    mode_confidence: float,
    communication: Dict[str, Any],
    compiled_turn_policy: Dict[str, Any],
    runtime: Dict[str, Any],
    diff_summary: Dict[str, Any],
) -> Dict[str, Any]:
    state = load_bridge_state(root)
    current_mood = _infer_bridge_mood(user_message, caller_hints)
    mood_history = list(state.get("mood_history", []))
    mood_history.append(current_mood)
    state["updated_at"] = utc_now()
    state["latest_rewrite_event_id"] = rewrite_event_id
    state["current_mood"] = current_mood
    state["mood_history"] = mood_history[-6:]
    state["context"] = {
        "user_message": user_message,
        "conversation_window_size": len(conversation_window),
        "conversation_turn_count": int(client_context.get("conversation_turn_count", len(conversation_window) or 1)),
        "active_terms": _active_terms(user_message, draft_text),
        "caller_hints": caller_hints,
        "client_context": client_context,
    }
    state["personalization"] = {
        "verbosity": profile.get("baseline_preferences", {}).get("verbosity", ""),
        "directness": profile.get("rhetorical_preferences", {}).get("directness", ""),
        "structure_density": profile.get("baseline_preferences", {}).get("structure_density", ""),
        "challenge_tolerance": profile.get("baseline_preferences", {}).get("challenge_tolerance", ""),
        "preferred_cadence": profile.get("rhetorical_preferences", {}).get("preferred_cadence", ""),
    }
    state["presentation"] = {
        "current_mode": mode,
        "mode_confidence": round(mode_confidence, 2),
        "communication_mode": communication["mode"],
        "communication_confidence": communication["confidence"],
        "applied_tactics": compiled_turn_policy.get("applied_tactics", []),
        "rewrite_backend": runtime.get("id", ""),
    }
    state["behavior_patterns"] = _merge_behavior_patterns(
        state.get("behavior_patterns", []),
        _infer_behavior_patterns(user_message, caller_hints, profile, compiled_turn_policy, communication["mode"]),
    )
    telemetry = dict(state.get("telemetry", {}))
    telemetry["rewrite_count"] = int(telemetry.get("rewrite_count", 0)) + 1
    telemetry["last_backend"] = runtime.get("id", "")
    telemetry["last_diff_summary"] = diff_summary
    state["telemetry"] = telemetry
    write_json(_bridge_state_path(root), state)
    return state


def _normalize_conversation_turns(conversation: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []
    role_map = {
        "user": "user",
        "human": "user",
        "assistant": "assistant",
        "agent": "assistant",
        "system": "system",
    }
    for index, turn in enumerate(conversation):
        role = role_map.get(str(turn.get("role") or turn.get("actor") or "").lower(), "unknown")
        content = turn.get("content")
        if content is None:
            content = turn.get("message")
        if content is None:
            content = turn.get("text")
        content = str(content or "").strip()
        if not content:
            continue
        normalized_turn = {
            "role": role,
            "content": content,
        }
        if turn.get("turn_id") is not None:
            normalized_turn["turn_id"] = turn.get("turn_id")
        elif turn.get("event_id") is not None:
            normalized_turn["turn_id"] = turn.get("event_id")
        else:
            normalized_turn["turn_id"] = f"turn-{index}"
        if turn.get("timestamp") is not None:
            normalized_turn["timestamp"] = turn.get("timestamp")
        normalized.append(normalized_turn)
    return normalized


def rewrite_conversation_turn(
    root: Path,
    draft_text: str,
    conversation: List[Dict[str, Any]],
    caller_hints: Dict[str, Any] | None = None,
    client_context: Dict[str, Any] | None = None,
    window_size: int = 8,
) -> Dict[str, Any]:
    normalized_turns = _normalize_conversation_turns(conversation)
    latest_user_turn = next((turn for turn in reversed(normalized_turns) if turn["role"] == "user"), None)
    if latest_user_turn is None:
        raise PersonalInterfaceError(
            "conversation_user_message_missing",
            "Conversation payload does not contain a user turn to anchor rewriting.",
        )

    bounded_window = normalized_turns[-max(1, int(window_size)) :]
    merged_client_context = dict(client_context or {})
    merged_client_context.setdefault("conversation_turn_count", len(normalized_turns))
    merged_client_context.setdefault("latest_user_turn_id", latest_user_turn.get("turn_id"))
    merged_client_context.setdefault("latest_turn_role", normalized_turns[-1]["role"] if normalized_turns else None)

    return rewrite_outgoing_message(
        root,
        draft_text=draft_text,
        user_message=latest_user_turn["content"],
        conversation_window=bounded_window,
        caller_hints=caller_hints or {},
        client_context=merged_client_context,
    )


def rewrite_outgoing_message(
    root: Path,
    draft_text: str,
    user_message: str,
    conversation_window: List[Dict[str, Any]] | None = None,
    caller_hints: Dict[str, Any] | None = None,
    client_context: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    ensure_personal_interface_runtime(root)
    profile = load_personal_interface_profile(root)
    policy_snapshot = load_personal_interface_policy_snapshot(root)
    runtime = _load_runtime(root)
    if not runtime or not runtime.get("id"):
        raise PersonalInterfaceError(
            "rewrite_backend_unavailable",
            "Rewrite backend is not configured.",
            {"next_action": "Configure product/personal_interface_v1/data/runtime.json"},
        )

    mode, confidence, inference_source = _infer_mode(user_message, draft_text, caller_hints or {}, profile)
    communication = identify_communication_mode(
        user_message=user_message,
        draft_text=draft_text,
        flow_mode=mode,
        caller_hints=caller_hints or {},
        profile=profile,
    )
    compiled_turn_policy = compile_turn_policy(
        profile=profile,
        mode=mode,
        confidence=confidence,
        communication_mode=communication["mode"],
        communication_axes=communication["axes"],
        caller_hints=caller_hints or {},
        policy_snapshot=policy_snapshot,
    )
    tactics = compiled_turn_policy["applied_tactics"]
    payload = {
        "draft_text": draft_text,
        "user_message": user_message,
        "conversation_window": conversation_window or [],
        "caller_hints": caller_hints or {},
        "client_context": client_context or {},
        "profile": profile,
        "policy": {
            "mode": mode,
            "mode_confidence": confidence,
            "inference_source": inference_source,
            "communication_mode": communication["mode"],
            "communication_confidence": communication["confidence"],
            "communication_inference_source": communication["inference_source"],
            "communication_axes": communication["axes"],
            "applied_tactics": tactics,
        },
        "compiled_turn_policy": compiled_turn_policy,
    }
    payload["rewrite_prompt"] = _compose_rewrite_prompt(payload)

    if runtime["id"] == "command_json":
        backend_result = _run_command_backend(root, payload, runtime)
    elif runtime["id"] == "openclaw_local":
        backend_result = _run_openclaw_local_backend(root, payload, runtime)
    else:
        raise PersonalInterfaceError("rewrite_backend_unavailable", f"Unsupported rewrite backend: {runtime['id']}")

    adapted_text = (backend_result.get("adapted_text") or "").strip()
    if not adapted_text:
        raise PersonalInterfaceError("rewrite_backend_empty", "Rewrite backend returned an empty adapted_text.")

    warnings: List[str] = []
    fidelity_warning = _fidelity_warning(draft_text, adapted_text)
    if fidelity_warning:
        warnings.append("rewrite_rejected_fidelity")
        warnings.append(fidelity_warning)
        adapted_text = draft_text

    rewrite_event = {
        "rewrite_event_id": make_id("rewrite"),
        "created_at": utc_now(),
        "draft_text": draft_text,
        "adapted_text": adapted_text,
        "user_message": user_message,
        "conversation_window": conversation_window or [],
        "caller_hints": caller_hints or {},
        "client_context": client_context or {},
        "policy": payload["policy"],
        "compiled_turn_policy": compiled_turn_policy,
        "rewrite_prompt": payload["rewrite_prompt"],
        "profile_version": profile["profile_version"],
        "rewrite_backend": runtime["id"],
        "backend_metadata": backend_result.get("backend_metadata", {}),
        "warnings": warnings,
    }
    append_jsonl(_rewrite_events_path(root), rewrite_event)
    diff_summary = _diff_summary(draft_text, adapted_text)
    _update_bridge_state(
        root,
        rewrite_event_id=rewrite_event["rewrite_event_id"],
        user_message=user_message,
        draft_text=draft_text,
        conversation_window=conversation_window or [],
        caller_hints=caller_hints or {},
        client_context=client_context or {},
        profile=profile,
        mode=mode,
        mode_confidence=confidence,
        communication=communication,
        compiled_turn_policy=compiled_turn_policy,
        runtime=runtime,
        diff_summary=diff_summary,
    )
    return {
        "rewrite_event_id": rewrite_event["rewrite_event_id"],
        "adapted_text": adapted_text,
        "policy_metadata": {
            "mode": mode,
            "mode_confidence": round(confidence, 2),
            "inference_source": inference_source,
            "communication_mode": communication["mode"],
            "communication_confidence": communication["confidence"],
            "communication_inference_source": communication["inference_source"],
            "communication_axes": communication["axes"],
            "applied_tactics": tactics,
            "compiled_turn_policy": compiled_turn_policy["instruction_lines"],
            "instruction_bundle": compiled_turn_policy["instruction_bundle"],
            "suppressed_instruction_keys": compiled_turn_policy["suppressed_instruction_keys"],
            "profile_version": profile["profile_version"],
            "rewrite_backend": runtime["id"],
            "warnings": warnings,
        },
        "diff_summary": diff_summary,
    }


def record_rewrite_feedback(root: Path, rewrite_event_id: str, feedback_state: str) -> Dict[str, Any]:
    ensure_personal_interface_runtime(root)
    if feedback_state not in TACTIC_REACTIONS:
        raise PersonalInterfaceError("unsupported_feedback_state", f"Unsupported feedback state: {feedback_state}")

    rewrite_event = None
    for row in read_jsonl(_rewrite_events_path(root)):
        if row.get("rewrite_event_id") == rewrite_event_id:
            rewrite_event = row
            break
    if rewrite_event is None:
        raise PersonalInterfaceError("rewrite_event_missing", "Unknown rewrite event.", {"rewrite_event_id": rewrite_event_id})

    feedback_event = {
        "feedback_event_id": make_id("rewrite-feedback"),
        "created_at": utc_now(),
        "rewrite_event_id": rewrite_event_id,
        "feedback_state": feedback_state,
        "mode": rewrite_event["policy"]["mode"],
        "applied_tactics": rewrite_event["policy"]["applied_tactics"],
    }
    append_jsonl(_feedback_events_path(root), feedback_event)
    snapshot = _update_personal_interface_policy_snapshot(root)
    return {
        "feedback_event_id": feedback_event["feedback_event_id"],
        "rewrite_event_id": rewrite_event_id,
        "feedback_state": feedback_state,
        "policy_snapshot": snapshot,
    }
