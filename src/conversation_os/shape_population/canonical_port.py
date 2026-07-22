"""Canonical Shape port boundary for approved promotion apply and rollback."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Protocol

from conversation_os.shape_population.contracts import IdempotencyConflictError, ValidationError, fingerprint_payload
from conversation_os.shape_population.execution_context import CAP_PROMOTION_APPLY, CAP_PROMOTION_ROLLBACK, ExecutionContext
from conversation_os.shape_projection_reader import CANONICAL_SHAPE_PROFILE_ID, migration_decision, read_shape_projections

MODULE_ID = "kernel.shape_population.canonical_port"
CONTRACT_VERSION = "1.0.0"
UNAVAILABLE_REASON = "canonical_profile_unavailable"
PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "CanonicalShapePort",
    "FailClosedCanonicalPort",
    "LocalRecordingCanonicalPort",
    "canonical_projection_from_records",
)
__all__ = list(PUBLIC_API)


class CanonicalShapePort(Protocol):
    def prepare(
        self,
        request: Mapping[str, Any],
        candidate: Mapping[str, Any],
        evaluation: Mapping[str, Any],
        approval: Mapping[str, Any],
        *,
        context: ExecutionContext,
    ) -> dict[str, Any]:
        ...

    def validate(self, projection: Mapping[str, Any], *, context: ExecutionContext) -> dict[str, Any]:
        ...

    def apply(
        self,
        projection: Mapping[str, Any],
        *,
        idempotency_key: str,
        context: ExecutionContext,
    ) -> dict[str, Any]:
        ...

    def read_back(self, canonical_id: str, *, context: ExecutionContext) -> dict[str, Any]:
        ...

    def rollback(
        self,
        canonical_id: str,
        *,
        reason: str,
        idempotency_key: str,
        context: ExecutionContext,
    ) -> dict[str, Any]:
        ...


def canonical_projection_from_records(
    request: Mapping[str, Any],
    candidate: Mapping[str, Any],
    evaluation: Mapping[str, Any],
    approval: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": CONTRACT_VERSION,
        "profile_id": CANONICAL_SHAPE_PROFILE_ID,
        "request_id": request.get("request_id"),
        "candidate_id": candidate.get("candidate_id"),
        "evaluation_id": evaluation.get("evaluation_id"),
        "approval_id": approval.get("approval_id") or approval.get("decision_event_id"),
        "title": candidate.get("title"),
        "statement": candidate.get("statement"),
        "boundary": candidate.get("boundary"),
        "mechanism": candidate.get("mechanism"),
        "dimensions": list(candidate.get("dimensions") or []),
        "relationships": list(candidate.get("relations") or []),
        "evidence_refs": [dict(item) for item in (candidate.get("evidence_refs") or [])],
        "uncertainty": candidate.get("uncertainty"),
        "decision": {
            "decision": approval.get("decision"),
            "human_principal_id": approval.get("human_principal_id") or approval.get("approval_identity"),
            "reason": approval.get("reason") or approval.get("approval_reason"),
        },
        "lineage": {
            "candidate_fingerprint": candidate.get("content_fingerprint"),
            "evaluation_fingerprint": evaluation.get("content_fingerprint"),
            "request_fingerprint": request.get("content_fingerprint"),
        },
    }


@dataclass
class FailClosedCanonicalPort:
    """Production-safe placeholder until the canonical Shape profile exists."""

    root: Path

    def profile_status(self) -> dict[str, Any]:
        projection = read_shape_projections(self.root, include_legacy=False)
        canonical = dict(projection.get("canonical") or {})
        return {
            "profile_id": CANONICAL_SHAPE_PROFILE_ID,
            "available": bool(canonical.get("available")),
            "profile_version": canonical.get("profile_version"),
            "reason": canonical.get("abstention_reason") or UNAVAILABLE_REASON,
            "migration_decision": migration_decision(),
        }

    def prepare(
        self,
        request: Mapping[str, Any],
        candidate: Mapping[str, Any],
        evaluation: Mapping[str, Any],
        approval: Mapping[str, Any],
        *,
        context: ExecutionContext,
    ) -> dict[str, Any]:
        context.require_capability(CAP_PROMOTION_APPLY)
        projection = canonical_projection_from_records(request, candidate, evaluation, approval)
        projection["profile_status"] = self.profile_status()
        return projection

    def validate(self, projection: Mapping[str, Any], *, context: ExecutionContext) -> dict[str, Any]:
        context.require_capability(CAP_PROMOTION_APPLY)
        status = self.profile_status()
        return {
            "valid": False,
            "status": UNAVAILABLE_REASON,
            "profile_status": status,
            "projection_fingerprint": fingerprint_payload(projection),
        }

    def apply(
        self,
        projection: Mapping[str, Any],
        *,
        idempotency_key: str,
        context: ExecutionContext,
    ) -> dict[str, Any]:
        context.require_capability(CAP_PROMOTION_APPLY)
        return {
            "status": UNAVAILABLE_REASON,
            "applied": False,
            "canonical_id": "",
            "idempotency_key": idempotency_key,
            "profile_status": self.profile_status(),
            "dependency_receipt": {
                "dependency": CANONICAL_SHAPE_PROFILE_ID,
                "reason": UNAVAILABLE_REASON,
                "migration_decision": migration_decision(),
            },
            "projection_fingerprint": fingerprint_payload(projection),
        }

    def read_back(self, canonical_id: str, *, context: ExecutionContext) -> dict[str, Any]:
        context.require_capability(CAP_PROMOTION_APPLY)
        return {
            "status": UNAVAILABLE_REASON,
            "canonical_id": canonical_id,
            "projection": None,
            "profile_status": self.profile_status(),
        }

    def rollback(
        self,
        canonical_id: str,
        *,
        reason: str,
        idempotency_key: str,
        context: ExecutionContext,
    ) -> dict[str, Any]:
        context.require_capability(CAP_PROMOTION_ROLLBACK)
        return {
            "status": UNAVAILABLE_REASON,
            "rolled_back": False,
            "canonical_id": canonical_id,
            "reason": reason,
            "idempotency_key": idempotency_key,
            "profile_status": self.profile_status(),
        }


@dataclass
class LocalRecordingCanonicalPort:
    """In-memory test port with exactly-once idempotency semantics."""

    applies: dict[str, dict[str, Any]] = field(default_factory=dict)
    rollbacks: dict[str, dict[str, Any]] = field(default_factory=dict)
    projections: dict[str, dict[str, Any]] = field(default_factory=dict)
    _fingerprints: dict[str, str] = field(default_factory=dict)

    def prepare(
        self,
        request: Mapping[str, Any],
        candidate: Mapping[str, Any],
        evaluation: Mapping[str, Any],
        approval: Mapping[str, Any],
        *,
        context: ExecutionContext,
    ) -> dict[str, Any]:
        context.require_capability(CAP_PROMOTION_APPLY)
        return canonical_projection_from_records(request, candidate, evaluation, approval)

    def validate(self, projection: Mapping[str, Any], *, context: ExecutionContext) -> dict[str, Any]:
        context.require_capability(CAP_PROMOTION_APPLY)
        required = ("request_id", "candidate_id", "evaluation_id", "approval_id", "evidence_refs")
        missing = [key for key in required if projection.get(key) in (None, "", [])]
        if missing:
            raise ValidationError(f"canonical projection missing fields: {', '.join(missing)}")
        return {
            "valid": True,
            "status": "validated",
            "projection_fingerprint": fingerprint_payload(projection),
        }

    def apply(
        self,
        projection: Mapping[str, Any],
        *,
        idempotency_key: str,
        context: ExecutionContext,
    ) -> dict[str, Any]:
        context.require_capability(CAP_PROMOTION_APPLY)
        if not idempotency_key:
            raise ValidationError("canonical idempotency_key required")
        fingerprint = fingerprint_payload(projection)
        if idempotency_key in self.applies:
            if self._fingerprints[idempotency_key] != fingerprint:
                raise IdempotencyConflictError("canonical apply idempotency key conflict")
            return dict(self.applies[idempotency_key], replayed=True)
        canonical_id = f"canonical:{projection.get('candidate_id')}"
        receipt = {
            "status": "applied",
            "applied": True,
            "canonical_id": canonical_id,
            "idempotency_key": idempotency_key,
            "projection_fingerprint": fingerprint,
            "projection": dict(projection),
            "replayed": False,
        }
        self.applies[idempotency_key] = dict(receipt)
        self._fingerprints[idempotency_key] = fingerprint
        self.projections[canonical_id] = dict(projection, canonical_id=canonical_id)
        return dict(receipt)

    def read_back(self, canonical_id: str, *, context: ExecutionContext) -> dict[str, Any]:
        context.require_capability(CAP_PROMOTION_APPLY)
        projection = self.projections.get(canonical_id)
        return {
            "status": "available" if projection is not None else "missing",
            "canonical_id": canonical_id,
            "projection": None if projection is None else dict(projection),
        }

    def rollback(
        self,
        canonical_id: str,
        *,
        reason: str,
        idempotency_key: str,
        context: ExecutionContext,
    ) -> dict[str, Any]:
        context.require_capability(CAP_PROMOTION_ROLLBACK)
        if not reason.strip():
            raise ValidationError("rollback reason required")
        fingerprint = fingerprint_payload({"canonical_id": canonical_id, "reason": reason.strip()})
        if idempotency_key in self.rollbacks:
            if self.rollbacks[idempotency_key]["rollback_fingerprint"] != fingerprint:
                raise IdempotencyConflictError("canonical rollback idempotency key conflict")
            return dict(self.rollbacks[idempotency_key], replayed=True)
        projection = self.projections.get(canonical_id)
        tombstone = None if projection is None else dict(projection, rollback_reason=reason.strip(), rolled_back=True)
        if tombstone is not None:
            self.projections[canonical_id] = tombstone
        receipt = {
            "status": "rolled_back",
            "rolled_back": True,
            "canonical_id": canonical_id,
            "reason": reason.strip(),
            "idempotency_key": idempotency_key,
            "rollback_fingerprint": fingerprint,
            "projection": tombstone,
            "replayed": False,
        }
        self.rollbacks[idempotency_key] = dict(receipt)
        return dict(receipt)
