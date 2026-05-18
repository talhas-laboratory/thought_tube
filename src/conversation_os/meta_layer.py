from __future__ import annotations

import hashlib
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List

from .analysis_units import build_analysis_units, load_analysis_units
from .conversation_deltas import build_conversation_deltas, load_conversation_deltas, load_user_expectations
from .meta_objects import META_LAYER_FILES, META_LAYER_KINDS
from .models import MetaLayerRecord
from .pipeline_runner import run_pipeline
from .plugins import load_plugins
from .storage import ensure_dir, read_jsonl, write_jsonl
from .vault_ingest import tokenize


def meta_layer_dir(root: Path) -> Path:
    return root / "product" / "inner_world_v1" / "data" / "meta_layer"


def _meta_path(root: Path, kind: str) -> Path:
    return meta_layer_dir(root) / META_LAYER_FILES[kind]


def load_meta_records(root: Path, kinds: List[str] | None = None) -> List[Dict]:
    selected = kinds or META_LAYER_KINDS
    rows: List[Dict] = []
    for kind in selected:
        rows.extend(read_jsonl(_meta_path(root, kind)))
    return rows


def _make_id(kind: str, anchor_id: str, label: str) -> str:
    digest = hashlib.sha256(f"{kind}:{anchor_id}:{label}".encode("utf-8")).hexdigest()[:12]
    return f"{kind}-{digest}"


def _record(
    *,
    kind: str,
    unit: Dict,
    label: str,
    summary: str,
    status: str = "provisional",
    confidence: float = 0.6,
    evidence: List[str] | None = None,
    attributes: Dict | None = None,
) -> Dict:
    return MetaLayerRecord(
        meta_id=_make_id(kind, unit["unit_id"], label),
        kind=kind,
        label=label,
        summary=summary,
        status=status,
        confidence=round(confidence, 2),
        source_refs=[unit["source_ref"]],
        chunk_ids=unit["chunk_ids"],
        evidence=evidence or [unit["content"][:220]],
        attributes=attributes or {},
    ).to_dict()


def _unit_delta_context(unit: Dict, delta_rows: List[Dict]) -> Dict:
    chunk_ids = set(unit.get("chunk_ids", []))
    matched = [
        row
        for row in delta_rows
        if row["initial_user_chunk_id"] in chunk_ids
        or row["repeated_user_chunk_id"] in chunk_ids
        or row.get("resolved_assistant_chunk_id") in chunk_ids
        or chunk_ids & set(row.get("unsatisfying_assistant_chunk_ids", []))
    ]
    if not matched:
        return {
            "user_redline": False,
            "delta_resolved": False,
            "delta_intent_keys": [],
            "priority_tokens": [],
            "follow_up_kind": "",
            "follow_up_focus": "",
            "follow_up_kinds": [],
            "follow_up_focuses": [],
            "assistant_relevance_score": 0.5,
            "assistant_relevance_label": "partial",
        }
    user_redline = any(
        row["initial_user_chunk_id"] in chunk_ids or row["repeated_user_chunk_id"] in chunk_ids
        for row in matched
    )
    delta_resolved = any(row.get("resolved_assistant_chunk_id") in chunk_ids for row in matched)
    feedback_entries = []
    for row in matched:
        if row["repeated_user_chunk_id"] in chunk_ids:
            feedback_entries.append(
                {
                    "kind": row.get("unsatisfying_follow_up_kind", ""),
                    "focus": row.get("unsatisfying_follow_up_focus", ""),
                    "score": row.get("unsatisfying_relevance_score", 0.5),
                    "label": row.get("unsatisfying_relevance_label", "partial"),
                }
            )
        if row.get("resolved_assistant_chunk_id") in chunk_ids:
            feedback_entries.append(
                {
                    "kind": row.get("resolved_follow_up_kind", ""),
                    "focus": row.get("resolved_follow_up_focus", ""),
                    "score": row.get("resolved_relevance_score", 0.5),
                    "label": row.get("resolved_relevance_label", "partial"),
                }
            )
        if chunk_ids & set(row.get("unsatisfying_assistant_chunk_ids", [])):
            feedback_entries.append(
                {
                    "kind": row.get("unsatisfying_follow_up_kind", ""),
                    "focus": row.get("unsatisfying_follow_up_focus", ""),
                    "score": row.get("unsatisfying_relevance_score", 0.5),
                    "label": row.get("unsatisfying_relevance_label", "partial"),
                }
            )
    follow_up_kinds = [entry["kind"] for entry in feedback_entries if entry["kind"]]
    follow_up_focuses = [entry["focus"] for entry in feedback_entries if entry["focus"]]
    relevance_score = round(
        sum(entry["score"] for entry in feedback_entries) / max(1, len(feedback_entries)),
        2,
    )
    if relevance_score >= 0.72:
        relevance_label = "high"
    elif relevance_score >= 0.45:
        relevance_label = "partial"
    else:
        relevance_label = "low"
    return {
        "user_redline": user_redline,
        "delta_resolved": delta_resolved,
        "delta_intent_keys": sorted({row["intent_key"] for row in matched}),
        "priority_tokens": sorted({token for row in matched for token in row.get("user_priority_tokens", [])})[:12],
        "follow_up_kind": Counter(follow_up_kinds).most_common(1)[0][0] if follow_up_kinds else "",
        "follow_up_focus": Counter(follow_up_focuses).most_common(1)[0][0] if follow_up_focuses else "",
        "follow_up_kinds": sorted(set(follow_up_kinds)),
        "follow_up_focuses": sorted(set(follow_up_focuses)),
        "assistant_relevance_score": relevance_score,
        "assistant_relevance_label": relevance_label,
    }


def _unit_role_context(unit: Dict, delta_rows: List[Dict]) -> Dict:
    speaker_role = unit.get("speaker_role") or unit.get("metadata", {}).get("speaker_role", "")
    delta_context = _unit_delta_context(unit, delta_rows)
    ontology_weight = float(unit.get("speaker_weight") or 0.8)
    semantic_role = "primary_source"
    knowledge_eligible = True
    theme_eligible = True
    approval_state = "implicit"
    if speaker_role == "user":
        semantic_role = "semantic_line"
        theme_eligible = True
        approval_state = "user_asserted"
        ontology_weight += 0.16
    elif speaker_role == "assistant":
        if delta_context["delta_resolved"]:
            semantic_role = "approved_context"
            approval_state = "approved"
            ontology_weight -= 0.02
        else:
            semantic_role = "assistant_attempt"
            approval_state = "unapproved"
            knowledge_eligible = False
            ontology_weight -= 0.28
    else:
        ontology_weight += 0.02
    if delta_context["user_redline"]:
        ontology_weight += 0.12
    if delta_context["delta_resolved"]:
        ontology_weight += 0.08
    if speaker_role == "user" and delta_context["follow_up_kind"] in {"correction", "instruction_shift"}:
        ontology_weight += 0.06
    if semantic_role == "approved_context":
        if delta_context["assistant_relevance_score"] >= 0.72:
            ontology_weight += 0.08
            approval_state = "approved_and_used"
        elif delta_context["assistant_relevance_score"] <= 0.35:
            ontology_weight -= 0.08
    return {
        "speaker_role": speaker_role,
        "ontology_weight": round(max(0.35, min(1.12, ontology_weight)), 2),
        "semantic_role": semantic_role,
        "knowledge_eligible": knowledge_eligible,
        "theme_eligible": theme_eligible,
        "approval_state": approval_state,
        "user_redline": delta_context["user_redline"],
        "delta_resolved": delta_context["delta_resolved"],
        "delta_intent_keys": delta_context["delta_intent_keys"],
        "priority_tokens": delta_context["priority_tokens"],
        "follow_up_kind": delta_context["follow_up_kind"],
        "follow_up_focus": delta_context["follow_up_focus"],
        "follow_up_kinds": delta_context["follow_up_kinds"],
        "follow_up_focuses": delta_context["follow_up_focuses"],
        "assistant_relevance_score": delta_context["assistant_relevance_score"],
        "assistant_relevance_label": delta_context["assistant_relevance_label"],
    }


def _weighted_confidence(base: float, role_context: Dict) -> float:
    adjusted = base
    if role_context["semantic_role"] == "semantic_line":
        adjusted += 0.08
    elif role_context["semantic_role"] == "approved_context":
        adjusted -= 0.02
    elif role_context["speaker_role"] == "assistant":
        adjusted -= 0.16
    if role_context["user_redline"]:
        adjusted += 0.08
    if role_context["delta_resolved"]:
        adjusted += 0.05
    if role_context["semantic_role"] == "semantic_line" and role_context.get("follow_up_kind") in {"correction", "instruction_shift"}:
        adjusted += 0.05
    if role_context["semantic_role"] == "approved_context":
        score = role_context.get("assistant_relevance_score", 0.5)
        if score >= 0.8:
            adjusted += 0.08
        elif score >= 0.65:
            adjusted += 0.05
        elif score <= 0.35:
            adjusted -= 0.08
    return round(max(0.32, min(0.96, adjusted)), 2)


def _theme_records(unit: Dict, packet: Dict, role_context: Dict) -> List[Dict]:
    if not role_context["theme_eligible"]:
        return []
    tokens = packet["subconscious_processing"]["active_signal_frame"].get("domain_tokens", [])[:3]
    if not tokens:
        return []
    label = " ".join(token.replace("-", " ") for token in tokens[:2]).title()
    return [
        _record(
            kind="theme",
            unit=unit,
            label=label,
            summary=f"A recurring thematic cluster around {label.lower()}.",
            confidence=_weighted_confidence(0.62, role_context),
            attributes={"tokens": tokens, "source_ref": unit["source_ref"], **role_context},
        )
    ]


def _discussion_records(unit: Dict, packet: Dict, role_context: Dict) -> List[Dict]:
    dimensions = packet["subconscious_processing"].get("active_dimensions", [])
    if "question" not in dimensions and "review" not in dimensions:
        return []
    label = packet["subconscious_processing"]["active_signal_frame"]["core_statement"][:72]
    return [
        _record(
            kind="discussion",
            unit=unit,
            label=label,
            summary="A discussion-shaped thread inside the vault material.",
            confidence=_weighted_confidence(0.64, role_context),
            attributes={
                "tokens": packet["subconscious_processing"]["active_signal_frame"].get("domain_tokens", []),
                "source_ref": unit["source_ref"],
                **role_context,
            },
        )
    ]


def _direction_records(unit: Dict, packet: Dict, role_context: Dict) -> List[Dict]:
    if role_context["semantic_role"] == "approved_context":
        return []
    text = unit["content"].lower()
    if not any(marker in text for marker in ["should", "must", "need to", "prefer", "choose", "let's", "lets "]):
        return []
    label = packet["subconscious_processing"]["active_signal_frame"]["core_statement"][:72]
    return [
        _record(
            kind="direction",
            unit=unit,
            label=label,
            summary="A directional move or recommendation inside the material.",
            confidence=_weighted_confidence(0.7, role_context),
            attributes={
                "tokens": packet["subconscious_processing"]["active_signal_frame"].get("domain_tokens", []),
                "polarity": "protective" if any(word in text for word in ["avoid", "defer", "quiet", "manual"]) else "expansive",
                "source_ref": unit["source_ref"],
                **role_context,
            },
        )
    ]


def _guardrail_records(unit: Dict, role_context: Dict) -> List[Dict]:
    if role_context["semantic_role"] == "approved_context":
        return []
    text = unit["content"].lower()
    if not any(marker in text for marker in ["must not", "should not", "avoid", "defer"]):
        return []
    label = unit["title"][:72]
    return [
        _record(
            kind="guardrail",
            unit=unit,
            label=label,
            summary="An explicit anti-goal or guardrail inside the vault.",
            confidence=_weighted_confidence(0.74, role_context),
            attributes={
                "tokens": tokenize(unit["content"])[:8],
                "polarity": "protective",
                "source_ref": unit["source_ref"],
                **role_context,
            },
        )
    ]


def _base_records_for_unit(unit: Dict, packet: Dict, role_context: Dict) -> List[Dict]:
    if not role_context["knowledge_eligible"]:
        return []
    records: List[Dict] = []
    signal_frame = packet["subconscious_processing"]["active_signal_frame"]
    records.append(
        _record(
            kind="signal_frame",
            unit=unit,
            label=signal_frame["core_statement"][:72],
            summary=signal_frame["generic_structure"],
            confidence=_weighted_confidence(0.72, role_context),
            attributes={
                "tokens": signal_frame.get("domain_tokens", []),
                "transformation_goal": signal_frame.get("transformation_goal"),
                "source_ref": unit["source_ref"],
                **role_context,
            },
        )
    )
    for interpretation in packet["subconscious_processing"].get("parallel_interpretations", []):
        records.append(
            _record(
                kind="interpretation",
                unit=unit,
                label=interpretation["label"],
                summary=interpretation["reading"],
                status=interpretation.get("status", "provisional"),
                confidence=_weighted_confidence(interpretation.get("confidence", 0.6), role_context),
                attributes={
                    "tokens": tokenize(interpretation["reading"])[:8],
                    "source_ref": unit["source_ref"],
                    **role_context,
                },
            )
        )
    if role_context["semantic_role"] != "approved_context":
        for question in packet["subconscious_processing"].get("open_questions", []):
            records.append(
                _record(
                    kind="question",
                    unit=unit,
                    label=question[:72],
                    summary=question,
                    status="speculative",
                    confidence=_weighted_confidence(0.56, role_context),
                    attributes={"tokens": tokenize(question)[:8], "source_ref": unit["source_ref"], **role_context},
                )
            )
        for tension in packet["subconscious_processing"].get("active_tensions", []):
            records.append(
                _record(
                    kind="tension",
                    unit=unit,
                    label=tension["marker"].replace("_", " "),
                    summary=tension["description"],
                    confidence=_weighted_confidence(0.68, role_context),
                    attributes={
                        "tokens": tokenize(tension["description"])[:8],
                        "polarity": "protective",
                        "source_ref": unit["source_ref"],
                        **role_context,
                    },
                )
            )
    for primitive in packet["emergent_structure"].get("shared_primitives", []):
        records.append(
            _record(
                kind="shared_primitive",
                unit=unit,
                label=primitive["label"],
                summary=primitive.get("summary", primitive["label"]),
                confidence=_weighted_confidence(primitive.get("confidence", 0.6), role_context),
                evidence=primitive.get("evidence", []),
                attributes={
                    "tokens": tokenize(" ".join(primitive.get("adjacent_concepts", [])))[:8],
                    "primitive_key": primitive.get("primitive_key"),
                    "family": primitive.get("family", "emergent_pattern"),
                    "transfer_targets": primitive.get("transfer_targets", []),
                    "source_ref": unit["source_ref"],
                    **role_context,
                },
            )
        )
        for concept in primitive.get("adjacent_concepts", [])[:4]:
            records.append(
                _record(
                    kind="adjacent_concept",
                    unit=unit,
                    label=concept.replace("-", " "),
                    summary=f"An adjacent concept around {primitive['label']}.",
                    status="speculative",
                    confidence=_weighted_confidence(0.54, role_context),
                    attributes={
                        "tokens": tokenize(concept)[:5],
                        "linked_to": primitive["primitive_key"],
                        "source_ref": unit["source_ref"],
                        **role_context,
                    },
                )
            )
        for target in primitive.get("transfer_targets", [])[:4]:
            records.append(
                _record(
                    kind="transfer_target",
                    unit=unit,
                    label=target.replace("_", " "),
                    summary=f"A domain where {primitive['label']} may transfer.",
                    status="speculative",
                    confidence=_weighted_confidence(0.55, role_context),
                    attributes={
                        "tokens": tokenize(target)[:5],
                        "linked_to": primitive["primitive_key"],
                        "source_ref": unit["source_ref"],
                        **role_context,
                    },
                )
            )
    for frame in packet["emergent_structure"].get("why_it_matters_frames", []):
        records.append(
            _record(
                kind="why_it_matters",
                unit=unit,
                label=frame["primitive_key"],
                summary=frame["frame"],
                confidence=_weighted_confidence(0.66, role_context),
                attributes={
                    "tokens": tokenize(frame["frame"])[:8],
                    "primitive_key": frame["primitive_key"],
                    "tension_count": frame.get("tension_count", 0),
                    "transfer_count": frame.get("transfer_count", 0),
                    "source_ref": unit["source_ref"],
                    **role_context,
                },
            )
        )
    records.extend(_theme_records(unit, packet, role_context))
    records.extend(_discussion_records(unit, packet, role_context))
    records.extend(_direction_records(unit, packet, role_context))
    records.extend(_guardrail_records(unit, role_context))
    return records


def _corpus_theme_records(units: List[Dict]) -> List[Dict]:
    token_counts: Dict[str, float] = defaultdict(float)
    token_refs: Dict[str, List[Dict]] = defaultdict(list)
    for unit in units:
        weight = float(unit.get("speaker_weight") or 0.8)
        for token in set(unit.get("tokens") or tokenize(unit["content"])):
            token_counts[token] += weight
            token_refs[token].append(unit)
    records = []
    for token, count in sorted(token_counts.items(), key=lambda item: (-item[1], item[0]))[:18]:
        if count < 1.65:
            continue
        supporting = token_refs[token][:4]
        records.append(
            MetaLayerRecord(
                meta_id=f"theme-{hashlib.sha256(f'global:{token}'.encode('utf-8')).hexdigest()[:12]}",
                kind="theme",
                label=token.replace("-", " ").title(),
                summary=f"A cross-vault theme recurring with weighted support {round(count, 2)}.",
                status="provisional",
                confidence=round(min(0.89, 0.5 + count * 0.04), 2),
                source_refs=sorted({item["source_ref"] for item in supporting}),
                chunk_ids=sorted({chunk_id for item in supporting for chunk_id in item["chunk_ids"]}),
                evidence=[item["content"][:180] for item in supporting],
                attributes={"tokens": [token], "support_count": round(count, 2)},
            ).to_dict()
        )
    return records


def _contradiction_records(records: List[Dict]) -> List[Dict]:
    contradictions = []
    candidates = [row for row in records if row["kind"] in {"direction", "guardrail", "tension", "theme"}]
    grouped_by_token: Dict[str, List[Dict]] = defaultdict(list)
    for row in candidates:
        for token in set(row.get("attributes", {}).get("tokens", [])):
            grouped_by_token[token].append(row)
    pair_buckets: Dict[tuple[str, str], Dict] = {}
    for token, rows in grouped_by_token.items():
        if len(rows) < 2 or len(rows) > 48:
            continue
        ordered_rows = sorted(rows, key=lambda item: (-item["confidence"], item["meta_id"]))
        for index, left in enumerate(ordered_rows):
            left_polarity = left.get("attributes", {}).get("polarity")
            for right in ordered_rows[index + 1 :]:
                right_polarity = right.get("attributes", {}).get("polarity")
                contradictory = left_polarity and right_polarity and left_polarity != right_polarity
                theme_vs_tension = {left["kind"], right["kind"]} == {"theme", "tension"}
                if not contradictory and not theme_vs_tension:
                    continue
                pair_key = tuple(sorted([left["meta_id"], right["meta_id"]]))
                bucket = pair_buckets.setdefault(
                    pair_key,
                    {
                        "left": left,
                        "right": right,
                        "shared_tokens": set(),
                        "contradictory": contradictory,
                    },
                )
                bucket["shared_tokens"].add(token)
                bucket["contradictory"] = bucket["contradictory"] or contradictory
    for pair_key, bucket in pair_buckets.items():
        shared = sorted(bucket["shared_tokens"])
        left = bucket["left"]
        right = bucket["right"]
        label = " / ".join(shared[:3]).title()
        contradictions.append(
            MetaLayerRecord(
                meta_id=f"contradiction-{hashlib.sha256(':'.join(pair_key).encode('utf-8')).hexdigest()[:12]}",
                kind="contradiction",
                label=label or "Design Tension",
                summary=f"{left['label']} pushes against {right['label']}.",
                status="provisional",
                confidence=0.71 if bucket["contradictory"] else 0.62,
                source_refs=sorted(set(left["source_refs"] + right["source_refs"])),
                chunk_ids=sorted(set(left["chunk_ids"] + right["chunk_ids"])),
                evidence=[left["summary"], right["summary"]],
                attributes={
                    "left_ref": left["meta_id"],
                    "right_ref": right["meta_id"],
                    "tokens": shared[:6],
                },
            ).to_dict()
        )
    return contradictions


def _review_item_records(records: List[Dict], contradictions: List[Dict]) -> List[Dict]:
    review_items = []
    for contradiction in contradictions:
        review_items.append(
            MetaLayerRecord(
                meta_id=f"review-{hashlib.sha256(contradiction['meta_id'].encode('utf-8')).hexdigest()[:12]}",
                kind="review_item",
                label=contradiction["label"],
                summary=f"Review whether this contradiction should remain active: {contradiction['summary']}",
                status="ready_for_review",
                confidence=contradiction["confidence"],
                source_refs=contradiction["source_refs"],
                chunk_ids=contradiction["chunk_ids"],
                evidence=contradiction["evidence"],
                attributes={"linked_to": contradiction["meta_id"]},
            ).to_dict()
        )
    low_confidence = [row for row in records if row["kind"] in {"shared_primitive", "direction"} and row["confidence"] < 0.58]
    for row in low_confidence[:24]:
        review_items.append(
            MetaLayerRecord(
                meta_id=f"review-{hashlib.sha256(row['meta_id'].encode('utf-8')).hexdigest()[:12]}",
                kind="review_item",
                label=row["label"],
                summary=f"Review whether `{row['label']}` should stay in the meta-layer.",
                status="ready_for_review",
                confidence=row["confidence"],
                source_refs=row["source_refs"],
                chunk_ids=row["chunk_ids"],
                evidence=row["evidence"],
                attributes={"linked_to": row["meta_id"]},
            ).to_dict()
        )
    return review_items


def extract_meta_layer(root: Path, domain_overlays: List[str] | None = None, ensure_dependencies: bool = True) -> Dict:
    ensure_dir(meta_layer_dir(root))
    if ensure_dependencies:
        analysis_summary = build_analysis_units(root)
        delta_summary = build_conversation_deltas(root)
    else:
        analysis_summary = {
            "chunk_count": sum(1 for _ in read_jsonl(root / "product" / "inner_world_v1" / "data" / "chunk_index.jsonl")),
            "analysis_unit_count": len(load_analysis_units(root)),
        }
        delta_summary = {
            "delta_count": len(load_conversation_deltas(root)),
        }
    units = load_analysis_units(root)
    delta_rows = load_conversation_deltas(root)
    expectation_rows = load_user_expectations(root)
    plugins = load_plugins(root, domain_overlays)
    plugin_primitives = []
    for plugin in plugins:
        plugin_primitives.extend(plugin.get("reasoning_primitives", []))

    records_by_kind = {kind: [] for kind in META_LAYER_KINDS}
    for unit in units:
        packet = run_pipeline(
            root,
            "vault_decomposition_v1",
            {
                "stimulus": {"raw_text": unit["content"], "source_ref": unit["source_ref"], "chunk_id": unit["unit_id"]},
                "subconscious_processing": {},
                "emergent_structure": {},
                "conscious_articulation": {},
                "memory_commit": {},
            },
            {"plugin_primitives": plugin_primitives},
        )
        role_context = _unit_role_context(unit, delta_rows)
        for record in _base_records_for_unit(unit, packet, role_context):
            records_by_kind[record["kind"]].append(record)

    semantic_line_units = [unit for unit in units if _unit_role_context(unit, delta_rows)["theme_eligible"]]
    for record in _corpus_theme_records(semantic_line_units):
        records_by_kind[record["kind"]].append(record)

    all_non_contradiction = []
    for kind, rows in records_by_kind.items():
        if kind in {"contradiction", "review_item"}:
            continue
        all_non_contradiction.extend(rows)
    contradictions = _contradiction_records(all_non_contradiction)
    records_by_kind["contradiction"].extend(contradictions)
    records_by_kind["review_item"].extend(_review_item_records(all_non_contradiction, contradictions))

    counts = {}
    for kind, rows in records_by_kind.items():
        deduped = {row["meta_id"]: row for row in rows}
        ordered = sorted(deduped.values(), key=lambda item: (item["label"], item["meta_id"]))
        write_jsonl(_meta_path(root, kind), ordered)
        counts[kind] = len(ordered)
    return {
        "chunk_count": analysis_summary["chunk_count"],
        "analysis_unit_count": analysis_summary["analysis_unit_count"],
        "delta_count": delta_summary["delta_count"],
        "expectation_count": len(expectation_rows),
        "meta_counts": counts,
        "total_meta_records": sum(counts.values()),
    }
