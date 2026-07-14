#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _check(label: str, command: list[str]) -> bool:
    completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    ok = completed.returncode == 0
    status = "ok" if ok else "missing"
    print(f"[{status}] {label}")
    if not ok and completed.stderr.strip():
        print(completed.stderr.strip())
    return ok


def main() -> int:
    print("Thought Tube bridge setup check")
    print(f"repo: {ROOT}")
    python_ok = _check("python3", ["python3", "--version"])
    mcp_ok = _check("bridge MCP import", ["python3", "-c", "import sys; sys.path[:0]=['src','.vendor/mcp_py']; import mcp"])
    cli_ok = _check(
        "bridge_prepare_turn CLI",
        ["python3", "tools/bridge_prepare_turn.py", "--text", "setup smoke", "--json"],
    )

    print("\nNext steps:")
    print("- Read .thought-tube/README.md")
    print("- Follow .thought-tube/install-cursor.md (or claude-code / codex / generic)")
    print("- Optional: export INNER_WORLD_BRIDGE_ENABLED=1 for agent classify")
    print("- Provision OpenClaw agent: python3 tools/provision_bridge_openclaw_agent.py --json")
    print("- If gateway is down, bridge openclaw_mode=auto uses --local embedded agent")
    if not python_ok or not cli_ok:
        return 1
    if not mcp_ok:
        print("- MCP SDK not found; stdio MCP server needs `mcp` or .vendor/mcp_py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
