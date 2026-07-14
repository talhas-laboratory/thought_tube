from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List

from .bridge_controller import load_bridge_config as load_bridge_config_impl
from .bridge_prepare import (
    build_reasoning_request_payload,
    prepare_turn as prepare_turn_impl,
    summarize_classify_preview,
)
from .bridge_session_context import build_element_scoped_session_context
from .bridge_session_tracking import (
    end_bridge_session,
    get_bridge_session,
    get_bridge_session_trace,
    list_bridge_sessions,
    record_assistant_turn,
    start_bridge_session,
)
from .bridge_session_retention import enforce_session_retention
from .reasoning_bridge import (
    classify_turn as classify_turn_impl,
    load_bridge_behavior_specs as load_bridge_behavior_specs_impl,
    load_control_packets as load_control_packets_impl,
    prepare_bridge_candidates as prepare_bridge_candidates_impl,
)
from .reasoning_runtime import inspect_reasoning_request as inspect_reasoning_request_impl
from .reasoning_runtime import run_reasoning as run_reasoning_impl


MODULE_ID = "surface.bridge.bridge_mcp"
CONTRACT_VERSION = "1.2"
PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "build_bridge_mcp_server",
    "summarize_run_result",
    "summarize_control_packet_row",
    "list_control_packet_summaries",
    "classify_preview",
)
__all__ = list(PUBLIC_API)

_MAX_LIST_LIMIT = 100
_DEFAULT_LIST_LIMIT = 20


def _vendor_paths(root: Path) -> list[Path]:
    return [root / ".vendor" / "mcp_py"]


def _ok_payload(**fields: Any) -> Dict[str, Any]:
    return {"ok": True, **fields}


def _error_payload(
    error: str,
    *,
    message: str = "",
    hint: str = "",
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {"ok": False, "error": error}
    if message:
        payload["message"] = message
    if hint:
        payload["hint"] = hint
    return payload


def summarize_control_packet_row(row: Dict[str, Any]) -> Dict[str, Any]:
    packet = dict(row.get("packet", {}) or {})
    metadata = dict(row.get("metadata", {}) or {})
    context_policy = dict(packet.get("context_policy", {}) or {})
    return {
        "timestamp": row.get("timestamp", ""),
        "packet_id": packet.get("packet_id", ""),
        "request_id": packet.get("request_id", ""),
        "routing_source": packet.get("routing_source", metadata.get("routing_source", "")),
        "active_topic": packet.get("active_topic", ""),
        "user_goal": packet.get("user_goal", ""),
        "reasoning_posture": packet.get("reasoning_posture", ""),
        "pipeline_id": packet.get("pipeline_id", ""),
        "bridge_behaviors": list(packet.get("bridge_behaviors", []) or []),
        "confidence": packet.get("confidence"),
        "context_policy_mode": context_policy.get("mode", ""),
        "context_policy_depth_mode": context_policy.get("depth_mode", ""),
    }


def summarize_run_result(result: Dict[str, Any]) -> Dict[str, Any]:
    context_state = dict(result.get("context_state", {}) or {})
    attributes = dict(context_state.get("attributes", {}) or {})
    run_result = dict(result.get("result", {}) or {})
    evaluation = dict(result.get("evaluation", {}) or {})
    route = dict(result.get("route", {}) or {})
    return {
        "request_id": context_state.get("request_id", ""),
        "routing_source": attributes.get("routing_source", "heuristic"),
        "control_packet_id": attributes.get("control_packet_id", ""),
        "pipeline_id": route.get("pipeline_id", ""),
        "response_text": run_result.get("response_text", ""),
        "integration_verdict": run_result.get("integration_verdict", ""),
        "fit_score": run_result.get("fit_score"),
        "confidence": run_result.get("confidence"),
        "recommended_next_action": run_result.get("recommended_next_action", ""),
        "operator_trace": list(run_result.get("operator_trace", []) or []),
        "evaluation": {
            "integration_verdict": evaluation.get("integration_verdict", ""),
            "fit_score": evaluation.get("fit_score"),
            "novelty_score": evaluation.get("novelty_score"),
            "generic_flattening_risk": evaluation.get("generic_flattening_risk"),
        },
    }


def classify_preview(
    root: Path,
    request: Dict[str, Any],
    *,
    include_candidates: bool = False,
) -> Dict[str, Any]:
    context_state = classify_turn_impl(root, request)
    preview = summarize_classify_preview(context_state)
    payload = _ok_payload(preview=preview)
    if include_candidates:
        candidates = prepare_bridge_candidates_impl(root, request)
        retrieval_bundle = dict(candidates.get("retrieval_bundle", {}) or {})
        payload["candidates"] = {
            "retrieval_count": int(retrieval_bundle.get("count", 0) or 0),
            "seed_capsule_ids": [
                str(row.get("capsule_id", "") or row.get("id", ""))
                for row in list(retrieval_bundle.get("seed_capsules", []) or [])[:6]
            ],
            "heuristic_preview": summarize_classify_preview(dict(candidates.get("heuristic_preview", {}) or {})),
        }
    return payload


def list_control_packet_summaries(
    root: Path,
    *,
    request_id: str = "",
    limit: int = _DEFAULT_LIST_LIMIT,
) -> Dict[str, Any]:
    bounded_limit = max(1, min(int(limit), _MAX_LIST_LIMIT))
    rows = load_control_packets_impl(root)
    if request_id.strip():
        rows = [
            row
            for row in rows
            if str((row.get("packet") or {}).get("request_id", "")).strip() == request_id.strip()
        ]
    selected = rows[-bounded_limit:]
    selected.reverse()
    return _ok_payload(
        count=len(selected),
        total_available=len(rows),
        request_id_filter=request_id.strip(),
        packets=[summarize_control_packet_row(row) for row in selected],
    )


def build_bridge_mcp_server(root: Path):
    for vendor_path in _vendor_paths(root):
        if vendor_path.exists() and str(vendor_path) not in sys.path:
            sys.path.insert(0, str(vendor_path))
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:
        raise RuntimeError(
            "The Python MCP SDK is not installed. Install `mcp` before running the bridge MCP server."
        ) from exc

    server = FastMCP(
        name="Thought Tube Bridge",
        instructions=(
            "Thought Tube bridge control plane. "
            "Call bridge_prepare_turn before substantive reasoning on every user turn. "
            "Honor steering_markdown and context_policy from the response. "
            "Use bridge_inspect_request for persisted turns and bridge_run only when a full product answer is needed. "
            "Do not request full corpus dumps."
        ),
    )

    @server.tool()
    def bridge_inspect_request(request_id: str) -> Dict[str, Any]:
        try:
            inspected = inspect_reasoning_request_impl(root, request_id.strip())
        except FileNotFoundError as exc:
            return _error_payload(
                "request_not_found",
                message=str(exc),
                hint="Run bridge_list_control_packets to find recent request_id values.",
            )
        except Exception as exc:
            return _error_payload("inspect_failed", message=str(exc) or exc.__class__.__name__)
        return _ok_payload(inspection=inspected)

    @server.tool()
    def bridge_list_control_packets(
        request_id: str = "",
        limit: int = _DEFAULT_LIST_LIMIT,
    ) -> Dict[str, Any]:
        try:
            return list_control_packet_summaries(root, request_id=request_id, limit=limit)
        except Exception as exc:
            return _error_payload("list_control_packets_failed", message=str(exc) or exc.__class__.__name__)

    @server.tool()
    def bridge_list_behaviors() -> Dict[str, Any]:
        try:
            specs = load_bridge_behavior_specs_impl(root)
        except Exception as exc:
            return _error_payload("list_behaviors_failed", message=str(exc) or exc.__class__.__name__)
        behaviors: List[Dict[str, Any]] = []
        for behavior_id in sorted(specs):
            spec = dict(specs[behavior_id])
            behaviors.append(
                {
                    "behavior_id": behavior_id,
                    "preferred_pipeline": spec.get("preferred_pipeline", ""),
                    "routing_mode": spec.get("routing_mode", ""),
                    "reasoning_posture": spec.get("reasoning_posture", ""),
                    "priority": spec.get("priority"),
                    "response_directives": list(spec.get("response_directives", []) or []),
                    "operator_biases": dict(spec.get("operator_biases", {}) or {}),
                }
            )
        return _ok_payload(count=len(behaviors), behaviors=behaviors)

    @server.tool()
    def bridge_get_config() -> Dict[str, Any]:
        try:
            config = load_bridge_config_impl(root)
        except Exception as exc:
            return _error_payload("get_config_failed", message=str(exc) or exc.__class__.__name__)
        return _ok_payload(config=config)

    @server.tool()
    def bridge_record_assistant_turn(
        session_id: str,
        response_text: str,
        workspace_id: str = "",
        surface: str = "cursor",
    ) -> Dict[str, Any]:
        try:
            result = record_assistant_turn(
                root,
                session_id=session_id.strip(),
                response_text=response_text,
                workspace_id=workspace_id,
                surface=surface,
            )
            return _ok_payload(result=result)
        except ValueError as exc:
            return _error_payload("invalid_request", message=str(exc))
        except Exception as exc:
            return _error_payload("record_assistant_turn_failed", message=str(exc) or exc.__class__.__name__)

    @server.tool()
    def bridge_compact_session(session_id: str) -> Dict[str, Any]:
        try:
            result = enforce_session_retention(root, session_id.strip())
            return _ok_payload(retention=result)
        except ValueError as exc:
            return _error_payload("invalid_request", message=str(exc))
        except Exception as exc:
            return _error_payload("compact_session_failed", message=str(exc) or exc.__class__.__name__)

    @server.tool()
    def bridge_get_session_context(
        session_id: str,
        max_turns: int = 12,
        element_key: str = "",
    ) -> Dict[str, Any]:
        try:
            context = build_element_scoped_session_context(
                root,
                session_id.strip(),
                max_turns=max(1, min(int(max_turns), 50)),
                element_key=element_key.strip(),
            )
            return _ok_payload(session_context=context)
        except ValueError as exc:
            return _error_payload("invalid_request", message=str(exc))
        except Exception as exc:
            return _error_payload("get_session_context_failed", message=str(exc) or exc.__class__.__name__)

    @server.tool()
    def bridge_list_element_captures(
        element_key: str,
        status: str = "provisional",
        session_id: str = "",
        limit: int = 20,
    ) -> Dict[str, Any]:
        try:
            from .element_capture import list_element_captures

            result = list_element_captures(
                root,
                element_key.strip(),
                status=status,
                session_id=session_id.strip(),
                limit=max(1, min(int(limit), 200)),
            )
            return _ok_payload(**result)
        except ValueError as exc:
            return _error_payload("invalid_request", message=str(exc))
        except Exception as exc:
            return _error_payload("list_element_captures_failed", message=str(exc) or exc.__class__.__name__)

    @server.tool()
    def bridge_review_element_captures(
        session_id: str,
        element_key: str = "",
        auto_apply: bool = False,
    ) -> Dict[str, Any]:
        try:
            from .element_curator import review_session_for_promotion

            result = review_session_for_promotion(
                root,
                session_id.strip(),
                element_key=element_key.strip(),
                auto_apply=bool(auto_apply),
            )
            return _ok_payload(review=result)
        except ValueError as exc:
            return _error_payload("invalid_request", message=str(exc))
        except Exception as exc:
            return _error_payload("review_element_captures_failed", message=str(exc) or exc.__class__.__name__)

    @server.tool()
    def bridge_ingest_to_element(
        raw_text: str,
        source_kind: str = "manual_ingest",
        source_ref: str = "",
        session_id: str = "",
        element_key: str = "",
        surface_hints: str = "",
    ) -> Dict[str, Any]:
        try:
            from .element_ingest import ingest_to_element_space

            hints = [part.strip() for part in surface_hints.split(",") if part.strip()]
            result = ingest_to_element_space(
                root,
                raw_text=raw_text,
                source_kind=source_kind.strip() or "manual_ingest",
                source_ref=source_ref.strip(),
                session_id=session_id.strip(),
                surface_hints=hints,
                element_key=element_key.strip(),
            )
            return _ok_payload(**result)
        except ValueError as exc:
            return _error_payload("invalid_request", message=str(exc))
        except Exception as exc:
            return _error_payload("ingest_to_element_failed", message=str(exc) or exc.__class__.__name__)

    @server.tool()
    def bridge_start_session(
        session_id: str,
        title: str = "",
        surface: str = "cursor",
        workspace_id: str = "",
        restart: bool = False,
        element_key: str = "",
        holodeck_id: str = "",
        topology_mode: str = "",
        auto_promote_review: bool = False,
    ) -> Dict[str, Any]:
        try:
            session = start_bridge_session(
                root,
                session_id=session_id.strip(),
                title=title,
                surface=surface,
                workspace_id=workspace_id,
                restart=restart,
                element_key=element_key,
                holodeck_id=holodeck_id,
                topology_mode=topology_mode,
                auto_promote_review=auto_promote_review,
            )
            return _ok_payload(session=session)
        except ValueError as exc:
            return _error_payload("invalid_request", message=str(exc))
        except Exception as exc:
            return _error_payload("start_session_failed", message=str(exc) or exc.__class__.__name__)

    @server.tool()
    def bridge_end_session(
        session_id: str,
        reason: str = "",
    ) -> Dict[str, Any]:
        try:
            session = end_bridge_session(root, session_id.strip(), reason=reason)
            return _ok_payload(session=session)
        except ValueError as exc:
            return _error_payload("invalid_request", message=str(exc))
        except Exception as exc:
            return _error_payload("end_session_failed", message=str(exc) or exc.__class__.__name__)

    @server.tool()
    def bridge_get_session(session_id: str) -> Dict[str, Any]:
        try:
            session = get_bridge_session(root, session_id.strip())
            return _ok_payload(session=session)
        except FileNotFoundError as exc:
            return _error_payload("session_not_found", message=str(exc))
        except Exception as exc:
            return _error_payload("get_session_failed", message=str(exc) or exc.__class__.__name__)

    @server.tool()
    def bridge_list_sessions(
        status: str = "",
        limit: int = _DEFAULT_LIST_LIMIT,
    ) -> Dict[str, Any]:
        try:
            payload = list_bridge_sessions(root, status=status, limit=limit)
            return _ok_payload(**payload)
        except Exception as exc:
            return _error_payload("list_sessions_failed", message=str(exc) or exc.__class__.__name__)

    @server.tool()
    def bridge_get_session_trace(session_id: str) -> Dict[str, Any]:
        try:
            trace = get_bridge_session_trace(root, session_id.strip())
            return _ok_payload(trace=trace)
        except FileNotFoundError as exc:
            return _error_payload("session_not_found", message=str(exc))
        except Exception as exc:
            return _error_payload("get_session_trace_failed", message=str(exc) or exc.__class__.__name__)

    @server.tool()
    def bridge_prepare_turn(
        raw_text: str,
        session_id: str = "",
        workspace_id: str = "",
        surface: str = "mcp",
        domain_hints: List[str] | None = None,
        caller_hints: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        try:
            return prepare_turn_impl(
                root,
                raw_text=raw_text,
                session_id=session_id,
                workspace_id=workspace_id,
                surface=surface,
                domain_hints=domain_hints,
                caller_hints=caller_hints,
                write_steering_file=True,
            )
        except ValueError as exc:
            return _error_payload("invalid_request", message=str(exc))
        except Exception as exc:
            return _error_payload("prepare_turn_failed", message=str(exc) or exc.__class__.__name__)

    @server.tool()
    def bridge_classify_preview(
        raw_text: str,
        request_id: str = "",
        session_id: str = "",
        surface: str = "mcp",
        domain_hints: List[str] | None = None,
        caller_hints: Dict[str, Any] | None = None,
        include_candidates: bool = False,
    ) -> Dict[str, Any]:
        try:
            request = build_reasoning_request_payload(
                raw_text=raw_text,
                request_id=request_id,
                session_id=session_id,
                surface=surface,
                domain_hints=domain_hints,
                caller_hints=caller_hints,
            )
            return classify_preview(root, request, include_candidates=include_candidates)
        except ValueError as exc:
            return _error_payload("invalid_request", message=str(exc))
        except Exception as exc:
            return _error_payload("classify_preview_failed", message=str(exc) or exc.__class__.__name__)

    @server.tool()
    def bridge_run(
        raw_text: str,
        request_id: str = "",
        session_id: str = "",
        surface: str = "mcp",
        domain_hints: List[str] | None = None,
        caller_hints: Dict[str, Any] | None = None,
        source_refs: List[str] | None = None,
    ) -> Dict[str, Any]:
        try:
            request = build_reasoning_request_payload(
                raw_text=raw_text,
                request_id=request_id,
                session_id=session_id,
                surface=surface,
                domain_hints=domain_hints,
                caller_hints=caller_hints,
                source_refs=source_refs,
            )
            result = run_reasoning_impl(root, request)
            summary = summarize_run_result(result)
            return _ok_payload(
                summary=summary,
                hint="Use bridge_inspect_request with summary.request_id for full artifacts.",
            )
        except ValueError as exc:
            return _error_payload("invalid_request", message=str(exc))
        except Exception as exc:
            return _error_payload(
                "run_failed",
                message=str(exc) or exc.__class__.__name__,
                hint="Check bridge_get_config and bridge_list_control_packets for recent failures.",
            )

    return server
