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

from conversation_os.bridge_prepare import prepare_turn, thought_tube_dir  # noqa: E402
from conversation_os.bridge_session_tracking import get_bridge_session, start_bridge_session  # noqa: E402
from conversation_os.storage import repo_root_from  # noqa: E402


def _read_input() -> dict:
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    return json.loads(raw)


def main() -> int:
    root = repo_root_from(ROOT)
    payload = _read_input()
    prompt = str(payload.get("prompt", "") or "").strip()
    if not prompt:
        print(json.dumps({"continue": True}))
        return 0

    session_id = os.environ.get("THOUGHT_TUBE_SESSION_ID", "").strip()
    workspace_id = os.environ.get("THOUGHT_TUBE_WORKSPACE_ID", root.name).strip()
    caller_hints = {}
    for env_key, hint_key in (
        ("THOUGHT_TUBE_ELEMENT_KEY", "element_key"),
        ("THOUGHT_TUBE_HOLODECK_ID", "holodeck_id"),
        ("THOUGHT_TUBE_SUBPROJECT_ID", "subproject_id"),
    ):
        value = os.environ.get(env_key, "").strip()
        if value:
            caller_hints[hint_key] = value

    if session_id:
        try:
            get_bridge_session(root, session_id)
        except ValueError:
            try:
                start_bridge_session(
                    root,
                    session_id=session_id,
                    title=f"Cursor session {session_id[:8]}",
                    surface="cursor",
                    workspace_id=workspace_id,
                    element_key=str(caller_hints.get("element_key", "") or ""),
                    holodeck_id=str(caller_hints.get("holodeck_id", "") or ""),
                )
            except ValueError:
                pass

    try:
        result = prepare_turn(
            root,
            raw_text=prompt,
            session_id=session_id,
            workspace_id=workspace_id,
            surface="cursor",
            caller_hints=caller_hints or None,
            write_steering_file=True,
        )
    except Exception as exc:
        steering_path = thought_tube_dir(root) / "latest-steering.md"
        print(
            json.dumps(
                {
                    "continue": True,
                    "user_message": "",
                    "bridge_hook_warning": str(exc) or exc.__class__.__name__,
                    "steering_file": str(steering_path),
                }
            )
        )
        return 0

    print(
        json.dumps(
            {
                "continue": True,
                "steering_file": result.get("steering_file", ""),
                "session_id": result.get("session_id", ""),
                "ledger_entry_id": result.get("ledger_entry_id", ""),
                "routing_source": result.get("routing_source", ""),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
