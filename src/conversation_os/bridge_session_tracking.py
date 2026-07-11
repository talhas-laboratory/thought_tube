from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from .analysis import update_manifest
from .bridge_prepare import (
    _append_turn_ledger,
    _sessions_dir,
    _turn_ledger_path,
    bridge_runtime_dir,
    load_bridge_session,
    save_bridge_session,
)
from .models import ConversationEvent, SessionManifest
from .reasoning_bridge import ensure_reasoning_runtime
from .storage import append_jsonl, ensure_dir, make_id, read_json, read_jsonl, session_dir, session_events_path, utc_now, write_json


MODULE_ID = "surface.bridge.bridge_session_tracking"
CONTRACT_VERSION = "1.0"
PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "SESSION_STATUS_ACTIVE",
    "SESSION_STATUS_ENDED",
    "sessions_index_path",
    "session_trace_path",
    "start_bridge_session",
    "end_bridge_session",
    "get_bridge_session",
    "list_bridge_sessions",
    "require_active_bridge_session",
    "append_bridge_turn",
    "record_assistant_turn",
    "record_bridge_session_event",
    "get_bridge_session_trace",
    "update_bridge_session_element",
)
__all__ = list(PUBLIC_API)

SESSION_STATUS_ACTIVE = "active"
SESSION_STATUS_ENDED = "ended"


def sessions_index_path(root: Path) -> Path:
    return bridge_runtime_dir(root) / "sessions_index.json"


def session_trace_path(root: Path, session_id: str) -> Path:
    return bridge_runtime_dir(root) / "session_traces" / f"{session_id}.jsonl"


def _load_sessions_index(root: Path) -> Dict[str, Any]:
    payload = read_json(sessions_index_path(root), default=None)
    if isinstance(payload, dict) and isinstance(payload.get("sessions"), dict):
        return payload
    return {"updated_at": utc_now(), "sessions": {}}


def _save_sessions_index(root: Path, index: Dict[str, Any]) -> None:
    ensure_reasoning_runtime(root)
    ensure_dir(bridge_runtime_dir(root))
    index["updated_at"] = utc_now()
    write_json(sessions_index_path(root), index)


def _upsert_sessions_index(root: Path, session: Dict[str, Any]) -> None:
    index = _load_sessions_index(root)
    sessions = index.setdefault("sessions", {})
    session_id = str(session.get("session_id", "")).strip()
    if not session_id:
        return
    sessions[session_id] = {
        "session_id": session_id,
        "status": session.get("status", SESSION_STATUS_ACTIVE),
        "surface": session.get("surface", ""),
        "workspace_id": session.get("workspace_id", ""),
        "title": session.get("title", ""),
        "created_at": session.get("created_at", ""),
        "updated_at": session.get("updated_at", ""),
        "ended_at": session.get("ended_at"),
        "turn_count": int(session.get("turn_count", 0) or 0),
        "user_turn_count": int(session.get("user_turn_count", 0) or 0),
        "assistant_turn_count": int(session.get("assistant_turn_count", 0) or 0),
        "element_key": session.get("element_key", ""),
        "holodeck_id": session.get("holodeck_id", ""),
        "topology_mode": session.get("topology_mode", ""),
    }
    _save_sessions_index(root, index)


def _default_bridge_session(session_id: str) -> Dict[str, Any]:
    now = utc_now()
    return {
        "session_id": session_id,
        "workspace_id": "",
        "surface": "",
        "title": "",
        "status": SESSION_STATUS_ACTIVE,
        "participants": ["user", "agent"],
        "source_type": "bridge_tracking",
        "created_at": now,
        "started_at": now,
        "ended_at": None,
        "updated_at": now,
        "turn_count": 0,
        "user_turn_count": 0,
        "assistant_turn_count": 0,
        "last_ledger_entry_id": "",
        "last_control_packet": {},
        "last_request_id": "",
        "trace_refs": {},
        "element_key": "",
        "element_keys_secondary": [],
        "topology_mode": "spine",
        "holodeck_id": "",
        "auto_promote_review": False,
    }


def record_bridge_session_event(
    root: Path,
    session_id: str,
    *,
    event_type: str,
    payload: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    ensure_reasoning_runtime(root)
    entry = {
        "type": event_type,
        "timestamp": utc_now(),
        "session_id": session_id,
        **(payload or {}),
    }
    append_jsonl(session_trace_path(root, session_id), entry)
    return entry


def start_bridge_session(
    root: Path,
    *,
    session_id: str,
    title: str = "",
    surface: str = "cursor",
    workspace_id: str = "",
    participants: List[str] | None = None,
    domains: List[str] | None = None,
    source_type: str = "bridge_tracking",
    restart: bool = False,
    element_key: str = "",
    element_keys_secondary: List[str] | None = None,
    topology_mode: str = "",
    holodeck_id: str = "",
    auto_promote_review: bool = False,
) -> Dict[str, Any]:
    session_key = session_id.strip()
    if not session_key:
        raise ValueError("session_id is required")

    existing = load_bridge_session(root, session_key)
    status = str(existing.get("status", "") or "").strip()
    if status == SESSION_STATUS_ACTIVE and not restart:
        raise ValueError(f"session_already_active:{session_key}")
    if status == SESSION_STATUS_ENDED and not restart:
        raise ValueError(f"session_already_ended:{session_key}; pass restart=true to reopen")

    from .element_routing import element_defaults_for_key

    element_defaults = element_defaults_for_key(root, element_key.strip()) if element_key.strip() else {}
    resolved_element_key = element_key.strip() or str(element_defaults.get("element_key", "") or "")
    resolved_holodeck_id = holodeck_id.strip() or str(element_defaults.get("holodeck_id", "") or "")
    resolved_topology = topology_mode.strip() or str(element_defaults.get("topology_mode", "spine") or "spine")
    if resolved_topology not in {"spine", "sidecar", "parallel"}:
        resolved_topology = "spine"

    now = utc_now()
    session = _default_bridge_session(session_key)
    session.update(
        {
            "workspace_id": workspace_id.strip(),
            "surface": surface.strip() or "cursor",
            "title": title.strip(),
            "participants": participants or ["user", "agent"],
            "source_type": source_type,
            "element_key": resolved_element_key,
            "element_keys_secondary": list(element_keys_secondary or []),
            "topology_mode": resolved_topology,
            "holodeck_id": resolved_holodeck_id,
            "auto_promote_review": bool(auto_promote_review),
            "started_at": now,
            "created_at": existing.get("created_at") or now,
            "turn_count": 0 if restart else int(existing.get("turn_count", 0) or 0),
            "user_turn_count": 0 if restart else int(existing.get("user_turn_count", 0) or 0),
            "assistant_turn_count": 0 if restart else int(existing.get("assistant_turn_count", 0) or 0),
            "trace_refs": {
                "events": str(session_events_path(root, session_key)),
                "turn_ledger": str(_turn_ledger_path(root)),
                "trace": str(session_trace_path(root, session_key)),
                "manifest": str(session_dir(root, session_key) / "manifest.json"),
            },
        }
    )
    save_bridge_session(root, session)
    _upsert_sessions_index(root, session)

    manifest = SessionManifest(
        session_id=session_key,
        title=title.strip() or f"Bridge session {session_key[:8]}",
        started_at=now,
        ended_at=None,
        participants=participants or ["user", "agent"],
        source_type=source_type,
        status=SESSION_STATUS_ACTIVE,
        artifact_refs=dict(session.get("trace_refs", {})),
        domains=domains or [],
    )
    ensure_dir(session_dir(root, session_key))
    update_manifest(root, manifest)
    ensure_dir(session_events_path(root, session_key).parent)
    session_events_path(root, session_key).touch(exist_ok=True)

    record_bridge_session_event(
        root,
        session_key,
        event_type="session_start",
        payload={
            "title": session["title"],
            "surface": session["surface"],
            "workspace_id": session["workspace_id"],
            "element_key": session.get("element_key", ""),
            "holodeck_id": session.get("holodeck_id", ""),
            "topology_mode": session.get("topology_mode", "spine"),
            "restart": restart,
        },
    )
    append_jsonl(
        session_events_path(root, session_key),
        ConversationEvent(
            event_id=make_id("event"),
            session_id=session_key,
            timestamp=now,
            actor="system",
            kind="session_start",
            content=title.strip() or "Bridge tracking session started",
            attachments=[],
            tags=["bridge_tracking", surface.strip() or "cursor"],
            source_ref=f"reasoning_runtime/session_traces/{session_key}.jsonl",
        ).to_dict(),
    )
    return session


def update_bridge_session_element(
    root: Path,
    session_id: str,
    *,
    element_key: str = "",
    element_keys_secondary: List[str] | None = None,
    topology_mode: str = "",
    holodeck_id: str = "",
    auto_promote_review: bool | None = None,
    source: str = "binding",
) -> Dict[str, Any]:
    session_key = session_id.strip()
    if not session_key:
        raise ValueError("session_id is required")

    session = require_active_bridge_session(root, session_key)
    changed = False
    updates: Dict[str, Any] = {}

    if element_key.strip() and element_key.strip() != str(session.get("element_key", "") or ""):
        updates["element_key"] = element_key.strip()
        changed = True
    if element_keys_secondary is not None:
        normalized = [str(value).strip() for value in element_keys_secondary if str(value).strip()]
        if normalized != list(session.get("element_keys_secondary", []) or []):
            updates["element_keys_secondary"] = normalized
            changed = True
    if topology_mode.strip() and topology_mode.strip() != str(session.get("topology_mode", "") or ""):
        updates["topology_mode"] = topology_mode.strip()
        changed = True
    if holodeck_id.strip() and holodeck_id.strip() != str(session.get("holodeck_id", "") or ""):
        updates["holodeck_id"] = holodeck_id.strip()
        changed = True
    if auto_promote_review is True and not bool(session.get("auto_promote_review")):
        updates["auto_promote_review"] = True
        changed = True

    if not changed:
        return session

    session.update(updates)
    save_bridge_session(root, session)
    _upsert_sessions_index(root, session)
    record_bridge_session_event(
        root,
        session_key,
        event_type="element_binding_updated",
        payload={
            "source": source.strip() or "binding",
            "element_key": session.get("element_key", ""),
            "element_keys_secondary": list(session.get("element_keys_secondary", []) or []),
            "topology_mode": session.get("topology_mode", "spine"),
            "holodeck_id": session.get("holodeck_id", ""),
            "auto_promote_review": bool(session.get("auto_promote_review")),
        },
    )
    return session


def end_bridge_session(
    root: Path,
    session_id: str,
    *,
    reason: str = "",
) -> Dict[str, Any]:
    session_key = session_id.strip()
    if not session_key:
        raise ValueError("session_id is required")

    session = load_bridge_session(root, session_key)
    status = str(session.get("status", SESSION_STATUS_ACTIVE) or SESSION_STATUS_ACTIVE)
    if status == SESSION_STATUS_ENDED:
        raise ValueError(f"session_already_ended:{session_key}")

    ended_at = utc_now()
    session["status"] = SESSION_STATUS_ENDED
    session["ended_at"] = ended_at
    save_bridge_session(root, session)
    _upsert_sessions_index(root, session)

    manifest_path = session_dir(root, session_key) / "manifest.json"
    manifest_payload = read_json(manifest_path, default=None)
    if isinstance(manifest_payload, dict):
        manifest = SessionManifest(**manifest_payload)
        manifest.ended_at = ended_at
        manifest.status = SESSION_STATUS_ENDED
        update_manifest(root, manifest)

    record_bridge_session_event(
        root,
        session_key,
        event_type="session_end",
        payload={
            "reason": reason.strip(),
            "turn_count": int(session.get("turn_count", 0) or 0),
            "user_turn_count": int(session.get("user_turn_count", 0) or 0),
            "assistant_turn_count": int(session.get("assistant_turn_count", 0) or 0),
        },
    )
    append_jsonl(
        session_events_path(root, session_key),
        ConversationEvent(
            event_id=make_id("event"),
            session_id=session_key,
            timestamp=ended_at,
            actor="system",
            kind="session_end",
            content=reason.strip() or "Bridge tracking session ended",
            attachments=[],
            tags=["bridge_tracking"],
            source_ref=f"reasoning_runtime/session_traces/{session_key}.jsonl",
        ).to_dict(),
    )
    return session


def get_bridge_session(root: Path, session_id: str) -> Dict[str, Any]:
    session_key = session_id.strip()
    if not session_key:
        raise ValueError("session_id is required")
    path = _sessions_dir(root) / f"{session_key}.json"
    if not path.exists():
        raise ValueError(
            f"session_not_found:{session_key}. Call bridge_start_session before recording turns."
        )
    return load_bridge_session(root, session_key)


def list_bridge_sessions(
    root: Path,
    *,
    status: str = "",
    limit: int = 50,
) -> Dict[str, Any]:
    index = _load_sessions_index(root)
    rows = list((index.get("sessions") or {}).values())
    if status.strip():
        rows = [row for row in rows if str(row.get("status", "")) == status.strip()]
    rows.sort(key=lambda row: str(row.get("updated_at", "")), reverse=True)
    bounded = max(1, min(int(limit), 200))
    selected = rows[:bounded]
    return {
        "count": len(selected),
        "total_available": len(rows),
        "status_filter": status.strip(),
        "sessions": selected,
    }


def require_active_bridge_session(root: Path, session_id: str) -> Dict[str, Any]:
    session = get_bridge_session(root, session_id)
    status = str(session.get("status", SESSION_STATUS_ACTIVE) or SESSION_STATUS_ACTIVE)
    if status != SESSION_STATUS_ACTIVE:
        raise ValueError(
            f"session_not_active:{session_id}; status={status}. "
            "Call bridge_start_session before recording turns."
        )
    return session


def append_bridge_turn(
    root: Path,
    *,
    session_id: str,
    workspace_id: str,
    surface: str,
    raw_text: str,
    actor: str,
    preview: Dict[str, Any],
    request_id: str,
    routing_source: str,
    kind: str = "turn",
) -> Dict[str, Any]:
    from .bridge_session_retention import (
        enforce_session_retention,
        retention_config,
        slim_control_packet,
        truncate_turn_text,
    )

    session = require_active_bridge_session(root, session_id)
    cfg = retention_config(root)
    bounded_text = truncate_turn_text(raw_text, actor=actor, config=cfg)
    stored_packet = slim_control_packet(preview) if cfg.get("slim_control_packets", True) else dict(preview or {})
    ledger_entry_id = make_id("bridge-turn")
    ledger_entry = {
        "ledger_entry_id": ledger_entry_id,
        "timestamp": utc_now(),
        "session_id": session_id,
        "workspace_id": workspace_id,
        "surface": surface,
        "actor": actor,
        "raw_text": bounded_text,
        "text_truncated": bounded_text != str(raw_text or ""),
        "request_id": request_id,
        "routing_source": routing_source,
        "control_packet": stored_packet,
    }
    _append_turn_ledger(root, ledger_entry)

    event = ConversationEvent(
        event_id=make_id("event"),
        session_id=session_id,
        timestamp=ledger_entry["timestamp"],
        actor=actor,
        kind=kind,
        content=bounded_text,
        attachments=[],
        tags=["bridge_tracking", surface, routing_source, actor],
        source_ref=f"reasoning_runtime/turn_ledger.jsonl#{ledger_entry_id}",
    )
    append_jsonl(session_events_path(root, session_id), event.to_dict())

    record_bridge_session_event(
        root,
        session_id,
        event_type="turn",
        payload={
            "ledger_entry_id": ledger_entry_id,
            "actor": actor,
            "request_id": request_id,
            "routing_source": routing_source,
            "raw_text": bounded_text,
            "text_truncated": bounded_text != str(raw_text or ""),
            "control_packet": stored_packet,
        },
    )

    session.update(
        {
            "workspace_id": workspace_id,
            "surface": surface,
            "turn_count": int(session.get("turn_count", 0) or 0) + 1,
            "last_ledger_entry_id": ledger_entry_id,
            "last_control_packet": stored_packet if actor == "assistant" else preview,
            "last_request_id": request_id,
        }
    )
    if actor == "user":
        session["user_turn_count"] = int(session.get("user_turn_count", 0) or 0) + 1
    elif actor == "assistant":
        session["assistant_turn_count"] = int(session.get("assistant_turn_count", 0) or 0) + 1
    save_bridge_session(root, session)
    _upsert_sessions_index(root, session)
    retention_result = enforce_session_retention(root, session_id)
    return {
        "ledger_entry_id": ledger_entry_id,
        "session": session,
        "event": event.to_dict(),
        "retention": retention_result,
    }


def record_assistant_turn(
    root: Path,
    *,
    session_id: str,
    response_text: str,
    workspace_id: str = "",
    surface: str = "cursor",
    request_id: str = "",
) -> Dict[str, Any]:
    from .bridge_session_retention import retention_config, slim_control_packet, truncate_turn_text

    session = require_active_bridge_session(root, session_id)
    bounded = truncate_turn_text(response_text, actor="assistant", config=retention_config(root))
    recent_turns = [
        row
        for row in read_jsonl(session_trace_path(root, session_id))
        if row.get("type") == "turn" and row.get("actor") == "assistant"
    ]
    if recent_turns and str(recent_turns[-1].get("raw_text", "")) == bounded:
        return {
            "skipped": "duplicate_assistant_turn",
            "session": session,
            "ledger_entry_id": recent_turns[-1].get("ledger_entry_id", ""),
        }

    last_packet = dict(session.get("last_control_packet", {}) or {})
    assistant_preview = {
        **slim_control_packet(last_packet),
        "request_id": request_id or str(session.get("last_request_id", "") or ""),
        "routing_source": "assistant_record",
    }
    return append_bridge_turn(
        root,
        session_id=session_id,
        workspace_id=workspace_id or str(session.get("workspace_id", "") or ""),
        surface=surface or str(session.get("surface", "") or "cursor"),
        raw_text=response_text,
        actor="assistant",
        preview=assistant_preview,
        request_id=str(assistant_preview.get("request_id", "") or ""),
        routing_source="assistant_record",
        kind="response",
    )


def get_bridge_session_trace(root: Path, session_id: str) -> Dict[str, Any]:
    session_key = session_id.strip()
    if not session_key:
        raise ValueError("session_id is required")

    session = get_bridge_session(root, session_key)
    trace_rows = read_jsonl(session_trace_path(root, session_key))
    event_rows = read_jsonl(session_events_path(root, session_key))
    ledger_rows = [
        {
            "ledger_entry_id": row.get("ledger_entry_id", ""),
            "timestamp": row.get("timestamp", ""),
            "session_id": session_key,
            "actor": row.get("actor", ""),
            "raw_text": row.get("raw_text", ""),
            "request_id": row.get("request_id", ""),
            "routing_source": row.get("routing_source", ""),
            "control_packet": row.get("control_packet", {}),
        }
        for row in trace_rows
        if row.get("type") == "turn"
    ]
    manifest_path = session_dir(root, session_key) / "manifest.json"
    manifest = read_json(manifest_path, default={})

    return {
        "session": session,
        "manifest": manifest,
        "trace": trace_rows,
        "events": event_rows,
        "turn_ledger": ledger_rows,
        "counts": {
            "trace_entries": len(trace_rows),
            "events": len(event_rows),
            "turn_ledger": len(ledger_rows),
            "user_turns": int(session.get("user_turn_count", 0) or 0),
            "assistant_turns": int(session.get("assistant_turn_count", 0) or 0),
        },
    }
