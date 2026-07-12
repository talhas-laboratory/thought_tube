"""Metaphysical kernel record contracts (framework v1.1 §4–6, §22).

Authority: docs/workspaces/unified-framework-synthesis/sources/
thought-tube-unified-metaphysical-modeling-framework-v1.1.md
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Literal, Optional

MODULE_ID = "kernel.metaphysical.records"
CONTRACT_VERSION = "1.1.0"
FRAMEWORK_AUTHORITY = (
    "docs/workspaces/unified-framework-synthesis/sources/"
    "thought-tube-unified-metaphysical-modeling-framework-v1.1.md"
)

MaturityStatus = Literal[
    "raw",
    "held",
    "differentiating",
    "structured",
    "stabilized_for_purpose",
    "archived",
    "released",
]
EpistemicStatus = Literal[
    "not_applicable",
    "unassessed",
    "candidate",
    "supported",
    "opposed",
    "both",
    "unresolved",
    "retracted",
]
GovernanceStatus = Literal[
    "local",
    "review_required",
    "approved_for_scope",
    "shared",
    "deprecated",
    "quarantined",
]

KERNEL_RECORD_KINDS = frozenset(
    {
        "source_fragment",
        "referent",
        "scope",
        "state",
        "claim",
        "relation_instance",
        "provenance",
        "model_branch",
        "branch_membership",
        "state_commitment",
        "profile_definition",
        "profile_conformance_result",
    }
)

BRANCH_BOUND_RECORD_KINDS = frozenset({"claim", "state", "state_commitment"})

FRAMEWORK_SECTIONS: Dict[str, str] = {
    "record_envelope": "§4.1",
    "source_fragment": "§5.1",
    "referent": "§5.2",
    "scope": "§5.3",
    "state": "§5.4",
    "relation_instance": "§5.6",
    "claim": "§5.7",
    "provenance": "§5.10",
    "model_branch": "§5.11",
    "branch_membership": "§5.15",
    "state_commitment": "§5.16",
    "lifecycle_axes": "§22.1",
    "profile_definition": "§4.3",
    "profile_conformance_result": "§6.12",
}


@dataclass
class KernelRecordEnvelope:
    """Universal record envelope (framework v1.1 §4.1)."""

    id: str
    record_kind: str
    type_id: str
    created_at: str
    created_by: str
    provenance_id: str
    maturity_status: MaturityStatus
    epistemic_status: EpistemicStatus
    governance_status: GovernanceStatus
    scope_id: str = ""
    version: str = "1"
    visibility_policy: str = "private"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SourceFragment:
    """Preserved input before interpretation (§5.1)."""

    envelope: KernelRecordEnvelope
    media_type: str
    content_pointer: str
    author_or_origin: str
    captured_at: str
    integrity_hash: str
    source_kind: Literal[
        "user_input", "document", "observation", "simulation_output", "import"
    ] = "user_input"

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["envelope"] = self.envelope.to_dict()
        return payload


@dataclass
class Referent:
    """Distinguishable target of reference (§5.2)."""

    envelope: KernelRecordEnvelope
    canonical_label: str
    aliases: List[str] = field(default_factory=list)
    identity_policy_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["envelope"] = self.envelope.to_dict()
        return payload


@dataclass
class Scope:
    """Boundary and conditions under which records hold (§5.3)."""

    envelope: KernelRecordEnvelope
    modal_scope: Literal[
        "actual", "possible", "fictional", "counterfactual", "desired"
    ] = "actual"
    temporal_scope: str = ""
    spatial_scope: str = ""
    scale: str = ""
    boundary_rule: str = ""
    domain: str = ""
    task: str = ""
    context_refs: List[str] = field(default_factory=list)
    semantic_address: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["envelope"] = self.envelope.to_dict()
        return payload


@dataclass
class State:
    """Modeled condition within a scope (§5.4). Distinct from Claim (§6.1)."""

    envelope: KernelRecordEnvelope
    subject_refs: List[str]
    state_type: str
    value: Any
    value_type: str
    valid_scope_id: str
    commitment_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["envelope"] = self.envelope.to_dict()
        return payload


@dataclass
class ClaimProposition:
    predicate: str
    arguments: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Claim:
    """Truth-evaluable assertion; not globally true by default (§5.7)."""

    envelope: KernelRecordEnvelope
    proposition: ClaimProposition
    claimant: str
    branch_id: str
    scope_id: str
    polarity: Literal["affirmative", "negative"] = "affirmative"

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["envelope"] = self.envelope.to_dict()
        payload["proposition"] = self.proposition.to_dict()
        return payload


@dataclass
class RelationParticipant:
    role: str
    ref: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RelationInstance:
    """Typed relation among participants (§5.6)."""

    envelope: KernelRecordEnvelope
    type_id: str
    participants: List[RelationParticipant]
    scope_id: str
    qualifiers: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["envelope"] = self.envelope.to_dict()
        payload["participants"] = [item.to_dict() for item in self.participants]
        return payload


@dataclass
class Provenance:
    """Derivation path for a record (§5.10)."""

    envelope: KernelRecordEnvelope
    source_refs: List[str]
    derivation_steps: List[Dict[str, Any]] = field(default_factory=list)
    model_or_agent: str = ""
    prompt_or_rule_version: str = ""
    user_confirmations: List[str] = field(default_factory=list)
    prior_versions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["envelope"] = self.envelope.to_dict()
        return payload


@dataclass
class ModelBranch:
    """Explicit scoped interpretation branch (§5.11)."""

    envelope: KernelRecordEnvelope
    parent_branch_id: str
    branch_kind: Literal[
        "interpretation", "counterfactual", "agent_belief", "simulation", "main"
    ]
    assumptions: List[str] = field(default_factory=list)
    included_records: List[str] = field(default_factory=list)
    retracted_records: List[str] = field(default_factory=list)
    divergence_points: List[str] = field(default_factory=list)
    merge_status: str = "open"

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["envelope"] = self.envelope.to_dict()
        return payload


@dataclass
class BranchMembership:
    """How a record participates in a branch (§5.15)."""

    envelope: KernelRecordEnvelope
    record_id: str
    branch_id: str
    membership_kind: Literal[
        "inherited", "asserted", "derived", "retracted", "hidden"
    ]
    effective_scope_id: str
    introduced_by: str
    membership_provenance_id: str

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["envelope"] = self.envelope.to_dict()
        return payload


@dataclass
class StateCommitment:
    """Explicit Claim-to-State adoption (§5.16, §6.11)."""

    envelope: KernelRecordEnvelope
    source_claim_ids: List[str]
    resulting_state_id: str
    branch_id: str
    scope_id: str
    commitment_kind: Literal[
        "stipulated", "user_confirmed", "evidence_supported", "model_assumed"
    ]
    responsible_actor: str
    commitment_provenance_id: str
    reversible: bool = True

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["envelope"] = self.envelope.to_dict()
        return payload


@dataclass
class ProfileDefinition:
    """Governed profile package; must not redefine kernel semantics (§4.3)."""

    envelope: KernelRecordEnvelope
    profile_id: str
    profile_version: str
    purpose: str
    kernel_records_used: List[str]
    profile_record_types: List[str]
    profile_dependencies: List[str]
    invariants: List[str]
    steward: str
    forbidden_kernel_redefinitions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["envelope"] = self.envelope.to_dict()
        return payload


@dataclass
class ProfileConformanceResult:
    """Profile validation outcome (§6.12)."""

    envelope: KernelRecordEnvelope
    profile_definition_id: str
    profile_version: str
    evaluated_record_id: str
    passed: bool
    violations: List[str] = field(default_factory=list)
    evaluated_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["envelope"] = self.envelope.to_dict()
        return payload


PUBLIC_MODELS = (
    "KernelRecordEnvelope",
    "SourceFragment",
    "Referent",
    "Scope",
    "State",
    "Claim",
    "ClaimProposition",
    "RelationInstance",
    "RelationParticipant",
    "Provenance",
    "ModelBranch",
    "BranchMembership",
    "StateCommitment",
    "ProfileDefinition",
    "ProfileConformanceResult",
)
__all__ = [
    "MODULE_ID",
    "CONTRACT_VERSION",
    "FRAMEWORK_AUTHORITY",
    "FRAMEWORK_SECTIONS",
    "KERNEL_RECORD_KINDS",
    "BRANCH_BOUND_RECORD_KINDS",
    "MaturityStatus",
    "EpistemicStatus",
    "GovernanceStatus",
    *PUBLIC_MODELS,
]
