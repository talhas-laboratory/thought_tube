"""Bounded ActiveState continuity across turns and adapters (CAE-008)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Mapping, Tuple

from .disclosure_contracts import ActiveStateSnapshot
from .storage import append_jsonl, make_id, read_json, read_jsonl, utc_now, write_jsonl


MODULE_ID = "kernel.disclosure.active_state_continuity"
TRANSITION_CONTRACT_VERSION = "1.0"
CARRY_FIELDS = (
    "topic",
    "purpose",
    "object_scope",
    "object_id",
    "tension",
    "posture",
    "lens",
    "branch_id",
    "scope_id",
)

PUBLIC_API = (
    "MODULE_ID",
    "TRANSITION_CONTRACT_VERSION",
    "CARRY_FIELDS",
    "load_active_state_config",
    "active_state_continuity_enabled",
    "build_continuity_key",
    "envelope_allows_durable_state",
    "merge_active_state_snapshots",
    "build_state_transition",
    "load_latest_snapshot_for_key",
    "load_latest_snapshot_for_workspace",
    "load_latest_transition_for_key",
    "apply_active_state_continuity",
    "rollback_active_state_transition",
    "list_active_state_transitions",
)
__all__ = list(PUBLIC_API)


def _runtime_config_path(root: Path) -> Path:
    return root / "product" / "inner_world_v1" / "config" / "runtime.json"


def active_state_transitions_path(root: Path) -> Path:
    path = (
        root
        / "product"
        / "inner_world_v1"
        / "data"
        / "reasoning_runtime"
        / "active_state_transitions.jsonl"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def load_active_state_config(root: Path) -> Dict[str, Any]:
    runtime = read_json(_runtime_config_path(root), default={}) or {}
    disclosure = runtime.get("disclosure", {}) or {}
    active_state = disclosure.get("active_state", {}) or {}
    return {
        "active_state_continuity_v1": bool(
            active_state.get(
                "continuity_v1",
                disclosure.get("active_state_continuity_v1", False),
            )
        ),
        "max_transitions": max(1, int(active_state.get("max_transitions", 200) or 200)),
    }


def active_state_continuity_enabled(root: Path) -> bool:
    return bool(load_active_state_config(root)["active_state_continuity_v1"])


def build_continuity_key(
    *,
    session_id: str = "",
    workspace_id: str = "",
    thought_id: str = "",
) -> str:
    parts: List[str] = []
    session = str(session_id or "").strip()
    workspace = str(workspace_id or "").strip()
    thought = str(thought_id or "").strip()
    if session:
        parts.append(f"session:{session}")
    if workspace:
        parts.append(f"workspace:{workspace}")
    if thought:
        parts.append(f"thought:{thought}")
    return "|".join(parts) if parts else "ephemeral"


def envelope_allows_durable_state(envelope_mode: str) -> bool:
    return str(envelope_mode or "bounded").strip().lower() != "incognito"


def merge_active_state_snapshots(
    prior: Mapping[str, Any] | None,
    current: Mapping[str, Any],
) -> Tuple[Dict[str, Any], List[str]]:
    merged = dict(current)
    if not prior:
        return merged, []

    changed: List[str] = []
    for field in CARRY_FIELDS:
        new_value = str(merged.get(field, "") or "").strip()
        prior_value = str(prior.get(field, "") or "").strip()
        if not new_value and prior_value:
            merged[field] = prior_value
            changed.append(f"carried:{field}")
        elif new_value and prior_value and new_value != prior_value:
            changed.append(f"updated:{field}")

    merged_refs = sorted(
        {
            str(value).strip()
            for value in list(prior.get("derived_from", []) or []) + list(current.get("derived_from", []) or [])
            if str(value).strip()
        }
    )
    merged["derived_from"] = merged_refs
    provenance = dict(merged.get("provenance", {}) or {})
    provenance["continuity_applied"] = True
    provenance["prior_snapshot_id"] = str(prior.get("snapshot_id", "") or "")
    provenance["reference_only"] = True
    merged["provenance"] = provenance
    ActiveStateSnapshot.from_dict(merged)
    return merged, changed


def build_state_transition(
    *,
    continuity_key: str,
    snapshot: Mapping[str, Any],
    envelope: str,
    surface: str,
    request_id: str,
    prior_snapshot_id: str = "",
    fields_changed: List[str] | None = None,
    durable: bool = True,
    operation: str = "transition",
    compensates_transition_id: str = "",
    rollback_reason: str = "",
) -> Dict[str, Any]:
    row = {
        "transition_id": make_id("state-transition"),
        "contract_version": TRANSITION_CONTRACT_VERSION,
        "operation": operation,
        "continuity_key": continuity_key,
        "surface": surface,
        "envelope": envelope,
        "prior_snapshot_id": prior_snapshot_id,
        "snapshot_id": str(snapshot.get("snapshot_id", "") or ""),
        "request_id": request_id,
        "fields_changed": list(fields_changed or []),
        "snapshot": dict(snapshot),
        "reference_only": True,
        "durable": durable,
        "recorded_at": utc_now(),
    }
    if operation == "rollback":
        row["compensates_transition_id"] = compensates_transition_id
        row["rollback_reason"] = rollback_reason
    return row


def _write_transition_rows(path: Path, rows: List[Dict[str, Any]]) -> None:
    write_jsonl(path, rows)


def apply_transition_retention(root: Path) -> Dict[str, Any]:
    config = load_active_state_config(root)
    path = active_state_transitions_path(root)
    rows = read_jsonl(path)
    max_entries = int(config["max_transitions"])
    removed = max(0, len(rows) - max_entries)
    if removed:
        _write_transition_rows(path, rows[-max_entries:])
    return {"removed": removed, "retained": min(len(rows), max_entries)}


def persist_state_transition(root: Path, transition: Mapping[str, Any]) -> Dict[str, Any]:
    if not transition.get("durable"):
        return dict(transition)
    append_jsonl(active_state_transitions_path(root), dict(transition))
    apply_transition_retention(root)
    return dict(transition)


def load_latest_snapshot_for_workspace(root: Path, workspace_id: str) -> Dict[str, Any] | None:
    needle = f"workspace:{str(workspace_id or '').strip()}"
    if not needle or needle == "workspace:":
        return None
    for row in reversed(read_jsonl(active_state_transitions_path(root))):
        if needle not in str(row.get("continuity_key", "")):
            continue
        if str(row.get("operation", "transition")) not in {"transition", "rollback"}:
            continue
        if not row.get("durable"):
            continue
        if row.get("superseded_by"):
            continue
        snapshot = dict(row.get("snapshot", {}) or {})
        if snapshot:
            return snapshot
    return None


def load_latest_transition_for_key(root: Path, continuity_key: str) -> Dict[str, Any] | None:
    for row in reversed(read_jsonl(active_state_transitions_path(root))):
        if str(row.get("continuity_key", "")) != continuity_key:
            continue
        if str(row.get("operation", "transition")) not in {"transition", "rollback"}:
            continue
        if not row.get("durable"):
            continue
        if row.get("superseded_by"):
            continue
        return dict(row)
    return None


def load_latest_snapshot_for_key(root: Path, continuity_key: str) -> Dict[str, Any] | None:
    transition = load_latest_transition_for_key(root, continuity_key)
    if not transition:
        return None
    snapshot = dict(transition.get("snapshot", {}) or {})
    return snapshot or None


def list_active_state_transitions(
    root: Path,
    *,
    continuity_key: str = "",
    limit: int = 20,
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for row in reversed(read_jsonl(active_state_transitions_path(root))):
        if continuity_key and str(row.get("continuity_key", "")) != continuity_key:
            continue
        rows.append(dict(row))
        if len(rows) >= max(1, int(limit)):
            break
    return rows


def apply_active_state_continuity(
    root: Path,
    snapshot: Mapping[str, Any],
    *,
    effective_grant: Mapping[str, Any],
    session_envelope: Mapping[str, Any],
    surface: str,
    context_state: Mapping[str, Any] | None = None,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    state = dict(context_state or {})
    attributes = dict(state.get("attributes", {}) or {})
    caller_hints = dict(attributes.get("caller_hints", {}) or {})
    envelope = str(
        effective_grant.get("envelope", "")
        or session_envelope.get("mode", "")
        or "bounded"
    )
    continuity_key = build_continuity_key(
        session_id=str(attributes.get("session_id", "") or state.get("session_id", "") or ""),
        workspace_id=str(state.get("active_workspace_id", "") or caller_hints.get("workspace_id", "") or ""),
        thought_id=str(caller_hints.get("thought_id", "") or snapshot.get("object_id", "") or ""),
    )

    if not envelope_allows_durable_state(envelope):
        transition = build_state_transition(
            continuity_key=continuity_key,
            snapshot=dict(snapshot),
            envelope=envelope,
            surface=surface,
            request_id=str(snapshot.get("request_id", "") or ""),
            durable=False,
            fields_changed=["ephemeral"],
        )
        transition["operation"] = "ephemeral"
        return dict(snapshot), transition

    prior = load_latest_snapshot_for_key(root, continuity_key)
    merged, fields_changed = merge_active_state_snapshots(prior, snapshot)
    transition = build_state_transition(
        continuity_key=continuity_key,
        snapshot=merged,
        envelope=envelope,
        surface=surface,
        request_id=str(snapshot.get("request_id", "") or ""),
        prior_snapshot_id=str((prior or {}).get("snapshot_id", "") or ""),
        fields_changed=fields_changed,
        durable=True,
    )
    if active_state_continuity_enabled(root):
        persist_state_transition(root, transition)
    return merged, transition


def rollback_active_state_transition(
    root: Path,
    *,
    continuity_key: str,
    compensates_transition_id: str,
    reason: str,
    surface: str = "bridge",
) -> Dict[str, Any]:
    target: Dict[str, Any] | None = None
    rows = read_jsonl(active_state_transitions_path(root))
    for row in rows:
        if str(row.get("transition_id", "")) == compensates_transition_id:
            target = dict(row)
            break
    if target is None:
        return {"status": "not_found", "compensates_transition_id": compensates_transition_id}

    restored_snapshot = dict(target.get("snapshot", {}) or {})
    rollback_row = build_state_transition(
        continuity_key=continuity_key,
        snapshot=restored_snapshot,
        envelope=str(target.get("envelope", "bounded") or "bounded"),
        surface=surface,
        request_id=str(restored_snapshot.get("request_id", "") or ""),
        prior_snapshot_id=str(target.get("snapshot_id", "") or ""),
        fields_changed=["rollback"],
        durable=True,
        operation="rollback",
        compensates_transition_id=compensates_transition_id,
        rollback_reason=reason,
    )
    rollback_row["rollback_id"] = make_id("state-rollback")

    updated_rows: List[Dict[str, Any]] = []
    for row in rows:
        current = dict(row)
        if str(current.get("transition_id", "")) == compensates_transition_id:
            current["superseded_by"] = rollback_row["rollback_id"]
        updated_rows.append(current)
    updated_rows.append(rollback_row)
    _write_transition_rows(active_state_transitions_path(root), updated_rows)
    apply_transition_retention(root)
    return {
        "status": "rolled_back",
        "rollback_id": rollback_row["rollback_id"],
        "compensates_transition_id": compensates_transition_id,
        "restored_snapshot_id": restored_snapshot.get("snapshot_id", ""),
        "transition": rollback_row,
    }
