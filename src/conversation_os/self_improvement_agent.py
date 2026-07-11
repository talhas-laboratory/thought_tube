from __future__ import annotations

import json
import subprocess
from typing import Any, Dict

from .self_improvement import default_packet_for_feedback, validate_system_improvement_packet


MODULE_ID = "kernel.reasoning.self_improvement_agent"
CONTRACT_VERSION = "1.0"
PUBLIC_API = ("MODULE_ID", "CONTRACT_VERSION", "draft_self_improvement_packet")
__all__ = list(PUBLIC_API)


def _extract_json_object(text: str) -> Dict[str, Any]:
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end < start:
        raise ValueError("no json object found")
    return json.loads(text[start : end + 1])


def _agent_prompt(raw_text: str, session_id: str, turn_id: str) -> str:
    return (
        "You are thought_tube_self_improve. Emit one SystemImprovementPacket JSON object only. "
        "Do not answer conversationally. Do not claim deploy authority. "
        f"session_id={session_id}\nturn_id={turn_id}\nraw_user_signal={raw_text}"
    )


def draft_self_improvement_packet(
    raw_text: str,
    session_id: str,
    turn_id: str,
    *,
    use_agent: bool = False,
    timeout_seconds: int = 90,
) -> Dict[str, Any]:
    if not use_agent:
        return default_packet_for_feedback(raw_text, session_id, turn_id)

    try:
        completed = subprocess.run(
            [
                "openclaw",
                "agent",
                "--agent",
                "thought_tube_self_improve",
                "--thinking",
                "high",
                "--message",
                _agent_prompt(raw_text, session_id, turn_id),
                "--json",
            ],
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
        if completed.returncode != 0:
            raise RuntimeError(completed.stderr.strip() or "openclaw exited nonzero")
        packet = _extract_json_object(completed.stdout)
        errors = validate_system_improvement_packet(packet)
        if errors:
            raise ValueError("; ".join(errors))
        return packet
    except Exception:
        packet = default_packet_for_feedback(raw_text, session_id, turn_id)
        packet.setdefault("attributes", {})["fallback_reason"] = "invalid_agent_packet"
        return packet
