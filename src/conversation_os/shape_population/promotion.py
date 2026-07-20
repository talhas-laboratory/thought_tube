"""Privileged evaluation recommendation and human-gated promotion."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Mapping, Optional

from conversation_os.shape_population.canonical_port import CanonicalShapePort, FailClosedCanonicalPort
from conversation_os.shape_population.contracts import (
    AuthorizationError,
    ForbiddenTransitionError,
    HumanApprovalEvent,
    IdempotencyConflictError,
    PromotionRequest,
    ValidationError,
    fingerprint_payload,
)
from conversation_os.shape_population.execution_context import (
    CAP_PROMOTION_APPLY,
    CAP_PROMOTION_APPROVE,
    CAP_PROMOTION_REQUEST,
    CAP_PROMOTION_ROLLBACK,
    ExecutionContext,
    service_context,
)
from conversation_os.shape_population.identities import (
    CANONICAL_AUTHORITY_ROLE,
    EVALUATOR_IDENTITY,
    HUMAN_APPROVER_ROLE,
    assert_tool_allowed,
)
from conversation_os.shape_population.storage import PopulationStore

MODULE_ID = "kernel.shape_population.promotion"
CONTRACT_VERSION = "1.0.0"
PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "request_promotion",
    "record_human_decision",
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
    context: Optional[ExecutionContext] = None,
    idempotency_key: str = "",
) -> Dict[str, Any]:
    """Privileged: designated evaluator may recommend/request, never approve."""
    if context is not None:
        context.require_capability(CAP_PROMOTION_REQUEST)
        requester_identity = context.principal_id
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
        "run_id": "" if context is None else context.run_id,
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


def record_human_decision(
    request_id: str,
    *,
    store: PopulationStore,
    approval_identity: str,
    approval_reason: str,
    decision: str = "approved",
    context: Optional[ExecutionContext] = None,
) -> HumanApprovalEvent:
    """Immutable human authorization event. Agents cannot synthesize this as candidate state."""
    if context is not None:
        context.require_capability(CAP_PROMOTION_APPROVE)
        if context.principal_kind != "human":
            raise AuthorizationError("human decision requires a human execution context")
        approval_identity = context.principal_id
    if context is None and approval_identity not in {HUMAN_APPROVER_ROLE, CANONICAL_AUTHORITY_ROLE}:
        raise AuthorizationError("only human approver/canonical authority may record approval")
    if decision not in {"approved", "rejected"}:
        raise ValidationError("decision must be approved or rejected")
    if not approval_reason.strip():
        raise ValidationError("approval_reason required")
    request = store.get_promotion(request_id)
    if request is None:
        raise ValidationError(f"unknown promotion request: {request_id}")
    if request.get("status") in {"approved", "rejected", "applied"}:
        raise ForbiddenTransitionError(f"promotion request decision is terminal from status {request.get('status')}")
    existing_decision = store.get_human_decision(request_id)
    if existing_decision is not None:
        raise ForbiddenTransitionError("promotion request already has a terminal human decision")
    event = HumanApprovalEvent(
        approval_id=store.new_id("appr"),
        request_id=request_id,
        approval_identity=approval_identity,
        approval_reason=approval_reason.strip(),
        decision=decision,
        created_at=store.now(),
        immutable=True,
    )
    with store.transaction():
        store.put_approval(event.to_dict())
        if decision == "rejected":
            candidate = store.get_candidate(request["candidate_id"])
            if candidate is not None:
                candidate = dict(candidate)
                candidate["status"] = "recommended"
                candidate["updated_at"] = store.now()
                store.put_candidate(candidate)
        request = dict(request)
        request["status"] = "approved" if decision == "approved" else "rejected"
        store.put_promotion(request)
    return event


def record_human_approval(
    request_id: str,
    *,
    store: PopulationStore,
    approval_identity: str,
    approval_reason: str,
    decision: str = "approved",
    context: Optional[ExecutionContext] = None,
) -> HumanApprovalEvent:
    return record_human_decision(
        request_id,
        store=store,
        approval_identity=approval_identity,
        approval_reason=approval_reason,
        decision=decision,
        context=context,
    )


def apply_promotion(
    request_id: str,
    *,
    store: PopulationStore,
    approval_identity: str,
    approval_reason: str = "",
    context: Optional[ExecutionContext] = None,
    canonical_port: Optional[CanonicalShapePort] = None,
    idempotency_key: str = "",
) -> Dict[str, Any]:
    """Privileged: only after a valid immutable human approval event."""
    if context is not None:
        context.require_capability(CAP_PROMOTION_APPLY)
        approval_identity = context.principal_id
    else:
        assert_tool_allowed(approval_identity, "apply_promotion")
    if context is None and approval_identity not in {HUMAN_APPROVER_ROLE, CANONICAL_AUTHORITY_ROLE}:
        raise AuthorizationError("population agents cannot apply promotion")
    request = store.get_promotion(request_id)
    if request is None:
        raise ValidationError(f"unknown promotion request: {request_id}")
    if request.get("status") == "rejected":
        raise ForbiddenTransitionError("rejected promotion request is terminal")
    approval = store.get_approval_for_request(request_id)
    if approval is None:
        raise ValidationError("prior human approval event required before apply_promotion")
    if approval.get("decision") != "approved":
        raise AuthorizationError("promotion request was not approved")
    # Evaluator cannot approve its own request.
    if approval.get("approval_identity") == request.get("requester_identity"):
        raise AuthorizationError("evaluator cannot approve its own promotion request")

    if context is None:
        context = service_context(
            approval_identity,
            capabilities=(CAP_PROMOTION_APPLY,),
            authenticated_by="legacy-compat",
        )
    if canonical_port is None:
        canonical_port = FailClosedCanonicalPort(Path.cwd())

    with store.transaction():
        candidate = store.get_candidate(request["candidate_id"])
        if candidate is None:
            raise ValidationError("candidate missing")
        if candidate.get("status") == "canonical" and store.get_canonical_projection(candidate["candidate_id"]):
            return {"candidate": candidate, "projection": store.get_canonical_projection(candidate["candidate_id"]), "replayed": True}
        if candidate.get("status") not in {"promotion_requested", "recommended"}:
            raise ForbiddenTransitionError(f"cannot promote from status {candidate.get('status')}")
        evaluation = store.get_evaluation(request["evaluation_id"])
        if evaluation is None:
            raise ValidationError("evaluation missing")
        projection = canonical_port.prepare(request, candidate, evaluation, approval, context=context)
        canonical_port.validate(projection, context=context)
        canonical_key = idempotency_key or f"canonical-apply:{request_id}:{candidate['candidate_id']}"
        canonical_receipt = canonical_port.apply(projection, idempotency_key=canonical_key, context=context)
        if not canonical_receipt.get("applied"):
            return {
                "candidate": candidate,
                "projection": None,
                "approval": approval,
                "canonical_receipt": canonical_receipt,
                "replayed": False,
            }
        read_back = canonical_port.read_back(str(canonical_receipt.get("canonical_id") or ""), context=context)
        now = store.now()
        candidate = dict(candidate)
        candidate["status"] = "canonical"
        candidate["updated_at"] = now
        store.put_candidate(candidate)
        stored_projection = {
            **dict(projection),
            "canonical_id": canonical_receipt.get("canonical_id"),
            "promoted_at": now,
            "read_back": read_back,
        }
        store.put_canonical_projection(candidate["candidate_id"], stored_projection)
        request = dict(request)
        request["status"] = "applied"
        store.put_promotion(request)
        return {
            "candidate": candidate,
            "projection": stored_projection,
            "approval": approval,
            "canonical_receipt": canonical_receipt,
            "read_back": read_back,
            "replayed": False,
        }


def rollback_promotion(
    candidate_id: str,
    *,
    store: PopulationStore,
    authority_identity: str,
    reason: str,
    context: Optional[ExecutionContext] = None,
    canonical_port: Optional[CanonicalShapePort] = None,
    idempotency_key: str = "",
) -> Dict[str, Any]:
    if context is not None:
        context.require_capability(CAP_PROMOTION_ROLLBACK)
        authority_identity = context.principal_id
    if context is None and authority_identity not in {HUMAN_APPROVER_ROLE, CANONICAL_AUTHORITY_ROLE}:
        raise AuthorizationError("only canonical authority may rollback promotion")
    if not reason.strip():
        raise ValidationError("rollback reason required")
    if context is None:
        context = service_context(
            authority_identity,
            capabilities=(CAP_PROMOTION_ROLLBACK,),
            authenticated_by="legacy-compat",
        )
    if canonical_port is None:
        canonical_port = FailClosedCanonicalPort(Path.cwd())
    with store.transaction():
        candidate = store.get_candidate(candidate_id)
        if candidate is None:
            raise ValidationError("unknown candidate")
        current_projection = store.get_canonical_projection(candidate_id)
        canonical_id = str((current_projection or {}).get("canonical_id") or f"canonical:{candidate_id}")
        rollback_receipt = canonical_port.rollback(
            canonical_id,
            reason=reason,
            idempotency_key=idempotency_key or f"canonical-rollback:{candidate_id}:{reason.strip()}",
            context=context,
        )
        if not rollback_receipt.get("rolled_back"):
            return {
                "candidate": candidate,
                "projection": current_projection,
                "rollback_receipt": rollback_receipt,
                "rollback_reason": reason.strip(),
            }
        store.remove_canonical_projection(candidate_id)
        candidate = dict(candidate)
        candidate["status"] = "recommended"
        candidate["updated_at"] = store.now()
        store.put_candidate(candidate)
        return {
            "candidate": candidate,
            "projection": store.get_canonical_projection(candidate_id),
            "rollback_receipt": rollback_receipt,
            "rollback_reason": reason.strip(),
        }
