from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from .mtsf_ingest import ENTITY_HINTS
from .mtsf_open_extractor import MERGED_ENTITY_HINTS
from .storage import ensure_dir, read_json, session_dir, utc_now, write_json

MODULE_ID = "kernel.mtsf.embeddings"
CONTRACT_VERSION = "1.0.0"
SEMANTIC_COSINE_THRESHOLD = 0.72
SEMANTIC_KNN = 5
LOCAL_MODEL_ID = "mtsf.concept_anchor.local"
OPENROUTER_MODEL_FALLBACK = "openai/text-embedding-3-small"

PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "SEMANTIC_COSINE_THRESHOLD",
    "SEMANTIC_KNN",
    "LOCAL_MODEL_ID",
    "build_entity_carrier_text",
    "cosine_similarity",
    "embed_texts",
    "embed_entity_carriers",
    "materialize_entity_embeddings",
    "load_session_entity_embeddings",
    "refresh_semantic_adjacency",
    "build_semantic_cluster_candidate_shapes",
    "infer_cluster_cohesion_score",
    "materialize_shape_cluster_cohesion",
    "infer_discovered_entity_shape_id",
)
__all__ = list(PUBLIC_API)

_CONCEPT_BRIDGES = (
    ("context field", "subconscious architecture"),
    ("latent manifold", "metaphysical zone"),
    ("effective topology", "liminal space"),
    ("synthetic subconscious", "subconscious architecture"),
    ("thought ocean", "thought tube"),
    ("subconscious maze", "subconscious architecture"),
    ("liminal corridor", "liminal space"),
    ("prior context", "context field"),
)


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def _term_activation(text: str, term: str) -> float:
    lowered = _normalize_text(text)
    needle = _normalize_text(term)
    if not needle:
        return 0.0
    if needle in lowered:
        return min(1.0, 0.55 + 0.08 * math.log1p(len(needle)))
    tokens = set(re.findall(r"[a-z0-9]+", needle))
    if not tokens:
        return 0.0
    hay_tokens = set(re.findall(r"[a-z0-9]+", lowered))
    overlap = len(tokens & hay_tokens) / len(tokens)
    if overlap >= 0.66:
        return 0.45 + 0.35 * overlap
    return 0.0


def _build_concept_anchors() -> List[Dict[str, Any]]:
    anchors: List[Dict[str, Any]] = []
    seen_ids: Set[str] = set()

    for hint in MERGED_ENTITY_HINTS:
        anchor_id = str(hint.get("proposed_id", "")).replace("entity-", "anchor-")
        if not anchor_id or anchor_id in seen_ids:
            continue
        seen_ids.add(anchor_id)
        terms = list(hint.get("keywords", ()))
        terms.append(str(hint.get("name", "")))
        terms.extend(str(item) for item in hint.get("stable_identity", []))
        anchors.append({"anchor_id": anchor_id, "terms": [term for term in terms if term]})

    for left, right in _CONCEPT_BRIDGES:
        for label in (left, right):
            anchor_id = "anchor-" + re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")
            if anchor_id in seen_ids:
                continue
            seen_ids.add(anchor_id)
            anchors.append({"anchor_id": anchor_id, "terms": [label]})

    bridge_groups: List[Set[str]] = []
    for left, right in _CONCEPT_BRIDGES:
        left_id = "anchor-" + re.sub(r"[^a-z0-9]+", "-", left.lower()).strip("-")
        right_id = "anchor-" + re.sub(r"[^a-z0-9]+", "-", right.lower()).strip("-")
        bridge_groups.append({left_id, right_id})

    return anchors


_CONCEPT_ANCHORS = _build_concept_anchors()
_BRIDGE_GROUPS = [
    {
        "anchor-" + re.sub(r"[^a-z0-9]+", "-", left.lower()).strip("-"),
        "anchor-" + re.sub(r"[^a-z0-9]+", "-", right.lower()).strip("-"),
    }
    for left, right in _CONCEPT_BRIDGES
]


def build_entity_carrier_text(entity: Dict[str, Any]) -> str:
    parts: List[str] = []
    name = str(entity.get("name", "")).strip()
    if name:
        parts.append(name)
    stable_identity = entity.get("stable_identity", [])
    if isinstance(stable_identity, list):
        parts.extend(str(item).strip() for item in stable_identity if str(item).strip())
    evidence = entity.get("evidence", {}) or {}
    spans = evidence.get("spans", []) if isinstance(evidence, dict) else []
    if isinstance(spans, list):
        parts.extend(str(span).strip() for span in spans if str(span).strip())
    return " | ".join(parts)


def cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    dot = sum(a * b for a, b in zip(left, right))
    left_mag = math.sqrt(sum(a * a for a in left))
    right_mag = math.sqrt(sum(b * b for b in right))
    if left_mag == 0.0 or right_mag == 0.0:
        return 0.0
    return dot / (left_mag * right_mag)


def _normalize_vector(vector: Sequence[float]) -> List[float]:
    magnitude = math.sqrt(sum(value * value for value in vector))
    if magnitude == 0.0:
        return [0.0 for _ in vector]
    return [value / magnitude for value in vector]


def _concept_anchor_embed(text: str) -> List[float]:
    activations = [
        max((_term_activation(text, term) for term in anchor["terms"]), default=0.0)
        for anchor in _CONCEPT_ANCHORS
    ]
    for group in _BRIDGE_GROUPS:
        indices = [
            index
            for index, anchor in enumerate(_CONCEPT_ANCHORS)
            if anchor["anchor_id"] in group
        ]
        if len(indices) < 2:
            continue
        peak = max(activations[index] for index in indices)
        if peak <= 0.0:
            continue
        blended = min(1.0, peak * 0.92)
        for index in indices:
            activations[index] = max(activations[index], blended)
    return _normalize_vector(activations)


def _openrouter_embed(root: Path, texts: Sequence[str]) -> Optional[List[List[float]]]:
    try:
        from .worldbuilding_studio import OpenRouterEmbeddingClient

        client = OpenRouterEmbeddingClient.from_runtime(root)
        if client is None:
            return None
        documents = [{"text": text, "modality": "text"} for text in texts]
        embedded = client.embed_documents(documents, input_type="search_document")
        vectors = [list(row.get("embedding", [])) for row in embedded]
        if not vectors or not vectors[0]:
            return None
        return vectors
    except Exception:
        return None


def embed_texts(root: Path, texts: Sequence[str]) -> Tuple[List[List[float]], str]:
    clean_texts = [str(text) for text in texts]
    remote_vectors = _openrouter_embed(root, clean_texts)
    if remote_vectors and len(remote_vectors) == len(clean_texts):
        return remote_vectors, OPENROUTER_MODEL_FALLBACK
    return [_concept_anchor_embed(text) for text in clean_texts], LOCAL_MODEL_ID


def embed_entity_carriers(
    root: Path,
    session_id: str,
    draft: Dict[str, Any],
) -> Dict[str, Any]:
    entities = list(draft.get("entities", []))
    carriers = [build_entity_carrier_text(entity) for entity in entities]
    if not carriers:
        return {
            "session_id": session_id,
            "draft_id": draft.get("draft_id"),
            "model": LOCAL_MODEL_ID,
            "generated_at": utc_now(),
            "entities": [],
        }

    vectors, model_id = embed_texts(root, carriers)
    rows: List[Dict[str, Any]] = []
    for entity, carrier, vector in zip(entities, carriers, vectors):
        entity_id = str(entity.get("proposed_id", ""))
        if not entity_id:
            continue
        rows.append(
            {
                "entity_id": entity_id,
                "vector": vector,
                "source_text": carrier,
                "embedding_source": "openrouter" if model_id != LOCAL_MODEL_ID else "concept_anchor",
            }
        )
    return {
        "session_id": session_id,
        "draft_id": draft.get("draft_id"),
        "model": model_id,
        "generated_at": utc_now(),
        "entities": rows,
    }


def materialize_entity_embeddings(
    root: Path,
    session_id: str,
    draft: Dict[str, Any],
) -> Dict[str, Any]:
    payload = embed_entity_carriers(root, session_id, draft)
    artifact_dir = session_dir(root, session_id) / "mtsf"
    ensure_dir(artifact_dir)
    artifact_path = artifact_dir / "entity_embeddings.json"
    write_json(artifact_path, payload)
    return {
        "session_id": session_id,
        "entity_count": len(payload.get("entities", [])),
        "artifact_refs": {"mtsf_entity_embeddings": str(artifact_path)},
        "model": payload.get("model"),
    }


def load_session_entity_embeddings(root: Path, session_id: str) -> Dict[str, Dict[str, Any]]:
    path = session_dir(root, session_id) / "mtsf" / "entity_embeddings.json"
    payload = read_json(path, default={})
    rows = payload.get("entities", [])
    indexed: Dict[str, Dict[str, Any]] = {}
    if isinstance(rows, list):
        for row in rows:
            if not isinstance(row, dict):
                continue
            entity_id = str(row.get("entity_id", ""))
            if entity_id:
                indexed[entity_id] = row
    return indexed


def _parse_global_node_id(global_node_id: str) -> Tuple[str, str]:
    if "::" not in global_node_id:
        return "", str(global_node_id)
    session_id, local_node_id = global_node_id.split("::", 1)
    return session_id, local_node_id


def refresh_semantic_adjacency(
    graph: Dict[str, Any],
    root: Path,
    *,
    cosine_threshold: float = SEMANTIC_COSINE_THRESHOLD,
    knn: int = SEMANTIC_KNN,
) -> Dict[str, Any]:
    nodes = graph.get("nodes", {})
    entity_vectors: Dict[str, List[float]] = {}
    entity_sessions: Dict[str, str] = {}

    for node_id, node in nodes.items():
        if str(node.get("kind", "")) != "entity":
            continue
        session_id, local_id = _parse_global_node_id(str(node_id))
        if not session_id:
            session_id = str(node.get("source_session_id", ""))
            local_id = str(node.get("local_id", node_id))
        embeddings = load_session_entity_embeddings(root, session_id)
        row = embeddings.get(local_id)
        if not row:
            continue
        vector = row.get("vector", [])
        if not isinstance(vector, list) or not vector:
            continue
        entity_vectors[str(node_id)] = [float(value) for value in vector]
        entity_sessions[str(node_id)] = session_id

    semantic: Dict[str, Set[str]] = {}
    overlays: Dict[str, Dict[str, Any]] = {}
    existing_semantic = graph.get("adjacency", {}).get("semantic", {})
    if isinstance(existing_semantic, dict):
        for node_id, neighbors in existing_semantic.items():
            semantic.setdefault(str(node_id), set()).update(str(neighbor) for neighbor in neighbors)

    node_ids = sorted(entity_vectors.keys())

    for index, left_id in enumerate(node_ids):
        left_vector = entity_vectors[left_id]
        scored: List[Tuple[float, str]] = []
        for right_id in node_ids:
            if right_id == left_id:
                continue
            cosine = cosine_similarity(left_vector, entity_vectors[right_id])
            if cosine >= cosine_threshold:
                scored.append((cosine, right_id))
        scored.sort(key=lambda item: (-item[0], item[1]))
        for cosine, right_id in scored[:knn]:
            semantic.setdefault(left_id, set()).add(right_id)
            semantic.setdefault(right_id, set()).add(left_id)
            edge_key = f"{left_id}::{right_id}" if left_id < right_id else f"{right_id}::{left_id}"
            overlays[edge_key] = {
                "cosine": round(cosine, 4),
                "source": "entity_embedding_knn",
                "left_session_id": entity_sessions.get(left_id, ""),
                "right_session_id": entity_sessions.get(right_id, ""),
            }

    graph.setdefault("adjacency", {})["semantic"] = {
        node_id: sorted(neighbors) for node_id, neighbors in sorted(semantic.items())
    }
    graph.setdefault("overlays", {})["semantic_edges"] = overlays
    return graph


def _relation_components(
    entities: Sequence[Dict[str, Any]],
    relations: Sequence[Dict[str, Any]],
) -> List[Set[str]]:
    entity_ids = {str(row.get("proposed_id", "")) for row in entities if row.get("proposed_id")}
    adjacency: Dict[str, Set[str]] = {entity_id: set() for entity_id in entity_ids}
    for relation in relations:
        if str(relation.get("level", "")) not in {"", "entity_entity"}:
            continue
        source = str(relation.get("source_ref", ""))
        target = str(relation.get("target_ref", ""))
        if source in adjacency and target in adjacency:
            adjacency[source].add(target)
            adjacency[target].add(source)

    visited: Set[str] = set()
    components: List[Set[str]] = []
    for entity_id in sorted(entity_ids):
        if entity_id in visited:
            continue
        stack = [entity_id]
        component: Set[str] = set()
        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)
            component.add(current)
            stack.extend(neighbor for neighbor in adjacency.get(current, set()) if neighbor not in visited)
        if len(component) >= 2:
            components.append(component)
    return components


def _cluster_cohesion(vectors: Sequence[Sequence[float]]) -> float:
    if len(vectors) < 2:
        return 0.0
    scores: List[float] = []
    for left_index, left in enumerate(vectors):
        for right in vectors[left_index + 1 :]:
            scores.append(cosine_similarity(left, right))
    return round(sum(scores) / len(scores), 4) if scores else 0.0


def build_semantic_cluster_candidate_shapes(
    *,
    root: Path,
    text: str,
    entities: Sequence[Dict[str, Any]],
    relations: Sequence[Dict[str, Any]],
    qualities: Sequence[Dict[str, Any]],
    existing_shapes: Optional[Sequence[Dict[str, Any]]] = None,
    min_cluster_size: int = 2,
) -> List[Dict[str, Any]]:
    if len(entities) < min_cluster_size:
        return list(existing_shapes or [])

    carriers = [build_entity_carrier_text(entity) for entity in entities]
    vectors, _model = embed_texts(root, carriers)
    entity_by_id = {str(entity.get("proposed_id", "")): entity for entity in entities}
    vector_by_id = {
        str(entity.get("proposed_id", "")): vector
        for entity, vector in zip(entities, vectors)
        if entity.get("proposed_id")
    }

    shapes: List[Dict[str, Any]] = list(existing_shapes or [])
    existing_ids = {str(shape.get("proposed_id", "")) for shape in shapes if shape.get("proposed_id")}
    quality_refs = [str(row.get("quality_id", "")) for row in qualities if row.get("quality_id")]

    for index, component in enumerate(_relation_components(entities, relations), start=1):
        members = [entity_by_id[entity_id] for entity_id in sorted(component) if entity_id in entity_by_id]
        if len(members) < min_cluster_size:
            continue
        member_vectors = [vector_by_id[str(member.get("proposed_id", ""))] for member in members]
        cohesion = _cluster_cohesion(member_vectors)
        names = [str(member.get("name", "")) for member in members if member.get("name")]
        proposed_id = f"cand-semantic-cluster-{index}"
        if proposed_id in existing_ids:
            continue
        shapes.append(
            {
                "proposed_id": proposed_id,
                "possible_names": [f"semantic cluster: {' + '.join(names[:3])}"],
                "relational_configuration": " + ".join(names[:3]) + " held together by relation glue",
                "entity_refs": [str(member.get("proposed_id", "")) for member in members],
                "quality_refs": quality_refs[:3],
                "confidence": min(0.84, 0.68 + 0.04 * len(members) + 0.06 * cohesion),
                "evidence": {"spans": [text.strip()[:180]]},
                "provenance": {
                    "source": "semantic_cluster",
                    "cluster_cohesion": cohesion,
                    "cluster_size": len(members),
                },
            }
        )
        existing_ids.add(proposed_id)

    if not any(str(shape.get("provenance", {}).get("source", "")) == "semantic_cluster" for shape in shapes):
        if len(entities) >= min_cluster_size and relations:
            member_vectors = vectors[: len(entities)]
            cohesion = _cluster_cohesion(member_vectors)
            names = [str(entity.get("name", "")) for entity in entities[:3] if entity.get("name")]
            proposed_id = "cand-semantic-cluster-session"
            if proposed_id not in existing_ids:
                shapes.append(
                    {
                        "proposed_id": proposed_id,
                        "possible_names": [f"semantic cluster: {' + '.join(names)}"],
                        "relational_configuration": " + ".join(names) + " co-occur in the same sensory scene",
                        "entity_refs": [
                            str(entity.get("proposed_id", ""))
                            for entity in entities[:4]
                            if entity.get("proposed_id")
                        ],
                        "quality_refs": quality_refs[:3],
                        "confidence": min(0.82, 0.7 + 0.05 * len(entities)),
                        "evidence": {"spans": [text.strip()[:180]]},
                        "provenance": {
                            "source": "semantic_cluster",
                            "cluster_cohesion": cohesion,
                            "cluster_size": len(entities),
                        },
                    }
                )
    return shapes


def infer_cluster_cohesion_score(draft: Dict[str, Any]) -> float:
    scores: List[float] = []
    for shape in draft.get("candidate_shapes", []):
        provenance = shape.get("provenance", {})
        if str(provenance.get("source", "")) != "semantic_cluster":
            continue
        scores.append(float(provenance.get("cluster_cohesion", 0.0)))
    if scores:
        return max(scores)
    entities = list(draft.get("entities", []))
    if len(entities) < 2:
        return 0.0
    carriers = [build_entity_carrier_text(entity) for entity in entities]
    vectors, _model = embed_texts(Path("."), carriers)
    return _cluster_cohesion(vectors)


def materialize_shape_cluster_cohesion(
    root: Path,
    session_id: str,
    draft: Dict[str, Any],
) -> Dict[str, Any]:
    score = infer_cluster_cohesion_score(draft)
    cluster_count = sum(
        1
        for shape in draft.get("candidate_shapes", [])
        if str(shape.get("provenance", {}).get("source", "")) == "semantic_cluster"
    )
    payload = {
        "session_id": session_id,
        "draft_id": draft.get("draft_id"),
        "score": round(score, 4),
        "cluster_count": cluster_count,
        "generated_at": utc_now(),
    }
    artifact_dir = session_dir(root, session_id) / "mtsf"
    ensure_dir(artifact_dir)
    artifact_path = artifact_dir / "shape_cluster_cohesion.json"
    write_json(artifact_path, payload)
    return {
        "session_id": session_id,
        "score": payload["score"],
        "artifact_refs": {"mtsf_shape_cluster_cohesion": str(artifact_path)},
    }


def infer_discovered_entity_shape_id(
    entity_row: Dict[str, Any],
    draft: Dict[str, Any],
    *,
    min_cluster_cohesion: float = 0.7,
) -> str:
    entity_id = str(entity_row.get("proposed_id", ""))
    entity_name = str(entity_row.get("name", "")).lower()
    cohesion = infer_cluster_cohesion_score(draft)
    if cohesion < min_cluster_cohesion:
        return "shape-observed"

    best_shape_id = ""
    best_score = -1.0
    for shape in draft.get("candidate_shapes", []):
        entity_refs = {str(ref) for ref in shape.get("entity_refs", [])}
        if entity_id not in entity_refs:
            continue
        proposed_id = str(shape.get("proposed_id", ""))
        shape_id = proposed_id.replace("cand-", "shape-", 1) if proposed_id.startswith("cand-") else proposed_id
        score = float(shape.get("confidence", 0.0))
        fragment = proposed_id.replace("cand-", "").replace("_", "-")
        if entity_name and any(token in fragment for token in entity_name.split()):
            score += 0.2
        if str(shape.get("provenance", {}).get("source", "")) == "semantic_cluster":
            score += 0.15
        if score > best_score:
            best_score = score
            best_shape_id = shape_id
    return best_shape_id or "shape-observed"
