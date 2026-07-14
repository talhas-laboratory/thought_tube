from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from .bridge_session_tracking import (
    SESSION_STATUS_ACTIVE,
    get_bridge_session,
    session_trace_path,
)
from .storage import make_id, read_jsonl


MODULE_ID = "surface.bridge.bridge_session_context"
CONTRACT_VERSION = "1.0"
PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "CONTEXT_MODE_SESSION_ONLY",
    "CONTEXT_MODE_BOUNDED_GLOBAL",
    "CONTEXT_MODE_DEEP_GLOBAL",
    "build_dynamic_session_context",
    "session_rows_for_bundle",
    "resolve_context_retrieval_mode",
    "should_skip_agent_classify",
    "tracking_config",
    "build_element_scoped_session_context",
)
__all__ = list(PUBLIC_API)

CONTEXT_MODE_SESSION_ONLY = "session_only"
CONTEXT_MODE_BOUNDED_GLOBAL = "bounded_global"
CONTEXT_MODE_DEEP_GLOBAL = "deep_global"


def tracking_config(root: Path) -> Dict[str, Any]:
    from .bridge_controller import load_bridge_config

    bridge = load_bridge_config(root)
    tracking = dict(bridge.get("tracking", {}) or {})
    return {
        "require_active_session": bool(tracking.get("require_active_session", True)),
        "default_context_mode": str(tracking.get("default_context_mode", CONTEXT_MODE_SESSION_ONLY)),
        "max_turn_window": int(tracking.get("max_turn_window", 12) or 12),
        "retention": dict(tracking.get("retention", {}) or {}),
    }


def _dedupe_preserve_order(values: List[str]) -> List[str]:
    seen: set[str] = set()
    ordered: List[str] = []
    for value in values:
        clean = str(value or "").strip()
        if not clean or clean in seen:
            continue
        seen.add(clean)
        ordered.append(clean)
    return ordered


def _active_tracked_session(root: Path, session_id: str) -> Dict[str, Any] | None:
    session_key = str(session_id or "").strip()
    if not session_key:
        return None
    try:
        session = get_bridge_session(root, session_key)
    except ValueError:
        return None
    if str(session.get("status", "")).strip() != SESSION_STATUS_ACTIVE:
        return None
    return session


def resolve_context_retrieval_mode(
    root: Path,
    *,
    session_id: str,
    depth_mode: str,
    policy: Dict[str, Any] | None,
    caller_hints: Dict[str, Any] | None,
) -> str:
    hints = dict(caller_hints or {})
    explicit = str(hints.get("context_mode", "") or hints.get("retrieval_mode", "")).strip().lower()
    if explicit in {CONTEXT_MODE_SESSION_ONLY, CONTEXT_MODE_BOUNDED_GLOBAL, CONTEXT_MODE_DEEP_GLOBAL}:
        return explicit
    if hints.get("request_global") or hints.get("force_global_retrieval"):
        return CONTEXT_MODE_BOUNDED_GLOBAL

    normalized_depth = str(depth_mode or "focused").strip().lower()
    if normalized_depth == "incognito":
        return CONTEXT_MODE_SESSION_ONLY
    if normalized_depth == "deep":
        return CONTEXT_MODE_DEEP_GLOBAL
    if policy and bool(policy.get("cross_ocean")):
        return CONTEXT_MODE_DEEP_GLOBAL

    session = _active_tracked_session(root, session_id)
    if session and str(session.get("element_key", "") or "").strip() and normalized_depth == "focused":
        if not hints.get("request_global"):
            return CONTEXT_MODE_SESSION_ONLY

    config = tracking_config(root)
    if config["default_context_mode"] == CONTEXT_MODE_SESSION_ONLY and _active_tracked_session(root, session_id):
        if normalized_depth == "focused":
            return CONTEXT_MODE_SESSION_ONLY
        if normalized_depth == "contextual" and not hints.get("request_global"):
            return CONTEXT_MODE_SESSION_ONLY

    if normalized_depth == "contextual":
        return CONTEXT_MODE_BOUNDED_GLOBAL
    return CONTEXT_MODE_SESSION_ONLY


def should_skip_agent_classify(root: Path, request: Dict[str, Any]) -> bool:
    hints = dict(request.get("caller_hints", {}) or {})
    if hints.get("force_agent_classify"):
        return False
    if str(hints.get("classify_mode", "")).strip().lower() == "heuristic":
        return True

    session_id = str(request.get("session_id", "")).strip()
    depth_mode = str(hints.get("depth_mode", "") or "focused").strip().lower()
    policy = hints.get("context_policy") if isinstance(hints.get("context_policy"), dict) else None
    mode = resolve_context_retrieval_mode(
        root,
        session_id=session_id,
        depth_mode=depth_mode,
        policy=policy,
        caller_hints=hints,
    )
    return mode == CONTEXT_MODE_SESSION_ONLY and _active_tracked_session(root, session_id) is not None


def build_dynamic_session_context(
    root: Path,
    session_id: str,
    *,
    max_turns: int = 12,
) -> Dict[str, Any]:
    session_key = session_id.strip()
    if not session_key:
        raise ValueError("session_id is required")

    session = get_bridge_session(root, session_key)
    trace_rows = read_jsonl(session_trace_path(root, session_key))
    turn_rows = [row for row in trace_rows if row.get("type") == "turn"][-max(1, max_turns) :]

    topics: List[str] = []
    goals: List[str] = []
    postures: List[str] = []
    recent_turns: List[Dict[str, Any]] = []
    for row in turn_rows:
        packet = dict(row.get("control_packet", {}) or {})
        topic = str(packet.get("active_topic", "") or "").strip()
        goal = str(packet.get("user_goal", "") or "").strip()
        posture = str(packet.get("reasoning_posture", "") or "").strip()
        if topic:
            topics.append(topic)
        if goal:
            goals.append(goal)
        if posture:
            postures.append(posture)
        recent_turns.append(
            {
                "ledger_entry_id": row.get("ledger_entry_id", ""),
                "timestamp": row.get("timestamp", ""),
                "actor": row.get("actor", "user"),
                "raw_text": str(row.get("raw_text", "") or ""),
                "request_id": row.get("request_id", ""),
                "routing_source": row.get("routing_source", ""),
                "active_topic": topic,
                "user_goal": goal,
                "reasoning_posture": posture,
                "control_packet": packet,
            }
        )

    continuity_lines = [
        f"- [{turn['actor']}] {turn['raw_text'][:240]}"
        for turn in recent_turns[-6:]
        if str(turn.get("raw_text", "")).strip()
    ]
    continuity_markdown = ""
    if continuity_lines:
        continuity_markdown = "## Recent session turns\n" + "\n".join(continuity_lines)

    return {
        "session_id": session_key,
        "status": session.get("status", ""),
        "title": session.get("title", ""),
        "surface": session.get("surface", ""),
        "element_key": session.get("element_key", ""),
        "holodeck_id": session.get("holodeck_id", ""),
        "topology_mode": session.get("topology_mode", "spine"),
        "turn_count": int(session.get("turn_count", 0) or 0),
        "user_turn_count": int(session.get("user_turn_count", 0) or 0),
        "assistant_turn_count": int(session.get("assistant_turn_count", 0) or 0),
        "recent_turns": recent_turns,
        "topic_trail": _dedupe_preserve_order(topics),
        "goal_trail": _dedupe_preserve_order(goals),
        "posture_trail": _dedupe_preserve_order(postures),
        "latest_topic": topics[-1] if topics else "",
        "latest_goal": goals[-1] if goals else "",
        "latest_posture": postures[-1] if postures else "",
        "continuity_markdown": continuity_markdown,
        "context_mode": CONTEXT_MODE_SESSION_ONLY,
    }


def build_element_scoped_session_context(
    root: Path,
    session_id: str,
    *,
    max_turns: int = 12,
    element_key: str = "",
) -> Dict[str, Any]:
    base = build_dynamic_session_context(root, session_id, max_turns=max_turns)
    session_element = str(element_key or base.get("element_key", "") or "").strip()
    if not session_element:
        session = get_bridge_session(root, session_id.strip())
        session_element = str(session.get("element_key", "") or "").strip()
        holodeck_id = str(session.get("holodeck_id", "") or "")
        topology_mode = str(session.get("topology_mode", "spine") or "spine")
    else:
        session = get_bridge_session(root, session_id.strip())
        holodeck_id = str(session.get("holodeck_id", "") or "")
        topology_mode = str(session.get("topology_mode", "spine") or "spine")

    base["element_key"] = session_element
    base["holodeck_id"] = holodeck_id
    base["topology_mode"] = topology_mode

    if not session_element:
        base["element_context"] = {}
        return base

    from .element_capture import build_element_context_bundle, element_context_config

    element_bundle = build_element_context_bundle(
        root,
        element_key=session_element,
        holodeck_id=holodeck_id,
        config=element_context_config(root),
    )
    base["element_context"] = element_bundle
    element_markdown = str(element_bundle.get("element_context_markdown", "") or "").strip()
    if element_markdown:
        continuity = str(base.get("continuity_markdown", "") or "").strip()
        base["continuity_markdown"] = (continuity + "\n\n" + element_markdown).strip()
    return base


def session_rows_for_bundle(
    session_context: Dict[str, Any],
    *,
    max_events: int,
) -> List[Dict[str, Any]]:
    session_id = str(session_context.get("session_id", "")).strip()
    rows: List[Dict[str, Any]] = []
    for turn in list(session_context.get("recent_turns", []) or [])[-max(1, max_events) :]:
        rows.append(
            {
                "event_id": str(turn.get("ledger_entry_id", "") or make_id("event")),
                "session_id": session_id,
                "timestamp": turn.get("timestamp", ""),
                "actor": turn.get("actor", "user"),
                "kind": "turn",
                "content": turn.get("raw_text", ""),
                "attachments": [],
                "tags": ["bridge_tracking", "dynamic_session_context"],
                "source_ref": f"reasoning_runtime/turn_ledger.jsonl#{turn.get('ledger_entry_id', '')}",
                "metadata": {
                    "active_topic": turn.get("active_topic", ""),
                    "user_goal": turn.get("user_goal", ""),
                    "reasoning_posture": turn.get("reasoning_posture", ""),
                    "routing_source": turn.get("routing_source", ""),
                },
            }
        )
    return rows
