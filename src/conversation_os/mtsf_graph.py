from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional, Sequence, Set, Tuple

from .storage import ensure_dir, make_id, read_json, read_jsonl, session_dir, session_events_path, utc_now, write_json

MODULE_ID = "kernel.mtsf.graph"
CONTRACT_VERSION = "1.0.0"
STORE_VERSION = "1.0.0"
GRAPH_VERSION = "1.0.0"

TraversalMode = Literal["semantic", "structural", "provenance", "temporal"]
DetailFacet = Literal["identity", "configuration", "evidence", "substrate", "payload"]
ExpandFacet = Literal["identity", "configuration", "evidence", "substrate", "payload", "all"]

PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "STORE_VERSION",
    "GRAPH_VERSION",
    "SubstrateIndex",
    "assertion_store_path",
    "content_graph_path",
    "build_substrate_index",
    "build_evidence_bundle",
    "build_assertion_store_from_draft",
    "project_content_graph",
    "materialize_session_graph",
    "load_assertion_store",
    "load_content_graph",
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


def follow_traversal(
    root,
    session_id: str,
    *,
    start: str,
    mode: TraversalMode = "semantic",
    depth: int = 1,
) -> Dict[str, Any]:
    graph = load_content_graph(root, session_id)
    if not graph:
        raise FileNotFoundError(f"content graph not found for session {session_id}")

    nodes = graph.get("nodes", {})
    if start not in nodes:
        raise KeyError(f"unknown node: {start}")

    visited: Set[str] = set()
    frontier: Set[str] = {start}
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
            neighbors = _neighbors_for_mode(root, session_id, graph, node_id, mode)
            for neighbor in neighbors:
                edges.append({"from": node_id, "to": neighbor, "mode": mode})
                if neighbor not in visited:
                    next_frontier.add(neighbor)
        frontier = next_frontier

    return {
        "session_id": session_id,
        "mode": mode,
        "start": start,
        "depth": depth,
        "nodes": path_nodes,
        "edges": edges,
        "visited": sorted(visited),
    }


def _neighbors_for_mode(
    root,
    session_id: str,
    graph: Dict[str, Any],
    node_id: str,
    mode: TraversalMode,
) -> List[str]:
    adjacency = graph.get("adjacency", {})
    if mode == "semantic":
        return list(adjacency.get("semantic", {}).get(node_id, []))
    if mode == "provenance":
        refs = adjacency.get("provenance", {}).get(node_id, [])
        store = load_assertion_store(root, session_id)
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
    if mode == "temporal":
        snapshot_path = session_dir(root, session_id) / "mtsf" / "activation_snapshot.json"
        if not snapshot_path.exists():
            return []
        snapshot = read_json(snapshot_path, default={})
        refs: List[str] = []
        for entity_id in snapshot.get("dominant_entities", []):
            refs.append(str(entity_id))
        for shape_id in snapshot.get("active_stencil_ids", []):
            refs.append(str(shape_id))
        return [item for item in refs if item != node_id]
    return []


def expand_node(
    root,
    session_id: str,
    node_id: str,
    *,
    facets: Optional[Sequence[ExpandFacet]] = None,
) -> Dict[str, Any]:
    store = load_assertion_store(root, session_id)
    graph = load_content_graph(root, session_id)
    if not store or not graph:
        raise FileNotFoundError(f"graph artifacts not found for session {session_id}")

    node = graph.get("nodes", {}).get(node_id)
    if not node:
        raise KeyError(f"unknown node: {node_id}")

    selected = set(facets or ["identity"])
    if "all" in selected:
        selected = {"identity", "configuration", "evidence", "substrate", "payload"}

    assertion = _assertion_by_subject(store).get(node_id) or _assertion_by_id(store).get(
        str(node.get("assertion_id", ""))
    )
    if not assertion:
        raise KeyError(f"assertion not found for node: {node_id}")

    bundle = store.get("evidence_bundles", {}).get(str(assertion["evidence_bundle_id"]), {})
    result: Dict[str, Any] = {
        "session_id": session_id,
        "node_id": node_id,
        "kind": node.get("kind"),
        "detail_level": node.get("detail_level"),
        "facet_completeness": node.get("facet_completeness", {}),
    }

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
