"""Deterministic token/block budget allocator for disclosure (CAE-003B)."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Sequence, Set

from .storage import read_json


MODULE_ID = "kernel.disclosure.budget_allocator"
CONTRACT_VERSION = "1.0"
ESTIMATOR_VERSION = "1.0"
RESERVATION_VERSION = "1.0"

DEFAULT_RESERVATIONS = {
    "system_tokens": 120,
    "answer_tokens": 256,
    "orientation_max_tokens": 120,
}

DEFAULT_TOKEN_BUDGET_BY_DEPTH = {
    "focused": 800,
    "contextual": 1200,
    "deep": 1600,
    "incognito": 0,
}

LAYER_PRIORITY = {
    "session": 0,
    "explicit_pin": 1,
    "workspace": 2,
    "user": 3,
    "global": 4,
}

PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "ESTIMATOR_VERSION",
    "RESERVATION_VERSION",
    "DEFAULT_RESERVATIONS",
    "LAYER_PRIORITY",
    "load_budget_allocator_config",
    "deterministic_budget_enforcement_enabled",
    "resolve_token_budget",
    "should_skip_budget_enforcement",
    "estimate_tokens",
    "estimate_orientation_tokens",
    "build_budget_reservation",
    "allocate_included_blocks",
    "apply_frame_budget_to_assembly",
    "budget_policy_hash",
)
__all__ = list(PUBLIC_API)

_TOKEN_PATTERN = re.compile(r"\S+")


def _runtime_config_path(root: Path) -> Path:
    return root / "product" / "inner_world_v1" / "config" / "runtime.json"


def load_budget_allocator_config(root: Path) -> Dict[str, Any]:
    runtime = read_json(_runtime_config_path(root), default={}) or {}
    bridge = runtime.get("bridge", {}) or {}
    disclosure = runtime.get("disclosure", {}) or {}
    reservations = dict(DEFAULT_RESERVATIONS)
    reservations.update(dict(disclosure.get("budget_reservations", {}) or {}))
    return {
        "deterministic_budget_enforcement_v1": bool(
            bridge.get(
                "deterministic_budget_enforcement_v1",
                disclosure.get("deterministic_budget_enforcement_v1", True),
            )
        ),
        "reservations": reservations,
        "reservation_version": str(disclosure.get("reservation_version", RESERVATION_VERSION) or RESERVATION_VERSION),
        "estimator_version": str(disclosure.get("estimator_version", ESTIMATOR_VERSION) or ESTIMATOR_VERSION),
    }


def deterministic_budget_enforcement_enabled(root: Path) -> bool:
    return bool(load_budget_allocator_config(root)["deterministic_budget_enforcement_v1"])


def resolve_token_budget(
    token_budget: int,
    *,
    depth_mode: str = "contextual",
    policy_specified: bool = False,
) -> int:
    budget = max(0, int(token_budget or 0))
    if budget > 0:
        return budget
    if policy_specified:
        return 0
    return int(DEFAULT_TOKEN_BUDGET_BY_DEPTH.get(str(depth_mode or "contextual"), 1200))


def should_skip_budget_enforcement(token_budget: int) -> bool:
    return max(0, int(token_budget or 0)) <= 0


def estimate_tokens(text: str) -> int:
    """Deterministic whitespace token estimator (versioned, no external tokenizer)."""
    normalized = str(text or "").strip()
    if not normalized:
        return 0
    return len(_TOKEN_PATTERN.findall(normalized))


def estimate_orientation_tokens(
    context_state: Mapping[str, Any],
    *,
    orientation_cap: int,
) -> int:
    parts = [
        str(context_state.get("active_topic", "") or ""),
        str(context_state.get("user_goal", "") or ""),
        str(context_state.get("reasoning_posture", "") or ""),
        str(context_state.get("object_scope", "") or ""),
    ]
    return min(max(0, int(orientation_cap)), estimate_tokens(" ".join(part for part in parts if part)))


def build_budget_reservation(
    *,
    token_budget: int,
    reservations: Mapping[str, Any] | None = None,
    orientation_tokens: int = 0,
) -> Dict[str, Any]:
    reservation = dict(DEFAULT_RESERVATIONS)
    reservation.update(dict(reservations or {}))
    system_tokens = max(0, int(reservation.get("system_tokens", 0) or 0))
    answer_tokens = max(0, int(reservation.get("answer_tokens", 0) or 0))
    orientation_cap = max(0, int(reservation.get("orientation_max_tokens", 0) or 0))
    orientation_used = min(orientation_cap, max(0, int(orientation_tokens)))
    total_budget = max(0, int(token_budget))
    available_for_blocks = max(0, total_budget - system_tokens - answer_tokens - orientation_used)
    return {
        "estimator_version": ESTIMATOR_VERSION,
        "reservation_version": RESERVATION_VERSION,
        "token_budget": total_budget,
        "system_tokens": system_tokens,
        "answer_tokens": answer_tokens,
        "orientation_cap_tokens": orientation_cap,
        "orientation_tokens": orientation_used,
        "available_for_blocks": available_for_blocks,
    }


def budget_policy_hash(
    *,
    token_budget: int,
    reservations: Mapping[str, Any],
    corpus_revision: str = "",
) -> str:
    payload = {
        "estimator_version": ESTIMATOR_VERSION,
        "reservation_version": RESERVATION_VERSION,
        "token_budget": int(token_budget),
        "reservations": dict(reservations),
        "corpus_revision": str(corpus_revision or ""),
    }
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def _block_cost(block: Mapping[str, Any]) -> int:
    estimate = int(block.get("token_estimate", 0) or 0)
    if estimate > 0:
        return estimate
    return max(1, estimate_tokens(str(block.get("summary", "") or "")))


def _sort_blocks(
    blocks: Sequence[Mapping[str, Any]],
    *,
    pinned_block_ids: Set[str],
) -> List[Dict[str, Any]]:
    return sorted(
        [dict(row) for row in blocks],
        key=lambda row: (
            0 if str(row.get("block_id", "")) in pinned_block_ids else 1,
            LAYER_PRIORITY.get(str(row.get("layer", "")), 99),
            str(row.get("block_id", "")),
        ),
    )


def allocate_included_blocks(
    blocks: Sequence[Mapping[str, Any]],
    *,
    token_budget: int,
    orientation_tokens: int,
    reservations: Mapping[str, Any] | None = None,
    required_layers: Iterable[str] | None = None,
    pinned_block_ids: Iterable[str] | None = None,
    corpus_revision: str = "",
) -> Dict[str, Any]:
    reservation = build_budget_reservation(
        token_budget=token_budget,
        reservations=reservations,
        orientation_tokens=orientation_tokens,
    )
    available = int(reservation["available_for_blocks"])
    required = {str(layer) for layer in (required_layers or [])}
    pinned = {str(value) for value in (pinned_block_ids or []) if str(value).strip()}
    ordered = _sort_blocks(blocks, pinned_block_ids=pinned)

    included: List[Dict[str, Any]] = []
    dropped: List[Dict[str, Any]] = []
    drop_ledger: List[Dict[str, Any]] = []
    used_tokens = 0

    for block in ordered:
        cost = _block_cost(block)
        layer = str(block.get("layer", "") or "")
        block_id = str(block.get("block_id", "") or "")
        is_required = layer in required or block_id in pinned
        if used_tokens + cost <= available:
            included.append(block)
            used_tokens += cost
            continue
        if is_required:
            return {
                "included_blocks": [],
                "dropped_blocks": ordered,
                "drop_ledger": [
                    {
                        "block_id": block_id,
                        "layer": layer,
                        "token_estimate": cost,
                        "reason_code": "budget_insufficient_required",
                        "reason": "Required whole block could not fit remaining evidence budget",
                    }
                ],
                "result_status": "abstained_insufficient_budget",
                "budget_summary": {
                    **reservation,
                    "evidence_tokens": 0,
                    "remaining_tokens": max(0, available),
                },
                "budget_ledger": {
                    "token_budget": reservation["token_budget"],
                    "orientation_tokens": reservation["orientation_tokens"],
                    "evidence_tokens": 0,
                    "dropped_tokens": sum(_block_cost(row) for row in ordered),
                },
                "policy_hash": budget_policy_hash(
                    token_budget=token_budget,
                    reservations=reservation,
                    corpus_revision=corpus_revision,
                ),
            }
        dropped.append(block)
        drop_ledger.append(
            {
                "block_id": block_id,
                "layer": layer,
                "token_estimate": cost,
                "reason_code": "budget_insufficient_optional",
                "reason": "Optional whole block dropped to remain within effective budget",
            }
        )

    evidence_tokens = sum(_block_cost(row) for row in included)
    return {
        "included_blocks": included,
        "dropped_blocks": dropped,
        "drop_ledger": drop_ledger,
        "result_status": "disclosed" if included else "empty_grant_excludes_all",
        "budget_summary": {
            **reservation,
            "evidence_tokens": evidence_tokens,
            "remaining_tokens": max(0, available - evidence_tokens),
        },
        "budget_ledger": {
            "token_budget": reservation["token_budget"],
            "orientation_tokens": reservation["orientation_tokens"],
            "evidence_tokens": evidence_tokens,
            "dropped_tokens": sum(_block_cost(row) for row in dropped),
        },
        "policy_hash": budget_policy_hash(
            token_budget=token_budget,
            reservations=reservation,
            corpus_revision=corpus_revision,
        ),
    }


def apply_frame_budget_to_assembly(
    assembly: MutableMapping[str, Any],
    *,
    context_state: Mapping[str, Any],
    effective_grant: Mapping[str, Any],
    root: Path,
    corpus_revision: str = "",
    session_event_count: int = 0,
    pinned_block_ids: Sequence[str] | None = None,
) -> Dict[str, Any]:
    config = load_budget_allocator_config(root)
    depth_mode = str(context_state.get("depth_mode", "contextual") or "contextual")
    policy_specified = bool(effective_grant.get("token_budget_specified"))
    token_budget = resolve_token_budget(
        int(effective_grant.get("token_budget", 0) or 0),
        depth_mode=depth_mode,
        policy_specified=policy_specified,
    )
    if should_skip_budget_enforcement(token_budget):
        return {
            "drop_ledger": [],
            "budget_ledger": {},
            "budget_summary": {
                "enforcement_skipped": True,
                "reason": "token_budget_unconfigured",
                "token_budget": 0,
            },
            "policy_hash": "",
            "result_status": str(assembly.get("result_status", "") or "disclosed"),
            "dropped_blocks": [],
            "estimator_version": config.get("estimator_version", ESTIMATOR_VERSION),
            "reservation_version": config.get("reservation_version", RESERVATION_VERSION),
            "enforcement_enabled": False,
        }

    reservations = dict(config.get("reservations", DEFAULT_RESERVATIONS))
    orientation_tokens = estimate_orientation_tokens(
        context_state,
        orientation_cap=int(reservations.get("orientation_max_tokens", 0) or 0),
    )
    required_layers: Set[str] = set()
    if session_event_count > 0 and any(row.get("layer") == "session" for row in assembly.get("included_blocks", []) or []):
        required_layers.add("session")
    for layer in effective_grant.get("effective_layers", []) or []:
        if str(layer) == "explicit_pin":
            required_layers.add("explicit_pin")

    allocation = allocate_included_blocks(
        list(assembly.get("included_blocks", []) or []),
        token_budget=token_budget,
        orientation_tokens=orientation_tokens,
        reservations=reservations,
        required_layers=required_layers,
        pinned_block_ids=pinned_block_ids,
        corpus_revision=corpus_revision,
    )

    assembly["included_blocks"] = allocation["included_blocks"]
    assembly["result_status"] = allocation["result_status"]
    assembly["budget_summary"] = allocation["budget_summary"]
    if allocation["included_blocks"]:
        assembly["assembly_status"] = "partial" if allocation["dropped_blocks"] else assembly.get("assembly_status", "complete")
    else:
        assembly["assembly_status"] = "empty"
    assembly["assembly_metrics"] = {
        **dict(assembly.get("assembly_metrics", {}) or {}),
        "estimated_token_cost": sum(_block_cost(row) for row in allocation["included_blocks"]),
        "dropped_block_count": len(allocation["dropped_blocks"]),
        "orientation_token_cost": orientation_tokens,
        "budget_remaining_tokens": allocation["budget_summary"].get("remaining_tokens", 0),
    }
    assembly["provenance_summary"] = {
        **dict(assembly.get("provenance_summary", {}) or {}),
        "included_layer_count": len(allocation["included_blocks"]),
    }

    return {
        "drop_ledger": allocation["drop_ledger"],
        "budget_ledger": allocation["budget_ledger"],
        "budget_summary": allocation["budget_summary"],
        "policy_hash": allocation["policy_hash"],
        "result_status": allocation["result_status"],
        "dropped_blocks": allocation["dropped_blocks"],
        "estimator_version": config.get("estimator_version", ESTIMATOR_VERSION),
        "reservation_version": config.get("reservation_version", RESERVATION_VERSION),
        "enforcement_enabled": bool(config.get("deterministic_budget_enforcement_v1", True)),
    }
