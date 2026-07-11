#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from conversation_os.workspace_client import WorkspaceClient
from conversation_os.workspace_continuity import render_workspace_continuity_markdown


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish or inspect a read-only canonical workspace continuity export.")
    parser.add_argument("command", choices=("publish", "status"))
    parser.add_argument("--workspace-api-base", required=True)
    parser.add_argument("--workspace-id", required=True)
    parser.add_argument("--task-id", default="")
    parser.add_argument("--path", required=True)
    args = parser.parse_args()
    client = WorkspaceClient(args.workspace_api_base)
    export = client.continuity(args.workspace_id, task_id=args.task_id)
    target = (ROOT / args.path).resolve()
    if ROOT not in target.parents:
        parser.error("--path must be inside this repository")
    if args.command == "publish":
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render_workspace_continuity_markdown(export), encoding="utf-8")
        print(f"published {target} revision={export['canonical_revision']}")
        return 0
    text = target.read_text(encoding="utf-8") if target.exists() else ""
    marker = re.search(r"canonical_revision: ([^\n ]+)", text)
    exported = marker.group(1) if marker else ""
    print("fresh" if exported and exported == export["canonical_revision"] else "stale")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
