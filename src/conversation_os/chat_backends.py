from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Dict, List, Mapping

from .cost_tracker import estimate_token_count, record_actual_cost
from .disclosure_contracts import validate_model_bound_payload


MODULE_ID = "kernel.runtime.chat_backends"
CONTRACT_VERSION = "1.0"
PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "get_openclaw_model_control_state",
    "stage_openclaw_agent_model",
    "apply_openclaw_model_control",
    "rollback_openclaw_model_control",
    "ensure_bridge_openclaw_agent",
    "diagnose_openclaw_telegram_config",
    "migrate_openclaw_telegram_bindings",
    "apply_openclaw_host_telegram_fix",
    "resolve_chat_backend",
    "compose_openclaw_message",
    "compose_execution_message",
    "trim_context_bundle",
    "request_openclaw_reply",
    "request_bridge_execution_reply",
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


def ensure_bridge_openclaw_agent(
    root: Path,
    *,
    agent_id: str,
    model_id: str = "",
    workspace: str = "",
) -> Dict[str, Any]:
    config_path = _openclaw_config_path(root)
    config = _read_openclaw_config(config_path)
    agents = config.setdefault("agents", {})
    agent_list = agents.setdefault("list", [])
    if not isinstance(agent_list, list):
        raise RuntimeError("OpenClaw config agents.list must be a list")

    lookup = _agent_lookup(config)
    default_model = _default_model_id(config)
    available_models = set(_available_model_ids(config))
    requested_model = model_id.strip()
    if requested_model and requested_model not in available_models:
        raise ValueError(
            f"Unknown OpenClaw model for bridge agent: {requested_model}. "
            f"Available models: {', '.join(sorted(available_models)) or '(none)'}"
        )
    target_model = requested_model or default_model

    defaults = agents.get("defaults", {}) if isinstance(agents.get("defaults"), dict) else {}
    default_workspace = defaults.get("workspace")
    if isinstance(default_workspace, dict):
        default_workspace = ""
    resolved_workspace = (
        workspace.strip()
        or (default_workspace if isinstance(default_workspace, str) else "")
        or str(Path.home() / ".openclaw" / "workspace")
    )

    changed = False
    row = lookup.get(agent_id)
    if row is None:
        entry: Dict[str, Any] = {
            "id": agent_id,
            "name": "Thought Tube Router",
            "workspace": resolved_workspace,
        }
        if target_model:
            entry["model"] = target_model
        agent_list.append(entry)
        row = entry
        changed = True
    else:
        if resolved_workspace and row.get("workspace") != resolved_workspace:
            row["workspace"] = resolved_workspace
            changed = True
        if target_model and row.get("model") != target_model:
            row["model"] = target_model
            changed = True

    if changed:
        _write_openclaw_config(config_path, config)

    effective_model = row.get("model") if isinstance(row.get("model"), str) and row.get("model") else default_model
    return {
        "ok": True,
        "changed": changed,
        "config_path": str(config_path),
        "agent_id": agent_id,
        "model": effective_model,
        "workspace": row.get("workspace", resolved_workspace),
    }



def _telegram_channel_config(config: Dict[str, Any]) -> Dict[str, Any]:
    channels = config.get("channels")
    if not isinstance(channels, dict):
        return {}
    telegram = channels.get("telegram")
    return telegram if isinstance(telegram, dict) else {}


def _telegram_account_map(telegram_config: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    accounts = telegram_config.get("accounts")
    if isinstance(accounts, dict) and accounts:
        return {str(account_id): row for account_id, row in accounts.items() if isinstance(row, dict)}
    if telegram_config.get("botToken") or telegram_config.get("tokenFile"):
        return {"default": telegram_config}
    return {}


def _binding_entries(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    bindings = config.get("bindings")
    if not isinstance(bindings, list):
        return []
    return [row for row in bindings if isinstance(row, dict)]


def _telegram_binding_lookup(config: Dict[str, Any]) -> Dict[str, str]:
    lookup: Dict[str, str] = {}
    for binding in _binding_entries(config):
        match = binding.get("match")
        agent_id = binding.get("agentId")
        if not isinstance(match, dict) or not isinstance(agent_id, str) or not agent_id.strip():
            continue
        if match.get("channel") != "telegram":
            continue
        account_id = str(match.get("accountId") or "default")
        lookup[account_id] = agent_id.strip()
    return lookup


def _collect_legacy_telegram_account_agent_ids(telegram_config: Dict[str, Any]) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    for account_id, account in _telegram_account_map(telegram_config).items():
        agent_id = account.get("agentId")
        if isinstance(agent_id, str) and agent_id.strip():
            rows.append({"account_id": account_id, "agent_id": agent_id.strip()})
    return rows


def diagnose_openclaw_telegram_config(root: Path, config: Dict[str, Any] | None = None, config_path: Path | None = None) -> Dict[str, Any]:
    resolved_path = config_path or _openclaw_config_path(root)
    issues: List[Dict[str, Any]] = []
    if config is None:
        try:
            config = _read_openclaw_config(resolved_path)
        except FileNotFoundError:
            return {
                "ok": False,
                "config_path": str(resolved_path),
                "issues": [
                    {
                        "code": "config_missing",
                        "severity": "error",
                        "message": f"OpenClaw config not found: {resolved_path}",
                        "fix": "Install or point INNER_WORLD_OPENCLAW_CONFIG_PATH at a valid openclaw.json.",
                    }
                ],
            }

    telegram_config = _telegram_channel_config(config)
    account_map = _telegram_account_map(telegram_config)
    declared_agent_ids = set(_agent_lookup(config))
    binding_lookup = _telegram_binding_lookup(config)
    legacy_account_agent_ids = _collect_legacy_telegram_account_agent_ids(telegram_config)

    if not telegram_config:
        issues.append(
            {
                "code": "telegram_channel_missing",
                "severity": "error",
                "message": "channels.telegram is not configured.",
                "fix": "Run `openclaw channels add telegram` or add channels.telegram to openclaw.json.",
            }
        )
    elif telegram_config.get("enabled") is False:
        issues.append(
            {
                "code": "telegram_channel_disabled",
                "severity": "error",
                "message": "channels.telegram.enabled is false.",
                "fix": "Set channels.telegram.enabled to true and restart the gateway.",
            }
        )

    if telegram_config and not account_map:
        issues.append(
            {
                "code": "telegram_token_missing",
                "severity": "error",
                "message": "No Telegram bot token is configured for any account.",
                "fix": "Set channels.telegram.botToken or channels.telegram.accounts.<id>.botToken.",
            }
        )

    for row in legacy_account_agent_ids:
        issues.append(
            {
                "code": "legacy_account_agent_id",
                "severity": "error",
                "message": (
                    f"channels.telegram.accounts.{row['account_id']}.agentId is no longer valid in OpenClaw 2026.4.8+."
                ),
                "account_id": row["account_id"],
                "agent_id": row["agent_id"],
                "fix": "Move routing to top-level bindings[] and remove agentId from the account block.",
            }
        )

    for account_id, account in account_map.items():
        if not (account.get("botToken") or account.get("tokenFile")):
            issues.append(
                {
                    "code": "telegram_token_missing",
                    "severity": "error",
                    "message": f"Telegram account '{account_id}' has no botToken or tokenFile.",
                    "account_id": account_id,
                    "fix": f"Set channels.telegram.accounts.{account_id}.botToken.",
                }
            )
        bound_agent_id = binding_lookup.get(account_id)
        legacy_agent_id = account.get("agentId") if isinstance(account.get("agentId"), str) else None
        effective_agent_id = (legacy_agent_id or bound_agent_id or "").strip()
        if not effective_agent_id:
            issues.append(
                {
                    "code": "missing_telegram_binding",
                    "severity": "error",
                    "message": f"No Telegram binding exists for account '{account_id}'.",
                    "account_id": account_id,
                    "fix": (
                        "Add bindings[].agentId with match.channel=telegram and match.accountId="
                        f"'{account_id}'."
                    ),
                }
            )
            continue
        if effective_agent_id not in declared_agent_ids:
            issues.append(
                {
                    "code": "agent_not_in_list",
                    "severity": "error",
                    "message": (
                        f"Telegram account '{account_id}' routes to agent '{effective_agent_id}', "
                        "but that agent is missing from agents.list."
                    ),
                    "account_id": account_id,
                    "agent_id": effective_agent_id,
                    "fix": f"Add {{\"id\": \"{effective_agent_id}\"}} to agents.list.",
                }
            )

    for account_id, agent_id in binding_lookup.items():
        if agent_id not in declared_agent_ids:
            issues.append(
                {
                    "code": "agent_not_in_list",
                    "severity": "error",
                    "message": f"bindings route Telegram account '{account_id}' to missing agent '{agent_id}'.",
                    "account_id": account_id,
                    "agent_id": agent_id,
                    "fix": f"Add {{\"id\": \"{agent_id}\"}} to agents.list.",
                }
            )

    dm_policy = str(telegram_config.get("dmPolicy") or "pairing")
    if dm_policy == "pairing":
        issues.append(
            {
                "code": "pairing_required",
                "severity": "info",
                "message": "Telegram DM policy is pairing; first-time users must approve pairing.",
                "fix": "Run `openclaw pairing list telegram` and `openclaw pairing approve telegram <CODE>`.",
            }
        )

    blocking_codes = {
        "config_missing",
        "telegram_channel_missing",
        "telegram_channel_disabled",
        "telegram_token_missing",
        "legacy_account_agent_id",
        "missing_telegram_binding",
        "agent_not_in_list",
    }
    blocking = [issue for issue in issues if issue["code"] in blocking_codes]
    return {
        "ok": not blocking,
        "config_path": str(resolved_path),
        "telegram_account_ids": sorted(account_map),
        "declared_agent_ids": sorted(declared_agent_ids),
        "binding_lookup": binding_lookup,
        "legacy_account_agent_ids": legacy_account_agent_ids,
        "issues": issues,
        "blocking_issue_count": len(blocking),
    }


def migrate_openclaw_telegram_bindings(root: Path, *, apply: bool = False) -> Dict[str, Any]:
    diagnosis = diagnose_openclaw_telegram_config(root)
    if diagnosis.get("issues") and diagnosis["issues"][0].get("code") == "config_missing":
        return {"ok": False, "applied": False, "diagnosis": diagnosis, "changes": []}

    config_path = Path(str(diagnosis["config_path"]))
    config = _read_openclaw_config(config_path)
    telegram_config = _telegram_channel_config(config)
    account_map = _telegram_account_map(telegram_config)
    bindings = _binding_entries(config)
    binding_lookup = _telegram_binding_lookup(config)
    changes: List[Dict[str, Any]] = []

    for account_id, account in account_map.items():
        legacy_agent_id = account.get("agentId")
        if not isinstance(legacy_agent_id, str) or not legacy_agent_id.strip():
            continue
        agent_id = legacy_agent_id.strip()
        if binding_lookup.get(account_id) == agent_id:
            changes.append(
                {
                    "kind": "remove_legacy_account_agent_id",
                    "account_id": account_id,
                    "agent_id": agent_id,
                }
            )
            account.pop("agentId", None)
            continue
        bindings.append(
            {
                "agentId": agent_id,
                "match": {"channel": "telegram", "accountId": account_id},
            }
        )
        binding_lookup[account_id] = agent_id
        account.pop("agentId", None)
        changes.append(
            {
                "kind": "move_account_agent_id_to_binding",
                "account_id": account_id,
                "agent_id": agent_id,
            }
        )

    if changes:
        config["bindings"] = bindings
        channels = config.setdefault("channels", {})
        if isinstance(channels, dict):
            telegram = channels.setdefault("telegram", {})
            if isinstance(telegram, dict) and isinstance(telegram.get("accounts"), dict):
                telegram["accounts"] = account_map
                if len(account_map) > 1 and not telegram.get("defaultAccount"):
                    if "default" in account_map:
                        telegram["defaultAccount"] = "default"
                    else:
                        telegram["defaultAccount"] = sorted(account_map)[0]
                    changes.append(
                        {
                            "kind": "set_default_account",
                            "default_account": telegram["defaultAccount"],
                        }
                    )

    if apply and changes:
        backup_dir = _openclaw_control_backup_dir(root)
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup_path = backup_dir / f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-telegram-bindings-openclaw.json"
        shutil.copy2(config_path, backup_path)
        _write_openclaw_config(config_path, config)
        post_diagnosis = diagnose_openclaw_telegram_config(root)
        return {
            "ok": post_diagnosis["ok"],
            "applied": True,
            "backup_path": str(backup_path),
            "changes": changes,
            "diagnosis": post_diagnosis,
        }

    post_diagnosis = diagnose_openclaw_telegram_config(root, config=config, config_path=config_path)
    return {
        "ok": post_diagnosis["ok"],
        "applied": False,
        "changes": changes,
        "diagnosis": post_diagnosis,
    }


def restart_openclaw_gateway(root: Path) -> Dict[str, Any]:
    restart_result = _run_openclaw_gateway_command(root, "restart")
    health_result = _run_openclaw_gateway_command(root, "health")
    return {
        "restart": restart_result,
        "health": health_result,
        "ok": bool(restart_result["ok"] and health_result["ok"]),
    }


def apply_openclaw_host_telegram_fix(
    root: Path,
    *,
    apply: bool = True,
    restart_gateway: bool = False,
) -> Dict[str, Any]:
    result = migrate_openclaw_telegram_bindings(root, apply=apply)
    if apply and result.get("applied") and restart_gateway:
        gateway = restart_openclaw_gateway(root)
        result["gateway"] = gateway
        result["ok"] = bool(result.get("ok")) and gateway["ok"]
    return result

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


def trim_context_bundle(bundle: Dict[str, Any], policy: Dict[str, Any] | None = None) -> Dict[str, Any]:
    layers = list((bundle.get("context_state") or {}).get("bundle_layers", []) or [])
    effective_policy = policy or bundle.get("context_policy") or {}
    if isinstance(effective_policy, dict) and effective_policy:
        include_layers = [str(value) for value in effective_policy.get("include_layers", []) or [] if str(value).strip()]
        exclude_layers = {str(value) for value in effective_policy.get("exclude_layers", []) or [] if str(value).strip()}
        if include_layers:
            layers = [name for name in layers if name in include_layers]
        if exclude_layers:
            layers = [name for name in layers if name not in exclude_layers]

    trimmed: Dict[str, Any] = {
        "bundle_layers": layers,
        "budget": dict(bundle.get("budget", {}) or {}),
        "session_envelope": dict(bundle.get("session_envelope", {}) or {}),
        "frame_spec": dict(bundle.get("frame_spec", {}) or {}),
        "frame_bundle": dict(bundle.get("frame_bundle", {}) or {}),
        "execution_audit_isolation_v1": bool(bundle.get("execution_audit_isolation_v1", True)),
        "orient_first_compose_v1": bool(bundle.get("orient_first_compose_v1", False)),
        "active_state_snapshot": dict(bundle.get("active_state_snapshot", {}) or {}),
    }
    if "session" in layers:
        trimmed["session_local"] = list(bundle.get("session_local", []) or [])
    if "workspace" in layers:
        trimmed["workspace_local"] = dict(bundle.get("workspace_local", {}) or {})
    if "user" in layers:
        trimmed["user_local"] = dict(bundle.get("user_local", {}) or {})
    if "global" in layers:
        trimmed["global_fallback"] = dict(bundle.get("global_fallback", {}) or {})
    return trimmed


def _format_frame_block_lines(rows: List[Dict[str, Any]]) -> str:
    if not rows:
        return "- none"
    return "\n".join(
        f"- {str(row.get('layer', 'unknown'))}: {str(row.get('summary', '')).strip() or 'no summary'}"
        for row in rows
    )


def _format_provenance_lines(source_refs: List[str]) -> str:
    refs = [str(value).strip() for value in source_refs if str(value).strip()]
    if not refs:
        return "- none"
    return "\n".join(f"- {value}" for value in refs[:6])


def _execution_audit_isolation_enabled(trimmed_bundle: Mapping[str, Any]) -> bool:
    return bool(trimmed_bundle.get("execution_audit_isolation_v1", True))


def _enforce_model_bound_isolation(trimmed_bundle: Mapping[str, Any]) -> None:
    frame_bundle = dict(trimmed_bundle.get("frame_bundle", {}) or {})
    if frame_bundle:
        validate_model_bound_payload(frame_bundle, label="FrameBundle")
    frame_audit = trimmed_bundle.get("frame_audit")
    if isinstance(frame_audit, dict) and frame_audit:
        validate_model_bound_payload(frame_audit, label="FrameAudit")


def compose_execution_message(control_packet: Dict[str, Any], trimmed_bundle: Dict[str, Any], user_text: str) -> str:
    isolation_enabled = _execution_audit_isolation_enabled(trimmed_bundle)
    if isolation_enabled:
        _enforce_model_bound_isolation(trimmed_bundle)

    if trimmed_bundle.get("orient_first_compose_v1"):
        from .orient_first_compose import ORIENTATION_MAX_CHARS, compose_orient_first_message

        return compose_orient_first_message(
            control_packet,
            trimmed_bundle,
            user_text,
            orientation_max_chars=int(trimmed_bundle.get("orientation_max_chars", ORIENTATION_MAX_CHARS) or ORIENTATION_MAX_CHARS),
        )

    policy = dict(control_packet.get("context_policy", {}) or {})
    layers = list(trimmed_bundle.get("bundle_layers", []) or [])
    constraints = [str(value) for value in control_packet.get("steering_constraints", []) or [] if str(value).strip()]
    behavior_ids = [str(value) for value in control_packet.get("bridge_behaviors", []) or [] if str(value).strip()]
    envelope = dict(trimmed_bundle.get("session_envelope", {}) or {})
    frame_spec = dict(trimmed_bundle.get("frame_spec", {}) or {})
    frame_bundle = dict(trimmed_bundle.get("frame_bundle", {}) or {})

    session_block = "No session-local events disclosed."
    if "session" in layers:
        events = trimmed_bundle.get("session_local", []) or []
        if events:
            session_block = "\n".join(
                f"- {row.get('actor', 'unknown')}: {row.get('content', '')[:240]}"
                for row in events[-6:]
            )

    workspace_block = "No workspace-local context disclosed."
    workspace = trimmed_bundle.get("workspace_local", {}) or {}
    if "workspace" in layers and workspace:
        workspace_block = json.dumps(workspace, ensure_ascii=False, indent=2)

    user_block = "No user-local patterns disclosed."
    if "user" in layers:
        user_local = trimmed_bundle.get("user_local", {}) or {}
        if user_local:
            user_block = json.dumps(user_local, ensure_ascii=False, indent=2)

    global_block = "No global retrieval disclosed."
    if "global" in layers:
        retrieval = trimmed_bundle.get("global_fallback", {}) or {}
        seeds = list(retrieval.get("seed_capsules", []) or [])[:4]
        if seeds:
            global_block = "\n".join(
                f"- {row.get('label', row.get('capsule_id', 'capsule'))}: {str(row.get('summary', ''))[:180]}"
                for row in seeds
            )
        elif retrieval.get("count"):
            global_block = f"Retrieval count: {retrieval.get('count')}"

    constraint_block = "\n".join(f"- {item}" for item in constraints) if constraints else "- Stay inside disclosed context."
    frame_included_block = _format_frame_block_lines(list(frame_bundle.get("included_blocks", []) or []))
    provenance_block = _format_provenance_lines(
        list((frame_bundle.get("provenance_summary", {}) or {}).get("source_refs", []) or [])
    )
    message_parts = [
            "Inner World bridge execution request.",
            "Answer the user inside the control packet bounds below.",
            "",
            f"Active topic: {control_packet.get('active_topic', '')}",
            f"User goal: {control_packet.get('user_goal', '')}",
            f"Reasoning posture: {control_packet.get('reasoning_posture', '')}",
            f"Pipeline: {control_packet.get('pipeline_id', '')}",
            f"Bridge behaviors: {', '.join(behavior_ids) if behavior_ids else 'none'}",
            f"Context policy mode: {policy.get('mode', '')}",
            f"Depth mode: {policy.get('depth_mode', '')}",
            f"Session envelope mode: {envelope.get('mode', '')}",
            f"Learning mode: {envelope.get('learning_mode', '')}",
            f"Persistence mode: {envelope.get('persistence_mode', '')}",
            f"Frame id: {frame_spec.get('frame_id', frame_bundle.get('frame_id', ''))}",
            f"Frame assembly: {frame_bundle.get('assembly_status', '')}",
            "",
            "Steering constraints:",
            constraint_block,
            "",
            "Included frame blocks:",
            frame_included_block,
        ]
    if not isolation_enabled:
        frame_suppressed_block = _format_frame_block_lines(list(frame_bundle.get("suppressed_blocks", []) or []))
        message_parts.extend(
            [
                "",
                "Suppressed frame blocks:",
                frame_suppressed_block,
            ]
        )
    message_parts.extend(
        [
            "",
            "Frame provenance:",
            provenance_block,
            "",
            "Session local:",
            session_block,
            "",
            "Workspace local:",
            workspace_block,
            "",
            "User local:",
            user_block,
            "",
            "Global retrieval:",
            global_block,
            "",
            f"User message: {user_text}",
            "",
            "Instructions:",
            "- Answer directly for the user.",
            "- Honor steering constraints and disclosed layers only.",
            "- Do not invent evidence outside the bundle.",
            "- Do not mention internal bridge, routing, frame, or context-assembly mechanics.",
            "- End with one concrete next move.",
        ]
    )
    return "\n".join(message_parts)


def request_bridge_execution_reply(
    root: Path,
    control_packet: Dict[str, Any],
    trimmed_bundle: Dict[str, Any],
    user_text: str,
    *,
    backend: Dict[str, Any] | None = None,
    bridge_config: Dict[str, Any] | None = None,
    session_id: str = "",
) -> Dict[str, Any]:
    from .bridge_controller import load_bridge_config

    resolved_backend = backend or resolve_chat_backend(root)
    resolved_bridge = bridge_config or load_bridge_config(root)
    openclaw = dict(resolved_backend.get("openclaw", {}) or {})
    openclaw["agent"] = resolved_bridge.get("agent") or openclaw.get("agent") or "thought_tube_router"
    openclaw["thinking"] = resolved_bridge.get("thinking") or openclaw.get("thinking") or "low"
    openclaw["timeout_seconds"] = int(
        resolved_bridge.get("timeout_seconds") or openclaw.get("timeout_seconds") or 25
    )

    message = compose_execution_message(control_packet, trimmed_bundle, user_text)
    command = [
        "openclaw",
        "agent",
        "--agent",
        openclaw["agent"],
        "--message",
        message,
        "--thinking",
        openclaw["thinking"],
        "--json",
    ]
    if session_id:
        command.extend(["--session-id", session_id])
    if resolved_backend.get("id") == "openclaw_local":
        command.append("--local")
    if openclaw.get("deliver"):
        command.append("--deliver")

    completed = subprocess.run(
        command,
        cwd=root,
        capture_output=True,
        text=True,
        timeout=int(openclaw["timeout_seconds"]),
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
    usage: Dict[str, Any] = {}
    if isinstance(payload, dict):
        reply_text = _extract_text_from_json(payload) or stdout
        usage = _extract_usage_from_json(payload)

    if not str(reply_text).strip():
        raise RuntimeError("openclaw returned an empty reply")

    prompt_tokens = usage.get("prompt_tokens") or estimate_token_count(message)
    completion_tokens = usage.get("completion_tokens") or estimate_token_count(str(reply_text))
    record_actual_cost(
        root,
        component="bridge_execution",
        operation="reasoning_execution",
        provider="openclaw",
        model=usage.get("model") or resolved_backend.get("id"),
        input_tokens=prompt_tokens,
        output_tokens=completion_tokens,
        usd_cost=usage.get("usd_cost"),
        token_source="actual" if usage.get("prompt_tokens") or usage.get("completion_tokens") else "estimated",
        metadata={
            "session_id": session_id,
            "backend_id": resolved_backend.get("id"),
            "thinking": openclaw["thinking"],
            "pipeline_id": control_packet.get("pipeline_id", ""),
        },
    )
    return {
        "content": str(reply_text).strip(),
        "backend_id": resolved_backend.get("id"),
        "agent": openclaw["agent"],
    }


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
