from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List

from .runtime_layout import product_runtime_dir
from .storage import append_jsonl, ensure_dir, make_id, read_json, read_jsonl, utc_now, workspace_manifest_path


MODULE_ID = "surface.bridge.element_capture"
CONTRACT_VERSION = "1.0"
CAPTURE_STATUS_PROVISIONAL = "provisional"
CAPTURE_STATUS_PROMOTED = "promoted"
CAPTURE_STATUS_REJECTED = "rejected"
PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "CAPTURE_STATUS_PROVISIONAL",
    "CAPTURE_STATUS_PROMOTED",
    "CAPTURE_STATUS_REJECTED",
    "element_captures_dir",
    "element_context_config",
    "should_capture_turn",
    "append_element_capture",
    "list_element_captures",
    "list_promoted_element_records",
    "promote_element_capture",
    "reject_element_capture",
    "maybe_capture_from_turn",
    "build_element_context_bundle",
)
__all__ = list(PUBLIC_API)

_LOW_SIGNAL_RE = re.compile(
    r"^(ok|okay|thanks|thank you|yes|no|sure|done|continue|go ahead|sounds good)[\s.!]*$",
    re.IGNORECASE,
)
_CAPTURE_GOALS = frozenset({"build", "evaluate", "decide", "record", "capture"})


def element_captures_dir(root: Path) -> Path:
    return product_runtime_dir(root, "inner_world_v1", "data") / "element_captures"


def provisional_capture_path(root: Path, element_key: str) -> Path:
    return element_captures_dir(root) / f"{element_key.strip()}.jsonl"


def promoted_capture_path(root: Path, element_key: str) -> Path:
    return element_captures_dir(root) / "promoted" / f"{element_key.strip()}.jsonl"


def element_context_config(root: Path) -> Dict[str, Any]:
    from .bridge_controller import load_bridge_config

    bridge = load_bridge_config(root)
    tracking = dict(bridge.get("tracking", {}) or {})
    defaults = {
        "max_provisional_captures": 5,
        "max_promoted_records": 8,
        "allow_cross_element": False,
        "min_capture_chars": 40,
        "min_capture_confidence": 0.6,
    }
    configured = dict(tracking.get("element_context", {}) or {})
    defaults.update({key: configured[key] for key in defaults if key in configured})
    return defaults


def _preview_text(value: str, limit: int = 220) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "…"


def _heuristic_thesis(raw_text: str) -> str:
    text = " ".join(str(raw_text or "").split())
    if not text:
        return ""
    for part in re.split(r"(?<=[.!?])\s+", text):
        clean = part.strip()
        if len(clean) >= 12:
            return _preview_text(clean, 160)
    return _preview_text(text, 160)


def should_capture_turn(
    *,
    raw_text: str,
    preview: Dict[str, Any],
    binding: Dict[str, Any],
    config: Dict[str, Any] | None = None,
) -> tuple[bool, str, float]:
    cfg = dict(config or {})
    min_chars = int(cfg.get("min_capture_chars", 40) or 40)
    min_confidence = float(cfg.get("min_capture_confidence", 0.6) or 0.6)
    text = str(raw_text or "").strip()
    if not text or _LOW_SIGNAL_RE.match(text):
        return False, "none", 0.0

    element_key = str(binding.get("element_key", "") or preview.get("element_key", "") or "").strip()
    if not element_key:
        return False, "none", 0.0

    if binding.get("request_ingest"):
        return True, "ingest", 1.0
    if binding.get("request_promote"):
        return True, "promote", 1.0

    confidence = float(binding.get("element_confidence", 0.0) or preview.get("element_confidence", 0.0) or 0.0)
    user_goal = str(preview.get("user_goal", "") or "").strip().lower()
    if len(text) >= min_chars and confidence >= min_confidence and user_goal in _CAPTURE_GOALS:
        return True, "goal", confidence

    lowered = text.lower()
    if len(text) >= min_chars and any(token in lowered for token in ("decide", "decision", "record this", "capture this")):
        return True, "explicit_language", max(confidence, 0.72)

    return False, "none", 0.0


def append_element_capture(
    root: Path,
    *,
    element_key: str,
    raw_text: str,
    session_id: str = "",
    source_kind: str = "session_turn",
    source_ref: str = "",
    element_keys_secondary: List[str] | None = None,
    thesis: str = "",
    confidence: float = 0.0,
    method: str = "heuristic",
    capture_trigger: str = "none",
    topology_mode: str = "spine",
    holodeck_id: str = "",
    status: str = CAPTURE_STATUS_PROVISIONAL,
) -> Dict[str, Any]:
    key = str(element_key or "").strip()
    if not key:
        raise ValueError("element_key is required")

    capture = {
        "capture_id": make_id("element-capture"),
        "element_key": key,
        "element_keys_secondary": list(element_keys_secondary or []),
        "status": status,
        "source_kind": source_kind,
        "source_ref": source_ref,
        "session_id": session_id,
        "raw_text": str(raw_text or "").strip(),
        "thesis": thesis.strip() or _heuristic_thesis(raw_text),
        "confidence": round(float(confidence or 0.0), 2),
        "method": method,
        "capture_trigger": capture_trigger,
        "topology_mode": topology_mode or "spine",
        "holodeck_id": holodeck_id,
        "created_at": utc_now(),
        "updated_at": utc_now(),
    }
    path = provisional_capture_path(root, key)
    ensure_dir(path.parent)
    append_jsonl(path, capture)
    return capture


def list_element_captures(
    root: Path,
    element_key: str,
    *,
    status: str = CAPTURE_STATUS_PROVISIONAL,
    session_id: str = "",
    limit: int = 50,
) -> Dict[str, Any]:
    key = str(element_key or "").strip()
    if not key:
        raise ValueError("element_key is required")

    rows = read_jsonl(provisional_capture_path(root, key))
    if status.strip():
        rows = [row for row in rows if str(row.get("status", "")) == status.strip()]
    if session_id.strip():
        rows = [row for row in rows if str(row.get("session_id", "")) == session_id.strip()]
    rows.sort(key=lambda row: str(row.get("created_at", "")), reverse=True)
    bounded = max(1, min(int(limit), 200))
    selected = rows[:bounded]
    return {
        "element_key": key,
        "status_filter": status.strip(),
        "session_id_filter": session_id.strip(),
        "count": len(selected),
        "total_available": len(rows),
        "captures": selected,
    }


def list_promoted_element_records(
    root: Path,
    element_key: str,
    *,
    limit: int = 50,
) -> Dict[str, Any]:
    key = str(element_key or "").strip()
    if not key:
        raise ValueError("element_key is required")
    rows = read_jsonl(promoted_capture_path(root, key))
    rows.sort(key=lambda row: str(row.get("promoted_at", row.get("created_at", ""))), reverse=True)
    bounded = max(1, min(int(limit), 200))
    selected = rows[:bounded]
    return {
        "element_key": key,
        "count": len(selected),
        "total_available": len(rows),
        "records": selected,
    }


def _rewrite_capture_rows(root: Path, element_key: str, rows: List[Dict[str, Any]]) -> None:
    path = provisional_capture_path(root, element_key)
    ensure_dir(path.parent)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def promote_element_capture(
    root: Path,
    *,
    element_key: str,
    capture_id: str,
    reason: str = "",
    confidence: float | None = None,
) -> Dict[str, Any]:
    key = str(element_key or "").strip()
    capture_key = str(capture_id or "").strip()
    if not key or not capture_key:
        raise ValueError("element_key and capture_id are required")

    rows = read_jsonl(provisional_capture_path(root, key))
    target = None
    for row in rows:
        if str(row.get("capture_id", "")) == capture_key:
            target = dict(row)
            break
    if target is None:
        raise ValueError(f"capture_not_found:{capture_key}")

    now = utc_now()
    target["status"] = CAPTURE_STATUS_PROMOTED
    target["updated_at"] = now
    target["promoted_at"] = now
    target["promotion_reason"] = reason.strip() or "manual_promotion"
    if confidence is not None:
        target["promotion_confidence"] = round(float(confidence), 2)

    updated_rows = []
    for row in rows:
        if str(row.get("capture_id", "")) == capture_key:
            updated_rows.append(target)
        else:
            updated_rows.append(row)
    _rewrite_capture_rows(root, key, updated_rows)

    promotion = {
        "promotion_id": make_id("element-promotion"),
        "capture_id": capture_key,
        "element_key": key,
        "thesis": target.get("thesis", ""),
        "reason": target.get("promotion_reason", ""),
        "confidence": target.get("promotion_confidence", target.get("confidence", 0.0)),
        "rollback_path": f"element_captures/{key}.jsonl#{capture_key}",
        "source_ref": target.get("source_ref", ""),
        "session_id": target.get("session_id", ""),
        "promoted_at": now,
    }
    promoted_path = promoted_capture_path(root, key)
    ensure_dir(promoted_path.parent)
    append_jsonl(promoted_path, promotion)
    return {"capture": target, "promotion": promotion}


def reject_element_capture(
    root: Path,
    *,
    element_key: str,
    capture_id: str,
    reason: str = "",
) -> Dict[str, Any]:
    key = str(element_key or "").strip()
    capture_key = str(capture_id or "").strip()
    if not key or not capture_key:
        raise ValueError("element_key and capture_id are required")

    rows = read_jsonl(provisional_capture_path(root, key))
    target = None
    for row in rows:
        if str(row.get("capture_id", "")) == capture_key:
            target = dict(row)
            break
    if target is None:
        raise ValueError(f"capture_not_found:{capture_key}")

    target["status"] = CAPTURE_STATUS_REJECTED
    target["updated_at"] = utc_now()
    target["rejection_reason"] = reason.strip() or "manual_rejection"

    updated_rows = []
    for row in rows:
        if str(row.get("capture_id", "")) == capture_key:
            updated_rows.append(target)
        else:
            updated_rows.append(row)
    _rewrite_capture_rows(root, key, updated_rows)
    return target


def maybe_capture_from_turn(
    root: Path,
    *,
    raw_text: str,
    preview: Dict[str, Any],
    binding: Dict[str, Any],
    session_id: str,
    ledger_entry_id: str,
) -> Dict[str, Any] | None:
    cfg = element_context_config(root)
    should_capture, trigger, confidence = should_capture_turn(
        raw_text=raw_text,
        preview=preview,
        binding=binding,
        config=cfg,
    )
    if not should_capture:
        return None

    element_key = str(binding.get("element_key", "") or preview.get("element_key", "") or "").strip()
    if not element_key:
        return None

    return append_element_capture(
        root,
        element_key=element_key,
        raw_text=raw_text,
        session_id=session_id,
        source_kind="session_turn",
        source_ref=f"reasoning_runtime/turn_ledger.jsonl#{ledger_entry_id}",
        element_keys_secondary=list(binding.get("element_keys_secondary", []) or []),
        confidence=confidence,
        method=str(binding.get("element_method", "") or "heuristic"),
        capture_trigger=trigger,
        topology_mode=str(binding.get("topology_mode", "spine") or "spine"),
        holodeck_id=str(binding.get("holodeck_id", "") or ""),
    )


def build_element_context_bundle(
    root: Path,
    *,
    element_key: str,
    holodeck_id: str = "",
    config: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    key = str(element_key or "").strip()
    if not key:
        return {}

    cfg = dict(config or element_context_config(root))
    provisional = list_element_captures(
        root,
        key,
        status=CAPTURE_STATUS_PROVISIONAL,
        limit=int(cfg.get("max_provisional_captures", 5) or 5),
    ).get("captures", [])
    promoted = list_promoted_element_records(
        root,
        key,
        limit=int(cfg.get("max_promoted_records", 8) or 8),
    ).get("records", [])

    holodeck_summary: Dict[str, Any] = {}
    workspace_id = str(holodeck_id or "").strip()
    if workspace_id:
        manifest = read_json(workspace_manifest_path(root, workspace_id), default=None)
        if isinstance(manifest, dict):
            holodeck_summary = {
                "workspace_id": workspace_id,
                "label": manifest.get("label", workspace_id),
                "status": manifest.get("status", ""),
                "goal": manifest.get("goal", ""),
                "purpose": manifest.get("purpose", ""),
                "scope_in": list(manifest.get("scope_in", []) or []),
                "scope_out": list(manifest.get("scope_out", []) or []),
                "workboard_ref": manifest.get("workboard_ref", ""),
                "pillars_ref": manifest.get("pillars_ref", ""),
                "active_subproject_id": manifest.get("active_subproject_id", ""),
            }

    from .element_workspace_binding import build_workspace_binding_bundle

    workspace_binding = build_workspace_binding_bundle(
        root,
        element_key=key,
        holodeck_id=workspace_id,
        subproject_id=str(holodeck_summary.get("active_subproject_id", "") or ""),
    )

    capture_lines = [
        f"- [{row.get('capture_trigger', '')}] {_preview_text(row.get('thesis', '') or row.get('raw_text', ''), 120)}"
        for row in provisional
        if str(row.get("thesis", "") or row.get("raw_text", "")).strip()
    ]
    promoted_lines = [
        f"- {_preview_text(row.get('thesis', ''), 120)}"
        for row in promoted
        if str(row.get("thesis", "")).strip()
    ]

    markdown_parts: List[str] = []
    if holodeck_summary:
        markdown_parts.append(
            "## Element Holodeck\n"
            f"- workspace: `{holodeck_summary.get('workspace_id', '')}`\n"
            f"- goal: {holodeck_summary.get('goal', '')}"
        )
    if capture_lines:
        markdown_parts.append("## Provisional element captures\n" + "\n".join(capture_lines))
    if promoted_lines:
        markdown_parts.append("## Promoted element records\n" + "\n".join(promoted_lines))
    binding_markdown = str(workspace_binding.get("workspace_binding_markdown", "") or "").strip()
    if binding_markdown:
        markdown_parts.append(binding_markdown)

    return {
        "element_key": key,
        "holodeck": holodeck_summary,
        "provisional_captures": provisional,
        "promoted_records": promoted,
        "workspace_binding": workspace_binding,
        "element_context_markdown": "\n\n".join(markdown_parts),
    }
