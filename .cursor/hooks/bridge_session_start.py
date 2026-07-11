#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(SRC))
sys.path[:] = [entry for entry in sys.path if entry != str(TOOLS)]

from conversation_os.bridge_controller import load_bridge_config  # noqa: E402
from conversation_os.bridge_session_tracking import get_bridge_session, start_bridge_session  # noqa: E402
from conversation_os.storage import repo_root_from  # noqa: E402


def _read_input() -> dict:
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    return json.loads(raw)


def _default_session_binding(root: Path) -> dict:
    bridge = load_bridge_config(root)
    tracking = dict(bridge.get("tracking", {}) or {})
    binding = dict(tracking.get("default_session_binding", {}) or {})
    return {
        "element_key": str(binding.get("element_key", "") or "").strip(),
        "holodeck_id": str(binding.get("holodeck_id", "") or "").strip(),
        "subproject_id": str(binding.get("subproject_id", "") or "").strip(),
    }


def main() -> int:
    root = repo_root_from(ROOT)
    payload = _read_input()
    session_id = str(payload.get("session_id", "") or "").strip()
    steering_path = root / ".thought-tube" / "STEERING.md"
    steering_contract = ""
    if steering_path.exists():
        steering_contract = steering_path.read_text(encoding="utf-8").strip()

    defaults = _default_session_binding(root)

    try:
        get_bridge_session(root, session_id)
    except ValueError:
        try:
            start_bridge_session(
                root,
                session_id=session_id,
                title=f"Cursor session {session_id[:8]}",
                surface="cursor",
                workspace_id=root.name,
                element_key=defaults.get("element_key", ""),
                holodeck_id=defaults.get("holodeck_id", ""),
            )
        except ValueError:
            pass

    binding_lines = []
    if defaults.get("element_key"):
        binding_lines.append(f"- element_key: `{defaults['element_key']}`")
    if defaults.get("holodeck_id"):
        binding_lines.append(f"- holodeck_id: `{defaults['holodeck_id']}`")
    if defaults.get("subproject_id"):
        binding_lines.append(f"- subproject_id: `{defaults['subproject_id']}`")
    binding_block = "\n".join(binding_lines)

    additional_context = "\n".join(
        [
            "# Thought Tube bridge session",
            "",
            "This repository uses the Thought Tube bridge control plane.",
            f"- session_id: `{session_id}`",
            "- Before substantive reasoning, read `.thought-tube/latest-steering.md` if it exists.",
            "- Honor the steering block as binding control-plane guidance.",
            "- Workspace binding keeps PWA work inside `product/thought_capture_pwa/` when frontend is active.",
            "- You may also call MCP tool `bridge_prepare_turn` when hooks are unavailable.",
            "",
            "## Default workspace binding",
            binding_block or "- (none configured)",
            "",
            "## Portable contract",
            steering_contract,
        ]
    ).strip()

    env = {
        "THOUGHT_TUBE_SESSION_ID": session_id,
        "THOUGHT_TUBE_WORKSPACE_ID": root.name,
    }
    if defaults.get("element_key"):
        env["THOUGHT_TUBE_ELEMENT_KEY"] = defaults["element_key"]
    if defaults.get("holodeck_id"):
        env["THOUGHT_TUBE_HOLODECK_ID"] = defaults["holodeck_id"]
    if defaults.get("subproject_id"):
        env["THOUGHT_TUBE_SUBPROJECT_ID"] = defaults["subproject_id"]

    print(
        json.dumps(
            {
                "env": env,
                "additional_context": additional_context,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
