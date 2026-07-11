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

from conversation_os.bridge_session_tracking import end_bridge_session, start_bridge_session  # noqa: E402
from conversation_os.element_curator import review_session_on_end_if_flagged  # noqa: E402
from conversation_os.storage import repo_root_from  # noqa: E402


def _read_input() -> dict:
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    return json.loads(raw)


def main() -> int:
    root = repo_root_from(ROOT)
    payload = _read_input()
    reason = str(payload.get("reason", "") or "Cursor session ended").strip()
    session_id = os.environ.get("THOUGHT_TUBE_SESSION_ID", "").strip() or str(payload.get("session_id", "")).strip()
    if not session_id:
        print(json.dumps({"ok": True, "skipped": "missing_session_id"}))
        return 0

    try:
        result = end_bridge_session(root, session_id, reason=reason)
    except ValueError:
        print(json.dumps({"ok": True, "skipped": "session_not_active"}))
        return 0

    curator_review = review_session_on_end_if_flagged(root, result)

    print(
        json.dumps(
            {
                "ok": True,
                "session_id": session_id,
                "status": result.get("status", ""),
                "curator_review": curator_review,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
