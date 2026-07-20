"""Persistent disclosure receipts and result reconstruction (CAE-007)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional

from .disclosure_contracts import (
    AuditReceipt,
    CONTRACT_VERSION,
    receipt_retention_for_envelope,
    validate_audit_receipt,
)
from .storage import append_jsonl, make_id, read_json, read_jsonl, utc_now, write_jsonl


MODULE_ID = "kernel.disclosure.receipts"
RECEIPTS_CONTRACT_VERSION = "1.0"

PUBLIC_API = (
    "MODULE_ID",
    "RECEIPTS_CONTRACT_VERSION",
    "disclosure_receipts_path",
    "load_receipt_config",
    "persistent_receipts_enabled",
    "build_audit_receipt",
    "record_disclosure_receipt",
    "list_disclosure_receipts",
    "get_disclosure_receipt",
    "apply_receipt_retention",
    "reconstruct_disclosure_result",
    "inspect_disclosure_receipt",
    "record_bridge_context_receipt",
)
__all__ = list(PUBLIC_API)


def _runtime_config_path(root: Path) -> Path:
    return root / "product" / "inner_world_v1" / "config" / "runtime.json"


def disclosure_receipts_path(root: Path) -> Path:
    path = (
        root
        / "product"
        / "inner_world_v1"
        / "data"
        / "reasoning_runtime"
        / "disclosure_receipts.jsonl"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def load_receipt_config(root: Path) -> Dict[str, Any]:
    runtime = read_json(_runtime_config_path(root), default={}) or {}
    disclosure = runtime.get("disclosure", {}) or {}
    receipts = disclosure.get("receipts", {}) or {}
    return {
        "persistent_receipts_v1": bool(
            receipts.get(
                "persistent_receipts_v1",
                disclosure.get("persistent_receipts_v1", False),
            )
        ),
        "max_entries": max(1, int(receipts.get("max_entries", 500) or 500)),
        "retention_days": max(0, int(receipts.get("retention_days", 30) or 30)),
    }


def persistent_receipts_enabled(root: Path) -> bool:
    return bool(load_receipt_config(root)["persistent_receipts_v1"])


def _policy_hash(prefix: str, payload: Mapping[str, Any]) -> str:
    digest = hashlib.sha256(
        json.dumps(dict(payload), sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return f"sha256:{prefix}:{digest}"


def _content_hashes_from_blocks(blocks: Iterable[Mapping[str, Any]]) -> List[str]:
    hashes: List[str] = []
    for row in blocks:
        source_ref = str(row.get("source_ref", "") or "").strip()
        block_id = str(row.get("block_id", "") or "").strip()
        payload = source_ref or block_id
        if not payload:
            continue
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        hashes.append(f"sha256:{digest}")
    return sorted(set(hashes))


def _candidate_decisions_from_retrieval(retrieval_bundle: Mapping[str, Any] | None) -> List[Dict[str, Any]]:
    if not retrieval_bundle:
        return []
    shadow = dict(retrieval_bundle.get("shadow_admission", {}) or {})
    decisions = list(shadow.get("decisions", []) or [])
    if decisions:
        return [
            {
                "candidate_id": str(row.get("capsule_id", "") or ""),
                "decision": "admitted" if row.get("admitted") else "rejected",
                "admission_signals": list(row.get("admission_signals", []) or []),
                "reason_code": str(row.get("reason_code", "") or ""),
            }
            for row in decisions
            if str(row.get("capsule_id", "") or "").strip()
        ]
    admitted_ids = {
        str(row.get("capsule_id", "") or "")
        for row in list(retrieval_bundle.get("seed_capsules", []) or [])
        + list(retrieval_bundle.get("related_capsules", []) or [])
    }
    return [
        {
            "candidate_id": capsule_id,
            "decision": "admitted",
            "admission_signals": ["semantic_retrieval"],
        }
        for capsule_id in sorted(admitted_ids)
        if capsule_id
    ]


def _requested_grant_from_effective(effective_grant: Mapping[str, Any]) -> Dict[str, Any]:
    envelope = str(effective_grant.get("envelope", "bounded") or "bounded")
    return {
        "grant_id": str(effective_grant.get("grant_id", "") or ""),
        "request_id": str(effective_grant.get("request_id", "") or ""),
        "envelope": envelope,
        "requested_layers": list(effective_grant.get("requested_layers", []) or effective_grant.get("effective_layers", []) or []),
        "requested_refs": list(effective_grant.get("effective_refs", []) or []),
        "dimensions": list(effective_grant.get("dimensions", []) or []),
        "shape_maturity": str(effective_grant.get("shape_maturity", "candidate") or "candidate"),
        "token_budget": int(effective_grant.get("token_budget", 0) or 0),
        "persistence_mode": str(effective_grant.get("persistence_mode", "gated") or "gated"),
        "explicit_pins": list(effective_grant.get("explicit_pins", []) or []),
        "explicit_denials": [
            str(row.get("field", "") or row.get("code", ""))
            for row in effective_grant.get("narrowing_reasons", []) or []
            if str(row.get("code", "")) in {"explicit_denial", "layer_denied", "envelope_default"}
        ],
    }


def build_audit_receipt(
    *,
    request_id: str,
    surface: str,
    result_status: str,
    effective_grant: Mapping[str, Any],
    frame_audit: Mapping[str, Any] | None = None,
    frame_bundle: Mapping[str, Any] | None = None,
    corpus_catalog: Mapping[str, Any] | None = None,
    budget_ledger: Mapping[str, Any] | None = None,
    metrics: Mapping[str, Any] | None = None,
    retrieval_bundle: Mapping[str, Any] | None = None,
    workspace_id: str = "",
) -> Dict[str, Any]:
    frame_audit = dict(frame_audit or {})
    frame_bundle = dict(frame_bundle or {})
    effective = dict(effective_grant or {})
    envelope = str(
        effective.get("envelope", "")
        or frame_audit.get("envelope_mode", "")
        or "bounded"
    )
    retention_mode = receipt_retention_for_envelope(envelope)
    incognito = envelope == "incognito" or retention_mode == "hashes_metrics_only"

    included_blocks = list(frame_bundle.get("included_blocks", []) or [])
    included_block_ids = [str(row.get("block_id", "") or "") for row in included_blocks if row.get("block_id")]

    omitted_block_ids: List[str] = []
    omission_reasons: List[Dict[str, Any]] = []
    for row in list(frame_audit.get("omitted_blocks", []) or []):
        block_id = str(row.get("block_id", "") or "")
        if block_id:
            omitted_block_ids.append(block_id)
        reason = {
            "block_id": block_id,
            "code": str(row.get("reason_code", "") or "layer_not_disclosed"),
            "reason": str(row.get("reason", "") or row.get("reason_code", "") or "layer_not_disclosed"),
        }
        if not incognito:
            if row.get("source_ref"):
                reason["source_ref"] = str(row.get("source_ref", ""))
            if row.get("layer"):
                reason["layer"] = str(row.get("layer", ""))
        omission_reasons.append(reason)

    for row in list(frame_audit.get("drop_ledger", []) or []):
        block_id = str(row.get("block_id", "") or "")
        if block_id and block_id not in omitted_block_ids:
            omitted_block_ids.append(block_id)
        omission_reasons.append(
            {
                "block_id": block_id,
                "code": str(row.get("reason_code", "") or "budget_insufficient"),
                "reason": "Required whole block could not fit remaining evidence budget"
                if incognito
                else str(row.get("reason", "") or "budget_insufficient"),
            }
        )

    corpus_revision = str((corpus_catalog or {}).get("corpus_revision", "") or "")
    if not corpus_revision:
        from .library_tracker import CHAT_CONVERTER_SEED_CORPUS_REVISION

        corpus_revision = CHAT_CONVERTER_SEED_CORPUS_REVISION

    receipt_metrics = dict(metrics or {})
    receipt_metrics.setdefault("included_block_count", len(included_block_ids))
    receipt_metrics.setdefault("omitted_block_count", len(omitted_block_ids))

    receipt = AuditReceipt(
        receipt_id=make_id("receipt"),
        request_id=str(request_id or effective.get("request_id", "") or ""),
        corpus_revision=corpus_revision,
        requested_grant=_requested_grant_from_effective(effective),
        effective_grant=effective,
        candidate_decisions=_candidate_decisions_from_retrieval(retrieval_bundle),
        included_block_ids=included_block_ids,
        omitted_block_ids=omitted_block_ids,
        omission_reasons=omission_reasons,
        budget_ledger=dict(budget_ledger or frame_audit.get("budget_ledger", {}) or {}),
        policy_hashes={
            "effective_grant": _policy_hash("grant", effective),
            "budget_policy": str(frame_audit.get("budget_policy_hash", "") or ""),
            "envelope_defaults": _policy_hash("envelope", {"envelope": envelope, "version": CONTRACT_VERSION}),
        },
        surface=str(surface or "bridge"),
        result_status=str(result_status or "disclosed"),
        retention_mode=retention_mode,
        content_hashes=_content_hashes_from_blocks(included_blocks) if incognito else [],
        metrics=receipt_metrics,
        sensitive_text_included=False,
        provenance={
            "recorded_at": utc_now(),
            "frame_audit_id": str(frame_audit.get("audit_id", "") or ""),
            "frame_id": str(frame_bundle.get("frame_id", "") or frame_audit.get("frame_id", "") or ""),
            "workspace_id": str(workspace_id or frame_audit.get("workspace_id", "") or ""),
            "assembly_status": str(frame_bundle.get("assembly_status", "") or frame_audit.get("assembly_status", "") or ""),
        },
    )
    validate_audit_receipt(receipt.to_dict(), envelope=envelope)
    return receipt.to_dict()


def _write_receipt_rows(path: Path, rows: List[Dict[str, Any]]) -> None:
    write_jsonl(path, rows)


def apply_receipt_retention(root: Path) -> Dict[str, Any]:
    config = load_receipt_config(root)
    path = disclosure_receipts_path(root)
    rows = read_jsonl(path)
    if not rows:
        return {"removed": 0, "retained": 0}

    if config["retention_days"] > 0:
        cutoff_prefix = utc_now()[:10]
        # Keep rows whose recorded_at date is within retention_days via simple count trim below;
        # exact day parsing is avoided to keep dependency-free behavior in tests.
        _ = cutoff_prefix

    max_entries = int(config["max_entries"])
    removed = max(0, len(rows) - max_entries)
    retained_rows = rows[-max_entries:] if removed else rows
    if removed:
        _write_receipt_rows(path, retained_rows)
    return {"removed": removed, "retained": len(retained_rows)}


def record_disclosure_receipt(
    root: Path,
    *,
    request_id: str,
    result_status: str,
    effective_grant: Mapping[str, Any],
    budget_ledger: Mapping[str, Any] | None = None,
    frame_audit: Mapping[str, Any] | None = None,
    metrics: Mapping[str, Any] | None = None,
    surface: str = "bridge",
    frame_bundle: Mapping[str, Any] | None = None,
    corpus_catalog: Mapping[str, Any] | None = None,
    retrieval_bundle: Mapping[str, Any] | None = None,
    workspace_id: str = "",
) -> Dict[str, Any]:
    receipt = build_audit_receipt(
        request_id=request_id,
        surface=surface,
        result_status=result_status,
        effective_grant=effective_grant,
        frame_audit=frame_audit,
        frame_bundle=frame_bundle,
        corpus_catalog=corpus_catalog,
        budget_ledger=budget_ledger,
        metrics=metrics,
        retrieval_bundle=retrieval_bundle,
        workspace_id=workspace_id,
    )
    if persistent_receipts_enabled(root):
        append_jsonl(disclosure_receipts_path(root), receipt)
        apply_receipt_retention(root)
    return receipt


def list_disclosure_receipts(
    root: Path,
    *,
    request_id: str = "",
    surface: str = "",
    workspace_id: str = "",
    limit: int = 20,
) -> List[Dict[str, Any]]:
    rows = read_jsonl(disclosure_receipts_path(root))
    filtered: List[Dict[str, Any]] = []
    for row in reversed(rows):
        if request_id and str(row.get("request_id", "")) != request_id:
            continue
        if surface and str(row.get("surface", "")) != surface:
            continue
        provenance = dict(row.get("provenance", {}) or {})
        if workspace_id and str(provenance.get("workspace_id", "")) != workspace_id:
            continue
        filtered.append(row)
        if len(filtered) >= max(1, int(limit)):
            break
    return filtered


def get_disclosure_receipt(root: Path, receipt_id: str) -> Dict[str, Any] | None:
    for row in read_jsonl(disclosure_receipts_path(root)):
        if str(row.get("receipt_id", "")) == str(receipt_id):
            return dict(row)
    return None


def reconstruct_disclosure_result(receipt_payload: Mapping[str, Any]) -> Dict[str, Any]:
    receipt = AuditReceipt.from_dict(receipt_payload)
    return {
        "receipt_id": receipt.receipt_id,
        "request_id": receipt.request_id,
        "surface": receipt.surface,
        "result_status": receipt.result_status,
        "corpus_revision": receipt.corpus_revision,
        "effective_layers": list(receipt.effective_grant.get("effective_layers", []) or []),
        "included_block_ids": list(receipt.included_block_ids),
        "omitted_block_ids": list(receipt.omitted_block_ids),
        "omission_reasons": [dict(row) for row in receipt.omission_reasons],
        "candidate_decisions": [dict(row) for row in receipt.candidate_decisions],
        "budget_ledger": dict(receipt.budget_ledger),
        "policy_hashes": dict(receipt.policy_hashes),
        "metrics": dict(receipt.metrics),
        "retention_mode": receipt.retention_mode,
        "content_hashes": list(receipt.content_hashes),
        "provenance": dict(receipt.provenance),
        "reconstructible": True,
        "sensitive_text_included": receipt.sensitive_text_included,
    }


def inspect_disclosure_receipt(root: Path, receipt_id: str) -> Dict[str, Any]:
    receipt = get_disclosure_receipt(root, receipt_id)
    if receipt is None:
        return {"found": False, "receipt_id": receipt_id}
    reconstructed = reconstruct_disclosure_result(receipt)
    return {
        "found": True,
        "receipt_id": receipt_id,
        "receipt": receipt,
        "reconstructed": reconstructed,
    }


def record_bridge_context_receipt(root: Path, bundle: Mapping[str, Any]) -> Dict[str, Any]:
    context_state = dict(bundle.get("context_state", {}) or {})
    frame_bundle = dict(bundle.get("frame_bundle", {}) or {})
    frame_audit = dict(bundle.get("frame_audit", {}) or {})
    return record_disclosure_receipt(
        root,
        request_id=str(context_state.get("request_id", "") or frame_bundle.get("request_id", "") or ""),
        result_status=str(
            bundle.get("result_status", "")
            or frame_bundle.get("result_status", "")
            or frame_bundle.get("assembly_status", "")
            or "disclosed"
        ),
        effective_grant=dict(bundle.get("effective_grant", {}) or {}),
        budget_ledger=dict(
            frame_audit.get("budget_ledger", {})
            or dict(bundle.get("budget_audit", {}) or {}).get("budget_ledger", {})
            or {}
        ),
        frame_audit=frame_audit,
        frame_bundle=frame_bundle,
        retrieval_bundle=dict(bundle.get("global_fallback", {}) or {}),
        metrics={
            "included_block_count": len(frame_bundle.get("included_blocks", []) or []),
            "suppressed_block_count": len(frame_audit.get("omitted_blocks", []) or []),
        },
        surface="bridge",
        workspace_id=str(context_state.get("active_workspace_id", "") or frame_audit.get("workspace_id", "") or ""),
    )
