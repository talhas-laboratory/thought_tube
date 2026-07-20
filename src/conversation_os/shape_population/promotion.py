"""Privileged evaluation recommendation and human-gated promotion."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Optional

from conversation_os.shape_population.contracts import (
    AuthorizationError,
    ForbiddenTransitionError,
    HumanApprovalEvent,
    IdempotencyConflictError,
    PromotionRequest,
    ValidationError,
    fingerprint_payload,
)
from conversation_os.shape_population.identities import (
    CANONICAL_AUTHORITY_ROLE,
    EVALUATOR_IDENTITY,
    HUMAN_APPROVER_ROLE,
    assert_tool_allowed,
    get_identity,
)
from conversation_os.shape_population.storage import PopulationStore

MODULE_ID = "kernel.shape_population.promotion"
CONTRACT_VERSION = "1.0.0"
PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "request_promotion",
    "record_human_approval",
    "apply_promotion",
    "rollback_promotion",
)
__all__ = list(PUBLIC_API)


def request_promotion(
    candidate_id: str,
    evaluation_id: str,
    rationale: str,
    evidence_refs: list[Mapping[str, Any]],
    *,
    store: PopulationStore,
    requester_identity: str = EVALUATOR_IDENTITY,
    idempotency_key: str = "",
) -> Dict[str, Any]:
    """Privileged: designated evaluator may recommend/request, never approve."""
    assert_tool_allowed(requester_identity, "request_promotion")
    if requester_identity != EVALUATOR_IDENTITY:
        raise AuthorizationError("only designated evaluator may request promotion")
    candidate = store.get_candidate(candidate_id)
    if candidate is None:
        raise ValidationError(f"unknown candidate: {candidate_id}")
    evaluation = store.get_evaluation(evaluation_id)
    if evaluation is None:
        raise ValidationError(f"unknown evaluation: {evaluation_id}")
    if evaluation.get("candidate_id") != candidate_id:
        raise ValidationError("evaluation does not belong to candidate")
    if not rationale.strip():
        raise ValidationError("rationale required")
    if not evidence_refs:
        raise ValidationError("evidence_refs required for promotion request")

    payload = {
        "candidate_id": candidate_id,
        "evaluation_id": evaluation_id,
        "rationale": rationale.strip(),
        "evidence_refs": [dict(item) for item in evidence_refs],
        "requester_identity": requester_identity,
    }
    fingerprint = fingerprint_payload(payload)
    key = idempotency_key or f"promotion:{candidate_id}:{fingerprint}"
    existing = store.get_idempotency(key)
    if existing is not None:
        if existing.get("fingerprint") != fingerprint:
            raise IdempotencyConflictError("promotion idempotency key conflict")
        return {"request": store.get_promotion(existing["request_id"]), "replayed": True}

    if candidate.get("status") != "recommended":
        raise ForbiddenTransitionError("promotion request requires recommended status")

    with store.transaction():
        # Race safety: re-read status under transaction.
        current = store.get_candidate(candidate_id)
        if current is None or current.get("status") != "recommended":
            raise ForbiddenTransitionError("candidate no longer recommended")
        if current.get("status") == "canonical":
            raise ForbiddenTransitionError("candidate already canonical")
        request_id = store.new_id("prom")
        now = store.now()
        request = PromotionRequest(
            request_id=request_id,
            candidate_id=candidate_id,
            evaluation_id=evaluation_id,
            rationale=rationale.strip(),
            evidence_refs=[dict(item) for item in evidence_refs],
            requester_identity=requester_identity,
            status="requested",
            created_at=now,
            content_fingerprint=fingerprint,
        )
        store.put_promotion(request.to_dict())
        current["status"] = "promotion_requested"
        current["updated_at"] = now
        store.put_candidate(current)
        store.put_idempotency(
            key,
            {"fingerprint": fingerprint, "request_id": request_id, "created_at": now},
        )
        return {"request": request.to_dict(), "candidate": current, "replayed": False}


def record_human_approval(
    request_id: str,
    *,
    store: PopulationStore,
    approval_identity: str,
    approval_reason: str,
    decision: str = "approved",
) -> HumanApprovalEvent:
    """Immutable human authorization event. Agents cannot synthesize this as candidate state."""
    if approval_identity not in {HUMAN_APPROVER_ROLE, CANONICAL_AUTHORITY_ROLE}:
        raise AuthorizationError("only human approver/canonical authority may record approval")
    if decision not in {"approved", "rejected"}:
        raise ValidationError("decision must be approved or rejected")
    if not approval_reason.strip():
        raise ValidationError("approval_reason required")
    request = store.get_promotion(request_id)
    if request is None:
        raise ValidationError(f"unknown promotion request: {request_id}")
    existing = store.get_approval_for_request(request_id)
    if existing is not None and decision == "approved":
        return HumanApprovalEvent(**{k: existing[k] for k in HumanApprovalEvent.__dataclass_fields__})
    event = HumanApprovalEvent(
        approval_id=store.new_id("appr"),
        request_id=request_id,
        approval_identity=approval_identity,
        approval_reason=approval_reason.strip(),
        decision=decision,
        created_at=store.now(),
        immutable=True,
    )
    store.put_approval(event.to_dict())
    if decision == "rejected":
        candidate = store.get_candidate(request["candidate_id"])
        if candidate is not None:
            candidate = dict(candidate)
            candidate["status"] = "recommended"
            candidate["updated_at"] = store.now()
            store.put_candidate(candidate)
        request = dict(request)
        request["status"] = "rejected"
        store.put_promotion(request)
    return event


def apply_promotion(
    request_id: str,
    *,
    store: PopulationStore,
    approval_identity: str,
    approval_reason: str = "",
) -> Dict[str, Any]:
    """Privileged: only after a valid immutable human approval event."""
    assert_tool_allowed(approval_identity, "apply_promotion")
    if approval_identity not in {HUMAN_APPROVER_ROLE, CANONICAL_AUTHORITY_ROLE}:
        raise AuthorizationError("population agents cannot apply promotion")
    request = store.get_promotion(request_id)
    if request is None:
        raise ValidationError(f"unknown promotion request: {request_id}")
    approval = store.get_approval_for_request(request_id)
    if approval is None:
        # Allow apply_promotion to record the immutable approval in the same call
        # when a human identity invokes it directly.
        if not approval_reason.strip():
            raise ValidationError("human approval event required before apply_promotion")
        approval_event = record_human_approval(
            request_id,
            store=store,
            approval_identity=approval_identity,
            approval_reason=approval_reason,
            decision="approved",
        )
        approval = approval_event.to_dict()
    if approval.get("decision") != "approved":
        raise AuthorizationError("promotion request was not approved")
    # Evaluator cannot approve its own request.
    if approval.get("approval_identity") == request.get("requester_identity"):
        raise AuthorizationError("evaluator cannot approve its own promotion request")

    with store.transaction():
        candidate = store.get_candidate(request["candidate_id"])
        if candidate is None:
            raise ValidationError("candidate missing")
        if candidate.get("status") == "canonical" and store.get_canonical_projection(candidate["candidate_id"]):
            return {"candidate": candidate, "projection": store.get_canonical_projection(candidate["candidate_id"]), "replayed": True}
        if candidate.get("status") not in {"promotion_requested", "recommended"}:
            raise ForbiddenTransitionError(f"cannot promote from status {candidate.get('status')}")
        now = store.now()
        candidate = dict(candidate)
        candidate["status"] = "canonical"
        candidate["updated_at"] = now
        store.put_candidate(candidate)
        projection = {
            "candidate_id": candidate["candidate_id"],
            "promoted_at": now,
            "request_id": request_id,
            "approval_id": approval["approval_id"],
            "title": candidate.get("title"),
            "statement": candidate.get("statement"),
            "boundary": candidate.get("boundary"),
            "evidence_refs": candidate.get("evidence_refs"),
        }
        store.put_canonical_projection(candidate["candidate_id"], projection)
        request = dict(request)
        request["status"] = "applied"
        store.put_promotion(request)
        return {"candidate": candidate, "projection": projection, "approval": approval, "replayed": False}


def rollback_promotion(
    candidate_id: str,
    *,
    store: PopulationStore,
    authority_identity: str,
    reason: str,
) -> Dict[str, Any]:
    if authority_identity not in {HUMAN_APPROVER_ROLE, CANONICAL_AUTHORITY_ROLE}:
        raise AuthorizationError("only canonical authority may rollback promotion")
    if not reason.strip():
        raise ValidationError("rollback reason required")
    with store.transaction():
        candidate = store.get_candidate(candidate_id)
        if candidate is None:
            raise ValidationError("unknown candidate")
        store.remove_canonical_projection(candidate_id)
        candidate = dict(candidate)
        candidate["status"] = "recommended"
        candidate["updated_at"] = store.now()
        store.put_candidate(candidate)
        return {
            "candidate": candidate,
            "projection": store.get_canonical_projection(candidate_id),
            "rollback_reason": reason.strip(),
        }
