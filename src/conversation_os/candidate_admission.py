"""Positive-admission gate for retrieval candidates (CAE-001)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Sequence, Set

from .storage import read_json


MODULE_ID = "kernel.disclosure.candidate_admission"
CONTRACT_VERSION = "1.0"
ADMISSION_SIGNALS = (
    "lexical_label",
    "lexical_summary",
    "lexical_attrs",
    "alias",
    "explicit_pin",
    "governed_graph",
    "structural_shape_legacy",
    "semantic_address",
)
REJECTION_REASONS = (
    "confidence_only",
    "no_positive_signal",
    "missing_membrane_metadata",
)
PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "ADMISSION_SIGNALS",
    "REJECTION_REASONS",
    "load_knowledge_admission_config",
    "fail_empty_admission_shadow_enabled",
    "fail_empty_admission_enforce_enabled",
    "evaluate_capsule_admission",
    "compute_ranking_score",
    "apply_fail_empty_gate",
    "build_shadow_admission_report",
)
__all__ = list(PUBLIC_API)

DEFAULT_KNOWLEDGE_ADMISSION_CONFIG = {
    "fail_empty_admission_shadow_v1": True,
    "fail_empty_admission_enforce_v1": True,
}


def _runtime_config_path(root: Path) -> Path:
    return root / "product" / "inner_world_v1" / "config" / "runtime.json"


def load_knowledge_admission_config(root: Path) -> Dict[str, bool]:
    runtime = read_json(_runtime_config_path(root), default={}) or {}
    knowledge = runtime.get("knowledge", {}) or {}
    return {
        "fail_empty_admission_shadow_v1": bool(
            knowledge.get(
                "fail_empty_admission_shadow_v1",
                DEFAULT_KNOWLEDGE_ADMISSION_CONFIG["fail_empty_admission_shadow_v1"],
            )
        ),
        "fail_empty_admission_enforce_v1": bool(
            knowledge.get(
                "fail_empty_admission_enforce_v1",
                DEFAULT_KNOWLEDGE_ADMISSION_CONFIG["fail_empty_admission_enforce_v1"],
            )
        ),
    }


def fail_empty_admission_shadow_enabled(root: Path) -> bool:
    return load_knowledge_admission_config(root)["fail_empty_admission_shadow_v1"]


def fail_empty_admission_enforce_enabled(root: Path) -> bool:
    return load_knowledge_admission_config(root)["fail_empty_admission_enforce_v1"]


def _normalized_envelope_mode(envelope_mode: str) -> str:
    return str(envelope_mode or "open").strip().lower()


def _explicit_pin_keys(explicit_pins: Sequence[str] | None) -> Set[str]:
    keys: Set[str] = set()
    for value in explicit_pins or ():
        text = str(value or "").strip()
        if not text:
            continue
        if ":" in text:
            keys.add(text)
            continue
        keys.add(f"capsule:{text}")
    return keys


def evaluate_capsule_admission(
    capsule: Mapping[str, Any],
    *,
    query_tokens: Set[str],
    index_tokens: Mapping[str, Set[str]],
    alias_matched: bool = False,
    explicit_pins: Sequence[str] | None = None,
    governed_graph: bool = False,
    envelope_mode: str = "open",
    pond_profile: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    admission_signals: List[str] = []
    ranking_features: Dict[str, float] = {}
    ref_key = f"{capsule.get('ref_type', '')}:{capsule.get('ref_id', '')}"
    capsule_key = f"capsule:{capsule.get('capsule_id', '')}"

    if alias_matched:
        admission_signals.append("alias")
    if governed_graph:
        admission_signals.append("governed_graph")
    if ref_key in _explicit_pin_keys(explicit_pins) or capsule_key in _explicit_pin_keys(explicit_pins):
        admission_signals.append("explicit_pin")

    label_overlap = query_tokens & set(index_tokens.get("label", set()))
    summary_overlap = query_tokens & set(index_tokens.get("summary", set()))
    attrs_overlap = query_tokens & set(index_tokens.get("attrs", set()))
    if label_overlap:
        admission_signals.append("lexical_label")
        ranking_features["lexical_label"] = float(len(label_overlap) * 4.0)
    if summary_overlap:
        admission_signals.append("lexical_summary")
        ranking_features["lexical_summary"] = float(len(summary_overlap) * 2.0)
    if attrs_overlap:
        admission_signals.append("lexical_attrs")
        ranking_features["lexical_attrs"] = float(len(attrs_overlap) * 1.2)

    attributes = capsule.get("attributes", {}) or {}
    if str(attributes.get("semantic_address", "") or "").strip() and query_tokens:
        address_tokens = set(str(attributes.get("semantic_address", "")).lower().split())
        if address_tokens & query_tokens:
            admission_signals.append("semantic_address")
            ranking_features["semantic_address"] = float(len(address_tokens & query_tokens) * 3.0)
    if str(attributes.get("shape_signature_id", "") or "").strip() or str(attributes.get("legacy_shape_id", "") or "").strip():
        if admission_signals:
            admission_signals.append("structural_shape_legacy")
            ranking_features["structural_shape_legacy"] = 1.0

    ranking_features["confidence"] = round(float(capsule.get("confidence", 0.0) or 0.0), 3)

    rejection_reason = ""
    mode = _normalized_envelope_mode(envelope_mode)
    profile = pond_profile or {}
    if mode in {"bounded", "strict"} and capsule.get("source_refs"):
        if not str(profile.get("primary_pond", "") or "").strip():
            rejection_reason = "missing_membrane_metadata"
            admission_signals = []

    admitted = bool(admission_signals) and not rejection_reason
    if not admitted and not rejection_reason:
        if query_tokens and float(ranking_features.get("confidence", 0.0) or 0.0) > 0:
            rejection_reason = "confidence_only"
        else:
            rejection_reason = "no_positive_signal"

    return {
        "capsule_id": str(capsule.get("capsule_id", "") or ""),
        "ref_key": ref_key,
        "admitted": admitted,
        "admission_signals": admission_signals,
        "ranking_features": ranking_features,
        "rejection_reason": rejection_reason,
    }


def compute_ranking_score(
    capsule: Mapping[str, Any],
    *,
    ranking_features: Mapping[str, float],
    type_weight: Mapping[str, float] | None = None,
) -> float:
    weights = type_weight or {}
    score = 0.0
    for key, value in ranking_features.items():
        if key == "confidence":
            continue
        score += float(value or 0.0)
    score += float(ranking_features.get("confidence", 0.0) or 0.0) * float(
        weights.get(str(capsule.get("capsule_type", "")), 0.7)
    )
    return round(score, 3)


def build_shadow_admission_report(
    decisions: Sequence[Mapping[str, Any]],
    *,
    query: str,
    enforce: bool,
) -> Dict[str, Any]:
    admitted = [row for row in decisions if row.get("admitted")]
    rejected = [row for row in decisions if not row.get("admitted")]
    return {
        "query": query,
        "enforce": enforce,
        "admitted_count": len(admitted),
        "rejected_count": len(rejected),
        "decisions": [dict(row) for row in decisions],
    }


def apply_fail_empty_gate(
    bundle: MutableMapping[str, Any],
    *,
    admission_decisions: Sequence[Mapping[str, Any]],
    enforce: bool,
    shadow: bool,
    envelope_mode: str = "open",
) -> Dict[str, Any]:
    admitted_ids = {str(row.get("capsule_id", "")) for row in admission_decisions if row.get("admitted")}
    seeds = [row for row in bundle.get("seed_capsules", []) if row.get("capsule_id") in admitted_ids]
    related = [
        row
        for row in bundle.get("related_capsules", [])
        if row.get("capsule_id") in admitted_ids and row.get("capsule_id") not in {seed.get("capsule_id") for seed in seeds}
    ]
    result = dict(bundle)
    result["seed_capsules"] = seeds
    result["related_capsules"] = related
    result["count"] = len(seeds) + len(related)
    result["envelope_mode"] = _normalized_envelope_mode(envelope_mode)

    if shadow:
        result["shadow_admission"] = build_shadow_admission_report(
            admission_decisions,
            query=str(bundle.get("query", "") or ""),
            enforce=enforce,
        )

    if enforce and not seeds and not related:
        result["seed_capsules"] = []
        result["related_capsules"] = []
        result["included_links"] = []
        result["source_refs"] = []
        result["count"] = 0
        result["result_status"] = "empty_no_positive_match"
    elif seeds or related:
        result["result_status"] = "disclosed"
    return result
