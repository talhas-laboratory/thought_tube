from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from .bridge_prepare import _turn_ledger_path, bridge_runtime_dir
from .bridge_session_tracking import session_trace_path
from .storage import append_jsonl, read_jsonl, utc_now, write_jsonl


MODULE_ID = "surface.bridge.bridge_session_retention"
CONTRACT_VERSION = "1.0"
PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "DEFAULT_RETENTION",
    "retention_config",
    "slim_control_packet",
    "truncate_turn_text",
    "trim_turn_ledger",
    "compact_session_trace",
    "compact_session_events",
    "enforce_session_retention",
)
__all__ = list(PUBLIC_API)

DEFAULT_RETENTION = {
    "max_turn_window": 12,
    "max_stored_turns": 200,
    "max_user_text_chars": 12000,
    "max_assistant_text_chars": 16000,
    "compact_after_turns": 150,
    "ledger_tail_entries": 5000,
    "max_events_per_session": 400,
    "slim_control_packets": True,
}

SLIM_PACKET_KEYS = (
    "request_id",
    "routing_source",
    "active_topic",
    "user_goal",
    "reasoning_posture",
    "depth_mode",
    "object_scope",
    "pipeline_id",
    "control_packet_id",
    "bridge_behavior_ids",
)


def retention_config(root: Path) -> Dict[str, Any]:
    from .bridge_session_context import tracking_config

    tracking = tracking_config(root)
    retention = dict(tracking.get("retention", {}) or {})
    resolved = dict(DEFAULT_RETENTION)
    resolved.update({key: value for key, value in retention.items() if key in DEFAULT_RETENTION})
    resolved["max_turn_window"] = int(tracking.get("max_turn_window", resolved["max_turn_window"]) or 12)
    return resolved


def slim_control_packet(packet: Dict[str, Any] | None) -> Dict[str, Any]:
    source = dict(packet or {})
    slim = {key: source[key] for key in SLIM_PACKET_KEYS if key in source and source[key] not in (None, "", [], {})}
    if source.get("context_policy"):
        policy = dict(source["context_policy"])
        slim["context_policy"] = {
            key: policy[key]
            for key in ("mode", "depth_mode", "token_budget", "cross_ocean")
            if key in policy
        }
    return slim


def truncate_turn_text(text: str, *, actor: str, config: Dict[str, Any] | None = None) -> str:
    cfg = dict(config or DEFAULT_RETENTION)
    limit = int(
        cfg["max_assistant_text_chars"]
        if actor == "assistant"
        else cfg["max_user_text_chars"]
    )
    clean = str(text or "")
    if len(clean) <= limit:
        return clean
    return clean[: max(0, limit - 24)] + "\n...[truncated]"


def _archive_rows(path: Path, rows: List[Dict[str, Any]]) -> str:
    archive_path = path.with_suffix(".archive.jsonl")
    existing = read_jsonl(archive_path)
    payload = existing + [{"type": "archive_marker", "timestamp": utc_now(), "count": len(rows)}] + rows
    write_jsonl(archive_path, payload)
    return str(archive_path)


def trim_turn_ledger(root: Path, *, max_entries: int) -> Dict[str, Any]:
    path = _turn_ledger_path(root)
    rows = read_jsonl(path)
    bounded = max(100, int(max_entries))
    if len(rows) <= bounded:
        return {"trimmed": 0, "remaining": len(rows)}
    archive_rows = rows[:-bounded]
    archive_path = path.with_name(f"turn_ledger.archive.{utc_now().replace(':', '-')}.jsonl")
    write_jsonl(archive_path, archive_rows)
    write_jsonl(path, rows[-bounded:])
    return {"trimmed": len(archive_rows), "remaining": bounded, "archive_path": str(archive_path)}


def compact_session_trace(root: Path, session_id: str, *, keep_turns: int) -> Dict[str, Any]:
    path = session_trace_path(root, session_id)
    rows = read_jsonl(path)
    if not rows:
        return {"compacted": 0, "remaining": 0}

    preserved: List[Dict[str, Any]] = []
    turn_rows: List[Dict[str, Any]] = []
    for row in rows:
        if row.get("type") != "turn":
            preserved.append(row)
        else:
            turn_rows.append(row)

    bounded = max(1, int(keep_turns))
    if len(turn_rows) <= bounded:
        return {"compacted": 0, "remaining": len(rows)}

    archived_turns = turn_rows[:-bounded]
    kept_turns = turn_rows[-bounded:]
    archive_path = _archive_rows(path, archived_turns)
    write_jsonl(path, preserved + kept_turns)
    return {
        "compacted": len(archived_turns),
        "remaining": len(preserved) + len(kept_turns),
        "archive_path": archive_path,
    }


def compact_session_events(root: Path, session_id: str, *, max_events: int) -> Dict[str, Any]:
    from .storage import session_events_path

    path = session_events_path(root, session_id)
    rows = read_jsonl(path)
    bounded = max(40, int(max_events))
    if len(rows) <= bounded:
        return {"compacted": 0, "remaining": len(rows)}
    archived = rows[:-bounded]
    archive_path = _archive_rows(path, archived)
    write_jsonl(path, rows[-bounded:])
    return {
        "compacted": len(archived),
        "remaining": bounded,
        "archive_path": archive_path,
    }


def enforce_session_retention(root: Path, session_id: str) -> Dict[str, Any]:
    cfg = retention_config(root)
    session_key = session_id.strip()
    if not session_key:
        return {"ok": False, "reason": "missing_session_id"}

    turn_count = 0
    try:
        trace_rows = read_jsonl(session_trace_path(root, session_key))
        turn_count = sum(1 for row in trace_rows if row.get("type") == "turn")
    except OSError:
        trace_rows = []

    result: Dict[str, Any] = {"session_id": session_key, "turn_count": turn_count}
    if turn_count >= int(cfg["compact_after_turns"]):
        result["trace"] = compact_session_trace(
            root,
            session_key,
            keep_turns=int(cfg["max_stored_turns"]),
        )
        result["events"] = compact_session_events(
            root,
            session_key,
            max_events=int(cfg["max_events_per_session"]),
        )
    result["ledger"] = trim_turn_ledger(root, max_entries=int(cfg["ledger_tail_entries"]))
    result["ok"] = True
    return result
