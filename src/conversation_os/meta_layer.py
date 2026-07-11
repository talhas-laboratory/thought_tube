from __future__ import annotations

import hashlib
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List

from .analysis_units import build_analysis_units, load_analysis_units
from .conversation_deltas import build_conversation_deltas, load_conversation_deltas, load_user_expectations
from .meta_objects import META_LAYER_FILES, META_LAYER_KINDS
from .models import (
    AlternativeInterpretation,
    CandidateShape,
    EvidenceSpan,
    MetaLayerRecord,
    SignatureAbsence,
    SignatureAffordance,
    SignatureConstraint,
    SignatureEntity,
    SignatureFeedbackLoop,
    SignatureRelation,
    SignatureState,
    ShapeGraphEdge,
    ShapeGraphNode,
    ShapeMemoryItem,
    SystemDynamicSignature,
)
from .pipeline_runner import run_pipeline
from .plugins import load_plugins
from .storage import ensure_dir, read_jsonl, utc_now, write_jsonl
from .vault_ingest import tokenize


MODULE_ID = "kernel.meta.meta_layer"
CONTRACT_VERSION = "1.0"
PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "meta_layer_dir",
    "shape_signatures_path",
    "shape_graph_nodes_path",
    "shape_graph_edges_path",
    "shape_memory_path",
    "load_meta_records",
    "load_shape_signatures",
    "load_shape_graph_nodes",
    "load_shape_graph_edges",
    "load_shape_memory",
    "find_shape_memory_matches",
    "record_shape_feedback",
    "extract_meta_layer",
    "extract_shape_signatures",
    "build_shape_graph",
)
__all__ = list(PUBLIC_API)


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


def shape_signatures_path(root: Path) -> Path:
    return root / "product" / "inner_world_v1" / "data" / "shape_signatures.jsonl"


def load_shape_signatures(root: Path) -> List[Dict]:
    return read_jsonl(shape_signatures_path(root))


def shape_graph_nodes_path(root: Path) -> Path:
    return root / "product" / "inner_world_v1" / "data" / "shape_graph_nodes.jsonl"


def shape_graph_edges_path(root: Path) -> Path:
    return root / "product" / "inner_world_v1" / "data" / "shape_graph_edges.jsonl"


def shape_memory_path(root: Path) -> Path:
    return root / "product" / "inner_world_v1" / "data" / "shape_memory.jsonl"


def load_shape_graph_nodes(root: Path) -> List[Dict]:
    return read_jsonl(shape_graph_nodes_path(root))


def load_shape_graph_edges(root: Path) -> List[Dict]:
    return read_jsonl(shape_graph_edges_path(root))


def load_shape_memory(root: Path) -> List[Dict]:
    return read_jsonl(shape_memory_path(root))


def find_shape_memory_matches(
    root: Path,
    *,
    scope: str | None = None,
    scope_key: str | None = None,
    shape_name: str | None = None,
    anchor_meta_id: str | None = None,
    candidate_meta_id: str | None = None,
) -> List[Dict]:
    rows = load_shape_memory(root)
    matched: List[Dict] = []
    normalized_scope = str(scope or "").strip()
    normalized_scope_key = str(scope_key or "").strip()
    normalized_shape_name = str(shape_name or "").strip().lower()
    normalized_anchor_meta_id = str(anchor_meta_id or "").strip()
    normalized_candidate_meta_id = str(candidate_meta_id or "").strip()
    for row in rows:
        if normalized_scope and str(row.get("scope", "")).strip() != normalized_scope:
            continue
        if normalized_scope_key and str(row.get("scope_key", "")).strip() != normalized_scope_key:
            continue
        if normalized_shape_name and str(row.get("shape_name", "")).strip().lower() != normalized_shape_name:
            continue
        records = row.get("attributes", {}).get("anti_match_records", [])
        if normalized_anchor_meta_id or normalized_candidate_meta_id:
            if not any(
                (not normalized_anchor_meta_id or str(record.get("anchor_meta_id", "")).strip() == normalized_anchor_meta_id)
                and (not normalized_candidate_meta_id or str(record.get("candidate_meta_id", "")).strip() == normalized_candidate_meta_id)
                for record in records
            ):
                continue
        matched.append(row)
    return matched


def _dedupe_strings(values: List[str]) -> List[str]:
    seen = set()
    ordered: List[str] = []
    for value in values:
        normalized = str(value).strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(normalized)
    return ordered


def record_shape_feedback(
    root: Path,
    *,
    scope: str,
    scope_key: str,
    shape_name: str,
    shape_definition: str,
    feedback_type: str,
    validated_example: str = "",
    rejected_candidate_id: str = "",
    anchor_meta_id: str = "",
    anti_match_penalty: float = 0.0,
    intervention: str = "",
    missing_constraint: str = "",
) -> Dict:
    rows = load_shape_memory(root)
    normalized_scope = scope.strip()
    normalized_scope_key = scope_key.strip()
    normalized_shape_name = shape_name.strip()
    normalized_feedback_type = feedback_type.strip().lower()
    now = utc_now()
    existing = next(
        (
            row
            for row in rows
            if str(row.get("scope", "")).strip() == normalized_scope
            and str(row.get("scope_key", "")).strip() == normalized_scope_key
            and str(row.get("shape_name", "")).strip() == normalized_shape_name
        ),
        None,
    )
    if existing is None:
        existing = ShapeMemoryItem(
            memory_id=_make_id("shape-memory", normalized_scope_key or "global", normalized_shape_name or "shape"),
            scope=normalized_scope,
            scope_key=normalized_scope_key,
            shape_name=normalized_shape_name,
            shape_definition=shape_definition.strip(),
            updated_at=now,
        ).to_dict()
        rows.append(existing)

    existing["shape_definition"] = shape_definition.strip() or str(existing.get("shape_definition", "")).strip()
    existing["validated_examples"] = list(existing.get("validated_examples", []))
    existing["anti_matches"] = list(existing.get("anti_matches", []))
    existing["interventions"] = list(existing.get("interventions", []))
    existing["missing_constraints"] = list(existing.get("missing_constraints", []))
    attributes = dict(existing.get("attributes", {}))
    anti_match_records = list(attributes.get("anti_match_records", []))

    if normalized_feedback_type == "accepted":
        existing["validation_count"] = int(existing.get("validation_count", 0)) + 1
        existing["last_validated_at"] = now
        if validated_example.strip():
            existing["validated_examples"] = _dedupe_strings(existing["validated_examples"] + [validated_example])
        if intervention.strip():
            existing["interventions"] = _dedupe_strings(existing["interventions"] + [intervention])
    elif normalized_feedback_type in {"rejected", "wrong_analogy", "anti_match"}:
        existing["rejection_count"] = int(existing.get("rejection_count", 0)) + 1
        if rejected_candidate_id.strip():
            existing["anti_matches"] = _dedupe_strings(existing["anti_matches"] + [rejected_candidate_id])
            record = next(
                (
                    item
                    for item in anti_match_records
                    if str(item.get("anchor_meta_id", "")).strip() == anchor_meta_id.strip()
                    and str(item.get("candidate_meta_id", "")).strip() == rejected_candidate_id.strip()
                ),
                None,
            )
            if record is None:
                anti_match_records.append(
                    {
                        "anchor_meta_id": anchor_meta_id.strip(),
                        "candidate_meta_id": rejected_candidate_id.strip(),
                        "anti_match_penalty": round(max(0.0, anti_match_penalty), 3),
                        "updated_at": now,
                    }
                )
            else:
                record["anti_match_penalty"] = round(
                    max(float(record.get("anti_match_penalty", 0.0)), max(0.0, anti_match_penalty)),
                    3,
                )
                record["updated_at"] = now
    if missing_constraint.strip():
        existing["missing_constraints"] = _dedupe_strings(existing["missing_constraints"] + [missing_constraint])

    attributes["anti_match_records"] = anti_match_records
    existing["attributes"] = attributes
    existing["updated_at"] = now
    write_jsonl(shape_memory_path(root), rows)
    return existing


def _make_id(kind: str, anchor_id: str, label: str) -> str:
    digest = hashlib.sha256(f"{kind}:{anchor_id}:{label}".encode("utf-8")).hexdigest()[:12]
    return f"{kind}-{digest}"


def _text_contains_any(text: str, markers: List[str]) -> bool:
    return any(marker in text for marker in markers)


def _matching_meta_rows(unit: Dict, meta_rows: List[Dict]) -> List[Dict]:
    unit_chunk_ids = set(unit.get("chunk_ids", []))
    unit_source_ref = unit.get("source_ref")
    matched = []
    for row in meta_rows:
        row_source_refs = set(row.get("source_refs", []))
        row_chunk_ids = set(row.get("chunk_ids", []))
        if unit_source_ref and unit_source_ref not in row_source_refs:
            continue
        if unit_chunk_ids and not unit_chunk_ids.intersection(row_chunk_ids):
            continue
        matched.append(row)
    return matched


def _evidence_spans_for_unit(unit: Dict, meta_rows: List[Dict]) -> List[Dict]:
    direct_text = unit.get("content", "").strip()
    spans = [
        EvidenceSpan(
            source_ref=unit["source_ref"],
            chunk_id=unit.get("anchor_chunk_id") or unit["chunk_ids"][0],
            text=direct_text[:280],
            kind="direct_quote",
        ).to_dict()
    ]
    for row in meta_rows[:3]:
        evidence_text = (row.get("evidence") or [row.get("summary", "")])[0]
        if not evidence_text:
            continue
        spans.append(
            EvidenceSpan(
                source_ref=row.get("source_refs", [unit["source_ref"]])[0],
                chunk_id=(row.get("chunk_ids") or [unit["chunk_ids"][0]])[0],
                text=evidence_text[:220],
                kind=f"meta_{row['kind']}",
                attributes={"meta_id": row["meta_id"]},
            ).to_dict()
        )
    return spans


def _build_candidate_shapes(unit: Dict, meta_rows: List[Dict], text: str) -> List[Dict]:
    candidates: List[Dict] = []
    seen = set()
    for row in meta_rows:
        if row["kind"] != "shared_primitive":
            continue
        shape_name = row["label"].strip()
        key = shape_name.lower()
        if not shape_name or key in seen:
            continue
        seen.add(key)
        candidates.append(
            CandidateShape(
                shape_name=shape_name,
                confidence=row.get("confidence", 0.6),
                rationale=row.get("summary", ""),
                attributes={
                    "origin": "shared_primitive",
                    "primitive_key": row.get("attributes", {}).get("primitive_key", ""),
                },
            ).to_dict()
        )
    if (
        _text_contains_any(text, ["many", "too many", "keep adding", "adding", "crowded", "feature"])
        and _text_contains_any(text, ["do not understand", "don't understand", "unclear", "confus", "overwhelm"])
        and "signal dilution through accumulation" not in seen
    ):
        candidates.append(
            CandidateShape(
                shape_name="Signal Dilution Through Accumulation",
                confidence=0.68,
                rationale="Accumulating useful elements without scalable hierarchy makes the main signal harder to perceive.",
                attributes={"origin": "heuristic_pattern"},
            ).to_dict()
        )
    return candidates


def _build_alternative_interpretations(meta_rows: List[Dict], text: str) -> List[Dict]:
    alternatives: List[Dict] = []
    for row in meta_rows:
        if row["kind"] != "interpretation":
            continue
        alternatives.append(
            AlternativeInterpretation(
                title=row["label"],
                summary=row["summary"],
                confidence=row.get("confidence", 0.6),
                attributes={"origin": "interpretation"},
            ).to_dict()
        )
    if _text_contains_any(text, ["what it is", "value proposition", "message", "framing"]):
        alternatives.append(
            AlternativeInterpretation(
                title="Failed Translation of Hidden Value",
                summary="The problem may be value framing or message translation, not accumulation alone.",
                confidence=0.58,
                attributes={"origin": "heuristic_pattern"},
            ).to_dict()
        )
    return alternatives


def _build_signature_for_unit(unit: Dict, meta_rows: List[Dict]) -> Dict | None:
    text = unit.get("content", "").lower()
    signal_frame = next((row for row in meta_rows if row["kind"] == "signal_frame"), None)
    candidate_shapes = _build_candidate_shapes(unit, meta_rows, text)
    if not signal_frame and not candidate_shapes:
        return None

    evidence_spans = _evidence_spans_for_unit(unit, meta_rows)
    title = signal_frame["label"] if signal_frame else unit["title"]
    summary = signal_frame["summary"] if signal_frame else unit["content"][:220]
    created_at = unit.get("created_at") or utc_now()
    desired_transformation = ""
    if signal_frame:
        desired_transformation = signal_frame.get("attributes", {}).get("transformation_goal", "")

    entities: List[Dict] = []
    states: List[Dict] = []
    relations: List[Dict] = []
    feedback_loops: List[Dict] = []
    constraints: List[Dict] = []
    absences: List[Dict] = []
    affordances: List[Dict] = []

    accumulation_markers = ["many", "too many", "keep adding", "adding", "accumulate", "feature", "features"]
    confusion_markers = ["do not understand", "don't understand", "unclear", "confus", "overwhelm", "what it is"]
    explanation_markers = ["explanation", "explanations", "onboarding", "documentation", "docs", "tutorial"]
    hierarchy_markers = ["primary", "main path", "clear hierarchy", "dominant", "hierarchy", "lead"]

    is_accumulation_case = _text_contains_any(text, accumulation_markers) and _text_contains_any(text, confusion_markers)
    has_explanation_feedback = _text_contains_any(text, explanation_markers)

    if is_accumulation_case:
        added_elements_id = "entity-added-elements"
        receiver_id = "entity-receiver-capacity"
        signal_id = "entity-source-signal"
        confusion_state_id = "state-receiver-confusion"
        explanation_id = "entity-coordination-layer"

        entities.append(
            SignatureEntity(
                entity_id=added_elements_id,
                label="Features" if "feature" in text else "Accumulating elements",
                node_type="entity",
                role="added_elements",
                confidence=0.78,
                evidence=evidence_spans[:1],
            ).to_dict()
        )
        entities.append(
            SignatureEntity(
                entity_id=receiver_id,
                label="User attention" if "user" in text else "Receiver attention",
                node_type="resource",
                role="limited_receiver_capacity",
                confidence=0.74,
                evidence=evidence_spans[:1],
            ).to_dict()
        )
        entities.append(
            SignatureEntity(
                entity_id=signal_id,
                label="Core value" if _text_contains_any(text, ["value", "what it is", "product"]) else "Primary signal",
                node_type="signal",
                role="source_signal",
                confidence=0.72,
                evidence=evidence_spans[:1],
            ).to_dict()
        )
        if has_explanation_feedback:
            entities.append(
                SignatureEntity(
                    entity_id=explanation_id,
                    label="Explanation layer",
                    node_type="entity",
                    role="coordination_layer",
                    confidence=0.68,
                    evidence=evidence_spans[:1],
                ).to_dict()
            )

        states.append(
            SignatureState(
                state_id=confusion_state_id,
                label="Receiver confusion",
                confidence=0.77,
                evidence=evidence_spans[:1],
            ).to_dict()
        )

        relation_ids: List[str] = []
        relation_one = SignatureRelation(
            relation_id="relation-added-elements-compete-receiver",
            source_id=added_elements_id,
            target_id=receiver_id,
            edge_type="competes_with",
            operation="accumulate",
            confidence=0.76,
            evidence=evidence_spans[:1],
        ).to_dict()
        relation_ids.append(relation_one["relation_id"])
        relations.append(relation_one)

        relation_two = SignatureRelation(
            relation_id="relation-added-elements-hide-signal",
            source_id=added_elements_id,
            target_id=signal_id,
            edge_type="hides",
            operation="accumulate",
            confidence=0.8,
            evidence=evidence_spans[:1],
        ).to_dict()
        relation_ids.append(relation_two["relation_id"])
        relations.append(relation_two)

        if has_explanation_feedback:
            relation_three = SignatureRelation(
                relation_id="relation-confusion-causes-explanations",
                source_id=confusion_state_id,
                target_id=explanation_id,
                edge_type="causes",
                operation="amplify",
                confidence=0.7,
                evidence=evidence_spans[:1],
            ).to_dict()
            relation_four = SignatureRelation(
                relation_id="relation-explanations-feed-complexity",
                source_id=explanation_id,
                target_id=added_elements_id,
                edge_type="feeds_back_into",
                operation="amplify",
                confidence=0.72,
                evidence=evidence_spans[:1],
            ).to_dict()
            relation_ids.extend([relation_three["relation_id"], relation_four["relation_id"]])
            relations.extend([relation_three, relation_four])
            feedback_loops.append(
                SignatureFeedbackLoop(
                    loop_id="feedback-loop-clarity-complexity",
                    label="Confusion drives more explanation, which increases surface complexity.",
                    node_ids=[confusion_state_id, explanation_id, added_elements_id],
                    edge_ids=[relation_three["relation_id"], relation_four["relation_id"]],
                    confidence=0.69,
                    evidence=evidence_spans[:2],
                ).to_dict()
            )

        constraints.append(
            SignatureConstraint(
                constraint_id="constraint-limited-receiver-capacity",
                label="Limited receiver capacity",
                confidence=0.75,
                evidence=evidence_spans[:1],
            ).to_dict()
        )
        if not _text_contains_any(text, hierarchy_markers):
            absences.append(
                SignatureAbsence(
                    absence_id="absence-primary-hierarchy",
                    label="Missing primary hierarchy",
                    confidence=0.71,
                    evidence=evidence_spans[:1],
                ).to_dict()
            )
        affordances.append(
            SignatureAffordance(
                affordance_id="affordance-hierarchy-restoration",
                label="Hierarchy can restore the dominant signal without removing depth",
                confidence=0.66,
                evidence=evidence_spans[:2],
            ).to_dict()
        )

    missing_information = [row["summary"] for row in meta_rows if row["kind"] == "question"]
    alternatives = _build_alternative_interpretations(meta_rows, text)
    confidence_rows = [row.get("confidence", 0.6) for row in meta_rows]
    confidence = round(sum(confidence_rows) / max(1, len(confidence_rows)), 2)
    failure_mode = candidate_shapes[0]["shape_name"] if candidate_shapes else ""
    observer_lens = "structural_interpretation"
    if signal_frame and signal_frame.get("attributes", {}).get("speaker_role"):
        observer_lens = signal_frame["attributes"]["speaker_role"]

    return SystemDynamicSignature(
        signature_id=_make_id("signature", unit["unit_id"], title),
        source_ref=unit["source_ref"],
        source_kind="analysis_unit",
        source_anchor_id=unit["unit_id"],
        title=title,
        summary=summary,
        system_boundary=unit["title"],
        observer_lens=observer_lens,
        entities=entities,
        states=states,
        relations=relations,
        feedback_loops=feedback_loops,
        constraints=constraints,
        absences=absences,
        affordances=affordances,
        failure_mode=failure_mode,
        desired_transformation=desired_transformation,
        candidate_shapes=candidate_shapes,
        alternative_interpretations=alternatives,
        evidence_spans=evidence_spans,
        missing_information=missing_information,
        confidence=confidence,
        status="provisional",
        version=1,
        created_at=created_at,
        updated_at=created_at,
        attributes={
            "source_meta_ids": [row["meta_id"] for row in meta_rows],
            "source_chunk_ids": unit.get("chunk_ids", []),
        },
    ).to_dict()


def _signature_graph_nodes(signature: Dict) -> List[Dict]:
    nodes: List[Dict] = []
    signature_id = signature["signature_id"]
    for entity in signature.get("entities", []):
        nodes.append(
            ShapeGraphNode(
                graph_node_id=f"{signature_id}:{entity['entity_id']}",
                signature_id=signature_id,
                node_key=entity["entity_id"],
                node_type=entity.get("node_type", "entity"),
                label=entity["label"],
                role=entity.get("role", ""),
                confidence=entity.get("confidence", 0.0),
                attributes={"origin": "entity"},
            ).to_dict()
        )
    for state in signature.get("states", []):
        nodes.append(
            ShapeGraphNode(
                graph_node_id=f"{signature_id}:{state['state_id']}",
                signature_id=signature_id,
                node_key=state["state_id"],
                node_type="state",
                label=state["label"],
                confidence=state.get("confidence", 0.0),
                attributes={"origin": "state"},
            ).to_dict()
        )
    for constraint in signature.get("constraints", []):
        nodes.append(
            ShapeGraphNode(
                graph_node_id=f"{signature_id}:{constraint['constraint_id']}",
                signature_id=signature_id,
                node_key=constraint["constraint_id"],
                node_type="constraint",
                label=constraint["label"],
                confidence=constraint.get("confidence", 0.0),
                attributes={"origin": "constraint"},
            ).to_dict()
        )
    for absence in signature.get("absences", []):
        nodes.append(
            ShapeGraphNode(
                graph_node_id=f"{signature_id}:{absence['absence_id']}",
                signature_id=signature_id,
                node_key=absence["absence_id"],
                node_type="absence",
                label=absence["label"],
                confidence=absence.get("confidence", 0.0),
                attributes={"origin": "absence"},
            ).to_dict()
        )
    for affordance in signature.get("affordances", []):
        nodes.append(
            ShapeGraphNode(
                graph_node_id=f"{signature_id}:{affordance['affordance_id']}",
                signature_id=signature_id,
                node_key=affordance["affordance_id"],
                node_type="affordance",
                label=affordance["label"],
                confidence=affordance.get("confidence", 0.0),
                attributes={"origin": "affordance"},
            ).to_dict()
        )
    return nodes


def _feedback_loop_edge_index(signature: Dict) -> Dict[str, List[str]]:
    index: Dict[str, List[str]] = defaultdict(list)
    for loop in signature.get("feedback_loops", []):
        loop_id = loop.get("loop_id", "")
        if not loop_id:
            continue
        for edge_id in loop.get("edge_ids", []):
            index[edge_id].append(loop_id)
    return {edge_id: sorted(loop_ids) for edge_id, loop_ids in index.items()}


def _signature_graph_edges(signature: Dict) -> List[Dict]:
    signature_id = signature["signature_id"]
    loop_index = _feedback_loop_edge_index(signature)
    edges: List[Dict] = []
    for relation in signature.get("relations", []):
        edges.append(
            ShapeGraphEdge(
                graph_edge_id=relation["relation_id"],
                signature_id=signature_id,
                source_node_key=relation["source_id"],
                target_node_key=relation["target_id"],
                edge_type=relation["edge_type"],
                operation=relation.get("operation", ""),
                confidence=relation.get("confidence", 0.0),
                attributes={
                    "origin": "relation",
                    "feedback_loop_ids": loop_index.get(relation["relation_id"], []),
                },
            ).to_dict()
        )
    return edges


def _count_invalid_edges(nodes: List[Dict], edges: List[Dict]) -> int:
    valid_node_keys = {row["node_key"] for row in nodes}
    invalid_count = 0
    for edge in edges:
        if edge["source_node_key"] not in valid_node_keys or edge["target_node_key"] not in valid_node_keys:
            invalid_count += 1
    return invalid_count


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


def extract_shape_signatures(root: Path, domain_overlays: List[str] | None = None, ensure_dependencies: bool = True) -> Dict:
    if ensure_dependencies:
        extract_meta_layer(root, domain_overlays=domain_overlays, ensure_dependencies=True)
    units = load_analysis_units(root)
    meta_rows = load_meta_records(root)

    # Pre-build index of meta_rows by chunk_id for fast O(1) lookup
    from collections import defaultdict
    chunk_to_meta = defaultdict(list)
    for row in meta_rows:
        for chunk_id in row.get("chunk_ids", []):
            chunk_to_meta[chunk_id].append(row)

    signatures: List[Dict] = []
    for unit in units:
        unit_chunk_ids = unit.get("chunk_ids", [])
        unit_source_ref = unit.get("source_ref")
        
        matched_set = {}
        for chunk_id in unit_chunk_ids:
            for row in chunk_to_meta[chunk_id]:
                matched_set[id(row)] = row
                
        matching_rows = []
        for row in matched_set.values():
            if unit_source_ref and unit_source_ref not in row.get("source_refs", []):
                continue
            matching_rows.append(row)
            
        signature = _build_signature_for_unit(unit, matching_rows)
        if signature is not None:
            signatures.append(signature)
            
    write_jsonl(shape_signatures_path(root), signatures)
    return {
        "analysis_unit_count": len(units),
        "meta_record_count": len(meta_rows),
        "shape_signature_count": len(signatures),
    }


def build_shape_graph(root: Path, domain_overlays: List[str] | None = None, ensure_dependencies: bool = True) -> Dict:
    if ensure_dependencies:
        extract_shape_signatures(root, domain_overlays=domain_overlays, ensure_dependencies=True)
    signatures = load_shape_signatures(root)
    nodes: List[Dict] = []
    edges: List[Dict] = []
    for signature in signatures:
        nodes.extend(_signature_graph_nodes(signature))
        edges.extend(_signature_graph_edges(signature))
    write_jsonl(shape_graph_nodes_path(root), nodes)
    write_jsonl(shape_graph_edges_path(root), edges)
    invalid_edge_count = _count_invalid_edges(nodes, edges)
    return {
        "shape_signature_count": len(signatures),
        "shape_graph_node_count": len(nodes),
        "shape_graph_edge_count": len(edges),
        "invalid_edge_count": invalid_edge_count,
    }
