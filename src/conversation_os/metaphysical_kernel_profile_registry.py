"""Profile registry, application bindings, and conformance (framework v1.1 §4.3, §8A, Gate F3)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set, Tuple

from conversation_os.metaphysical_kernel import (
    KERNEL_RECORD_KINDS,
    KernelRecordEnvelope,
    ProfileConformanceResult,
    ProfileDefinition,
)
from conversation_os.metaphysical_kernel_contracts import (
    profile_conformance_result_from_dict,
    profile_definition_from_dict,
    validate_profile_conformance,
    validate_profile_definition,
)
from conversation_os.metaphysical_kernel_runtime import FoundationRuntime
from conversation_os.storage import make_id, utc_now

MODULE_ID = "kernel.metaphysical.profile_registry"
CONTRACT_VERSION = "1.1.0"
FRAMEWORK_SECTION = "§4.3"

FIELD_FORMATION_PROFILE_ID = "profile:field_formation"
FIELD_FORMATION_PROFILE_VERSION = "1.0.0"
QUALITY_INSTANCE_PROFILE_ID = "profile:quality_instance"
QUALITY_INSTANCE_PROFILE_VERSION = "1.0.0"
COMPOSITION_PROFILE_ID = "profile:composition"
COMPOSITION_PROFILE_VERSION = "1.0.0"
ROLE_ASSIGNMENT_PROFILE_ID = "profile:role_assignment"
ROLE_ASSIGNMENT_PROFILE_VERSION = "1.0.0"
SHAPE_PROFILE_ID = "profile:shape"
SHAPE_PROFILE_VERSION = "1.0.0"

PROFILE_INVARIANT_CHECKS = {
    "no_claim_without_branch_membership": "Every claim must have matching BranchMembership",
    "no_state_without_state_commitment": "Adopted state requires StateCommitment",
    "hold_preserves_source_without_forcing_differentiation": "Held material must remain source_fragment or held maturity",
    "formation_requires_coherence_basis": "Formation records must declare coherence_basis",
    "quality_instance_requires_grounding": "QualityInstance requires bearer, quality definition, scope, provenance, and a claim or committed state basis",
    "quality_refinement_preserves_lineage": "Quality refinement must preserve the source quality instance, relation, and reified referent",
    "composition_assertion_is_bounded": "Composition assertion requires a declared kind, boundary, scope, branch, provenance, and relation",
    "system_boundary_preserves_identity_rule": "System boundary requires an explicit boundary and identity rule",
    "role_assignment_is_contextual": "Role assignment requires participant, host, role, mechanism, scope, time, branch, and provenance",
    "influence_assessment_is_evidence_bound": "Influence assessment requires a declared basis, uncertainty, confidence, and provenance",
}


class ProfileRegistryError(ValueError):
    def __init__(self, code: str, message: str, details: Optional[List[str]] = None) -> None:
        self.code = code
        self.details = list(details or [])
        super().__init__(message)


@dataclass
class ApplicationProfileBinding:
    application_id: str
    profile_id: str
    profile_version: str
    required_invariants: List[str] = field(default_factory=list)
    bound_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ProfileUpgradeReport:
    profile_id: str
    from_version: str
    to_version: str
    removed_record_types: List[str] = field(default_factory=list)
    stale_record_ids: List[str] = field(default_factory=list)
    stale_projections: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class QualityInstanceContract:
    """Contract-only Shape profile record; persistence follows a later task."""

    record_id: str
    bearer_referent_id: str
    quality_definition_id: str
    scope_id: str
    branch_id: str
    provenance_id: str
    basis_kind: str
    basis_record_id: str


@dataclass(frozen=True)
class QualityRefinementContract:
    """Optional lineage record for reifying a quality as a separate referent."""

    record_id: str
    source_quality_instance_id: str
    relation_instance_id: str
    relation_type: str
    reified_referent_id: str


@dataclass(frozen=True)
class SystemBoundaryContract:
    """A bounded whole at a declared resolution; not necessarily a physical boundary."""

    record_id: str
    whole_referent_id: str
    boundary_rule: str
    identity_rule: str
    scale: str
    scope_id: str
    branch_id: str
    provenance_id: str


@dataclass(frozen=True)
class CompositionAssertionContract:
    """One scoped claim that a constituent composes a declared whole in one way."""

    record_id: str
    whole_referent_id: str
    constituent_referent_id: str
    composition_kind: str
    boundary_id: str
    scope_id: str
    branch_id: str
    provenance_id: str
    relation_instance_id: str
    source_quality_instance_id: str = ""


def validate_role_assignment_contract(payload: Mapping[str, Any]) -> List[str]:
    errors: List[str] = []
    if str(payload.get("record_type", "")) != "role_assignment":
        errors.append("role assignment record_type must be role_assignment")
    for name in ("id", "participant_ref", "host_ref", "role_type", "mechanism", "scope_id", "temporal_scope", "branch_id", "provenance_id"):
        if not str(payload.get(name, "")):
            errors.append(f"role assignment {name} is required")
    if str(payload.get("participant_ref", "")) == str(payload.get("host_ref", "")):
        errors.append("role assignment participant and host must be distinct")
    return errors


def validate_influence_assessment_contract(payload: Mapping[str, Any]) -> List[str]:
    errors: List[str] = []
    if str(payload.get("record_type", "")) != "influence_assessment":
        errors.append("influence assessment record_type must be influence_assessment")
    for name in ("id", "role_assignment_id", "target_ref", "direction", "mechanism", "assessment_basis", "uncertainty", "confidence", "scope_id", "temporal_scope", "branch_id", "provenance_id"):
        if payload.get(name) in (None, ""):
            errors.append(f"influence assessment {name} is required")
    if str(payload.get("direction", "")) not in {"enables", "constrains", "amplifies", "dampens", "stabilizes", "destabilizes", "transforms"}:
        errors.append("influence assessment direction is invalid")
    if str(payload.get("assessment_basis", "")) not in {"measured", "estimated", "model_derived", "expert_judged", "qualitative"}:
        errors.append("influence assessment assessment_basis is invalid")
    confidence = payload.get("confidence")
    if not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
        errors.append("influence assessment confidence must be between 0 and 1")
    if "magnitude" in payload:
        if not isinstance(payload["magnitude"], (int, float)):
            errors.append("influence assessment magnitude must be numeric")
        for name in ("magnitude_scale", "magnitude_unit"):
            if not str(payload.get(name, "")):
                errors.append(f"influence assessment {name} is required with magnitude")
    return errors


def validate_role_influence_bundle_contract(roles: Sequence[Mapping[str, Any]], assessments: Sequence[Mapping[str, Any]]) -> List[str]:
    errors: List[str] = []
    role_index = {str(item.get("id", "")): item for item in roles}
    for role in roles:
        errors.extend(validate_role_assignment_contract(role))
    for assessment in assessments:
        errors.extend(validate_influence_assessment_contract(assessment))
        role = role_index.get(str(assessment.get("role_assignment_id", "")))
        if role is None:
            errors.append("influence assessment references unknown role assignment")
        elif any(str(assessment.get(k, "")) != str(role.get(k, "")) for k in ("scope_id", "temporal_scope", "branch_id")):
            errors.append("influence assessment scope, time, or branch conflicts with role assignment")
    return sorted(set(errors))


def validate_shape_contract(payload: Mapping[str, Any], kind: str) -> List[str]:
    errors=[]
    if payload.get("record_type") != kind: errors.append(f"shape record_type must be {kind}")
    required={"shape_core":("id","focal_ref","scope_id","branch_id","provenance_id","relation_refs"),"shape_view":("id","shape_core_id","semantic_address","abstraction_contract","relation_refs","projection"),"shape_record":("id","shape_core_id","shape_view_id","input_refs","derivation_method","provenance_id","reproducibility"),"composite_shape":("id","dimensional_shape_refs","coupling_refs","provenance_id")}[kind]
    for name in required:
        if payload.get(name) in (None,"",[]): errors.append(f"{kind} {name} is required")
    if kind=="shape_record" and payload.get("reproducibility") not in {"reproducible","interpretative"}: errors.append("shape_record reproducibility is invalid")
    if kind=="shape_view":
        projection=payload.get("projection",{})
        if not isinstance(projection,dict) or any(not projection.get(k) for k in ("nodes","edges","groups")): errors.append("shape_view projection requires nodes, edges, and groups")
        signature=payload.get("comparison_signature",{})
        if not isinstance(signature,dict) or not signature.get("role_relation_summary"): errors.append("shape_view comparison_signature requires role_relation_summary")
    return errors


def build_shape_profile_v1(*, envelope_id: str, provenance_id: str) -> ProfileDefinition:
    return ProfileDefinition(envelope=KernelRecordEnvelope(id=envelope_id,record_kind="profile_definition",type_id=SHAPE_PROFILE_ID,created_at=utc_now(),created_by="service:profile_registry",provenance_id=provenance_id,maturity_status="structured",epistemic_status="not_applicable",governance_status="review_required"),profile_id=SHAPE_PROFILE_ID,profile_version=SHAPE_PROFILE_VERSION,purpose="Represent bounded relational Shapes, their views, derived records, and composite couplings.",kernel_records_used=["referent","scope","relation_instance","provenance","model_branch","branch_membership"],profile_record_types=["shape_core","shape_view","shape_record","dimensional_shape","composite_shape"],profile_dependencies=[ROLE_ASSIGNMENT_PROFILE_ID],invariants=["shape_views_preserve_relation_refs","composite_shapes_declare_couplings","comparison_signatures_are_candidate_aids"],steward="service:profile_registry")


def validate_quality_instance_contract(payload: Mapping[str, Any]) -> List[str]:
    """Validate the contract for a profile-level quality instance.

    This deliberately validates a portable profile record, not a new kernel
    record.  The later Shape persistence task will decide how these contracts
    are stored and queried.
    """
    errors: List[str] = []
    if str(payload.get("record_type", "")) != "quality_instance":
        errors.append("quality instance record_type must be quality_instance")
    for field_name in (
        "id",
        "bearer_referent_id",
        "quality_definition_id",
        "scope_id",
        "branch_id",
        "provenance_id",
        "basis_record_id",
    ):
        if not str(payload.get(field_name, "")):
            errors.append(f"quality instance {field_name} is required")
    if str(payload.get("basis_kind", "")) not in {"claim", "state"}:
        errors.append("quality instance basis_kind must be claim or state")
    return errors


def validate_quality_refinement_contract(payload: Mapping[str, Any]) -> List[str]:
    """Validate optional reification lineage without making it mandatory."""
    errors: List[str] = []
    if str(payload.get("record_type", "")) != "quality_refinement":
        errors.append("quality refinement record_type must be quality_refinement")
    for field_name in (
        "id",
        "source_quality_instance_id",
        "relation_instance_id",
        "relation_type",
        "reified_referent_id",
    ):
        if not str(payload.get(field_name, "")):
            errors.append(f"quality refinement {field_name} is required")
    if str(payload.get("relation_type", "")) not in {"refines_to", "reified_as"}:
        errors.append("quality refinement relation_type must be refines_to or reified_as")
    return errors


def validate_system_boundary_contract(payload: Mapping[str, Any]) -> List[str]:
    """Validate a whole's boundary and identity rule at one resolution."""
    errors: List[str] = []
    if str(payload.get("record_type", "")) != "system_boundary":
        errors.append("system boundary record_type must be system_boundary")
    for field_name in (
        "id",
        "whole_referent_id",
        "boundary_rule",
        "identity_rule",
        "scale",
        "scope_id",
        "branch_id",
        "provenance_id",
    ):
        if not str(payload.get(field_name, "")):
            errors.append(f"system boundary {field_name} is required")
    if str(payload.get("boundary_rule", "")) not in {
        "material",
        "functional",
        "organizational",
        "semantic",
        "unresolved",
    }:
        errors.append("system boundary boundary_rule is invalid")
    if str(payload.get("identity_rule", "")) not in {
        "whole_preserved",
        "contextual",
        "unresolved",
    }:
        errors.append("system boundary identity_rule is invalid")
    return errors


def validate_composition_assertion_contract(payload: Mapping[str, Any]) -> List[str]:
    """Validate a composition assertion without inferring causal or role semantics."""
    errors: List[str] = []
    if str(payload.get("record_type", "")) != "composition_assertion":
        errors.append("composition assertion record_type must be composition_assertion")
    for field_name in (
        "id",
        "whole_referent_id",
        "constituent_referent_id",
        "composition_kind",
        "boundary_id",
        "scope_id",
        "branch_id",
        "provenance_id",
        "relation_instance_id",
    ):
        if not str(payload.get(field_name, "")):
            errors.append(f"composition assertion {field_name} is required")
    if str(payload.get("composition_kind", "")) not in {
        "material_part",
        "functional_component",
        "membership",
        "social_constitution",
    }:
        errors.append("composition assertion composition_kind is invalid")
    if str(payload.get("whole_referent_id", "")) == str(payload.get("constituent_referent_id", "")):
        errors.append("composition assertion cannot make a referent its own constituent")
    return errors


def validate_composition_bundle_contract(
    boundaries: Sequence[Mapping[str, Any]],
    assertions: Sequence[Mapping[str, Any]],
) -> List[str]:
    """Validate cross-record composition consistency and containment cycles."""
    errors: List[str] = []
    boundary_index: Dict[str, Mapping[str, Any]] = {}
    for boundary in boundaries:
        errors.extend(validate_system_boundary_contract(boundary))
        boundary_id = str(boundary.get("id", ""))
        if boundary_id:
            if boundary_id in boundary_index:
                errors.append(f"duplicate system boundary id: {boundary_id}")
            boundary_index[boundary_id] = boundary

    graph: Dict[str, List[str]] = {}
    for assertion in assertions:
        errors.extend(validate_composition_assertion_contract(assertion))
        boundary = boundary_index.get(str(assertion.get("boundary_id", "")))
        if boundary is None:
            errors.append("composition assertion references unknown boundary")
            continue
        for shared_field in ("whole_referent_id", "scope_id", "branch_id", "provenance_id"):
            if str(assertion.get(shared_field, "")) != str(boundary.get(shared_field, "")):
                errors.append(f"composition assertion {shared_field} conflicts with system boundary")
        whole = str(assertion.get("whole_referent_id", ""))
        constituent = str(assertion.get("constituent_referent_id", ""))
        if whole and constituent:
            graph.setdefault(whole, []).append(constituent)

    visiting: Set[str] = set()
    visited: Set[str] = set()

    def visit(node: str) -> bool:
        if node in visiting:
            return True
        if node in visited:
            return False
        visiting.add(node)
        for child in graph.get(node, []):
            if visit(child):
                return True
        visiting.remove(node)
        visited.add(node)
        return False

    if any(visit(node) for node in graph):
        errors.append("composition bundle contains a containment cycle")
    return sorted(set(errors))


def parse_semver(version: str) -> Tuple[int, int, int]:
    parts = version.split(".")
    numbers: List[int] = []
    for index in range(3):
        if index < len(parts):
            segment = parts[index]
            digits = "".join(char for char in segment if char.isdigit())
            numbers.append(int(digits or "0"))
        else:
            numbers.append(0)
    return numbers[0], numbers[1], numbers[2]


def compare_semver(left: str, right: str) -> int:
    a = parse_semver(left)
    b = parse_semver(right)
    if a < b:
        return -1
    if a > b:
        return 1
    return 0


def build_field_formation_profile_v1(*, envelope_id: str, provenance_id: str) -> ProfileDefinition:
    """Built-in Field and Formation profile (§8A)."""
    return ProfileDefinition(
        envelope=KernelRecordEnvelope(
          id=envelope_id,
          record_kind="profile_definition",
          type_id=FIELD_FORMATION_PROFILE_ID,
          created_at=utc_now(),
          created_by="service:profile_registry",
          provenance_id=provenance_id,
          maturity_status="structured",
          epistemic_status="not_applicable",
          governance_status="review_required",
      ),
      profile_id=FIELD_FORMATION_PROFILE_ID,
      profile_version=FIELD_FORMATION_PROFILE_VERSION,
      purpose="Represent unresolved meaning and progressive stabilization into formations.",
      kernel_records_used=[
          "source_fragment",
          "referent",
          "scope",
          "claim",
          "state",
          "provenance",
          "model_branch",
          "branch_membership",
          "state_commitment",
      ],
      profile_record_types=["field", "hold", "formation"],
      profile_dependencies=[],
      invariants=[
          "hold_preserves_source_without_forcing_differentiation",
          "formation_requires_coherence_basis",
          "no_claim_without_branch_membership",
          "no_state_without_state_commitment",
      ],
      steward="service:profile_registry",
      forbidden_kernel_redefinitions=[],
  )


def build_quality_instance_profile_v1(*, envelope_id: str, provenance_id: str) -> ProfileDefinition:
    """Built-in QualityInstance contract profile for the Shape program."""
    return ProfileDefinition(
        envelope=KernelRecordEnvelope(
            id=envelope_id,
            record_kind="profile_definition",
            type_id=QUALITY_INSTANCE_PROFILE_ID,
            created_at=utc_now(),
            created_by="service:profile_registry",
            provenance_id=provenance_id,
            maturity_status="structured",
            epistemic_status="not_applicable",
            governance_status="review_required",
        ),
        profile_id=QUALITY_INSTANCE_PROFILE_ID,
        profile_version=QUALITY_INSTANCE_PROFILE_VERSION,
        purpose=(
            "Represent a quality of a specific bearer under bounded scope and provenance, "
            "with optional explicit lineage when it is reified as a referent."
        ),
        kernel_records_used=[
            "referent",
            "scope",
            "claim",
            "state",
            "relation_instance",
            "provenance",
            "model_branch",
            "branch_membership",
            "state_commitment",
        ],
        profile_record_types=["quality_instance", "quality_refinement"],
        profile_dependencies=[],
        invariants=[
            "quality_instance_requires_grounding",
            "quality_refinement_preserves_lineage",
            "no_claim_without_branch_membership",
            "no_state_without_state_commitment",
        ],
        steward="service:profile_registry",
        forbidden_kernel_redefinitions=[],
    )


def build_composition_profile_v1(*, envelope_id: str, provenance_id: str) -> ProfileDefinition:
    """Built-in composition contract profile for bounded and recursive systems."""
    return ProfileDefinition(
        envelope=KernelRecordEnvelope(
            id=envelope_id,
            record_kind="profile_definition",
            type_id=COMPOSITION_PROFILE_ID,
            created_at=utc_now(),
            created_by="service:profile_registry",
            provenance_id=provenance_id,
            maturity_status="structured",
            epistemic_status="not_applicable",
            governance_status="review_required",
        ),
        profile_id=COMPOSITION_PROFILE_ID,
        profile_version=COMPOSITION_PROFILE_VERSION,
        purpose=(
            "Represent bounded whole-constituent composition at a declared resolution "
            "without inferring causation, ownership, or role."
        ),
        kernel_records_used=[
            "referent",
            "scope",
            "relation_instance",
            "provenance",
            "model_branch",
            "branch_membership",
        ],
        profile_record_types=["system_boundary", "composition_assertion"],
        profile_dependencies=[QUALITY_INSTANCE_PROFILE_ID],
        invariants=[
            "composition_assertion_is_bounded",
            "system_boundary_preserves_identity_rule",
        ],
        steward="service:profile_registry",
        forbidden_kernel_redefinitions=[],
    )


def build_role_assignment_profile_v1(*, envelope_id: str, provenance_id: str) -> ProfileDefinition:
    return ProfileDefinition(
        envelope=KernelRecordEnvelope(id=envelope_id, record_kind="profile_definition", type_id=ROLE_ASSIGNMENT_PROFILE_ID, created_at=utc_now(), created_by="service:profile_registry", provenance_id=provenance_id, maturity_status="structured", epistemic_status="not_applicable", governance_status="review_required"),
        profile_id=ROLE_ASSIGNMENT_PROFILE_ID, profile_version=ROLE_ASSIGNMENT_PROFILE_VERSION,
        purpose="Represent contextual, time-bound participant roles and evidence-bound influence assessments without treating either as intrinsic properties.",
        kernel_records_used=["referent", "scope", "relation_instance", "provenance", "model_branch", "branch_membership"],
        profile_record_types=["role_assignment", "influence_assessment"],
        profile_dependencies=[COMPOSITION_PROFILE_ID],
        invariants=["role_assignment_is_contextual", "influence_assessment_is_evidence_bound"], steward="service:profile_registry",
    )


class ProfileRegistry:
    """Versioned profile registry with dependency validation and conformance."""

    def __init__(self, runtime: FoundationRuntime) -> None:
        self.runtime = runtime
        self._bindings: Dict[str, ApplicationProfileBinding] = {}

    def _profiles(self) -> List[ProfileDefinition]:
        rows = self.runtime.current_bundle().get("profile_definitions", [])
        return [profile_definition_from_dict(row) for row in rows if isinstance(row, dict)]

    def _profile_index(self) -> Dict[str, List[ProfileDefinition]]:
        index: Dict[str, List[ProfileDefinition]] = {}
        for profile in self._profiles():
            index.setdefault(profile.profile_id, []).append(profile)
        for versions in index.values():
            versions.sort(key=lambda item: parse_semver(item.profile_version))
        return index

    def validate_registration(self, profile: ProfileDefinition) -> List[str]:
        errors = list(validate_profile_definition(profile))
        errors.extend(self._parallel_kernel_type_errors(profile))
        if profile.profile_id in profile.profile_dependencies:
            errors.append("profile cannot depend on itself")
        for dependency in profile.profile_dependencies:
            if dependency not in self._profile_index():
                errors.append(f"unknown profile dependency: {dependency}")
        if not errors:
            errors.extend(self._dependency_cycle_errors(profile))
        return errors

    def _parallel_kernel_type_errors(self, profile: ProfileDefinition) -> List[str]:
        overlap = sorted(set(profile.profile_record_types) & set(KERNEL_RECORD_KINDS))
        if overlap:
            return [f"profile_record_types cannot duplicate kernel record kinds: {overlap}"]
        return []

    def _dependency_cycle_errors(self, candidate: ProfileDefinition) -> List[str]:
        graph: Dict[str, List[str]] = {
            item.profile_id: list(item.profile_dependencies) for item in self._profiles()
        }
        graph[candidate.profile_id] = list(candidate.profile_dependencies)
        visiting: Set[str] = set()
        visited: Set[str] = set()

        def visit(node: str) -> Optional[List[str]]:
            if node in visiting:
                return [node]
            if node in visited:
                return None
            visiting.add(node)
            for dependency in graph.get(node, []):
                cycle = visit(dependency)
                if cycle:
                    cycle.append(node)
                    return cycle
            visiting.remove(node)
            visited.add(node)
            return None

        for node in graph:
            cycle = visit(node)
            if cycle:
                cycle.reverse()
                return [f"profile dependency cycle detected: {' -> '.join(cycle)}"]
        return []

    def register(self, profile: ProfileDefinition) -> Dict[str, Any]:
        errors = self.validate_registration(profile)
        if errors:
            raise ProfileRegistryError("registration_rejected", "profile registration failed", errors)
        for existing in self._profile_index().get(profile.profile_id, []):
            if existing.profile_version == profile.profile_version:
                raise ProfileRegistryError(
                    "duplicate_version",
                    f"profile {profile.profile_id}@{profile.profile_version} already registered",
                )
        return self.runtime._append_record(profile.to_dict())

    def get_profile(self, profile_id: str, *, version: Optional[str] = None) -> Optional[ProfileDefinition]:
        versions = self._profile_index().get(profile_id, [])
        if not versions:
            return None
        if version:
            for item in versions:
                if item.profile_version == version:
                    return item
            return None
        return versions[-1]

    def bootstrap_field_formation_profile(self) -> Dict[str, Any]:
        if self.get_profile(FIELD_FORMATION_PROFILE_ID):
            existing = self.get_profile(FIELD_FORMATION_PROFILE_ID)
            return existing.to_dict() if existing else {}
        fragment = self.runtime.capture_source_fragment(
            content_pointer="memory://foundation/profile-bootstrap",
            author_or_origin="service:profile_registry",
            integrity_hash="sha256:profile-bootstrap",
            source_kind="import",
        )
        provenance_id = str(fragment["envelope"]["provenance_id"])
        profile = build_field_formation_profile_v1(
            envelope_id=make_id("profile"),
            provenance_id=provenance_id,
        )
        return self.register(profile)

    def bootstrap_quality_instance_profile(self) -> Dict[str, Any]:
        if self.get_profile(QUALITY_INSTANCE_PROFILE_ID):
            existing = self.get_profile(QUALITY_INSTANCE_PROFILE_ID)
            return existing.to_dict() if existing else {}
        fragment = self.runtime.capture_source_fragment(
            content_pointer="memory://foundation/quality-instance-profile-bootstrap",
            author_or_origin="service:profile_registry",
            integrity_hash="sha256:quality-instance-profile-bootstrap",
            source_kind="import",
        )
        profile = build_quality_instance_profile_v1(
            envelope_id=make_id("profile"),
            provenance_id=str(fragment["envelope"]["provenance_id"]),
        )
        return self.register(profile)

    def bootstrap_composition_profile(self) -> Dict[str, Any]:
        if self.get_profile(COMPOSITION_PROFILE_ID):
            existing = self.get_profile(COMPOSITION_PROFILE_ID)
            return existing.to_dict() if existing else {}
        if not self.get_profile(QUALITY_INSTANCE_PROFILE_ID):
            self.bootstrap_quality_instance_profile()
        fragment = self.runtime.capture_source_fragment(
            content_pointer="memory://foundation/composition-profile-bootstrap",
            author_or_origin="service:profile_registry",
            integrity_hash="sha256:composition-profile-bootstrap",
            source_kind="import",
        )
        profile = build_composition_profile_v1(
            envelope_id=make_id("profile"),
            provenance_id=str(fragment["envelope"]["provenance_id"]),
        )
        return self.register(profile)

    def bootstrap_role_assignment_profile(self) -> Dict[str, Any]:
        if self.get_profile(ROLE_ASSIGNMENT_PROFILE_ID):
            return self.get_profile(ROLE_ASSIGNMENT_PROFILE_ID).to_dict()  # type: ignore[union-attr]
        if not self.get_profile(COMPOSITION_PROFILE_ID):
            self.bootstrap_composition_profile()
        fragment = self.runtime.capture_source_fragment(content_pointer="memory://foundation/role-assignment-profile-bootstrap", author_or_origin="service:profile_registry", integrity_hash="sha256:role-assignment-profile-bootstrap", source_kind="import")
        return self.register(build_role_assignment_profile_v1(envelope_id=make_id("profile"), provenance_id=str(fragment["envelope"]["provenance_id"])))

    def bootstrap_shape_profile(self) -> Dict[str, Any]:
        if self.get_profile(SHAPE_PROFILE_ID): return self.get_profile(SHAPE_PROFILE_ID).to_dict()  # type: ignore[union-attr]
        if not self.get_profile(ROLE_ASSIGNMENT_PROFILE_ID): self.bootstrap_role_assignment_profile()
        fragment=self.runtime.capture_source_fragment(content_pointer="memory://foundation/shape-profile-bootstrap",author_or_origin="service:profile_registry",integrity_hash="sha256:shape-profile-bootstrap",source_kind="import")
        return self.register(build_shape_profile_v1(envelope_id=make_id("profile"),provenance_id=str(fragment["envelope"]["provenance_id"])))

    def bind_application(
        self,
        *,
        application_id: str,
        profile_id: str,
        profile_version: str,
        required_invariants: Sequence[str],
    ) -> ApplicationProfileBinding:
        profile = self.get_profile(profile_id, version=profile_version)
        if not profile:
            raise ProfileRegistryError(
                "unknown_profile",
                f"profile not registered: {profile_id}@{profile_version}",
            )
        missing = sorted(set(required_invariants) - set(profile.invariants))
        if missing:
            raise ProfileRegistryError(
                "invariant_not_in_profile",
                f"binding requires unknown invariants: {missing}",
            )
        weakened = sorted(set(profile.invariants) - set(required_invariants))
        if profile.invariants and not required_invariants:
            raise ProfileRegistryError(
                "invariants_weakened",
                "application binding cannot omit all profile invariants",
                weakened,
            )
        binding = ApplicationProfileBinding(
            application_id=application_id,
            profile_id=profile_id,
            profile_version=profile_version,
            required_invariants=list(required_invariants),
            bound_at=utc_now(),
        )
        self._bindings[application_id] = binding
        return binding

    def get_binding(self, application_id: str) -> Optional[ApplicationProfileBinding]:
        return self._bindings.get(application_id)

    def evaluate_conformance(
        self,
        *,
        profile_id: str,
        profile_version: Optional[str] = None,
        evaluated_record_id: str = "bundle",
    ) -> ProfileConformanceResult:
        profile = self.get_profile(profile_id, version=profile_version)
        if not profile:
            raise ProfileRegistryError("unknown_profile", f"profile not registered: {profile_id}")

        violations = self._evaluate_invariants(profile)
        bundle_errors = self.runtime.validate_current_bundle()
        violations.extend(bundle_errors)

        result = ProfileConformanceResult(
            envelope=KernelRecordEnvelope(
                id=make_id("pcr"),
                record_kind="profile_conformance_result",
                type_id="core:profile_conformance_result",
                created_at=utc_now(),
                created_by="service:profile_registry",
                provenance_id=profile.envelope.provenance_id,
                maturity_status="structured",
                epistemic_status="not_applicable",
                governance_status="local",
            ),
            profile_definition_id=profile.envelope.id,
            profile_version=profile.profile_version,
            evaluated_record_id=evaluated_record_id,
            passed=not violations,
            violations=violations,
            evaluated_at=utc_now(),
        )
        validation_errors = validate_profile_conformance(result)
        if validation_errors:
            raise ProfileRegistryError("invalid_conformance_result", "; ".join(validation_errors))
        self.runtime._append_record(result.to_dict())
        return result

    def _evaluate_invariants(self, profile: ProfileDefinition) -> List[str]:
        violations: List[str] = []
        bundle = self.runtime.current_bundle()
        claims = bundle.get("claims", [])
        memberships = bundle.get("branch_memberships", [])
        states = bundle.get("states", [])
        commitments = bundle.get("state_commitments", [])
        fragments = bundle.get("source_fragments", [])

        membership_index = {
            str(item.get("record_id", "")): item for item in memberships if isinstance(item, dict)
        }
        committed_state_ids = {
            str(item.get("resulting_state_id", ""))
            for item in commitments
            if isinstance(item, dict)
        }
        commitment_linked = {
            str(item.get("commitment_id", ""))
            for item in states
            if isinstance(item, dict) and item.get("commitment_id")
        }

        if "no_claim_without_branch_membership" in profile.invariants:
            for claim in claims:
                if not isinstance(claim, dict):
                    continue
                claim_id = str(claim.get("envelope", {}).get("id", ""))
                branch_id = str(claim.get("branch_id", ""))
                matched = [
                    item
                    for item in memberships
                    if isinstance(item, dict)
                    and item.get("record_id") == claim_id
                    and item.get("branch_id") == branch_id
                ]
                if not matched:
                    violations.append(
                        PROFILE_INVARIANT_CHECKS["no_claim_without_branch_membership"]
                    )

        if "no_state_without_state_commitment" in profile.invariants:
            for state in states:
                if not isinstance(state, dict):
                    continue
                state_id = str(state.get("envelope", {}).get("id", ""))
                if state_id not in committed_state_ids and str(state.get("commitment_id", "")) not in commitment_linked:
                    violations.append(PROFILE_INVARIANT_CHECKS["no_state_without_state_commitment"])

        if "hold_preserves_source_without_forcing_differentiation" in profile.invariants:
            for fragment in fragments:
                if not isinstance(fragment, dict):
                    continue
                maturity = str(fragment.get("envelope", {}).get("maturity_status", ""))
                record_kind = str(fragment.get("envelope", {}).get("record_kind", ""))
                if record_kind == "source_fragment" and maturity == "held":
                    continue
                if record_kind == "source_fragment" and maturity not in {"raw", "held"}:
                    violations.append(
                        PROFILE_INVARIANT_CHECKS["hold_preserves_source_without_forcing_differentiation"]
                    )

        return sorted(set(violations))

    def plan_upgrade(
        self,
        *,
        profile_id: str,
        from_version: str,
        to_version: str,
        active_profile_records: Mapping[str, str],
    ) -> ProfileUpgradeReport:
        old_profile = self.get_profile(profile_id, version=from_version)
        new_profile = self.get_profile(profile_id, version=to_version)
        if not old_profile or not new_profile:
            raise ProfileRegistryError("unknown_profile", "both profile versions must be registered")
        if compare_semver(from_version, to_version) >= 0:
            raise ProfileRegistryError("invalid_upgrade", "to_version must be greater than from_version")

        removed_types = sorted(
            set(old_profile.profile_record_types) - set(new_profile.profile_record_types)
        )
        stale_record_ids = sorted(
            record_id
            for record_id, record_type in active_profile_records.items()
            if record_type in removed_types
        )
        stale_projections = [f"projection:{record_type}" for record_type in removed_types]
        return ProfileUpgradeReport(
            profile_id=profile_id,
            from_version=from_version,
            to_version=to_version,
            removed_record_types=removed_types,
            stale_record_ids=stale_record_ids,
            stale_projections=stale_projections,
        )


def load_profile_definition(payload: Mapping[str, Any]) -> ProfileDefinition:
    return profile_definition_from_dict(payload)


def load_conformance_result(payload: Mapping[str, Any]) -> ProfileConformanceResult:
    return profile_conformance_result_from_dict(payload)


__all__ = [
    "MODULE_ID",
    "CONTRACT_VERSION",
    "FIELD_FORMATION_PROFILE_ID",
    "FIELD_FORMATION_PROFILE_VERSION",
    "QUALITY_INSTANCE_PROFILE_ID",
    "QUALITY_INSTANCE_PROFILE_VERSION",
    "COMPOSITION_PROFILE_ID",
    "COMPOSITION_PROFILE_VERSION",
    "ROLE_ASSIGNMENT_PROFILE_ID",
    "ROLE_ASSIGNMENT_PROFILE_VERSION",
    "SHAPE_PROFILE_ID",
    "SHAPE_PROFILE_VERSION",
    "ProfileRegistryError",
    "ApplicationProfileBinding",
    "ProfileUpgradeReport",
    "QualityInstanceContract",
    "QualityRefinementContract",
    "SystemBoundaryContract",
    "CompositionAssertionContract",
    "ProfileRegistry",
    "build_field_formation_profile_v1",
    "build_quality_instance_profile_v1",
    "build_composition_profile_v1",
    "build_role_assignment_profile_v1",
    "build_shape_profile_v1",
    "validate_quality_instance_contract",
    "validate_quality_refinement_contract",
    "validate_system_boundary_contract",
    "validate_composition_assertion_contract",
    "validate_composition_bundle_contract",
    "validate_role_assignment_contract",
    "validate_influence_assessment_contract",
    "validate_role_influence_bundle_contract",
    "validate_shape_contract",
    "parse_semver",
    "compare_semver",
    "load_profile_definition",
    "load_conformance_result",
]
