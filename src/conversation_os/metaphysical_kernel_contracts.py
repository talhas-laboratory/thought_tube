"""Validation and invariant checks for metaphysical kernel contracts."""

from __future__ import annotations

from dataclasses import fields
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Set

from conversation_os.metaphysical_kernel import (
    BRANCH_BOUND_RECORD_KINDS,
    FRAMEWORK_SECTIONS,
    KERNEL_RECORD_KINDS,
    BranchMembership,
    Claim,
    ClaimProposition,
    KernelRecordEnvelope,
    ModelBranch,
    ProfileConformanceResult,
    ProfileDefinition,
    Provenance,
    Referent,
    RelationInstance,
    RelationParticipant,
    Scope,
    SourceFragment,
    State,
    StateCommitment,
)

MODULE_ID = "kernel.metaphysical.contracts"
CONTRACT_VERSION = "1.1.0"

MATURITY_VALUES = {
    "raw",
    "held",
    "differentiating",
    "structured",
    "stabilized_for_purpose",
    "archived",
    "released",
}
EPISTEMIC_VALUES = {
    "not_applicable",
    "unassessed",
    "candidate",
    "supported",
    "opposed",
    "both",
    "unresolved",
    "retracted",
}
GOVERNANCE_VALUES = {
    "local",
    "review_required",
    "approved_for_scope",
    "shared",
    "deprecated",
    "quarantined",
}

FORBIDDEN_KERNEL_REDEFINITIONS = frozenset(
    {
        "claim_is_state",
        "state_is_claim",
        "merge_claim_state",
        "universal_branch_id",
        "single_status_field",
    }
)


class ContractValidationError(ValueError):
    def __init__(self, code: str, message: str, section: str = "") -> None:
        self.code = code
        self.section = section
        super().__init__(message)


def _require_mapping(payload: Any, label: str) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        raise ContractValidationError(
            "invalid_payload",
            f"{label} must be a mapping",
            FRAMEWORK_SECTIONS["record_envelope"],
        )
    return payload


def envelope_from_dict(payload: Mapping[str, Any]) -> KernelRecordEnvelope:
    data = _require_mapping(payload, "envelope")
    return KernelRecordEnvelope(
        id=str(data.get("id", "")),
        record_kind=str(data.get("record_kind", "")),
        type_id=str(data.get("type_id", "")),
        created_at=str(data.get("created_at", "")),
        created_by=str(data.get("created_by", "")),
        provenance_id=str(data.get("provenance_id", "")),
        maturity_status=data.get("maturity_status", "raw"),  # type: ignore[arg-type]
        epistemic_status=data.get("epistemic_status", "not_applicable"),  # type: ignore[arg-type]
        governance_status=data.get("governance_status", "local"),  # type: ignore[arg-type]
        scope_id=str(data.get("scope_id", "")),
        version=str(data.get("version", "1")),
        visibility_policy=str(data.get("visibility_policy", "private")),
    )


def validate_envelope(envelope: KernelRecordEnvelope) -> List[str]:
    """Validate universal record envelope (§4.1)."""
    errors: List[str] = []
    section = FRAMEWORK_SECTIONS["record_envelope"]
    if not envelope.id:
        errors.append(f"[{section}] envelope.id is required")
    if envelope.record_kind not in KERNEL_RECORD_KINDS:
        errors.append(f"[{section}] unknown record_kind: {envelope.record_kind}")
    if not envelope.type_id:
        errors.append(f"[{section}] envelope.type_id is required")
    if not envelope.created_at:
        errors.append(f"[{section}] envelope.created_at is required")
    if not envelope.created_by:
        errors.append(f"[{section}] envelope.created_by is required")
    if not envelope.provenance_id:
        errors.append(f"[{section}] envelope.provenance_id is required")
    if envelope.maturity_status not in MATURITY_VALUES:
        errors.append(f"[{section}] invalid maturity_status")
    if envelope.epistemic_status not in EPISTEMIC_VALUES:
        errors.append(f"[{section}] invalid epistemic_status")
    if envelope.governance_status not in GOVERNANCE_VALUES:
        errors.append(f"[{section}] invalid governance_status")
    return errors


def validate_lifecycle_independence(envelope: KernelRecordEnvelope) -> List[str]:
    """Maturity, epistemic, and governance must remain orthogonal (§22.1)."""
    section = FRAMEWORK_SECTIONS["lifecycle_axes"]
    errors: List[str] = []
    if envelope.maturity_status == envelope.epistemic_status:
        errors.append(f"[{section}] maturity_status must not equal epistemic_status")
    if envelope.maturity_status == envelope.governance_status:
        errors.append(f"[{section}] maturity_status must not equal governance_status")
    if envelope.epistemic_status == envelope.governance_status:
        if envelope.epistemic_status != "not_applicable":
            errors.append(f"[{section}] epistemic_status must not equal governance_status")
    collapsed = {envelope.maturity_status, envelope.epistemic_status, envelope.governance_status}
    if len(collapsed) == 1:
        errors.append(f"[{section}] lifecycle axes collapsed into one value")
    return errors


def validate_state_claim_disjoint(record_kind: str) -> List[str]:
    """State and Claim are disjoint functional roles (§6.1)."""
    section = FRAMEWORK_SECTIONS["state"]
    if record_kind == "claim" and record_kind == "state":
        return [f"[{section}] record cannot be both State and Claim"]
    return []


def validate_claim(claim: Claim, memberships: Sequence[BranchMembership]) -> List[str]:
    """Branch-scoped assertion rules (§6.2)."""
    section = FRAMEWORK_SECTIONS["claim"]
    errors = validate_envelope(claim.envelope)
    errors.extend(validate_lifecycle_independence(claim.envelope))
    if claim.envelope.record_kind != "claim":
        errors.append(f"[{section}] envelope.record_kind must be claim")
    if not claim.branch_id:
        errors.append(f"[{section}] claim.branch_id is required")
    if not claim.scope_id:
        errors.append(f"[{section}] claim.scope_id is required")
    if not claim.claimant:
        errors.append(f"[{section}] claim.claimant is required")
    if not claim.proposition.predicate:
        errors.append(f"[{section}] claim.proposition.predicate is required")
    claim_memberships = [
        membership
        for membership in memberships
        if membership.record_id == claim.envelope.id and membership.branch_id == claim.branch_id
    ]
    if not claim_memberships:
        errors.append(f"[{FRAMEWORK_SECTIONS['branch_membership']}] claim requires BranchMembership")
    return errors


def validate_state(
    state: State,
    commitments: Sequence[StateCommitment],
    memberships: Sequence[BranchMembership],
    claims: Optional[Sequence[Claim]] = None,
) -> List[str]:
    """Represented State requires explicit adoption path (§5.4, §6.11)."""
    section = FRAMEWORK_SECTIONS["state"]
    errors = validate_envelope(state.envelope)
    if state.envelope.record_kind != "state":
        errors.append(f"[{section}] envelope.record_kind must be state")
    if not state.subject_refs:
        errors.append(f"[{section}] state.subject_refs is required")
    if not state.state_type:
        errors.append(f"[{section}] state.state_type is required")
    if not state.valid_scope_id:
        errors.append(f"[{section}] state.valid_scope_id is required")
    matching_commitments = [
        item for item in commitments if item.resulting_state_id == state.envelope.id
    ]
    if not state.commitment_id and not matching_commitments:
        errors.append(
            f"[{FRAMEWORK_SECTIONS['state_commitment']}] state requires StateCommitment"
        )
    branch_memberships = [
        item for item in memberships if item.record_id == state.envelope.id
    ]
    if not branch_memberships:
        errors.append(f"[{FRAMEWORK_SECTIONS['branch_membership']}] state requires BranchMembership")
    if claims is not None:
        errors.extend(
            validate_state_adoption_links(state, commitments, memberships, claims)
        )
    return errors


def validate_state_adoption_links(
    state: State,
    commitments: Sequence[StateCommitment],
    memberships: Sequence[BranchMembership],
    claims: Sequence[Claim],
) -> List[str]:
    """State, StateCommitment, BranchMembership, and source Claims must agree (§5.16, §6.11)."""
    section_sc = FRAMEWORK_SECTIONS["state_commitment"]
    section_bm = FRAMEWORK_SECTIONS["branch_membership"]
    errors: List[str] = []

    commitments_by_id = {item.envelope.id: item for item in commitments}
    commitments_for_state = [
        item for item in commitments if item.resulting_state_id == state.envelope.id
    ]

    active_commitment: Optional[StateCommitment] = None
    if state.commitment_id:
        linked = commitments_by_id.get(state.commitment_id)
        if linked is None:
            errors.append(f"[{section_sc}] state.commitment_id does not resolve to StateCommitment")
        elif linked.resulting_state_id != state.envelope.id:
            errors.append(
                f"[{section_sc}] state.commitment_id must reference commitment adopting this state"
            )
        else:
            active_commitment = linked
    elif len(commitments_for_state) == 1:
        active_commitment = commitments_for_state[0]
    elif len(commitments_for_state) > 1:
        errors.append(f"[{section_sc}] state requires explicit commitment_id when multiple commitments exist")

    if active_commitment is None:
        return errors

    aligned_memberships = [
        membership
        for membership in memberships
        if membership.record_id == state.envelope.id
        and membership.branch_id == active_commitment.branch_id
        and membership.effective_scope_id == active_commitment.scope_id
    ]
    if not aligned_memberships:
        errors.append(
            f"[{section_bm}] state BranchMembership must match StateCommitment branch and scope"
        )

    if state.valid_scope_id != active_commitment.scope_id:
        errors.append(f"[{section_sc}] state.valid_scope_id must match StateCommitment scope_id")

    claims_by_id = {item.envelope.id: item for item in claims}
    for claim_id in active_commitment.source_claim_ids:
        claim = claims_by_id.get(claim_id)
        if claim is None:
            errors.append(f"[{section_sc}] source claim {claim_id} does not exist")
            continue
        if claim.branch_id != active_commitment.branch_id:
            errors.append(
                f"[{section_sc}] source claim {claim_id} branch incompatible with commitment"
            )
        if claim.scope_id != active_commitment.scope_id:
            errors.append(
                f"[{section_sc}] source claim {claim_id} scope incompatible with commitment"
            )
        claim_memberships = [
            membership
            for membership in memberships
            if membership.record_id == claim_id and membership.branch_id == claim.branch_id
        ]
        if not claim_memberships:
            errors.append(f"[{section_bm}] source claim {claim_id} requires BranchMembership")

    commitment_memberships = [
        membership
        for membership in memberships
        if membership.record_id == active_commitment.envelope.id
        and membership.branch_id == active_commitment.branch_id
        and membership.effective_scope_id == active_commitment.scope_id
    ]
    if not commitment_memberships:
        errors.append(f"[{section_bm}] state_commitment requires BranchMembership")

    return errors


def validate_state_commitment(
    commitment: StateCommitment,
    memberships: Optional[Sequence[BranchMembership]] = None,
) -> List[str]:
    section = FRAMEWORK_SECTIONS["state_commitment"]
    errors = validate_envelope(commitment.envelope)
    if commitment.envelope.record_kind != "state_commitment":
        errors.append(f"[{section}] envelope.record_kind must be state_commitment")
    if not commitment.source_claim_ids:
        errors.append(f"[{section}] source_claim_ids is required")
    if not commitment.resulting_state_id:
        errors.append(f"[{section}] resulting_state_id is required")
    if not commitment.branch_id:
        errors.append(f"[{section}] branch_id is required")
    if not commitment.scope_id:
        errors.append(f"[{section}] scope_id is required")
    if not commitment.responsible_actor:
        errors.append(f"[{section}] responsible_actor is required")
    if not commitment.commitment_provenance_id:
        errors.append(f"[{section}] commitment_provenance_id is required")
    if memberships is not None:
        commitment_memberships = [
            membership
            for membership in memberships
            if membership.record_id == commitment.envelope.id
            and membership.branch_id == commitment.branch_id
            and membership.effective_scope_id == commitment.scope_id
        ]
        if not commitment_memberships:
            errors.append(
                f"[{FRAMEWORK_SECTIONS['branch_membership']}] state_commitment requires BranchMembership"
            )
    return errors


def validate_branch_membership(membership: BranchMembership) -> List[str]:
    section = FRAMEWORK_SECTIONS["branch_membership"]
    errors = validate_envelope(membership.envelope)
    if membership.envelope.record_kind != "branch_membership":
        errors.append(f"[{section}] envelope.record_kind must be branch_membership")
    if not membership.record_id:
        errors.append(f"[{section}] record_id is required")
    if not membership.branch_id:
        errors.append(f"[{section}] branch_id is required")
    if not membership.effective_scope_id:
        errors.append(f"[{section}] effective_scope_id is required")
    if not membership.introduced_by:
        errors.append(f"[{section}] introduced_by is required")
    if not membership.membership_provenance_id:
        errors.append(f"[{section}] membership_provenance_id is required")
    return errors


def validate_provenance_closure(
    provenance: Provenance,
    known_source_fragment_ids: Optional[Set[str]] = None,
) -> List[str]:
    section = FRAMEWORK_SECTIONS["provenance"]
    errors = validate_envelope(provenance.envelope)
    if provenance.envelope.record_kind != "provenance":
        errors.append(f"[{section}] envelope.record_kind must be provenance")
    if not provenance.source_refs:
        errors.append(f"[{section}] provenance.source_refs must terminate in sources")
    if known_source_fragment_ids is not None:
        if not any(ref in known_source_fragment_ids for ref in provenance.source_refs):
            errors.append(f"[{section}] provenance lacks terminating SourceFragment")
    return errors


def validate_profile_definition(profile: ProfileDefinition) -> List[str]:
    section = FRAMEWORK_SECTIONS["profile_definition"]
    errors = validate_envelope(profile.envelope)
    if profile.envelope.record_kind != "profile_definition":
        errors.append(f"[{section}] envelope.record_kind must be profile_definition")
    if not profile.profile_id:
        errors.append(f"[{section}] profile_id is required")
    if not profile.profile_version:
        errors.append(f"[{section}] profile_version is required")
    if not profile.kernel_records_used:
        errors.append(f"[{section}] kernel_records_used is required")
    forbidden = set(profile.forbidden_kernel_redefinitions) & FORBIDDEN_KERNEL_REDEFINITIONS
    if forbidden:
        errors.append(f"[{section}] profile redefines kernel semantics: {sorted(forbidden)}")
    if profile.profile_id in profile.profile_dependencies:
        errors.append(f"[{section}] profile_dependencies must be acyclic")
    return errors


def validate_profile_conformance(result: ProfileConformanceResult) -> List[str]:
    section = FRAMEWORK_SECTIONS["profile_conformance_result"]
    errors = validate_envelope(result.envelope)
    if result.envelope.record_kind != "profile_conformance_result":
        errors.append(f"[{section}] envelope.record_kind must be profile_conformance_result")
    if not result.profile_definition_id:
        errors.append(f"[{section}] profile_definition_id is required")
    if not result.evaluated_record_id:
        errors.append(f"[{section}] evaluated_record_id is required")
    if result.passed and result.violations:
        errors.append(f"[{section}] passed result cannot include violations")
    if not result.passed and not result.violations:
        errors.append(f"[{section}] failed result must include violations")
    return errors


def source_fragment_from_dict(payload: Mapping[str, Any]) -> SourceFragment:
    data = _require_mapping(payload, "source_fragment")
    return SourceFragment(
        envelope=envelope_from_dict(data.get("envelope", {})),
        media_type=str(data.get("media_type", "")),
        content_pointer=str(data.get("content_pointer", "")),
        author_or_origin=str(data.get("author_or_origin", "")),
        captured_at=str(data.get("captured_at", "")),
        integrity_hash=str(data.get("integrity_hash", "")),
        source_kind=data.get("source_kind", "user_input"),  # type: ignore[arg-type]
    )


def referent_from_dict(payload: Mapping[str, Any]) -> Referent:
    data = _require_mapping(payload, "referent")
    return Referent(
        envelope=envelope_from_dict(data.get("envelope", {})),
        canonical_label=str(data.get("canonical_label", "")),
        aliases=[str(value) for value in data.get("aliases", []) or []],
        identity_policy_id=str(data.get("identity_policy_id", "")),
    )


def scope_from_dict(payload: Mapping[str, Any]) -> Scope:
    data = _require_mapping(payload, "scope")
    return Scope(
        envelope=envelope_from_dict(data.get("envelope", {})),
        modal_scope=data.get("modal_scope", "actual"),  # type: ignore[arg-type]
        temporal_scope=str(data.get("temporal_scope", "")),
        spatial_scope=str(data.get("spatial_scope", "")),
        scale=str(data.get("scale", "")),
        boundary_rule=str(data.get("boundary_rule", "")),
        domain=str(data.get("domain", "")),
        task=str(data.get("task", "")),
        context_refs=[str(value) for value in data.get("context_refs", []) or []],
        semantic_address=dict(data.get("semantic_address", {}) or {}),
    )


def claim_from_dict(payload: Mapping[str, Any]) -> Claim:
    data = _require_mapping(payload, "claim")
    proposition_payload = _require_mapping(data.get("proposition", {}), "proposition")
    return Claim(
        envelope=envelope_from_dict(data.get("envelope", {})),
        proposition=ClaimProposition(
            predicate=str(proposition_payload.get("predicate", "")),
            arguments=[str(value) for value in proposition_payload.get("arguments", []) or []],
        ),
        claimant=str(data.get("claimant", "")),
        branch_id=str(data.get("branch_id", "")),
        scope_id=str(data.get("scope_id", "")),
        polarity=data.get("polarity", "affirmative"),  # type: ignore[arg-type]
    )


def state_from_dict(payload: Mapping[str, Any]) -> State:
    data = _require_mapping(payload, "state")
    return State(
        envelope=envelope_from_dict(data.get("envelope", {})),
        subject_refs=[str(value) for value in data.get("subject_refs", []) or []],
        state_type=str(data.get("state_type", "")),
        value=data.get("value"),
        value_type=str(data.get("value_type", "")),
        valid_scope_id=str(data.get("valid_scope_id", "")),
        commitment_id=str(data.get("commitment_id", "")),
    )


def relation_instance_from_dict(payload: Mapping[str, Any]) -> RelationInstance:
    data = _require_mapping(payload, "relation_instance")
    participants = [
        RelationParticipant(role=str(item.get("role", "")), ref=str(item.get("ref", "")))
        for item in data.get("participants", []) or []
        if isinstance(item, dict)
    ]
    return RelationInstance(
        envelope=envelope_from_dict(data.get("envelope", {})),
        type_id=str(data.get("type_id", "")),
        participants=participants,
        scope_id=str(data.get("scope_id", "")),
        qualifiers=dict(data.get("qualifiers", {}) or {}),
    )


def provenance_from_dict(payload: Mapping[str, Any]) -> Provenance:
    data = _require_mapping(payload, "provenance")
    return Provenance(
        envelope=envelope_from_dict(data.get("envelope", {})),
        source_refs=[str(value) for value in data.get("source_refs", []) or []],
        derivation_steps=list(data.get("derivation_steps", []) or []),
        model_or_agent=str(data.get("model_or_agent", "")),
        prompt_or_rule_version=str(data.get("prompt_or_rule_version", "")),
        user_confirmations=[str(value) for value in data.get("user_confirmations", []) or []],
        prior_versions=[str(value) for value in data.get("prior_versions", []) or []],
    )


def model_branch_from_dict(payload: Mapping[str, Any]) -> ModelBranch:
    data = _require_mapping(payload, "model_branch")
    return ModelBranch(
        envelope=envelope_from_dict(data.get("envelope", {})),
        parent_branch_id=str(data.get("parent_branch_id", "")),
        branch_kind=data.get("branch_kind", "interpretation"),  # type: ignore[arg-type]
        assumptions=[str(value) for value in data.get("assumptions", []) or []],
        included_records=[str(value) for value in data.get("included_records", []) or []],
        retracted_records=[str(value) for value in data.get("retracted_records", []) or []],
        divergence_points=[str(value) for value in data.get("divergence_points", []) or []],
        merge_status=str(data.get("merge_status", "open")),
    )


def branch_membership_from_dict(payload: Mapping[str, Any]) -> BranchMembership:
    data = _require_mapping(payload, "branch_membership")
    return BranchMembership(
        envelope=envelope_from_dict(data.get("envelope", {})),
        record_id=str(data.get("record_id", "")),
        branch_id=str(data.get("branch_id", "")),
        membership_kind=data.get("membership_kind", "asserted"),  # type: ignore[arg-type]
        effective_scope_id=str(data.get("effective_scope_id", "")),
        introduced_by=str(data.get("introduced_by", "")),
        membership_provenance_id=str(data.get("membership_provenance_id", "")),
    )


def state_commitment_from_dict(payload: Mapping[str, Any]) -> StateCommitment:
    data = _require_mapping(payload, "state_commitment")
    return StateCommitment(
        envelope=envelope_from_dict(data.get("envelope", {})),
        source_claim_ids=[str(value) for value in data.get("source_claim_ids", []) or []],
        resulting_state_id=str(data.get("resulting_state_id", "")),
        branch_id=str(data.get("branch_id", "")),
        scope_id=str(data.get("scope_id", "")),
        commitment_kind=data.get("commitment_kind", "user_confirmed"),  # type: ignore[arg-type]
        responsible_actor=str(data.get("responsible_actor", "")),
        commitment_provenance_id=str(data.get("commitment_provenance_id", "")),
        reversible=bool(data.get("reversible", True)),
    )


def profile_definition_from_dict(payload: Mapping[str, Any]) -> ProfileDefinition:
    data = _require_mapping(payload, "profile_definition")
    return ProfileDefinition(
        envelope=envelope_from_dict(data.get("envelope", {})),
        profile_id=str(data.get("profile_id", "")),
        profile_version=str(data.get("profile_version", "")),
        purpose=str(data.get("purpose", "")),
        kernel_records_used=[str(value) for value in data.get("kernel_records_used", []) or []],
        profile_record_types=[str(value) for value in data.get("profile_record_types", []) or []],
        profile_dependencies=[str(value) for value in data.get("profile_dependencies", []) or []],
        invariants=[str(value) for value in data.get("invariants", []) or []],
        steward=str(data.get("steward", "")),
        forbidden_kernel_redefinitions=[
            str(value) for value in data.get("forbidden_kernel_redefinitions", []) or []
        ],
    )


def profile_conformance_result_from_dict(payload: Mapping[str, Any]) -> ProfileConformanceResult:
    data = _require_mapping(payload, "profile_conformance_result")
    return ProfileConformanceResult(
        envelope=envelope_from_dict(data.get("envelope", {})),
        profile_definition_id=str(data.get("profile_definition_id", "")),
        profile_version=str(data.get("profile_version", "")),
        evaluated_record_id=str(data.get("evaluated_record_id", "")),
        passed=bool(data.get("passed", False)),
        violations=[str(value) for value in data.get("violations", []) or []],
        evaluated_at=str(data.get("evaluated_at", "")),
    )


def validate_fixture_bundle(bundle: Mapping[str, Any]) -> List[str]:
    """Validate a coordinated fixture bundle used in tests."""
    errors: List[str] = []
    source_fragments = {
        item.envelope.id: item
        for item in [source_fragment_from_dict(payload) for payload in bundle.get("source_fragments", [])]
    }
    provenances = [provenance_from_dict(payload) for payload in bundle.get("provenances", [])]
    memberships = [
        branch_membership_from_dict(payload) for payload in bundle.get("branch_memberships", [])
    ]
    commitments = [
        state_commitment_from_dict(payload) for payload in bundle.get("state_commitments", [])
    ]
    claims = [claim_from_dict(payload) for payload in bundle.get("claims", [])]
    states = [state_from_dict(payload) for payload in bundle.get("states", [])]
    profiles = [profile_definition_from_dict(payload) for payload in bundle.get("profile_definitions", [])]
    conformance = [
        profile_conformance_result_from_dict(payload)
        for payload in bundle.get("profile_conformance_results", [])
    ]

    for record in source_fragments.values():
        errors.extend(validate_envelope(record.envelope))

    for provenance in provenances:
        errors.extend(
            validate_provenance_closure(provenance, known_source_fragment_ids=set(source_fragments))
        )

    for membership in memberships:
        errors.extend(validate_branch_membership(membership))

    for commitment in commitments:
        errors.extend(validate_state_commitment(commitment, memberships))

    for claim in claims:
        errors.extend(validate_claim(claim, memberships))

    for state in states:
        errors.extend(validate_state(state, commitments, memberships, claims))

    for profile in profiles:
        errors.extend(validate_profile_definition(profile))

    for result in conformance:
        errors.extend(validate_profile_conformance(result))

    return errors
