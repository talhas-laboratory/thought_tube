from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Dict, List

from .cost_tracker import estimate_token_count, record_actual_cost


MODULE_ID = "kernel.runtime.chat_backends"
CONTRACT_VERSION = "1.0"
PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "get_openclaw_model_control_state",
    "stage_openclaw_agent_model",
    "apply_openclaw_model_control",
    "rollback_openclaw_model_control",
    "resolve_chat_backend",
    "compose_openclaw_message",
    "request_openclaw_reply",
)
__all__ = list(PUBLIC_API)


def _config_path(root: Path) -> Path:
    return root / "product" / "inner_world_v1" / "config" / "runtime.json"


def _read_runtime_config(root: Path) -> Dict:
    path = _config_path(root)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _openclaw_config_path(root: Path) -> Path:
    config = _read_runtime_config(root)
    openclaw = config.get("openclaw", {}) if isinstance(config, dict) else {}
    raw_path = (
        os.getenv("INNER_WORLD_OPENCLAW_CONFIG_PATH")
        or openclaw.get("config_path")
        or openclaw.get("control_config_path")
    )
    if raw_path:
        return Path(raw_path).expanduser()
    return Path.home() / ".openclaw" / "openclaw.json"


def _openclaw_control_state_path(root: Path) -> Path:
    return root / "product" / "inner_world_v1" / "data" / "openclaw_model_control_state.json"


def _openclaw_control_backup_dir(root: Path) -> Path:
    return root / "product" / "inner_world_v1" / "data" / "openclaw_model_control_backups"


def _read_openclaw_config(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"OpenClaw config not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _read_openclaw_control_state(root: Path) -> Dict[str, Any]:
    path = _openclaw_control_state_path(root)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json_atomic(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", delete=False, dir=path.parent, encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
        temp_path = Path(handle.name)
    temp_path.replace(path)


def _write_openclaw_config(path: Path, payload: Dict[str, Any]) -> None:
    _write_json_atomic(path, payload)


def _write_openclaw_control_state(root: Path, payload: Dict[str, Any]) -> None:
    _write_json_atomic(_openclaw_control_state_path(root), payload)


def _config_hash(payload: Dict[str, Any]) -> str:
    normalized = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _openclaw_agent_list(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    agents = config.get("agents")
    if not isinstance(agents, dict):
        return []
    rows = agents.get("list")
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict) and row.get("id")]


def _default_model_id(config: Dict[str, Any]) -> str:
    agents = config.get("agents")
    if not isinstance(agents, dict):
        return ""
    defaults = agents.get("defaults")
    if not isinstance(defaults, dict):
        return ""
    model = defaults.get("model")
    if isinstance(model, str):
        return model
    if isinstance(model, dict):
        primary = model.get("primary")
        if isinstance(primary, str):
            return primary
        for value in model.values():
            if isinstance(value, str):
                return value
    return ""


def _available_model_ids(config: Dict[str, Any]) -> List[str]:
    ids: set[str] = set()
    agents = config.get("agents")
    if isinstance(agents, dict):
        defaults = agents.get("defaults")
        if isinstance(defaults, dict):
            models = defaults.get("models")
            if isinstance(models, dict):
                ids.update(str(key) for key in models.keys())
    default_model = _default_model_id(config)
    if default_model:
        ids.add(default_model)
    for row in _openclaw_agent_list(config):
        model = row.get("model")
        if isinstance(model, str) and model:
            ids.add(model)
    providers = config.get("models", {}).get("providers")
    if isinstance(providers, dict):
        for provider_id, provider_payload in providers.items():
            if not isinstance(provider_payload, dict):
                continue
            models = provider_payload.get("models")
            if not isinstance(models, list):
                continue
            for model in models:
                if not isinstance(model, dict):
                    continue
                model_id = model.get("id")
                if isinstance(model_id, str) and model_id:
                    ids.add(f"{provider_id}/{model_id}")
    return sorted(ids)


def _agent_lookup(config: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {row["id"]: row for row in _openclaw_agent_list(config)}


def _serialize_pending_changes(
    config: Dict[str, Any],
    pending_assignments: Dict[str, Any],
) -> List[Dict[str, Any]]:
    default_model = _default_model_id(config)
    lookup = _agent_lookup(config)
    changes: List[Dict[str, Any]] = []
    for agent_id in sorted(pending_assignments.keys()):
        row = lookup.get(agent_id)
        if not row:
            continue
        explicit_model = row.get("model") if isinstance(row.get("model"), str) else None
        old_model_id = explicit_model or default_model
        staged_value = pending_assignments[agent_id]
        new_model_id = default_model if staged_value is None else staged_value
        changes.append(
            {
                "agent_id": agent_id,
                "old_model_id": old_model_id,
                "new_model_id": new_model_id,
                "uses_default_after_apply": staged_value is None,
            }
        )
    return changes


def get_openclaw_model_control_state(root: Path) -> Dict[str, Any]:
    config_path = _openclaw_config_path(root)
    config = _read_openclaw_config(config_path)
    current_hash = _config_hash(config)
    saved_state = _read_openclaw_control_state(root)
    pending_assignments = saved_state.get("pending_assignments")
    if not isinstance(pending_assignments, dict):
        pending_assignments = {}

    default_model = _default_model_id(config)
    lookup = _agent_lookup(config)
    agents = []
    for row in _openclaw_agent_list(config):
        agent_id = row["id"]
        explicit_model = row.get("model") if isinstance(row.get("model"), str) else None
        staged_value = pending_assignments.get(agent_id, "__missing__")
        effective_model_id = (
            default_model
            if staged_value is None
            else staged_value
            if staged_value != "__missing__"
            else explicit_model or default_model
        )
        agents.append(
            {
                "agent_id": agent_id,
                "label": row.get("name") or agent_id,
                "current_model_id": explicit_model or default_model,
                "explicit_model_id": explicit_model,
                "effective_model_id": effective_model_id,
                "uses_default": explicit_model is None,
                "has_pending_change": agent_id in pending_assignments,
            }
        )

    warnings = []
    baseline_hash = saved_state.get("config_hash")
    if pending_assignments and isinstance(baseline_hash, str) and baseline_hash and baseline_hash != current_hash:
        warnings.append("Pending model changes were staged against an older OpenClaw config revision.")

    return {
        "config_path": str(config_path),
        "config_hash": current_hash,
        "default_model_id": default_model,
        "available_models": _available_model_ids(config),
        "agents": agents,
        "dirty": bool(pending_assignments),
        "pending_changes": _serialize_pending_changes(config, pending_assignments),
        "warnings": warnings,
        "last_backup_path": saved_state.get("last_backup_path"),
        "last_applied_at": saved_state.get("last_applied_at"),
        "last_rolled_back_at": saved_state.get("last_rolled_back_at"),
    }


def stage_openclaw_agent_model(root: Path, agent_id: str, model_id: str) -> Dict[str, Any]:
    config_path = _openclaw_config_path(root)
    config = _read_openclaw_config(config_path)
    lookup = _agent_lookup(config)
    row = lookup.get(agent_id)
    if not row:
        raise ValueError(f"Unknown OpenClaw agent: {agent_id}")

    available_models = set(_available_model_ids(config))
    if model_id not in available_models:
        raise ValueError(f"Unknown OpenClaw model: {model_id}")

    default_model = _default_model_id(config)
    explicit_model = row.get("model") if isinstance(row.get("model"), str) else None
    current_effective_model = explicit_model or default_model

    saved_state = _read_openclaw_control_state(root)
    pending_assignments = saved_state.get("pending_assignments")
    if not isinstance(pending_assignments, dict):
        pending_assignments = {}

    if model_id == default_model:
        if explicit_model is None:
            pending_assignments.pop(agent_id, None)
        else:
            pending_assignments[agent_id] = None
    elif explicit_model == model_id:
        pending_assignments.pop(agent_id, None)
    else:
        pending_assignments[agent_id] = model_id

    payload = {
        **saved_state,
        "config_path": str(config_path),
        "config_hash": _config_hash(config),
        "pending_assignments": pending_assignments,
        "updated_at": _iso_now(),
    }
    _write_openclaw_control_state(root, payload)
    state = get_openclaw_model_control_state(root)
    staged_change = next((item for item in state["pending_changes"] if item["agent_id"] == agent_id), None)
    return {
        "ok": True,
        "dirty": state["dirty"],
        "change": staged_change
        or {
            "agent_id": agent_id,
            "old_model_id": current_effective_model,
            "new_model_id": model_id,
            "uses_default_after_apply": model_id == default_model,
        },
        "pending_changes": state["pending_changes"],
    }


def _run_openclaw_gateway_command(root: Path, command: str, timeout_seconds: int = 45) -> Dict[str, Any]:
    completed = subprocess.run(
        ["openclaw", "gateway", command],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        check=False,
    )
    return {
        "ok": completed.returncode == 0,
        "returncode": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }


def apply_openclaw_model_control(root: Path) -> Dict[str, Any]:
    state = _read_openclaw_control_state(root)
    pending_assignments = state.get("pending_assignments")
    if not isinstance(pending_assignments, dict) or not pending_assignments:
        return {"ok": True, "applied": False, "pending_changes": []}

    config_path = _openclaw_config_path(root)
    config = _read_openclaw_config(config_path)
    current_hash = _config_hash(config)
    baseline_hash = state.get("config_hash")
    if isinstance(baseline_hash, str) and baseline_hash and baseline_hash != current_hash:
        raise RuntimeError("OpenClaw config changed after model assignments were staged.")

    lookup = _agent_lookup(config)
    for agent_id in pending_assignments.keys():
        if agent_id not in lookup:
            raise RuntimeError(f"Cannot apply model change for missing OpenClaw agent: {agent_id}")

    backup_dir = _openclaw_control_backup_dir(root)
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_path = backup_dir / f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-openclaw.json"
    shutil.copy2(config_path, backup_path)

    for agent_id, staged_value in pending_assignments.items():
        row = lookup[agent_id]
        if staged_value is None:
            row.pop("model", None)
        else:
            row["model"] = staged_value

    _write_openclaw_config(config_path, config)
    restart_result = _run_openclaw_gateway_command(root, "restart")
    health_result = _run_openclaw_gateway_command(root, "health")

    if not restart_result["ok"] or not health_result["ok"]:
        shutil.copy2(backup_path, config_path)
        rollback_restart = _run_openclaw_gateway_command(root, "restart")
        raise RuntimeError(
            "OpenClaw model control apply failed: "
            f"restart_ok={restart_result['ok']} health_ok={health_result['ok']} "
            f"rollback_restart_ok={rollback_restart['ok']}"
        )

    payload = {
        **state,
        "config_path": str(config_path),
        "config_hash": _config_hash(config),
        "pending_assignments": {},
        "updated_at": _iso_now(),
        "last_backup_path": str(backup_path),
        "last_applied_at": _iso_now(),
        "last_apply_result": {
            "restart": restart_result,
            "health": health_result,
        },
    }
    _write_openclaw_control_state(root, payload)
    return {
        "ok": True,
        "applied": True,
        "backup_path": str(backup_path),
        "restart": restart_result,
        "health_check": health_result,
        "pending_changes": [],
    }


def rollback_openclaw_model_control(root: Path) -> Dict[str, Any]:
    state = _read_openclaw_control_state(root)
    backup_path_raw = state.get("last_backup_path")
    pending_assignments = state.get("pending_assignments")
    if not backup_path_raw:
        if isinstance(pending_assignments, dict) and pending_assignments:
            payload = {
                **state,
                "pending_assignments": {},
                "updated_at": _iso_now(),
            }
            _write_openclaw_control_state(root, payload)
            return {"ok": True, "rolled_back": False, "cleared_pending_changes": True}
        return {"ok": True, "rolled_back": False, "cleared_pending_changes": False}

    backup_path = Path(str(backup_path_raw))
    if not backup_path.exists():
        raise FileNotFoundError(f"OpenClaw model control backup not found: {backup_path}")

    config_path = _openclaw_config_path(root)
    shutil.copy2(backup_path, config_path)
    restart_result = _run_openclaw_gateway_command(root, "restart")
    health_result = _run_openclaw_gateway_command(root, "health")
    if not restart_result["ok"] or not health_result["ok"]:
        raise RuntimeError(
            "OpenClaw model control rollback failed: "
            f"restart_ok={restart_result['ok']} health_ok={health_result['ok']}"
        )

    config = _read_openclaw_config(config_path)
    payload = {
        **state,
        "config_path": str(config_path),
        "config_hash": _config_hash(config),
        "pending_assignments": {},
        "updated_at": _iso_now(),
        "last_rolled_back_at": _iso_now(),
        "last_rollback_result": {
            "restart": restart_result,
            "health": health_result,
        },
    }
    _write_openclaw_control_state(root, payload)
    return {
        "ok": True,
        "rolled_back": True,
        "backup_path": str(backup_path),
        "restart": restart_result,
        "health_check": health_result,
        "pending_changes": [],
    }


def resolve_chat_backend(root: Path) -> Dict:
    config = _read_runtime_config(root)
    backend = (
        os.getenv("INNER_WORLD_CHAT_BACKEND")
        or config.get("chat_backend")
        or "heuristic"
    )
    openclaw = config.get("openclaw", {})
    return {
        "id": backend,
        "openclaw": {
            "agent": os.getenv("INNER_WORLD_OPENCLAW_AGENT") or openclaw.get("agent") or "main",
            "thinking": os.getenv("INNER_WORLD_OPENCLAW_THINKING") or openclaw.get("thinking") or "minimal",
            "timeout_seconds": int(
                os.getenv("INNER_WORLD_OPENCLAW_TIMEOUT")
                or openclaw.get("timeout_seconds")
                or 90
            ),
            "deliver": str(os.getenv("INNER_WORLD_OPENCLAW_DELIVER") or openclaw.get("deliver") or "false").lower()
            in {"1", "true", "yes", "on"},
        },
    }


def compose_openclaw_message(context: Dict, user_message: str, thread: Dict) -> str:
    history = []
    for message in thread.get("messages", [])[-6:]:
        history.append(f"{message['role']}: {message['content']}")
    history_block = "\n".join(history) if history else "No prior messages."
    evidence = "\n".join(
        f"- {snippet['title']} ({Path(snippet['source_ref']).name}): {snippet['excerpt']}"
        for snippet in context.get("source_snippets", [])[:4]
    )
    if not evidence:
        evidence = "- No direct source snippets were attached."

    return "\n".join(
        [
            "Inner World thought-chat request.",
            "",
            f"Character: {context['character']}",
            "System prompt:",
            context["system_prompt"],
            "",
            "Evidence:",
            evidence,
            "",
            "Recent thread history:",
            history_block,
            "",
            f"User message: {user_message}",
            "",
            "Instructions:",
            "- Answer as the thought speaking from its own evidence.",
            "- Stay concise and grounded.",
            "- Do not claim evidence that is not present above.",
            "- End with one concrete next move.",
        ]
    )


def _extract_text_from_json(payload: Dict) -> str | None:
    candidates: List[str | None] = [
        payload.get("reply"),
        payload.get("text"),
        payload.get("content"),
        payload.get("message"),
    ]
    result = payload.get("result")
    if isinstance(result, dict):
        candidates.extend(
            [
                result.get("reply"),
                result.get("text"),
                result.get("content"),
                result.get("message"),
                result.get("finalAssistantVisibleText"),
                result.get("finalAssistantRawText"),
            ]
        )
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
    payloads = payload.get("payloads")
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
    for candidate in candidates:
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
    return None


def _extract_usage_from_json(payload: Dict) -> Dict:
    result = payload.get("result") if isinstance(payload.get("result"), dict) else {}
    usage = payload.get("usage") if isinstance(payload.get("usage"), dict) else {}
    if not usage and isinstance(result.get("usage"), dict):
        usage = result["usage"]
    model = payload.get("model") or result.get("model") or ""
    prompt_tokens = usage.get("prompt_tokens") or usage.get("input_tokens") or 0
    completion_tokens = usage.get("completion_tokens") or usage.get("output_tokens") or 0
    total_tokens = usage.get("total_tokens") or usage.get("tokens") or 0
    usd_cost = usage.get("cost_usd") or usage.get("usd_cost") or payload.get("cost_usd") or result.get("cost_usd")
    return {
        "model": model,
        "prompt_tokens": int(prompt_tokens or 0),
        "completion_tokens": int(completion_tokens or 0),
        "total_tokens": int(total_tokens or 0),
        "usd_cost": float(usd_cost) if usd_cost is not None else None,
    }


def request_openclaw_reply(root: Path, context: Dict, user_message: str, thread: Dict, backend: Dict) -> Dict:
    backend_id = backend["id"]
    openclaw = backend["openclaw"]
    message = compose_openclaw_message(context, user_message, thread)
    command = [
        "openclaw",
        "agent",
        "--session-id",
        thread["thread_id"],
        "--agent",
        openclaw["agent"],
        "--message",
        message,
        "--thinking",
        openclaw["thinking"],
        "--json",
    ]
    if backend_id == "openclaw_local":
        command.append("--local")
    if openclaw["deliver"]:
        command.append("--deliver")

    completed = subprocess.run(
        command,
        cwd=root,
        capture_output=True,
        text=True,
        timeout=openclaw["timeout_seconds"],
        check=False,
    )
    stdout = completed.stdout.strip()
    stderr = completed.stderr.strip()
    if completed.returncode != 0:
        raise RuntimeError(stderr or stdout or f"openclaw exited with code {completed.returncode}")

    reply_text = stdout
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError:
        payload = None
    usage = {}
    if isinstance(payload, dict):
        reply_text = _extract_text_from_json(payload) or stdout
        usage = _extract_usage_from_json(payload)

    if not reply_text.strip():
        raise RuntimeError("openclaw returned an empty reply")

    prompt_tokens = usage.get("prompt_tokens") or estimate_token_count(message)
    completion_tokens = usage.get("completion_tokens") or estimate_token_count(reply_text)
    record_actual_cost(
        root,
        component="chat_backend",
        operation="thought_chat",
        provider="openclaw",
        model=usage.get("model") or backend_id,
        input_tokens=prompt_tokens,
        output_tokens=completion_tokens,
        usd_cost=usage.get("usd_cost"),
        token_source="actual" if usage.get("prompt_tokens") or usage.get("completion_tokens") else "estimated",
        metadata={
            "thread_id": thread["thread_id"],
            "backend_id": backend_id,
            "thinking": openclaw["thinking"],
        },
    )
    return {"content": reply_text.strip(), "backend_id": backend_id}
