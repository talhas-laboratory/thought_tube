from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict

from .personal_interface import (
    PersonalInterfaceError,
    answer_calibration_question as answer_calibration_question_impl,
    get_profile_snapshot as get_profile_snapshot_impl,
    ingest_learning_conversation as ingest_learning_conversation_impl,
    record_rewrite_feedback as record_rewrite_feedback_impl,
    rewrite_conversation_turn as rewrite_conversation_turn_impl,
    rewrite_outgoing_message as rewrite_outgoing_message_impl,
    start_calibration_interview as start_calibration_interview_impl,
)


def _error_payload(exc: PersonalInterfaceError) -> Dict[str, Any]:
    return exc.to_dict()


def _vendor_paths(root: Path) -> list[Path]:
    return [
        root / ".vendor" / "mcp_py",
    ]


def build_personal_interface_mcp_server(root: Path):
    for vendor_path in _vendor_paths(root):
        if vendor_path.exists() and str(vendor_path) not in sys.path:
            sys.path.insert(0, str(vendor_path))
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:
        raise RuntimeError(
            "The Python MCP SDK is not installed. Install `mcp` before running the personal interface server."
        ) from exc

    server = FastMCP(
        name="Personal Interface",
        instructions=(
            "Rewrites outgoing agent replies to preserve the user's flow state. "
            "Use calibration first, then rewrite outgoing messages, then record feedback."
        ),
    )

    @server.tool()
    def start_calibration_interview() -> Dict[str, Any]:
        try:
            return start_calibration_interview_impl(root)
        except PersonalInterfaceError as exc:
            return _error_payload(exc)

    @server.tool()
    def answer_calibration_question(session_id: str, answer: str) -> Dict[str, Any]:
        try:
            return answer_calibration_question_impl(root, session_id, answer)
        except PersonalInterfaceError as exc:
            return _error_payload(exc)

    @server.tool()
    def get_profile_snapshot() -> Dict[str, Any]:
        try:
            return get_profile_snapshot_impl(root)
        except PersonalInterfaceError as exc:
            return _error_payload(exc)

    @server.tool()
    def ingest_learning_conversation(
        source_text: str | None = None,
        source_path: str | None = None,
        source_url: str | None = None,
        source_label: str | None = None,
    ) -> Dict[str, Any]:
        try:
            return ingest_learning_conversation_impl(
                root,
                source_text=source_text,
                source_path=source_path,
                source_url=source_url,
                source_label=source_label,
            )
        except PersonalInterfaceError as exc:
            return _error_payload(exc)

    @server.tool()
    def rewrite_conversation_turn(
        draft_text: str,
        conversation: list[dict[str, Any]],
        caller_hints: dict[str, Any] | None = None,
        client_context: dict[str, Any] | None = None,
        window_size: int = 8,
    ) -> Dict[str, Any]:
        try:
            return rewrite_conversation_turn_impl(
                root,
                draft_text=draft_text,
                conversation=conversation,
                caller_hints=caller_hints or {},
                client_context=client_context or {},
                window_size=window_size,
            )
        except PersonalInterfaceError as exc:
            return _error_payload(exc)

    @server.tool()
    def rewrite_outgoing_message(
        draft_text: str,
        user_message: str,
        conversation_window: list[dict[str, Any]] | None = None,
        caller_hints: dict[str, Any] | None = None,
        client_context: dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        try:
            return rewrite_outgoing_message_impl(
                root,
                draft_text=draft_text,
                user_message=user_message,
                conversation_window=conversation_window or [],
                caller_hints=caller_hints or {},
                client_context=client_context or {},
            )
        except PersonalInterfaceError as exc:
            return _error_payload(exc)

    @server.tool()
    def record_rewrite_feedback(rewrite_event_id: str, feedback_state: str) -> Dict[str, Any]:
        try:
            return record_rewrite_feedback_impl(root, rewrite_event_id, feedback_state)
        except PersonalInterfaceError as exc:
            return _error_payload(exc)

    return server
