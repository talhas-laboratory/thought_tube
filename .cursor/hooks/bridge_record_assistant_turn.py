#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(SRC))
sys.path[:] = [entry for entry in sys.path if entry != str(TOOLS)]

from conversation_os.bridge_session_tracking import record_assistant_turn  # noqa: E402
from conversation_os.storage import repo_root_from  # noqa: E402


def _read_input() -> dict:
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    return json.loads(raw)


def _extract_response_text(payload: dict) -> str:
    for key in ("text", "response", "assistant_message", "message", "content", "final_message"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    messages = payload.get("messages")
    if isinstance(messages, list):
        parts: list[str] = []
        for row in messages:
            if not isinstance(row, dict):
                continue
            role = str(row.get("role", "")).strip().lower()
            text = str(row.get("content", "") or row.get("text", "")).strip()
            if role in {"assistant", "agent"} and text:
                parts.append(text)
        if parts:
            return "\n\n".join(parts)
    return ""


def main() -> int:
    root = repo_root_from(ROOT)
    payload = _read_input()
    response_text = _extract_response_text(payload)
    if not response_text:
        print(json.dumps({"ok": True, "skipped": "empty_response"}))
        return 0

    session_id = os.environ.get("THOUGHT_TUBE_SESSION_ID", "").strip() or str(payload.get("session_id", "")).strip()
    workspace_id = os.environ.get("THOUGHT_TUBE_WORKSPACE_ID", root.name).strip()
    if not session_id:
        print(json.dumps({"ok": True, "skipped": "missing_session_id"}))
        return 0

    try:
        result = record_assistant_turn(
            root,
            session_id=session_id,
            response_text=response_text,
            workspace_id=workspace_id,
            surface="cursor",
        )
    except ValueError as exc:
        print(json.dumps({"ok": True, "skipped": str(exc)}))
        return 0
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc) or exc.__class__.__name__}))
        return 0

    print(
        json.dumps(
            {
                "ok": True,
                "session_id": session_id,
                "ledger_entry_id": result.get("ledger_entry_id", ""),
                "assistant_turn_count": int((result.get("session") or {}).get("assistant_turn_count", 0) or 0),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
