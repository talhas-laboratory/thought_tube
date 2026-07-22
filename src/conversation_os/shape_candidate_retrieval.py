"""Bounded Shape-candidate retrieval for disclosure admission (R-001, R-002)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Optional, Sequence, Set

from .storage import read_json
from .vault_ingest import tokenize


MODULE_ID = "kernel.disclosure.shape_candidate_retrieval"
CONTRACT_VERSION = "1.0"
STRUCTURAL_ADMISSION_THRESHOLD = 0.4
HARD_REJECT_ANTI_MATCH_PENALTY = 0.5

PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "STRUCTURAL_ADMISSION_THRESHOLD",
    "ShapeQuery",
    "ShapeCandidateDecision",
    "AntiMatchDecision",
    "load_shape_retrieval_config",
    "shape_candidate_search_enabled",
    "shape_anti_match_enforcement_enabled",
    "build_shape_query",
    "read_shape_retrieval_context",
    "compute_structural_alignment",
    "evaluate_anti_match",
    "enrich_capsule_admission_with_shape",
    "apply_shape_ranking_adjustment",
    "retrieve_after_canonical_apply",
)
__all__ = list(PUBLIC_API)


@dataclass
class ShapeQuery:
    query_text: str
    branch_id: str = ""
    scope_id: str = ""
    source_refs: List[str] = field(default_factory=list)
    maturity_ceiling: str = "candidate"
    orientation_tokens: Set[str] = field(default_factory=set)

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["orientation_tokens"] = sorted(self.orientation_tokens)
        return payload


@dataclass
class AntiMatchDecision:
    outcome: str
    anti_match_id: str = ""
    reason: str = ""
    penalty: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ShapeCandidateDecision:
    capsule_id: str
    projection_id: str
    structural_score: float
    alignment_features: Dict[str, float]
    admission_signal: str = ""
    anti_match: AntiMatchDecision = field(default_factory=lambda: AntiMatchDecision(outcome="not_applicable"))

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["anti_match"] = self.anti_match.to_dict()
        return payload


def _runtime_config_path(root: Path) -> Path:
    return root / "product" / "inner_world_v1" / "config" / "runtime.json"


def load_shape_retrieval_config(root: Path) -> Dict[str, bool]:
    runtime = read_json(_runtime_config_path(root), default={}) or {}
    knowledge = runtime.get("knowledge", {}) or {}
    return {
        "shape_candidate_search_v1": bool(knowledge.get("shape_candidate_search_v1", False)),
        "shape_anti_match_enforcement_v1": bool(knowledge.get("shape_anti_match_enforcement_v1", False)),
    }


def shape_candidate_search_enabled(root: Path) -> bool:
    return load_shape_retrieval_config(root)["shape_candidate_search_v1"]


def shape_anti_match_enforcement_enabled(root: Path) -> bool:
    return load_shape_retrieval_config(root)["shape_anti_match_enforcement_v1"]


def build_shape_query(
    query: str,
    *,
    branch_id: str = "",
    scope_id: str = "",
    source_refs: Sequence[str] | None = None,
    maturity_ceiling: str = "candidate",
) -> ShapeQuery:
    return ShapeQuery(
        query_text=str(query or "").strip(),
        branch_id=str(branch_id or "").strip(),
        scope_id=str(scope_id or "").strip(),
        source_refs=[str(value).strip() for value in list(source_refs or []) if str(value).strip()],
        maturity_ceiling=str(maturity_ceiling or "candidate").strip() or "candidate",
        orientation_tokens=set(tokenize(query)),
    )


def _matches_branch_scope(row: Mapping[str, Any], *, branch_id: str, scope_id: str) -> bool:
    if branch_id and str(row.get("branch_id", "") or "").strip() not in {"", branch_id}:
        return False
    if scope_id:
        row_scope = str(row.get("scope_id", "") or "").strip()
        row_scope_key = str(row.get("scope_key", "") or "").strip()
        if row_scope and row_scope not in {"", scope_id}:
            if row_scope_key not in {"", scope_id}:
                return False
    return True


def read_shape_retrieval_context(root: Path, shape_query: ShapeQuery) -> Dict[str, Any]:
    from .shape_projection_reader import read_shape_projections

    payload = read_shape_projections(
        root,
        branch_id=shape_query.branch_id,
        scope_id=shape_query.scope_id,
        source_refs=shape_query.source_refs or None,
        include_legacy=True,
        include_anti_match=True,
    )
    if not payload.get("retrieval_allowed"):
        return {
            "result_status": "abstained_dependency_not_ready",
            "readiness_state": str(payload.get("readiness_state", "") or ""),
            "candidate_projections": [],
            "anti_match_projections": [],
            "expansion_count": 0,
            "resolved_bytes": 0,
        }

    legacy = dict(payload.get("legacy", {}) or {})
    candidates = list(legacy.get("candidate_projections", []) or [])
    anti_matches = list(legacy.get("anti_match_projections", []) or [])
    return {
        "result_status": "ready",
        "readiness_state": str(payload.get("readiness_state", "") or ""),
        "candidate_projections": candidates,
        "anti_match_projections": anti_matches,
        "expansion_count": len(candidates) + len(anti_matches),
        "resolved_bytes": 0,
    }


def _projection_tokens(projection: Mapping[str, Any]) -> Set[str]:
    text = " ".join(
        [
            str(projection.get("system_boundary", "") or ""),
            str(projection.get("abstraction_contract", "") or ""),
            str(projection.get("scale", "") or ""),
            str(projection.get("shape_name", "") or ""),
        ]
    )
    return set(tokenize(text))


def _capsule_projection_id(capsule: Mapping[str, Any]) -> str:
    attributes = dict(capsule.get("attributes", {}) or {})
    return str(
        attributes.get("shape_signature_id", "")
        or attributes.get("legacy_shape_id", "")
        or ""
    ).strip()


def _capsule_meta_id(capsule: Mapping[str, Any]) -> str:
    attributes = dict(capsule.get("attributes", {}) or {})
    if str(attributes.get("meta_id", "") or "").strip():
        return str(attributes["meta_id"]).strip()
    if str(capsule.get("ref_type", "") or "") == "meta":
        return str(capsule.get("ref_id", "") or "").strip()
    return ""


def compute_structural_alignment(
    capsule: Mapping[str, Any],
    projection: Mapping[str, Any],
    *,
    orientation_tokens: Set[str],
) -> Dict[str, Any]:
    features: Dict[str, float] = {}
    score = 0.0

    linked_projection_id = _capsule_projection_id(capsule)
    if linked_projection_id and linked_projection_id == str(projection.get("projection_id", "") or "").strip():
        features["projection_link"] = 1.0
        score += 0.45

    source_refs = {str(value).strip() for value in capsule.get("source_refs", []) or [] if str(value).strip()}
    projection_source = str(projection.get("source_ref", "") or "").strip()
    if projection_source and projection_source in source_refs:
        features["source_ref_link"] = 1.0
        score += 0.15

    overlap = orientation_tokens & _projection_tokens(projection)
    if overlap:
        features["orientation_overlap"] = float(len(overlap))
        score += min(0.3, len(overlap) * 0.08)

    shape_name = str(dict(capsule.get("attributes", {}) or {}).get("shape_name", "") or "").strip().lower()
    abstraction = str(projection.get("abstraction_contract", "") or "").lower()
    if shape_name and shape_name in abstraction:
        features["shape_name_match"] = 1.0
        score += 0.2

    return {
        "projection_id": str(projection.get("projection_id", "") or ""),
        "structural_score": round(min(1.0, score), 3),
        "alignment_features": features,
    }


def _best_projection_alignment(
    capsule: Mapping[str, Any],
    projections: Sequence[Mapping[str, Any]],
    *,
    orientation_tokens: Set[str],
) -> Dict[str, Any]:
    best = {
        "projection_id": "",
        "structural_score": 0.0,
        "alignment_features": {},
    }
    for projection in projections:
        alignment = compute_structural_alignment(
            capsule,
            projection,
            orientation_tokens=orientation_tokens,
        )
        if alignment["structural_score"] > best["structural_score"]:
            best = alignment
    return best


def evaluate_anti_match(
    capsule: Mapping[str, Any],
    *,
    anti_matches: Sequence[Mapping[str, Any]],
    branch_id: str = "",
    scope_id: str = "",
    structural_score: float = 0.0,
    anchor_meta_id: str = "",
    positive_admission_signals: Sequence[str] | None = None,
) -> AntiMatchDecision:
    candidate_meta_id = _capsule_meta_id(capsule)
    if not candidate_meta_id:
        return AntiMatchDecision(outcome="not_applicable")

    has_positive_signal = bool(positive_admission_signals) or structural_score > 0.0
    for anti_match in anti_matches:
        if str(anti_match.get("candidate_meta_id", "") or "").strip() != candidate_meta_id:
            continue
        if not _matches_branch_scope(anti_match, branch_id=branch_id, scope_id=scope_id):
            return AntiMatchDecision(
                outcome="not_applicable",
                anti_match_id=str(anti_match.get("projection_id", "") or ""),
                reason="branch_or_scope_incompatible",
            )
        anchor = str(anti_match.get("anchor_meta_id", "") or "").strip()
        if anchor_meta_id and anchor and anchor != anchor_meta_id:
            return AntiMatchDecision(
                outcome="not_applicable",
                anti_match_id=str(anti_match.get("projection_id", "") or ""),
                reason="anchor_mismatch",
            )
        if not has_positive_signal:
            return AntiMatchDecision(
                outcome="not_applicable",
                anti_match_id=str(anti_match.get("projection_id", "") or ""),
                reason="no_positive_shape_candidate",
            )
        penalty = float(anti_match.get("anti_match_penalty", 0.0) or 0.0)
        if penalty >= HARD_REJECT_ANTI_MATCH_PENALTY:
            return AntiMatchDecision(
                outcome="hard_reject",
                anti_match_id=str(anti_match.get("projection_id", "") or ""),
                reason="anti_match_hard_reject",
                penalty=penalty,
            )
        return AntiMatchDecision(
            outcome="penalize",
            anti_match_id=str(anti_match.get("projection_id", "") or ""),
            reason="anti_match_penalty",
            penalty=penalty,
        )
    return AntiMatchDecision(outcome="not_applicable")


def enrich_capsule_admission_with_shape(
    capsule: Mapping[str, Any],
    admission: MutableMapping[str, Any],
    *,
    shape_context: Mapping[str, Any],
    orientation_tokens: Set[str],
    enforce_anti_match: bool,
) -> ShapeCandidateDecision | None:
    if str(shape_context.get("result_status", "") or "") != "ready":
        return None

    projections = list(shape_context.get("candidate_projections", []) or [])
    if not projections:
        return None

    alignment = _best_projection_alignment(capsule, projections, orientation_tokens=orientation_tokens)
    anti_match = evaluate_anti_match(
        capsule,
        anti_matches=list(shape_context.get("anti_match_projections", []) or []),
        branch_id=str(shape_context.get("branch_id", "") or ""),
        scope_id=str(shape_context.get("scope_id", "") or ""),
        structural_score=float(alignment.get("structural_score", 0.0) or 0.0),
        positive_admission_signals=list(admission.get("admission_signals", []) or []),
    )

    decision = ShapeCandidateDecision(
        capsule_id=str(capsule.get("capsule_id", "") or ""),
        projection_id=str(alignment.get("projection_id", "") or ""),
        structural_score=float(alignment.get("structural_score", 0.0) or 0.0),
        alignment_features=dict(alignment.get("alignment_features", {}) or {}),
        anti_match=anti_match,
    )

    if enforce_anti_match and anti_match.outcome == "hard_reject":
        admission["admitted"] = False
        admission["rejection_reason"] = "anti_match_blocked"
        admission["admission_signals"] = list(admission.get("admission_signals", []) or [])
        if "anti_match_blocked" not in admission["admission_signals"]:
            admission["admission_signals"].append("anti_match_blocked")
        admission["shape_candidate"] = decision.to_dict()
        return decision

    if float(alignment.get("structural_score", 0.0) or 0.0) >= STRUCTURAL_ADMISSION_THRESHOLD:
        signals = list(admission.get("admission_signals", []) or [])
        if "structural_shape_match" not in signals:
            signals.append("structural_shape_match")
        admission["admission_signals"] = signals
        admission["admitted"] = True
        admission["rejection_reason"] = ""
        features = dict(admission.get("ranking_features", {}) or {})
        features["structural_shape_match"] = float(alignment["structural_score"]) * 10.0
        admission["ranking_features"] = features
        decision.admission_signal = "structural_shape_match"
    elif "structural_shape_legacy" not in list(admission.get("admission_signals", []) or []):
        features = dict(admission.get("ranking_features", {}) or {})
        if alignment["structural_score"] > 0:
            features["structural_shape_candidate"] = float(alignment["structural_score"])
            admission["ranking_features"] = features

    admission["shape_candidate"] = decision.to_dict()
    return decision


def apply_shape_ranking_adjustment(score: float, shape_decision: Mapping[str, Any] | None) -> float:
    if not shape_decision:
        return score
    anti_match = dict(shape_decision.get("anti_match", {}) or {})
    if anti_match.get("outcome") == "penalize":
        penalty = float(anti_match.get("penalty", 0.0) or 0.0)
        return round(max(0.0, score - penalty * 100.0), 3)
    return score


def retrieve_after_canonical_apply(
    root: Path,
    *,
    canonical_id: str,
    query_text: str,
    branch_id: str = "",
    scope_id: str = "",
    source_refs: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    """Close a golden production trace by reading back the owner receipt and Shape context.

    This is the retrieve step of:
    ingest -> ... -> human approve -> canonical apply -> retrieve
    """
    from conversation_os.shape_population.canonical_port import FoundationCanonicalPort
    from conversation_os.shape_population.execution_context import CAP_PROMOTION_APPLY, service_context

    context = service_context("golden.trace.retrieve", capabilities=(CAP_PROMOTION_APPLY,))
    port = FoundationCanonicalPort(Path(root), bootstrap_profile=True)
    read_back = port.read_back(canonical_id, context=context)
    shape_query = build_shape_query(
        query_text,
        branch_id=branch_id,
        scope_id=scope_id,
        source_refs=list(source_refs or []),
    )
    shape_context = read_shape_retrieval_context(Path(root), shape_query)
    projection = dict(read_back.get("projection") or {})
    return {
        "contract_id": "GoldenTraceRetrieve",
        "schema_version": CONTRACT_VERSION,
        "canonical_id": canonical_id,
        "read_back_status": read_back.get("status"),
        "owner_version": read_back.get("owner_version"),
        "shape_core_id": (projection.get("shape_core") or {}).get("id"),
        "shape_view_id": (projection.get("shape_view") or {}).get("id"),
        "profile_id": projection.get("profile_id"),
        "shape_retrieval": shape_context,
        "query": shape_query.to_dict(),
        "retrieval_ok": str(read_back.get("status") or "") in {"available", "stale"},
    }
