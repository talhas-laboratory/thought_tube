#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from conversation_os.workspace_client import WorkspaceClient, WorkspaceClientError
from conversation_os.workspace_work_adapter import WorkspaceWorkAdapter


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the connected workspace lifecycle for a terminal agent.")
    parser.add_argument("command", choices=("begin", "heartbeat", "handoff"))
    parser.add_argument("--workspace-api-base", required=True)
    parser.add_argument("--workspace-id", required=True)
    parser.add_argument("--task-id", default="")
    parser.add_argument("--run-id", default="")
    parser.add_argument("--agent-id", default="codex")
    parser.add_argument("--device-id", required=True)
    parser.add_argument("--surface", default="codex")
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--intent", default="")
    parser.add_argument("--claimed-path", action="append", default=[])
    parser.add_argument("--next-action", default="")
    parser.add_argument("--update", default="")
    parser.add_argument("--reasoning", default="")
    parser.add_argument("--source-revision", default="")
    parser.add_argument("--idempotency-key", default="")
    args = parser.parse_args(argv)
    adapter = WorkspaceWorkAdapter(WorkspaceClient(args.workspace_api_base), args.workspace_id, args.agent_id, args.device_id, args.surface, args.session_id)
    try:
        if args.command == "begin":
            result = adapter.begin(task_id=args.task_id, intent=args.intent, claimed_paths=args.claimed_path, source_revision=args.source_revision, next_action=args.next_action, idempotency_key=args.idempotency_key)
        elif args.command == "heartbeat":
            result = adapter.heartbeat(run_id=args.run_id, update=args.update, rationale=args.reasoning, idempotency_key=args.idempotency_key)
        else:
            result = adapter.handoff(run_id=args.run_id, next_action=args.next_action, rationale=args.reasoning, idempotency_key=args.idempotency_key)
    except (FileNotFoundError, ValueError, WorkspaceClientError) as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
