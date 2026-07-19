"""Orient-first execution compose for the Cognitive Aperture Bridge path (CAE-004)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence

from .disclosure_contracts import ActiveStateSnapshot
from .storage import make_id, read_json


MODULE_ID = "kernel.disclosure.orient_first_compose"
CONTRACT_VERSION = "1.0"
ORIENTATION_MAX_CHARS = 480
COMPOSE_SECTION_ORDER = (
    "orientation",
    "constraints",
    "evidence",
    "user_turn",
)

PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "ORIENTATION_MAX_CHARS",
    "COMPOSE_SECTION_ORDER",
    "load_orient_first_config",
    "orient_first_compose_enabled",
    "build_active_state_snapshot",
    "render_orientation_text",
    "authorize_second_pass_widen",
    "compose_orient_first_message",
    "message_section_index",
)
__all__ = list(PUBLIC_API)


def _runtime_config_path(root: Path) -> Path:
    return root / "product" / "inner_world_v1" / "config" / "runtime.json"


def load_orient_first_config(root: Path) -> Dict[str, Any]:
    runtime = read_json(_runtime_config_path(root), default={}) or {}
    bridge = runtime.get("bridge", {}) or {}
    disclosure = runtime.get("disclosure", {}) or {}
    return {
        "orient_first_compose_v1": bool(
            bridge.get(
                "orient_first_compose_v1",
                disclosure.get("orient_first_compose_v1", True),
            )
        ),
        "orientation_max_chars": int(
            disclosure.get("orientation_max_chars", ORIENTATION_MAX_CHARS) or ORIENTATION_MAX_CHARS
        ),
    }


def orient_first_compose_enabled(root: Path) -> bool:
    return bool(load_orient_first_config(root)["orient_first_compose_v1"])


def build_active_state_snapshot(
    context_state: Mapping[str, Any],
    control_packet: Mapping[str, Any],
    *,
    workspace_layer: Mapping[str, Any] | None = None,
    session_envelope: Mapping[str, Any] | None = None,
    corpus_revision: str = "",
) -> Dict[str, Any]:
    attributes = dict(context_state.get("attributes", {}) or {})
    caller_hints = dict(attributes.get("caller_hints", {}) or {})
    workspace = dict(workspace_layer or {})
    envelope = dict(session_envelope or {})
    derived_from: List[str] = []
    session_id = str(attributes.get("session_id", "") or context_state.get("session_id", "") or "").strip()
    if session_id:
        derived_from.append(f"session:{session_id}")
    workspace_id = str(
        workspace.get("workspace_id", "")
        or context_state.get("active_workspace_id", "")
        or caller_hints.get("workspace_id", "")
    ).strip()
    if workspace_id:
        derived_from.append(f"workspace:{workspace_id}")
    thought_id = str(workspace.get("thought_id", "") or caller_hints.get("thought_id", "") or "").strip()
    if thought_id:
        derived_from.append(f"thought:{thought_id}")

    snapshot = ActiveStateSnapshot(
        snapshot_id=make_id("state-snap"),
        request_id=str(
            context_state.get("request_id", "")
            or control_packet.get("request_id", "")
            or attributes.get("request_id", "")
        ),
        topic=str(control_packet.get("active_topic") or context_state.get("active_topic", "") or ""),
        purpose=str(control_packet.get("user_goal") or context_state.get("user_goal", "") or ""),
        object_scope=str(control_packet.get("object_scope") or context_state.get("object_scope", "same_main") or "same_main"),
        object_id=thought_id,
        tension=str(context_state.get("tension", "") or ""),
        posture=str(control_packet.get("reasoning_posture") or context_state.get("reasoning_posture", "") or ""),
        lens=str(context_state.get("lens", "") or ""),
        branch_id=str(caller_hints.get("branch_id", "") or ""),
        scope_id=str(caller_hints.get("scope_id", "") or ""),
        source_revision=str(corpus_revision or ""),
        derived_from=derived_from,
        provenance={
            "derived_from_authorized_only": True,
            "excludes_undisclosed_global": True,
            "envelope_mode": str(envelope.get("mode", "") or ""),
        },
    )
    return snapshot.to_dict()


def render_orientation_text(snapshot: Mapping[str, Any], *, max_chars: int = ORIENTATION_MAX_CHARS) -> str:
    lines = [
        f"- topic: {snapshot.get('topic', '')}",
        f"- purpose: {snapshot.get('purpose', '')}",
        f"- object_scope: {snapshot.get('object_scope', '')}",
        f"- posture: {snapshot.get('posture', '')}",
    ]
    if snapshot.get("object_id"):
        lines.append(f"- object_id: {snapshot.get('object_id', '')}")
    if snapshot.get("tension"):
        lines.append(f"- tension: {snapshot.get('tension', '')}")
    if snapshot.get("lens"):
        lines.append(f"- lens: {snapshot.get('lens', '')}")
    envelope_mode = str((snapshot.get("provenance", {}) or {}).get("envelope_mode", "") or "")
    if envelope_mode:
        lines.append(f"- envelope: {envelope_mode}")
    text = "\n".join(lines)
    cap = max(80, int(max_chars))
    if len(text) <= cap:
        return text
    return text[: cap - 3].rstrip() + "..."


def authorize_second_pass_widen(
    *,
    base_mode: str,
    proposed_mode: str,
    caller_hints: Mapping[str, Any] | None = None,
    effective_layers: Sequence[str] | None = None,
) -> tuple[bool, str]:
    widen_targets = {"bounded_global", "deep_global", "session_plus_ocean", "ocean_wide"}
    base = str(base_mode or "").strip().lower()
    proposed = str(proposed_mode or "").strip().lower()
    if proposed in {"", base, "session_only"} or proposed == base:
        return True, ""
    if base not in {"session_only", ""} or proposed not in widen_targets:
        return True, ""
    hints = dict(caller_hints or {})
    if hints.get("second_pass_widen_grant_id") or hints.get("widen_grant_id"):
        return True, "explicit_second_pass_grant"
    layers = {str(value) for value in (effective_layers or [])}
    if "governed_global" in layers and hints.get("requested_global_grant"):
        return True, "requested_global_in_effective_grant"
    return False, "second_pass_widen_requires_new_grant"


def message_section_index(message: str, section_title: str) -> int:
    needle = f"{section_title}:"
    return message.find(needle)


def compose_orient_first_message(
    control_packet: Mapping[str, Any],
    trimmed_bundle: Mapping[str, Any],
    user_text: str,
    *,
    orientation_max_chars: int = ORIENTATION_MAX_CHARS,
) -> str:
    snapshot = dict(trimmed_bundle.get("active_state_snapshot", {}) or {})
    if not snapshot:
        snapshot = build_active_state_snapshot(
            trimmed_bundle.get("context_state", {}) or {},
            control_packet,
            workspace_layer=trimmed_bundle.get("workspace_local", {}) or {},
            session_envelope=trimmed_bundle.get("session_envelope", {}) or {},
        )

    layers = list(trimmed_bundle.get("bundle_layers", []) or [])
    policy = dict(control_packet.get("context_policy", {}) or {})
    constraints = [str(value) for value in control_packet.get("steering_constraints", []) or [] if str(value).strip()]
    envelope = dict(trimmed_bundle.get("session_envelope", {}) or {})
    frame_bundle = dict(trimmed_bundle.get("frame_bundle", {}) or {})

    session_block = "No session-local events disclosed."
    if "session" in layers:
        events = trimmed_bundle.get("session_local", []) or []
        if events:
            session_block = "\n".join(
                f"- {row.get('actor', 'unknown')}: {row.get('content', '')[:240]}"
                for row in events[-6:]
            )

    workspace_block = "No workspace-local context disclosed."
    workspace = trimmed_bundle.get("workspace_local", {}) or {}
    if "workspace" in layers and workspace:
        workspace_block = str(workspace)

    user_block = "No user-local patterns disclosed."
    if "user" in layers:
        user_local = trimmed_bundle.get("user_local", {}) or {}
        if user_local:
            user_block = str(user_local)

    global_block = "No global retrieval disclosed."
    if "global" in layers:
        retrieval = trimmed_bundle.get("global_fallback", {}) or {}
        seeds = list(retrieval.get("seed_capsules", []) or [])[:4]
        if seeds:
            global_block = "\n".join(
                f"- {row.get('label', row.get('capsule_id', 'capsule'))}: {str(row.get('summary', ''))[:180]}"
                for row in seeds
            )
        elif retrieval.get("count"):
            global_block = f"Retrieval count: {retrieval.get('count')}"

    frame_included_block = _format_frame_block_lines(list(frame_bundle.get("included_blocks", []) or []))
    provenance_block = _format_provenance_lines(
        list((frame_bundle.get("provenance_summary", {}) or {}).get("source_refs", []) or [])
    )

    has_evidence = (
        ("session" in layers and "No session-local events disclosed." not in session_block)
        or ("workspace" in layers and workspace and workspace_block != "No workspace-local context disclosed.")
        or ("user" in layers and user_local and user_block != "No user-local patterns disclosed.")
        or ("global" in layers and "No global retrieval disclosed." not in global_block)
        or frame_included_block != "- none"
    )
    evidence_intro = (
        "Disclosed evidence blocks:"
        if has_evidence
        else "No disclosed evidence blocks are available for this turn. Answer from orientation and constraints only; do not invent external evidence."
    )

    constraint_block = "\n".join(f"- {item}" for item in constraints) if constraints else "- Stay inside disclosed context."
    orientation_block = render_orientation_text(snapshot, max_chars=orientation_max_chars)

    message_parts = [
        "Inner World bridge execution request.",
        "Answer the user inside the control packet bounds below.",
        "",
        "Orientation:",
        orientation_block,
        "",
        "Steering constraints:",
        constraint_block,
        "",
        "Evidence:",
        evidence_intro,
        "",
        "Session local:",
        session_block,
        "",
        "Workspace local:",
        workspace_block,
        "",
        "User local:",
        user_block,
        "",
        "Global retrieval:",
        global_block,
        "",
        "Included frame blocks:",
        frame_included_block,
        "",
        "Frame provenance:",
        provenance_block,
        "",
        f"User message: {user_text}",
        "",
        "Instructions:",
        "- Answer directly for the user.",
        "- Honor steering constraints and disclosed layers only.",
        "- Do not invent evidence outside the bundle.",
        "- Do not mention internal bridge, routing, frame, or context-assembly mechanics.",
        "- End with one concrete next move.",
        "",
        f"Context policy mode: {policy.get('mode', '')}",
        f"Depth mode: {policy.get('depth_mode', '')}",
        f"Session envelope mode: {envelope.get('mode', '')}",
        f"Frame id: {frame_bundle.get('frame_id', '')}",
        f"Frame assembly: {frame_bundle.get('assembly_status', '')}",
    ]
    return "\n".join(message_parts)


def _format_frame_block_lines(rows: Sequence[Mapping[str, Any]]) -> str:
    if not rows:
        return "- none"
    return "\n".join(
        f"- {str(row.get('layer', 'unknown'))}: {str(row.get('summary', '')).strip() or 'no summary'}"
        for row in rows
    )


def _format_provenance_lines(source_refs: Sequence[str]) -> str:
    refs = [str(value).strip() for value in source_refs if str(value).strip()]
    if not refs:
        return "- none"
    return "\n".join(f"- {value}" for value in refs[:6])
