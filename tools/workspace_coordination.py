from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) in sys.path:
    sys.path.remove(str(SRC))
sys.path.insert(0, str(SRC))

from conversation_os.storage import repo_root_from
from conversation_os.workspace_atlas import materialize_workspace_atlas
from conversation_os.workspace_client import WorkspaceClient, WorkspaceClientError
from conversation_os.workspace_context_packet import assemble_workspace_context_packet
from conversation_os.workspace_runs import begin_workspace_run, end_workspace_run, heartbeat_workspace_run, list_workspace_runs
from conversation_os.workspace_reasoning import list_workspace_reasoning, record_workspace_reasoning
from conversation_os.workspace_progress import derive_workspace_task_progress
from conversation_os.workspace_coordination import (
    claim_workspace_task,
    complete_workspace_task,
    create_workspace_task,
    evaluate_workspace_release_gate,
    prepare_workspace_task,
    record_workspace_blocker,
    record_workspace_decision,
    record_workspace_test_run,
    release_workspace_task_claims,
    resolve_workspace_blocker,
    render_workspace_status,
    render_workspace_tasks,
    update_workspace_task,
)


def _default_workspace_api_base() -> str:
    configured = str(os.environ.get("INNER_WORLD_WORKSPACE_API_BASE", "") or "").strip()
    if configured:
        return configured
    config_path = Path(os.path.expanduser("~/.config/inner-space-workspace.env"))
    if not config_path.is_file():
        return ""
    for line in config_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("INNER_WORLD_WORKSPACE_API_BASE="):
            return stripped.split("=", 1)[1].strip()
    return ""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Workspace coordination helper.")
    parser.add_argument("command", choices=("status", "tasks", "context", "prepare", "progress", "runs", "begin-run", "heartbeat-run", "end-run", "reasoning", "record-reasoning", "create-task", "update-task", "claim", "handoff", "decision", "verify", "blocker", "resolve-blocker", "complete", "gate", "atlas"))
    parser.add_argument("--root", default="", help="Repo root. Defaults to current repo.")
    parser.add_argument(
        "--mode",
        choices=("connected", "offline"),
        default="",
        help="Workspace authority mode. Defaults to connected unless --root explicitly selects an offline local store.",
    )
    parser.add_argument("--workspace-id", required=True)
    parser.add_argument("--task-id", default="")
    parser.add_argument("--agent-id", default="codex")
    parser.add_argument("--surface", default="codex")
    parser.add_argument("--session-id", default="local-session")
    parser.add_argument("--device-id", default="")
    parser.add_argument("--run-id", default="")
    parser.add_argument("--heartbeat-ttl-seconds", type=int, default=900)
    parser.add_argument("--run-end-status", choices=("released", "handed_off", "completed", "cancelled"), default="released")
    parser.add_argument("--source-revision", default="")
    parser.add_argument("--reasoning-kind", default="")
    parser.add_argument("--confidence", type=float, default=None)
    parser.add_argument("--idempotency-key", default="", help="Optional retry-safe key for one canonical service mutation.")
    parser.add_argument("--intent", default="")
    parser.add_argument("--claimed-path", action="append", default=[])
    parser.add_argument("--file-touched", action="append", default=[])
    parser.add_argument("--command-run", action="append", default=[])
    parser.add_argument("--residual-risk", action="append", default=[])
    parser.add_argument("--title", default="")
    parser.add_argument("--task-status", default=None)
    parser.add_argument("--priority", default=None)
    parser.add_argument("--owner", default=None)
    parser.add_argument("--acceptance", action="append", default=None)
    parser.add_argument("--constraint", action="append", default=None)
    parser.add_argument("--depends-on", action="append", default=None)
    parser.add_argument("--linked-artifact", action="append", default=None)
    parser.add_argument("--source-ref", action="append", default=None)
    parser.add_argument("--parent-task-id", default=None, help="Optional parent task id; creates a first-class subtask.")
    parser.add_argument("--blocker-id", default="")
    parser.add_argument("--summary", default="")
    parser.add_argument("--reasoning", default="")
    parser.add_argument("--next-action", default="")
    parser.add_argument("--test-name", default="")
    parser.add_argument("--result", default="")
    parser.add_argument("--evidence-ref", default="")
    parser.add_argument("--notes", default="")
    parser.add_argument("--command-or-protocol", default="")
    parser.add_argument("--git-changes-path", default="")
    parser.add_argument(
        "--workspace-api-base",
        default="",
        help="Canonical workspace service base URL. File mode is used only when unset.",
    )
    return parser


def _resolve_root(raw_root: str) -> Path:
    if raw_root:
        return Path(raw_root).expanduser().resolve()
    return repo_root_from(Path(__file__).resolve()).resolve()


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    root = _resolve_root(args.root)
    mode = args.mode or ("connected" if args.workspace_api_base else ("offline" if args.root else "connected"))
    if mode == "connected":
        if not args.workspace_api_base:
            args.workspace_api_base = _default_workspace_api_base()
        if not args.workspace_api_base:
            parser.error("connected mode requires --workspace-api-base or INNER_WORLD_WORKSPACE_API_BASE")
        if args.command == "atlas":
            parser.error("atlas materialization is offline-only until the canonical service exposes an atlas endpoint")
    elif args.workspace_api_base:
        parser.error("offline mode cannot use --workspace-api-base")

    if mode == "connected":
        client = WorkspaceClient(args.workspace_api_base)
        common = {
            "task_id": args.task_id,
            "agent_id": args.agent_id,
            "surface": args.surface,
            "session_id": args.session_id,
        }
        if args.idempotency_key:
            common["_idempotency_key"] = args.idempotency_key
        try:
            if args.command == "status":
                print(client.status(args.workspace_id)["text"])
            elif args.command == "tasks":
                print(client.tasks(args.workspace_id)["text"])
            elif args.command == "prepare":
                print(json.dumps(client.prepare(args.workspace_id, **common), indent=2))
            elif args.command == "context":
                print(json.dumps(client.context(args.workspace_id, **common), indent=2))
            elif args.command == "progress":
                print(json.dumps(client.progress(args.workspace_id, task_id=args.task_id), indent=2))
            elif args.command == "runs":
                print(json.dumps(client.runs(args.workspace_id, task_id=args.task_id), indent=2))
            elif args.command == "begin-run":
                print(json.dumps(client.begin_run(args.workspace_id, **common, device_id=args.device_id, intent=args.intent, source_revision=args.source_revision, heartbeat_ttl_seconds=args.heartbeat_ttl_seconds, run_id=args.run_id, claimed_paths=list(args.claimed_path or [])), indent=2))
            elif args.command == "heartbeat-run":
                print(json.dumps(client.heartbeat_run(args.workspace_id, run_id=args.run_id, agent_id=args.agent_id, _idempotency_key=args.idempotency_key), indent=2))
            elif args.command == "end-run":
                print(json.dumps(client.end_run(args.workspace_id, run_id=args.run_id, agent_id=args.agent_id, status=args.run_end_status, reason=args.reasoning, _idempotency_key=args.idempotency_key), indent=2))
            elif args.command == "reasoning":
                print(json.dumps(client.reasoning(args.workspace_id, task_id=args.task_id, run_id=args.run_id), indent=2))
            elif args.command == "record-reasoning":
                print(json.dumps(client.record_reasoning(args.workspace_id, **common, run_id=args.run_id, kind=args.reasoning_kind, summary=args.summary, rationale=args.reasoning, source_refs=list(args.source_ref or []), confidence=args.confidence), indent=2))
            elif args.command == "create-task":
                print(json.dumps(client.create_task(args.workspace_id, **common, title=args.title, reasoning=args.reasoning, status=args.task_status or "backlog", priority=args.priority or "medium", owner=args.owner or "", acceptance_criteria=list(args.acceptance or []), constraints=list(args.constraint or []), depends_on=list(args.depends_on or []), linked_artifacts=list(args.linked_artifact or []), source_refs=list(args.source_ref or []), parent_task_id=args.parent_task_id or ""), indent=2))
            elif args.command == "update-task":
                print(json.dumps(client.update_task(args.workspace_id, **common, reasoning=args.reasoning, status=args.task_status, priority=args.priority, owner=args.owner, acceptance_criteria=args.acceptance, constraints=args.constraint, depends_on=args.depends_on, linked_artifacts=args.linked_artifact, source_refs=args.source_ref, parent_task_id=args.parent_task_id), indent=2))
            elif args.command == "claim":
                print(json.dumps(client.claim(args.workspace_id, **common, intent=args.intent, claimed_paths=list(args.claimed_path or []), run_id=args.run_id), indent=2))
            elif args.command == "handoff":
                print(json.dumps(client.handoff(args.workspace_id, **common, summary=args.summary, reasoning=args.reasoning, next_action=args.next_action), indent=2))
            elif args.command == "decision":
                print(json.dumps(client.decision(args.workspace_id, **common, summary=args.summary, reasoning=args.reasoning), indent=2))
            elif args.command == "verify":
                print(json.dumps(client.verify(args.workspace_id, **common, test_name=args.test_name, result=args.result, evidence_ref=args.evidence_ref, notes=args.notes, command_or_protocol=args.command_or_protocol), indent=2))
            elif args.command == "blocker":
                print(json.dumps(client.blocker(args.workspace_id, **common, reason=args.reasoning, next_action=args.next_action), indent=2))
            elif args.command == "complete":
                print(json.dumps(client.complete(args.workspace_id, **common, summary=args.summary, reasoning=args.reasoning, files_touched=list(args.file_touched or []), commands_run=list(args.command_run or []), residual_risks=list(args.residual_risk or [])), indent=2))
            elif args.command == "resolve-blocker":
                print(json.dumps(client.resolve_blocker(args.workspace_id, blocker_id=args.blocker_id, agent_id=args.agent_id, surface=args.surface, session_id=args.session_id, reasoning=args.reasoning), indent=2))
            else:
                print(json.dumps(client.gate(args.workspace_id), indent=2))
        except WorkspaceClientError as exc:
            print(f"workspace service error: {exc}", file=sys.stderr)
            return 2
        return 0

    if args.command == "status":
        print(render_workspace_status(root, args.workspace_id))
        return 0

    if args.command == "tasks":
        print(render_workspace_tasks(root, args.workspace_id))
        return 0

    if args.command == "context":
        print(json.dumps(assemble_workspace_context_packet(root, args.workspace_id, task_id=args.task_id, agent_id=args.agent_id, surface=args.surface, session_id=args.session_id), indent=2))
        return 0

    if args.command == "progress":
        print(json.dumps(derive_workspace_task_progress(root, args.workspace_id, task_id=args.task_id), indent=2))
        return 0

    if args.command == "runs":
        print(json.dumps({"workspace_id": args.workspace_id, "runs": list_workspace_runs(root, args.workspace_id, task_id=args.task_id)}, indent=2))
        return 0

    if args.command == "begin-run":
        print(json.dumps(begin_workspace_run(root, args.workspace_id, task_id=args.task_id, agent_id=args.agent_id, device_id=args.device_id, surface=args.surface, session_id=args.session_id, intent=args.intent, source_revision=args.source_revision, heartbeat_ttl_seconds=args.heartbeat_ttl_seconds, run_id=args.run_id, claimed_paths=list(args.claimed_path or [])), indent=2))
        return 0

    if args.command == "heartbeat-run":
        print(json.dumps(heartbeat_workspace_run(root, args.workspace_id, run_id=args.run_id, agent_id=args.agent_id), indent=2))
        return 0

    if args.command == "end-run":
        print(json.dumps(end_workspace_run(root, args.workspace_id, run_id=args.run_id, agent_id=args.agent_id, status=args.run_end_status, reason=args.reasoning), indent=2))
        return 0

    if args.command == "reasoning":
        print(json.dumps({"workspace_id": args.workspace_id, "reasoning": list_workspace_reasoning(root, args.workspace_id, task_id=args.task_id, run_id=args.run_id)}, indent=2))
        return 0

    if args.command == "record-reasoning":
        print(json.dumps(record_workspace_reasoning(root, args.workspace_id, task_id=args.task_id, agent_id=args.agent_id, surface=args.surface, session_id=args.session_id, run_id=args.run_id, kind=args.reasoning_kind, summary=args.summary, rationale=args.reasoning, source_refs=list(args.source_ref or []), confidence=args.confidence), indent=2))
        return 0

    if args.command == "prepare":
        print(
            json.dumps(
                prepare_workspace_task(
                    root,
                    args.workspace_id,
                    task_id=args.task_id,
                    agent_id=args.agent_id,
                    surface=args.surface,
                    session_id=args.session_id,
                ),
                indent=2,
            )
        )
        return 0

    if args.command == "create-task":
        print(json.dumps(create_workspace_task(root, args.workspace_id, task_id=args.task_id, agent_id=args.agent_id, surface=args.surface, session_id=args.session_id, title=args.title, reasoning=args.reasoning, status=args.task_status or "backlog", priority=args.priority or "medium", owner=args.owner or "", acceptance_criteria=list(args.acceptance or []), constraints=list(args.constraint or []), depends_on=list(args.depends_on or []), linked_artifacts=list(args.linked_artifact or []), source_refs=list(args.source_ref or []), parent_task_id=args.parent_task_id or ""), indent=2))
        return 0

    if args.command == "update-task":
        print(json.dumps(update_workspace_task(root, args.workspace_id, task_id=args.task_id, agent_id=args.agent_id, surface=args.surface, session_id=args.session_id, reasoning=args.reasoning, status=args.task_status, priority=args.priority, owner=args.owner, acceptance_criteria=args.acceptance, constraints=args.constraint, depends_on=args.depends_on, linked_artifacts=args.linked_artifact, source_refs=args.source_ref, parent_task_id=args.parent_task_id), indent=2))
        return 0

    if args.command == "claim":
        print(
            json.dumps(
                claim_workspace_task(
                    root,
                    args.workspace_id,
                    task_id=args.task_id,
                    agent_id=args.agent_id,
                    surface=args.surface,
                    session_id=args.session_id,
                    intent=args.intent,
                    claimed_paths=list(args.claimed_path or []),
                    run_id=args.run_id,
                ),
                indent=2,
            )
        )
        return 0

    if args.command == "decision":
        print(
            json.dumps(
                record_workspace_decision(
                    root,
                    args.workspace_id,
                    task_id=args.task_id,
                    agent_id=args.agent_id,
                    surface=args.surface,
                    session_id=args.session_id,
                    summary=args.summary,
                    reasoning=args.reasoning,
                ),
                indent=2,
            )
        )
        return 0

    if args.command == "verify":
        print(
            json.dumps(
                record_workspace_test_run(
                    root,
                    args.workspace_id,
                    task_id=args.task_id,
                    agent_id=args.agent_id,
                    surface=args.surface,
                    session_id=args.session_id,
                    test_name=args.test_name,
                    result=args.result,
                    evidence_ref=args.evidence_ref,
                    notes=args.notes,
                    command_or_protocol=args.command_or_protocol,
                ),
                indent=2,
            )
        )
        return 0

    if args.command == "blocker":
        print(
            json.dumps(
                record_workspace_blocker(
                    root,
                    args.workspace_id,
                    task_id=args.task_id,
                    agent_id=args.agent_id,
                    surface=args.surface,
                    session_id=args.session_id,
                    reason=args.reasoning,
                    next_action=args.next_action,
                ),
                indent=2,
            )
        )
        return 0

    if args.command == "complete":
        print(
            json.dumps(
                complete_workspace_task(
                    root,
                    args.workspace_id,
                    task_id=args.task_id,
                    agent_id=args.agent_id,
                    surface=args.surface,
                    session_id=args.session_id,
                    summary=args.summary,
                    reasoning=args.reasoning,
                    files_touched=list(args.file_touched or []),
                    commands_run=list(args.command_run or []),
                    residual_risks=list(args.residual_risk or []),
                ),
                indent=2,
            )
        )
        return 0

    if args.command == "resolve-blocker":
        print(json.dumps(resolve_workspace_blocker(root, args.workspace_id, blocker_id=args.blocker_id, agent_id=args.agent_id, surface=args.surface, session_id=args.session_id, reasoning=args.reasoning), indent=2))
        return 0

    if args.command == "gate":
        print(json.dumps(evaluate_workspace_release_gate(root, args.workspace_id), indent=2))
        return 0

    if args.command == "atlas":
        git_change_report = {}
        if args.git_changes_path:
            git_change_report = json.loads(Path(args.git_changes_path).read_text(encoding="utf-8"))
        print(
            json.dumps(
                materialize_workspace_atlas(
                    root,
                    args.workspace_id,
                    git_change_report=git_change_report,
                ),
                indent=2,
            )
        )
        return 0

    print(
        json.dumps(
            release_workspace_task_claims(
                root,
                args.workspace_id,
                task_id=args.task_id,
                agent_id=args.agent_id,
                surface=args.surface,
                session_id=args.session_id,
                summary=args.summary,
                reasoning=args.reasoning,
                next_action=args.next_action,
            ),
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
