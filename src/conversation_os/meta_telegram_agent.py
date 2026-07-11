from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict
from urllib import error, request

from .storage import append_jsonl, ensure_dir, read_json, utc_now, write_json
from .workspace_atlas import materialize_workspace_atlas
from .workspace_coordination import append_workspace_activity_event
from .workspace_coordination import evaluate_workspace_release_gate


MODULE_ID = "surface.inner_world.meta_telegram_agent"
CONTRACT_VERSION = "1.0"
PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "MetaCommand",
    "apply_packet_decision",
    "build_meta_chat_payload",
    "build_meta_telegram_reply",
    "classify_meta_command",
    "create_workspace_paths",
    "execute_release_deploy",
    "evaluate_release_readiness",
    "extract_telegram_message",
    "parse_release_approval",
    "parse_workspace_blocker",
    "parse_workspace_blocker_resolution",
    "parse_workspace_decision",
    "parse_workspace_claim",
    "parse_workspace_complete",
    "parse_workspace_gate",
    "parse_workspace_handoff",
    "parse_workspace_verify",
    "parse_workspace_task_create",
    "parse_workspace_task_update",
    "persist_meta_packet",
    "read_telegram_offset",
    "record_inbox_event",
    "record_outbox_event",
    "render_rollback_status_reply",
    "render_meta_status_reply",
    "release_is_approved",
    "save_telegram_offset",
    "read_selected_workspace",
    "save_selected_workspace",
    "triage_packet_to_workboard",
)
__all__ = list(PUBLIC_API)


def _get_json(url: str) -> Dict[str, Any]:
    with request.urlopen(url) as response:
        return json.loads(response.read().decode("utf-8"))


def _workspace_gate_from_service(workspace_api_base: str, workspace_id: str) -> Dict[str, Any]:
    base = workspace_api_base.rstrip("/")
    return _get_json(f"{base}/workspaces/{workspace_id}/gate")


@dataclass(frozen=True)
class MetaCommand:
    command: str
    text: str
    meta_state: str


def classify_meta_command(raw_text: str) -> MetaCommand:
    text = raw_text.strip()
    if not text:
        return MetaCommand(command="meta", text="", meta_state="discuss")
    if text.startswith("/change"):
        return MetaCommand(
            command="change",
            text=text[len("/change") :].strip(),
            meta_state="operate",
        )
    if text.startswith("/meta"):
        return MetaCommand(
            command="meta",
            text=text[len("/meta") :].strip(),
            meta_state="discuss",
        )
    if text.startswith("/deploy"):
        return MetaCommand(
            command="deploy",
            text=text[len("/deploy") :].strip(),
            meta_state="operate",
        )
    if text.startswith("/rollback"):
        return MetaCommand(
            command="rollback",
            text=text[len("/rollback") :].strip(),
            meta_state="operate",
        )
    if text.startswith("/approve"):
        return MetaCommand(
            command="approve",
            text=text[len("/approve") :].strip(),
            meta_state="operate",
        )
    if text.startswith("/reject"):
        return MetaCommand(
            command="reject",
            text=text[len("/reject") :].strip(),
            meta_state="operate",
        )
    if text.startswith("/status"):
        return MetaCommand(
            command="status",
            text=text[len("/status") :].strip(),
            meta_state="discuss",
        )
    if text.startswith("/workspace"):
        return MetaCommand(
            command="workspace",
            text=text[len("/workspace") :].strip(),
            meta_state="discuss",
        )
    if text.startswith("/tasks"):
        return MetaCommand(
            command="tasks",
            text=text[len("/tasks") :].strip(),
            meta_state="discuss",
        )
    if text.startswith("/context"):
        return MetaCommand(
            command="context",
            text=text[len("/context") :].strip(),
            meta_state="discuss",
        )
    if text.startswith("/task-update"):
        return MetaCommand(
            command="task-update",
            text=text[len("/task-update") :].strip(),
            meta_state="operate",
        )
    if text.startswith("/task"):
        return MetaCommand(
            command="task",
            text=text[len("/task") :].strip(),
            meta_state="operate",
        )
    if text.startswith("/claim"):
        return MetaCommand(
            command="claim",
            text=text[len("/claim") :].strip(),
            meta_state="operate",
        )
    if text.startswith("/handoff"):
        return MetaCommand(
            command="handoff",
            text=text[len("/handoff") :].strip(),
            meta_state="operate",
        )
    if text.startswith("/complete"):
        return MetaCommand(
            command="complete",
            text=text[len("/complete") :].strip(),
            meta_state="operate",
        )
    if text.startswith("/decision"):
        return MetaCommand(
            command="decision",
            text=text[len("/decision") :].strip(),
            meta_state="operate",
        )
    if text.startswith("/verify"):
        return MetaCommand(
            command="verify",
            text=text[len("/verify") :].strip(),
            meta_state="operate",
        )
    if text.startswith("/blocker"):
        return MetaCommand(
            command="blocker",
            text=text[len("/blocker") :].strip(),
            meta_state="operate",
        )
    if text.startswith("/resolve"):
        return MetaCommand(
            command="resolve",
            text=text[len("/resolve") :].strip(),
            meta_state="operate",
        )
    if text.startswith("/gate"):
        return MetaCommand(
            command="gate",
            text=text[len("/gate") :].strip(),
            meta_state="discuss",
        )
    return MetaCommand(command="meta", text=text, meta_state="discuss")


def build_meta_chat_payload(
    *,
    text: str,
    meta_state: str,
    chat_id: str,
    update_id: str,
    user_id: str,
    message_id: str,
) -> Dict[str, Any]:
    return {
        "text": text,
        "surface_mode": "meta",
        "meta_state": meta_state,
        "session_id": f"telegram:{chat_id}",
        "turn_id": f"telegram:{update_id}",
        "source": {
            "channel": "telegram",
            "from_user_id": user_id,
            "message_id": message_id,
        },
    }


def build_meta_telegram_reply(payload: Dict[str, Any]) -> str:
    assistant_text = str(payload.get("assistant_text") or "").strip() or "No assistant response."
    interpretation = payload.get("interpretation", {}) or {}
    packet = payload.get("packet") or {}
    if interpretation.get("builder_phase"):
        lines = [assistant_text]
        if packet.get("packet_id"):
            lines.extend(["", f"Packet: {packet['packet_id']}"])
        return "\n".join(lines)
    lines = [
        assistant_text,
        "",
        f"Mode: {interpretation.get('meta_state', 'discuss')}",
        f"Domain: {interpretation.get('domain', 'unknown')}",
        f"Risk: {interpretation.get('risk', 'unknown')}",
    ]
    if packet.get("packet_id"):
        lines.append(f"Packet: {packet['packet_id']}")
    return "\n".join(lines)


def parse_release_approval(text: str) -> Dict[str, str] | None:
    raw = text.strip()
    if not raw:
        return None
    packet_part, separator, release_part = raw.partition(" for release ")
    if not separator:
        return None
    packet_id = packet_part.strip()
    release_id = release_part.strip()
    if not packet_id or not release_id:
        return None
    return {"packet_id": packet_id, "release_id": release_id}


def parse_workspace_claim(text: str) -> Dict[str, Any] | None:
    parts = [segment.strip() for segment in text.split("::")]
    if len(parts) < 3:
        return None
    task_id = parts[0]
    intent = parts[1]
    claimed_paths = [item.strip() for item in "::".join(parts[2:]).split(",") if item.strip()]
    if not task_id or not intent or not claimed_paths:
        return None
    return {
        "task_id": task_id,
        "intent": intent,
        "claimed_paths": claimed_paths,
    }


def parse_workspace_gate(text: str) -> Dict[str, str]:
    return {"workspace_id": str(text or "").strip()}


def parse_workspace_handoff(text: str) -> Dict[str, str] | None:
    parts = [segment.strip() for segment in text.split("::")]
    if len(parts) < 3:
        return None
    task_id = parts[0]
    summary = parts[1]
    reasoning = parts[2]
    next_action = parts[3] if len(parts) > 3 else ""
    if not task_id or not summary or not reasoning:
        return None
    return {
        "task_id": task_id,
        "summary": summary,
        "reasoning": reasoning,
        "next_action": next_action,
    }


def parse_workspace_decision(text: str) -> Dict[str, str] | None:
    parts = [segment.strip() for segment in text.split("::")]
    if len(parts) < 3:
        return None
    task_id, summary, reasoning = parts[:3]
    if not task_id or not summary or not reasoning:
        return None
    return {
        "task_id": task_id,
        "summary": summary,
        "reasoning": reasoning,
    }


def parse_workspace_complete(text: str) -> Dict[str, Any] | None:
    parts = [segment.strip() for segment in text.split("::")]
    if len(parts) != 6:
        return None
    task_id, summary, reasoning, files_raw, commands_raw, risks_raw = parts
    files_touched = [item.strip() for item in files_raw.split(",") if item.strip()]
    commands_run = [item.strip() for item in commands_raw.split(";;") if item.strip()]
    residual_risks = [item.strip() for item in risks_raw.split(",") if item.strip()]
    if not task_id or not summary or not reasoning or not files_touched or not commands_run or not residual_risks:
        return None
    return {
        "task_id": task_id,
        "summary": summary,
        "reasoning": reasoning,
        "files_touched": files_touched,
        "commands_run": commands_run,
        "residual_risks": residual_risks,
    }


def parse_workspace_verify(text: str) -> Dict[str, str] | None:
    parts = [segment.strip() for segment in text.split("::")]
    if len(parts) < 3:
        return None
    task_id = parts[0]
    test_name = parts[1]
    result = parts[2]
    evidence_ref = parts[3] if len(parts) > 3 else ""
    notes = parts[4] if len(parts) > 4 else ""
    if not task_id or not test_name or not result:
        return None
    return {
        "task_id": task_id,
        "test_name": test_name,
        "result": result,
        "evidence_ref": evidence_ref,
        "notes": notes,
    }


def parse_workspace_blocker(text: str) -> Dict[str, str] | None:
    parts = [segment.strip() for segment in text.split("::")]
    if len(parts) < 2:
        return None
    task_id = parts[0]
    reason = parts[1]
    next_action = parts[2] if len(parts) > 2 else ""
    if not task_id or not reason:
        return None
    return {
        "task_id": task_id,
        "reason": reason,
        "next_action": next_action,
    }


def parse_workspace_task_create(text: str) -> Dict[str, Any] | None:
    parts = [segment.strip() for segment in text.split("::")]
    if len(parts) not in {4, 5}:
        return None
    task_id, title, criteria_raw, reasoning = parts[:4]
    parent_task_id = parts[4] if len(parts) == 5 else ""
    criteria = [item.strip() for item in criteria_raw.split(",") if item.strip()]
    if not task_id or not title or not criteria or not reasoning:
        return None
    return {
        "task_id": task_id,
        "title": title,
        "acceptance_criteria": criteria,
        "reasoning": reasoning,
        "parent_task_id": parent_task_id,
    }


def parse_workspace_task_update(text: str) -> Dict[str, str] | None:
    parts = [segment.strip() for segment in text.split("::")]
    if len(parts) != 3:
        return None
    task_id, status, reasoning = parts
    if not task_id or not status or not reasoning:
        return None
    return {"task_id": task_id, "status": status, "reasoning": reasoning}


def parse_workspace_blocker_resolution(text: str) -> Dict[str, str] | None:
    parts = [segment.strip() for segment in text.split("::")]
    if len(parts) != 2 or not parts[0] or not parts[1]:
        return None
    return {"blocker_id": parts[0], "reasoning": parts[1]}


def read_telegram_offset(root: Path) -> int:
    payload = read_json(create_workspace_paths(root)["telegram_offset"], default={}) or {}
    try:
        return int(payload.get("offset", 0))
    except (TypeError, ValueError):
        return 0


def save_telegram_offset(root: Path, offset: int) -> None:
    write_json(
        create_workspace_paths(root)["telegram_offset"],
        {"offset": int(offset), "updated_at": utc_now()},
    )


def extract_telegram_message(update: Dict[str, Any], *, allowed_user_ids: set[int]) -> Dict[str, str] | None:
    message = update.get("message") or update.get("edited_message") or {}
    text = str(message.get("text") or "").strip()
    from_user = message.get("from") or {}
    chat = message.get("chat") or {}
    user_id_raw = from_user.get("id")
    if not text or user_id_raw is None:
        return None
    try:
        user_id = int(user_id_raw)
    except (TypeError, ValueError):
        return None
    if allowed_user_ids and user_id not in allowed_user_ids:
        return None
    return {
        "text": text,
        "chat_id": str(chat.get("id", "")),
        "update_id": str(update.get("update_id", "")),
        "user_id": str(user_id),
        "message_id": str(message.get("message_id", "")),
    }


def create_workspace_paths(root: Path) -> Dict[str, Path]:
    return {
        "state": root / "state",
        "active_packets": root / "state" / "active_packets.json",
        "approval_state": root / "state" / "approval_state.json",
        "builder_sessions": root / "state" / "builder_sessions",
        "deployment_state": root / "state" / "deployment_state.json",
        "selected_workspace": root / "state" / "selected_workspace.json",
        "telegram_offset": root / "state" / "telegram_update_offset.json",
        "inbox": root / "inbox" / "telegram.jsonl",
        "outbox": root / "outbox" / "telegram.jsonl",
        "agent_events": root / "logs" / "agent_events.jsonl",
        "packets_proposed": root / "packets" / "proposed",
        "packets_approved": root / "packets" / "approved",
        "packets_rejected": root / "packets" / "rejected",
    }


def _packet_dir(paths: Dict[str, Path], status: str) -> Path:
    if status == "approved":
        return paths["packets_approved"]
    if status == "rejected":
        return paths["packets_rejected"]
    return paths["packets_proposed"]


def _load_active_packets(path: Path) -> Dict[str, Any]:
    payload = read_json(path, default=None)
    if isinstance(payload, dict) and isinstance(payload.get("packets"), list):
        return payload
    return {"updated_at": "", "packets": []}


def _upsert_active_packet(path: Path, packet: Dict[str, Any]) -> None:
    payload = _load_active_packets(path)
    packets = [row for row in payload["packets"] if row.get("packet_id") != packet["packet_id"]]
    packets.append(packet)
    payload["updated_at"] = utc_now()
    payload["packets"] = sorted(packets, key=lambda row: row.get("packet_id", ""))
    write_json(path, payload)


def _remove_active_packet(path: Path, packet_id: str) -> None:
    payload = _load_active_packets(path)
    payload["updated_at"] = utc_now()
    payload["packets"] = [row for row in payload["packets"] if row.get("packet_id") != packet_id]
    write_json(path, payload)


def record_inbox_event(root: Path, payload: Dict[str, Any]) -> None:
    paths = create_workspace_paths(root)
    append_jsonl(paths["inbox"], payload)


def record_outbox_event(root: Path, payload: Dict[str, Any]) -> None:
    paths = create_workspace_paths(root)
    append_jsonl(paths["outbox"], payload)


def read_builder_session_state(root: Path, session_id: str) -> Dict[str, Any]:
    if not session_id:
        return {}
    path = create_workspace_paths(root)["builder_sessions"] / f"{session_id.replace('/', '_')}.json"
    payload = read_json(path, default={}) or {}
    if isinstance(payload, dict):
        return dict(payload.get("builder_state") or {})
    return {}


def save_builder_session_state(root: Path, session_id: str, builder_state: Dict[str, Any]) -> None:
    if not session_id:
        return
    path = create_workspace_paths(root)["builder_sessions"] / f"{session_id.replace('/', '_')}.json"
    ensure_dir(path.parent)
    write_json(
        path,
        {
            "session_id": session_id,
            "updated_at": utc_now(),
            "builder_state": builder_state,
        },
    )


def persist_meta_packet(root: Path, packet: Dict[str, Any], *, status: str = "proposed") -> Dict[str, Any]:
    paths = create_workspace_paths(root)
    resolved = dict(packet)
    resolved["status"] = status
    packet_id = str(resolved["packet_id"])
    packet_path = _packet_dir(paths, status) / f"{packet_id}.json"
    ensure_dir(packet_path.parent)
    write_json(packet_path, resolved)
    if status == "proposed":
        _upsert_active_packet(
            paths["active_packets"],
            {
                "packet_id": packet_id,
                "status": status,
                "domain": resolved.get("classification", {}).get("domain", "unknown"),
                "risk": resolved.get("classification", {}).get("risk", "unknown"),
                "summary": resolved.get("proposal", {}).get("summary", ""),
                "updated_at": utc_now(),
            },
        )
    else:
        _remove_active_packet(paths["active_packets"], packet_id)
    return resolved


def _find_packet(paths: Dict[str, Path], packet_id: str) -> tuple[Path, Dict[str, Any]]:
    for status in ("proposed", "approved", "rejected"):
        candidate = _packet_dir(paths, status) / f"{packet_id}.json"
        payload = read_json(candidate, default=None)
        if isinstance(payload, dict):
            return candidate, payload
    raise FileNotFoundError(packet_id)


def apply_packet_decision(
    root: Path,
    packet_id: str,
    *,
    decision: str,
    actor: str,
    release_id: str = "",
) -> Dict[str, Any]:
    paths = create_workspace_paths(root)
    source_path, payload = _find_packet(paths, packet_id)
    resolved = dict(payload)
    resolved["status"] = decision
    resolved["approval"] = {
        "actor": actor,
        "decision": decision,
        "created_at": utc_now(),
    }
    if release_id:
        resolved["approval"]["release_id"] = release_id
    target_path = _packet_dir(paths, decision) / f"{packet_id}.json"
    ensure_dir(target_path.parent)
    if source_path != target_path and source_path.exists():
        source_path.unlink()
    write_json(target_path, resolved)
    approval_payload = {
        "packet_id": packet_id,
        "actor": actor,
        "decision": decision,
        "updated_at": utc_now(),
    }
    if isinstance(resolved.get("approval"), dict) and resolved["approval"].get("release_id"):
        approval_payload["release_id"] = resolved["approval"]["release_id"]
    write_json(paths["approval_state"], approval_payload)
    if decision == "proposed":
        _upsert_active_packet(
            paths["active_packets"],
            {
                "packet_id": packet_id,
                "status": decision,
                "domain": resolved.get("classification", {}).get("domain", "unknown"),
                "risk": resolved.get("classification", {}).get("risk", "unknown"),
                "summary": resolved.get("proposal", {}).get("summary", ""),
                "updated_at": utc_now(),
            },
        )
    else:
        _remove_active_packet(paths["active_packets"], packet_id)
    return resolved


def render_meta_status_reply(root: Path) -> str:
    payload = _load_active_packets(create_workspace_paths(root)["active_packets"])
    packets = payload["packets"]
    if not packets:
        return "No active packets."
    label = "packet" if len(packets) == 1 else "packets"
    lines = [f"{len(packets)} active {label}:"]
    for row in packets:
        lines.append(
            f"- {row.get('packet_id', 'unknown')} [{row.get('status', 'unknown')}] "
            f"{row.get('domain', 'unknown')} · {row.get('risk', 'unknown')}"
        )
    return "\n".join(lines)


def read_selected_workspace(root: Path) -> str:
    payload = read_json(create_workspace_paths(root)["selected_workspace"], default={}) or {}
    return str(payload.get("workspace_id", "") or "").strip()


def save_selected_workspace(root: Path, workspace_id: str) -> None:
    write_json(
        create_workspace_paths(root)["selected_workspace"],
        {
            "workspace_id": str(workspace_id or "").strip(),
            "updated_at": utc_now(),
        },
    )


def release_is_approved(root: Path, release_id: str) -> bool:
    payload = read_json(create_workspace_paths(root)["approval_state"], default={}) or {}
    return payload.get("decision") == "approved" and payload.get("release_id") == release_id


def triage_packet_to_workboard(root: Path, packet: Dict[str, Any], *, actor: str) -> Dict[str, Any]:
    board_root = root / "docs" / "workboards" / "inner-space-agent-ops"
    inbox_dir = ensure_dir(board_root / "inbox")
    tasks_dir = ensure_dir(board_root / "tasks")
    packet_id = str(packet["packet_id"])
    task_id = packet_id.upper()
    write_json(inbox_dir / f"{packet_id}.json", packet)
    task_path = tasks_dir / f"{task_id}.md"
    summary = packet.get("proposal", {}).get("summary", "")
    observed = packet.get("problem", {}).get("observed", "")
    tests = packet.get("gates", {}).get("required_tests", [])
    acceptance_lines = [f"- {item}" for item in tests] if tests else ["- TBD"]
    task_lines = [
        f"# {task_id}: {summary or packet_id}",
        "",
        "Status: backlog",
        f"Owner: {actor}",
        "Current gate: intake",
        "",
        "## Problem",
        "",
        observed or "TBD",
        "",
        "## Scope",
        "",
        "In:",
        "",
        f"- {summary or 'TBD'}",
        "",
        "Out:",
        "",
        "- Deploy without gates.",
        "",
        "## Acceptance Criteria",
        "",
        *acceptance_lines,
        "",
        "## Verification Evidence",
        "",
        "- Not run yet.",
        "",
        "## Updates",
        "",
        f"- Triaged from packet `{packet_id}` by `{actor}` at `{utc_now()}`.",
    ]
    task_body = "\n".join(task_lines)
    task_path.write_text(task_body + "\n", encoding="utf-8")
    append_jsonl(
        board_root / "UPDATES.jsonl",
        {
            "timestamp": utc_now(),
            "actor": actor,
            "event": "packet_triaged",
            "packet_id": packet_id,
            "task_id": task_id,
        },
    )
    return {"task_id": task_id, "task_path": str(task_path)}


def evaluate_release_readiness(root: Path, release_id: str, *, workspace_api_base: str = "") -> Dict[str, Any]:
    release_dir = root / "product" / "inner_world_v1" / "releases" / release_id
    manifest = read_json(release_dir / "manifest.json", default={}) or {}
    workspace_id = str(manifest.get("workspace_id", "") or "")
    required = {
        "manifest": release_dir / "manifest.json",
        "gate_report": release_dir / "gate_report.json",
        "rollback_plan": release_dir / "rollback_plan.json",
    }
    missing = [name for name, path in required.items() if not path.exists()]
    workspace_gate = {}
    if workspace_id and not missing:
        try:
            if workspace_api_base:
                workspace_gate = _workspace_gate_from_service(workspace_api_base, workspace_id)
            else:
                workspace_gate = evaluate_workspace_release_gate(root, workspace_id)
        except FileNotFoundError:
            workspace_gate = {"status": "blocked", "reasons": ["workspace_not_found"]}
        except (error.URLError, error.HTTPError):
            workspace_gate = evaluate_workspace_release_gate(root, workspace_id)
        if workspace_gate.get("status") != "ready":
            missing.append("workspace_gate")
    return {
        "release_id": release_id,
        "status": "ready" if not missing else "blocked",
        "missing": missing,
        "workspace_id": workspace_id,
        "workspace_gate": workspace_gate,
        "paths": {name: str(path) for name, path in required.items()},
    }


def _release_dir(root: Path, release_id: str) -> Path:
    return root / "product" / "inner_world_v1" / "releases" / release_id


def _deploy_commands(root: Path, release_id: str) -> list[list[str]]:
    gate_report = _release_dir(root, release_id) / "gate_report.json"
    return [
        [
            "python3",
            "tools/deploy_inner_world_to_openclaw.py",
            "--release-gate-report",
            str(gate_report),
        ],
        [
            "python3",
            "tools/deploy_thought_capture_pwa_to_openclaw.py",
            "--release-gate-report",
            str(gate_report),
        ],
    ]


def execute_release_deploy(
    repo_root: Path,
    workspace_root: Path,
    release_id: str,
    *,
    workspace_api_base: str = "",
) -> Dict[str, Any]:
    readiness = evaluate_release_readiness(repo_root, release_id, workspace_api_base=workspace_api_base)
    if readiness["missing"]:
        result = {
            "release_id": release_id,
            "status": "blocked",
            "reason": "workspace_gate_blocked" if "workspace_gate" in readiness["missing"] else "missing_release_artifacts",
            "missing": list(readiness["missing"]),
            "workspace_id": readiness.get("workspace_id", ""),
            "workspace_gate": dict(readiness.get("workspace_gate", {}) or {}),
            "updated_at": utc_now(),
        }
        write_json(create_workspace_paths(workspace_root)["deployment_state"], result)
        return result

    commands = _deploy_commands(repo_root, release_id)
    logs: list[dict[str, Any]] = []
    for command in commands:
        completed = subprocess.run(
            command,
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        logs.append(
            {
                "command": command,
                "returncode": completed.returncode,
                "stdout": completed.stdout.strip(),
                "stderr": completed.stderr.strip(),
            }
        )
        if completed.returncode != 0:
            result = {
                "release_id": release_id,
                "status": "failed",
                "reason": "deploy_command_failed",
                "logs": logs,
                "updated_at": utc_now(),
            }
            write_json(create_workspace_paths(workspace_root)["deployment_state"], result)
            return result

    smoke = {
        "schema_version": "1.0",
        "release_id": release_id,
        "status": "passed",
        "executed_at": utc_now(),
        "commands": [{"command": row["command"], "returncode": row["returncode"]} for row in logs],
    }
    write_json(_release_dir(repo_root, release_id) / "post_deploy_smoke.json", smoke)
    result = {
        "release_id": release_id,
        "status": "deployed",
        "logs": logs,
        "post_deploy_smoke_path": str(_release_dir(repo_root, release_id) / "post_deploy_smoke.json"),
        "workspace_id": readiness.get("workspace_id", ""),
        "updated_at": utc_now(),
    }
    workspace_id = str(readiness.get("workspace_id", "") or "")
    if workspace_id:
        append_workspace_activity_event(
            repo_root,
            workspace_id,
            task_id="",
            agent_id="system:deploy",
            surface="deploy",
            session_id=f"release:{release_id}",
            event_type="deployed",
            summary=f"Deployed release {release_id}",
            reasoning="Release gate passed and deploy commands completed successfully.",
            verification=[result["post_deploy_smoke_path"]],
            metadata={
                "release_id": release_id,
                "post_deploy_smoke_path": result["post_deploy_smoke_path"],
            },
        )
        materialize_workspace_atlas(repo_root, workspace_id)
    write_json(create_workspace_paths(workspace_root)["deployment_state"], result)
    return result


def render_rollback_status_reply(root: Path, release_id: str) -> str:
    release_dir = _release_dir(root, release_id)
    rollback_plan = read_json(release_dir / "rollback_plan.json", default=None)
    manifest = read_json(release_dir / "manifest.json", default=None)
    if not isinstance(rollback_plan, dict):
        return (
            f"Rollback for {release_id} is blocked.\n\n"
            "Mode: operate\nDomain: deployment_release\nRisk: critical\n"
            "Missing: rollback_plan"
        )
    target_release_id = str(rollback_plan.get("target_release_id") or "")
    if not target_release_id and isinstance(manifest, dict):
        target_release_id = str((manifest.get("rollback") or {}).get("previous_release_id") or "")
    steps = rollback_plan.get("steps") or []
    step_preview = ", ".join(str(step) for step in steps[:3]) if steps else "no steps declared"
    target_label = target_release_id or "unspecified target"
    return (
        f"Rollback plan for {release_id} is ready as a dry run.\n\n"
        "Mode: operate\nDomain: deployment_release\nRisk: critical\n"
        f"Target: {target_label}\n"
        f"Steps: {step_preview}\n"
        "Execution: rollback executor not wired yet"
    )
