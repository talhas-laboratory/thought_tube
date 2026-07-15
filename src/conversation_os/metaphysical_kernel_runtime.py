"""Phase 1 foundation vertical slice runtime (framework v1.1 §20, §29, Workstream F2)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Set

from conversation_os.metaphysical_kernel_contracts import ContractValidationError, validate_fixture_bundle
from conversation_os.metaphysical_kernel_store import FoundationStore, RECORD_COLLECTION_KEYS, RECORD_KIND_TO_KEY
from conversation_os.storage import make_id, utc_now

MODULE_ID = "kernel.metaphysical.runtime"
CONTRACT_VERSION = "1.1.0"
FRAMEWORK_SECTIONS = {
    "bounded_view": "§20.3",
    "provenance_trace": "§20.5",
    "capture": "§21.1",
    "branch": "§21.3",
    "assert": "§21.6",
    "relation": "§5.6",
    "identity_uncertainty": "§5.13",
}


@dataclass
class BoundedViewQuery:
    branch_id: str
    scope_id: str
    root_record_ids: List[str]
    max_depth: int = 3
    record_kinds: Optional[List[str]] = None
    include_retracted: bool = False


@dataclass
class BoundedViewNode:
    record_id: str
    record_kind: str
    depth: int
    branch_id: str = ""
    epistemic_status: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "record_id": self.record_id,
            "record_kind": self.record_kind,
            "depth": self.depth,
            "branch_id": self.branch_id,
            "epistemic_status": self.epistemic_status,
        }


@dataclass
class BoundedViewResult:
    query: BoundedViewQuery
    nodes: List[BoundedViewNode] = field(default_factory=list)
    truncated: bool = False
    excluded_retracted: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "framework_section": FRAMEWORK_SECTIONS["bounded_view"],
            "branch_id": self.query.branch_id,
            "scope_id": self.query.scope_id,
            "root_record_ids": list(self.query.root_record_ids),
            "max_depth": self.query.max_depth,
            "nodes": [node.to_dict() for node in self.nodes],
            "truncated": self.truncated,
            "excluded_retracted": self.excluded_retracted,
        }


@dataclass
class ProvenanceTraceStep:
    record_id: str
    record_kind: str
    role: str

    def to_dict(self) -> Dict[str, Any]:
        return {"record_id": self.record_id, "record_kind": self.record_kind, "role": self.role}


@dataclass
class ProvenanceTrace:
    start_record_id: str
    steps: List[ProvenanceTraceStep] = field(default_factory=list)
    source_fragment_ids: List[str] = field(default_factory=list)
    complete: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "framework_section": FRAMEWORK_SECTIONS["provenance_trace"],
            "start_record_id": self.start_record_id,
            "steps": [step.to_dict() for step in self.steps],
            "source_fragment_ids": list(self.source_fragment_ids),
            "complete": self.complete,
        }


class FoundationRuntime:
    """Minimal Phase 1 path from capture through bounded view and provenance."""

    def __init__(self, root: Path, *, actor: str = "service:foundation") -> None:
        self.root = root
        self.actor = actor
        self.store = FoundationStore(root)
        self._default_provenance_id: Optional[str] = None

    def _append_record(self, record: Mapping[str, Any]) -> Dict[str, Any]:
        envelope = record.get("envelope", {})
        record_kind = str(envelope.get("record_kind", "")) if isinstance(envelope, dict) else ""
        self.store.append_event(
            "append_record",
            actor=self.actor,
            record_kind=record_kind,
            record=dict(record),
        )
        return dict(record)

    def _base_envelope(
        self,
        record_id: str,
        record_kind: str,
        type_id: str,
        *,
        provenance_id: str,
        maturity_status: str = "structured",
        epistemic_status: str = "not_applicable",
        governance_status: str = "local",
        created_at: Optional[str] = None,
        created_by: Optional[str] = None,
    ) -> Dict[str, Any]:
        return {
            "id": record_id,
            "record_kind": record_kind,
            "type_id": type_id,
            "created_at": created_at or utc_now(),
            "created_by": created_by or self.actor,
            "provenance_id": provenance_id,
            "maturity_status": maturity_status,
            "epistemic_status": epistemic_status,
            "governance_status": governance_status,
        }

    def ensure_provenance(self, provenance_id: str, source_refs: List[str]) -> Dict[str, Any]:
        if not source_refs:
            structural_id = self._structural_provenance_id()
            existing = self.store.get_record(structural_id)
            if existing:
                return existing
        existing = self.store.get_record(provenance_id)
        if existing:
            return existing
        record = {
            "envelope": self._base_envelope(
                provenance_id,
                "provenance",
                "core:provenance",
                provenance_id=provenance_id,
                epistemic_status="not_applicable",
            ),
            "source_refs": list(source_refs),
            "derivation_steps": [{"step": "capture"}],
        }
        if source_refs:
            self._default_provenance_id = provenance_id
        return self._append_record(record)

    def _structural_provenance_id(self) -> str:
        if self._default_provenance_id:
            return self._default_provenance_id
        bootstrap = self.capture_source_fragment(
            content_pointer="memory://foundation/bootstrap",
            author_or_origin=self.actor,
            integrity_hash="sha256:bootstrap",
            source_kind="import",
        )
        return str(bootstrap["envelope"]["provenance_id"])

    def capture_source_fragment(
        self,
        *,
        content_pointer: str,
        author_or_origin: str,
        captured_at: Optional[str] = None,
        integrity_hash: str,
        media_type: str = "text",
        source_kind: str = "user_input",
        provenance_id: Optional[str] = None,
        maturity_status: str = "raw",
    ) -> Dict[str, Any]:
        fragment_id = make_id("sf")
        prov_id = provenance_id or make_id("prov")
        self.ensure_provenance(prov_id, [fragment_id])
        self._default_provenance_id = prov_id
        record = {
            "envelope": self._base_envelope(
                fragment_id,
                "source_fragment",
                "core:source_fragment",
                provenance_id=prov_id,
                maturity_status=maturity_status,
                epistemic_status="not_applicable",
                created_at=captured_at,
                created_by=author_or_origin,
            ),
            "media_type": media_type,
            "content_pointer": content_pointer,
            "author_or_origin": author_or_origin,
            "captured_at": captured_at or utc_now(),
            "integrity_hash": integrity_hash,
            "source_kind": source_kind,
        }
        return self._append_record(record)

    def capture_from_conversation_event(self, event: Mapping[str, Any]) -> Dict[str, Any]:
        """Bridge session_append output to SourceFragment (raw capture without inference)."""
        session_id = str(event.get("session_id", ""))
        event_id = str(event.get("event_id", make_id("event")))
        return self.capture_source_fragment(
            content_pointer=f"memory://events/{session_id}/{event_id}",
            author_or_origin=str(event.get("actor", "unknown")),
            captured_at=str(event.get("timestamp", utc_now())),
            integrity_hash=f"sha256:{event_id}",
            media_type="text",
            source_kind="user_input",
        )

    def ensure_scope(self, scope_id: str, *, domain: str = "", task: str = "") -> Dict[str, Any]:
        existing = self.store.get_record(scope_id)
        if existing:
            return existing
        prov_id = self._structural_provenance_id()
        record = {
            "envelope": self._base_envelope(
                scope_id,
                "scope",
                "core:scope",
                provenance_id=prov_id,
                epistemic_status="not_applicable",
            ),
            "modal_scope": "actual",
            "boundary_rule": f"explicit:{scope_id}",
            "domain": domain,
            "task": task,
        }
        return self._append_record(record)

    def ensure_branch(
        self,
        branch_id: str,
        *,
        parent_branch_id: str = "",
        branch_kind: str = "main",
    ) -> Dict[str, Any]:
        existing = self.store.get_record(branch_id)
        if existing:
            return existing
        prov_id = self._structural_provenance_id()
        record = {
            "envelope": self._base_envelope(
                branch_id,
                "model_branch",
                "core:model_branch",
                provenance_id=prov_id,
                epistemic_status="not_applicable",
            ),
            "parent_branch_id": parent_branch_id,
            "branch_kind": branch_kind,
        }
        return self._append_record(record)

    def resolve_referent(self, label: str, *, aliases: Optional[List[str]] = None) -> Dict[str, Any]:
        folded = self.store.fold()
        for referent in folded.get("referents", []):
            if str(referent.get("canonical_label", "")) == label:
                return referent
        referent_id = make_id("ref")
        prov_id = self._structural_provenance_id()
        record = {
            "envelope": self._base_envelope(
                referent_id,
                "referent",
                "core:referent",
                provenance_id=prov_id,
                epistemic_status="unassessed",
            ),
            "canonical_label": label,
            "aliases": list(aliases or []),
            "identity_policy_id": f"label:{label}",
        }
        return self._append_record(record)

    def attach_branch_membership(
        self,
        *,
        record_id: str,
        branch_id: str,
        scope_id: str,
        provenance_id: str,
        membership_kind: str = "asserted",
    ) -> Dict[str, Any]:
        record = self._branch_membership_record(
            record_id=record_id,
            branch_id=branch_id,
            scope_id=scope_id,
            provenance_id=provenance_id,
            membership_kind=membership_kind,
        )
        return self._append_record(record)

    def _branch_membership_record(
        self,
        *,
        record_id: str,
        branch_id: str,
        scope_id: str,
        provenance_id: str,
        membership_kind: str,
    ) -> Dict[str, Any]:
        membership_id = make_id("bm")
        return {
            "envelope": self._base_envelope(
                membership_id,
                "branch_membership",
                "core:branch_membership",
                provenance_id=provenance_id,
                epistemic_status="not_applicable",
            ),
            "record_id": record_id,
            "branch_id": branch_id,
            "membership_kind": membership_kind,
            "effective_scope_id": scope_id,
            "introduced_by": self.actor,
            "membership_provenance_id": provenance_id,
        }

    def assert_claim(
        self,
        *,
        predicate: str,
        arguments: List[str],
        branch_id: str,
        scope_id: str,
        claimant: str,
        provenance_id: str,
        polarity: str = "affirmative",
    ) -> Dict[str, Any]:
        claim_id = make_id("cl")
        record = {
            "envelope": self._base_envelope(
                claim_id,
                "claim",
                "core:claim",
                provenance_id=provenance_id,
                maturity_status="differentiating",
                epistemic_status="candidate",
                created_by=claimant,
            ),
            "proposition": {"predicate": predicate, "arguments": arguments},
            "claimant": claimant,
            "branch_id": branch_id,
            "scope_id": scope_id,
            "polarity": polarity,
        }
        self._append_record(record)
        self.attach_branch_membership(
            record_id=claim_id,
            branch_id=branch_id,
            scope_id=scope_id,
            provenance_id=provenance_id,
        )
        return record

    def commit_state_from_claims(
        self,
        *,
        source_claim_ids: List[str],
        branch_id: str,
        scope_id: str,
        subject_refs: List[str],
        state_type: str,
        value: Any,
        value_type: str,
        provenance_id: str,
        commitment_kind: str = "user_confirmed",
        responsible_actor: Optional[str] = None,
    ) -> Dict[str, Any]:
        state_id = make_id("st")
        commitment_id = make_id("sc")
        actor = responsible_actor or self.actor

        commitment = {
            "envelope": self._base_envelope(
                commitment_id,
                "state_commitment",
                "core:state_commitment",
                provenance_id=provenance_id,
                epistemic_status="supported",
                governance_status="review_required",
                created_by=actor,
            ),
            "source_claim_ids": list(source_claim_ids),
            "resulting_state_id": state_id,
            "branch_id": branch_id,
            "scope_id": scope_id,
            "commitment_kind": commitment_kind,
            "responsible_actor": actor,
            "commitment_provenance_id": provenance_id,
            "reversible": True,
        }
        state = {
            "envelope": self._base_envelope(
                state_id,
                "state",
                state_type,
                provenance_id=provenance_id,
                epistemic_status="supported",
                created_by=actor,
            ),
            "subject_refs": list(subject_refs),
            "state_type": state_type,
            "value": value,
            "value_type": value_type,
            "valid_scope_id": scope_id,
            "commitment_id": commitment_id,
        }
        commitment_membership = self._branch_membership_record(
            record_id=commitment_id,
            branch_id=branch_id,
            scope_id=scope_id,
            provenance_id=provenance_id,
            membership_kind="asserted",
        )
        state_membership = self._branch_membership_record(
            record_id=state_id,
            branch_id=branch_id,
            scope_id=scope_id,
            provenance_id=provenance_id,
            membership_kind="derived",
        )

        proposed_records = [commitment, state, commitment_membership, state_membership]
        prospective_bundle = self.current_bundle()
        for record in proposed_records:
            envelope = record["envelope"]
            collection = RECORD_KIND_TO_KEY[str(envelope["record_kind"])]
            prospective_bundle[collection] = list(prospective_bundle.get(collection, [])) + [record]
        errors = validate_fixture_bundle(prospective_bundle)
        if errors:
            raise ContractValidationError(
                "invalid_state_adoption",
                "; ".join(errors),
                "§5.16",
            )

        self.store.append_records(proposed_records, actor=self.actor)
        return {"state_commitment": commitment, "state": state}

    def retract_record(self, record_id: str, *, reason: str = "") -> Dict[str, Any]:
        return self.store.append_event(
            "retract_record",
            actor=self.actor,
            record_kind="",
            target_record_id=record_id,
            reason=reason,
        )

    def revise_claim(
        self,
        *,
        superseded_claim_id: str,
        predicate: str,
        arguments: List[str],
        branch_id: str,
        scope_id: str,
        claimant: str,
        provenance_id: str,
    ) -> Dict[str, Any]:
        self.retract_record(superseded_claim_id, reason="revised")
        revised = self.assert_claim(
            predicate=predicate,
            arguments=arguments,
            branch_id=branch_id,
            scope_id=scope_id,
            claimant=claimant,
            provenance_id=provenance_id,
        )
        revised["supersedes"] = superseded_claim_id
        return revised

    def assert_relation_instance(
        self,
        *,
        type_id: str,
        participants: List[Mapping[str, str]],
        scope_id: str,
        provenance_id: str,
        qualifiers: Optional[Mapping[str, Any]] = None,
        epistemic_status: str = "candidate",
        governance_status: str = "local",
        maturity_status: str = "differentiating",
    ) -> Dict[str, Any]:
        """Append a validated RelationInstance (§5.6). Fails closed before persistence."""
        relation_id = make_id("rel")
        if not participants or any(
            not str(item.get("role", "")).strip() or not str(item.get("ref", "")).strip()
            for item in participants
        ):
            raise ContractValidationError(
                "invalid_relation_participant",
                "every relation participant requires non-empty role and ref",
                FRAMEWORK_SECTIONS["relation"],
            )
        normalized_participants = [
            {"role": str(item["role"]), "ref": str(item["ref"])}
            for item in participants
        ]
        record = {
            "envelope": self._base_envelope(
                relation_id,
                "relation_instance",
                type_id,
                provenance_id=provenance_id,
                maturity_status=maturity_status,
                epistemic_status=epistemic_status,
                governance_status=governance_status,
            ),
            "type_id": type_id,
            "participants": normalized_participants,
            "scope_id": scope_id,
            "qualifiers": dict(qualifiers or {}),
        }
        prospective_bundle = self.current_bundle()
        prospective_bundle["relation_instances"] = list(prospective_bundle.get("relation_instances", [])) + [record]
        errors = validate_fixture_bundle(prospective_bundle)
        if errors:
            raise ContractValidationError(
                "invalid_relation_instance",
                "; ".join(errors),
                FRAMEWORK_SECTIONS["relation"],
            )
        return self._append_record(record)

    def record_identity_uncertainty(
        self,
        *,
        left_referent_id: str,
        right_referent_id: str,
        scope_id: str,
        provenance_id: str,
        relation_kind: str = "possibly_same_as",
        confidence: float = 0.5,
        rationale: str = "",
    ) -> Dict[str, Any]:
        """Conservative identity path (§5.13): relation only, never Referent merge."""
        if left_referent_id == right_referent_id:
            raise ContractValidationError(
                "identity_collapse",
                "left and right referent must differ",
                FRAMEWORK_SECTIONS["identity_uncertainty"],
            )
        for referent_id in (left_referent_id, right_referent_id):
            existing = self.store.get_record(referent_id)
            envelope = existing.get("envelope", {}) if existing else {}
            if not existing or str(envelope.get("record_kind", "")) != "referent":
                raise ContractValidationError(
                    "missing_referent",
                    f"referent not found: {referent_id}",
                    "§5.2",
                )
        kind = str(relation_kind or "possibly_same_as").strip()
        if kind == "same_as":
            raise ContractValidationError(
                "forced_identity_merge",
                "same_as requires explicit confirmation; use possibly_same_as until confirmed",
                FRAMEWORK_SECTIONS["identity_uncertainty"],
            )
        if kind not in {"possibly_same_as", "distinct_from"}:
            raise ContractValidationError(
                "unsupported_identity_relation",
                f"unsupported identity relation: {kind}",
                FRAMEWORK_SECTIONS["identity_uncertainty"],
            )
        try:
            normalized_confidence = float(confidence)
        except (TypeError, ValueError) as exc:
            raise ContractValidationError(
                "invalid_identity_confidence",
                "identity confidence must be a number between 0 and 1",
                FRAMEWORK_SECTIONS["identity_uncertainty"],
            ) from exc
        if not 0.0 <= normalized_confidence <= 1.0:
            raise ContractValidationError(
                "invalid_identity_confidence",
                "identity confidence must be between 0 and 1",
                FRAMEWORK_SECTIONS["identity_uncertainty"],
            )
        return self.assert_relation_instance(
            type_id=f"kernel:identity:{kind}",
            participants=[
                {"role": "left", "ref": left_referent_id},
                {"role": "right", "ref": right_referent_id},
            ],
            scope_id=scope_id,
            provenance_id=provenance_id,
            qualifiers={"confidence": normalized_confidence, "rationale": rationale},
            epistemic_status="unresolved",
            governance_status="review_required",
        )

    def current_bundle(self) -> Dict[str, Any]:
        folded = self.store.fold()
        return {key: folded.get(key, []) for key in RECORD_KIND_TO_KEY.values()}

    def validate_current_bundle(self) -> List[str]:
        return validate_fixture_bundle(self.current_bundle())

    def _membership_index(self) -> Dict[str, List[Dict[str, Any]]]:
        index: Dict[str, List[Dict[str, Any]]] = {}
        for membership in self.store.fold().get("branch_memberships", []):
            record_id = str(membership.get("record_id", ""))
            index.setdefault(record_id, []).append(membership)
        return index

    def _record_branch_id(self, record: Mapping[str, Any]) -> str:
        if "branch_id" in record:
            return str(record.get("branch_id", ""))
        record_id = str(record.get("envelope", {}).get("id", ""))
        memberships = self._membership_index().get(record_id, [])
        if memberships:
            return str(memberships[0].get("branch_id", ""))
        return ""

    def _is_retracted(self, record: Mapping[str, Any]) -> bool:
        if record.get("_retracted"):
            return True
        envelope = record.get("envelope", {})
        return isinstance(envelope, dict) and envelope.get("epistemic_status") == "retracted"

    def _related_record_ids(self, record: Mapping[str, Any]) -> List[str]:
        related: List[str] = []
        envelope = record.get("envelope", {})
        record_kind = str(envelope.get("record_kind", "")) if isinstance(envelope, dict) else ""
        record_id = str(envelope.get("id", "")) if isinstance(envelope, dict) else ""

        if record_kind == "claim":
            related.extend(str(value) for value in record.get("proposition", {}).get("arguments", []) or [])
        elif record_kind == "state":
            related.extend(str(value) for value in record.get("subject_refs", []) or [])
            if record.get("commitment_id"):
                related.append(str(record["commitment_id"]))
        elif record_kind == "state_commitment":
            related.extend(str(value) for value in record.get("source_claim_ids", []) or [])
            if record.get("resulting_state_id"):
                related.append(str(record["resulting_state_id"]))
        elif record_kind == "branch_membership":
            if record.get("record_id"):
                related.append(str(record["record_id"]))
        elif record_kind == "provenance":
            related.extend(str(value) for value in record.get("source_refs", []) or [])
        elif record_kind == "relation_instance":
            for participant in record.get("participants", []) or []:
                if isinstance(participant, dict) and participant.get("ref"):
                    related.append(str(participant["ref"]))

        prov_id = str(envelope.get("provenance_id", "")) if isinstance(envelope, dict) else ""
        if prov_id and prov_id != record_id:
            related.append(prov_id)
        return related

    def query_bounded_view(self, query: BoundedViewQuery) -> BoundedViewResult:
        """Task-specific bounded projection (§20.3). Fails closed on depth and branch."""
        folded = self.store.fold()
        all_records: Dict[str, Dict[str, Any]] = {}
        for key in RECORD_COLLECTION_KEYS:
            for record in folded.get(key, []):
                envelope = record.get("envelope", {})
                if isinstance(envelope, dict) and envelope.get("id"):
                    all_records[str(envelope["id"])] = record

        result = BoundedViewResult(query=query)
        visited: Set[str] = set()
        queue: List[tuple[str, int]] = [(record_id, 0) for record_id in query.root_record_ids]

        while queue:
            record_id, depth = queue.pop(0)
            if record_id in visited:
                continue
            if depth > query.max_depth:
                result.truncated = True
                continue
            visited.add(record_id)

            record = all_records.get(record_id)
            if not record:
                continue

            envelope = record.get("envelope", {})
            record_kind = str(envelope.get("record_kind", "")) if isinstance(envelope, dict) else ""
            if query.record_kinds and record_kind not in query.record_kinds:
                continue

            if self._is_retracted(record):
                result.excluded_retracted += 1
                if not query.include_retracted:
                    continue

            branch_id = self._record_branch_id(record)
            if branch_id and branch_id != query.branch_id:
                continue

            scope_id = str(record.get("scope_id", record.get("valid_scope_id", "")))
            membership_scope = ""
            memberships = self._membership_index().get(record_id, [])
            if memberships:
                membership_scope = str(memberships[0].get("effective_scope_id", ""))
            effective_scope = scope_id or membership_scope
            if effective_scope and effective_scope != query.scope_id and record_kind not in {
                "scope",
                "model_branch",
                "source_fragment",
                "provenance",
                "referent",
            }:
                continue

            result.nodes.append(
                BoundedViewNode(
                    record_id=record_id,
                    record_kind=record_kind,
                    depth=depth,
                    branch_id=branch_id,
                    epistemic_status=str(envelope.get("epistemic_status", "")) if isinstance(envelope, dict) else "",
                )
            )

            if depth < query.max_depth:
                for related_id in self._related_record_ids(record):
                    if related_id not in visited:
                        queue.append((related_id, depth + 1))

        return result

    def trace_provenance(self, start_record_id: str) -> ProvenanceTrace:
        """Traverse output → claim → provenance → source fragment (§20.5)."""
        trace = ProvenanceTrace(start_record_id=start_record_id)
        visited: Set[str] = set()
        queue: List[tuple[str, str]] = [(start_record_id, "start")]

        while queue:
            record_id, role = queue.pop(0)
            if record_id in visited:
                continue
            visited.add(record_id)

            record = self.store.get_record(record_id)
            if not record:
                continue

            envelope = record.get("envelope", {})
            record_kind = str(envelope.get("record_kind", "")) if isinstance(envelope, dict) else ""
            trace.steps.append(ProvenanceTraceStep(record_id, record_kind, role))

            if record_kind == "source_fragment":
                trace.source_fragment_ids.append(record_id)

            for related_id in self._related_record_ids(record):
                if related_id not in visited:
                    queue.append((related_id, "derived_from"))

        trace.source_fragment_ids = sorted(set(trace.source_fragment_ids))
        trace.complete = bool(trace.source_fragment_ids)
        return trace


def run_vertical_slice(
    root: Path,
    *,
    session_event: Mapping[str, Any],
    referent_label: str,
    claim_predicate: str,
    claim_arguments: List[str],
    branch_id: str = "branch_main",
    scope_id: str = "scope_session",
    adopt_state: bool = False,
    state_value: Any = None,
) -> Dict[str, Any]:
    """Execute the Phase 1 path end-to-end for tests and demos."""
    runtime = FoundationRuntime(root, actor=str(session_event.get("actor", "user:test")))

    fragment = runtime.capture_from_conversation_event(session_event)
    fragment_id = fragment["envelope"]["id"]
    prov_id = fragment["envelope"]["provenance_id"]

    runtime.ensure_scope(scope_id, task=str(session_event.get("session_id", "")))
    runtime.ensure_branch(branch_id)

    referent = runtime.resolve_referent(referent_label)
    referent_id = referent["envelope"]["id"]

    claim = runtime.assert_claim(
        predicate=claim_predicate,
        arguments=[referent_id, *claim_arguments],
        branch_id=branch_id,
        scope_id=scope_id,
        claimant=str(session_event.get("actor", "user:test")),
        provenance_id=prov_id,
    )

    adoption: Optional[Dict[str, Any]] = None
    if adopt_state:
        adoption = runtime.commit_state_from_claims(
            source_claim_ids=[claim["envelope"]["id"]],
            branch_id=branch_id,
            scope_id=scope_id,
            subject_refs=[referent_id],
            state_type="workspace:condition",
            value=state_value,
            value_type="literal",
            provenance_id=prov_id,
            responsible_actor=str(session_event.get("actor", "user:test")),
        )

    view = runtime.query_bounded_view(
        BoundedViewQuery(
            branch_id=branch_id,
            scope_id=scope_id,
            root_record_ids=[claim["envelope"]["id"]],
            max_depth=4,
        )
    )
    trace = runtime.trace_provenance(claim["envelope"]["id"])

    return {
        "source_fragment_id": fragment_id,
        "referent_id": referent_id,
        "claim_id": claim["envelope"]["id"],
        "adoption": adoption,
        "bounded_view": view.to_dict(),
        "provenance_trace": trace.to_dict(),
        "validation_errors": runtime.validate_current_bundle(),
    }


__all__ = [
    "MODULE_ID",
    "CONTRACT_VERSION",
    "FRAMEWORK_SECTIONS",
    "BoundedViewQuery",
    "BoundedViewNode",
    "BoundedViewResult",
    "ProvenanceTrace",
    "ProvenanceTraceStep",
    "FoundationRuntime",
    "run_vertical_slice",
]
