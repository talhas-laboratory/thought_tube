from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
import sys
from pathlib import Path
from urllib import error, parse, request

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
tools_dir = str(Path(__file__).resolve().parent)
if tools_dir in sys.path:
    sys.path.remove(tools_dir)
    sys.path.append(tools_dir)

from conversation_os.meta_telegram_agent import (
    apply_packet_decision,
    build_meta_chat_payload,
    build_meta_telegram_reply,
    classify_meta_command,
    create_workspace_paths,
    execute_release_deploy,
    evaluate_release_readiness,
    extract_telegram_message,
    parse_release_approval,
    parse_workspace_blocker,
    parse_workspace_blocker_resolution,
    parse_workspace_decision,
    parse_workspace_claim,
    parse_workspace_complete,
    parse_workspace_gate,
    parse_workspace_handoff,
    parse_workspace_verify,
    parse_workspace_task_create,
    parse_workspace_task_update,
    persist_meta_packet,
    read_telegram_offset,
    record_inbox_event,
    record_outbox_event,
    render_rollback_status_reply,
    render_meta_status_reply,
    release_is_approved,
    read_selected_workspace,
    read_builder_session_state,
    save_telegram_offset,
    save_builder_session_state,
    save_selected_workspace,
    triage_packet_to_workboard,
)
from conversation_os.builder_behavior import build_builder_chat_response
from conversation_os.storage import append_jsonl, repo_root_from, utc_now
from conversation_os.workspace_context_packet import assemble_workspace_context_packet
from conversation_os.workspace_runs import begin_workspace_run, end_workspace_run, heartbeat_workspace_run
from conversation_os.workspace_coordination import (
    claim_workspace_task,
    complete_workspace_task,
    create_workspace_task,
    evaluate_workspace_release_gate,
    load_workspace_manifest,
    record_workspace_blocker,
    record_workspace_decision,
    record_workspace_test_run,
    release_workspace_task_claims,
    resolve_workspace_blocker,
    render_workspace_tasks,
    update_workspace_task,
)


def _get_json(url: str) -> dict:
    with request.urlopen(url) as response:
        return json.loads(response.read().decode("utf-8"))


def _post_json(url: str, payload: dict) -> dict:
    body = json.dumps(payload).encode("utf-8")
    req = request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with request.urlopen(req) as response:
        return json.loads(response.read().decode("utf-8"))


def _load_runtime_config(root: Path) -> dict:
    for candidate in (
        root / "product" / "inner_world_v1" / "config" / "runtime.json",
        root / "product" / "inner_world_v1" / "config" / "runtime.sample.json",
    ):
        if not candidate.exists():
            continue
        try:
            return json.loads(candidate.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
    return {}


def _resolve_telegram_meta_openclaw(root: Path) -> dict:
    config = _load_runtime_config(root)
    telegram_meta = dict(config.get("telegram_meta", {}) or {})
    openclaw = dict(config.get("openclaw", {}) or {})
    default_agent = openclaw.get("agent") or "main"
    return {
        "agent": os.getenv("INNER_SPACE_META_AGENT_ID") or telegram_meta.get("agent") or default_agent,
        "fallback_agent": default_agent,
        "thinking": os.getenv("INNER_WORLD_OPENCLAW_THINKING") or openclaw.get("thinking") or "low",
        "timeout_seconds": int(os.getenv("INNER_WORLD_OPENCLAW_TIMEOUT") or openclaw.get("timeout_seconds") or 60),
        "deliver": str(os.getenv("INNER_WORLD_OPENCLAW_DELIVER") or openclaw.get("deliver") or "false").lower()
        in {"1", "true", "yes", "on"},
    }


def _compose_meta_openclaw_message(*, text: str, builder_analysis: dict, workspace_context: dict) -> str:
    builder_state = dict(builder_analysis.get("builder_state", {}) or {})
    interpretation = dict(builder_analysis.get("interpretation", {}) or {})
    view = dict(builder_state.get("conversation_view", {}) or {})
    objective = str(builder_state.get("confirmed_objective") or builder_state.get("candidate_objective") or "").strip()
    missing = [str(item).strip() for item in list(view.get("missing_information", []) or []) if str(item).strip()]
    workspace_id = str(workspace_context.get("workspace_id") or "").strip()
    repository = dict(workspace_context.get("repository", {}) or {})
    changed_files = [str(item).strip() for item in list(repository.get("changed_files", []) or []) if str(item).strip()]
    return "\n".join(
        [
            "Inner Space Telegram meta conversation.",
            "Reply naturally and conversationally.",
            "Do not mention internal state machines, builder phases, packets, or workflow scaffolding unless the user explicitly asks for them or asks you to act.",
            "Use the analysis notes below as internal guidance only.",
            "",
            "Internal guidance:",
            f"- Probable objective: {objective or 'not stable yet'}",
            f"- Missing information: {', '.join(missing) if missing else 'none obvious'}",
            f"- Current domain guess: {interpretation.get('domain', 'unknown')}",
            f"- Objective confirmed: {bool(builder_state.get('objective_confirmed'))}",
            f"- Workspace: {workspace_id or 'none selected'}",
            f"- Changed files observed: {len(changed_files)}",
            "- If the user is exploring, answer the substance first and clarify gently.",
            "- If the goal becomes concrete, you may suggest turning it into scoped work.",
            "- Keep the tone like a normal capable collaborator.",
            "",
            f"User message: {text}",
        ]
    )


def _request_meta_openclaw_reply(
    *,
    root: Path,
    text: str,
    session_id: str,
    builder_analysis: dict,
    workspace_context: dict,
) -> str:
    settings = _resolve_telegram_meta_openclaw(root)
    message = _compose_meta_openclaw_message(
        text=text,
        builder_analysis=builder_analysis,
        workspace_context=workspace_context,
    )
    attempted_agents = []
    completed = None
    stdout = ""
    stderr = ""
    for agent_id in [settings["agent"], settings.get("fallback_agent", "")]:
        agent_id = str(agent_id or "").strip()
        if not agent_id or agent_id in attempted_agents:
            continue
        attempted_agents.append(agent_id)
        command = [
            "openclaw",
            "agent",
            "--session-id",
            session_id,
            "--agent",
            agent_id,
            "--message",
            message,
            "--thinking",
            settings["thinking"],
            "--json",
        ]
        if settings["deliver"]:
            command.append("--deliver")
        completed = subprocess.run(
            command,
            cwd=root,
            capture_output=True,
            text=True,
            timeout=settings["timeout_seconds"],
            check=False,
        )
        stdout = completed.stdout.strip()
        stderr = completed.stderr.strip()
        if completed.returncode == 0:
            break
        if "Unknown agent id" not in f"{stderr}\n{stdout}":
            raise RuntimeError(stderr or stdout or f"openclaw exited with code {completed.returncode}")
    if completed is None or completed.returncode != 0:
        raise RuntimeError(stderr or stdout or "openclaw reply failed")
    if not stdout:
        raise RuntimeError("openclaw returned an empty reply")
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError:
        return stdout
    result = payload.get("result") if isinstance(payload.get("result"), dict) else {}
    candidates = [
        payload.get("reply"),
        payload.get("text"),
        payload.get("content"),
        payload.get("message"),
        result.get("reply"),
        result.get("text"),
        result.get("content"),
        result.get("message"),
        result.get("finalAssistantVisibleText"),
        result.get("finalAssistantRawText"),
    ]
    payloads = result.get("payloads")
    if isinstance(payloads, list):
        for item in payloads:
            if not isinstance(item, dict):
                continue
            candidates.extend(
                [
                    item.get("text"),
                    item.get("content"),
                    item.get("message"),
                ]
            )
    top_payloads = payload.get("payloads")
    if isinstance(top_payloads, list):
        for item in top_payloads:
            if not isinstance(item, dict):
                continue
            candidates.extend(
                [
                    item.get("text"),
                    item.get("content"),
                    item.get("message"),
                ]
            )
    for candidate in candidates:
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
    return stdout


def _workspace_service_url(base_url: str, workspace_id: str, action: str, *, query: dict[str, str] | None = None) -> str:
    base = base_url.rstrip("/")
    url = f"{base}/workspaces/{workspace_id}/{action}"
    if query:
        url = f"{url}?{parse.urlencode(query)}"
    return url


def _read_workspace_git_change_report(root: Path, workspace_id: str) -> dict:
    atlas_json = root / "context" / "workspaces" / workspace_id / "atlas.json"
    if not atlas_json.exists():
        return {}
    try:
        payload = json.loads(atlas_json.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return dict(payload.get("git_changes", {}) or {})


def _resolve_builder_root(workspace_root: Path) -> Path:
    current = workspace_root.resolve()
    for candidate in [current, *current.parents]:
        if (candidate / "context" / "workspaces").exists():
            return candidate
    return repo_root_from(Path(__file__).resolve())


def _inspection_needs_gitnexus(workspace_context: dict) -> bool:
    repository = dict(workspace_context.get("repository", {}) or {})
    changed_files = list(repository.get("changed_files", []) or [])
    workspace = dict(workspace_context.get("workspace", {}) or {})
    artifact_roots = list(workspace.get("artifact_roots", []) or [])
    return len(changed_files) > 2 or len(artifact_roots) > 1


def _collect_builder_inspection(root: Path, workspace_id: str, workspace_context: dict) -> dict:
    task = dict((workspace_context.get("focus", {}) or {}).get("task", {}) or {})
    orientation = dict(workspace_context.get("orientation", {}) or {})
    repository = dict(workspace_context.get("repository", {}) or {})
    changed_files = [str(item).strip() for item in list(repository.get("changed_files", []) or []) if str(item).strip()]
    active_claims = list(orientation.get("active_claims", []) or [])
    blockers = list(orientation.get("blockers", []) or [])
    tests = list(orientation.get("tests", []) or [])
    git_changes = _read_workspace_git_change_report(root, workspace_id) if _inspection_needs_gitnexus(workspace_context) else {}
    affected_surfaces = []
    for item in list(git_changes.get("changed_symbols", []) or [])[:8]:
        label = str(item.get("filePath", "") or "").strip()
        if label and label not in affected_surfaces:
            affected_surfaces.append(label)
    for item in list(git_changes.get("affected_processes", []) or [])[:5]:
        label = str(item.get("name", "") or "").strip()
        if label and label not in affected_surfaces:
            affected_surfaces.append(label)
    return {
        "task_status": str(task.get("status", "") or ""),
        "artifact_roots": list((workspace_context.get("workspace", {}) or {}).get("artifact_roots", []) or []),
        "changed_files": changed_files[:20],
        "active_claim_count": len(active_claims),
        "blocker_count": len(blockers),
        "verification_gap": not any(str(row.get("latest_result", "") or "") == "passing" for row in tests),
        "completion_gap": str(task.get("status", "") or "") != "done",
        "gitnexus_used": bool(git_changes),
        "affected_surfaces": affected_surfaces[:8],
        "risk_level": str((git_changes.get("summary", {}) or {}).get("risk_level", "none") or "none"),
    }


def _builder_task_title(builder_state: dict) -> str:
    objective = str(builder_state.get("confirmed_objective") or builder_state.get("candidate_objective") or "").strip()
    if not objective:
        return "Builder-scoped change"
    return objective[:120]


def _create_builder_workspace_task(
    *,
    workspace_id: str,
    packet: dict,
    builder_state: dict,
    builder_scope: dict,
    user_id: str,
    chat_id: str,
    message_id: str,
    workspace_api_base: str,
) -> dict:
    task_id = str(packet.get("packet_id", "") or "").upper()
    payload = {
        "task_id": task_id,
        "agent_id": f"telegram:{user_id}",
        "surface": "telegram",
        "session_id": f"telegram:{chat_id}",
        "title": _builder_task_title(builder_state),
        "reasoning": str(builder_scope.get("summary") or builder_state.get("acceptance_criteria") or "Builder-scoped work.").strip(),
        "status": "ready",
        "priority": "high" if str(builder_scope.get("risk") or "") in {"high", "critical"} else "medium",
        "owner": "",
        "acceptance_criteria": [str(builder_state.get("acceptance_criteria") or "").strip()] if str(builder_state.get("acceptance_criteria") or "").strip() else ["Deliver the confirmed objective."],
        "constraints": [],
        "depends_on": [],
        "linked_artifacts": [],
        "source_refs": [f"telegram:message:{message_id}", f"packet:{packet.get('packet_id', '')}"],
    }
    if workspace_api_base:
        return _post_json(_workspace_service_url(workspace_api_base, workspace_id, "tasks"), payload)
    return create_workspace_task(
        repo_root_from(Path(__file__).resolve()),
        workspace_id,
        **payload,
    )


def _claim_builder_scope(
    *,
    workspace_id: str,
    task_id: str,
    builder_scope: dict,
    user_id: str,
    chat_id: str,
    workspace_api_base: str,
) -> dict | None:
    claimed_paths = [str(item).strip() for item in list(builder_scope.get("claimed_paths", []) or []) if str(item).strip()]
    if not claimed_paths:
        return None
    payload = {
        "task_id": task_id,
        "agent_id": f"telegram:{user_id}",
        "surface": "telegram",
        "session_id": f"telegram:{chat_id}",
        "intent": str(builder_scope.get("summary") or "Reserve builder scope paths.").strip(),
        "claimed_paths": claimed_paths,
        "ttl_seconds": 900,
    }
    try:
        if workspace_api_base:
            return _post_json(_workspace_service_url(workspace_api_base, workspace_id, "claim"), payload)
        return claim_workspace_task(
            repo_root_from(Path(__file__).resolve()),
            workspace_id,
            **payload,
        )
    except (ValueError, FileNotFoundError, error.URLError, error.HTTPError):
        return None


def _begin_builder_workspace_run(
    *,
    workspace_id: str,
    task_id: str,
    builder_scope: dict,
    user_id: str,
    chat_id: str,
    workspace_api_base: str,
) -> dict | None:
    claimed_paths = [str(item).strip() for item in list(builder_scope.get("claimed_paths", []) or []) if str(item).strip()]
    payload = {
        "task_id": task_id,
        "agent_id": f"telegram:{user_id}",
        "device_id": f"telegram-chat:{chat_id}",
        "surface": "telegram",
        "session_id": f"telegram:{chat_id}",
        "intent": str(builder_scope.get("summary") or "Begin builder-scoped work.").strip(),
        "claimed_paths": claimed_paths,
    }
    try:
        if workspace_api_base:
            return _post_json(_workspace_service_url(workspace_api_base, workspace_id, "runs"), payload)
        return begin_workspace_run(repo_root_from(Path(__file__).resolve()), workspace_id, **payload)
    except (ValueError, FileNotFoundError, error.URLError, error.HTTPError):
        return None


def _heartbeat_builder_workspace_run(
    *,
    workspace_id: str,
    run_id: str,
    user_id: str,
    workspace_api_base: str,
) -> dict | None:
    if not run_id:
        return None
    payload = {"run_id": run_id, "agent_id": f"telegram:{user_id}"}
    try:
        if workspace_api_base:
            return _post_json(_workspace_service_url(workspace_api_base, workspace_id, "run-heartbeat"), payload)
        return heartbeat_workspace_run(repo_root_from(Path(__file__).resolve()), workspace_id, **payload)
    except (ValueError, FileNotFoundError, error.URLError, error.HTTPError):
        return None


def _end_builder_workspace_run(
    *,
    workspace_id: str,
    run_id: str,
    reason: str,
    user_id: str,
    workspace_api_base: str,
) -> dict | None:
    if not run_id:
        return None
    payload = {
        "run_id": run_id,
        "agent_id": f"telegram:{user_id}",
        "status": "handed_off",
        "reason": reason,
    }
    try:
        if workspace_api_base:
            return _post_json(_workspace_service_url(workspace_api_base, workspace_id, "run-end"), payload)
        return end_workspace_run(repo_root_from(Path(__file__).resolve()), workspace_id, **payload)
    except (ValueError, FileNotFoundError, error.URLError, error.HTTPError):
        return None


def _record_builder_decision(
    *,
    workspace_id: str,
    task_id: str,
    summary: str,
    reasoning: str,
    user_id: str,
    chat_id: str,
    workspace_api_base: str,
) -> dict | None:
    payload = {
        "task_id": task_id,
        "agent_id": f"telegram:{user_id}",
        "surface": "telegram",
        "session_id": f"telegram:{chat_id}",
        "summary": summary,
        "reasoning": reasoning,
    }
    try:
        if workspace_api_base:
            return _post_json(_workspace_service_url(workspace_api_base, workspace_id, "decision"), payload)
        return record_workspace_decision(
            repo_root_from(Path(__file__).resolve()),
            workspace_id,
            **payload,
        )
    except (ValueError, FileNotFoundError, error.URLError, error.HTTPError):
        return None


def _record_builder_handoff(
    *,
    workspace_id: str,
    task_id: str,
    summary: str,
    reasoning: str,
    next_action: str,
    user_id: str,
    chat_id: str,
    workspace_api_base: str,
    run_id: str = "",
) -> dict | None:
    payload = {
        "task_id": task_id,
        "agent_id": f"telegram:{user_id}",
        "surface": "telegram",
        "session_id": f"telegram:{chat_id}",
        "summary": summary,
        "reasoning": reasoning,
        "next_action": next_action,
        "run_id": run_id,
    }
    try:
        if workspace_api_base:
            return _post_json(_workspace_service_url(workspace_api_base, workspace_id, "handoff"), payload)
        return release_workspace_task_claims(
            repo_root_from(Path(__file__).resolve()),
            workspace_id,
            **payload,
        )
    except (ValueError, FileNotFoundError, error.URLError, error.HTTPError):
        return None


def _looks_like_start_request(text: str) -> bool:
    lowered = str(text or "").strip().lower()
    return lowered.startswith(("start", "begin", "proceed")) or "start implementation" in lowered or "begin implementation" in lowered


def _looks_like_verification_report(text: str) -> bool:
    lowered = str(text or "").strip().lower()
    return ("test" in lowered or "verify" in lowered or "verified" in lowered) and any(
        token in lowered for token in ("pass", "passed", "passing", "green")
    )


def _parse_conversational_completion(text: str) -> dict | None:
    raw = str(text or "").strip()
    lowered = raw.lower()
    if lowered.startswith("complete:"):
        raw = raw.split(":", 1)[1].strip()
    elif lowered.startswith("done:"):
        raw = raw.split(":", 1)[1].strip()
    else:
        return None
    parts = [segment.strip() for segment in raw.split("::")]
    if len(parts) != 5:
        return None
    summary, reasoning, files_raw, commands_raw, risks_raw = parts
    files_touched = [item.strip() for item in files_raw.split(",") if item.strip()]
    commands_run = [item.strip() for item in commands_raw.split(";;") if item.strip()]
    residual_risks = [item.strip() for item in risks_raw.split(",") if item.strip()]
    if not summary or not reasoning or not files_touched or not commands_run or not residual_risks:
        return None
    return {
        "summary": summary,
        "reasoning": reasoning,
        "files_touched": files_touched,
        "commands_run": commands_run,
        "residual_risks": residual_risks,
    }


def _completion_prompt(field: str) -> str:
    prompts = {
        "summary": "What short summary should I record for completion?",
        "reasoning": "What reasoning should I record for why this is complete?",
        "files_touched": "Which files changed? Reply with comma-separated repo paths.",
        "commands_run": "Which verification commands did you run? Reply with commands separated by `;;`.",
        "residual_risks": "What residual risks remain? Reply with comma-separated risks, or `none known`.",
    }
    return prompts.get(field, "Provide the next completion field.")


def _parse_completion_field(field: str, text: str) -> str | list[str]:
    raw = str(text or "").strip()
    if field in {"summary", "reasoning"}:
        return raw
    if field == "files_touched":
        return [item.strip() for item in raw.split(",") if item.strip()]
    if field == "commands_run":
        return [item.strip() for item in raw.split(";;") if item.strip()]
    if field == "residual_risks":
        return [item.strip() for item in raw.split(",") if item.strip()]
    return raw


def _start_completion_collection(builder_state: dict) -> tuple[int, str]:
    builder_state["phase"] = "completion_collection"
    builder_state["pending_completion_field"] = "summary"
    builder_state["completion_draft"] = {}
    return 0, _completion_prompt("summary")


def _task_has_passing_verification(workspace_context: dict) -> bool:
    tests = list((workspace_context.get("orientation", {}) or {}).get("tests", []) or [])
    return any(str(row.get("latest_result", "") or "") == "passing" for row in tests)


def _reconcile_builder_state_from_context(builder_state: dict, workspace_context: dict) -> dict:
    task = dict((workspace_context.get("focus", {}) or {}).get("task", {}) or {})
    status = str(task.get("status", "") or "")
    blockers = list((workspace_context.get("orientation", {}) or {}).get("blockers", []) or [])
    if status == "done":
        builder_state["phase"] = "completed"
    elif builder_state.get("phase") == "completion_collection" and builder_state.get("pending_completion_field"):
        return builder_state
    elif blockers:
        builder_state["phase"] = "blocked"
    elif _task_has_passing_verification(workspace_context):
        builder_state["phase"] = "verification"
    elif status in {"in-progress", "in_progress", "review", "verification"}:
        builder_state["phase"] = "execution"
    return builder_state


def _resume_gap_reply(builder_state: dict, workspace_context: dict, inspection: dict) -> str | None:
    task = dict((workspace_context.get("focus", {}) or {}).get("task", {}) or {})
    task_id = str(task.get("task_id", "") or "")
    if not task_id:
        return None
    status = str(task.get("status", "") or "unknown")
    blockers = list((workspace_context.get("orientation", {}) or {}).get("blockers", []) or [])
    claims = list((workspace_context.get("orientation", {}) or {}).get("active_claims", []) or [])
    changed_files = list((workspace_context.get("repository", {}) or {}).get("changed_files", []) or [])
    if status == "done":
        return f"{task_id} is already done. No open execution gap remains."
    if blockers:
        blocker = blockers[0]
        return (
            f"{task_id} is currently blocked.\n\n"
            f"Reason: {blocker.get('reason', 'unknown')}\n"
            "Next gap: resolve the blocker before continuing."
        )
    if _task_has_passing_verification(workspace_context):
        extra = ""
        if inspection.get("affected_surfaces"):
            extra = f"\nAffected surfaces: {', '.join(list(inspection.get('affected_surfaces', []) or [])[:3])}"
        return (
            f"{task_id} is in {status or 'verification'} with passing verification already recorded.\n\n"
            f"Next gap: provide completion evidence or say `done` and I will collect it.{extra}"
        )
    if status in {"in-progress", "in_progress", "review", "verification"}:
        extra = ""
        if inspection.get("affected_surfaces"):
            extra = f"\nSuggested adjacent surfaces: {', '.join(list(inspection.get('affected_surfaces', []) or [])[:3])}"
        return (
            f"{task_id} is currently {status}.\n\n"
            f"Observed changed files: {len(changed_files)}\n"
            f"Active claims: {len(claims)}\n"
            f"Next gap: record passing verification once the implementation is ready.{extra}"
        )
    return (
        f"{task_id} is currently {status}.\n\n"
        "Next gap: start implementation when you are ready."
    )


def _continue_completion_collection(
    *,
    text: str,
    builder_state: dict,
    workspace_id: str,
    task_id: str,
    user_id: str,
    chat_id: str,
    workspace_api_base: str,
) -> tuple[int, str]:
    field = str(builder_state.get("pending_completion_field") or "").strip()
    draft = dict(builder_state.get("completion_draft") or {})
    value = _parse_completion_field(field, text)
    if (isinstance(value, str) and not value) or (isinstance(value, list) and not value):
        return 0, _completion_prompt(field)
    draft[field] = value
    order = ["summary", "reasoning", "files_touched", "commands_run", "residual_risks"]
    current_index = order.index(field)
    if current_index < len(order) - 1:
        next_field = order[current_index + 1]
        builder_state["completion_draft"] = draft
        builder_state["pending_completion_field"] = next_field
        return 0, _completion_prompt(next_field)

    payload = {
        "task_id": task_id,
        "agent_id": f"telegram:{user_id}",
        "surface": "telegram",
        "session_id": f"telegram:{chat_id}",
        "summary": str(draft["summary"]),
        "reasoning": str(draft["reasoning"]),
        "files_touched": list(draft["files_touched"]),
        "commands_run": list(draft["commands_run"]),
        "residual_risks": list(draft["residual_risks"]),
    }
    try:
        if workspace_api_base:
            result = _post_json(_workspace_service_url(workspace_api_base, workspace_id, "complete"), payload)
        else:
            result = complete_workspace_task(repo_root_from(Path(__file__).resolve()), workspace_id, **payload)
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            details = json.loads(body)
            missing = ", ".join(details.get("missing", []) or [])
            message = f"completion gate failed: {missing}" if missing else str(details.get("message", details.get("error", exc)))
        except json.JSONDecodeError:
            message = str(exc)
        return 1, f"meta agent bridge error: {message}"
    except (FileNotFoundError, ValueError, error.URLError) as exc:
        return 1, f"meta agent bridge error: {exc}"
    builder_state["phase"] = "completed"
    builder_state["pending_completion_field"] = ""
    builder_state["completion_draft"] = {}
    return 0, (
        f"Completed {task_id}.\n\n"
        f"Evidence accepted. Released claims: {len(result.get('released_claim_ids', []))}\n"
        f"Residual risks: {', '.join(payload['residual_risks'])}"
    )


def _handle_builder_follow_up(
    *,
    text: str,
    builder_state: dict,
    workspace_id: str,
    user_id: str,
    chat_id: str,
    message_id: str,
    workspace_api_base: str,
) -> tuple[int, str] | None:
    task_id = str(builder_state.get("workspace_task_id") or "").strip()
    if not task_id:
        return None

    if builder_state.get("phase") == "completion_collection" and builder_state.get("pending_completion_field"):
        return _continue_completion_collection(
            text=text,
            builder_state=builder_state,
            workspace_id=workspace_id,
            task_id=task_id,
            user_id=user_id,
            chat_id=chat_id,
            workspace_api_base=workspace_api_base,
        )

    if _looks_like_start_request(text):
        payload = {
            "task_id": task_id,
            "agent_id": f"telegram:{user_id}",
            "surface": "telegram",
            "session_id": f"telegram:{chat_id}",
            "reasoning": "Builder conversation promoted this task into active implementation.",
            "status": "in-progress",
            "owner": f"telegram:{user_id}",
            "source_refs": [f"telegram:message:{message_id}"],
        }
        try:
            if workspace_api_base:
                task = _post_json(_workspace_service_url(workspace_api_base, workspace_id, "task-update"), payload)
            else:
                task = update_workspace_task(repo_root_from(Path(__file__).resolve()), workspace_id, **payload)
        except (FileNotFoundError, ValueError, error.URLError, error.HTTPError) as exc:
            return 1, f"meta agent bridge error: {exc}"
        _record_builder_decision(
            workspace_id=workspace_id,
            task_id=task_id,
            summary="Execution started",
            reasoning="Builder conversation moved the scoped task into active implementation.",
            user_id=user_id,
            chat_id=chat_id,
            workspace_api_base=workspace_api_base,
        )
        builder_state["phase"] = "execution"
        return 0, f"Task {task['task_id']} is now in-progress.\n\nOwner: {task.get('owner', '') or 'unassigned'}"

    completion = _parse_conversational_completion(text)
    if completion is not None:
        payload = {
            **completion,
            "task_id": task_id,
            "agent_id": f"telegram:{user_id}",
            "surface": "telegram",
            "session_id": f"telegram:{chat_id}",
        }
        try:
            if workspace_api_base:
                result = _post_json(_workspace_service_url(workspace_api_base, workspace_id, "complete"), payload)
            else:
                result = complete_workspace_task(repo_root_from(Path(__file__).resolve()), workspace_id, **payload)
        except error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            try:
                details = json.loads(body)
                missing = ", ".join(details.get("missing", []) or [])
                message = f"completion gate failed: {missing}" if missing else str(details.get("message", details.get("error", exc)))
            except json.JSONDecodeError:
                message = str(exc)
            return 1, f"meta agent bridge error: {message}"
        except (FileNotFoundError, ValueError, error.URLError) as exc:
            return 1, f"meta agent bridge error: {exc}"
        builder_state["phase"] = "completed"
        return 0, (
            f"Completed {task_id}.\n\n"
            f"Evidence accepted. Released claims: {len(result.get('released_claim_ids', []))}\n"
            f"Residual risks: {', '.join(completion['residual_risks'])}"
        )

    if _looks_like_verification_report(text):
        payload = {
            "task_id": task_id,
            "agent_id": f"telegram:{user_id}",
            "surface": "telegram",
            "session_id": f"telegram:{chat_id}",
            "test_name": "builder-follow-up",
            "result": "passing",
            "evidence_ref": f"telegram:message:{message_id}",
            "notes": str(text or "").strip(),
        }
        try:
            if workspace_api_base:
                run = _post_json(_workspace_service_url(workspace_api_base, workspace_id, "verify"), payload)
            else:
                run = record_workspace_test_run(repo_root_from(Path(__file__).resolve()), workspace_id, **payload)
        except (FileNotFoundError, ValueError, error.URLError, error.HTTPError) as exc:
            return 1, f"meta agent bridge error: {exc}"
        handoff = _record_builder_handoff(
            workspace_id=workspace_id,
            task_id=task_id,
            summary="Verification evidence recorded",
            reasoning=str(text or "").strip(),
            next_action="Review completion evidence and close the task if residual risks are acceptable.",
            user_id=user_id,
            chat_id=chat_id,
            workspace_api_base=workspace_api_base,
            run_id=str(builder_state.get("workspace_run_id") or ""),
        )
        ended_run = _end_builder_workspace_run(
            workspace_id=workspace_id,
            run_id=str(builder_state.get("workspace_run_id") or ""),
            reason=str(text or "").strip(),
            user_id=user_id,
            workspace_api_base=workspace_api_base,
        )
        builder_state["phase"] = "verification"
        builder_state["claim_status"] = "released" if handoff else builder_state.get("claim_status", "")
        if ended_run:
            builder_state["workspace_run_id"] = ""
        return 0, (
            f"Verification recorded for {task_id}.\n\n"
            f"Test: {run['test_name']}\n"
            f"Evidence: {payload['evidence_ref']}"
        )

    if str(text or "").strip().lower() in {"done", "complete", "finished"}:
        return _start_completion_collection(builder_state)

    return None


def _telegram_api_request(bot_token: str, method: str, payload: dict | None = None) -> dict:
    url = f"https://api.telegram.org/bot{bot_token}/{method}"
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = request.Request(url, data=data, headers=headers, method="POST" if data is not None else "GET")
    with request.urlopen(req) as response:
        return json.loads(response.read().decode("utf-8"))


def _telegram_get_updates(bot_token: str, *, offset: int) -> list[dict]:
    query = parse.urlencode({"timeout": 1, "offset": offset})
    url = f"https://api.telegram.org/bot{bot_token}/getUpdates?{query}"
    with request.urlopen(url) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return payload.get("result", []) if payload.get("ok") else []


def _telegram_send_message(bot_token: str, *, chat_id: str, text: str) -> None:
    _telegram_api_request(
        bot_token,
        "sendMessage",
        {"chat_id": chat_id, "text": text},
    )


def _allowed_user_ids(raw: str) -> set[int]:
    values = set()
    for item in raw.split(","):
        item = item.strip()
        if not item:
            continue
        try:
            values.add(int(item))
        except ValueError:
            continue
    return values


def _poll_once(
    *,
    bot_token: str,
    allowed_user_ids: set[int],
    workspace_root: Path,
    api_base: str,
    workspace_api_base: str = "",
) -> int:
    offset = read_telegram_offset(workspace_root)
    updates = _telegram_get_updates(bot_token, offset=offset)
    last_offset = offset
    for update in updates:
        extracted = extract_telegram_message(update, allowed_user_ids=allowed_user_ids)
        update_id = int(update.get("update_id", 0))
        if update_id >= last_offset:
            last_offset = update_id + 1
        if extracted is None:
            continue
        _exit_code, reply = _handle_meta_command(
            text=extracted["text"],
            chat_id=extracted["chat_id"],
            update_id=extracted["update_id"],
            user_id=extracted["user_id"],
            message_id=extracted["message_id"],
            workspace_root=workspace_root,
            api_base=api_base,
            workspace_api_base=workspace_api_base,
        )
        _telegram_send_message(bot_token, chat_id=extracted["chat_id"], text=reply)
    save_telegram_offset(workspace_root, last_offset)
    return 0


def _handle_meta_command(
    *,
    text: str,
    chat_id: str,
    update_id: str,
    user_id: str,
    message_id: str,
    workspace_root: Path,
    api_base: str,
    workspace_api_base: str = "",
) -> tuple[int, str]:
    command = classify_meta_command(text or "")
    payload = build_meta_chat_payload(
        text=command.text,
        meta_state=command.meta_state,
        chat_id=chat_id,
        update_id=update_id,
        user_id=user_id,
        message_id=message_id,
    )
    inbox_event = {
        "created_at": utc_now(),
        "command": command.command,
        "meta_state": command.meta_state,
        **payload,
    }
    record_inbox_event(workspace_root, inbox_event)
    append_jsonl(
        workspace_root / "logs" / "agent_events.jsonl",
        {
            "created_at": utc_now(),
            "kind": "inbox",
            "command": command.command,
            "text": command.text,
        },
    )

    if command.command == "status":
        reply = render_meta_status_reply(workspace_root)
        record_outbox_event(workspace_root, {"created_at": utc_now(), "text": reply, "kind": "status"})
        return 0, reply

    if command.command == "workspace":
        workspace_id = str(command.text or "").strip()
        if not workspace_id:
            selected = read_selected_workspace(workspace_root)
            if not selected:
                return 1, "meta agent bridge error: workspace id required"
            reply = f"Workspace: {selected}"
            record_outbox_event(workspace_root, {"created_at": utc_now(), "text": reply, "kind": "workspace"})
            return 0, reply
        try:
            if workspace_api_base:
                _get_json(_workspace_service_url(workspace_api_base, workspace_id, "status"))
            else:
                repo_root = repo_root_from(Path(__file__).resolve())
                load_workspace_manifest(repo_root, workspace_id)
        except (FileNotFoundError, error.URLError):
            return 1, f"meta agent bridge error: unknown workspace {workspace_id}"
        save_selected_workspace(workspace_root, workspace_id)
        reply = f"Workspace: {workspace_id}"
        record_outbox_event(workspace_root, {"created_at": utc_now(), "text": reply, "kind": "workspace"})
        return 0, reply

    if command.command == "tasks":
        workspace_id = read_selected_workspace(workspace_root)
        if not workspace_id:
            return 1, "meta agent bridge error: select a workspace first with /workspace <workspace_id>"
        try:
            if workspace_api_base:
                reply = str(_get_json(_workspace_service_url(workspace_api_base, workspace_id, "tasks")).get("text", "") or "")
            else:
                repo_root = repo_root_from(Path(__file__).resolve())
                reply = render_workspace_tasks(repo_root, workspace_id)
        except (FileNotFoundError, error.URLError):
            return 1, f"meta agent bridge error: unknown workspace {workspace_id}"
        record_outbox_event(workspace_root, {"created_at": utc_now(), "text": reply, "kind": "tasks"})
        return 0, reply

    if command.command == "context":
        workspace_id = read_selected_workspace(workspace_root)
        if not workspace_id:
            return 1, "meta agent bridge error: select a workspace first with /workspace <workspace_id>"
        try:
            query = {
                "task_id": command.text.strip(),
                "agent_id": f"telegram:{user_id}",
                "surface": "telegram",
                "session_id": f"telegram:{chat_id}",
            }
            if workspace_api_base:
                packet = _get_json(_workspace_service_url(workspace_api_base, workspace_id, "context", query=query))
            else:
                packet = assemble_workspace_context_packet(repo_root_from(Path(__file__).resolve()), workspace_id, **query)
        except (FileNotFoundError, ValueError, error.URLError, error.HTTPError) as exc:
            return 1, f"meta agent bridge error: {exc}"
        task = dict(packet.get("focus", {}).get("task", {}) or {})
        repository = dict(packet.get("repository", {}) or {})
        reply = (
            f"Context for {workspace_id}.\n\n"
            f"Focus: {task.get('task_id', 'workspace')} [{task.get('status', 'n/a')}] {task.get('title', '')}\n"
            f"Open threads: {len(packet.get('orientation', {}).get('open_threads', []))}\n"
            f"Active blockers: {len(packet.get('orientation', {}).get('blockers', []))}\n"
            f"Changed files: {len(repository.get('changed_files', []))}\n"
            f"Revision: {repository.get('source_revision', '') or 'not observed'}"
        )
        record_outbox_event(workspace_root, {"created_at": utc_now(), "text": reply, "kind": "context"})
        return 0, reply

    if command.command == "task":
        workspace_id = read_selected_workspace(workspace_root)
        if not workspace_id:
            return 1, "meta agent bridge error: select a workspace first with /workspace <workspace_id>"
        parsed = parse_workspace_task_create(command.text)
        if parsed is None:
            return 1, "meta agent bridge error: use /task <task_id> :: <title> :: <acceptance1,acceptance2> :: <reasoning> :: [parent_task_id]"
        payload = {
            **parsed,
            "agent_id": f"telegram:{user_id}",
            "surface": "telegram",
            "session_id": f"telegram:{chat_id}",
            "status": "backlog",
            "priority": "medium",
            "owner": "",
            "constraints": [],
            "depends_on": [],
            "linked_artifacts": [],
            "source_refs": [f"telegram:message:{message_id}"],
        }
        try:
            if workspace_api_base:
                task = _post_json(_workspace_service_url(workspace_api_base, workspace_id, "tasks"), payload)
            else:
                task = create_workspace_task(repo_root_from(Path(__file__).resolve()), workspace_id, **payload)
        except (FileNotFoundError, ValueError, error.URLError, error.HTTPError) as exc:
            return 1, f"meta agent bridge error: {exc}"
        reply = f"Created {task['task_id']} in {workspace_id}.\n\nStatus: {task['status']}\nTitle: {task['title']}"
        record_outbox_event(workspace_root, {"created_at": utc_now(), "text": reply, "kind": "task"})
        return 0, reply

    if command.command == "task-update":
        workspace_id = read_selected_workspace(workspace_root)
        if not workspace_id:
            return 1, "meta agent bridge error: select a workspace first with /workspace <workspace_id>"
        parsed = parse_workspace_task_update(command.text)
        if parsed is None:
            return 1, "meta agent bridge error: use /task-update <task_id> :: <status> :: <reasoning>"
        payload = {
            **parsed,
            "agent_id": f"telegram:{user_id}",
            "surface": "telegram",
            "session_id": f"telegram:{chat_id}",
            "source_refs": [f"telegram:message:{message_id}"],
        }
        try:
            if workspace_api_base:
                task = _post_json(_workspace_service_url(workspace_api_base, workspace_id, "task-update"), payload)
            else:
                task = update_workspace_task(repo_root_from(Path(__file__).resolve()), workspace_id, **payload)
        except (FileNotFoundError, ValueError, error.URLError, error.HTTPError) as exc:
            return 1, f"meta agent bridge error: {exc}"
        reply = f"Updated {task['task_id']} in {workspace_id}.\n\nStatus: {task['status']}\nOwner: {task.get('owner', '') or 'unassigned'}"
        record_outbox_event(workspace_root, {"created_at": utc_now(), "text": reply, "kind": "task-update"})
        return 0, reply

    if command.command == "claim":
        workspace_id = read_selected_workspace(workspace_root)
        if not workspace_id:
            return 1, "meta agent bridge error: select a workspace first with /workspace <workspace_id>"
        parsed = parse_workspace_claim(command.text)
        if parsed is None:
            return 1, "meta agent bridge error: use /claim <task_id> :: <intent> :: <path[,path]...>"
        try:
            if workspace_api_base:
                claim = _post_json(
                    _workspace_service_url(workspace_api_base, workspace_id, "claim"),
                    {
                        "task_id": parsed["task_id"],
                        "agent_id": f"telegram:{user_id}",
                        "surface": "telegram",
                        "session_id": f"telegram:{chat_id}",
                        "intent": parsed["intent"],
                        "claimed_paths": list(parsed["claimed_paths"]),
                    },
                )
            else:
                repo_root = repo_root_from(Path(__file__).resolve())
                claim = claim_workspace_task(
                    repo_root,
                    workspace_id,
                    task_id=parsed["task_id"],
                    agent_id=f"telegram:{user_id}",
                    surface="telegram",
                    session_id=f"telegram:{chat_id}",
                    intent=parsed["intent"],
                    claimed_paths=list(parsed["claimed_paths"]),
                )
        except (FileNotFoundError, ValueError, error.URLError, error.HTTPError) as exc:
            return 1, f"meta agent bridge error: {exc}"
        reply = (
            f"Claimed {claim['task_id']} in {workspace_id}.\n\n"
            f"Paths: {', '.join(claim.get('claimed_paths', []))}\n"
            f"Intent: {claim.get('intent', '')}"
        )
        record_outbox_event(workspace_root, {"created_at": utc_now(), "text": reply, "kind": "claim"})
        return 0, reply

    if command.command == "handoff":
        workspace_id = read_selected_workspace(workspace_root)
        if not workspace_id:
            return 1, "meta agent bridge error: select a workspace first with /workspace <workspace_id>"
        parsed = parse_workspace_handoff(command.text)
        if parsed is None:
            return 1, "meta agent bridge error: use /handoff <task_id> :: <summary> :: <reasoning> :: [next_action]"
        try:
            if workspace_api_base:
                result = _post_json(
                    _workspace_service_url(workspace_api_base, workspace_id, "handoff"),
                    {
                        "task_id": parsed["task_id"],
                        "agent_id": f"telegram:{user_id}",
                        "surface": "telegram",
                        "session_id": f"telegram:{chat_id}",
                        "summary": parsed["summary"],
                        "reasoning": parsed["reasoning"],
                        "next_action": parsed["next_action"],
                    },
                )
            else:
                repo_root = repo_root_from(Path(__file__).resolve())
                result = release_workspace_task_claims(
                    repo_root,
                    workspace_id,
                    task_id=parsed["task_id"],
                    agent_id=f"telegram:{user_id}",
                    surface="telegram",
                    session_id=f"telegram:{chat_id}",
                    summary=parsed["summary"],
                    reasoning=parsed["reasoning"],
                    next_action=parsed["next_action"],
                )
        except (FileNotFoundError, error.URLError, error.HTTPError) as exc:
            return 1, f"meta agent bridge error: {exc}"
        reply = (
            f"Handed off {parsed['task_id']} in {workspace_id}.\n\n"
            f"Released claims: {len(result.get('released_claim_ids', []))}\n"
            f"Next: {parsed['next_action'] or 'none'}"
        )
        record_outbox_event(workspace_root, {"created_at": utc_now(), "text": reply, "kind": "handoff"})
        return 0, reply

    if command.command == "decision":
        workspace_id = read_selected_workspace(workspace_root)
        if not workspace_id:
            return 1, "meta agent bridge error: select a workspace first with /workspace <workspace_id>"
        parsed = parse_workspace_decision(command.text)
        if parsed is None:
            return 1, "meta agent bridge error: use /decision <task_id> :: <summary> :: <reasoning>"
        try:
            if workspace_api_base:
                decision = _post_json(
                    _workspace_service_url(workspace_api_base, workspace_id, "decision"),
                    {
                        "task_id": parsed["task_id"],
                        "agent_id": f"telegram:{user_id}",
                        "surface": "telegram",
                        "session_id": f"telegram:{chat_id}",
                        "summary": parsed["summary"],
                        "reasoning": parsed["reasoning"],
                    },
                )
            else:
                repo_root = repo_root_from(Path(__file__).resolve())
                decision = record_workspace_decision(
                    repo_root,
                    workspace_id,
                    task_id=parsed["task_id"],
                    agent_id=f"telegram:{user_id}",
                    surface="telegram",
                    session_id=f"telegram:{chat_id}",
                    summary=parsed["summary"],
                    reasoning=parsed["reasoning"],
                )
        except (FileNotFoundError, error.URLError, error.HTTPError) as exc:
            return 1, f"meta agent bridge error: {exc}"
        reply = (
            f"Decision recorded for {parsed['task_id']}.\n\n"
            f"Decision: {decision['decision_id']}\n"
            f"Summary: {decision['summary']}"
        )
        record_outbox_event(workspace_root, {"created_at": utc_now(), "text": reply, "kind": "decision"})
        return 0, reply

    if command.command == "complete":
        workspace_id = read_selected_workspace(workspace_root)
        if not workspace_id:
            return 1, "meta agent bridge error: select a workspace first with /workspace <workspace_id>"
        parsed = parse_workspace_complete(command.text)
        if parsed is None:
            return 1, (
                "meta agent bridge error: use /complete <task_id> :: <summary> :: <reasoning> :: "
                "<file1,file2> :: <command1 ;; command2> :: <risk1,risk2|none known>"
            )
        try:
            completion_payload = {
                **parsed,
                "agent_id": f"telegram:{user_id}",
                "surface": "telegram",
                "session_id": f"telegram:{chat_id}",
            }
            if workspace_api_base:
                result = _post_json(
                    _workspace_service_url(workspace_api_base, workspace_id, "complete"),
                    completion_payload,
                )
            else:
                repo_root = repo_root_from(Path(__file__).resolve())
                result = complete_workspace_task(
                    repo_root,
                    workspace_id,
                    **completion_payload,
                )
        except error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            try:
                details = json.loads(body)
                missing = ", ".join(details.get("missing", []) or [])
                message = f"completion gate failed: {missing}" if missing else str(details.get("message", details.get("error", exc)))
            except json.JSONDecodeError:
                message = str(exc)
            return 1, f"meta agent bridge error: {message}"
        except (FileNotFoundError, ValueError, error.URLError) as exc:
            return 1, f"meta agent bridge error: {exc}"
        reply = (
            f"Completed {parsed['task_id']} in {workspace_id}.\n\n"
            f"Evidence accepted. Released claims: {len(result.get('released_claim_ids', []))}\n"
            f"Residual risks: {', '.join(parsed['residual_risks'])}"
        )
        record_outbox_event(workspace_root, {"created_at": utc_now(), "text": reply, "kind": "complete"})
        return 0, reply

    if command.command == "verify":
        workspace_id = read_selected_workspace(workspace_root)
        if not workspace_id:
            return 1, "meta agent bridge error: select a workspace first with /workspace <workspace_id>"
        parsed = parse_workspace_verify(command.text)
        if parsed is None:
            return 1, "meta agent bridge error: use /verify <task_id> :: <test_name> :: <result> :: [evidence_ref] :: [notes]"
        try:
            if workspace_api_base:
                run = _post_json(
                    _workspace_service_url(workspace_api_base, workspace_id, "verify"),
                    {
                        "task_id": parsed["task_id"],
                        "agent_id": f"telegram:{user_id}",
                        "surface": "telegram",
                        "session_id": f"telegram:{chat_id}",
                        "test_name": parsed["test_name"],
                        "result": parsed["result"],
                        "evidence_ref": parsed["evidence_ref"],
                        "notes": parsed["notes"],
                    },
                )
            else:
                repo_root = repo_root_from(Path(__file__).resolve())
                run = record_workspace_test_run(
                    repo_root,
                    workspace_id,
                    task_id=parsed["task_id"],
                    agent_id=f"telegram:{user_id}",
                    surface="telegram",
                    session_id=f"telegram:{chat_id}",
                    test_name=parsed["test_name"],
                    result=parsed["result"],
                    evidence_ref=parsed["evidence_ref"],
                    notes=parsed["notes"],
                )
        except (FileNotFoundError, ValueError, error.URLError, error.HTTPError) as exc:
            return 1, f"meta agent bridge error: {exc}"
        reply = (
            f"Verification recorded for {parsed['task_id']}.\n\n"
            f"Test: {run['test_name']}\n"
            f"Result: {run['result']}"
        )
        record_outbox_event(workspace_root, {"created_at": utc_now(), "text": reply, "kind": "verify"})
        return 0, reply

    if command.command == "blocker":
        workspace_id = read_selected_workspace(workspace_root)
        if not workspace_id:
            return 1, "meta agent bridge error: select a workspace first with /workspace <workspace_id>"
        parsed = parse_workspace_blocker(command.text)
        if parsed is None:
            return 1, "meta agent bridge error: use /blocker <task_id> :: <reason> :: [next_action]"
        try:
            if workspace_api_base:
                blocker = _post_json(
                    _workspace_service_url(workspace_api_base, workspace_id, "blocker"),
                    {
                        "task_id": parsed["task_id"],
                        "agent_id": f"telegram:{user_id}",
                        "surface": "telegram",
                        "session_id": f"telegram:{chat_id}",
                        "reason": parsed["reason"],
                        "next_action": parsed["next_action"],
                    },
                )
            else:
                repo_root = repo_root_from(Path(__file__).resolve())
                blocker = record_workspace_blocker(
                    repo_root,
                    workspace_id,
                    task_id=parsed["task_id"],
                    agent_id=f"telegram:{user_id}",
                    surface="telegram",
                    session_id=f"telegram:{chat_id}",
                    reason=parsed["reason"],
                    next_action=parsed["next_action"],
                )
        except (FileNotFoundError, error.URLError, error.HTTPError) as exc:
            return 1, f"meta agent bridge error: {exc}"
        reply = (
            f"Blocker recorded for {parsed['task_id']}.\n\n"
            f"Blocker: {blocker['blocker_id']}\n"
            f"Reason: {blocker['reason']}"
        )
        record_outbox_event(workspace_root, {"created_at": utc_now(), "text": reply, "kind": "blocker"})
        return 0, reply

    if command.command == "resolve":
        workspace_id = read_selected_workspace(workspace_root)
        if not workspace_id:
            return 1, "meta agent bridge error: select a workspace first with /workspace <workspace_id>"
        parsed = parse_workspace_blocker_resolution(command.text)
        if parsed is None:
            return 1, "meta agent bridge error: use /resolve <blocker_id> :: <reasoning>"
        payload = {
            **parsed,
            "agent_id": f"telegram:{user_id}",
            "surface": "telegram",
            "session_id": f"telegram:{chat_id}",
        }
        try:
            if workspace_api_base:
                blocker = _post_json(_workspace_service_url(workspace_api_base, workspace_id, "blocker-resolve"), payload)
            else:
                blocker = resolve_workspace_blocker(repo_root_from(Path(__file__).resolve()), workspace_id, **payload)
        except (FileNotFoundError, ValueError, error.URLError, error.HTTPError) as exc:
            return 1, f"meta agent bridge error: {exc}"
        reply = f"Resolved {blocker['blocker_id']} in {workspace_id}.\n\nReason: {blocker['resolution']}"
        record_outbox_event(workspace_root, {"created_at": utc_now(), "text": reply, "kind": "resolve"})
        return 0, reply

    if command.command == "gate":
        gate_request = parse_workspace_gate(command.text)
        workspace_id = gate_request["workspace_id"] or read_selected_workspace(workspace_root)
        if not workspace_id:
            return 1, "meta agent bridge error: select a workspace first with /workspace <workspace_id>"
        try:
            if workspace_api_base:
                gate = _get_json(_workspace_service_url(workspace_api_base, workspace_id, "gate"))
            else:
                repo_root = repo_root_from(Path(__file__).resolve())
                gate = evaluate_workspace_release_gate(repo_root, workspace_id)
        except (FileNotFoundError, error.URLError) as exc:
            return 1, f"meta agent bridge error: {exc}"
        reply = (
            f"Release gate: {gate['status']}.\n\n"
            f"Workspace: {workspace_id}\n"
            f"Reasons: {', '.join(gate['reasons']) or 'none'}"
        )
        record_outbox_event(workspace_root, {"created_at": utc_now(), "text": reply, "kind": "gate"})
        return 0, reply

    if command.command in {"approve", "reject"}:
        if not command.text:
            return 1, "meta agent bridge error: packet id required"
        packet_id = command.text.split()[0]
        if command.command == "approve":
            approval = parse_release_approval(command.text)
            if approval is None:
                return 1, "meta agent bridge error: use /approve <packet_id> for release <release_id>"
            try:
                packet = apply_packet_decision(
                    workspace_root,
                    approval["packet_id"],
                    decision="approved",
                    actor=f"telegram:{user_id}",
                    release_id=approval["release_id"],
                )
            except FileNotFoundError:
                return 1, f"meta agent bridge error: unknown packet {approval['packet_id']}"
            reply = (
                f"Packet {packet['packet_id']} approved for release {approval['release_id']}.\n\n"
                f"Mode: operate\nDomain: {packet.get('classification', {}).get('domain', 'unknown')}\n"
                f"Risk: {packet.get('classification', {}).get('risk', 'unknown')}"
            )
        else:
            try:
                packet = apply_packet_decision(
                    workspace_root,
                    packet_id,
                    decision="rejected",
                    actor=f"telegram:{user_id}",
                )
            except FileNotFoundError:
                return 1, f"meta agent bridge error: unknown packet {packet_id}"
            reply = (
                f"Packet {packet['packet_id']} marked rejected.\n\n"
                f"Mode: operate\nDomain: {packet.get('classification', {}).get('domain', 'unknown')}\n"
                f"Risk: {packet.get('classification', {}).get('risk', 'unknown')}"
            )
        record_outbox_event(workspace_root, {"created_at": utc_now(), "text": reply, "kind": command.command})
        return 0, reply

    if command.command == "deploy":
        if not command.text:
            return 1, "meta agent bridge error: release id required"
        release_id = command.text.split()[0]
        repo_root = repo_root_from(Path(__file__).resolve())
        readiness = evaluate_release_readiness(repo_root, release_id, workspace_api_base=workspace_api_base)
        if not release_is_approved(workspace_root, release_id):
            reply = (
                f"Release {release_id} is blocked.\n\n"
                "Mode: operate\nDomain: deployment_release\nRisk: critical\n"
                "Missing: explicit approved packet for this release"
            )
            record_outbox_event(
                workspace_root,
                {"created_at": utc_now(), "text": reply, "kind": "deploy", "release_id": release_id},
            )
            return 1, reply
        if readiness["missing"]:
            reply = (
                f"Release {readiness['release_id']} is blocked.\n\n"
                "Mode: operate\nDomain: deployment_release\nRisk: critical\n"
                f"Missing: {', '.join(readiness['missing'])}"
            )
            exit_code = 1
        else:
            deploy_result = execute_release_deploy(
                repo_root,
                workspace_root,
                release_id,
                workspace_api_base=workspace_api_base,
            )
            if deploy_result["status"] == "deployed":
                reply = (
                    f"Release {release_id} deployed.\n\n"
                    "Mode: operate\nDomain: deployment_release\nRisk: critical\n"
                    f"Evidence: {deploy_result['post_deploy_smoke_path']}"
                )
                exit_code = 0
            else:
                reply = (
                    f"Release {release_id} failed to deploy.\n\n"
                    "Mode: operate\nDomain: deployment_release\nRisk: critical\n"
                    f"Reason: {deploy_result.get('reason', deploy_result['status'])}"
                )
                exit_code = 1
        record_outbox_event(
            workspace_root,
            {
                "created_at": utc_now(),
                "text": reply,
                "kind": "deploy",
                "release_id": readiness["release_id"],
            },
        )
        return exit_code, reply

    if command.command == "rollback":
        if not command.text:
            return 1, "meta agent bridge error: release id required"
        release_id = command.text.split()[0]
        repo_root = repo_root_from(Path(__file__).resolve())
        reply = render_rollback_status_reply(repo_root, release_id)
        exit_code = 0 if "ready as a dry run" in reply else 1
        record_outbox_event(
            workspace_root,
            {"created_at": utc_now(), "text": reply, "kind": "rollback", "release_id": release_id},
        )
        return exit_code, reply

    builder_state = read_builder_session_state(workspace_root, payload["session_id"])
    selected_workspace = read_selected_workspace(workspace_root)
    workspace_context: dict = {}
    if selected_workspace:
        query = {
            "task_id": str(builder_state.get("workspace_task_id") or "").strip(),
            "agent_id": f"telegram:{user_id}",
            "surface": "telegram",
            "session_id": f"telegram:{chat_id}",
        }
        try:
            if workspace_api_base:
                workspace_context = _get_json(_workspace_service_url(workspace_api_base, selected_workspace, "context", query=query))
            else:
                workspace_context = assemble_workspace_context_packet(
                    repo_root_from(Path(__file__).resolve()),
                    selected_workspace,
                    **query,
                )
        except (FileNotFoundError, ValueError, error.URLError, error.HTTPError):
            workspace_context = {"workspace_id": selected_workspace}
    inspection = {}
    if selected_workspace and workspace_context:
        inspection = _collect_builder_inspection(_resolve_builder_root(workspace_root), selected_workspace, workspace_context)
    if selected_workspace and builder_state:
        _heartbeat_builder_workspace_run(
            workspace_id=selected_workspace,
            run_id=str(builder_state.get("workspace_run_id") or ""),
            user_id=user_id,
            workspace_api_base=workspace_api_base,
        )
        if inspection:
            builder_state["inspection"] = inspection
        builder_state = _reconcile_builder_state_from_context(builder_state, workspace_context)
        lowered_text = str(command.text or "").strip().lower()
        if lowered_text in {"continue", "resume", "what next", "next", "where are we", "status"}:
            reply = _resume_gap_reply(builder_state, workspace_context, inspection)
            if reply:
                save_builder_session_state(workspace_root, payload["session_id"], builder_state)
                record_outbox_event(workspace_root, {"created_at": utc_now(), "text": reply, "kind": "builder-resume"})
                return 0, reply
        follow_up = _handle_builder_follow_up(
            text=command.text,
            builder_state=builder_state,
            workspace_id=selected_workspace,
            user_id=user_id,
            chat_id=chat_id,
            message_id=message_id,
            workspace_api_base=workspace_api_base,
        )
        if follow_up is not None:
            save_builder_session_state(workspace_root, payload["session_id"], builder_state)
            record_outbox_event(workspace_root, {"created_at": utc_now(), "text": follow_up[1], "kind": "builder-follow-up"})
            return follow_up
    payload["builder_state"] = builder_state
    if workspace_context:
        payload["workspace_context"] = workspace_context

    builder_mode_active = str(builder_state.get("target_meta_state") or "").strip().lower() == "operate"
    if command.command == "meta" and not builder_mode_active:
        analysis = build_builder_chat_response(
            command.text,
            requested_meta_state=command.meta_state,
            builder_state=builder_state,
            workspace_context=workspace_context,
        )
        session_builder_state = dict(analysis.get("builder_state", {}) or {})
        if session_builder_state:
            save_builder_session_state(workspace_root, payload["session_id"], session_builder_state)
        try:
            reply = _request_meta_openclaw_reply(
                root=repo_root_from(Path(__file__).resolve()),
                text=command.text,
                session_id=payload["session_id"],
                builder_analysis=analysis,
                workspace_context=workspace_context,
            )
        except RuntimeError as exc:
            fallback = str(analysis.get("assistant_text") or "").strip() or "Tell me more about what you want to work on."
            reply = fallback
            append_jsonl(
                workspace_root / "logs" / "agent_events.jsonl",
                {
                    "created_at": utc_now(),
                    "kind": "openclaw_fallback",
                    "error": str(exc),
                },
            )
        record_outbox_event(workspace_root, {"created_at": utc_now(), "text": reply, "kind": command.command})
        append_jsonl(
            workspace_root / "logs" / "agent_events.jsonl",
            {
                "created_at": utc_now(),
                "kind": "response",
                "command": command.command,
                "packet_id": "",
            },
        )
        return 0, reply

    try:
        response = _post_json(f"{api_base.rstrip('/')}/self-improvement/chat", payload)
    except error.URLError as exc:
        return 1, f"meta agent bridge error: {exc}"

    if isinstance(response.get("builder_state"), dict):
        session_builder_state = dict(response["builder_state"])
    else:
        session_builder_state = {}

    if isinstance(response.get("packet"), dict) and response["packet"].get("packet_id"):
        persist_meta_packet(workspace_root, response["packet"], status="proposed")
        triage_packet_to_workboard(
            repo_root_from(Path(__file__).resolve()),
            response["packet"],
            actor=f"telegram:{user_id}",
        )
        builder_scope = dict(response.get("builder_scope", {}) or {})
        workspace_id = selected_workspace
        if workspace_id and session_builder_state:
            task = _create_builder_workspace_task(
                workspace_id=workspace_id,
                packet=response["packet"],
                builder_state=session_builder_state,
                builder_scope=builder_scope,
                user_id=user_id,
                chat_id=chat_id,
                message_id=message_id,
                workspace_api_base=workspace_api_base,
            )
            session_builder_state["workspace_task_id"] = str(task.get("task_id", "") or str(response["packet"].get("packet_id", "")).upper())
            run = _begin_builder_workspace_run(
                workspace_id=workspace_id,
                task_id=session_builder_state["workspace_task_id"],
                builder_scope=builder_scope,
                user_id=user_id,
                chat_id=chat_id,
                workspace_api_base=workspace_api_base,
            )
            session_builder_state["workspace_run_id"] = str((run or {}).get("run_id", "") or "")
            session_builder_state["claim_status"] = "active" if run and list(run.get("claim_ids", []) or []) else "not_claimed"
            decision = _record_builder_decision(
                workspace_id=workspace_id,
                task_id=session_builder_state["workspace_task_id"],
                summary=f"Builder scoped objective: {_builder_task_title(session_builder_state)}",
                reasoning=str(builder_scope.get("summary") or session_builder_state.get("acceptance_criteria") or "Builder conversation confirmed the initial implementation scope.").strip(),
                user_id=user_id,
                chat_id=chat_id,
                workspace_api_base=workspace_api_base,
            )
            if decision:
                session_builder_state["last_decision_id"] = str(decision.get("decision_id", "") or "")
            response["assistant_text"] = (
                f"{response.get('assistant_text', '').rstrip()}\n\n"
                f"Workspace task: {session_builder_state['workspace_task_id']}"
            )
            if run and list(run.get("claimed_paths", []) or []):
                response["assistant_text"] = (
                    f"{response['assistant_text']}\nReserved paths: {', '.join(list(run.get('claimed_paths', []) or []))}"
                )
    if session_builder_state:
        save_builder_session_state(workspace_root, payload["session_id"], session_builder_state)
    reply = build_meta_telegram_reply(response)
    record_outbox_event(workspace_root, {"created_at": utc_now(), "text": reply, "kind": command.command})
    append_jsonl(
        workspace_root / "logs" / "agent_events.jsonl",
        {
            "created_at": utc_now(),
            "kind": "response",
            "command": command.command,
            "packet_id": (response.get("packet") or {}).get("packet_id", ""),
        },
    )
    return 0, reply


def main() -> int:
    parser = argparse.ArgumentParser(description="Telegram-first meta agent bridge for Inner Space.")
    parser.add_argument("--text", help="Telegram command text to interpret and forward.")
    parser.add_argument("--chat-id", default="local-chat")
    parser.add_argument("--update-id", default="local-update")
    parser.add_argument("--user-id", default="local-user")
    parser.add_argument("--message-id", default="local-message")
    parser.add_argument("--poll-once", action="store_true")
    parser.add_argument("--poll-forever", action="store_true")
    parser.add_argument("--poll-interval-seconds", type=float, default=2.0)
    parser.add_argument("--bot-token", default=os.environ.get("TELEGRAM_BOT_TOKEN", ""))
    parser.add_argument(
        "--allowed-user-ids",
        default=os.environ.get("TELEGRAM_ALLOWED_USER_IDS", ""),
        help="Comma-separated allowlist of Telegram user ids.",
    )
    parser.add_argument(
        "--workspace-root",
        default=os.environ.get("INNER_SPACE_META_WORKSPACE_ROOT", ""),
        help="Root directory for inbox/outbox/packet state.",
    )
    parser.add_argument(
        "--api-base",
        default=os.environ.get("INNER_WORLD_API_BASE", "http://127.0.0.1:8422/api"),
    )
    parser.add_argument(
        "--workspace-api-base",
        default=os.environ.get("INNER_WORLD_WORKSPACE_API_BASE", ""),
        help="Optional workspace service base URL, for example http://127.0.0.1:8765/api",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the payload that would be sent to the self-improvement API.",
    )
    args = parser.parse_args()
    workspace_root = (
        Path(args.workspace_root).expanduser()
        if args.workspace_root
        else repo_root_from(Path(__file__).resolve()).resolve() / "product" / "inner_world_v1" / "meta_agent" / "state" / "runtime"
    )

    if args.poll_once or args.poll_forever:
        if not args.bot_token:
            mode = "--poll-forever" if args.poll_forever else "--poll-once"
            print(f"meta agent bridge error: TELEGRAM_BOT_TOKEN is required for {mode}")
            return 1
        allowed_user_ids = _allowed_user_ids(args.allowed_user_ids)
        if args.poll_once:
            return _poll_once(
                bot_token=args.bot_token,
                allowed_user_ids=allowed_user_ids,
                workspace_root=workspace_root,
                api_base=args.api_base,
                workspace_api_base=args.workspace_api_base,
            )
        while True:
            try:
                _poll_once(
                    bot_token=args.bot_token,
                    allowed_user_ids=allowed_user_ids,
                    workspace_root=workspace_root,
                    api_base=args.api_base,
                    workspace_api_base=args.workspace_api_base,
                )
            except KeyboardInterrupt:
                return 0
            except Exception as exc:
                print(f"meta agent bridge error: poll loop failure: {exc}", file=sys.stderr)
            time.sleep(max(args.poll_interval_seconds, 0.2))

    if args.dry_run:
        command = classify_meta_command(args.text or "")
        payload = build_meta_chat_payload(
            text=command.text,
            meta_state=command.meta_state,
            chat_id=args.chat_id,
            update_id=args.update_id,
            user_id=args.user_id,
            message_id=args.message_id,
        )
        print(json.dumps(payload, indent=2))
        return 0

    exit_code, reply = _handle_meta_command(
        text=args.text or "",
        chat_id=args.chat_id,
        update_id=args.update_id,
        user_id=args.user_id,
        message_id=args.message_id,
        workspace_root=workspace_root,
        api_base=args.api_base,
        workspace_api_base=args.workspace_api_base,
    )
    print(reply)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
