#!/usr/bin/env python3
import asyncio
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
VENDOR = ROOT / ".vendor" / "mcp_py"
if VENDOR.exists() and str(VENDOR) not in sys.path:
    sys.path.insert(0, str(VENDOR))

from conversation_os.personal_interface_mcp import build_personal_interface_mcp_server  # noqa: E402
from conversation_os.storage import repo_root_from  # noqa: E402


async def _run() -> None:
    root = repo_root_from(ROOT)
    server = build_personal_interface_mcp_server(root)
    await server.run_stdio_async()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_run()))
