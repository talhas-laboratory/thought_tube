from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Tuple

from .chat_backends import ensure_bridge_openclaw_agent, resolve_chat_backend
from .models import ContextPolicy, ControlPacket
from .reasoning_bridge import BRIDGE_BEHAVIOR_RULES, load_bridge_behavior_specs
from .storage import read_json, utc_now


MODULE_ID = "kernel.reasoning.bridge_controller"
CONTRACT_VERSION = "1.0"
PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "load_bridge_config",
    "build_bridge_candidate_package",
    "compose_bridge_prompt",
    "invoke_bridge_agent",
    "parse_control_packet",
    "validate_control_packet",
    "classify_with_agent",
)
__all__ = list(PUBLIC_API)

VALID_CONTEXT_MODES = {
    "none",
    "recent_local",
    "semantic_narrow",
    "graph_contextual",
    "cross_ocean_exploration",
    "evidence_strict",
}
VALID_DEPTH_MODES = {"focused", "contextual", "deep", "incognito"}
VALID_ROUTING_SOURCES = {"agent", "heuristic", "hybrid"}
DEPTH_POLICY_MAXIMA = {
    "focused": {"retrieval_limit": 4, "neighbor_limit": 2},
    "contextual": {"retrieval_limit": 6, "neighbor_limit": 4},
    "deep": {"retrieval_limit": 8, "neighbor_limit": 6},
    "incognito": {"retrieval_limit": 0, "neighbor_limit": 0},
}
DEFAULT_BRIDGE_CONFIG = {
    "enabled": True,
    "agent": "thought_tube_router",
    "model": "moonshot/kimi-k2.5",
    "thinking": "low",
    "timeout_seconds": 25,
    "fallback": "heuristic",
    "emit_heuristic_preview": True,
    "execution_mode": "operators",
    "execution_audit_isolation_v1": True,
    "effective_grant_normalization_v1": True,
    "openclaw_mode": "auto",
}
MAX_BRIDGE_PROMPT_CHARS = 48_000


def _slim_capsule_summary(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "capsule_id": str(row.get("capsule_id", "") or row.get("id", "")),
        "label": str(row.get("label", ""))[:120],
        "summary": str(row.get("summary", ""))[:180],
        "score": row.get("score"),
    }


def _slim_heuristic_preview(preview: Dict[str, Any] | None) -> Dict[str, Any]:
    if not preview:
        return {}
    attributes = preview.get("attributes", {}) or {}
    return {
        "active_topic": preview.get("active_topic", ""),
        "depth_mode": preview.get("depth_mode", ""),
        "user_goal": preview.get("user_goal", ""),
        "object_scope": preview.get("object_scope", ""),
        "reasoning_posture": preview.get("reasoning_posture", ""),
        "bridge_behavior_ids": list(attributes.get("bridge_behavior_ids", []) or []),
    }


def _truncate_bridge_prompt(prompt: str) -> str:
    if len(prompt) <= MAX_BRIDGE_PROMPT_CHARS:
        return prompt
    return (
        prompt[: MAX_BRIDGE_PROMPT_CHARS - 120]
        + "\n\n[bridge prompt truncated for transport budget]\n"
    )


def _runtime_config_path(root: Path) -> Path:
    return root / "product" / "inner_world_v1" / "config" / "runtime.json"


def load_bridge_config(root: Path) -> Dict[str, Any]:
    runtime = read_json(_runtime_config_path(root), default={}) or {}
    bridge = dict(runtime.get("bridge", {}) or {})
    config = dict(DEFAULT_BRIDGE_CONFIG)
    config.update({key: value for key, value in bridge.items() if key in DEFAULT_BRIDGE_CONFIG})
    tracking = bridge.get("tracking")
    if isinstance(tracking, dict):
        config["tracking"] = tracking
    enabled = os.getenv("INNER_WORLD_BRIDGE_ENABLED")
    if enabled is not None:
        config["enabled"] = str(enabled).lower() in {"1", "true", "yes", "on"}
    agent = os.getenv("INNER_WORLD_BRIDGE_AGENT")
    if agent:
        config["agent"] = agent
    timeout = os.getenv("INNER_WORLD_BRIDGE_TIMEOUT")
    if timeout:
        config["timeout_seconds"] = int(timeout)
    execution_mode = os.getenv("INNER_WORLD_BRIDGE_EXECUTION_MODE")
    if execution_mode:
        config["execution_mode"] = execution_mode
    model = os.getenv("INNER_WORLD_BRIDGE_MODEL")
    if model:
        config["model"] = model
    openclaw_mode = os.getenv("INNER_WORLD_BRIDGE_OPENCLAW_MODE")
    if openclaw_mode:
        config["openclaw_mode"] = openclaw_mode
    return config


def _bridge_use_local_openclaw(root: Path, bridge_config: Dict[str, Any], backend: Dict[str, Any]) -> bool:
    if backend.get("id") == "openclaw_local":
        return True
    mode = str(bridge_config.get("openclaw_mode", DEFAULT_BRIDGE_CONFIG["openclaw_mode"]) or "gateway").strip().lower()
    if mode == "local":
        return True
    if mode == "gateway":
        return False
    if mode != "auto":
        return False
    try:
        completed = subprocess.run(
            ["openclaw", "gateway", "health"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return True
    return completed.returncode != 0


def build_bridge_candidate_package(
    root: Path,
    request: Dict[str, Any],
    *,
    retrieval_bundle: Dict[str, Any],
    bridge_state: Dict[str, Any],
    heuristic_preview: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    behavior_rules = load_bridge_behavior_specs(root)
    behavior_menu = [
        {
            "behavior_id": rule["behavior_id"],
            "preferred_pipeline": rule.get("preferred_pipeline", ""),
            "reasoning_posture": rule.get("reasoning_posture", ""),
            "response_directives": rule.get("response_directives", []),
        }
        for rule in behavior_rules.values()
    ]
    seed_capsules = [_slim_capsule_summary(row) for row in list(retrieval_bundle.get("seed_capsules", []) or [])[:6]]
    related_capsules = [_slim_capsule_summary(row) for row in list(retrieval_bundle.get("related_capsules", []) or [])[:4]]
    return {
        "request": {
            "request_id": request.get("request_id", ""),
            "session_id": request.get("session_id", ""),
            "raw_text": request.get("raw_text", ""),
            "domain_hints": list(request.get("domain_hints", []) or []),
            "caller_hints": dict(request.get("caller_hints", {}) or {}),
        },
        "heuristic_preview": _slim_heuristic_preview(heuristic_preview),
        "retrieval_candidates": {
            "query": retrieval_bundle.get("query", ""),
            "count": int(retrieval_bundle.get("count", 0) or 0),
            "seed_capsules": seed_capsules,
            "related_capsules": related_capsules,
        },
        "behavior_menu": behavior_menu,
        "bridge_state_summary": {
            "behavior_pattern_count": len(bridge_state.get("behavior_patterns", []) or []),
            "presentation_mode": (bridge_state.get("presentation", {}) or {}).get("current_mode", ""),
        },
        "generated_at": utc_now(),
    }


def compose_bridge_prompt(package: Dict[str, Any]) -> str:
    request = package.get("request", {}) or {}
    preview = package.get("heuristic_preview", {}) or {}
    candidates = package.get("retrieval_candidates", {}) or {}
    behavior_menu = package.get("behavior_menu", []) or []
    lines = [
        "Bridge control-plane request.",
        "Return JSON only. Do not answer the user directly.",
        "",
        f"Turn: {request.get('raw_text', '')}",
        f"Session: {request.get('session_id', '')}",
        f"Heuristic preview: {json.dumps(preview, ensure_ascii=False)}",
        "",
        "Retrieval candidates:",
        json.dumps(candidates, ensure_ascii=False, indent=2),
        "",
        "Behavior menu:",
        json.dumps(behavior_menu, ensure_ascii=False, indent=2),
        "",
        "Required JSON shape:",
        json.dumps(
            {
                "packet_id": "pkt-...",
                "request_id": request.get("request_id", ""),
                "active_topic": "...",
                "object_scope": "same_main",
                "object_id": "...",
                "user_goal": "explore",
                "reasoning_posture": "exploratory",
                "factual_anchor_level": "medium",
                "bridge_behaviors": ["creative_expansion"],
                "pipeline_id": "intuition_expansion_v1",
                "context_policy": {
                    "mode": "semantic_narrow",
                    "depth_mode": "contextual",
                    "token_budget": 1200,
                    "include_layers": ["session", "workspace", "user", "global"],
                    "exclude_layers": [],
                    "cross_ocean": False,
                    "retrieval_limit": 6,
                    "neighbor_limit": 4,
                },
                "steering_constraints": [],
                "confidence": 0.8,
                "routing_source": "agent",
            },
            ensure_ascii=False,
            indent=2,
        ),
    ]
    return _truncate_bridge_prompt("\n".join(lines))


def _strip_markdown_json_fence(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.I)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned.strip()


def _packet_dict_from_candidate(candidate: Any) -> Dict[str, Any] | None:
    if isinstance(candidate, dict) and candidate.get("packet_id") and candidate.get("context_policy"):
        return candidate
    if not isinstance(candidate, str):
        return None
    candidate = _strip_markdown_json_fence(candidate.strip())
    if not candidate:
        return None
    try:
        nested = json.loads(candidate)
    except json.JSONDecodeError:
        nested = None
    if isinstance(nested, dict) and nested.get("packet_id") and nested.get("context_policy"):
        return nested
    match = re.search(r"\{.*\}", candidate, re.S)
    if not match:
        return None
    try:
        nested = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    if isinstance(nested, dict) and nested.get("packet_id") and nested.get("context_policy"):
        return nested
    return None


def _extract_control_packet_json(stdout: str) -> Dict[str, Any] | None:
    text = stdout.strip()
    if not text:
        return None
    candidates: List[Any] = []
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        payload = None
    if isinstance(payload, dict):
        candidates.append(payload)
        for key in ("reply", "text", "content", "message"):
            if payload.get(key):
                candidates.append(payload[key])
        result = payload.get("result")
        if isinstance(result, dict):
            candidates.append(result)
            for key in ("reply", "text", "content", "message"):
                if result.get(key):
                    candidates.append(result[key])
            payloads = result.get("payloads")
            if isinstance(payloads, list):
                for item in payloads:
                    if not isinstance(item, dict):
                        continue
                    for key in ("text", "content", "message", "reply"):
                        if item.get(key):
                            candidates.append(item[key])
    else:
        candidates.append(text)
    for candidate in candidates:
        packet = _packet_dict_from_candidate(candidate)
        if packet is not None:
            return packet
    return None


def parse_control_packet(stdout: str) -> Dict[str, Any] | None:
    return _extract_control_packet_json(stdout)


def validate_control_packet(payload: Dict[str, Any], *, root: Path | None = None) -> Tuple[ControlPacket | None, List[str]]:
    warnings: List[str] = []
    if not isinstance(payload, dict):
        return None, ["payload_not_object"]
    if not payload.get("packet_id") or not payload.get("context_policy"):
        return None, ["missing_required_fields"]

    policy_payload = dict(payload.get("context_policy", {}) or {})
    depth_mode = str(policy_payload.get("depth_mode", "focused")).strip().lower()
    if depth_mode not in VALID_DEPTH_MODES:
        warnings.append(f"depth_mode_coerced:{depth_mode}")
        depth_mode = "focused"
    policy_payload["depth_mode"] = depth_mode

    mode = str(policy_payload.get("mode", "semantic_narrow")).strip().lower()
    if mode not in VALID_CONTEXT_MODES:
        warnings.append(f"context_mode_coerced:{mode}")
        mode = "semantic_narrow"
    policy_payload["mode"] = mode

    maxima = DEPTH_POLICY_MAXIMA[depth_mode]
    retrieval_limit = int(policy_payload.get("retrieval_limit", maxima["retrieval_limit"]) or 0)
    neighbor_limit = int(policy_payload.get("neighbor_limit", maxima["neighbor_limit"]) or 0)
    if retrieval_limit > maxima["retrieval_limit"]:
        warnings.append("retrieval_limit_clamped")
        retrieval_limit = maxima["retrieval_limit"]
    if neighbor_limit > maxima["neighbor_limit"]:
        warnings.append("neighbor_limit_clamped")
        neighbor_limit = maxima["neighbor_limit"]
    policy_payload["retrieval_limit"] = retrieval_limit
    policy_payload["neighbor_limit"] = neighbor_limit
    policy_payload["cross_ocean"] = False

    behavior_rules = load_bridge_behavior_specs(root) if root is not None else BRIDGE_BEHAVIOR_RULES
    known_behaviors = list(behavior_rules)
    requested_behaviors = [str(value) for value in payload.get("bridge_behaviors", []) or []]
    filtered_behaviors = [behavior_id for behavior_id in requested_behaviors if behavior_id in known_behaviors]
    if filtered_behaviors != requested_behaviors:
        warnings.append("bridge_behaviors_filtered")
    payload = dict(payload)
    payload["bridge_behaviors"] = filtered_behaviors
    payload["context_policy"] = policy_payload

    routing_source = str(payload.get("routing_source", "agent")).strip().lower()
    if routing_source not in VALID_ROUTING_SOURCES:
        warnings.append(f"routing_source_coerced:{routing_source}")
        routing_source = "agent"
    payload["routing_source"] = routing_source

    confidence = float(payload.get("confidence", 0.0) or 0.0)
    if confidence > 1.0:
        warnings.append("confidence_clamped")
        confidence = 1.0
    if confidence < 0.0:
        confidence = 0.0
    payload["confidence"] = confidence

    packet = ControlPacket.from_dict(payload)
    return packet, warnings


def invoke_bridge_agent(root: Path, prompt: str, *, config: Dict[str, Any] | None = None) -> str:
    bridge_config = config or load_bridge_config(root)
    agent_id = str(bridge_config.get("agent", DEFAULT_BRIDGE_CONFIG["agent"]))
    model_id = str(bridge_config.get("model", DEFAULT_BRIDGE_CONFIG.get("model", "")) or "")
    try:
        ensure_bridge_openclaw_agent(root, agent_id=agent_id, model_id=model_id)
    except (FileNotFoundError, ValueError) as exc:
        raise RuntimeError(f"bridge_agent_provision_failed:{exc}") from exc
    backend = resolve_chat_backend(root)
    command = [
        "openclaw",
        "agent",
        "--agent",
        str(bridge_config.get("agent", DEFAULT_BRIDGE_CONFIG["agent"])),
        "--thinking",
        str(bridge_config.get("thinking", DEFAULT_BRIDGE_CONFIG["thinking"])),
        "--message",
        prompt,
        "--json",
    ]
    if _bridge_use_local_openclaw(root, bridge_config, backend):
        command.append("--local")
    completed = subprocess.run(
        command,
        cwd=root,
        capture_output=True,
        text=True,
        timeout=int(bridge_config.get("timeout_seconds", DEFAULT_BRIDGE_CONFIG["timeout_seconds"])),
        check=False,
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "").strip().replace("\n", " ")[:240]
        raise RuntimeError(f"bridge_agent_exit_{completed.returncode}:{detail or 'no_output'}")
    return completed.stdout


def classify_with_agent(
    root: Path,
    request: Dict[str, Any],
    *,
    retrieval_bundle: Dict[str, Any],
    bridge_state: Dict[str, Any],
    heuristic_preview: Dict[str, Any] | None,
) -> Tuple[ControlPacket, Dict[str, Any]] | None:
    package = build_bridge_candidate_package(
        root,
        request,
        retrieval_bundle=retrieval_bundle,
        bridge_state=bridge_state,
        heuristic_preview=heuristic_preview,
    )
    prompt = compose_bridge_prompt(package)
    config = load_bridge_config(root)
    try:
        stdout = invoke_bridge_agent(root, prompt, config=config)
    except (RuntimeError, subprocess.TimeoutExpired, FileNotFoundError):
        return None
    raw_payload = parse_control_packet(stdout)
    if not raw_payload:
        return None
    packet, warnings = validate_control_packet(raw_payload, root=root)
    if packet is None:
        return None
    metadata = {
        "routing_source": packet.routing_source,
        "validation_warnings": warnings,
        "raw_payload": raw_payload,
    }
    return packet, metadata
