from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from .personal_interface import load_bridge_state
from .storage import append_jsonl, ensure_dir, read_jsonl, utc_now, write_json


MODULE_ID = "kernel.reasoning.reasoning_learning"
CONTRACT_VERSION = "1.0"
PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "load_learning_events",
    "record_learning_event",
    "persist_bridge_behavior_preferences",
)
__all__ = list(PUBLIC_API)


def _runtime_dir(root: Path) -> Path:
    return root / "product" / "inner_world_v1" / "data" / "reasoning_runtime"


def _learning_events_path(root: Path) -> Path:
    return _runtime_dir(root) / "reasoning_learning_events.jsonl"


def _bridge_state_path(root: Path) -> Path:
    return root / "product" / "personal_interface_v1" / "data" / "bridge_state.json"


def _merge_pattern_rows(existing_rows: List[Dict[str, Any]], incoming_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    index = {
        str(row.get("pattern_key", "")).strip(): dict(row)
        for row in existing_rows
        if isinstance(row, dict) and str(row.get("pattern_key", "")).strip()
    }
    for row in incoming_rows:
        pattern_key = str(row.get("pattern_key", "")).strip()
        if not pattern_key:
            continue
        existing = index.get(pattern_key)
        if existing is None:
            normalized = dict(row)
            normalized["count"] = int(normalized.get("count", 1) or 1)
            index[pattern_key] = normalized
            continue
        existing["count"] = int(existing.get("count", 1) or 1) + int(row.get("count", 1) or 1)
        existing["confidence"] = max(float(existing.get("confidence", 0.0) or 0.0), float(row.get("confidence", 0.0) or 0.0))
        existing["last_seen_at"] = row.get("last_seen_at", existing.get("last_seen_at", ""))
        existing_evidence = list(existing.get("evidence", []))
        for evidence in row.get("evidence", []) or []:
            if evidence not in existing_evidence:
                existing_evidence.append(evidence)
        existing["evidence"] = existing_evidence[:8]
        attributes = dict(existing.get("attributes", {}) or {})
        attributes.update(dict(row.get("attributes", {}) or {}))
        existing["attributes"] = attributes
    return sorted(index.values(), key=lambda row: (-int(row.get("count", 1) or 1), row.get("pattern_key", "")))


def _bridge_behavior_patterns_from_learning(
    learning_event: Dict[str, Any],
    *,
    context_state: Dict[str, Any] | None = None,
    result: Dict[str, Any] | None = None,
) -> List[Dict[str, Any]]:
    feedback_kind = str(learning_event.get("feedback_kind", "")).strip().lower()
    if feedback_kind not in {"accept", "reframe", "prefer", "confirm"}:
        return []

    explicit = [
        str(value).strip()
        for value in learning_event.get("attributes", {}).get("accepted_bridge_behaviors", []) or []
        if str(value).strip()
    ]
    active = [
        str(behavior.get("behavior_id", "")).strip()
        for behavior in (context_state or {}).get("bridge_behaviors", []) or []
        if str(behavior.get("behavior_id", "")).strip()
    ]
    behavior_ids = explicit or active
    if not behavior_ids:
        return []

    evidence = list(learning_event.get("evidence_refs", []) or [])
    if result and result.get("pipeline_id"):
        evidence.append(f"pipeline:{result['pipeline_id']}")
    seen_at = str(learning_event.get("timestamp", "")).strip() or utc_now()
    rows: List[Dict[str, Any]] = []
    for behavior_id in behavior_ids:
        rows.append(
            {
                "pattern_key": f"bridge_behavior:{behavior_id}",
                "label": f"Prefers {behavior_id.replace('_', ' ')} bridge behavior",
                "confidence": 0.86 if feedback_kind in {"accept", "confirm"} else 0.78,
                "evidence": evidence[:4],
                "count": 1,
                "last_seen_at": seen_at,
                "attributes": {
                    "origin": "reasoning_learning",
                    "feedback_kind": feedback_kind,
                    "request_id": learning_event.get("request_id", ""),
                    "result_id": learning_event.get("result_id", ""),
                },
            }
        )
    return rows


def load_learning_events(root: Path) -> List[Dict[str, Any]]:
    ensure_dir(_runtime_dir(root))
    return read_jsonl(_learning_events_path(root))


def record_learning_event(root: Path, event: Dict[str, Any]) -> Dict[str, Any]:
    ensure_dir(_runtime_dir(root))
    append_jsonl(_learning_events_path(root), event)
    return event


def persist_bridge_behavior_preferences(
    root: Path,
    learning_event: Dict[str, Any],
    *,
    context_state: Dict[str, Any] | None = None,
    result: Dict[str, Any] | None = None,
) -> List[Dict[str, Any]]:
    incoming = _bridge_behavior_patterns_from_learning(learning_event, context_state=context_state, result=result)
    if not incoming:
        return []
    state = load_bridge_state(root)
    merged = _merge_pattern_rows(list(state.get("behavior_patterns", []) or []), incoming)
    state["behavior_patterns"] = merged
    state["updated_at"] = str(learning_event.get("timestamp", "")).strip() or utc_now()
    ensure_dir(_bridge_state_path(root).parent)
    write_json(_bridge_state_path(root), state)
    return incoming
