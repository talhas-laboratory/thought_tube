"""Atomic candidate validation, persistence, and receipts."""

from __future__ import annotations

import time
from typing import Any, Dict, Mapping, Optional

from conversation_os.shape_population.contracts import (
    ALLOWED_TRANSITIONS,
    CANDIDATE_SCHEMA_VERSION,
    CandidatePayload,
    CandidateRecord,
    EVALUATION_SCHEMA_VERSION,
    EvaluationPayload,
    EvaluationRecord,
    ForbiddenTransitionError,
    IdempotencyConflictError,
    PopulationReceipt,
    ValidationError,
    fingerprint_payload,
)
from conversation_os.shape_population.evidence import validate_evidence_ref_against_packet
from conversation_os.shape_population.identities import (
    CRITIC_IDENTITY,
    PROPOSER_IDENTITY,
    SYNTHESIZER_IDENTITY,
    get_identity,
)
from conversation_os.shape_population.storage import PopulationStore

MODULE_ID = "kernel.shape_population.governance"
CONTRACT_VERSION = "1.0.0"
PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "validate_candidate",
    "persist_candidate",
    "record_population_receipt",
    "validate_evaluation",
    "atomic_submit_candidate",
    "atomic_submit_evaluation",
    "transition_candidate",
)
__all__ = list(PUBLIC_API)

DEFAULT_RETRY_CAP = 3
DEFAULT_COST_CAP = 100.0


def _resolve_evidence_ref(store: PopulationStore, packet_id: str, ref: Mapping[str, Any]) -> None:
    validate_evidence_ref_against_packet(store, packet_id, ref)


def validate_candidate(store: PopulationStore, payload: CandidatePayload, *, policy_version: str = CANDIDATE_SCHEMA_VERSION) -> None:
    """Structural/policy validation only — no semantic support judgment."""
    get_identity(payload.agent_identity)
    if payload.agent_identity != PROPOSER_IDENTITY:
        raise ValidationError("only proposer identity may submit candidates")
    packet = store.get_packet(payload.packet_id)
    if packet is None:
        raise ValidationError(f"unknown evidence packet: {payload.packet_id}")
    if not policy_version:
        raise ValidationError("policy_version required")
    for ref in payload.evidence_refs:
        _resolve_evidence_ref(store, payload.packet_id, ref)
    # No semantic adjudication here.


def persist_candidate(store: PopulationStore, record: CandidateRecord) -> CandidateRecord:
    store.put_candidate(record.to_dict())
    return record


def record_population_receipt(store: PopulationStore, receipt: PopulationReceipt) -> PopulationReceipt:
    # Redaction-safe: never embed raw source text in receipts.
    safe = receipt.to_dict()
    provenance = dict(safe.get("provenance") or {})
    provenance.pop("raw_text", None)
    provenance.pop("source_text", None)
    safe["provenance"] = provenance
    store.put_receipt(safe)
    return PopulationReceipt(**safe)


def transition_candidate(store: PopulationStore, candidate_id: str, new_status: str) -> CandidateRecord:
    row = store.get_candidate(candidate_id)
    if row is None:
        raise ValidationError(f"unknown candidate: {candidate_id}")
    current = row["status"]
    if new_status == "canonical":
        raise ForbiddenTransitionError("canonical status may only be set by apply_promotion")
    allowed = ALLOWED_TRANSITIONS.get(current, frozenset())
    if new_status not in allowed:
        raise ForbiddenTransitionError(f"cannot transition {current} -> {new_status}")
    row = dict(row)
    row["status"] = new_status
    row["updated_at"] = store.now()
    store.put_candidate(row)
    return CandidateRecord(**{k: row[k] for k in CandidateRecord.__dataclass_fields__})


def validate_evaluation(store: PopulationStore, payload: EvaluationPayload) -> CandidateRecord:
    get_identity(payload.agent_identity)
    if payload.agent_identity not in {CRITIC_IDENTITY, SYNTHESIZER_IDENTITY, "shape.evaluator"}:
        raise ValidationError("evaluation requires critic, synthesizer, or evaluator identity")
    row = store.get_candidate(payload.candidate_id)
    if row is None:
        raise ValidationError(f"unknown candidate: {payload.candidate_id}")
    if row.get("agent_identity") == payload.agent_identity and row.get("run_id") and row.get("run_id") == payload.run_id:
        raise ValidationError("critic identity/run must be distinct from proposer run")
    packet_id = str(row.get("packet_id") or "")
    for ref in payload.evidence_refs:
        _resolve_evidence_ref(store, packet_id, ref)
    return CandidateRecord(**{k: row[k] for k in CandidateRecord.__dataclass_fields__ if k in row})


def _check_budget(retry_count: int, cost_units: float) -> None:
    if retry_count > DEFAULT_RETRY_CAP:
        raise ValidationError("retry cap exceeded")
    if cost_units > DEFAULT_COST_CAP:
        raise ValidationError("cost cap exceeded")


def atomic_submit_candidate(
    store: PopulationStore,
    payload_raw: Mapping[str, Any],
    *,
    timing_ms: int = 0,
    retry_count: int = 0,
    cost_units: float = 0.0,
) -> Dict[str, Any]:
    started = time.time()
    payload = CandidatePayload.from_mapping(payload_raw)
    fingerprint = fingerprint_payload(payload.to_dict())
    key = payload.idempotency_key or f"candidate:{payload.agent_identity}:{fingerprint}"
    existing = store.get_idempotency(key)
    if existing is not None:
        if existing.get("fingerprint") != fingerprint:
            raise IdempotencyConflictError("idempotency key reused with different payload")
        receipt = store.get_receipt(existing["receipt_id"])
        candidate = store.get_candidate(existing["candidate_id"])
        return {"candidate": candidate, "receipt": receipt, "replayed": True}

    _check_budget(retry_count, cost_units)
    with store.transaction():
        validate_candidate(store, payload)
        candidate_id = store.new_id("cand")
        now = store.now()
        status = payload.recommended_disposition
        record = CandidateRecord(
            candidate_id=candidate_id,
            status=status,
            packet_id=payload.packet_id,
            title=payload.title,
            statement=payload.statement,
            boundary=payload.boundary,
            mechanism=payload.mechanism,
            dimensions=list(payload.dimensions),
            evidence_refs=[dict(item) for item in payload.evidence_refs],
            counter_hypotheses=list(payload.counter_hypotheses),
            uncertainty=payload.uncertainty,
            agent_identity=payload.agent_identity,
            model_version=payload.model_version,
            prompt_version=payload.prompt_version,
            tool_contract_version=payload.tool_contract_version,
            run_id=payload.run_id,
            relations=list(payload.relations),
            created_at=now,
            updated_at=now,
            content_fingerprint=fingerprint,
        )
        persist_candidate(store, record)
        elapsed = timing_ms or int((time.time() - started) * 1000)
        receipt = PopulationReceipt(
            receipt_id=store.new_id("rcpt"),
            operation="submit_candidate",
            request_id=key,
            outcome="accepted",
            agent_identity=payload.agent_identity,
            packet_fingerprint=fingerprint_payload(store.get_packet(payload.packet_id) or {}),
            model_version=payload.model_version,
            prompt_version=payload.prompt_version,
            tool_contract_version=payload.tool_contract_version,
            candidate_id=candidate_id,
            timing_ms=elapsed,
            retry_count=retry_count,
            cost_units=cost_units,
            validation_outcome="passed",
            created_at=now,
            provenance={"packet_id": payload.packet_id, "schema_version": CANDIDATE_SCHEMA_VERSION},
        )
        record_population_receipt(store, receipt)
        store.put_idempotency(
            key,
            {
                "fingerprint": fingerprint,
                "receipt_id": receipt.receipt_id,
                "candidate_id": candidate_id,
                "created_at": now,
            },
        )
        return {"candidate": record.to_dict(), "receipt": receipt.to_dict(), "replayed": False}


def atomic_submit_evaluation(
    store: PopulationStore,
    payload_raw: Mapping[str, Any],
    *,
    timing_ms: int = 0,
    retry_count: int = 0,
    cost_units: float = 0.0,
) -> Dict[str, Any]:
    started = time.time()
    payload = EvaluationPayload.from_mapping(payload_raw)
    fingerprint = fingerprint_payload(payload.to_dict())
    key = payload.idempotency_key or f"evaluation:{payload.agent_identity}:{fingerprint}"
    existing = store.get_idempotency(key)
    if existing is not None:
        if existing.get("fingerprint") != fingerprint:
            raise IdempotencyConflictError("idempotency key reused with different payload")
        return {
            "evaluation": store.get_evaluation(existing["evaluation_id"]),
            "candidate": store.get_candidate(existing["candidate_id"]),
            "receipt": store.get_receipt(existing["receipt_id"]),
            "replayed": True,
        }

    _check_budget(retry_count, cost_units)
    with store.transaction():
        candidate = validate_evaluation(store, payload)
        # Apply disposition via allowed transitions (never canonical).
        if payload.disposition != candidate.status:
            transition_candidate(store, candidate.candidate_id, payload.disposition)
        evaluation_id = store.new_id("eval")
        now = store.now()
        evaluation = EvaluationRecord(
            evaluation_id=evaluation_id,
            candidate_id=candidate.candidate_id,
            disposition=payload.disposition,
            critique=payload.critique,
            evidence_refs=[dict(item) for item in payload.evidence_refs],
            uncertainty=payload.uncertainty,
            agent_identity=payload.agent_identity,
            model_version=payload.model_version,
            prompt_version=payload.prompt_version,
            tool_contract_version=payload.tool_contract_version,
            relationship_findings=[dict(item) for item in payload.relationship_findings],
            revisions=list(payload.revisions),
            schema_version=EVALUATION_SCHEMA_VERSION,
            run_id=payload.run_id,
            created_at=now,
            content_fingerprint=fingerprint,
        )
        store.put_evaluation(evaluation.to_dict())
        # Explicit revision note required to alter boundary in candidate record.
        updated = store.get_candidate(candidate.candidate_id)
        assert updated is not None
        if payload.revisions:
            for revision in payload.revisions:
                if revision.startswith("boundary:"):
                    updated["boundary"] = revision.split("boundary:", 1)[1].strip()
                    updated["updated_at"] = now
                    store.put_candidate(updated)
        elapsed = timing_ms or int((time.time() - started) * 1000)
        receipt = PopulationReceipt(
            receipt_id=store.new_id("rcpt"),
            operation="submit_evaluation",
            request_id=key,
            outcome="accepted",
            agent_identity=payload.agent_identity,
            packet_fingerprint=fingerprint,
            model_version=payload.model_version,
            prompt_version=payload.prompt_version,
            tool_contract_version=payload.tool_contract_version,
            candidate_id=candidate.candidate_id,
            evaluation_id=evaluation_id,
            timing_ms=elapsed,
            retry_count=retry_count,
            cost_units=cost_units,
            validation_outcome="passed",
            created_at=now,
            provenance={"schema_version": EVALUATION_SCHEMA_VERSION},
        )
        record_population_receipt(store, receipt)
        store.put_idempotency(
            key,
            {
                "fingerprint": fingerprint,
                "receipt_id": receipt.receipt_id,
                "candidate_id": candidate.candidate_id,
                "evaluation_id": evaluation_id,
                "created_at": now,
            },
        )
        return {
            "evaluation": evaluation.to_dict(),
            "candidate": store.get_candidate(candidate.candidate_id),
            "receipt": receipt.to_dict(),
            "replayed": False,
        }
