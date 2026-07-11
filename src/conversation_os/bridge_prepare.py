from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from .bridge_controller import load_bridge_config
from .models import ReasoningRequest
from .reasoning_bridge import ensure_reasoning_runtime, heuristic_classify_turn
from .runtime_layout import product_runtime_dir
from .storage import append_jsonl, ensure_dir, make_id, read_json, session_events_path, utc_now, write_json


MODULE_ID = "surface.bridge.bridge_prepare"
CONTRACT_VERSION = "1.0"
PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "build_reasoning_request_payload",
    "summarize_classify_preview",
    "bridge_runtime_dir",
    "thought_tube_dir",
    "resolve_session_id",
    "load_bridge_session",
    "save_bridge_session",
    "render_steering_markdown",
    "write_latest_steering_file",
    "prepare_turn",
)
__all__ = list(PUBLIC_API)

_SUPPORTED_SURFACES = {
    "cursor",
    "codex",
    "claude_code",
    "mcp",
    "hook",
    "cli",
    "thought_chat",
    "reasoning",
}


def build_reasoning_request_payload(
    *,
    raw_text: str,
    request_id: str = "",
    session_id: str = "",
    surface: str = "mcp",
    domain_hints: List[str] | None = None,
    caller_hints: Dict[str, Any] | None = None,
    source_refs: List[str] | None = None,
) -> Dict[str, Any]:
    text = raw_text.strip()
    if not text:
        raise ValueError("raw_text is required")
    return ReasoningRequest(
        request_id=request_id.strip() or make_id("reasoning-request"),
        session_id=session_id.strip(),
        surface=surface.strip() or "mcp",
        raw_text=text,
        source_refs=[str(value) for value in (source_refs or []) if str(value).strip()],
        timestamp=utc_now(),
        domain_hints=[str(value) for value in (domain_hints or []) if str(value).strip()],
        caller_hints=dict(caller_hints or {}),
    ).to_dict()


def summarize_classify_preview(context_state: Dict[str, Any]) -> Dict[str, Any]:
    attributes = dict(context_state.get("attributes", {}) or {})
    metadata = dict(attributes.get("control_packet_metadata", {}) or {})
    preview = {
        "request_id": context_state.get("request_id", ""),
        "routing_source": attributes.get("routing_source", "heuristic"),
        "active_topic": context_state.get("active_topic", ""),
        "user_goal": context_state.get("user_goal", ""),
        "reasoning_posture": context_state.get("reasoning_posture", ""),
        "depth_mode": context_state.get("depth_mode", ""),
        "object_scope": context_state.get("object_scope", ""),
        "pipeline_id": attributes.get("pipeline_id", ""),
        "control_packet_id": attributes.get("control_packet_id", ""),
        "bridge_behavior_ids": list(attributes.get("bridge_behavior_ids", []) or []),
        "context_policy": dict(attributes.get("context_policy", {}) or {}),
        "steering_constraints": list(attributes.get("steering_constraints", []) or []),
        "validation_warnings": list(metadata.get("validation_warnings", []) or []),
        "fallback_reason": str(metadata.get("fallback_reason", "") or ""),
    }
    binding = dict(attributes.get("element_binding", {}) or {})
    if binding:
        preview.update(
            {
                "element_key": binding.get("element_key", ""),
                "element_keys_secondary": list(binding.get("element_keys_secondary", []) or []),
                "topology_mode": binding.get("topology_mode", ""),
                "holodeck_id": binding.get("holodeck_id", ""),
                "element_method": binding.get("element_method", ""),
                "element_confidence": binding.get("element_confidence", 0.0),
                "element_label": binding.get("element_label", ""),
            }
        )
    return preview


def bridge_runtime_dir(root: Path) -> Path:
    return product_runtime_dir(root, "inner_world_v1", "data") / "reasoning_runtime"


def thought_tube_dir(root: Path) -> Path:
    return root / ".thought-tube"


def _sessions_dir(root: Path) -> Path:
    return bridge_runtime_dir(root) / "sessions"


def _turn_ledger_path(root: Path) -> Path:
    return bridge_runtime_dir(root) / "turn_ledger.jsonl"


def _default_workspace_id(root: Path, workspace_id: str = "") -> str:
    explicit = workspace_id.strip()
    if explicit:
        return explicit
    return root.resolve().name or "workspace"


def resolve_session_id(
    root: Path,
    *,
    session_id: str = "",
    workspace_id: str = "",
    surface: str = "mcp",
) -> str:
    explicit = session_id.strip()
    if explicit:
        return explicit
    workspace = _default_workspace_id(root, workspace_id)
    normalized_surface = surface.strip().lower() or "mcp"
    return make_id(f"bridge-session-{workspace}-{normalized_surface}")


def load_bridge_session(root: Path, session_id: str) -> Dict[str, Any]:
    path = _sessions_dir(root) / f"{session_id}.json"
    payload = read_json(path, default=None)
    if isinstance(payload, dict):
        return payload
    return {
        "session_id": session_id,
        "workspace_id": "",
        "surface": "",
        "created_at": utc_now(),
        "updated_at": utc_now(),
        "turn_count": 0,
        "last_ledger_entry_id": "",
        "last_control_packet": {},
    }


def save_bridge_session(root: Path, session: Dict[str, Any]) -> Dict[str, Any]:
    ensure_reasoning_runtime(root)
    ensure_dir(_sessions_dir(root))
    session_id = str(session.get("session_id", "")).strip()
    if not session_id:
        raise ValueError("session_id is required")
    session["updated_at"] = utc_now()
    write_json(_sessions_dir(root) / f"{session_id}.json", session)
    return session


def _append_turn_ledger(root: Path, entry: Dict[str, Any]) -> Dict[str, Any]:
    ensure_reasoning_runtime(root)
    ensure_dir(bridge_runtime_dir(root))
    append_jsonl(_turn_ledger_path(root), entry)
    return entry


def render_steering_markdown(
    preview: Dict[str, Any],
    *,
    session_id: str,
    surface: str,
    bridge_config: Dict[str, Any] | None = None,
) -> str:
    config = dict(bridge_config or {})
    policy = dict(preview.get("context_policy", {}) or {})
    constraints = list(preview.get("steering_constraints", []) or [])
    behaviors = list(preview.get("bridge_behavior_ids", []) or [])
    warnings = list(preview.get("validation_warnings", []) or [])
    lines = [
        "# Thought Tube bridge steering",
        "",
        "Treat this block as binding control-plane guidance for the current turn.",
        "",
        f"- session_id: `{session_id}`",
        f"- surface: `{surface}`",
        f"- routing_source: `{preview.get('routing_source', 'heuristic')}`",
        f"- bridge_enabled: `{bool(config.get('enabled', False))}`",
        "",
        "## Turn framing",
        f"- active_topic: {preview.get('active_topic', '')}",
        f"- user_goal: {preview.get('user_goal', '')}",
        f"- reasoning_posture: {preview.get('reasoning_posture', '')}",
        f"- depth_mode: {preview.get('depth_mode', '')}",
        f"- object_scope: {preview.get('object_scope', '')}",
        f"- pipeline_id: {preview.get('pipeline_id', '')}",
        "",
    ]
    element_key = str(preview.get("element_key", "") or "").strip()
    if element_key:
        lines.extend(
            [
                "## Product element",
                f"- element_key: `{element_key}`",
                f"- element_label: {preview.get('element_label', '')}",
                f"- topology_mode: {preview.get('topology_mode', 'spine')}",
                f"- holodeck_id: `{preview.get('holodeck_id', '')}`",
                f"- element_method: {preview.get('element_method', '')}",
                f"- element_confidence: {preview.get('element_confidence', '')}",
                "",
            ]
        )
        workspace_binding = dict(preview.get("workspace_binding", {}) or {})
        if workspace_binding:
            lines.extend(
                [
                    "## Active workspace scope",
                    f"- primary_artifact_root: `{workspace_binding.get('primary_artifact_root', '')}`",
                    f"- subproject_id: `{workspace_binding.get('subproject_id', '')}`",
                ]
            )
            roots = list(workspace_binding.get("artifact_roots", []) or [])
            if roots:
                lines.append(f"- artifact_roots: {', '.join(f'`{item}`' for item in roots[:6])}")
            lines.append("")
        secondary = list(preview.get("element_keys_secondary", []) or [])
        if secondary:
            lines.append(f"- element_keys_secondary: {', '.join(secondary)}")
            lines.append("")
    lines.extend(
        [
            "## Context policy",
            f"- mode: {policy.get('mode', '')}",
            f"- depth_mode: {policy.get('depth_mode', '')}",
            f"- token_budget: {policy.get('token_budget', '')}",
            f"- include_layers: {', '.join(policy.get('include_layers', []) or [])}",
            f"- exclude_layers: {', '.join(policy.get('exclude_layers', []) or [])}",
            f"- cross_ocean: {policy.get('cross_ocean', False)}",
            f"- retrieval_limit: {policy.get('retrieval_limit', '')}",
            f"- neighbor_limit: {policy.get('neighbor_limit', '')}",
            "",
            "## Bridge behaviors",
        ]
    )
    if behaviors:
        lines.extend(f"- {behavior_id}" for behavior_id in behaviors)
    else:
        lines.append("- (none)")
    lines.extend(["", "## Steering constraints"])
    if constraints:
        lines.extend(f"- {constraint}" for constraint in constraints)
    else:
        lines.append("- honor context policy budgets")
        lines.append("- do not request full corpus dumps")
        lines.append("- preserve provenance for imported material")
    if warnings:
        lines.extend(["", "## Validation warnings"])
        lines.extend(f"- {warning}" for warning in warnings)
    fallback_reason = str(preview.get("fallback_reason", "") or "").strip()
    if fallback_reason:
        lines.extend(["", "## Fallback", f"- {fallback_reason}"])
    lines.extend(
        [
            "",
            "## Agent obligations",
            "- Honor this steering before substantive reasoning or edits.",
            "- Stay within the context policy; retrieve narrowly, not exhaustively.",
            "- If steering conflicts with a user override, follow the user and note the override.",
            "",
        ]
    )
    return "\n".join(lines)


def write_latest_steering_file(
    root: Path,
    steering_markdown: str,
    *,
    preview: Dict[str, Any],
    session_id: str,
) -> Path:
    directory = thought_tube_dir(root)
    ensure_dir(directory)
    path = directory / "latest-steering.md"
    header = (
        f"<!-- generated_at: {utc_now()} | session_id: {session_id} "
        f"| request_id: {preview.get('request_id', '')} -->\n"
    )
    path.write_text(header + steering_markdown, encoding="utf-8")
    return path


def prepare_turn(
    root: Path,
    *,
    raw_text: str,
    session_id: str = "",
    workspace_id: str = "",
    surface: str = "mcp",
    domain_hints: List[str] | None = None,
    caller_hints: Dict[str, Any] | None = None,
    write_steering_file: bool = True,
) -> Dict[str, Any]:
    text = raw_text.strip()
    if not text:
        raise ValueError("raw_text is required")

    normalized_surface = surface.strip().lower() or "mcp"
    if normalized_surface not in _SUPPORTED_SURFACES:
        normalized_surface = "mcp"

    workspace = _default_workspace_id(root, workspace_id)
    resolved_session_id = resolve_session_id(
        root,
        session_id=session_id,
        workspace_id=workspace,
        surface=normalized_surface,
    )
    merged_hints = dict(caller_hints or {})
    merged_hints.setdefault("workspace_id", workspace)
    merged_hints.setdefault("bridge_session_id", resolved_session_id)

    from .bridge_session_tracking import get_bridge_session
    from .element_routing import (
        enrich_preview_with_element,
        resolve_element_binding,
        sync_session_element_binding,
    )

    try:
        session_row = get_bridge_session(root, resolved_session_id)
    except ValueError:
        session_row = {}

    element_binding = resolve_element_binding(
        root,
        session=session_row,
        caller_hints=merged_hints,
        raw_text=text,
    )
    if element_binding.get("element_key"):
        merged_hints["element_key"] = element_binding["element_key"]
    if element_binding.get("holodeck_id"):
        merged_hints["holodeck_id"] = element_binding["holodeck_id"]
        merged_hints.setdefault("active_workspace_id", element_binding["holodeck_id"])
    if element_binding.get("request_deep"):
        merged_hints["request_global"] = True
        merged_hints["depth_mode"] = "deep"

    request = build_reasoning_request_payload(
        raw_text=text,
        session_id=resolved_session_id,
        surface=normalized_surface,
        domain_hints=domain_hints,
        caller_hints=merged_hints,
    )
    # Tracking turns use fast heuristic classify only. Agent classify + retrieval
    # belong on explicit bridge_run / bridge_classify_preview paths.
    context_state = heuristic_classify_turn(root, request)
    attributes = dict(context_state.get("attributes", {}) or {})
    attributes["element_binding"] = element_binding
    context_state["attributes"] = attributes
    if element_binding.get("element_key"):
        context_state["dimension_axis"] = element_binding["element_key"]
    if element_binding.get("holodeck_id"):
        context_state["active_workspace_id"] = element_binding["holodeck_id"]
    preview = enrich_preview_with_element(summarize_classify_preview(context_state), element_binding)
    if element_binding.get("element_key"):
        from .element_workspace_binding import (
            build_workspace_binding_bundle,
            merge_workspace_binding_into_preview,
        )

        workspace_bundle = build_workspace_binding_bundle(
            root,
            element_key=str(element_binding.get("element_key", "") or ""),
            holodeck_id=str(element_binding.get("holodeck_id", "") or ""),
            subproject_id=str(merged_hints.get("subproject_id", "") or ""),
        )
        preview = merge_workspace_binding_into_preview(preview, workspace_bundle)
    bridge_config = load_bridge_config(root)
    tracking_config = dict(bridge_config.get("tracking", {}) or {})
    require_active = bool(tracking_config.get("require_active_session", True))
    steering_markdown = render_steering_markdown(
        preview,
        session_id=resolved_session_id,
        surface=normalized_surface,
        bridge_config=bridge_config,
    )

    from .bridge_session_tracking import append_bridge_turn, require_active_bridge_session

    if require_active:
        require_active_bridge_session(root, resolved_session_id)
        sync_session_element_binding(root, resolved_session_id, element_binding)

    turn_record = append_bridge_turn(
        root,
        session_id=resolved_session_id,
        workspace_id=workspace,
        surface=normalized_surface,
        raw_text=text,
        actor="user",
        preview=preview,
        request_id=str(preview.get("request_id", "") or request.get("request_id", "")),
        routing_source=str(preview.get("routing_source", "heuristic") or "heuristic"),
    )
    ledger_entry_id = turn_record["ledger_entry_id"]
    session = turn_record["session"]

    element_capture = None
    try:
        from .element_capture import maybe_capture_from_turn

        element_capture = maybe_capture_from_turn(
            root,
            raw_text=text,
            preview=preview,
            binding=element_binding,
            session_id=resolved_session_id,
            ledger_entry_id=ledger_entry_id,
        )
    except ValueError:
        element_capture = None

    session_context: Dict[str, Any] = {}
    try:
        from .bridge_session_context import build_element_scoped_session_context

        session_context = build_element_scoped_session_context(root, resolved_session_id)
        continuity = str(session_context.get("continuity_markdown", "") or "").strip()
        if continuity:
            steering_markdown = steering_markdown.rstrip() + "\n\n" + continuity + "\n"
    except ValueError:
        session_context = {}

    steering_path = ""
    if write_steering_file:
        steering_path = str(
            write_latest_steering_file(
                root,
                steering_markdown,
                preview=preview,
                session_id=resolved_session_id,
            )
        )

    return {
        "ok": True,
        "session_id": resolved_session_id,
        "workspace_id": workspace,
        "surface": normalized_surface,
        "ledger_entry_id": ledger_entry_id,
        "request_id": preview.get("request_id", ""),
        "routing_source": preview.get("routing_source", "heuristic"),
        "control_packet": preview,
        "context_policy": dict(preview.get("context_policy", {}) or {}),
        "element_binding": element_binding,
        "element_capture": element_capture,
        "steering_markdown": steering_markdown,
        "steering_file": steering_path,
        "session_context": session_context,
        "bridge_config": {
            "enabled": bool(bridge_config.get("enabled", False)),
            "execution_mode": bridge_config.get("execution_mode", "operators"),
            "agent": bridge_config.get("agent", ""),
            "model": bridge_config.get("model", ""),
            "openclaw_mode": bridge_config.get("openclaw_mode", "gateway"),
        },
    }
