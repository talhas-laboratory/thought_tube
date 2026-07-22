"""Bounded Shape-candidate retrieval for disclosure admission (R-001, R-002).

T10-06: Pattern derivation and typed Pattern/AntiMatch/transfer records live on
this owner so structural intelligence stays fail-closed and never merges Shapes
merely because they instantiate a Pattern.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Optional, Sequence, Set

from .storage import read_json, utc_now
from .vault_ingest import tokenize


MODULE_ID = "kernel.disclosure.shape_candidate_retrieval"
CONTRACT_VERSION = "1.0"
PATTERN_REASONING_CONTRACT_VERSION = "1.0"
STRUCTURAL_ADMISSION_THRESHOLD = 0.4
HARD_REJECT_ANTI_MATCH_PENALTY = 0.5
PATTERN_RECORD_KINDS = (
    "candidate_match",
    "validated_membership",
    "anti_match",
    "transfer_hypothesis",
    "rejected_analogy",
)

PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "PATTERN_REASONING_CONTRACT_VERSION",
    "STRUCTURAL_ADMISSION_THRESHOLD",
    "PATTERN_RECORD_KINDS",
    "ShapeQuery",
    "ShapeCandidateDecision",
    "AntiMatchDecision",
    "InvariantAssessment",
    "PatternRecord",
    "PatternReasoningRecord",
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
    "derive_pattern_from_shapes",
    "classify_shape_pair",
    "revise_anti_match_record",
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
class InvariantAssessment:
    invariant_id: str
    status: str  # preserved | violated | unknown
    evidence_refs: List[str] = field(default_factory=list)
    abstraction_contract: str = ""

    def to_dict(self) -> Dict[str, Any]:
        if self.status not in {"preserved", "violated", "unknown"}:
            raise ValueError(f"invalid invariant status: {self.status}")
        return asdict(self)


@dataclass
class PatternRecord:
    """Derived abstraction over a declared Shape population (never authoritative merge)."""

    pattern_id: str
    shape_population_refs: List[str]
    role_mappings: List[Dict[str, Any]] = field(default_factory=list)
    invariants: List[InvariantAssessment] = field(default_factory=list)
    abstracted_values: List[str] = field(default_factory=list)
    boundary_correspondences: List[Dict[str, Any]] = field(default_factory=list)
    scale_correspondences: List[Dict[str, Any]] = field(default_factory=list)
    mechanism_differences: List[str] = field(default_factory=list)
    transfer_limits: List[str] = field(default_factory=list)
    branch_id: str = ""
    scope_id: str = ""
    merge_shapes_forbidden: bool = True
    contract_version: str = PATTERN_REASONING_CONTRACT_VERSION

    def to_dict(self) -> Dict[str, Any]:
        if not self.shape_population_refs:
            raise ValueError("Pattern requires declared shape_population_refs")
        if not self.merge_shapes_forbidden:
            raise ValueError("Patterns must keep merge_shapes_forbidden=True")
        return {
            "contract_id": "PatternRecord",
            "contract_version": self.contract_version,
            "pattern_id": self.pattern_id,
            "shape_population_refs": list(self.shape_population_refs),
            "role_mappings": [dict(item) for item in self.role_mappings],
            "invariants": [item.to_dict() for item in self.invariants],
            "abstracted_values": list(self.abstracted_values),
            "boundary_correspondences": [dict(item) for item in self.boundary_correspondences],
            "scale_correspondences": [dict(item) for item in self.scale_correspondences],
            "mechanism_differences": list(self.mechanism_differences),
            "transfer_limits": list(self.transfer_limits),
            "branch_id": self.branch_id,
            "scope_id": self.scope_id,
            "merge_shapes_forbidden": True,
            "note": "Pattern is a derived abstraction; instantiating Shapes must not be merged from Pattern alone.",
        }


@dataclass
class PatternReasoningRecord:
    """One of the separated Pattern reasoning record kinds."""

    record_kind: str
    record_id: str
    left_shape_ref: str
    right_shape_ref: str
    pattern_id: str = ""
    branch_id: str = ""
    scope_id: str = ""
    holds_where: List[str] = field(default_factory=list)
    breaks_where: List[str] = field(default_factory=list)
    abstracts: List[str] = field(default_factory=list)
    evidence_refs: List[str] = field(default_factory=list)
    revisable: bool = True
    disposition: str = "active"  # active | revised | withdrawn
    reason: str = ""
    merge_shapes_forbidden: bool = True
    contract_version: str = PATTERN_REASONING_CONTRACT_VERSION

    def to_dict(self) -> Dict[str, Any]:
        if self.record_kind not in PATTERN_RECORD_KINDS:
            raise ValueError(f"invalid pattern record kind: {self.record_kind}")
        if not self.merge_shapes_forbidden:
            raise ValueError("Pattern reasoning records must keep merge_shapes_forbidden=True")
        return {
            "contract_id": "PatternReasoningRecord",
            "contract_version": self.contract_version,
            "record_kind": self.record_kind,
            "record_id": self.record_id,
            "left_shape_ref": self.left_shape_ref,
            "right_shape_ref": self.right_shape_ref,
            "pattern_id": self.pattern_id,
            "branch_id": self.branch_id,
            "scope_id": self.scope_id,
            "holds_where": list(self.holds_where),
            "breaks_where": list(self.breaks_where),
            "abstracts": list(self.abstracts),
            "evidence_refs": list(self.evidence_refs),
            "revisable": bool(self.revisable),
            "disposition": self.disposition,
            "reason": self.reason,
            "merge_shapes_forbidden": True,
        }


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


def _shape_ref(shape: Mapping[str, Any], *, fallback_prefix: str) -> str:
    for key in ("shape_id", "canonical_id", "projection_id", "signature_id", "id", "meta_id"):
        value = str(shape.get(key, "") or "").strip()
        if value:
            return value
    title = str(shape.get("title") or shape.get("shape_name") or shape.get("label") or "").strip()
    if title:
        digest = hashlib.sha256(title.encode("utf-8")).hexdigest()[:12]
        return f"{fallback_prefix}:{digest}"
    raise ValueError("shape population member requires an identity ref")


def _shape_roles(shape: Mapping[str, Any]) -> List[str]:
    roles: list[str] = []
    for entity in list(shape.get("entities") or []):
        if not isinstance(entity, Mapping):
            continue
        role = str(entity.get("role") or entity.get("node_type") or entity.get("label") or "").strip()
        if role:
            roles.append(role)
    for role in list(shape.get("roles") or []):
        text = str(role or "").strip()
        if text:
            roles.append(text)
    return roles


def _shape_token_set(shape: Mapping[str, Any]) -> Set[str]:
    pieces = [
        str(shape.get("title") or ""),
        str(shape.get("summary") or ""),
        str(shape.get("statement") or ""),
        str(shape.get("system_boundary") or shape.get("boundary") or ""),
        str(shape.get("mechanism") or ""),
        " ".join(_shape_roles(shape)),
        " ".join(str(item) for item in (shape.get("dimensions") or [])),
    ]
    for candidate in list(shape.get("candidate_shapes") or []):
        if isinstance(candidate, Mapping):
            pieces.append(str(candidate.get("shape_name") or ""))
            pieces.append(str(candidate.get("rationale") or ""))
    return set(tokenize(" ".join(pieces)))


def _overlap_ratio(left: Set[str], right: Set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def derive_pattern_from_shapes(
    shapes: Sequence[Mapping[str, Any]],
    *,
    pattern_id: str = "",
    branch_id: str = "",
    scope_id: str = "",
    required_invariants: Sequence[str] | None = None,
) -> Dict[str, Any]:
    """Derive a Pattern over a declared Shape population.

    Patterns are abstractions only: merge_shapes_forbidden remains True.
    """
    members = [dict(shape) for shape in shapes if isinstance(shape, Mapping)]
    if len(members) < 2:
        raise ValueError("Pattern derivation requires at least two declared Shape population members")

    refs = [_shape_ref(shape, fallback_prefix="shape") for shape in members]
    role_sets = [set(_shape_roles(shape)) for shape in members]
    shared_roles = set.intersection(*role_sets) if role_sets and all(role_sets) else set()
    role_mappings = [
        {
            "role": role,
            "shape_refs": refs,
            "status": "preserved",
        }
        for role in sorted(shared_roles)
    ]

    token_sets = [_shape_token_set(shape) for shape in members]
    shared_tokens = set.intersection(*token_sets) if token_sets else set()
    abstracted_values = sorted(token for token in shared_tokens if len(token) > 3)[:24]

    boundaries = [
        str(shape.get("system_boundary") or shape.get("boundary") or "").strip() for shape in members
    ]
    boundary_correspondences = []
    if all(boundaries):
        boundary_correspondences.append(
            {
                "kind": "boundary",
                "values": boundaries,
                "status": "corresponds" if len(set(boundaries)) == 1 else "analogous",
            }
        )

    scales = [str((shape.get("attributes") or {}).get("scale") or shape.get("scale") or "").strip() for shape in members]
    scale_correspondences = []
    if any(scales):
        scale_correspondences.append(
            {
                "kind": "scale",
                "values": scales,
                "status": "preserved" if len({value for value in scales if value}) <= 1 else "mismatched",
            }
        )

    mechanisms = [str(shape.get("mechanism") or "").strip() for shape in members if str(shape.get("mechanism") or "").strip()]
    mechanism_differences = sorted({value for value in mechanisms}) if len(set(mechanisms)) > 1 else []

    invariant_ids = [str(item).strip() for item in list(required_invariants or ["shared_roles", "shared_structure"]) if str(item).strip()]
    invariants: list[InvariantAssessment] = []
    for invariant_id in invariant_ids:
        if invariant_id == "shared_roles":
            status = "preserved" if shared_roles else "unknown"
            contract = "Roles present on every declared Shape population member."
        elif invariant_id == "shared_structure":
            status = "preserved" if abstracted_values else "unknown"
            contract = "Non-trivial shared structural tokens across the declared population."
        else:
            status = "unknown"
            contract = f"Explicit evidence required for invariant `{invariant_id}`."
        invariants.append(
            InvariantAssessment(
                invariant_id=invariant_id,
                status=status,
                evidence_refs=list(refs),
                abstraction_contract=contract,
            )
        )

    transfer_limits = [
        "literal_vocabulary_identity",
        "shape_identity_merge",
    ]
    if mechanism_differences:
        transfer_limits.append("mechanism_identity")
    if scale_correspondences and scale_correspondences[0].get("status") == "mismatched":
        transfer_limits.append("scale_identity")

    digest_material = {
        "refs": refs,
        "roles": sorted(shared_roles),
        "abstracted": abstracted_values,
        "branch_id": branch_id,
        "scope_id": scope_id,
    }
    auto_id = hashlib.sha256(
        json.dumps(digest_material, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:16]
    pattern = PatternRecord(
        pattern_id=str(pattern_id or f"pattern:{auto_id}").strip() or f"pattern:{auto_id}",
        shape_population_refs=refs,
        role_mappings=role_mappings,
        invariants=invariants,
        abstracted_values=abstracted_values,
        boundary_correspondences=boundary_correspondences,
        scale_correspondences=scale_correspondences,
        mechanism_differences=mechanism_differences,
        transfer_limits=transfer_limits,
        branch_id=str(branch_id or "").strip(),
        scope_id=str(scope_id or "").strip(),
        merge_shapes_forbidden=True,
    )
    payload = pattern.to_dict()
    payload["generated_at"] = utc_now()
    return payload


def classify_shape_pair(
    left: Mapping[str, Any],
    right: Mapping[str, Any],
    *,
    pattern: Mapping[str, Any] | None = None,
    branch_id: str = "",
    scope_id: str = "",
    anti_match_penalty: float | None = None,
    vocabulary_overlap_ceiling: float = 0.35,
) -> Dict[str, Any]:
    """Classify a Shape pair into one separated Pattern reasoning record kind.

    Never merges Shapes. Preserves rejected analogies as first-class records.
    """
    left_ref = _shape_ref(left, fallback_prefix="left")
    right_ref = _shape_ref(right, fallback_prefix="right")
    left_tokens = _shape_token_set(left)
    right_tokens = _shape_token_set(right)
    vocab_overlap = _overlap_ratio(left_tokens, right_tokens)
    left_roles = set(_shape_roles(left))
    right_roles = set(_shape_roles(right))
    shared_roles = sorted(left_roles & right_roles)
    missing_roles = sorted((left_roles | right_roles) - (left_roles & right_roles))

    left_boundary = str(left.get("system_boundary") or left.get("boundary") or "").strip()
    right_boundary = str(right.get("system_boundary") or right.get("boundary") or "").strip()
    left_scale = str((left.get("attributes") or {}).get("scale") or left.get("scale") or "").strip()
    right_scale = str((right.get("attributes") or {}).get("scale") or right.get("scale") or "").strip()
    left_mechanism = str(left.get("mechanism") or "").strip()
    right_mechanism = str(right.get("mechanism") or "").strip()

    holds_where: list[str] = []
    breaks_where: list[str] = []
    abstracts: list[str] = []
    if shared_roles:
        holds_where.append("shared_roles")
        abstracts.extend(shared_roles)
    if left_boundary and right_boundary and left_boundary == right_boundary:
        holds_where.append("boundary_identity")
    elif left_boundary and right_boundary:
        holds_where.append("boundary_analogy")
        abstracts.append("boundary")
    if left_scale and right_scale and left_scale != right_scale:
        breaks_where.append("scale_mismatch")
    if left_mechanism and right_mechanism and left_mechanism != right_mechanism:
        breaks_where.append("mechanism_mismatch")
    if missing_roles:
        breaks_where.append("role_mismatch")

    pattern_id = str((pattern or {}).get("pattern_id", "") or "")
    pattern_refs = {
        str(item).strip()
        for item in list((pattern or {}).get("shape_population_refs") or [])
        if str(item).strip()
    }
    in_declared_population = bool(pattern_refs) and {left_ref, right_ref}.issubset(pattern_refs)

    # Structural compatibility prefers shared roles/structure over vocabulary.
    structural_positive = bool(shared_roles) or (
        vocab_overlap < vocabulary_overlap_ceiling and bool(left_tokens & right_tokens)
    )
    hard_incompatible = bool({"scale_mismatch", "mechanism_mismatch", "role_mismatch"} & set(breaks_where)) and not shared_roles

    if hard_incompatible or (vocab_overlap >= 0.55 and not shared_roles):
        record_kind = "anti_match" if hard_incompatible or vocab_overlap >= 0.55 else "rejected_analogy"
        if vocab_overlap >= 0.55 and not shared_roles:
            record_kind = "anti_match"
            breaks_where.append("lexical_similarity_without_structure")
        reason = "structurally_incompatible"
        if anti_match_penalty is None:
            anti_match_penalty = HARD_REJECT_ANTI_MATCH_PENALTY if record_kind == "anti_match" else 0.25
    elif in_declared_population and shared_roles and not breaks_where:
        record_kind = "validated_membership"
        reason = "validated_pattern_membership"
        anti_match_penalty = None
    elif structural_positive and vocab_overlap <= vocabulary_overlap_ceiling:
        record_kind = "transfer_hypothesis" if breaks_where else "candidate_match"
        reason = "low_vocabulary_structural_correspondence"
        anti_match_penalty = None
    elif structural_positive:
        record_kind = "candidate_match"
        reason = "structural_candidate"
        anti_match_penalty = None
    else:
        record_kind = "rejected_analogy"
        reason = "insufficient_structure"
        anti_match_penalty = None
        breaks_where.append("insufficient_shared_structure")

    record_id = hashlib.sha256(
        f"{record_kind}|{left_ref}|{right_ref}|{pattern_id}|{branch_id}|{scope_id}".encode("utf-8")
    ).hexdigest()[:20]
    record = PatternReasoningRecord(
        record_kind=record_kind,
        record_id=f"{record_kind}:{record_id}",
        left_shape_ref=left_ref,
        right_shape_ref=right_ref,
        pattern_id=pattern_id,
        branch_id=str(branch_id or "").strip(),
        scope_id=str(scope_id or "").strip(),
        holds_where=holds_where,
        breaks_where=breaks_where,
        abstracts=sorted(set(abstracts)),
        evidence_refs=[left_ref, right_ref],
        revisable=True,
        disposition="active",
        reason=reason,
        merge_shapes_forbidden=True,
    )
    payload = record.to_dict()
    payload["vocabulary_overlap"] = round(vocab_overlap, 4)
    payload["shared_roles"] = shared_roles
    payload["anti_match_penalty"] = anti_match_penalty
    payload["generated_at"] = utc_now()
    # Compatibility projection for evaluate_anti_match consumers.
    if record_kind == "anti_match":
        payload["anti_match_projection"] = {
            "projection_id": payload["record_id"],
            "candidate_meta_id": right_ref,
            "anchor_meta_id": left_ref,
            "branch_id": payload["branch_id"],
            "scope_id": payload["scope_id"],
            "anti_match_penalty": float(anti_match_penalty or HARD_REJECT_ANTI_MATCH_PENALTY),
            "revisable": True,
            "disposition": "active",
        }
    return payload


def revise_anti_match_record(
    record: Mapping[str, Any],
    *,
    disposition: str,
    reason: str,
    branch_id: str | None = None,
    scope_id: str | None = None,
) -> Dict[str, Any]:
    """Revise a branch/scope-aware AntiMatch (or rejected analogy) without deleting history."""
    kind = str(record.get("record_kind", "") or "")
    if kind not in {"anti_match", "rejected_analogy"}:
        raise ValueError("only anti_match or rejected_analogy records are revisable through this helper")
    if disposition not in {"active", "revised", "withdrawn"}:
        raise ValueError(f"invalid disposition: {disposition}")
    if not bool(record.get("revisable", True)):
        raise ValueError("record is marked not revisable")
    revised = dict(record)
    revised["disposition"] = disposition
    revised["reason"] = str(reason or "").strip() or revised.get("reason", "")
    if branch_id is not None:
        revised["branch_id"] = str(branch_id or "").strip()
    if scope_id is not None:
        revised["scope_id"] = str(scope_id or "").strip()
    revised["revised_at"] = utc_now()
    revised["merge_shapes_forbidden"] = True
    projection = dict(revised.get("anti_match_projection") or {})
    if projection:
        projection["disposition"] = disposition
        projection["branch_id"] = revised.get("branch_id", "")
        projection["scope_id"] = revised.get("scope_id", "")
        revised["anti_match_projection"] = projection
    return revised
