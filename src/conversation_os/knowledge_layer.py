from __future__ import annotations

import hashlib
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Tuple

from .conversation_synthesis import load_concept_edges, load_concept_nodes
from .context_bubbles import load_bubble_edges, load_bubble_memberships, load_context_bubbles
from .conversation_threads import build_conversation_threads, load_conversation_threads, load_thread_links
from .meta_layer import load_meta_records
from .models import KnowledgeEdge, KnowledgeNode
from .runtime_layout import product_runtime_dir
from .storage import read_json, read_jsonl, utc_now, write_json, write_jsonl
from .thread_abstractions import (
    build_thread_abstractions,
    load_project_lenses,
    load_thread_abstraction_links,
    load_thread_abstractions,
)
from .candidate_admission import (
    apply_fail_empty_gate,
    compute_ranking_score,
    evaluate_capsule_admission,
    fail_empty_admission_enforce_enabled,
    fail_empty_admission_shadow_enabled,
)
from .vault_ingest import load_source_registry, tokenize


MODULE_ID = "kernel.knowledge.knowledge_layer"
CONTRACT_VERSION = "1.0"
PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "load_knowledge_nodes",
    "load_knowledge_edges",
    "load_context_links",
    "load_semantic_capsules",
    "load_link_governance",
    "govern_context_link",
    "add_alias_resolution",
    "build_retrieval_bundle",
    "build_knowledge_layer",
    "select_candidate_pairs",
)
__all__ = list(PUBLIC_API)


def _data_dir(root: Path) -> Path:
    return product_runtime_dir(root, "inner_world_v1", "data")


def _nodes_path(root: Path) -> Path:
    return _data_dir(root) / "knowledge_nodes.jsonl"


def _edges_path(root: Path) -> Path:
    return _data_dir(root) / "knowledge_edges.jsonl"


def _context_links_path(root: Path) -> Path:
    return _data_dir(root) / "context_links.jsonl"


def _capsules_path(root: Path) -> Path:
    return _data_dir(root) / "semantic_capsules.jsonl"


def _link_governance_path(root: Path) -> Path:
    return _data_dir(root) / "link_governance.json"


def _default_link_governance(root: Path) -> Dict[str, Any]:
    path = _link_governance_path(root)
    return {
        "governance_path": str(path),
        "updated_at": None,
        "link_policies": [],
        "alias_resolutions": [],
    }


def load_knowledge_nodes(root: Path) -> List[Dict]:
    return read_jsonl(_nodes_path(root))


def load_knowledge_edges(root: Path) -> List[Dict]:
    return read_jsonl(_edges_path(root))


def load_context_links(root: Path) -> List[Dict]:
    rows = read_jsonl(_context_links_path(root))
    return _apply_link_governance(root, rows, load_link_governance(root))


def load_semantic_capsules(root: Path) -> List[Dict]:
    return read_jsonl(_capsules_path(root))


def load_link_governance(root: Path) -> Dict[str, Any]:
    stored = read_json(_link_governance_path(root), default=None)
    base = _default_link_governance(root)
    if not stored:
        return base
    return {
        **base,
        **stored,
        "link_policies": list(stored.get("link_policies", [])),
        "alias_resolutions": list(stored.get("alias_resolutions", [])),
    }


def _save_link_governance(root: Path, payload: Dict[str, Any]) -> None:
    write_json(_link_governance_path(root), payload)


def _upsert_governance_row(rows: List[Dict[str, Any]], key: str, value: str, patch: Dict[str, Any]) -> Dict[str, Any]:
    target = next((row for row in rows if row.get(key) == value), None)
    if target is None:
        target = {key: value}
        rows.append(target)
    target.update(patch)
    target["updated_at"] = utc_now()
    return target


def govern_context_link(
    root: Path,
    link_id: str,
    *,
    governance_status: str,
    confidence_override: float | None = None,
    confidence_delta: float | None = None,
    notes: str | None = None,
) -> Dict[str, Any]:
    governance = load_link_governance(root)
    patch: Dict[str, Any] = {"governance_status": governance_status}
    if confidence_override is not None:
        patch["confidence_override"] = round(float(confidence_override), 3)
    if confidence_delta is not None:
        patch["confidence_delta"] = round(float(confidence_delta), 3)
    if notes is not None:
        patch["notes"] = notes
    record = _upsert_governance_row(governance["link_policies"], "link_id", link_id, patch)
    governance["updated_at"] = utc_now()
    _save_link_governance(root, governance)
    resolved = next((row for row in load_context_links(root) if row.get("link_id") == link_id), None)
    return {"policy": record, "resolved_link": resolved}


def add_alias_resolution(
    root: Path,
    alias_text: str,
    *,
    ref_type: str,
    ref_id: str,
    status: str = "active",
    notes: str | None = None,
) -> Dict[str, Any]:
    governance = load_link_governance(root)
    alias_key = alias_text.strip().lower()
    patch: Dict[str, Any] = {
        "alias_text": alias_text.strip(),
        "status": status,
        "ref_type": ref_type,
        "ref_id": ref_id,
    }
    if notes is not None:
        patch["notes"] = notes
    record = _upsert_governance_row(governance["alias_resolutions"], "alias_key", alias_key, patch)
    governance["updated_at"] = utc_now()
    _save_link_governance(root, governance)
    return {"alias_resolution": record}


def _ref_pond_profiles(root: Path) -> Dict[str, Dict[str, Any]]:
    source_ref_map = _source_ref_pond_map(root)
    source_profiles: Dict[str, Dict[str, Any]] = {}
    for row in load_source_registry(root):
        source_id = str(row.get("source_id", "")).strip()
        source_ref = str(row.get("source_ref", "")).strip()
        if not source_id or not source_ref:
            continue
        profile = source_ref_map.get(source_ref, {"primary_pond": "", "pond_layers": []})
        source_profiles[f"source:{source_id}"] = {
            "primary_pond": str(profile.get("primary_pond", "")).strip(),
            "pond_layers": [str(value).strip() for value in profile.get("pond_layers", []) if str(value).strip()],
        }
    capsule_profiles: Dict[str, Dict[str, Any]] = {}
    for capsule in load_semantic_capsules(root):
        ref_type = str(capsule.get("ref_type", "")).strip()
        ref_id = str(capsule.get("ref_id", "")).strip()
        if not ref_type or not ref_id:
            continue
        capsule_profiles[f"{ref_type}:{ref_id}"] = _capsule_pond_profile(capsule, source_ref_map)
    return {**capsule_profiles, **source_profiles}


def _apply_link_governance(root: Path, rows: List[Dict[str, Any]], governance: Dict[str, Any]) -> List[Dict[str, Any]]:
    policy_map = {row.get("link_id"): row for row in governance.get("link_policies", []) if row.get("link_id")}
    ref_pond_profiles = _ref_pond_profiles(root)
    resolved: List[Dict[str, Any]] = []
    for row in rows:
        updated = dict(row)
        from_key = f"{row.get('from_ref_type', '')}:{row.get('from_ref_id', '')}"
        to_key = f"{row.get('to_ref_type', '')}:{row.get('to_ref_id', '')}"
        from_pond_profile = dict(ref_pond_profiles.get(from_key, {"primary_pond": "", "pond_layers": []}))
        to_pond_profile = dict(ref_pond_profiles.get(to_key, {"primary_pond": "", "pond_layers": []}))
        from_pond = str(from_pond_profile.get("primary_pond", "")).strip()
        to_pond = str(to_pond_profile.get("primary_pond", "")).strip()
        cross_pond = bool(from_pond and to_pond and from_pond != to_pond)
        updated["from_pond_profile"] = from_pond_profile
        updated["to_pond_profile"] = to_pond_profile
        updated["cross_pond"] = cross_pond
        updated["bridge_status"] = "same_pond"
        if cross_pond:
            updated["bridge_status"] = "candidate"
        policy = policy_map.get(row.get("link_id"))
        if not policy:
            if cross_pond:
                updated["confidence"] = round(min(0.999, max(0.0, float(updated.get("confidence", 0.0)) - 0.08)), 3)
            resolved.append(updated)
            continue
        status = policy.get("governance_status", "").strip().lower()
        if status:
            updated["status"] = status
        confidence = float(updated.get("confidence", 0.0))
        if policy.get("confidence_override") is not None:
            confidence = float(policy["confidence_override"])
        elif policy.get("confidence_delta") is not None:
            confidence += float(policy["confidence_delta"])
        elif status == "promoted":
            confidence += 0.18
        elif status == "downweighted":
            confidence -= 0.18
        elif status == "rejected":
            confidence = 0.0
        if cross_pond and status not in {"promoted", "rejected"} and policy.get("confidence_override") is None:
            confidence -= 0.08
        updated["confidence"] = round(min(0.999, max(0.0, confidence)), 3)
        governance_meta = {
            "governance_status": status or "active",
            "notes": policy.get("notes", ""),
            "updated_at": policy.get("updated_at"),
        }
        if policy.get("confidence_override") is not None:
            governance_meta["confidence_override"] = policy["confidence_override"]
        if policy.get("confidence_delta") is not None:
            governance_meta["confidence_delta"] = policy["confidence_delta"]
        updated["governance"] = governance_meta
        if cross_pond:
            if status == "promoted":
                updated["bridge_status"] = "promoted"
            elif status == "rejected":
                updated["bridge_status"] = "rejected"
            elif status == "downweighted":
                updated["bridge_status"] = "downweighted"
        resolved.append(updated)
    return resolved


def _active_alias_resolutions(governance: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [
        row
        for row in governance.get("alias_resolutions", [])
        if row.get("alias_key") and row.get("status", "active") not in {"rejected", "archived"}
    ]


def _edge_kind(left: Dict, right: Dict) -> str:
    if left["kind"] == "contradiction" or right["kind"] == "contradiction":
        return "contradicts"
    if left["kind"] == "transfer_target" or right["kind"] == "transfer_target":
        return "transfers_to"
    if left["kind"] == "review_item" or right["kind"] == "review_item":
        return "requires_review"
    return "relates_to"


def _add_token_pairs(pair_buckets: Dict[tuple[str, str], Dict], rows: List[Dict], token: str) -> None:
    ordered_rows = sorted(rows, key=lambda item: (-item["confidence"], item["meta_id"]))[:12]
    for index, left in enumerate(ordered_rows):
        for right in ordered_rows[index + 1 : index + 5]:
            pair = tuple(sorted([left["meta_id"], right["meta_id"]]))
            bucket = pair_buckets.setdefault(
                pair,
                {
                    "left": left,
                    "right": right,
                    "shared_tokens": set(),
                    "fallback": False,
                },
            )
            bucket["shared_tokens"].add(token)


def _add_source_pairs(pair_buckets: Dict[tuple[str, str], Dict], rows: List[Dict]) -> None:
    ordered_rows = sorted(rows, key=lambda item: (-item["confidence"], item["meta_id"]))[:12]
    for index, left in enumerate(ordered_rows):
        matches = 0
        for right in ordered_rows[index + 1 :]:
            if left["kind"] == right["kind"]:
                continue
            pair = tuple(sorted([left["meta_id"], right["meta_id"]]))
            bucket = pair_buckets.setdefault(
                pair,
                {
                    "left": left,
                    "right": right,
                    "shared_tokens": set(
                        sorted(set(left.get("attributes", {}).get("tokens", [])) & set(right.get("attributes", {}).get("tokens", [])))
                    ),
                    "fallback": True,
                },
            )
            bucket["fallback"] = True
            matches += 1
            if matches >= 3:
                break


def _semantic_role(meta: Dict) -> str:
    return meta.get("attributes", {}).get("semantic_role", "")


def _node_ref(node_id: str) -> Tuple[str, str]:
    prefixes = [
        ("abstract-thread-node-", "thread_abstraction"),
        ("project-lens-node-", "project_lens"),
        ("bubble-node-", "bubble"),
        ("thread-node-", "thread"),
        ("source-node-", "source"),
        ("meta-node-", "meta"),
        ("concept-node-", "concept"),
    ]
    for prefix, ref_type in prefixes:
        if node_id.startswith(prefix):
            return ref_type, node_id.removeprefix(prefix)
    return "node", node_id


def _make_link(
    *,
    layer: str,
    kind: str,
    from_ref_type: str,
    from_ref_id: str,
    to_ref_type: str,
    to_ref_id: str,
    status: str,
    confidence: float,
    evidence_refs: List[str],
    attributes: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    seed = "::".join([layer, kind, from_ref_type, from_ref_id, to_ref_type, to_ref_id]).encode("utf-8")
    return {
        "link_id": f"link-{hashlib.sha256(seed).hexdigest()[:12]}",
        "layer": layer,
        "kind": kind,
        "from_ref_type": from_ref_type,
        "from_ref_id": from_ref_id,
        "to_ref_type": to_ref_type,
        "to_ref_id": to_ref_id,
        "status": status,
        "confidence": round(confidence, 3),
        "evidence_refs": sorted(set(evidence_refs)),
        "attributes": attributes or {},
    }


def _make_capsule(
    *,
    capsule_type: str,
    ref_type: str,
    ref_id: str,
    label: str,
    summary: str,
    status: str,
    confidence: float,
    source_refs: List[str],
    evidence_refs: List[str],
    linked_ref_ids: List[str],
    attributes: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    capsule_id = f"capsule-{ref_type}-{ref_id}"
    return {
        "capsule_id": capsule_id,
        "capsule_type": capsule_type,
        "ref_type": ref_type,
        "ref_id": ref_id,
        "label": label,
        "summary": summary,
        "status": status,
        "confidence": round(confidence, 3),
        "source_refs": sorted(set(source_refs)),
        "evidence_refs": sorted(set(evidence_refs)),
        "linked_ref_ids": sorted(set(linked_ref_ids)),
        "attributes": attributes or {},
    }


def _build_meta_thread_map(meta_rows: List[Dict], thread_rows: List[Dict]) -> Dict[str, set[str]]:
    mapping: Dict[str, set[str]] = defaultdict(set)
    for meta in meta_rows:
        chunk_ids = set(meta.get("chunk_ids", []))
        if not chunk_ids:
            continue
        role = _semantic_role(meta)
        for thread in thread_rows:
            if role == "approved_context":
                target_chunks = set(thread.get("approved_context_chunk_ids", []))
            else:
                target_chunks = set(thread.get("user_chunk_ids", []))
            if chunk_ids & target_chunks:
                mapping[meta["meta_id"]].add(thread["thread_id"])
    return mapping


def _build_meta_abstraction_map(abstraction_rows: List[Dict]) -> Dict[str, set[str]]:
    mapping: Dict[str, set[str]] = defaultdict(set)
    for abstraction in abstraction_rows:
        abstract_thread_id = abstraction["abstract_thread_id"]
        for meta_id in abstraction.get("semantic_line_meta_ids", []):
            mapping[meta_id].add(abstract_thread_id)
        for meta_id in abstraction.get("approved_context_meta_ids", []):
            mapping[meta_id].add(abstract_thread_id)
    return mapping


def _build_chunk_meta_maps(meta_rows: List[Dict]) -> tuple[Dict[str, List[Dict]], Dict[str, List[Dict]]]:
    semantic_meta_by_chunk: Dict[str, List[Dict]] = defaultdict(list)
    context_meta_by_chunk: Dict[str, List[Dict]] = defaultdict(list)
    for meta in meta_rows:
        role = _semantic_role(meta)
        target = None
        if role in {"semantic_line", "primary_source"}:
            target = semantic_meta_by_chunk
        elif role == "approved_context":
            target = context_meta_by_chunk
        if target is None:
            continue
        for chunk_id in meta.get("chunk_ids", []):
            target[chunk_id].append(meta)
    return semantic_meta_by_chunk, context_meta_by_chunk


def _build_source_ref_to_ids(source_rows: List[Dict]) -> Dict[str, List[str]]:
    mapping: Dict[str, List[str]] = defaultdict(list)
    for source in source_rows:
        mapping[source["source_ref"]].append(source["source_id"])
    return mapping


def _add_context_embedding_edges(
    edges: List[Dict],
    meta_rows: List[Dict],
    meta_to_threads: Dict[str, set[str]],
    meta_to_abstractions: Dict[str, set[str]],
) -> int:
    semantic_lines = [row for row in meta_rows if _semantic_role(row) == "semantic_line"]
    approved_contexts = [row for row in meta_rows if _semantic_role(row) == "approved_context"]
    if not semantic_lines or not approved_contexts:
        return 0

    lines_by_source: Dict[str, List[Dict]] = defaultdict(list)
    for row in semantic_lines:
        for source_ref in row.get("source_refs", []):
            lines_by_source[source_ref].append(row)

    created = 0
    seen_pairs = set()
    for context in approved_contexts:
        context_intents = set(context.get("attributes", {}).get("delta_intent_keys", []))
        if not context_intents:
            continue
        context_tokens = set(context.get("attributes", {}).get("tokens", []))
        context_priority = set(context.get("attributes", {}).get("priority_tokens", []))
        context_threads = meta_to_threads.get(context["meta_id"], set())
        context_abstractions = meta_to_abstractions.get(context["meta_id"], set())
        candidate_rows = {}
        for source_ref in context.get("source_refs", []):
            for line in lines_by_source.get(source_ref, []):
                candidate_rows[line["meta_id"]] = line
        ranked = []
        for line in candidate_rows.values():
            line_intents = set(line.get("attributes", {}).get("delta_intent_keys", []))
            shared_intents = sorted(context_intents & line_intents)
            if not shared_intents:
                continue
            line_tokens = set(line.get("attributes", {}).get("tokens", []))
            shared_tokens = sorted(context_tokens & line_tokens)[:6]
            line_priority = set(line.get("attributes", {}).get("priority_tokens", []))
            shared_priority = sorted(context_priority & line_priority)[:6]
            same_threads = sorted(context_threads & meta_to_threads.get(line["meta_id"], set()))
            same_abstractions = sorted(context_abstractions & meta_to_abstractions.get(line["meta_id"], set()))
            score = len(shared_intents) * 10 + len(shared_priority) * 4 + len(shared_tokens)
            if same_threads:
                score += 5
            if same_abstractions:
                score += 3
            ranked.append((score, shared_intents, shared_tokens, shared_priority, same_threads, same_abstractions, line))
        ranked.sort(
            key=lambda item: (
                -item[0],
                -len(item[1]),
                -len(item[4]),
                -len(item[5]),
                -item[6]["confidence"],
                item[6]["meta_id"],
            )
        )
        for score, shared_intents, shared_tokens, shared_priority, same_threads, same_abstractions, line in ranked[:2]:
            pair_key = (context["meta_id"], line["meta_id"])
            if pair_key in seen_pairs:
                continue
            seen_pairs.add(pair_key)
            confidence = 0.66 + 0.06 * min(2, len(shared_intents)) + 0.03 * min(2, len(shared_priority))
            if same_threads:
                confidence += 0.05
            if same_abstractions:
                confidence += 0.04
            edges.append(
                KnowledgeEdge(
                    edge_id=f"edge-context-{hashlib.sha256(':'.join(pair_key).encode('utf-8')).hexdigest()[:12]}",
                    kind="context_for",
                    from_id=f"meta-node-{context['meta_id']}",
                    to_id=f"meta-node-{line['meta_id']}",
                    status="provisional",
                    confidence=round(min(0.94, confidence), 2),
                    evidence_refs=sorted(set(context["source_refs"] + line["source_refs"])),
                    attributes={
                        "shared_intent_keys": shared_intents,
                        "shared_tokens": shared_tokens,
                        "shared_priority_tokens": shared_priority,
                        "same_thread_ids": same_threads,
                        "same_abstract_thread_ids": same_abstractions,
                    },
                ).to_dict()
            )
            created += 1
    return created


def _build_substrate_links(source_rows: List[Dict], meta_rows: List[Dict]) -> List[Dict]:
    links: List[Dict] = []

    grouped_sources: Dict[str, List[Dict]] = defaultdict(list)
    for row in source_rows:
        grouped_sources[row.get("source_family", "unknown")].append(row)
    for rows in grouped_sources.values():
        ordered = sorted(rows, key=lambda item: (item.get("created_at") or "", item["source_ref"]))
        for left, right in zip(ordered, ordered[1:]):
            links.append(
                _make_link(
                    layer="substrate",
                    kind="source_sequence",
                    from_ref_type="source",
                    from_ref_id=left["source_id"],
                    to_ref_type="source",
                    to_ref_id=right["source_id"],
                    status="stable",
                    confidence=0.72,
                    evidence_refs=[left["source_ref"], right["source_ref"]],
                    attributes={"source_family": left.get("source_family", "unknown")},
                )
            )

    metas_by_chunk: Dict[str, List[Dict]] = defaultdict(list)
    for meta in meta_rows:
        for chunk_id in meta.get("chunk_ids", []):
            metas_by_chunk[chunk_id].append(meta)
    for chunk_id, rows in metas_by_chunk.items():
        ordered = sorted(rows, key=lambda item: (-item["confidence"], item["meta_id"]))[:6]
        for index, left in enumerate(ordered):
            for right in ordered[index + 1 :]:
                links.append(
                    _make_link(
                        layer="substrate",
                        kind="same_chunk",
                        from_ref_type="meta",
                        from_ref_id=left["meta_id"],
                        to_ref_type="meta",
                        to_ref_id=right["meta_id"],
                        status="provisional",
                        confidence=0.68,
                        evidence_refs=sorted(set(left["source_refs"] + right["source_refs"])),
                        attributes={"chunk_id": chunk_id},
                    )
                )

    return links


def _build_semantic_capsules(
    meta_rows: List[Dict],
    abstraction_rows: List[Dict],
    bubble_rows: List[Dict],
    concept_rows: List[Dict],
) -> List[Dict]:
    capsules: List[Dict] = []
    for meta in meta_rows:
        capsules.append(
            _make_capsule(
                capsule_type="meta",
                ref_type="meta",
                ref_id=meta["meta_id"],
                label=meta["label"],
                summary=meta["summary"],
                status=meta["status"],
                confidence=meta["confidence"],
                source_refs=meta.get("source_refs", []),
                evidence_refs=meta.get("evidence", []),
                linked_ref_ids=[f"chunk:{chunk_id}" for chunk_id in meta.get("chunk_ids", [])],
                attributes={"kind": meta["kind"], **meta.get("attributes", {})},
            )
        )
    for abstraction in abstraction_rows:
        capsules.append(
            _make_capsule(
                capsule_type="thread_abstraction",
                ref_type="thread_abstraction",
                ref_id=abstraction["abstract_thread_id"],
                label=abstraction["label"],
                summary=abstraction["thesis"],
                status="stable" if abstraction["resolution_state"] == "resolved" else "provisional",
                confidence=abstraction["confidence"],
                source_refs=abstraction.get("source_refs", []),
                evidence_refs=abstraction.get("dominant_tensions", []) + abstraction.get("delta_intent_keys", []),
                linked_ref_ids=[f"thread:{thread_id}" for thread_id in abstraction.get("child_thread_ids", [])],
                attributes={
                    "primary_lens_key": abstraction["primary_lens_key"],
                    "secondary_lens_keys": abstraction.get("secondary_lens_keys", []),
                    "project_lens_keys": abstraction.get("project_lens_keys", []),
                },
            )
        )
    for bubble in bubble_rows:
        capsules.append(
            _make_capsule(
                capsule_type="bubble",
                ref_type="bubble",
                ref_id=bubble["bubble_id"],
                label=bubble["label"],
                summary=bubble["thesis"],
                status=bubble["status"],
                confidence=bubble["confidence"],
                source_refs=bubble.get("source_refs", []),
                evidence_refs=bubble.get("active_tensions", []) + bubble.get("open_questions", []),
                linked_ref_ids=[f"meta:{meta_id}" for meta_id in bubble.get("meta_ids", [])]
                + [f"concept:{concept_id}" for concept_id in bubble.get("concept_ids", [])],
                attributes={
                    "domain_lenses": bubble.get("domain_lenses", []),
                    "project_lens_keys": bubble.get("project_lens_keys", []),
                    "primary_concept_id": bubble.get("primary_concept_id", ""),
                },
            )
        )
    for concept in concept_rows:
        capsules.append(
            _make_capsule(
                capsule_type="concept",
                ref_type="concept",
                ref_id=concept["concept_id"],
                label=concept["label"],
                summary=concept.get("transfer_shape") or concept.get("abstract_pattern") or concept["label"],
                status=concept["status"],
                confidence=float(concept.get("confidence", 0.0)),
                source_refs=concept.get("source_refs", []),
                evidence_refs=concept.get("aliases", []),
                linked_ref_ids=[f"artifact:{artifact}" for artifact in concept.get("artifact_refs", [])],
                attributes={
                    "aliases": concept.get("aliases", []),
                    "abstract_pattern": concept.get("abstract_pattern", ""),
                    "transfer_shape": concept.get("transfer_shape", ""),
                },
            )
        )

    capsules.sort(key=lambda item: (-float(item["confidence"]), item["capsule_type"], item["label"]))
    return capsules


def _build_context_links(
    substrate_links: List[Dict],
    knowledge_edges: List[Dict],
    bubble_rows: List[Dict],
    concept_rows: List[Dict],
    concept_edges: List[Dict],
) -> List[Dict]:
    links = list(substrate_links)

    for edge in knowledge_edges:
        from_ref_type, from_ref_id = _node_ref(edge["from_id"])
        to_ref_type, to_ref_id = _node_ref(edge["to_id"])
        links.append(
            _make_link(
                layer="semantic",
                kind=edge["kind"],
                from_ref_type=from_ref_type,
                from_ref_id=from_ref_id,
                to_ref_type=to_ref_type,
                to_ref_id=to_ref_id,
                status=edge["status"],
                confidence=float(edge["confidence"]),
                evidence_refs=edge.get("evidence_refs", []),
                attributes=edge.get("attributes", {}),
            )
        )

    concept_by_id = {row["concept_id"]: row for row in concept_rows}
    for bubble in bubble_rows:
        for concept_id in bubble.get("concept_ids", []):
            if concept_id not in concept_by_id:
                continue
            links.append(
                _make_link(
                    layer="semantic",
                    kind="bubble_aligns_concept",
                    from_ref_type="bubble",
                    from_ref_id=bubble["bubble_id"],
                    to_ref_type="concept",
                    to_ref_id=concept_id,
                    status="provisional",
                    confidence=round(min(0.95, 0.62 + 0.06 * len(bubble.get("concept_ids", []))), 2),
                    evidence_refs=sorted(set(bubble.get("source_refs", []) + concept_by_id[concept_id].get("source_refs", []))),
                    attributes={"primary_concept": bubble.get("primary_concept_id", "") == concept_id},
                )
            )

    for edge in concept_edges:
        links.append(
            _make_link(
                layer="semantic",
                kind=edge["kind"],
                from_ref_type="concept",
                from_ref_id=edge["from_id"],
                to_ref_type="concept",
                to_ref_id=edge["to_id"],
                status=edge.get("status", "provisional"),
                confidence=float(edge.get("confidence", 0.0)),
                evidence_refs=edge.get("source_refs", []),
                attributes={"shared_terms": edge.get("shared_terms", [])},
            )
        )

    deduped = {link["link_id"]: link for link in links}
    return sorted(
        deduped.values(),
        key=lambda item: (
            item["layer"],
            -float(item["confidence"]),
            item["kind"],
            item["from_ref_type"],
            item["from_ref_id"],
            item["to_ref_type"],
            item["to_ref_id"],
        ),
    )


def _capsule_index_tokens(capsule: Dict[str, Any]) -> Dict[str, set[str]]:
    return {
        "label": set(tokenize(capsule.get("label", ""))),
        "summary": set(tokenize(capsule.get("summary", ""))),
        "attrs": set(
            token
            for value in capsule.get("attributes", {}).values()
            for token in tokenize(" ".join(value) if isinstance(value, list) else str(value))
        ),
    }


def _source_ref_pond_map(root: Path) -> Dict[str, Dict[str, Any]]:
    from .library_tracker import resolve_governed_chunk_rows

    source_map: Dict[str, Dict[str, Any]] = {}
    for row in resolve_governed_chunk_rows(root):
        source_ref = str(row.get("source_ref", "")).strip()
        primary_pond = str(row.get("primary_pond", "")).strip()
        if not source_ref or not primary_pond:
            continue
        entry = source_map.setdefault(source_ref, {"primary_pond_counts": defaultdict(int), "pond_layers": defaultdict(set)})
        entry["primary_pond_counts"][primary_pond] += 1
        for layer in row.get("pond_layers", []) or []:
            entry["pond_layers"][primary_pond].add(str(layer).strip())
    resolved: Dict[str, Dict[str, Any]] = {}
    for source_ref, entry in source_map.items():
        ranked = sorted(entry["primary_pond_counts"].items(), key=lambda item: (-item[1], item[0]))
        primary_pond = ranked[0][0]
        resolved[source_ref] = {
            "primary_pond": primary_pond,
            "pond_layers": sorted(entry["pond_layers"].get(primary_pond, set())),
        }
    return resolved


def _capsule_pond_profile(capsule: Dict[str, Any], source_ref_map: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    pond_counts: Dict[str, int] = defaultdict(int)
    pond_layers: Dict[str, set[str]] = defaultdict(set)
    for source_ref in capsule.get("source_refs", []) or []:
        entry = source_ref_map.get(str(source_ref).strip())
        if not entry:
            continue
        pond_id = str(entry.get("primary_pond", "")).strip()
        if not pond_id:
            continue
        pond_counts[pond_id] += 1
        for layer in entry.get("pond_layers", []) or []:
            pond_layers[pond_id].add(str(layer).strip())
    if not pond_counts:
        return {"primary_pond": "", "pond_layers": []}
    primary_pond = sorted(pond_counts.items(), key=lambda item: (-item[1], item[0]))[0][0]
    return {
        "primary_pond": primary_pond,
        "pond_layers": sorted(pond_layers.get(primary_pond, set())),
    }


def build_retrieval_bundle(
    root: Path,
    query: str,
    limit: int = 10,
    neighbor_limit: int = 6,
    *,
    include_cross_pond: bool = False,
    envelope_mode: str = "open",
    explicit_pins: List[str] | None = None,
    shape_search: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    empty_bundle = {
        "query": query,
        "seed_capsules": [],
        "related_capsules": [],
        "included_links": [],
        "source_refs": [],
        "count": 0,
        "alias_hits": [],
        "anchor_pond": "",
        "include_cross_pond": include_cross_pond,
        "envelope_mode": str(envelope_mode or "open").strip().lower(),
    }
    shadow_enabled = fail_empty_admission_shadow_enabled(root)
    enforce_enabled = fail_empty_admission_enforce_enabled(root)

    shape_context: Dict[str, Any] = {"result_status": "disabled"}
    shape_decisions_by_capsule: Dict[str, Dict[str, Any]] = {}
    from .shape_candidate_retrieval import (
        build_shape_query,
        enrich_capsule_admission_with_shape,
        apply_shape_ranking_adjustment,
        read_shape_retrieval_context,
        shape_anti_match_enforcement_enabled,
        shape_candidate_search_enabled,
    )

    shape_search_enabled = shape_candidate_search_enabled(root)
    if shape_search is not None and "enabled" in shape_search:
        shape_search_enabled = bool(shape_search.get("enabled"))
    if shape_search_enabled:
        shape_query = build_shape_query(
            query,
            branch_id=str((shape_search or {}).get("branch_id", "") or ""),
            scope_id=str((shape_search or {}).get("scope_id", "") or ""),
            source_refs=list((shape_search or {}).get("source_refs", []) or []),
            maturity_ceiling=str((shape_search or {}).get("maturity_ceiling", "candidate") or "candidate"),
        )
        shape_context = read_shape_retrieval_context(root, shape_query)
        shape_context["branch_id"] = shape_query.branch_id
        shape_context["scope_id"] = shape_query.scope_id
    enforce_anti_match = shape_anti_match_enforcement_enabled(root)
    if shape_search is not None and "enforce_anti_match" in shape_search:
        enforce_anti_match = bool(shape_search.get("enforce_anti_match"))

    if enforce_enabled:
        from .corpus_catalog_snapshot import load_corpus_catalog_for_request

        catalog = load_corpus_catalog_for_request(root)
        readiness = str(catalog.get("readiness_state", "") or "")
        if readiness == "stale":
            return empty_bundle | {"result_status": "abstained_stale_index"}
        if readiness in {"interrupted", "unsupported"}:
            return empty_bundle | {"result_status": "abstained_dependency_not_ready"}

    capsules = load_semantic_capsules(root)
    links = load_context_links(root)
    governance = load_link_governance(root)
    query_tokens = set(tokenize(query))
    source_ref_map = _source_ref_pond_map(root)
    if not capsules:
        bundle = dict(empty_bundle)
        if enforce_enabled:
            bundle["result_status"] = "empty_no_positive_match"
        return bundle

    type_weight = {
        "concept": 1.2,
        "bubble": 1.1,
        "thread_abstraction": 1.0,
        "meta": 0.8,
    }
    scores: Dict[str, float] = {}
    admission_by_capsule: Dict[str, Dict[str, Any]] = {}
    capsule_by_ref = {f"{row['ref_type']}:{row['ref_id']}": row for row in capsules}
    alias_ref_keys: set[str] = set()
    alias_hits: List[Dict[str, Any]] = []
    for alias in _active_alias_resolutions(governance):
        alias_tokens = set(tokenize(alias.get("alias_text", "")))
        if not alias_tokens or not (alias_tokens & query_tokens):
            continue
        ref_key = f"{alias.get('ref_type', '')}:{alias.get('ref_id', '')}"
        capsule = capsule_by_ref.get(ref_key)
        if capsule is None:
            continue
        alias_ref_keys.add(ref_key)
        alias_hits.append(
            {
                "alias_text": alias.get("alias_text", ""),
                "ref_type": alias.get("ref_type", ""),
                "ref_id": alias.get("ref_id", ""),
            }
        )

    for capsule in capsules:
        index = _capsule_index_tokens(capsule)
        capsule["pond_profile"] = _capsule_pond_profile(capsule, source_ref_map)
        ref_key = f"{capsule['ref_type']}:{capsule['ref_id']}"
        decision = evaluate_capsule_admission(
            capsule,
            query_tokens=query_tokens,
            index_tokens=index,
            alias_matched=ref_key in alias_ref_keys,
            explicit_pins=explicit_pins,
            envelope_mode=envelope_mode,
            pond_profile=capsule.get("pond_profile", {}),
        )
        admission_by_capsule[capsule["capsule_id"]] = decision
        shape_decision = enrich_capsule_admission_with_shape(
            capsule,
            decision,
            shape_context=shape_context,
            orientation_tokens=query_tokens,
            enforce_anti_match=enforce_anti_match,
        )
        if shape_decision is not None:
            shape_decisions_by_capsule[capsule["capsule_id"]] = shape_decision.to_dict()
        ranking_score = compute_ranking_score(
            capsule,
            ranking_features=decision["ranking_features"],
            type_weight=type_weight,
        )
        ranking_score = apply_shape_ranking_adjustment(
            ranking_score,
            shape_decisions_by_capsule.get(capsule["capsule_id"]),
        )
        if ref_key in alias_ref_keys:
            ranking_score = round(ranking_score + 7.5, 3)
        scores[capsule["capsule_id"]] = ranking_score

    pond_scores: Dict[str, float] = defaultdict(float)
    for capsule in capsules:
        decision = admission_by_capsule[capsule["capsule_id"]]
        if not decision.get("admitted"):
            continue
        pond_id = str(capsule.get("pond_profile", {}).get("primary_pond", "")).strip()
        if pond_id:
            pond_scores[pond_id] += scores.get(capsule["capsule_id"], 0.0)
    ranked_ponds = sorted(pond_scores.items(), key=lambda item: (-item[1], item[0]))
    anchor_pond = ranked_ponds[0][0] if ranked_ponds and ranked_ponds[0][1] > 0 else ""

    ranked = sorted(
        capsules,
        key=lambda item: (
            anchor_pond and str(item.get("pond_profile", {}).get("primary_pond", "")).strip() != anchor_pond,
            -scores[item["capsule_id"]],
            -float(item.get("confidence", 0.0)),
            item["label"],
        ),
    )
    admitted_ranked = [
        row for row in ranked if admission_by_capsule[row["capsule_id"]].get("admitted")
    ]
    seeds = admitted_ranked[:3]
    if not seeds and not enforce_enabled:
        legacy_seeds = [row for row in ranked if scores[row["capsule_id"]] > 0][:3]
        seeds = legacy_seeds or ranked[: min(3, len(ranked))]
    if anchor_pond:
        bounded_seeds = [
            row
            for row in seeds
            if str(row.get("pond_profile", {}).get("primary_pond", "")).strip() in {"", anchor_pond}
        ]
        if bounded_seeds:
            seeds = bounded_seeds

    selected_capsules = {row["capsule_id"]: row for row in seeds}
    included_links: List[Dict[str, Any]] = []
    adjacency: Dict[str, List[Tuple[float, Dict[str, Any], str]]] = defaultdict(list)
    for link in links:
        if link.get("status") in {"rejected", "archived"}:
            continue
        left = f"{link['from_ref_type']}:{link['from_ref_id']}"
        right = f"{link['to_ref_type']}:{link['to_ref_id']}"
        if left in capsule_by_ref and right in capsule_by_ref:
            adjacency[left].append((float(link["confidence"]), link, right))
            adjacency[right].append((float(link["confidence"]), link, left))

    for seed in seeds:
        ref_key = f"{seed['ref_type']}:{seed['ref_id']}"
        ranked_neighbors = sorted(
            adjacency.get(ref_key, []),
            key=lambda item: (-item[0], item[1]["kind"], item[2]),
        )
        added = 0
        for _, link, neighbor_ref in ranked_neighbors:
            neighbor = capsule_by_ref.get(neighbor_ref)
            if neighbor is None:
                continue
            if "pond_profile" not in neighbor:
                neighbor["pond_profile"] = _capsule_pond_profile(neighbor, source_ref_map)
            if anchor_pond and not include_cross_pond:
                neighbor_pond = str(neighbor.get("pond_profile", {}).get("primary_pond", "")).strip()
                bridge_status = str(link.get("bridge_status", "")).strip().lower()
                if neighbor_pond and neighbor_pond != anchor_pond and bridge_status != "promoted":
                    continue
            neighbor_index = _capsule_index_tokens(neighbor)
            neighbor_decision = evaluate_capsule_admission(
                neighbor,
                query_tokens=query_tokens,
                index_tokens=neighbor_index,
                alias_matched=neighbor_ref in alias_ref_keys,
                explicit_pins=explicit_pins,
                governed_graph=True,
                envelope_mode=envelope_mode,
                pond_profile=neighbor.get("pond_profile", {}),
            )
            neighbor_shape = enrich_capsule_admission_with_shape(
                neighbor,
                neighbor_decision,
                shape_context=shape_context,
                orientation_tokens=query_tokens,
                enforce_anti_match=enforce_anti_match,
            )
            if neighbor_shape is not None:
                shape_decisions_by_capsule[neighbor["capsule_id"]] = neighbor_shape.to_dict()
            admission_by_capsule[neighbor["capsule_id"]] = neighbor_decision
            if neighbor_decision.get("admitted"):
                neighbor_score = compute_ranking_score(
                    neighbor,
                    ranking_features=neighbor_decision["ranking_features"],
                    type_weight=type_weight,
                )
                scores[neighbor["capsule_id"]] = apply_shape_ranking_adjustment(
                    neighbor_score,
                    shape_decisions_by_capsule.get(neighbor["capsule_id"]),
                )
            if enforce_enabled and not neighbor_decision.get("admitted"):
                continue
            selected_capsules.setdefault(neighbor["capsule_id"], neighbor)
            included_links.append(link)
            added += 1
            if added >= neighbor_limit:
                break

    related_capsules = [
        row
        for row in sorted(
            selected_capsules.values(),
            key=lambda item: (
                item["capsule_id"] not in {seed["capsule_id"] for seed in seeds},
                -scores.get(item["capsule_id"], 0.0),
                -float(item.get("confidence", 0.0)),
                item["label"],
            ),
        )
        if row["capsule_id"] not in {seed["capsule_id"] for seed in seeds}
    ][: max(0, limit - len(seeds))]
    if anchor_pond and include_cross_pond:
        same_pond = []
        cross_pond = []
        for row in related_capsules:
            row_pond = str(row.get("pond_profile", {}).get("primary_pond", "")).strip()
            if row_pond and row_pond != anchor_pond:
                cross_pond.append(row)
            else:
                same_pond.append(row)
        related_capsules = same_pond + cross_pond
    source_refs = sorted(
        {
            source_ref
            for capsule in [*seeds, *related_capsules]
            for source_ref in capsule.get("source_refs", [])
        }
    )
    deduped_links = {link["link_id"]: link for link in included_links}
    bundle = {
        "query": query,
        "seed_capsules": seeds,
        "related_capsules": related_capsules,
        "included_links": list(deduped_links.values())[: limit + neighbor_limit],
        "source_refs": source_refs,
        "count": len(seeds) + len(related_capsules),
        "alias_hits": alias_hits,
        "anchor_pond": anchor_pond,
        "include_cross_pond": include_cross_pond,
        "envelope_mode": str(envelope_mode or "open").strip().lower(),
    }
    if shape_context.get("result_status") not in {"", "disabled"}:
        bundle["shape_retrieval"] = {
            "result_status": shape_context.get("result_status", ""),
            "readiness_state": shape_context.get("readiness_state", ""),
            "expansion_count": int(shape_context.get("expansion_count", 0) or 0),
            "resolved_bytes": int(shape_context.get("resolved_bytes", 0) or 0),
            "decision_count": len(shape_decisions_by_capsule),
        }
    if shadow_enabled or enforce_enabled:
        return apply_fail_empty_gate(
            bundle,
            admission_decisions=list(admission_by_capsule.values()),
            enforce=enforce_enabled,
            shadow=shadow_enabled,
            envelope_mode=envelope_mode,
        )
    return bundle


def build_knowledge_layer(root: Path, ensure_dependencies: bool = True) -> Dict:
    if ensure_dependencies:
        build_thread_abstractions(root)
    source_rows = load_source_registry(root)
    meta_rows = load_meta_records(root)
    bubble_rows = load_context_bubbles(root)
    bubble_memberships = load_bubble_memberships(root)
    bubble_edges = load_bubble_edges(root)
    thread_rows = load_conversation_threads(root)
    thread_links = load_thread_links(root)
    abstraction_rows = load_thread_abstractions(root)
    abstraction_links = load_thread_abstraction_links(root)
    project_lenses = load_project_lenses(root)
    concept_rows = load_concept_nodes(root)
    concept_edges = load_concept_edges(root)
    meta_to_threads = _build_meta_thread_map(meta_rows, thread_rows)
    meta_to_abstractions = _build_meta_abstraction_map(abstraction_rows)
    semantic_meta_by_chunk, context_meta_by_chunk = _build_chunk_meta_maps(meta_rows)
    source_ids_by_ref = _build_source_ref_to_ids(source_rows)

    nodes: List[Dict] = []
    edges: List[Dict] = []

    for source in source_rows:
        nodes.append(
            KnowledgeNode(
                node_id=f"source-node-{source['source_id']}",
                kind="source",
                label=source["title"],
                status="stable",
                confidence=1.0,
                source_refs=[source["source_ref"]],
                ref_id=source["source_id"],
                attributes={
                    "source_type": source["source_type"],
                    "source_family": source["source_family"],
                    "sensitivity_tier": source["sensitivity_tier"],
                },
            ).to_dict()
        )
    for meta in meta_rows:
        nodes.append(
            KnowledgeNode(
                node_id=f"meta-node-{meta['meta_id']}",
                kind=meta["kind"],
                label=meta["label"],
                status=meta["status"],
                confidence=meta["confidence"],
                source_refs=meta["source_refs"],
                ref_id=meta["meta_id"],
                attributes=meta.get("attributes", {}),
            ).to_dict()
        )
        source_ids = sorted(
            {
                source_id
                for source_ref in meta["source_refs"]
                for source_id in source_ids_by_ref.get(source_ref, [])
            }
        )
        for source_id in source_ids[:4]:
            edges.append(
                KnowledgeEdge(
                    edge_id=f"edge-source-meta-{source_id}-{meta['meta_id']}",
                    kind="source_contains",
                    from_id=f"source-node-{source_id}",
                    to_id=f"meta-node-{meta['meta_id']}",
                    status=meta["status"],
                    confidence=meta["confidence"],
                    evidence_refs=meta["source_refs"],
                    attributes={},
            ).to_dict()
        )

    for bubble in bubble_rows:
        nodes.append(
            KnowledgeNode(
                node_id=f"bubble-node-{bubble['bubble_id']}",
                kind="context_bubble",
                label=bubble["label"],
                status=bubble["status"],
                confidence=bubble["confidence"],
                source_refs=bubble["source_refs"],
                ref_id=bubble["bubble_id"],
                attributes={
                    "thesis": bubble["thesis"],
                    "support_count": bubble["support_count"],
                    "dominant_primitives": bubble.get("dominant_primitives", []),
                    "domain_lenses": bubble.get("domain_lenses", []),
                },
            ).to_dict()
        )
    for membership in bubble_memberships:
        edges.append(
            KnowledgeEdge(
                edge_id=f"edge-bubble-meta-{membership['bubble_id']}-{membership['meta_id']}",
                kind="bubble_contains",
                from_id=f"bubble-node-{membership['bubble_id']}",
                to_id=f"meta-node-{membership['meta_id']}",
                status="provisional",
                confidence=membership["confidence"],
                evidence_refs=[],
                attributes={"role": membership["role"]},
            ).to_dict()
        )
    for bubble_edge in bubble_edges:
        edges.append(
            KnowledgeEdge(
                edge_id=bubble_edge["edge_id"],
                kind=bubble_edge["kind"],
                from_id=f"bubble-node-{bubble_edge['from_bubble_id']}",
                to_id=f"bubble-node-{bubble_edge['to_bubble_id']}",
                status="provisional",
                confidence=bubble_edge["confidence"],
                evidence_refs=bubble_edge.get("evidence_refs", []),
                attributes={"shared_terms": bubble_edge.get("shared_terms", [])},
            ).to_dict()
        )

    for thread in thread_rows:
        nodes.append(
            KnowledgeNode(
                node_id=f"thread-node-{thread['thread_id']}",
                kind="conversation_thread",
                label=" / ".join(thread.get("topic_signature", [])[:4]) or thread["thread_id"],
                status="provisional",
                confidence=0.76,
                source_refs=thread.get("source_refs", []),
                ref_id=thread["thread_id"],
                attributes={
                    "turn_count": thread["turn_count"],
                    "interruption_count": thread["interruption_count"],
                    "topic_signature": thread.get("topic_signature", []),
                    "delta_intent_keys": thread.get("delta_intent_keys", []),
                },
            ).to_dict()
        )
        for chunk_id in thread.get("user_chunk_ids", []):
            for meta in semantic_meta_by_chunk.get(chunk_id, []):
                edges.append(
                    KnowledgeEdge(
                        edge_id=f"edge-thread-meta-{thread['thread_id']}-{meta['meta_id']}",
                        kind="thread_contains",
                        from_id=f"thread-node-{thread['thread_id']}",
                        to_id=f"meta-node-{meta['meta_id']}",
                        status="provisional",
                        confidence=meta["confidence"],
                        evidence_refs=meta["source_refs"],
                        attributes={},
                    ).to_dict()
                )
        for chunk_id in thread.get("approved_context_chunk_ids", []):
            for meta in context_meta_by_chunk.get(chunk_id, []):
                edges.append(
                    KnowledgeEdge(
                        edge_id=f"edge-thread-context-{thread['thread_id']}-{meta['meta_id']}",
                        kind="thread_context",
                        from_id=f"thread-node-{thread['thread_id']}",
                        to_id=f"meta-node-{meta['meta_id']}",
                        status="provisional",
                        confidence=meta["confidence"],
                        evidence_refs=meta["source_refs"],
                        attributes={},
                    ).to_dict()
                )

    for link in thread_links:
        edge_kind = "thread_continues" if link["kind"] == "continues_across_sources" else "thread_returns"
        edges.append(
            KnowledgeEdge(
                edge_id=link["link_id"],
                kind=edge_kind,
                from_id=f"thread-node-{link['from_thread_id']}",
                to_id=f"thread-node-{link['to_thread_id']}",
                status="provisional",
                confidence=link["confidence"],
                evidence_refs=link.get("source_refs", []),
                attributes={"thread_link_kind": link["kind"]},
            ).to_dict()
        )

    for abstraction in abstraction_rows:
        nodes.append(
            KnowledgeNode(
                node_id=f"abstract-thread-node-{abstraction['abstract_thread_id']}",
                kind="thread_abstraction",
                label=abstraction["label"],
                status="stable" if abstraction["resolution_state"] == "resolved" else "provisional",
                confidence=abstraction["confidence"],
                source_refs=abstraction.get("source_refs", []),
                ref_id=abstraction["abstract_thread_id"],
                attributes={
                    "primary_lens_key": abstraction["primary_lens_key"],
                    "secondary_lens_keys": abstraction.get("secondary_lens_keys", []),
                    "thesis": abstraction["thesis"],
                    "delta_intent_keys": abstraction.get("delta_intent_keys", []),
                    "answer_shape_constraints": abstraction.get("answer_shape_constraints", []),
                    "resolution_state": abstraction["resolution_state"],
                },
            ).to_dict()
        )
    for lens in project_lenses:
        nodes.append(
            KnowledgeNode(
                node_id=f"project-lens-node-{lens['lens_key']}",
                kind="project_lens",
                label=lens["label"],
                status="stable",
                confidence=1.0,
                source_refs=[],
                ref_id=lens["lens_key"],
                attributes={"thesis_hint": lens.get("thesis_hint", ""), "keywords": lens.get("keywords", [])},
            ).to_dict()
        )
    for concept in concept_rows:
        nodes.append(
            KnowledgeNode(
                node_id=f"concept-node-{concept['concept_id']}",
                kind="concept",
                label=concept["label"],
                status=concept.get("status", "provisional"),
                confidence=float(concept.get("confidence", 0.0)),
                source_refs=concept.get("source_refs", []),
                ref_id=concept["concept_id"],
                attributes={
                    "aliases": concept.get("aliases", []),
                    "abstract_pattern": concept.get("abstract_pattern", ""),
                    "transfer_shape": concept.get("transfer_shape", ""),
                    "artifact_refs": concept.get("artifact_refs", []),
                },
            ).to_dict()
        )
    for link in abstraction_links:
        if link["kind"] == "abstracts_to":
            edges.append(
                KnowledgeEdge(
                    edge_id=link["link_id"],
                    kind="abstracts_to",
                    from_id=f"thread-node-{link['from_id']}",
                    to_id=f"abstract-thread-node-{link['to_id']}",
                    status="provisional",
                    confidence=link["confidence"],
                    evidence_refs=link.get("evidence_refs", []),
                    attributes=link.get("attributes", {}),
                ).to_dict()
            )
        elif link["kind"] == "aligned_to_lens":
            edges.append(
                KnowledgeEdge(
                    edge_id=link["link_id"],
                    kind="aligned_to_lens",
                    from_id=f"abstract-thread-node-{link['from_id']}",
                    to_id=f"project-lens-node-{link['to_id']}",
                    status="provisional",
                    confidence=link["confidence"],
                    evidence_refs=link.get("evidence_refs", []),
                    attributes=link.get("attributes", {}),
                ).to_dict()
            )

    for abstraction in abstraction_rows:
        abstraction_meta_ids = set(abstraction.get("semantic_line_meta_ids", [])) | set(abstraction.get("approved_context_meta_ids", []))
        abstraction_lenses = set(abstraction.get("project_lens_keys", []))
        for bubble in bubble_rows:
            bubble_meta_ids = set(bubble.get("meta_ids", []))
            meta_overlap = sorted(abstraction_meta_ids & bubble_meta_ids)
            lens_overlap = sorted(abstraction_lenses & set(bubble.get("project_lens_keys", [])))
            if not meta_overlap and not lens_overlap:
                continue
            edges.append(
                KnowledgeEdge(
                    edge_id=f"edge-abstract-bubble-{hashlib.sha256(':'.join([abstraction['abstract_thread_id'], bubble['bubble_id']]).encode('utf-8')).hexdigest()[:12]}",
                    kind="abstract_supports_bubble",
                    from_id=f"abstract-thread-node-{abstraction['abstract_thread_id']}",
                    to_id=f"bubble-node-{bubble['bubble_id']}",
                    status="provisional",
                    confidence=round(min(0.93, 0.58 + min(0.18, len(meta_overlap) * 0.03) + min(0.12, len(lens_overlap) * 0.04)), 2),
                    evidence_refs=sorted(set(abstraction.get("source_refs", []) + bubble.get("source_refs", []))),
                    attributes={"shared_meta_ids": meta_overlap[:12], "shared_project_lens_keys": lens_overlap},
                ).to_dict()
            )

    grouped_by_token: Dict[str, List[Dict]] = defaultdict(list)
    for meta in meta_rows:
        for token in set(meta.get("attributes", {}).get("tokens", [])):
            grouped_by_token[token].append(meta)

    pair_buckets: Dict[tuple[str, str], Dict] = {}
    filtered_token_groups = 0
    for token, rows in grouped_by_token.items():
        if len(rows) < 2:
            continue
        if len(rows) > 24:
            filtered_token_groups += 1
            continue
        _add_token_pairs(pair_buckets, rows, token)

    grouped_by_source: Dict[str, List[Dict]] = defaultdict(list)
    for meta in meta_rows:
        source_key = "|".join(sorted(set(meta.get("source_refs", []))))
        if source_key:
            grouped_by_source[source_key].append(meta)
    for rows in grouped_by_source.values():
        if len(rows) >= 2:
            _add_source_pairs(pair_buckets, rows)

    context_edge_count = _add_context_embedding_edges(edges, meta_rows, meta_to_threads, meta_to_abstractions)

    for pair, bucket in pair_buckets.items():
        left = bucket["left"]
        right = bucket["right"]
        shared_tokens = sorted(bucket["shared_tokens"])[:8]
        is_fallback = bucket.get("fallback", False)
        if not shared_tokens and not is_fallback:
            continue
        confidence = 0.42 + 0.08 * len(shared_tokens)
        if is_fallback and left["kind"] != right["kind"]:
            confidence += 0.12
        edges.append(
            KnowledgeEdge(
                edge_id=f"edge-{hashlib.sha256(':'.join(pair).encode('utf-8')).hexdigest()[:12]}",
                kind=_edge_kind(left, right),
                from_id=f"meta-node-{left['meta_id']}",
                to_id=f"meta-node-{right['meta_id']}",
                status="provisional",
                confidence=round(min(0.92, confidence), 2),
                evidence_refs=sorted(set(left["source_refs"] + right["source_refs"])),
                attributes={"shared_tokens": shared_tokens, "fallback": is_fallback},
            ).to_dict()
        )

    for edge in concept_edges:
        edges.append(
            KnowledgeEdge(
                edge_id=edge["edge_id"],
                kind=edge["kind"],
                from_id=f"concept-node-{edge['from_id']}",
                to_id=f"concept-node-{edge['to_id']}",
                status=edge.get("status", "provisional"),
                confidence=float(edge.get("confidence", 0.0)),
                evidence_refs=edge.get("source_refs", []),
                attributes={"shared_terms": edge.get("shared_terms", [])},
            ).to_dict()
        )

    write_jsonl(_nodes_path(root), nodes)
    write_jsonl(_edges_path(root), edges)
    substrate_links = _build_substrate_links(source_rows, meta_rows)
    context_links = _build_context_links(substrate_links, edges, bubble_rows, concept_rows, concept_edges)
    capsules = _build_semantic_capsules(meta_rows, abstraction_rows, bubble_rows, concept_rows)
    write_jsonl(_context_links_path(root), context_links)
    write_jsonl(_capsules_path(root), capsules)
    return {
        "source_node_count": len(source_rows),
        "chunk_node_count": 0,
        "bubble_node_count": len(bubble_rows),
        "thread_node_count": len(thread_rows),
        "abstract_thread_node_count": len(abstraction_rows),
        "concept_node_count": len(concept_rows),
        "project_lens_node_count": len(project_lenses),
        "meta_node_count": len(meta_rows),
        "edge_count": len(edges),
        "context_edge_count": context_edge_count,
        "filtered_token_groups": filtered_token_groups,
        "context_link_count": len(context_links),
        "capsule_count": len(capsules),
    }


def select_candidate_pairs(root: Path, limit: int = 36) -> List[Dict]:
    meta_rows = {row["meta_id"]: row for row in load_meta_records(root)}
    candidates = []
    seen = set()
    for edge in load_knowledge_edges(root):
        if edge["kind"] not in {"relates_to", "contradicts", "transfers_to", "requires_review", "context_for"}:
            continue
        left_id = edge["from_id"].replace("meta-node-", "")
        right_id = edge["to_id"].replace("meta-node-", "")
        if left_id not in meta_rows or right_id not in meta_rows:
            continue
        left = meta_rows[left_id]
        right = meta_rows[right_id]
        if set(left["chunk_ids"]) == set(right["chunk_ids"]) and left["kind"] == right["kind"]:
            continue
        pair_key = tuple(sorted([left_id, right_id]))
        if pair_key in seen:
            continue
        seen.add(pair_key)
        shared_tokens = edge.get("attributes", {}).get("shared_tokens", [])
        score = edge["confidence"] + min(0.18, len(shared_tokens) * 0.04)
        if edge["kind"] == "contradicts":
            score += 0.12
        if left["kind"] != right["kind"]:
            score += 0.06
        if edge.get("attributes", {}).get("fallback"):
            score += 0.04
        candidates.append(
            {
                "left": left,
                "right": right,
                "edge_kind": edge["kind"],
                "edge_id": edge["edge_id"],
                "score": round(min(0.99, score), 3),
                "shared_tokens": shared_tokens[:8],
                "evidence_refs": edge.get("evidence_refs", []),
            }
        )
    candidates.sort(key=lambda item: (-item["score"], item["edge_kind"], item["left"]["label"]))
    return candidates[:limit]
