"""Post-candidate comparison retrieval for Shape population."""

from __future__ import annotations

import math
import re
from dataclasses import asdict, dataclass, field
from typing import Any, Mapping, Protocol, Sequence

from conversation_os.shape_population.contracts import COMPARISON_RELATIONS, ValidationError, fingerprint_payload
from conversation_os.shape_population.execution_context import CAP_COMPARISON_READ, ExecutionContext
from conversation_os.shape_population.storage import PopulationStore

MODULE_ID = "kernel.shape_population.comparison"
CONTRACT_VERSION = "1.0.0"
DEFAULT_POLICY_VERSION = "lexical-comparison-v1"
MAX_LIMIT = 25
PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "DEFAULT_POLICY_VERSION",
    "ComparisonRetriever",
    "ComparisonNeighborResult",
    "ComparisonSet",
    "DefaultLexicalComparisonRetriever",
    "find_neighbors",
)
__all__ = list(PUBLIC_API)


@dataclass(frozen=True)
class ComparisonNeighborResult:
    """A non-authoritative retrieval neighbor with auditable score provenance."""

    candidate_id: str
    relation_hint: str
    title: str
    statement: str
    boundary: str
    evidence_refs: list[dict[str, Any]]
    status: str
    score: float
    score_components: dict[str, float]
    provenance: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        if payload["relation_hint"] not in COMPARISON_RELATIONS:
            raise ValidationError(f"invalid relation_hint: {payload['relation_hint']}")
        return payload


@dataclass(frozen=True)
class ComparisonSet:
    candidate_id: str
    policy_version: str
    comparison_set_version: str
    retriever_profile: dict[str, Any]
    neighbors: list[ComparisonNeighborResult] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "policy_version": self.policy_version,
            "comparison_set_version": self.comparison_set_version,
            "retriever_profile": dict(self.retriever_profile),
            "neighbors": [neighbor.to_dict() for neighbor in self.neighbors],
            "note": "Comparison retrieval is provisional evidence only; it never decides equivalence, merge, or promotion.",
        }


class ComparisonRetriever(Protocol):
    """Port for ranked Shape comparison reads."""

    def retrieve(
        self,
        candidate: Mapping[str, Any],
        *,
        store: PopulationStore,
        limit: int,
        policy_version: str,
    ) -> ComparisonSet:
        ...


def _tokens(value: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]+", value.lower()) if len(token) > 2}


def _jaccard(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def _text_for_candidate(candidate: Mapping[str, Any]) -> str:
    pieces: list[str] = [
        str(candidate.get("title") or ""),
        str(candidate.get("statement") or ""),
        str(candidate.get("boundary") or ""),
        str(candidate.get("mechanism") or ""),
        " ".join(str(item) for item in (candidate.get("dimensions") or [])),
        " ".join(str(item) for item in (candidate.get("relations") or [])),
    ]
    for ref in candidate.get("evidence_refs") or []:
        if isinstance(ref, Mapping):
            pieces.extend(str(ref.get(key) or "") for key in ("source_id", "segment_id", "block_id"))
    return " ".join(pieces)


def _relation_hint(overall: float, candidate_tokens: set[str], neighbor_tokens: set[str]) -> str:
    conflict = {"not", "unlike", "opposite", "conflict", "contradict", "versus", "anti"}
    if candidate_tokens & conflict or neighbor_tokens & conflict:
        return "possibly_conflicting"
    if overall >= 0.55:
        return "possible_same"
    if overall >= 0.18:
        return "possibly_adjacent"
    return "possibly_distinct"


class DefaultLexicalComparisonRetriever:
    """Deterministic local retriever used until canonical semantic indexes exist."""

    profile_name = "default_lexical_candidate_retriever"
    profile_version = "1.0.0"

    def retrieve(
        self,
        candidate: Mapping[str, Any],
        *,
        store: PopulationStore,
        limit: int,
        policy_version: str,
    ) -> ComparisonSet:
        candidate_id = str(candidate.get("candidate_id") or "")
        candidate_tokens = _tokens(_text_for_candidate(candidate))
        candidate_title_tokens = _tokens(str(candidate.get("title") or ""))
        candidate_dimensions = _tokens(" ".join(str(item) for item in (candidate.get("dimensions") or [])))
        scored: list[ComparisonNeighborResult] = []

        for other in store.list_candidates():
            other_id = str(other.get("candidate_id") or "")
            if not other_id or other_id == candidate_id:
                continue
            other_tokens = _tokens(_text_for_candidate(other))
            title_overlap = _jaccard(candidate_title_tokens, _tokens(str(other.get("title") or "")))
            dimension_overlap = _jaccard(
                candidate_dimensions,
                _tokens(" ".join(str(item) for item in (other.get("dimensions") or []))),
            )
            lexical_overlap = _jaccard(candidate_tokens, other_tokens)
            evidence_overlap = _jaccard(
                {str(ref.get("source_id") or "") for ref in candidate.get("evidence_refs") or [] if isinstance(ref, Mapping)},
                {str(ref.get("source_id") or "") for ref in other.get("evidence_refs") or [] if isinstance(ref, Mapping)},
            )
            score = (lexical_overlap * 0.60) + (title_overlap * 0.20) + (dimension_overlap * 0.15) + (evidence_overlap * 0.05)
            if not math.isfinite(score):
                score = 0.0
            components = {
                "lexical_overlap": round(lexical_overlap, 6),
                "title_overlap": round(title_overlap, 6),
                "dimension_overlap": round(dimension_overlap, 6),
                "evidence_source_overlap": round(evidence_overlap, 6),
            }
            scored.append(
                ComparisonNeighborResult(
                    candidate_id=other_id,
                    relation_hint=_relation_hint(score, candidate_tokens, other_tokens),
                    title=str(other.get("title") or ""),
                    statement=str(other.get("statement") or ""),
                    boundary=str(other.get("boundary") or ""),
                    evidence_refs=[dict(item) for item in (other.get("evidence_refs") or [])],
                    status=str(other.get("status") or ""),
                    score=round(score, 6),
                    score_components=components,
                    provenance={
                        "retriever": self.profile_name,
                        "retriever_version": self.profile_version,
                        "policy_version": policy_version,
                        "source": "shape_population_store.candidates",
                        "candidate_status": str(other.get("status") or ""),
                    },
                )
            )

        scored.sort(key=lambda item: (-item.score, item.candidate_id))
        neighbors = scored[:limit]
        version = fingerprint_payload(
            {
                "candidate_id": candidate_id,
                "policy_version": policy_version,
                "retriever": self.profile_name,
                "neighbors": [
                    {
                        "candidate_id": item.candidate_id,
                        "score": item.score,
                        "relation_hint": item.relation_hint,
                    }
                    for item in neighbors
                ],
            }
        )
        return ComparisonSet(
            candidate_id=candidate_id,
            policy_version=policy_version,
            comparison_set_version=f"cmp-{version[:20]}",
            retriever_profile={"name": self.profile_name, "version": self.profile_version},
            neighbors=neighbors,
        )


def _persist_comparison_set_if_supported(store: PopulationStore, comparison_set: ComparisonSet) -> None:
    payload = comparison_set.to_dict()
    for method_name in ("put_comparison_set", "record_comparison_set", "persist_comparison_set"):
        method = getattr(store, method_name, None)
        if callable(method):
            method(payload)
            return
    method = getattr(store, "put_comparison_set_version", None)
    if callable(method):
        method(comparison_set.candidate_id, comparison_set.comparison_set_version, payload)


def find_neighbors(
    candidate_id: str,
    *,
    store: PopulationStore,
    context: ExecutionContext,
    retriever: ComparisonRetriever | None = None,
    limit: int = 5,
    policy_version: str = DEFAULT_POLICY_VERSION,
) -> dict[str, Any]:
    """Retrieve bounded non-authoritative neighbors after candidate persistence."""

    context.require_capability(CAP_COMPARISON_READ)
    if not str(policy_version or "").strip():
        raise ValidationError("policy_version required")
    if limit < 1:
        raise ValidationError("limit must be >= 1")
    bounded_limit = min(int(limit), MAX_LIMIT)
    candidate = store.get_candidate(candidate_id)
    if candidate is None:
        raise ValidationError("comparison unavailable before durable candidate acceptance")
    comparison_set = (retriever or DefaultLexicalComparisonRetriever()).retrieve(
        candidate,
        store=store,
        limit=bounded_limit,
        policy_version=policy_version,
    )
    _persist_comparison_set_if_supported(store, comparison_set)
    return comparison_set.to_dict()
