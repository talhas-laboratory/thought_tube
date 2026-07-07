from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional, Sequence, Set, Tuple

from pathlib import Path

from .storage import (
    append_jsonl,
    ensure_dir,
    make_id,
    read_json,
    read_jsonl,
    session_dir,
    session_events_path,
    utc_now,
    write_json,
)

MODULE_ID = "kernel.mtsf.graph"
CONTRACT_VERSION = "1.0.0"
STORE_VERSION = "1.0.0"
GRAPH_VERSION = "1.0.0"
GLOBAL_GRAPH_VERSION = "1.0.0"
SUBSTRATE_PREVIEW_LIMIT = 500

TraversalMode = Literal["semantic", "structural", "provenance", "temporal", "activation", "alias"]
GraphScope = Literal["session", "global"]
ACTIVATION_CONFIDENCE_THRESHOLD = 0.35
DetailFacet = Literal["identity", "configuration", "evidence", "substrate", "payload"]
ExpandFacet = Literal["identity", "configuration", "evidence", "substrate", "payload", "all"]

PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "STORE_VERSION",
    "GRAPH_VERSION",
    "GLOBAL_GRAPH_VERSION",
    "SUBSTRATE_PREVIEW_LIMIT",
    "SubstrateIndex",
    "assertion_store_path",
    "content_graph_path",
    "default_graph_events_path",
    "default_global_content_graph_path",
    "build_substrate_index",
    "substrate_ref_fields",
    "apply_substrate_refs_to_draft",
    "build_evidence_bundle",
    "build_assertion_store_from_draft",
    "project_content_graph",
    "materialize_session_graph",
    "load_assertion_store",
    "load_content_graph",
    "load_global_content_graph",
    "empty_global_content_graph",
    "merge_session_graph_into_global",
    "append_graph_event",
    "read_graph_events",
    "promote_session_graph_to_global",
    "rebuild_global_content_graph",
    "ACTIVATION_CONFIDENCE_THRESHOLD",
    "activation_snapshot_path",
    "derive_activation_summary",
    "resolve_activation_bindings",
    "sync_activation_to_content_graph",
    "get_active_content_nodes",
    "GraphScope",
    "resolve_global_node_id",
    "refresh_global_alias_adjacency",
    "follow_traversal",
    "expand_node",
)
__all__ = list(PUBLIC_API)


@dataclass
class SubstrateIndex:
    text: str
    event_spans: List[Tuple[str, int, int]]

    def anchor_span(self, span: str) -> Optional[Dict[str, Any]]:
        needle = span.strip()
        if not needle:
            return None
        lowered_text = self.text.lower()
        lowered_needle = needle.lower()
        start = lowered_text.find(lowered_needle)
        if start < 0 and len(needle) > 80:
            start = lowered_text.find(lowered_needle[:80])
        if start < 0:
            return None
        end = start + len(needle)
        event_id = self._event_id_for_offset(start)
        excerpt = self.text[start:end][:500]
        return {
            "event_id": event_id,
            "char_start": start,
            "char_end": end,
            "excerpt": excerpt,
        }

    def _event_id_for_offset(self, offset: int) -> str:
        for event_id, char_start, char_end in self.event_spans:
            if char_start <= offset < char_end:
                return event_id
        if self.event_spans:
            return self.event_spans[-1][0]
        return "unknown"


def assertion_store_path(root, session_id: str):
    return session_dir(root, session_id) / "mtsf" / "assertion_store.json"


def content_graph_path(root, session_id: str):
    return session_dir(root, session_id) / "mtsf" / "content_graph.json"


def build_substrate_index(events: Sequence[Dict[str, Any]]) -> SubstrateIndex:
    parts: List[str] = []
    event_spans: List[Tuple[str, int, int]] = []
    cursor = 0
    for event in events:
        event_id = str(event.get("event_id") or make_id("ev"))
        content = str(event.get("content", "")).strip()
        if not content:
            continue
        if parts:
            parts.append("\n\n")
            cursor += 2
        char_start = cursor
        parts.append(content)
        cursor += len(content)
        event_spans.append((event_id, char_start, cursor))
    return SubstrateIndex(text="".join(parts), event_spans=event_spans)


def _evidence_from_item(item: Dict[str, Any]) -> Dict[str, Any]:
    return dict(item.get("evidence", {}) or {})


def build_evidence_bundle(
    *,
    spans: Sequence[str],
    source_refs: Optional[Sequence[str]] = None,
    substrate: Optional[SubstrateIndex] = None,
) -> Dict[str, Any]:
    bundle_id = make_id("evb")
    clean_spans = [str(span).strip() for span in spans if str(span).strip()]
    if not clean_spans:
        clean_spans = ["derived"]
    anchors: List[Dict[str, Any]] = []
    if substrate:
        for index, span in enumerate(clean_spans):
            anchor = substrate.anchor_span(span)
            if anchor:
                anchor["span_index"] = index
                anchors.append(anchor)
    return {
        "id": bundle_id,
        "spans": clean_spans,
        "anchors": anchors,
        "source_refs": sorted(set(source_refs or [])),
    }


def _facet_completeness_for_entity(entity: Dict[str, Any], *, has_anchors: bool) -> Dict[str, bool]:
    return {
        "identity": bool(entity.get("name")) and bool(entity.get("stable_identity")),
        "configuration": bool(entity.get("type")),
        "evidence": bool(_evidence_from_item(entity).get("spans")),
        "substrate": has_anchors,
        "causal_geometry": False,
        "temporal_dynamics": False,
        "constraint_landscape": False,
        "cybernetic_feedback": False,
    }


def _facet_completeness_for_stencil(stencil: Dict[str, Any], *, has_anchors: bool) -> Dict[str, bool]:
    facets = dict(stencil.get("facet_completeness", {}) or {})
    topology = stencil.get("relation_topology", [])
    return {
        "identity": bool(stencil.get("proposed_name")),
        "configuration": bool(topology),
        "evidence": bool(_evidence_from_item(stencil).get("spans")),
        "substrate": has_anchors,
        "causal_geometry": bool(facets.get("causal_geometry")),
        "temporal_dynamics": bool(facets.get("temporal_dynamics")),
        "constraint_landscape": bool(facets.get("constraint_landscape")),
        "cybernetic_feedback": bool(facets.get("cybernetic_feedback")),
    }


def _detail_level_from_facets(facets: Dict[str, bool]) -> str:
    if facets.get("substrate"):
        return "substrate"
    if facets.get("evidence"):
        return "evidence"
    if facets.get("configuration"):
        return "configuration"
    if facets.get("identity"):
        return "identity"
    return "handle"


def _assertion(
    *,
    kind: str,
    subject_ref: str,
    payload: Dict[str, Any],
    bundle: Dict[str, Any],
    confidence: float,
    facet_completeness: Dict[str, bool],
    status: str,
) -> Dict[str, Any]:
    return {
        "id": make_id("ast"),
        "kind": kind,
        "subject_ref": subject_ref,
        "payload": payload,
        "confidence": confidence,
        "detail_level": _detail_level_from_facets(facet_completeness),
        "facet_completeness": facet_completeness,
        "evidence_bundle_id": bundle["id"],
        "status": status,
    }


def build_assertion_store_from_draft(
    root,
    session_id: str,
    draft: Dict[str, Any],
    *,
    events: Optional[Sequence[Dict[str, Any]]] = None,
    status: str = "proposed",
) -> Dict[str, Any]:
    if events is None:
        events = read_jsonl(session_events_path(root, session_id))
    substrate = build_substrate_index(events)
    substrate_ref = str(session_events_path(root, session_id))
    raw_content_ref = draft.get("raw_content_ref")
    if not raw_content_ref and draft.get("raw_content"):
        raw_content_ref = str(session_dir(root, session_id) / "mtsf" / "extraction_draft.json")

    bundles: Dict[str, Dict[str, Any]] = {}
    assertions: List[Dict[str, Any]] = []

    def register_bundle(
        spans: Sequence[str],
        source_refs: Optional[Sequence[str]] = None,
    ) -> Dict[str, Any]:
        bundle = build_evidence_bundle(spans=spans, source_refs=source_refs, substrate=substrate)
        bundles[bundle["id"]] = bundle
        return bundle

    for entity in draft.get("entities", []):
        evidence = _evidence_from_item(entity)
        bundle = register_bundle(
            evidence.get("spans", ["derived"]),
            evidence.get("source_refs"),
        )
        has_anchors = bool(bundle.get("anchors"))
        facets = _facet_completeness_for_entity(entity, has_anchors=has_anchors)
        subject_ref = str(entity["proposed_id"])
        payload = {
            "name": entity.get("name"),
            "type": entity.get("type"),
            "stable_identity": list(entity.get("stable_identity", [])),
            "status": entity.get("status", "proposed"),
        }
        assertions.append(
            _assertion(
                kind="entity",
                subject_ref=subject_ref,
                payload=payload,
                bundle=bundle,
                confidence=float(entity.get("confidence", 0.7)),
                facet_completeness=facets,
                status=status,
            )
        )

    for quality in draft.get("qualities", []):
        evidence = _evidence_from_item(quality)
        bundle = register_bundle(evidence.get("spans", ["derived"]), evidence.get("source_refs"))
        facets = {
            "identity": bool(quality.get("quality_id")),
            "configuration": bool(quality.get("labels")),
            "evidence": bool(evidence.get("spans")),
            "substrate": bool(bundle.get("anchors")),
        }
        subject_ref = str(quality["quality_id"])
        payload = {
            "quality_type": quality.get("quality_type"),
            "intensity": quality.get("intensity"),
            "kind": quality.get("kind"),
            "entity_ref": quality.get("entity_ref"),
            "labels": list(quality.get("labels", [])),
        }
        assertions.append(
            _assertion(
                kind="quality",
                subject_ref=subject_ref,
                payload=payload,
                bundle=bundle,
                confidence=float(quality.get("confidence", 0.7)),
                facet_completeness=facets,
                status=status,
            )
        )

    for role in draft.get("quality_roles", []):
        evidence = _evidence_from_item(role)
        bundle = register_bundle(evidence.get("spans", ["derived"]), evidence.get("source_refs"))
        facets = {
            "identity": bool(role.get("quality_ref")),
            "configuration": bool(role.get("role")),
            "evidence": bool(evidence.get("spans")),
            "substrate": bool(bundle.get("anchors")),
        }
        subject_ref = f"{role.get('quality_ref')}::{role.get('role')}"
        payload = {
            "quality_ref": role.get("quality_ref"),
            "entity_ref": role.get("entity_ref"),
            "role": role.get("role"),
        }
        assertions.append(
            _assertion(
                kind="quality_role",
                subject_ref=subject_ref,
                payload=payload,
                bundle=bundle,
                confidence=float(role.get("confidence", 0.7)),
                facet_completeness=facets,
                status=status,
            )
        )

    for relation in draft.get("relations", []):
        evidence = _evidence_from_item(relation)
        bundle = register_bundle(evidence.get("spans", ["derived"]), evidence.get("source_refs"))
        facets = {
            "identity": bool(relation.get("source_ref")) and bool(relation.get("target_ref")),
            "configuration": bool(relation.get("primitive")),
            "evidence": bool(evidence.get("spans")),
            "substrate": bool(bundle.get("anchors")),
        }
        subject_ref = make_id("rel")
        payload = {
            "source_ref": relation.get("source_ref"),
            "target_ref": relation.get("target_ref"),
            "level": relation.get("level"),
            "relation_type": relation.get("relation_type"),
            "primitive": relation.get("primitive"),
            "domain_expression": relation.get("domain_expression"),
            "weight": relation.get("weight"),
        }
        assertions.append(
            _assertion(
                kind="relation",
                subject_ref=subject_ref,
                payload=payload,
                bundle=bundle,
                confidence=float(relation.get("confidence", 0.7)),
                facet_completeness=facets,
                status=status,
            )
        )

    for shape in draft.get("candidate_shapes", []):
        evidence = _evidence_from_item(shape)
        bundle = register_bundle(evidence.get("spans", ["derived"]), evidence.get("source_refs"))
        facets = {
            "identity": bool(shape.get("proposed_id")),
            "configuration": bool(shape.get("relational_configuration")),
            "evidence": bool(evidence.get("spans")),
            "substrate": bool(bundle.get("anchors")),
        }
        subject_ref = str(shape["proposed_id"])
        payload = {
            "possible_names": list(shape.get("possible_names", [])),
            "relational_configuration": shape.get("relational_configuration"),
            "entity_refs": list(shape.get("entity_refs", [])),
        }
        assertions.append(
            _assertion(
                kind="candidate_shape",
                subject_ref=subject_ref,
                payload=payload,
                bundle=bundle,
                confidence=float(shape.get("confidence", 0.7)),
                facet_completeness=facets,
                status=status,
            )
        )

    for stencil in draft.get("stencil_drafts", []):
        evidence = _evidence_from_item(stencil)
        bundle = register_bundle(evidence.get("spans", ["derived"]), evidence.get("source_refs"))
        facets = _facet_completeness_for_stencil(stencil, has_anchors=bool(bundle.get("anchors")))
        subject_ref = str(stencil.get("proposed_name", make_id("stencil-draft")))
        payload = {
            "proposed_name": stencil.get("proposed_name"),
            "role_entities": list(stencil.get("role_entities", [])),
            "relation_topology": list(stencil.get("relation_topology", [])),
            "dynamics_class": stencil.get("dynamics_class"),
            "symmetry_profile": stencil.get("symmetry_profile"),
            "facet_completeness": dict(stencil.get("facet_completeness", {}) or {}),
        }
        assertions.append(
            _assertion(
                kind="stencil_draft",
                subject_ref=subject_ref,
                payload=payload,
                bundle=bundle,
                confidence=float(stencil.get("confidence", 0.7)),
                facet_completeness=facets,
                status=status,
            )
        )

    return {
        "version": STORE_VERSION,
        "session_id": session_id,
        "draft_id": str(draft.get("draft_id", "")),
        "subgraph_id": str(draft.get("subgraph_id", f"session-{session_id}")),
        "substrate_ref": substrate_ref,
        "raw_content_ref": raw_content_ref,
        "materialized_at": utc_now(),
        "evidence_bundles": bundles,
        "assertions": assertions,
    }


def _node_summary(assertion: Dict[str, Any]) -> Dict[str, Any]:
    payload = dict(assertion.get("payload", {}))
    kind = assertion["kind"]
    if kind == "entity":
        return {
            "name": payload.get("name"),
            "type": payload.get("type"),
            "stable_identity": payload.get("stable_identity", []),
        }
    if kind == "relation":
        return {
            "source_ref": payload.get("source_ref"),
            "target_ref": payload.get("target_ref"),
            "primitive": payload.get("primitive"),
            "relation_type": payload.get("relation_type"),
            "level": payload.get("level"),
        }
    if kind == "quality":
        return {
            "quality_type": payload.get("quality_type"),
            "labels": payload.get("labels", []),
            "entity_ref": payload.get("entity_ref"),
        }
    if kind == "candidate_shape":
        return {
            "possible_names": payload.get("possible_names", []),
            "entity_refs": payload.get("entity_refs", []),
        }
    if kind == "stencil_draft":
        return {
            "proposed_name": payload.get("proposed_name"),
            "dynamics_class": payload.get("dynamics_class"),
            "symmetry_profile": payload.get("symmetry_profile"),
        }
    return payload


def _semantic_neighbors(assertion: Dict[str, Any]) -> List[str]:
    kind = assertion["kind"]
    payload = assertion.get("payload", {})
    if kind == "relation":
        neighbors = [str(payload.get("source_ref", "")), str(payload.get("target_ref", ""))]
        return [item for item in neighbors if item]
    if kind == "quality":
        entity_ref = payload.get("entity_ref")
        return [str(entity_ref)] if entity_ref else []
    if kind == "quality_role":
        refs = [payload.get("quality_ref"), payload.get("entity_ref")]
        return [str(item) for item in refs if item]
    if kind == "candidate_shape":
        return [str(item) for item in payload.get("entity_refs", []) if item]
    return []


def project_content_graph(
    assertion_store: Dict[str, Any],
    *,
    shape_instances: Optional[Sequence[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    nodes: Dict[str, Dict[str, Any]] = {}
    semantic: Dict[str, Set[str]] = {}
    provenance: Dict[str, Set[str]] = {}
    structural: Dict[str, Set[str]] = {}

    for assertion in assertion_store.get("assertions", []):
        node_id = str(assertion["subject_ref"])
        bundle_id = str(assertion["evidence_bundle_id"])
        nodes[node_id] = {
            "id": node_id,
            "kind": assertion["kind"],
            "name": assertion.get("payload", {}).get("name")
            or assertion.get("payload", {}).get("proposed_name")
            or node_id,
            "detail_level": assertion.get("detail_level", "identity"),
            "assertion_id": assertion["id"],
            "evidence_bundle_id": bundle_id,
            "facet_completeness": dict(assertion.get("facet_completeness", {})),
            "summary": _node_summary(assertion),
        }
        provenance.setdefault(node_id, set()).update({assertion["id"], bundle_id})
        for neighbor in _semantic_neighbors(assertion):
            semantic.setdefault(node_id, set()).add(neighbor)
            semantic.setdefault(neighbor, set()).add(node_id)
        if assertion["kind"] == "relation":
            payload = assertion.get("payload", {})
            source_ref = str(payload.get("source_ref", ""))
            target_ref = str(payload.get("target_ref", ""))
            if source_ref and target_ref:
                semantic.setdefault(source_ref, set()).add(target_ref)
                semantic.setdefault(target_ref, set()).add(source_ref)

    for instance in shape_instances or []:
        entity_id = str(instance.get("entity_id", ""))
        if not entity_id:
            continue
        ref = str(instance.get("id") or instance.get("stencil_id", ""))
        if ref:
            structural.setdefault(entity_id, set()).add(ref)

    def _sorted_adjacency(adj: Dict[str, Set[str]]) -> Dict[str, List[str]]:
        return {key: sorted(values) for key, values in sorted(adj.items())}

    return {
        "version": GRAPH_VERSION,
        "session_id": assertion_store.get("session_id"),
        "subgraph_id": assertion_store.get("subgraph_id"),
        "draft_id": assertion_store.get("draft_id"),
        "assertion_store_ref": "assertion_store.json",
        "materialized_at": utc_now(),
        "nodes": nodes,
        "adjacency": {
            "semantic": _sorted_adjacency(semantic),
            "provenance": _sorted_adjacency(provenance),
            "structural": _sorted_adjacency(structural),
        },
    }


def materialize_session_graph(
    root,
    session_id: str,
    draft: Dict[str, Any],
    *,
    events: Optional[Sequence[Dict[str, Any]]] = None,
    shape_instances: Optional[Sequence[Dict[str, Any]]] = None,
    status: Optional[str] = None,
) -> Dict[str, Any]:
    draft_status = status or str(draft.get("status", "proposed"))
    if draft.get("quarantine", {}).get("quarantine"):
        draft_status = "quarantined"
    elif draft_status == "validated":
        draft_status = "validated"

    store = build_assertion_store_from_draft(
        root,
        session_id,
        draft,
        events=events,
        status=draft_status,
    )
    graph = project_content_graph(store, shape_instances=shape_instances)

    artifact_dir = session_dir(root, session_id) / "mtsf"
    ensure_dir(artifact_dir)
    store_path = artifact_dir / "assertion_store.json"
    graph_path = artifact_dir / "content_graph.json"
    write_json(store_path, store)
    write_json(graph_path, graph)

    return {
        "session_id": session_id,
        "assertion_count": len(store.get("assertions", [])),
        "evidence_bundle_count": len(store.get("evidence_bundles", {})),
        "node_count": len(graph.get("nodes", {})),
        "artifact_refs": {
            "mtsf_assertion_store": str(store_path),
            "mtsf_content_graph": str(graph_path),
        },
    }


def load_assertion_store(root, session_id: str) -> Dict[str, Any]:
    path = assertion_store_path(root, session_id)
    return read_json(path, default={})


def load_content_graph(root, session_id: str) -> Dict[str, Any]:
    path = content_graph_path(root, session_id)
    return read_json(path, default={})


def _assertion_by_subject(store: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {str(row["subject_ref"]): row for row in store.get("assertions", [])}


def _assertion_by_id(store: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {str(row["id"]): row for row in store.get("assertions", [])}


def activation_snapshot_path(root: Path, session_id: str) -> Path:
    return session_dir(root, session_id) / "mtsf" / "activation_snapshot.json"


def _normalize_entity_name(value: str) -> str:
    return " ".join(str(value).lower().split())


def _catalog_entities_by_id(root: Path) -> Dict[str, Dict[str, Any]]:
    from .mtsf_session import default_entity_catalog_path

    payload = read_json(default_entity_catalog_path(root), default={})
    return {str(row["id"]): row for row in payload.get("entities", [])}


def derive_activation_summary(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    dominant_catalog_entities: List[str] = []
    entity_shapes: Dict[str, str] = {}
    for row in snapshot.get("shape_activation_results", []):
        entity_id = str(row.get("entity_id", ""))
        if not entity_id:
            continue
        confidence = float(row.get("confidence", 0.0))
        if confidence < ACTIVATION_CONFIDENCE_THRESHOLD:
            continue
        dominant_catalog_entities.append(entity_id)
        dominant_shape = row.get("dominant_shape_id")
        if dominant_shape:
            entity_shapes[entity_id] = str(dominant_shape)

    return {
        "dominant_catalog_entities": sorted(set(dominant_catalog_entities)),
        "entity_shapes": entity_shapes,
        "active_stencil_ids": list(snapshot.get("active_stencil_ids", [])),
    }


def resolve_activation_bindings(root: Path, session_id: str) -> Dict[str, Any]:
    snapshot_path = activation_snapshot_path(root, session_id)
    graph = load_content_graph(root, session_id)
    if not snapshot_path.exists():
        return {
            "session_id": session_id,
            "bindings": {},
            "unbound_catalog_entities": [],
            "ambiguous": [],
            "reason": "missing_activation_snapshot",
        }
    if not graph:
        return {
            "session_id": session_id,
            "bindings": {},
            "unbound_catalog_entities": [],
            "ambiguous": [],
            "reason": "missing_content_graph",
        }

    snapshot = read_json(snapshot_path, default={})
    catalog = _catalog_entities_by_id(root)
    summary = derive_activation_summary(snapshot)
    fired_catalog_ids = summary["dominant_catalog_entities"]

    entity_nodes: Dict[str, Dict[str, Any]] = {}
    name_to_nodes: Dict[str, List[str]] = {}
    for node_id, node in graph.get("nodes", {}).items():
        if str(node.get("kind", "")) != "entity":
            continue
        entity_nodes[str(node_id)] = node
        normalized_name = _normalize_entity_name(str(node.get("name", "")))
        if normalized_name:
            name_to_nodes.setdefault(normalized_name, []).append(str(node_id))

    draft_path = session_dir(root, session_id) / "mtsf" / "extraction_draft.json"
    hint_refs: Set[str] = set()
    if draft_path.exists():
        draft = read_json(draft_path, default={})
        hint_refs = {
            str(ref)
            for ref in draft.get("activation_snapshot_hint", {}).get("dominant_entity_refs", [])
            if ref
        }

    results_by_entity = {
        str(row.get("entity_id", "")): row for row in snapshot.get("shape_activation_results", [])
    }
    bindings: Dict[str, Dict[str, Any]] = {}
    unbound_catalog_entities: List[str] = []
    ambiguous: List[Dict[str, Any]] = []

    for catalog_id in fired_catalog_ids:
        result = results_by_entity.get(catalog_id, {})
        catalog_row = catalog.get(catalog_id, {})
        content_node_id: Optional[str] = None
        match_method: Optional[str] = None

        if catalog_id in entity_nodes:
            content_node_id = catalog_id
            match_method = "exact_id"
        else:
            catalog_name = _normalize_entity_name(str(catalog_row.get("name", "")))
            for hint_ref in hint_refs:
                if hint_ref not in entity_nodes:
                    continue
                hint_name = _normalize_entity_name(str(entity_nodes[hint_ref].get("name", "")))
                if hint_ref == catalog_id or (catalog_name and hint_name == catalog_name):
                    content_node_id = hint_ref
                    match_method = "extraction_hint"
                    break
            if not content_node_id:
                candidates = name_to_nodes.get(catalog_name, [])
                if len(candidates) == 1:
                    content_node_id = candidates[0]
                    match_method = "name_match"
                elif len(candidates) > 1:
                    ambiguous.append(
                        {
                            "catalog_entity_id": catalog_id,
                            "normalized_name": catalog_name,
                            "candidate_content_node_ids": candidates,
                        }
                    )

        if content_node_id:
            bindings[catalog_id] = {
                "catalog_entity_id": catalog_id,
                "content_node_id": content_node_id,
                "match_method": match_method,
                "confidence": float(result.get("confidence", 0.0)),
                "dominant_shape_id": result.get("dominant_shape_id"),
                "secondary_shape_ids": list(result.get("secondary_shape_ids", [])),
            }
        else:
            unbound_catalog_entities.append(catalog_id)

    return {
        "session_id": session_id,
        "bindings": bindings,
        "unbound_catalog_entities": unbound_catalog_entities,
        "ambiguous": ambiguous,
        "dominant_catalog_entities": fired_catalog_ids,
        "active_stencil_ids": summary["active_stencil_ids"],
    }


def _build_activation_adjacency(
    bindings: Dict[str, Dict[str, Any]],
    graph: Dict[str, Any],
) -> Dict[str, List[str]]:
    active_content_nodes = sorted(
        {str(binding["content_node_id"]) for binding in bindings.values() if binding.get("content_node_id")}
    )
    structural = graph.get("adjacency", {}).get("structural", {})
    activation_adj: Dict[str, Set[str]] = {}

    for binding in bindings.values():
        node_id = str(binding.get("content_node_id", ""))
        if not node_id:
            continue
        neighbors: Set[str] = set()
        for other_id in active_content_nodes:
            if other_id != node_id:
                neighbors.add(other_id)
        for shape_ref in structural.get(node_id, []):
            neighbors.add(str(shape_ref))
        activation_adj[node_id] = neighbors

    return {node_id: sorted(neighbors) for node_id, neighbors in sorted(activation_adj.items())}


def sync_activation_to_content_graph(root: Path, session_id: str) -> Dict[str, Any]:
    resolution = resolve_activation_bindings(root, session_id)
    if resolution.get("reason"):
        return {
            "session_id": session_id,
            "synced": False,
            "reason": resolution["reason"],
            "artifact_refs": {},
        }

    graph_path = content_graph_path(root, session_id)
    graph = read_json(graph_path, default={})
    snapshot_path = activation_snapshot_path(root, session_id)
    snapshot = read_json(snapshot_path, default={})
    bindings = resolution["bindings"]

    activation_adj = _build_activation_adjacency(bindings, graph)
    graph.setdefault("adjacency", {})["activation"] = activation_adj
    dominant_content_nodes = sorted(
        {str(binding["content_node_id"]) for binding in bindings.values() if binding.get("content_node_id")}
    )
    graph["overlays"] = {
        **dict(graph.get("overlays", {})),
        "activation": {
            "snapshot_ref": "activation_snapshot.json",
            "synced_at": utc_now(),
            "bindings": bindings,
            "dominant_catalog_entities": resolution["dominant_catalog_entities"],
            "dominant_content_nodes": dominant_content_nodes,
            "active_stencil_ids": resolution.get("active_stencil_ids", []),
            "unbound_catalog_entities": resolution.get("unbound_catalog_entities", []),
            "ambiguous": resolution.get("ambiguous", []),
        },
    }
    write_json(graph_path, graph)

    snapshot["dominant_entities"] = resolution["dominant_catalog_entities"]
    snapshot["dominant_content_nodes"] = dominant_content_nodes
    snapshot["content_graph_bindings"] = {
        catalog_id: binding["content_node_id"] for catalog_id, binding in bindings.items()
    }
    snapshot["activation_synced_at"] = utc_now()
    write_json(snapshot_path, snapshot)

    event = append_graph_event(
        root,
        {
            "kind": "activation_synced",
            "session_id": session_id,
            "bound_count": len(bindings),
            "unbound_count": len(resolution.get("unbound_catalog_entities", [])),
            "dominant_content_nodes": dominant_content_nodes,
        },
    )

    return {
        "session_id": session_id,
        "synced": True,
        "bound_count": len(bindings),
        "unbound_catalog_entities": resolution.get("unbound_catalog_entities", []),
        "ambiguous": resolution.get("ambiguous", []),
        "dominant_content_nodes": dominant_content_nodes,
        "artifact_refs": {
            "mtsf_content_graph": str(graph_path),
            "mtsf_activation_snapshot": str(snapshot_path),
        },
        "event_id": event["event_id"],
    }


def get_active_content_nodes(root: Path, session_id: str) -> List[str]:
    graph = load_content_graph(root, session_id)
    overlay = graph.get("overlays", {}).get("activation", {})
    if overlay.get("dominant_content_nodes"):
        return list(overlay["dominant_content_nodes"])
    snapshot = read_json(activation_snapshot_path(root, session_id), default={})
    if snapshot.get("dominant_content_nodes"):
        return list(snapshot["dominant_content_nodes"])
    return []


def resolve_global_node_id(session_id: Optional[str], node_id: str) -> str:
    if "::" in node_id:
        return node_id
    if not session_id:
        raise ValueError("session_id is required when node_id is not a global id (session::node)")
    return _global_node_id(session_id, node_id)


def _parse_global_node_id(global_node_id: str) -> Tuple[str, str]:
    if "::" not in global_node_id:
        raise ValueError(f"not a global node id: {global_node_id}")
    session_id, local_node_id = global_node_id.split("::", 1)
    if not session_id or not local_node_id:
        raise ValueError(f"not a global node id: {global_node_id}")
    return session_id, local_node_id


def refresh_global_alias_adjacency(graph: Dict[str, Any]) -> Dict[str, Any]:
    nodes = graph.get("nodes", {})
    by_name: Dict[str, List[str]] = {}
    for node_id, node in nodes.items():
        if str(node.get("kind", "")) != "entity":
            continue
        name = _normalize_entity_name(str(node.get("name", "")))
        if not name:
            continue
        by_name.setdefault(name, []).append(str(node_id))

    alias_adj: Dict[str, Set[str]] = {}
    for node_ids in by_name.values():
        if len(node_ids) < 2:
            continue
        sessions = {str(nodes[nid].get("source_session_id", "")) for nid in node_ids}
        if len(sessions) < 2:
            continue
        for node_id in node_ids:
            alias_adj.setdefault(node_id, set()).update(
                other for other in node_ids if other != node_id
            )

    graph.setdefault("adjacency", {})["alias"] = {
        node_id: sorted(neighbors) for node_id, neighbors in sorted(alias_adj.items())
    }
    return graph


def _graph_nodes_only(graph: Dict[str, Any], neighbor_ids: Sequence[str]) -> List[str]:
    nodes = graph.get("nodes", {})
    return [str(neighbor) for neighbor in neighbor_ids if str(neighbor) in nodes]


def follow_traversal(
    root,
    session_id: Optional[str] = None,
    *,
    start: str,
    mode: TraversalMode = "semantic",
    depth: int = 1,
    scope: GraphScope = "session",
) -> Dict[str, Any]:
    if scope == "global":
        graph = load_global_content_graph(root)
        if not graph.get("nodes"):
            raise FileNotFoundError("global content graph not found or empty")
        start_id = resolve_global_node_id(session_id, start)
    else:
        if not session_id:
            raise ValueError("session_id is required when scope=session")
        graph = load_content_graph(root, session_id)
        if not graph:
            raise FileNotFoundError(f"content graph not found for session {session_id}")
        start_id = start

    nodes = graph.get("nodes", {})
    if start_id not in nodes:
        raise KeyError(f"unknown node: {start_id}")

    visited: Set[str] = set()
    frontier: Set[str] = {start_id}
    edges: List[Dict[str, Any]] = []
    path_nodes: Dict[str, Dict[str, Any]] = {}

    max_distance = max(depth, 0)
    for _distance in range(max_distance + 1):
        next_frontier: Set[str] = set()
        for node_id in sorted(frontier):
            if node_id in visited:
                continue
            visited.add(node_id)
            path_nodes[node_id] = nodes[node_id]
            neighbors = _neighbors_for_mode(
                root,
                session_id,
                graph,
                node_id,
                mode,
                scope=scope,
            )
            for neighbor in neighbors:
                edges.append({"from": node_id, "to": neighbor, "mode": mode})
                if neighbor not in visited:
                    next_frontier.add(neighbor)
        frontier = next_frontier

    return {
        "scope": scope,
        "session_id": session_id,
        "mode": mode,
        "start": start_id,
        "depth": depth,
        "nodes": path_nodes,
        "edges": edges,
        "visited": sorted(visited),
    }


def _neighbors_for_mode(
    root,
    session_id: Optional[str],
    graph: Dict[str, Any],
    node_id: str,
    mode: TraversalMode,
    *,
    scope: GraphScope = "session",
) -> List[str]:
    adjacency = graph.get("adjacency", {})
    if scope == "global":
        if mode == "alias":
            return _graph_nodes_only(graph, adjacency.get("alias", {}).get(node_id, []))
        if mode == "semantic":
            return _graph_nodes_only(graph, adjacency.get("semantic", {}).get(node_id, []))
        if mode == "structural":
            return _graph_nodes_only(graph, adjacency.get("structural", {}).get(node_id, []))
        if mode == "activation":
            return _graph_nodes_only(graph, adjacency.get("activation", {}).get(node_id, []))
        if mode == "provenance":
            return _graph_nodes_only(graph, adjacency.get("provenance", {}).get(node_id, []))
        if mode == "temporal":
            return []

    if mode == "semantic":
        return list(adjacency.get("semantic", {}).get(node_id, []))
    if mode == "provenance":
        if not session_id:
            ref = graph.get("assertion_refs", {}).get(node_id, {})
            session_id = str(ref.get("session_id", ""))
        refs = adjacency.get("provenance", {}).get(node_id, [])
        store = load_assertion_store(root, session_id) if session_id else {}
        expanded: List[str] = []
        bundles = store.get("evidence_bundles", {})
        assertions = _assertion_by_id(store)
        for ref in refs:
            if ref in bundles:
                expanded.append(ref)
            elif ref in assertions:
                expanded.append(ref)
        return expanded
    if mode == "structural":
        return list(adjacency.get("structural", {}).get(node_id, []))
    if mode == "activation":
        return list(adjacency.get("activation", {}).get(node_id, []))
    if mode == "alias":
        return list(adjacency.get("alias", {}).get(node_id, []))
    if mode == "temporal":
        if not session_id:
            return []
        active_nodes = get_active_content_nodes(root, session_id)
        if active_nodes:
            return [item for item in active_nodes if item != node_id]
        snapshot = read_json(activation_snapshot_path(root, session_id), default={})
        refs: List[str] = []
        for entity_id in snapshot.get("dominant_content_nodes", []) or snapshot.get("dominant_entities", []):
            refs.append(str(entity_id))
        for shape_id in snapshot.get("active_stencil_ids", []):
            refs.append(str(shape_id))
        return [item for item in refs if item != node_id]
    return []


def _expand_node_from_store(
    root: Path,
    session_id: str,
    local_node_id: str,
    node: Dict[str, Any],
    *,
    facets: Optional[Sequence[ExpandFacet]] = None,
    scope: GraphScope = "session",
    global_node_id: Optional[str] = None,
) -> Dict[str, Any]:
    store = load_assertion_store(root, session_id)
    if not store:
        raise FileNotFoundError(f"assertion store not found for session {session_id}")

    selected = set(facets or ["identity"])
    if "all" in selected:
        selected = {"identity", "configuration", "evidence", "substrate", "payload"}

    assertion = _assertion_by_subject(store).get(local_node_id) or _assertion_by_id(store).get(
        str(node.get("assertion_id", ""))
    )
    if not assertion:
        raise KeyError(f"assertion not found for node: {local_node_id}")

    bundle = store.get("evidence_bundles", {}).get(str(assertion["evidence_bundle_id"]), {})
    result: Dict[str, Any] = {
        "scope": scope,
        "session_id": session_id,
        "node_id": global_node_id or local_node_id,
        "local_node_id": local_node_id,
        "kind": node.get("kind"),
        "detail_level": node.get("detail_level"),
        "facet_completeness": node.get("facet_completeness", {}),
    }
    if global_node_id:
        result["global_node_id"] = global_node_id
        result["source_session_id"] = session_id

    if "identity" in selected:
        result["identity"] = _node_summary(assertion)
    if "configuration" in selected or "payload" in selected:
        result["payload"] = dict(assertion.get("payload", {}))
    if "evidence" in selected:
        result["evidence"] = {
            "bundle_id": bundle.get("id"),
            "spans": list(bundle.get("spans", [])),
            "source_refs": list(bundle.get("source_refs", [])),
        }
    if "substrate" in selected:
        anchors = list(bundle.get("anchors", []))
        events = read_jsonl(session_events_path(root, session_id))
        event_by_id = {str(event.get("event_id")): event for event in events}
        substrate_hits: List[Dict[str, Any]] = []
        for anchor in anchors:
            event = event_by_id.get(str(anchor.get("event_id", "")))
            substrate_hits.append(
                {
                    **anchor,
                    "event_actor": event.get("actor") if event else None,
                    "event_kind": event.get("kind") if event else None,
                }
            )
        result["substrate"] = {
            "substrate_ref": store.get("substrate_ref"),
            "raw_content_ref": store.get("raw_content_ref"),
            "anchors": substrate_hits,
        }

    return result


def expand_node(
    root,
    session_id: Optional[str] = None,
    node_id: str = "",
    *,
    facets: Optional[Sequence[ExpandFacet]] = None,
    scope: GraphScope = "session",
) -> Dict[str, Any]:
    if scope == "global":
        graph = load_global_content_graph(root)
        if not graph.get("nodes"):
            raise FileNotFoundError("global content graph not found or empty")
        global_id = resolve_global_node_id(session_id, node_id)
        node = graph.get("nodes", {}).get(global_id)
        if not node:
            raise KeyError(f"unknown global node: {global_id}")
        ref = graph.get("assertion_refs", {}).get(global_id, {})
        local_session = str(ref.get("session_id", node.get("source_session_id", "")))
        local_node = str(ref.get("local_node_id", node.get("local_id", "")))
        if not local_session or not local_node:
            raise KeyError(f"assertion ref not found for global node: {global_id}")
        return _expand_node_from_store(
            root,
            local_session,
            local_node,
            node,
            facets=facets,
            scope="global",
            global_node_id=global_id,
        )

    if not session_id:
        raise ValueError("session_id is required when scope=session")
    graph = load_content_graph(root, session_id)
    if not graph:
        raise FileNotFoundError(f"graph artifacts not found for session {session_id}")
    node = graph.get("nodes", {}).get(node_id)
    if not node:
        raise KeyError(f"unknown node: {node_id}")
    return _expand_node_from_store(
        root,
        session_id,
        node_id,
        node,
        facets=facets,
        scope="session",
    )


def default_graph_events_path(root: Path) -> Path:
    return root / "memory" / "mtsf" / "graph_events.jsonl"


def default_global_content_graph_path(root: Path) -> Path:
    return root / "memory" / "mtsf" / "global_content_graph.json"


def substrate_ref_fields(
    root: Path,
    session_id: str,
    events: Sequence[Dict[str, Any]],
    *,
    preview_limit: int = SUBSTRATE_PREVIEW_LIMIT,
) -> Dict[str, Any]:
    substrate = build_substrate_index(events)
    return {
        "raw_content_ref": str(session_events_path(root, session_id)),
        "substrate_offsets": [
            {"event_id": event_id, "char_start": char_start, "char_end": char_end}
            for event_id, char_start, char_end in substrate.event_spans
        ],
        "raw_content_preview": substrate.text[:preview_limit],
    }


def apply_substrate_refs_to_draft(
    root: Path,
    session_id: str,
    events: Sequence[Dict[str, Any]],
    draft: Dict[str, Any],
    *,
    preview_limit: int = SUBSTRATE_PREVIEW_LIMIT,
) -> Dict[str, Any]:
    refs = substrate_ref_fields(root, session_id, events, preview_limit=preview_limit)
    draft.update(refs)
    if refs.get("raw_content_ref"):
        preview = str(refs.get("raw_content_preview", ""))
        if preview:
            draft["raw_content"] = preview
        elif draft.get("raw_content"):
            draft["raw_content"] = str(draft["raw_content"])[:preview_limit]
    return draft


def empty_global_content_graph() -> Dict[str, Any]:
    return {
        "version": GLOBAL_GRAPH_VERSION,
        "scope": "global",
        "nodes": {},
        "adjacency": {"semantic": {}, "provenance": {}, "structural": {}, "activation": {}, "alias": {}},
        "assertion_refs": {},
        "sessions_contributed": {},
    }


def load_global_content_graph(root: Path) -> Dict[str, Any]:
    path = default_global_content_graph_path(root)
    if not path.exists():
        return empty_global_content_graph()
    payload = read_json(path, default={})
    if not payload:
        return empty_global_content_graph()
    payload.setdefault("version", GLOBAL_GRAPH_VERSION)
    payload.setdefault("scope", "global")
    payload.setdefault("nodes", {})
    payload.setdefault("adjacency", {"semantic": {}, "provenance": {}, "structural": {}, "activation": {}, "alias": {}})
    payload.setdefault("assertion_refs", {})
    payload.setdefault("sessions_contributed", {})
    return payload


def append_graph_event(root: Path, event: Dict[str, Any]) -> Dict[str, Any]:
    payload = dict(event)
    payload.setdefault("event_id", make_id("mtsf-graph-ev"))
    payload.setdefault("timestamp", utc_now())
    events_path = default_graph_events_path(root)
    ensure_dir(events_path.parent)
    append_jsonl(events_path, payload)
    return payload


def read_graph_events(
    root: Path,
    *,
    limit: int = 50,
    kinds: Optional[Sequence[str]] = None,
) -> List[Dict[str, Any]]:
    events_path = default_graph_events_path(root)
    if not events_path.exists():
        return []
    events = read_jsonl(events_path)
    if kinds:
        allowed = {str(kind) for kind in kinds}
        events = [row for row in events if str(row.get("kind", "")) in allowed]
    if limit <= 0:
        return events
    return events[-limit:]


def _global_node_id(session_id: str, local_node_id: str) -> str:
    return f"{session_id}::{local_node_id}"


def merge_session_graph_into_global(
    global_graph: Dict[str, Any],
    session_graph: Dict[str, Any],
    store: Dict[str, Any],
    *,
    session_id: str,
    promotion_mode: str = "auto",
) -> Dict[str, Any]:
    merged = dict(global_graph)
    merged.setdefault("nodes", {})
    merged.setdefault("adjacency", {"semantic": {}, "provenance": {}, "structural": {}, "activation": {}, "alias": {}})
    merged.setdefault("assertion_refs", {})
    merged.setdefault("sessions_contributed", {})

    id_map: Dict[str, str] = {}
    local_nodes = session_graph.get("nodes", {})
    for local_id, node in local_nodes.items():
        global_id = _global_node_id(session_id, str(local_id))
        id_map[str(local_id)] = global_id
        promoted_node = dict(node)
        promoted_node["id"] = global_id
        promoted_node["source_session_id"] = session_id
        promoted_node["local_id"] = str(local_id)
        merged["nodes"][global_id] = promoted_node
        merged["assertion_refs"][global_id] = {
            "session_id": session_id,
            "local_node_id": str(local_id),
            "assertion_id": str(node.get("assertion_id", "")),
            "subject_ref": str(local_id),
            "evidence_bundle_id": str(node.get("evidence_bundle_id", "")),
        }

    for adjacency_kind in ("semantic", "provenance", "structural", "activation"):
        session_adj = session_graph.get("adjacency", {}).get(adjacency_kind, {})
        global_adj = merged["adjacency"].setdefault(adjacency_kind, {})
        for local_id, neighbors in session_adj.items():
            global_id = id_map.get(str(local_id), _global_node_id(session_id, str(local_id)))
            remapped_neighbors = [
                id_map.get(str(neighbor), _global_node_id(session_id, str(neighbor)))
                for neighbor in neighbors
            ]
            existing = set(global_adj.get(global_id, []))
            existing.update(remapped_neighbors)
            global_adj[global_id] = sorted(existing)

    subgraph_id = str(
        session_graph.get("subgraph_id", store.get("subgraph_id", f"session-{session_id}"))
    )
    draft_id = str(session_graph.get("draft_id", store.get("draft_id", "")))
    merged["sessions_contributed"][session_id] = {
        "promoted_at": utc_now(),
        "draft_id": draft_id,
        "subgraph_id": subgraph_id,
        "promotion_mode": promotion_mode,
        "node_count": len(local_nodes),
    }
    merged["updated_at"] = utc_now()
    merged["version"] = GLOBAL_GRAPH_VERSION
    merged["scope"] = "global"
    return refresh_global_alias_adjacency(merged)


def _session_graph_promotion_ready(root: Path, session_id: str) -> tuple[bool, str]:
    from .mtsf_index import PROMOTION_CONFIDENCE_THRESHOLD

    draft_path = session_dir(root, session_id) / "mtsf" / "extraction_draft.json"
    if draft_path.exists():
        draft = read_json(draft_path, default={})
        quarantine = draft.get("quarantine", {})
        if quarantine.get("quarantine"):
            return False, "validation_quarantine"
        if quarantine.get("promotion_ready"):
            return True, "promotion_ready"
        confidence = float(draft.get("confidence", 0.0))
        if confidence >= PROMOTION_CONFIDENCE_THRESHOLD:
            return True, "confidence_threshold"
        return False, "confidence_below_threshold"

    if content_graph_path(root, session_id).exists():
        return True, "content_graph_present"
    return False, "missing_content_graph"


def promote_session_graph_to_global(
    root: Path,
    session_id: str,
    *,
    mode: str = "auto",
) -> Dict[str, Any]:
    graph_path = content_graph_path(root, session_id)
    store_path = assertion_store_path(root, session_id)
    if not graph_path.exists() or not store_path.exists():
        return {
            "session_id": session_id,
            "promoted": False,
            "reason": "missing_session_graph",
            "artifact_refs": {},
        }

    if mode == "auto":
        ready, reason = _session_graph_promotion_ready(root, session_id)
        if not ready:
            return {
                "session_id": session_id,
                "promoted": False,
                "reason": reason,
                "artifact_refs": {},
            }

    session_graph = read_json(graph_path, default={})
    store = read_json(store_path, default={})
    global_path = default_global_content_graph_path(root)
    global_graph = load_global_content_graph(root)
    promotion_mode = "explicit" if mode == "force" else mode
    merged = merge_session_graph_into_global(
        global_graph,
        session_graph,
        store,
        session_id=session_id,
        promotion_mode=promotion_mode,
    )
    ensure_dir(global_path.parent)
    write_json(global_path, merged)

    event = append_graph_event(
        root,
        {
            "kind": "session_promoted",
            "session_id": session_id,
            "draft_id": session_graph.get("draft_id", ""),
            "subgraph_id": session_graph.get("subgraph_id", ""),
            "promotion_mode": promotion_mode,
            "node_count": len(session_graph.get("nodes", {})),
        },
    )

    return {
        "session_id": session_id,
        "promoted": True,
        "promotion_mode": promotion_mode,
        "node_count": len(session_graph.get("nodes", {})),
        "artifact_refs": {"mtsf_global_content_graph": str(global_path)},
        "event_id": event["event_id"],
    }


def rebuild_global_content_graph(
    root: Path,
    *,
    session_ids: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    global_graph = empty_global_content_graph()
    sessions_dir = root / "memory" / "sessions"
    if session_ids is not None:
        candidates = [sessions_dir / session_id for session_id in session_ids]
    else:
        candidates = sorted(sessions_dir.glob("*/")) if sessions_dir.exists() else []

    scanned: List[str] = []
    merged_sessions = 0
    for candidate in candidates:
        session_id = candidate.name if candidate.is_dir() else str(candidate)
        graph_path = content_graph_path(root, session_id)
        store_path = assertion_store_path(root, session_id)
        if not graph_path.exists() or not store_path.exists():
            continue
        session_graph = read_json(graph_path, default={})
        if not session_graph.get("nodes"):
            continue
        store = read_json(store_path, default={})
        global_graph = merge_session_graph_into_global(
            global_graph,
            session_graph,
            store,
            session_id=session_id,
            promotion_mode="rebuild",
        )
        scanned.append(session_id)
        merged_sessions += 1

    global_path = default_global_content_graph_path(root)
    ensure_dir(global_path.parent)
    write_json(global_path, global_graph)

    event = append_graph_event(
        root,
        {
            "kind": "global_rebuilt",
            "session_ids": scanned,
            "merged_session_count": merged_sessions,
            "node_count": len(global_graph.get("nodes", {})),
        },
    )

    return {
        "rebuilt": True,
        "merged_session_count": merged_sessions,
        "session_ids": scanned,
        "node_count": len(global_graph.get("nodes", {})),
        "artifact_refs": {"mtsf_global_content_graph": str(global_path)},
        "event_id": event["event_id"],
    }
