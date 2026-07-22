"""Canonical Shape port boundary for approved promotion apply and rollback."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Optional, Protocol

from conversation_os.metaphysical_kernel_profile_registry import (
    SHAPE_PROFILE_VERSION,
    ProfileRegistry,
    validate_shape_contract,
)
from conversation_os.metaphysical_kernel_runtime import FoundationRuntime
from conversation_os.shape_population.contracts import (
    CANONICAL_SHAPE_PROPOSAL_VERSION,
    CanonicalShapeProposal,
    IdempotencyConflictError,
    PopulationCandidate,
    ValidationError,
    fingerprint_payload,
)
from conversation_os.shape_population.execution_context import CAP_PROMOTION_APPLY, CAP_PROMOTION_ROLLBACK, ExecutionContext
from conversation_os.shape_projection_reader import CANONICAL_SHAPE_PROFILE_ID, migration_decision, read_shape_projections
from conversation_os.storage import make_id, utc_now

MODULE_ID = "kernel.shape_population.canonical_port"
CONTRACT_VERSION = "1.0.0"
UNAVAILABLE_REASON = "canonical_profile_unavailable"
OWNER_STORE_DIR = Path("runtime") / "foundation" / "shape_canonical"
PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "CanonicalShapePort",
    "FailClosedCanonicalPort",
    "FoundationCanonicalPort",
    "LocalRecordingCanonicalPort",
    "canonical_projection_from_records",
    "map_population_candidate_to_proposal",
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


def _closed_evidence_ref(ref: Mapping[str, Any]) -> Optional[str]:
    packet_id = str(ref.get("packet_id") or "").strip()
    block_id = str(ref.get("block_id") or "").strip()
    segment_id = str(ref.get("segment_id") or "").strip()
    if packet_id and block_id:
        return f"evidence:{packet_id}:{block_id}"
    if packet_id and segment_id:
        return f"evidence:{packet_id}:{segment_id}"
    return None


def _relation_entries(raw_relations: list[Any]) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    """Split relations into closed refs vs unresolved labels. Never merge by label alone."""
    closed: list[dict[str, Any]] = []
    closed_refs: list[str] = []
    unresolved_labels: list[str] = []
    for item in raw_relations:
        if isinstance(item, Mapping):
            relation_id = str(item.get("relation_id") or item.get("id") or "").strip()
            participants = [
                str(part).strip()
                for part in (item.get("participant_refs") or item.get("participants") or [])
                if str(part).strip()
            ]
            if relation_id and participants:
                closed.append(
                    {
                        "relation_id": relation_id,
                        "relation_type": str(item.get("relation_type") or item.get("type") or "related"),
                        "participant_refs": participants,
                        "resolution": "closed",
                    }
                )
                closed_refs.append(relation_id)
            else:
                label = str(item.get("label") or item.get("name") or item.get("statement") or "").strip()
                if label:
                    unresolved_labels.append(label)
        else:
            text = str(item or "").strip()
            if text.startswith("relation:") or text.startswith("rel:"):
                closed.append(
                    {
                        "relation_id": text,
                        "relation_type": "related",
                        "participant_refs": [],
                        "resolution": "closed_id_only",
                    }
                )
                closed_refs.append(text)
            elif text:
                unresolved_labels.append(text)
    return closed, closed_refs, unresolved_labels


def map_population_candidate_to_proposal(
    request: Mapping[str, Any],
    candidate: Mapping[str, Any],
    evaluation: Mapping[str, Any],
    approval: Mapping[str, Any],
    *,
    profile_version: str = SHAPE_PROFILE_VERSION,
) -> CanonicalShapeProposal:
    """Map a population candidate into a versioned CanonicalShapeProposal.

    ShapeCore relation_refs include only closed validated references. Label-only
    or embedding-similar strings stay in unresolved_referents / semantic_loss.
    """
    population = PopulationCandidate.from_mapping(
        {
            **dict(candidate),
            "candidate_id": candidate.get("candidate_id") or request.get("candidate_id"),
            "branch_id": candidate.get("branch_id") or request.get("branch_id") or "",
            "scope_id": candidate.get("scope_id") or request.get("scope_id") or "",
        }
    )
    observed: list[dict[str, Any]] = []
    closed_evidence_refs: list[str] = []
    for ref in population.evidence_refs:
        closed = _closed_evidence_ref(ref)
        if closed:
            closed_evidence_refs.append(closed)
            observed.append(
                {"referent_id": closed, "kind": "evidence_span", "resolution": "observed", "source": dict(ref)}
            )
        else:
            observed.append(
                {
                    "referent_id": None,
                    "kind": "evidence_span",
                    "resolution": "unresolved",
                    "source": dict(ref),
                }
            )

    relations, closed_relation_refs, unresolved_relation_labels = _relation_entries(list(population.relations))
    unresolved = [
        {"label": label, "kind": "relation_or_participant", "resolution": "unresolved", "merge_forbidden": True}
        for label in unresolved_relation_labels
    ]
    for item in observed:
        if item.get("resolution") == "unresolved":
            unresolved.append({**item, "merge_forbidden": True})

    semantic_loss: list[str] = []
    if unresolved_relation_labels:
        semantic_loss.append("label_only_relations_not_merged_into_shape_core")
    if any(item.get("resolution") == "unresolved" for item in observed if item.get("kind") == "evidence_span"):
        semantic_loss.append("evidence_refs_missing_packet_block_or_segment_ids")

    negative_evidence = [
        dict(item)
        for item in (evaluation.get("negative_evidence") or evaluation.get("anti_match_refs") or [])
        if isinstance(item, Mapping)
    ]
    anti_match_refs = [dict(item) for item in (evaluation.get("anti_match_refs") or []) if isinstance(item, Mapping)]
    competing_view = bool(evaluation.get("competing_view") or evaluation.get("disposition") == "competing_view")

    branch_id = population.branch_id or "branch:unscoped"
    scope_id = population.scope_id or "scope:unscoped"
    perspective = population.perspective or str(evaluation.get("perspective") or "population_candidate")
    scale = population.scale or "unspecified"
    temporal_scope = population.temporal_scope or "unspecified"
    provenance_id = str(
        request.get("provenance_id")
        or candidate.get("provenance_id")
        or f"provenance:population:{population.candidate_id}"
    )
    shape_core_id = f"shape-core:{population.candidate_id}"
    shape_view_id = f"shape-view:{population.candidate_id}:{perspective}"

    relation_refs = list(dict.fromkeys([*closed_relation_refs, *closed_evidence_refs]))
    focal_ref = closed_evidence_refs[0] if closed_evidence_refs else (
        closed_relation_refs[0] if closed_relation_refs else ""
    )
    if not focal_ref:
        semantic_loss.append("shape_core_focal_ref_unresolved")

    shape_core = {
        "record_type": "shape_core",
        "id": shape_core_id,
        "focal_ref": focal_ref or f"unresolved:{population.candidate_id}",
        "scope_id": scope_id,
        "branch_id": branch_id,
        "provenance_id": provenance_id,
        "relation_refs": relation_refs or [f"unresolved:{population.candidate_id}"],
        "boundary": population.boundary,
        "mechanism": population.mechanism,
        "dimensions": list(population.dimensions),
        "closed_only": True,
        "closed_complete": bool(relation_refs and closed_evidence_refs),
    }
    if not shape_core["closed_complete"] and "shape_core_incomplete_closed_refs" not in semantic_loss:
        semantic_loss.append("shape_core_incomplete_closed_refs")

    nodes = [{"id": ref, "kind": "referent"} for ref in relation_refs] or [
        {"id": f"unresolved:{population.candidate_id}", "kind": "placeholder"}
    ]
    edges = [
        {"id": rel["relation_id"], "relation_type": rel["relation_type"], "participants": rel["participant_refs"]}
        for rel in relations
    ]
    groups = [{"id": f"dimension:{dim}", "members": []} for dim in population.dimensions] or [
        {"id": "dimension:unspecified", "members": []}
    ]
    shape_view = {
        "record_type": "shape_view",
        "id": shape_view_id,
        "shape_core_id": shape_core_id,
        "semantic_address": f"shape:{population.candidate_id}",
        "abstraction_contract": f"{perspective}: {population.statement[:180]}",
        "relation_refs": list(relation_refs),
        "projection": {"nodes": nodes, "edges": edges, "groups": groups},
        "comparison_signature": {
            "role_relation_summary": population.mechanism or population.statement[:120],
            "boundary": population.boundary,
            "scale": scale,
        },
        "perspective": perspective,
        "temporal_scope": temporal_scope,
        "competing_view": competing_view,
    }

    return CanonicalShapeProposal(
        proposal_id=make_id("shape-proposal"),
        schema_version=CANONICAL_SHAPE_PROPOSAL_VERSION,
        profile_id=CANONICAL_SHAPE_PROFILE_ID,
        profile_version=profile_version,
        candidate_id=population.candidate_id,
        request_id=str(request.get("request_id") or ""),
        evaluation_id=str(evaluation.get("evaluation_id") or ""),
        approval_id=str(approval.get("approval_id") or approval.get("decision_event_id") or ""),
        observed_referents=[item for item in observed if item.get("resolution") == "observed"],
        unresolved_referents=unresolved,
        qualities=[{"label": dim, "kind": "dimension_quality"} for dim in population.dimensions],
        claimed_states=[{"statement": population.statement, "uncertainty": population.uncertainty}],
        relations=relations,
        participant_roles=[
            {"role": "participant", "referent_id": part, "relation_id": rel["relation_id"]}
            for rel in relations
            for part in rel.get("participant_refs") or []
        ],
        boundary={"text": population.boundary, "scope_id": scope_id},
        dimensions=list(population.dimensions),
        scale=scale,
        temporal_scope=temporal_scope,
        perspective=perspective,
        composition=[dict(item) for item in (candidate.get("composition") or []) if isinstance(item, Mapping)],
        influence=[dict(item) for item in (candidate.get("influence") or []) if isinstance(item, Mapping)],
        mechanisms=[{"text": population.mechanism}],
        constraints=[dict(item) for item in (candidate.get("constraints") or []) if isinstance(item, Mapping)],
        feedback=[dict(item) for item in (candidate.get("feedback") or []) if isinstance(item, Mapping)],
        delays=[dict(item) for item in (candidate.get("delays") or []) if isinstance(item, Mapping)],
        uncertainty=population.uncertainty,
        counter_hypotheses=list(population.counter_hypotheses),
        negative_evidence=negative_evidence,
        closed_relation_refs=closed_relation_refs,
        shape_core=shape_core,
        shape_view=shape_view,
        semantic_loss_warnings=semantic_loss,
        competing_view=competing_view,
        anti_match_refs=anti_match_refs,
        content_fingerprint=population.content_fingerprint or fingerprint_payload(population.to_dict()),
    )


def canonical_projection_from_records(
    request: Mapping[str, Any],
    candidate: Mapping[str, Any],
    evaluation: Mapping[str, Any],
    approval: Mapping[str, Any],
) -> dict[str, Any]:
    proposal = map_population_candidate_to_proposal(request, candidate, evaluation, approval)
    payload = proposal.to_dict()
    payload.update(
        {
            "schema_version": CONTRACT_VERSION,
            "proposal_schema_version": CANONICAL_SHAPE_PROPOSAL_VERSION,
            "profile_id": CANONICAL_SHAPE_PROFILE_ID,
            "title": candidate.get("title"),
            "statement": candidate.get("statement"),
            "boundary": candidate.get("boundary"),
            "mechanism": candidate.get("mechanism"),
            "evidence_refs": [dict(item) for item in (candidate.get("evidence_refs") or [])],
            "decision": {
                "decision": approval.get("decision"),
                "human_principal_id": approval.get("human_principal_id") or approval.get("approval_identity"),
                "reason": approval.get("reason") or approval.get("approval_reason"),
            },
            "lineage": {
                "candidate_fingerprint": candidate.get("content_fingerprint"),
                "evaluation_fingerprint": evaluation.get("content_fingerprint"),
                "request_fingerprint": request.get("content_fingerprint"),
                "proposal_fingerprint": fingerprint_payload(
                    {
                        "candidate_id": payload.get("candidate_id"),
                        "shape_core": payload.get("shape_core"),
                        "shape_view": payload.get("shape_view"),
                    }
                ),
            },
        }
    )
    return payload


@dataclass
class FailClosedCanonicalPort:
    """Production-safe placeholder that never applies."""

    root: Path

    def profile_status(self) -> dict[str, Any]:
        projection = read_shape_projections(self.root, include_legacy=False)
        canonical = dict(projection.get("canonical") or {})
        return {
            "profile_id": CANONICAL_SHAPE_PROFILE_ID,
            "available": bool(canonical.get("available")),
            "profile_version": canonical.get("profile_version"),
            "abstention_code": canonical.get("abstention_code"),
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
class FoundationCanonicalPort:
    """Apply CanonicalShapeProposal into profile:shape with versioned owner receipts."""

    root: Path
    bootstrap_profile: bool = True

    def _store_dir(self) -> Path:
        path = Path(self.root) / OWNER_STORE_DIR
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _receipt_path(self, canonical_id: str) -> Path:
        safe = canonical_id.replace("/", "_")
        return self._store_dir() / f"{safe}.json"

    def _index_path(self) -> Path:
        return self._store_dir() / "idempotency_index.json"

    def _load_index(self) -> dict[str, Any]:
        path = self._index_path()
        if not path.exists():
            return {"applies": {}, "rollbacks": {}}
        return json.loads(path.read_text(encoding="utf-8"))

    def _save_index(self, index: Mapping[str, Any]) -> None:
        self._index_path().write_text(json.dumps(index, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def profile_status(self) -> dict[str, Any]:
        projection = read_shape_projections(
            self.root,
            include_legacy=False,
            bootstrap=self.bootstrap_profile,
        )
        canonical = dict(projection.get("canonical") or {})
        return {
            "profile_id": CANONICAL_SHAPE_PROFILE_ID,
            "available": bool(canonical.get("available")),
            "profile_version": canonical.get("profile_version"),
            "abstention_code": canonical.get("abstention_code"),
            "reason": canonical.get("abstention_reason"),
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
        if self.bootstrap_profile:
            ProfileRegistry(FoundationRuntime(self.root)).bootstrap_shape_profile()
        projection = canonical_projection_from_records(request, candidate, evaluation, approval)
        projection["profile_status"] = self.profile_status()
        return projection

    def validate(self, projection: Mapping[str, Any], *, context: ExecutionContext) -> dict[str, Any]:
        context.require_capability(CAP_PROMOTION_APPLY)
        status = self.profile_status()
        if not status.get("available"):
            return {
                "valid": False,
                "status": UNAVAILABLE_REASON,
                "profile_status": status,
                "projection_fingerprint": fingerprint_payload(projection),
            }
        required = ("request_id", "candidate_id", "evaluation_id", "approval_id", "shape_core", "shape_view")
        missing = [key for key in required if projection.get(key) in (None, "", [])]
        if missing:
            raise ValidationError(f"canonical projection missing fields: {', '.join(missing)}")
        core_errors = validate_shape_contract(dict(projection.get("shape_core") or {}), "shape_core")
        view_errors = validate_shape_contract(dict(projection.get("shape_view") or {}), "shape_view")
        errors = [*core_errors, *view_errors]
        if not bool((projection.get("shape_core") or {}).get("closed_complete")):
            errors.append("shape_core requires closed validated relation/evidence refs")
        return {
            "valid": not errors,
            "status": "validated" if not errors else "invalid_shape_contract",
            "errors": errors,
            "profile_status": status,
            "semantic_loss_warnings": list(projection.get("semantic_loss_warnings") or []),
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
        validation = self.validate(projection, context=context)
        if not validation.get("valid"):
            return {
                "status": validation.get("status") or UNAVAILABLE_REASON,
                "applied": False,
                "canonical_id": "",
                "idempotency_key": idempotency_key,
                "profile_status": validation.get("profile_status"),
                "errors": list(validation.get("errors") or []),
                "dependency_receipt": {
                    "dependency": CANONICAL_SHAPE_PROFILE_ID,
                    "reason": validation.get("status") or UNAVAILABLE_REASON,
                    "migration_decision": migration_decision(),
                },
                "projection_fingerprint": validation.get("projection_fingerprint"),
            }

        fingerprint = str(validation["projection_fingerprint"])
        index = self._load_index()
        prior = dict((index.get("applies") or {}).get(idempotency_key) or {})
        if prior:
            if prior.get("projection_fingerprint") != fingerprint:
                raise IdempotencyConflictError("canonical apply idempotency key conflict")
            return dict(prior, replayed=True)

        canonical_id = f"canonical:{projection.get('candidate_id')}"
        owner_version = 1
        existing_path = self._receipt_path(canonical_id)
        if existing_path.exists():
            existing = json.loads(existing_path.read_text(encoding="utf-8"))
            owner_version = int(existing.get("owner_version") or 1) + 1

        owner_receipt = {
            "status": "applied",
            "applied": True,
            "canonical_id": canonical_id,
            "owner": "FoundationCanonicalPort",
            "owner_version": owner_version,
            "profile_id": CANONICAL_SHAPE_PROFILE_ID,
            "profile_version": (projection.get("profile_version") or SHAPE_PROFILE_VERSION),
            "proposal_schema_version": projection.get("proposal_schema_version") or CANONICAL_SHAPE_PROPOSAL_VERSION,
            "shape_core_id": (projection.get("shape_core") or {}).get("id"),
            "shape_view_id": (projection.get("shape_view") or {}).get("id"),
            "idempotency_key": idempotency_key,
            "projection_fingerprint": fingerprint,
            "semantic_loss_warnings": list(projection.get("semantic_loss_warnings") or []),
            "applied_at": utc_now(),
            "replayed": False,
            "stale": False,
            "projection": dict(projection),
        }
        existing_path.write_text(json.dumps(owner_receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        index.setdefault("applies", {})[idempotency_key] = {
            key: value for key, value in owner_receipt.items() if key != "projection"
        }
        index["applies"][idempotency_key]["projection"] = dict(projection)
        self._save_index(index)
        return dict(owner_receipt)

    def read_back(self, canonical_id: str, *, context: ExecutionContext) -> dict[str, Any]:
        context.require_capability(CAP_PROMOTION_APPLY)
        path = self._receipt_path(canonical_id)
        if not path.exists():
            return {"status": "missing", "canonical_id": canonical_id, "projection": None}
        payload = json.loads(path.read_text(encoding="utf-8"))
        return {
            "status": "stale" if payload.get("stale") else "available",
            "canonical_id": canonical_id,
            "owner_version": payload.get("owner_version"),
            "projection": dict(payload.get("projection") or {}),
            "owner_receipt": {key: value for key, value in payload.items() if key != "projection"},
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
        index = self._load_index()
        prior = dict((index.get("rollbacks") or {}).get(idempotency_key) or {})
        if prior:
            if prior.get("rollback_fingerprint") != fingerprint:
                raise IdempotencyConflictError("canonical rollback idempotency key conflict")
            return dict(prior, replayed=True)

        path = self._receipt_path(canonical_id)
        projection = None
        if path.exists():
            payload = json.loads(path.read_text(encoding="utf-8"))
            projection = dict(payload.get("projection") or {})
            projection["rolled_back"] = True
            projection["rollback_reason"] = reason.strip()
            payload["stale"] = True
            payload["rolled_back"] = True
            payload["rollback_reason"] = reason.strip()
            payload["projection"] = projection
            path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        receipt = {
            "status": "rolled_back",
            "rolled_back": True,
            "canonical_id": canonical_id,
            "reason": reason.strip(),
            "idempotency_key": idempotency_key,
            "rollback_fingerprint": fingerprint,
            "projection": projection,
            "stale": True,
            "replayed": False,
        }
        index.setdefault("rollbacks", {})[idempotency_key] = dict(receipt)
        self._save_index(index)
        return dict(receipt)


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
