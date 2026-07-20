"""Shared Shape population schemas, statuses, and invariants."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence

MODULE_ID = "kernel.shape_population.contracts"
CONTRACT_VERSION = "1.0.0"
NORMALIZATION_VERSION = "1.0.0"
EVIDENCE_POLICY_VERSION = "1.0.0"
CANDIDATE_SCHEMA_VERSION = "1.0.0"
EVALUATION_SCHEMA_VERSION = "1.0.0"
PROMOTION_POLICY_VERSION = "1.0.0"

PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "NORMALIZATION_VERSION",
    "EVIDENCE_POLICY_VERSION",
    "CANDIDATE_SCHEMA_VERSION",
    "EVALUATION_SCHEMA_VERSION",
    "PROMOTION_POLICY_VERSION",
    "CANDIDATE_STATUSES",
    "NON_CANONICAL_STATUSES",
    "COMPARISON_RELATIONS",
    "POPULATION_AGENT_TOOLS",
    "PRIVILEGED_PROMOTION_OPS",
    "AUTOMATIC_INFRA_OPS",
    "ShapePopulationError",
    "ValidationError",
    "AuthorizationError",
    "IdempotencyConflictError",
    "ForbiddenTransitionError",
    "SegmentRecord",
    "NormalizedSource",
    "EvidenceInquiry",
    "EvidenceBlock",
    "EvidencePacket",
    "CandidatePayload",
    "CandidateRecord",
    "EvaluationPayload",
    "EvaluationRecord",
    "PopulationReceipt",
    "PromotionRequest",
    "HumanApprovalEvent",
    "ComparisonNeighbor",
)
__all__ = list(PUBLIC_API)

CANDIDATE_STATUSES = frozenset(
    {
        "proposed",
        "under_review",
        "rejected",
        "needs_evidence",
        "recommended",
        "promotion_requested",
        "canonical",
    }
)
NON_CANONICAL_STATUSES = frozenset(CANDIDATE_STATUSES - {"canonical"})
COMPARISON_RELATIONS = frozenset(
    {
        "possible_same",
        "possibly_adjacent",
        "possibly_conflicting",
        "possibly_distinct",
    }
)
POPULATION_AGENT_TOOLS = (
    "submit_candidate",
    "find_comparison_candidates",
    "submit_evaluation",
)
PRIVILEGED_PROMOTION_OPS = (
    "request_promotion",
    "apply_promotion",
)
AUTOMATIC_INFRA_OPS = (
    "normalize_source",
    "build_evidence_packet",
    "validate_candidate",
    "persist_candidate",
    "record_population_receipt",
)

ALLOWED_TRANSITIONS: Mapping[str, frozenset[str]] = {
    "proposed": frozenset({"under_review", "rejected", "needs_evidence", "recommended"}),
    "under_review": frozenset({"recommended", "rejected", "needs_evidence", "under_review"}),
    "needs_evidence": frozenset({"proposed", "under_review", "rejected", "recommended"}),
    "recommended": frozenset({"promotion_requested", "rejected", "needs_evidence", "under_review"}),
    "promotion_requested": frozenset({"canonical", "recommended", "rejected"}),
    "rejected": frozenset(),
    "canonical": frozenset(),
}


class ShapePopulationError(Exception):
    """Base error for Shape population operations."""


class ValidationError(ShapePopulationError):
    """Structural or policy validation failed."""


class AuthorizationError(ShapePopulationError):
    """Caller is not authorized for the requested operation."""


class IdempotencyConflictError(ShapePopulationError):
    """Idempotency key replayed with a different payload fingerprint."""


class ForbiddenTransitionError(ShapePopulationError):
    """Candidate lifecycle transition is not allowed."""


def _require_non_empty_str(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{field_name} must be a non-empty string")
    return value.strip()


@dataclass
class SegmentRecord:
    segment_id: str
    source_id: str
    ordinal: int
    char_start: int
    char_end: int
    structure_path: str
    text: str
    text_sha256: str
    byte_start: Optional[int] = None
    byte_end: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class NormalizedSource:
    source_id: str
    content_sha256: str
    modality: str
    metadata: Dict[str, Any]
    normalization_version: str
    segments: List[SegmentRecord]
    raw_ref: str = ""
    locator: str = ""
    ingested_at: str = ""
    rejected: bool = False
    rejection_reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["segments"] = [segment.to_dict() for segment in self.segments]
        return payload

    def reconstructed_text(self) -> str:
        return "".join(segment.text for segment in sorted(self.segments, key=lambda item: item.ordinal))


@dataclass
class EvidenceInquiry:
    question: str
    anchors: List[str] = field(default_factory=list)
    scope: str = "declared_segments"
    requested_by: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class EvidenceBlock:
    block_id: str
    source_id: str
    segment_id: str
    char_start: int
    char_end: int
    text: str
    structure_path: str
    ordinal: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            **asdict(self),
            "envelope": "quoted_data",
            "instruction_authority": False,
        }


@dataclass
class EvidencePacket:
    packet_id: str
    inquiry: EvidenceInquiry
    blocks: List[EvidenceBlock]
    omitted: List[Dict[str, Any]]
    budget: Dict[str, Any]
    policy_version: str
    corpus_revision: str
    safe: bool = True
    empty_reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "packet_id": self.packet_id,
            "inquiry": self.inquiry.to_dict(),
            "blocks": [block.to_dict() for block in self.blocks],
            "omitted": list(self.omitted),
            "budget": dict(self.budget),
            "policy_version": self.policy_version,
            "corpus_revision": self.corpus_revision,
            "safe": self.safe,
            "empty_reason": self.empty_reason,
            "injection_safe_envelope": True,
        }


@dataclass
class CandidatePayload:
    packet_id: str
    title: str
    statement: str
    boundary: str
    mechanism: str
    dimensions: List[str]
    evidence_refs: List[Dict[str, Any]]
    counter_hypotheses: List[str]
    uncertainty: str
    recommended_disposition: str
    agent_identity: str
    model_version: str
    prompt_version: str
    tool_contract_version: str
    run_id: str = ""
    relations: List[str] = field(default_factory=list)
    idempotency_key: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "CandidatePayload":
        if "canonical" in payload or payload.get("status") == "canonical":
            raise ValidationError("candidate payload cannot include canonical status")
        if payload.get("candidate_id"):
            raise ValidationError("candidate payload cannot assign candidate_id")
        required = (
            "packet_id",
            "title",
            "statement",
            "boundary",
            "mechanism",
            "dimensions",
            "evidence_refs",
            "counter_hypotheses",
            "uncertainty",
            "recommended_disposition",
            "agent_identity",
            "model_version",
            "prompt_version",
            "tool_contract_version",
        )
        missing = [name for name in required if name not in payload]
        if missing:
            raise ValidationError(f"candidate payload missing fields: {', '.join(missing)}")
        dimensions = payload.get("dimensions") or []
        evidence_refs = payload.get("evidence_refs") or []
        counter_hypotheses = payload.get("counter_hypotheses") or []
        if not isinstance(dimensions, list) or not dimensions:
            raise ValidationError("dimensions must be a non-empty list")
        if not isinstance(evidence_refs, list) or not evidence_refs:
            raise ValidationError("evidence_refs must be a non-empty list")
        if not isinstance(counter_hypotheses, list):
            raise ValidationError("counter_hypotheses must be a list")
        disposition = _require_non_empty_str(payload["recommended_disposition"], "recommended_disposition")
        if disposition not in {"proposed", "needs_evidence", "under_review"}:
            raise ValidationError("recommended_disposition must be proposed, needs_evidence, or under_review")
        return cls(
            packet_id=_require_non_empty_str(payload["packet_id"], "packet_id"),
            title=_require_non_empty_str(payload["title"], "title"),
            statement=_require_non_empty_str(payload["statement"], "statement"),
            boundary=_require_non_empty_str(payload["boundary"], "boundary"),
            mechanism=_require_non_empty_str(payload["mechanism"], "mechanism"),
            dimensions=[_require_non_empty_str(item, "dimension") for item in dimensions],
            evidence_refs=[dict(item) for item in evidence_refs],
            counter_hypotheses=[str(item) for item in counter_hypotheses],
            uncertainty=_require_non_empty_str(payload["uncertainty"], "uncertainty"),
            recommended_disposition=disposition,
            agent_identity=_require_non_empty_str(payload["agent_identity"], "agent_identity"),
            model_version=_require_non_empty_str(payload["model_version"], "model_version"),
            prompt_version=_require_non_empty_str(payload["prompt_version"], "prompt_version"),
            tool_contract_version=_require_non_empty_str(
                payload["tool_contract_version"], "tool_contract_version"
            ),
            run_id=str(payload.get("run_id") or ""),
            relations=[str(item) for item in (payload.get("relations") or [])],
            idempotency_key=str(payload.get("idempotency_key") or ""),
        )


@dataclass
class CandidateRecord:
    candidate_id: str
    status: str
    packet_id: str
    title: str
    statement: str
    boundary: str
    mechanism: str
    dimensions: List[str]
    evidence_refs: List[Dict[str, Any]]
    counter_hypotheses: List[str]
    uncertainty: str
    agent_identity: str
    model_version: str
    prompt_version: str
    tool_contract_version: str
    schema_version: str = CANDIDATE_SCHEMA_VERSION
    run_id: str = ""
    relations: List[str] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
    content_fingerprint: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class EvaluationPayload:
    candidate_id: str
    disposition: str
    critique: str
    evidence_refs: List[Dict[str, Any]]
    uncertainty: str
    agent_identity: str
    model_version: str
    prompt_version: str
    tool_contract_version: str
    relationship_findings: List[Dict[str, Any]] = field(default_factory=list)
    revisions: List[str] = field(default_factory=list)
    run_id: str = ""
    idempotency_key: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "EvaluationPayload":
        if payload.get("status") == "canonical" or "canonical" in payload:
            raise ValidationError("evaluation payload cannot set canonical status")
        required = (
            "candidate_id",
            "disposition",
            "critique",
            "evidence_refs",
            "uncertainty",
            "agent_identity",
            "model_version",
            "prompt_version",
            "tool_contract_version",
        )
        missing = [name for name in required if name not in payload]
        if missing:
            raise ValidationError(f"evaluation payload missing fields: {', '.join(missing)}")
        disposition = _require_non_empty_str(payload["disposition"], "disposition")
        if disposition not in {"under_review", "recommended", "rejected", "needs_evidence"}:
            raise ValidationError("disposition must be under_review, recommended, rejected, or needs_evidence")
        findings = payload.get("relationship_findings") or []
        for finding in findings:
            relation = finding.get("relation")
            if relation not in COMPARISON_RELATIONS:
                raise ValidationError(f"invalid comparison relation: {relation}")
        return cls(
            candidate_id=_require_non_empty_str(payload["candidate_id"], "candidate_id"),
            disposition=disposition,
            critique=_require_non_empty_str(payload["critique"], "critique"),
            evidence_refs=[dict(item) for item in (payload.get("evidence_refs") or [])],
            uncertainty=_require_non_empty_str(payload["uncertainty"], "uncertainty"),
            agent_identity=_require_non_empty_str(payload["agent_identity"], "agent_identity"),
            model_version=_require_non_empty_str(payload["model_version"], "model_version"),
            prompt_version=_require_non_empty_str(payload["prompt_version"], "prompt_version"),
            tool_contract_version=_require_non_empty_str(
                payload["tool_contract_version"], "tool_contract_version"
            ),
            relationship_findings=[dict(item) for item in findings],
            revisions=[str(item) for item in (payload.get("revisions") or [])],
            run_id=str(payload.get("run_id") or ""),
            idempotency_key=str(payload.get("idempotency_key") or ""),
        )


@dataclass
class EvaluationRecord:
    evaluation_id: str
    candidate_id: str
    disposition: str
    critique: str
    evidence_refs: List[Dict[str, Any]]
    uncertainty: str
    agent_identity: str
    model_version: str
    prompt_version: str
    tool_contract_version: str
    relationship_findings: List[Dict[str, Any]] = field(default_factory=list)
    revisions: List[str] = field(default_factory=list)
    schema_version: str = EVALUATION_SCHEMA_VERSION
    run_id: str = ""
    created_at: str = ""
    content_fingerprint: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PopulationReceipt:
    receipt_id: str
    operation: str
    request_id: str
    outcome: str
    agent_identity: str
    packet_fingerprint: str
    model_version: str = ""
    prompt_version: str = ""
    tool_contract_version: str = ""
    candidate_id: str = ""
    evaluation_id: str = ""
    timing_ms: int = 0
    retry_count: int = 0
    cost_units: float = 0.0
    validation_outcome: str = ""
    created_at: str = ""
    provenance: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ComparisonNeighbor:
    candidate_id: str
    relation_hint: str
    title: str
    statement: str
    boundary: str
    evidence_refs: List[Dict[str, Any]]
    status: str

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        # Never authoritative equivalence.
        payload["authoritative_equivalence"] = False
        return payload


@dataclass
class PromotionRequest:
    request_id: str
    candidate_id: str
    evaluation_id: str
    rationale: str
    evidence_refs: List[Dict[str, Any]]
    requester_identity: str
    status: str = "requested"
    created_at: str = ""
    content_fingerprint: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class HumanApprovalEvent:
    approval_id: str
    request_id: str
    approval_identity: str
    approval_reason: str
    decision: str
    created_at: str = ""
    immutable: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def fingerprint_payload(payload: Mapping[str, Any] | Sequence[Any] | str) -> str:
    import hashlib
    import json

    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()
