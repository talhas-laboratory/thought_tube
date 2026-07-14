#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from conversation_os.bridge_controller import load_bridge_config  # noqa: E402
from conversation_os.chat_backends import ensure_bridge_openclaw_agent  # noqa: E402
from conversation_os.storage import repo_root_from  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Provision the bridge OpenClaw agent and model.")
    parser.add_argument("--agent", default="", help="Override bridge agent id")
    parser.add_argument("--model", default="", help="Override bridge model id")
    parser.add_argument("--workspace", default="", help="Optional OpenClaw workspace path")
    parser.add_argument("--json", action="store_true", help="Print JSON result")
    args = parser.parse_args()

    root = repo_root_from(ROOT)
    bridge = load_bridge_config(root)
    agent_id = args.agent.strip() or str(bridge.get("agent", "thought_tube_router"))
    model_id = args.model.strip() or str(bridge.get("model", "") or "")

    try:
        result = ensure_bridge_openclaw_agent(
            root,
            agent_id=agent_id,
            model_id=model_id,
            workspace=args.workspace.strip(),
        )
    except Exception as exc:
        payload = {"ok": False, "error": str(exc) or exc.__class__.__name__}
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print(payload["error"], file=sys.stderr)
        return 1

    payload = {"ok": True, **result, "bridge_config": bridge}
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"agent={result['agent_id']} model={result['model']} changed={result['changed']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
