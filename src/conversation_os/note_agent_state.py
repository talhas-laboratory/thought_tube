from __future__ import annotations

import re
from typing import Any, Dict, List

from .models import ResponseModeDecision, RetrievalPolicy, ThoughtInterpretation, UserState


NOTE_AGENT_SURFACES = {"mobile_capture", "thought_chat"}


def _tokenize_topic_signals(raw_text: str) -> List[str]:
    lowered = raw_text.lower()
    tokens = re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{2,}", lowered)
    seen: set[str] = set()
    topic_signals: List[str] = []
    for token in tokens:
        if token in seen:
            continue
        seen.add(token)
        topic_signals.append(token)
        if len(topic_signals) >= 6:
            break
    return topic_signals


def _is_note_agent_request(request_payload: Dict[str, Any]) -> bool:
    surface = str(request_payload.get("surface", "") or "").strip().lower()
    if surface in NOTE_AGENT_SURFACES:
        return True
    caller_hints = dict(request_payload.get("caller_hints", {}) or {})
    workspace_id = str(caller_hints.get("workspace_id", "") or "").strip().lower()
    if workspace_id.startswith("thought:"):
        return True
    return bool(str(caller_hints.get("thought_id", "") or "").strip())


def _infer_mode(raw_text: str) -> str:
    lowered = raw_text.lower().strip()
    if not lowered:
        return "dump"
    if any(term in lowered for term in ("i feel", "overwhelmed", "anxious", "afraid", "hurt", "sad", "angry")):
        return "emotionally_loaded"
    if any(term in lowered for term in ("what do you think", "is this good", "compare", "better", "worse", "opinion")):
        return "evaluative"
    if any(term in lowered for term in ("how do", "how should", "steps", "plan", "execute", "implement")):
        return "practical"
    if any(term in lowered for term in ("let's", "i will", "i'm going to", "decide", "choose")):
        return "decisive"
    if any(term in lowered for term in ("what if", "maybe", "could", "suggest", "possib")) or "?" in lowered:
        if any(term in lowered for term in ("i think", "i keep", "i notice", "circling", "pattern", "meaning")):
            return "reflective"
        return "exploratory"
    if any(term in lowered for term in ("i think", "i keep", "i notice", "pattern", "why", "meaning", "identity", "tension")):
        return "reflective"
    return "dump"


def _user_state_for_mode(mode: str) -> UserState:
    mapping = {
        "dump": UserState(mode="dump", confidence=0.62, pace="fast", response_pressure="low", retrieval_appetite="minimal", preferred_shape="ack"),
        "reflective": UserState(mode="reflective", confidence=0.79, pace="steady", response_pressure="medium", retrieval_appetite="bounded", preferred_shape="resonance"),
        "exploratory": UserState(mode="exploratory", confidence=0.72, pace="open", response_pressure="medium", retrieval_appetite="bounded", preferred_shape="continuation"),
        "emotionally_loaded": UserState(mode="emotionally_loaded", confidence=0.76, pace="gentle", response_pressure="low", retrieval_appetite="minimal", preferred_shape="resonance"),
        "evaluative": UserState(mode="evaluative", confidence=0.8, pace="steady", response_pressure="medium", retrieval_appetite="bounded", preferred_shape="evaluation"),
        "practical": UserState(mode="practical", confidence=0.83, pace="direct", response_pressure="high", retrieval_appetite="bounded", preferred_shape="actions"),
        "decisive": UserState(mode="decisive", confidence=0.78, pace="direct", response_pressure="high", retrieval_appetite="bounded", preferred_shape="actions"),
    }
    return mapping.get(mode, mapping["dump"])


def _retrieval_policy_for_mode(mode: str) -> RetrievalPolicy:
    if mode in {"reflective", "exploratory", "evaluative", "practical", "decisive"}:
        return RetrievalPolicy(
            retrieval_mode="session_plus_ocean",
            cross_ocean=False,
            retrieval_limit=6,
            neighbor_limit=4,
            include_layers=["session", "workspace", "user", "global"],
            exclude_layers=[],
            anchor_strategy="topic_first",
        )
    if mode == "emotionally_loaded":
        return RetrievalPolicy(
            retrieval_mode="session_only",
            cross_ocean=False,
            retrieval_limit=0,
            neighbor_limit=0,
            include_layers=["session", "workspace", "user"],
            exclude_layers=["global"],
            anchor_strategy="session_first",
        )
    return RetrievalPolicy(
        retrieval_mode="session_only",
        cross_ocean=False,
        retrieval_limit=0,
        neighbor_limit=0,
        include_layers=["session", "workspace"],
        exclude_layers=["global"],
        anchor_strategy="session_first",
    )


def _response_mode_for_mode(mode: str) -> ResponseModeDecision:
    mapping = {
        "dump": ResponseModeDecision(mode="silent_ack", directness="light", length="short", abstraction="concrete", preserve_ambiguity=True),
        "reflective": ResponseModeDecision(mode="resonance", directness="balanced", length="short", abstraction="mixed", preserve_ambiguity=True),
        "exploratory": ResponseModeDecision(mode="continuation_cue", directness="balanced", length="short", abstraction="mixed", preserve_ambiguity=True),
        "emotionally_loaded": ResponseModeDecision(mode="resonance", directness="gentle", length="short", abstraction="concrete", preserve_ambiguity=True),
        "evaluative": ResponseModeDecision(mode="evaluation", directness="direct", length="medium", abstraction="mixed", preserve_ambiguity=False),
        "practical": ResponseModeDecision(mode="action_suggestion", directness="direct", length="medium", abstraction="concrete", preserve_ambiguity=False),
        "decisive": ResponseModeDecision(mode="structure_proposal", directness="direct", length="medium", abstraction="concrete", preserve_ambiguity=False),
    }
    return mapping.get(mode, mapping["dump"])


def infer_note_agent_state(
    request_payload: Dict[str, Any],
    recent_events: List[Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    if not _is_note_agent_request(request_payload):
        return {}

    raw_text = str(request_payload.get("raw_text", "") or "").strip()
    recent = list(recent_events or [])
    mode = _infer_mode(raw_text)
    user_state = _user_state_for_mode(mode)
    retrieval_policy = _retrieval_policy_for_mode(mode)
    response_mode = _response_mode_for_mode(mode)
    lowered = raw_text.lower()
    thought_interpretation = ThoughtInterpretation(
        topic_signals=_tokenize_topic_signals(raw_text),
        tension_signals=["identity_tension"] if "identity" in lowered or "tension" in lowered else [],
        intent="question" if "?" in raw_text else "capture",
        abstraction_level="abstract" if any(term in lowered for term in ("identity", "meaning", "pattern")) else "mixed",
        emotional_weight=0.75 if mode == "emotionally_loaded" else 0.25,
        symbolic_weight=0.7 if any(term in lowered for term in ("identity", "meaning", "symbol")) else 0.2,
        practical_weight=0.8 if mode in {"practical", "decisive"} else 0.2,
        novelty_weight=0.55 if any(term in lowered for term in ("new", "suddenly", "surprising")) else 0.25,
        continuation_pressure=0.8 if "?" in raw_text or recent else 0.3,
    )
    return {
        "thought_interpretation": thought_interpretation.to_dict(),
        "user_state": user_state.to_dict(),
        "retrieval_policy": retrieval_policy.to_dict(),
        "response_mode": response_mode.to_dict(),
    }
