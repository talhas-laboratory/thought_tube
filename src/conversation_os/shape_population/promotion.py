"""Privileged evaluation recommendation and human-gated promotion."""

from __future__ import annotations

import json
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
)
from conversation_os.shape_population.identities import (
    EVALUATOR_IDENTITY,
    assert_tool_allowed,
)
from conversation_os.shape_population.storage import PopulationStore

MODULE_ID = "kernel.shape_population.promotion"
CONTRACT_VERSION = "1.1.0"
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


def _require_context(context: ExecutionContext | None, operation: str) -> ExecutionContext:
    if context is None:
        raise AuthorizationError(f"authenticated ExecutionContext is required for {operation}")
    return context


def _projection_parity(projection: Mapping[str, Any], read_back: Mapping[str, Any]) -> bool:
    read_projection = read_back.get("projection")
    if not isinstance(read_projection, Mapping):
        return False

    def _canon(value: Any) -> str:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)

    scalar_keys = (
        "candidate_id",
        "request_id",
        "evaluation_id",
        "approval_id",
        "title",
        "statement",
        "boundary",
        "mechanism",
        "uncertainty",
    )
    for key in scalar_keys:
        if projection.get(key) != read_projection.get(key):
            return False
    for key in ("dimensions", "relationships", "evidence_refs"):
        if _canon(projection.get(key) or []) != _canon(read_projection.get(key) or []):
            return False
    for key in ("decision", "lineage"):
        if _canon(projection.get(key) or {}) != _canon(read_projection.get(key) or {}):
            return False
    return True


def request_promotion(
    candidate_id: str,
    evaluation_id: str,
    rationale: str,
    evidence_refs: list[Mapping[str, Any]],
    *,
    store: PopulationStore,
    context: ExecutionContext,
    idempotency_key: str = "",
) -> Dict[str, Any]:
    """Privileged: designated evaluator may recommend/request, never approve."""
    context = _require_context(context, "request_promotion")
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
        "run_id": context.run_id,
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
    context: ExecutionContext,
    approval_reason: str,
    decision: str = "approved",
    approval_identity: str = "",
) -> HumanApprovalEvent:
    """Immutable human authorization event. Agents cannot synthesize this as candidate state."""
    context = _require_context(context, "record_human_decision")
    context.require_capability(CAP_PROMOTION_APPROVE)
    if context.principal_kind != "human":
        raise AuthorizationError("human decision requires a human execution context")
    approval_identity = context.principal_id
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
    context: ExecutionContext,
    approval_reason: str,
    decision: str = "approved",
    approval_identity: str = "",
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
    context: ExecutionContext,
    canonical_port: Optional[CanonicalShapePort] = None,
    idempotency_key: str = "",
    approval_identity: str = "",
    approval_reason: str = "",
) -> Dict[str, Any]:
    """Privileged: only after a valid immutable human approval event."""
    context = _require_context(context, "apply_promotion")
    context.require_capability(CAP_PROMOTION_APPLY)
    if context.principal_kind == "agent":
        assert_tool_allowed(context.principal_id, "apply_promotion")
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
    if approval.get("approval_identity") == request.get("requester_identity"):
        raise AuthorizationError("evaluator cannot approve its own promotion request")

    if canonical_port is None:
        canonical_port = FailClosedCanonicalPort(Path(store.root))

    with store.transaction():
        candidate = store.get_candidate(request["candidate_id"])
        if candidate is None:
            raise ValidationError("candidate missing")
        if candidate.get("status") == "canonical" and store.get_canonical_projection(candidate["candidate_id"]):
            return {
                "candidate": candidate,
                "projection": store.get_canonical_projection(candidate["candidate_id"]),
                "replayed": True,
            }
        if candidate.get("status") not in {"promotion_requested", "recommended", "approved"}:
            # approved request status is on the promotion row; candidate stays promotion_requested
            if candidate.get("status") not in {"promotion_requested", "recommended"}:
                raise ForbiddenTransitionError(f"cannot promote from status {candidate.get('status')}")
        evaluation = store.get_evaluation(request["evaluation_id"])
        if evaluation is None:
            raise ValidationError("evaluation missing")

        applying = dict(request)
        applying["status"] = "applying"
        store.put_promotion(applying)

        projection = canonical_port.prepare(request, candidate, evaluation, approval, context=context)
        validation = canonical_port.validate(projection, context=context)
        if not validation.get("valid"):
            applying["status"] = "approved"
            store.put_promotion(applying)
            raise ValidationError(
                f"canonical projection validation failed: {validation.get('status') or 'invalid'}"
            )
        canonical_key = idempotency_key or f"canonical-apply:{request_id}:{candidate['candidate_id']}"
        canonical_receipt = canonical_port.apply(projection, idempotency_key=canonical_key, context=context)
        if not canonical_receipt.get("applied"):
            applying["status"] = "approved"
            store.put_promotion(applying)
            return {
                "candidate": candidate,
                "projection": None,
                "approval": approval,
                "canonical_receipt": canonical_receipt,
                "validation": validation,
                "replayed": False,
            }
        read_back = canonical_port.read_back(str(canonical_receipt.get("canonical_id") or ""), context=context)
        if read_back.get("status") != "available" or not _projection_parity(projection, read_back):
            # Do not mark local candidate canonical without confirmed read-back parity.
            rollback = getattr(canonical_port, "rollback", None)
            if callable(rollback):
                rollback(
                    str(canonical_receipt.get("canonical_id") or ""),
                    reason="read_back_parity_failed",
                    idempotency_key=f"canonical-rollback-parity:{request_id}",
                    context=context,
                )
            applying["status"] = "approved"
            store.put_promotion(applying)
            raise ValidationError("canonical read-back parity failed")
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
            "validation": validation,
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
            "validation": validation,
            "replayed": False,
        }


def rollback_promotion(
    candidate_id: str,
    *,
    store: PopulationStore,
    context: ExecutionContext,
    reason: str,
    canonical_port: Optional[CanonicalShapePort] = None,
    idempotency_key: str = "",
    authority_identity: str = "",
) -> Dict[str, Any]:
    context = _require_context(context, "rollback_promotion")
    context.require_capability(CAP_PROMOTION_ROLLBACK)
    if not reason.strip():
        raise ValidationError("rollback reason required")
    if canonical_port is None:
        canonical_port = FailClosedCanonicalPort(Path(store.root))
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
        # Append-only tombstone: keep prior apply receipt and record rollback on top.
        store.put_canonical_rollback_tombstone(
            candidate_id,
            request_id=str((current_projection or {}).get("request_id") or ""),
            canonical_id=canonical_id,
            reason=reason.strip(),
            rollback_receipt=rollback_receipt,
            prior_projection=current_projection,
        )
        candidate = dict(candidate)
        candidate["status"] = "recommended"
        candidate["updated_at"] = store.now()
        store.put_candidate(candidate)
        return {
            "candidate": candidate,
            "projection": store.get_canonical_projection(candidate_id),
            "tombstone": store.get_canonical_projection_receipt(candidate_id),
            "rollback_receipt": rollback_receipt,
            "rollback_reason": reason.strip(),
        }
