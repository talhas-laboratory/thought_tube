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
PATTERN_PROFILE_ID = "profile:pattern"
PATTERN_PROFILE_VERSION = "1.0.0"
CYBERNETICS_PROFILE_ID = "profile:cybernetics"
CYBERNETICS_PROFILE_VERSION = "1.0.0"
CYBERNETIC_COMPILER_ID = "compiler:cybernetic-profile-v1"
EXECUTABLE_CYBERNETIC_IR_VERSION = "1.0.0"

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
    "shape_composites_preserve_lifecycle_context": "Composite shapes require boundary, scale, temporal scope, branch, and explicit coupling context",
    "patterns_require_declared_shape_cores": "Patterns must reference one or more ShapeCore records instead of merging Shapes",
    "patterns_forbid_shape_merges": "Pattern validation must preserve merge_shapes_forbidden",
    "anti_matches_record_rejection_basis": "AntiMatch records must preserve apparent similarity and explicit rejection reasons",
    "transfer_assessments_are_explicit": "Transfer assessments require declared transferability and mechanism notes",
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


@dataclass(frozen=True)
class CyberneticCompilationResult:
    """Pure compilation output; it never executes or mutates source records."""

    compilation_id: str
    status: str
    profile_id: str
    profile_version: str
    compiler_ref: str
    source_record_ids: List[str] = field(default_factory=list)
    executable_model_ir: Dict[str, Any] = field(default_factory=dict)
    unresolved_requirements: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


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
    errors: List[str] = []
    if payload.get("record_type") != kind:
        errors.append(f"shape record_type must be {kind}")
    required = {
        "shape_core": ("id", "focal_ref", "scope_id", "branch_id", "provenance_id", "relation_refs"),
        "shape_view": ("id", "shape_core_id", "semantic_address", "abstraction_contract", "relation_refs", "projection"),
        "shape_record": ("id", "shape_core_id", "shape_view_id", "input_refs", "derivation_method", "provenance_id", "reproducibility"),
        "dimensional_shape": ("id", "shape_core_id", "dimension_id", "scope_id", "branch_id", "provenance_id"),
        "composite_shape": (
            "id",
            "dimensional_shape_refs",
            "coupling_refs",
            "boundary_ref",
            "scale",
            "temporal_scope",
            "branch_id",
            "provenance_id",
        ),
    }.get(kind)
    if required is None:
        return [f"unknown shape record type: {kind}"]
    for name in required:
        if payload.get(name) in (None, "", []):
            errors.append(f"{kind} {name} is required")
    if kind == "shape_record" and payload.get("reproducibility") not in {"reproducible", "interpretative"}:
        errors.append("shape_record reproducibility is invalid")
    if kind == "shape_view":
        projection = payload.get("projection", {})
        if not isinstance(projection, dict) or any(not projection.get(k) for k in ("nodes", "edges", "groups")):
            errors.append("shape_view projection requires nodes, edges, and groups")
        signature = payload.get("comparison_signature", {})
        if not isinstance(signature, dict) or not signature.get("role_relation_summary"):
            errors.append("shape_view comparison_signature requires role_relation_summary")
    if kind == "composite_shape" and "coupling_specs" in payload:
        specs = payload.get("coupling_specs")
        if not isinstance(specs, list) or not specs:
            errors.append("composite_shape coupling_specs must be a non-empty list")
        else:
            allowed = {"compositional", "regulatory", "temporal", "informational", "unknown"}
            for spec in specs:
                if not isinstance(spec, Mapping):
                    errors.append("composite_shape coupling_specs entries must be mappings")
                    continue
                if not str(spec.get("coupling_ref", "")):
                    errors.append("composite_shape coupling_spec coupling_ref is required")
                if spec.get("coupling_kind") not in allowed:
                    errors.append("composite_shape coupling_spec coupling_kind is invalid")
    return errors


def validate_shape_lifecycle_bundle(
    cores: Sequence[Mapping[str, Any]],
    views: Sequence[Mapping[str, Any]],
    records: Sequence[Mapping[str, Any]],
    composites: Sequence[Mapping[str, Any]],
    *,
    dimensional_shapes: Sequence[Mapping[str, Any]] = (),
) -> List[str]:
    errors: List[str] = []
    core_index = {str(item.get("id", "")): item for item in cores}
    view_index = {str(item.get("id", "")): item for item in views}
    record_index = {str(item.get("id", "")): item for item in records}
    dimensional_index = {str(item.get("id", "")): item for item in dimensional_shapes}

    for core in cores:
        errors.extend(validate_shape_contract(core, "shape_core"))
    for view in views:
        errors.extend(validate_shape_contract(view, "shape_view"))
        if str(view.get("shape_core_id", "")) not in core_index:
            errors.append(f"shape_view {view.get('id')} references unknown shape_core")
    for record in records:
        errors.extend(validate_shape_contract(record, "shape_record"))
        if str(record.get("shape_core_id", "")) not in core_index:
            errors.append(f"shape_record {record.get('id')} references unknown shape_core")
        if str(record.get("shape_view_id", "")) not in view_index:
            errors.append(f"shape_record {record.get('id')} references unknown shape_view")
    for dimensional in dimensional_shapes:
        errors.extend(validate_shape_contract(dimensional, "dimensional_shape"))
        if str(dimensional.get("shape_core_id", "")) not in core_index:
            errors.append(f"dimensional_shape {dimensional.get('id')} references unknown shape_core")

    resolvable_shapes = dimensional_index if dimensional_shapes else record_index
    target_label = "dimensional_shape" if dimensional_shapes else "shape_record"
    for composite in composites:
        errors.extend(validate_shape_contract(composite, "composite_shape"))
        if not composite.get("coupling_refs"):
            errors.append(f"composite_shape {composite.get('id')} coupling_refs must be non-empty")
        for reference in composite.get("dimensional_shape_refs", []) or []:
            if str(reference) not in resolvable_shapes:
                errors.append(f"composite_shape {composite.get('id')} references unknown {target_label}: {reference}")
    return sorted(set(errors))


def validate_pattern_contract(payload: Mapping[str, Any]) -> List[str]:
    errors: List[str] = []
    if payload.get("record_type") != "pattern":
        errors.append("pattern record_type must be pattern")
    for name in ("id", "name", "abstraction_contract", "branch_id", "scope_id", "provenance_id"):
        if payload.get(name) in (None, ""):
            errors.append(f"pattern {name} is required")
    if not isinstance(payload.get("shape_core_refs"), list) or not payload.get("shape_core_refs"):
        errors.append("pattern shape_core_refs must be a non-empty list")
    if not isinstance(payload.get("required_invariants"), list):
        errors.append("pattern required_invariants must be a list")
    if payload.get("validation_status") not in {"candidate", "validated", "rejected", "abstained"}:
        errors.append("pattern validation_status is invalid")
    if payload.get("merge_shapes_forbidden", True) is False:
        errors.append("pattern merge_shapes_forbidden cannot be false")
    return errors


def validate_anti_match_contract(payload: Mapping[str, Any]) -> List[str]:
    errors: List[str] = []
    if payload.get("record_type") != "anti_match":
        errors.append("anti_match record_type must be anti_match")
    for name in ("id", "candidate_a", "candidate_b", "apparent_similarity", "evaluator_ref", "provenance_id"):
        if payload.get(name) in (None, ""):
            errors.append(f"anti_match {name} is required")
    if not isinstance(payload.get("rejection_reasons"), list) or not payload.get("rejection_reasons"):
        errors.append("anti_match rejection_reasons must be a non-empty list")
    return errors


def validate_transfer_assessment_contract(payload: Mapping[str, Any]) -> List[str]:
    errors: List[str] = []
    if payload.get("record_type") != "transfer_assessment":
        errors.append("transfer_assessment record_type must be transfer_assessment")
    for name in ("id", "pattern_id", "source_shape_ref", "target_shape_ref", "mechanism_notes", "provenance_id"):
        if payload.get(name) in (None, ""):
            errors.append(f"transfer_assessment {name} is required")
    if payload.get("transferability") not in {"transferable", "partial", "not_transferable", "abstain"}:
        errors.append("transfer_assessment transferability is invalid")
    return errors


def validate_emergent_state_contract(payload: Mapping[str, Any]) -> List[str]:
    errors: List[str] = []
    if payload.get("record_type") != "emergent_state":
        errors.append("emergent_state record_type must be emergent_state")
    for name in ("id", "scale_transition", "emergence_rule", "uncertainty", "scope_id", "branch_id", "provenance_id"):
        if payload.get(name) in (None, ""):
            errors.append(f"emergent_state {name} is required")
    if not str(payload.get("type") or payload.get("emergent_type") or ""):
        errors.append("emergent_state type or emergent_type is required")
    for name in ("grounded_in", "evidence_refs"):
        if not isinstance(payload.get(name), list) or not payload.get(name):
            errors.append(f"emergent_state {name} must be a non-empty list")
    if payload.get("reduction_status") not in {"reducible", "partially_reducible", "irreducible", "unknown"}:
        errors.append("emergent_state reduction_status is invalid")
    return errors


def validate_cybernetic_contract(payload: Mapping[str, Any], kind: str) -> List[str]:
    """Validate one descriptive cybernetic record.

    This is deliberately a contract validator, not a dynamics engine.  It
    records enough semantics to later compile or execute a model while keeping
    observation, estimation, and hypotheses visibly distinct.
    """
    required = {
        "state_variable": (
            "id", "target_ref", "value_type", "value_domain", "unit",
            "observation_basis", "sampling_interval", "epistemic_status",
            "scope_id", "temporal_scope", "branch_id", "provenance_id",
        ),
        "signal": (
            "id", "source_ref", "target_ref", "payload_type", "payload_unit",
            "mechanism", "delay", "epistemic_status", "scope_id",
            "temporal_scope", "branch_id", "provenance_id",
        ),
        "setpoint": (
            "id", "variable_ref", "target_range", "priority", "scope_id",
            "temporal_scope", "branch_id", "provenance_id",
        ),
        "regulator": (
            "id", "controller_ref", "observed_variable_refs", "action_channel_refs",
            "setpoint_refs", "policy_ref", "authority_scope", "scope_id",
            "temporal_scope", "branch_id", "provenance_id",
        ),
        "feedback_loop": (
            "id", "variable_refs", "signal_refs", "regulator_refs", "polarity",
            "mechanism", "constraint_ref", "scope_id", "temporal_scope",
            "branch_id", "provenance_id",
        ),
        "disturbance": (
            "id", "target_variable_refs", "mechanism", "magnitude_basis", "scope_id",
            "temporal_scope", "branch_id", "provenance_id",
        ),
        "viability_condition": (
            "id", "variable_ref", "threshold_or_range", "recovery_condition",
            "failure_interpretation", "scope_id", "temporal_scope", "branch_id",
            "provenance_id",
        ),
        "dynamic_model_extension": (
            "id", "shape_ref", "input_variable_refs", "output_variable_refs",
            "timing_model_ref", "uncertainty_model_ref", "execution_status",
            "provenance_id",
        ),
    }
    if kind not in required:
        return [f"unknown cybernetic record type: {kind}"]

    errors: List[str] = []
    if payload.get("record_type") != kind:
        errors.append(f"cybernetic record_type must be {kind}")
    for name in required[kind]:
        if payload.get(name) in (None, "", []):
            errors.append(f"{kind} {name} is required")

    if kind == "state_variable":
        if payload.get("epistemic_status") not in {"observed", "estimated", "hypothesized", "derived"}:
            errors.append("state_variable epistemic_status is invalid")
        has_lower = "lower_bound" in payload
        has_upper = "upper_bound" in payload
        if has_lower != has_upper:
            errors.append("state_variable lower_bound and upper_bound must be supplied together")
        if has_lower and (
            not isinstance(payload["lower_bound"], (int, float))
            or not isinstance(payload["upper_bound"], (int, float))
            or payload["lower_bound"] > payload["upper_bound"]
        ):
            errors.append("state_variable bounds must be numeric and ordered")
    elif kind == "signal":
        delay = payload.get("delay")
        valid_delay = (
            isinstance(delay, (int, float)) and delay >= 0
        ) or (isinstance(delay, str) and (delay == "0" or delay.startswith("P")))
        if not valid_delay:
            errors.append("signal delay must be a non-negative number, 0, or ISO-8601 duration")
        if payload.get("epistemic_status") not in {"observed", "estimated", "hypothesized", "derived"}:
            errors.append("signal epistemic_status is invalid")
    elif kind == "setpoint":
        if (
            not isinstance(payload.get("priority"), int)
            or isinstance(payload.get("priority"), bool)
            or payload["priority"] < 0
        ):
            errors.append("setpoint priority must be a non-negative integer")
    elif kind == "feedback_loop":
        if payload.get("polarity") not in {"positive", "negative", "mixed", "unknown"}:
            errors.append("feedback_loop polarity is invalid")
        if payload.get("oscillation_risk") not in (None, "low", "medium", "high", "unknown"):
            errors.append("feedback_loop oscillation_risk is invalid")
    elif kind == "dynamic_model_extension":
        status = payload.get("execution_status")
        if status not in {"descriptive", "specified", "compiled", "approved"}:
            errors.append("dynamic_model_extension execution_status is invalid")
        if status in {"specified", "compiled", "approved"}:
            for name in ("equation_refs", "update_rule_refs", "compiler_ref", "validation_ref"):
                if payload.get(name) in (None, "", []):
                    errors.append(f"dynamic_model_extension {name} is required for {status}")
        if status == "approved" and payload.get("approval_ref") in (None, ""):
            errors.append("dynamic_model_extension approval_ref is required for approved execution")
    return errors


def validate_cybernetic_bundle_contract(
    records: Sequence[Mapping[str, Any]],
    *,
    shape_records: Optional[Sequence[Mapping[str, Any]]] = None,
    claim_records: Optional[Sequence[Mapping[str, Any]]] = None,
) -> List[str]:
    """Validate a cybernetic description as a coherent, bounded system.

    References are checked inside the supplied bundle only.  Kernel referents,
    relations, and policy objects remain external references, so this function
    never pretends that a contract proves the model's empirical truth.
    """
    errors: List[str] = []
    records_by_id: Dict[str, Mapping[str, Any]] = {}
    for record in records:
        kind = str(record.get("record_type", ""))
        errors.extend(validate_cybernetic_contract(record, kind))
        record_id = str(record.get("id", ""))
        if record_id in records_by_id:
            errors.append(f"cybernetic bundle has duplicate record id: {record_id}")
        else:
            records_by_id[record_id] = record

    by_type: Dict[str, Dict[str, Mapping[str, Any]]] = {}
    for record_id, record in records_by_id.items():
        by_type.setdefault(str(record.get("record_type", "")), {})[record_id] = record
    variables = by_type.get("state_variable", {})
    signals = by_type.get("signal", {})
    regulators = by_type.get("regulator", {})
    setpoints = by_type.get("setpoint", {})

    def require_refs(record: Mapping[str, Any], field_name: str, known: Mapping[str, Any], label: str) -> None:
        for reference in record.get(field_name, []):
            if str(reference) not in known:
                errors.append(f"{record.get('record_type')} {record.get('id')} references unknown {label}: {reference}")

    for signal in signals.values():
        target = variables.get(str(signal.get("target_ref", "")))
        if target is None:
            errors.append(f"signal {signal.get('id')} target_ref must identify a state_variable")
        elif signal.get("payload_unit") != target.get("unit") and not signal.get("unit_transform_ref"):
            errors.append(f"signal {signal.get('id')} payload_unit conflicts with target variable unit")
        _require_same_context(errors, signal, target, "signal", "state_variable")

    for setpoint in setpoints.values():
        variable = variables.get(str(setpoint.get("variable_ref", "")))
        if variable is None:
            errors.append(f"setpoint {setpoint.get('id')} variable_ref must identify a state_variable")
        else:
            _require_same_context(errors, setpoint, variable, "setpoint", "state_variable")

    for regulator in regulators.values():
        require_refs(regulator, "observed_variable_refs", variables, "state_variable")
        require_refs(regulator, "action_channel_refs", signals, "signal")
        require_refs(regulator, "setpoint_refs", setpoints, "setpoint")
        for variable_id in regulator.get("observed_variable_refs", []):
            _require_same_context(
                errors,
                regulator,
                variables.get(str(variable_id)),
                "regulator",
                "state_variable",
            )
        for setpoint_id in regulator.get("setpoint_refs", []):
            _require_same_context(
                errors,
                regulator,
                setpoints.get(str(setpoint_id)),
                "regulator",
                "setpoint",
            )
        for signal_id in regulator.get("action_channel_refs", []):
            signal = signals.get(str(signal_id))
            if signal and signal.get("source_ref") not in {regulator.get("controller_ref"), *(regulator.get("actuator_refs") or [])}:
                errors.append(f"regulator {regulator.get('id')} does not own action signal {signal_id}")
            if signal:
                _require_same_context(errors, regulator, signal, "regulator", "signal")

    for loop in by_type.get("feedback_loop", {}).values():
        require_refs(loop, "variable_refs", variables, "state_variable")
        require_refs(loop, "signal_refs", signals, "signal")
        require_refs(loop, "regulator_refs", regulators, "regulator")
        closed = False
        for regulator_id in loop.get("regulator_refs", []):
            regulator = regulators.get(str(regulator_id))
            if regulator is None:
                continue
            observed = set(str(item) for item in regulator.get("observed_variable_refs", []))
            for signal_id in regulator.get("action_channel_refs", []):
                signal = signals.get(str(signal_id))
                if signal and str(signal_id) in loop.get("signal_refs", []) and str(signal.get("target_ref")) in loop.get("variable_refs", []) and observed & set(str(item) for item in loop.get("variable_refs", [])):
                    closed = True
        if not closed:
            errors.append(f"feedback_loop {loop.get('id')} does not form a closed observation-action path")
        for participant_id in [*loop.get("variable_refs", []), *loop.get("signal_refs", []), *loop.get("regulator_refs", [])]:
            participant = records_by_id.get(str(participant_id))
            if participant:
                _require_same_context(errors, loop, participant, "feedback_loop", "participant")

    for disturbance in by_type.get("disturbance", {}).values():
        require_refs(disturbance, "target_variable_refs", variables, "state_variable")
    for condition in by_type.get("viability_condition", {}).values():
        variable = variables.get(str(condition.get("variable_ref", "")))
        if variable is None:
            errors.append(f"viability_condition {condition.get('id')} variable_ref must identify a state_variable")
        else:
            _require_same_context(errors, condition, variable, "viability_condition", "state_variable")
    for extension in by_type.get("dynamic_model_extension", {}).values():
        require_refs(extension, "input_variable_refs", variables, "state_variable")
        require_refs(extension, "output_variable_refs", variables, "state_variable")

    if shape_records is not None:
        shape_index = {_record_identifier(shape): shape for shape in shape_records if _record_identifier(shape)}
        for extension in by_type.get("dynamic_model_extension", {}).values():
            shape_ref = str(extension.get("shape_ref", ""))
            shape = shape_index.get(shape_ref)
            if shape is None:
                errors.append(f"dynamic_model_extension {extension.get('id')} references unknown shape_ref: {shape_ref}")
                continue
            context_record = _extension_context_record(extension, variables)
            for field_name in ("branch_id", "scope_id"):
                left_value = extension.get(field_name) or (context_record or {}).get(field_name)
                right_value = shape.get(field_name)
                if left_value and right_value and str(left_value) != str(right_value):
                    errors.append(
                        f"dynamic_model_extension {extension.get('id')} {field_name} conflicts with shape {shape_ref}"
                    )

    if claim_records is not None:
        claim_index = {_record_identifier(claim): claim for claim in claim_records if _record_identifier(claim)}
        allowed_claim_statuses = {"observed", "estimated", "hypothesized", "derived", "asserted"}
        for claim_id, claim in claim_index.items():
            status = claim.get("epistemic_status") or dict(claim.get("envelope", {}) or {}).get("epistemic_status")
            if status is not None and status not in allowed_claim_statuses:
                errors.append(f"claim {claim_id} epistemic_status is invalid")
        for variable in variables.values():
            claim_ref = variable.get("claim_ref")
            if claim_ref and str(claim_ref) not in claim_index:
                errors.append(f"state_variable {variable.get('id')} references unknown claim_ref: {claim_ref}")

    setpoint_index: Dict[Tuple[str, str, str, str, int], str] = {}
    for setpoint in setpoints.values():
        priority = setpoint.get("priority")
        if not isinstance(priority, int) or isinstance(priority, bool) or priority < 0:
            continue
        key = (str(setpoint.get("variable_ref")), str(setpoint.get("scope_id")), str(setpoint.get("temporal_scope")), str(setpoint.get("branch_id")), priority)
        target_range = str(setpoint.get("target_range"))
        prior = setpoint_index.get(key)
        if prior is not None and prior != target_range:
            errors.append(f"setpoints conflict for variable {key[0]} at priority {key[-1]}")
        setpoint_index[key] = target_range
    return sorted(set(errors))


def compile_cybernetic_bundle_to_ir(
    records: Sequence[Mapping[str, Any]],
    *,
    compilation_id: str,
    source_branch: str = "",
    source_scope: str = "",
    intended_runtime: str = "rule_engine",
    question: str = "",
    provenance_id: str = "",
) -> CyberneticCompilationResult:
    """Compile one selected cybernetics bundle into an inspectable executable IR.

    The compiler only uses the records passed in by the caller.  It does not
    search the wider record universe, approve execution, or update runtime state.
    """
    copied_records = [dict(record) for record in records]
    source_record_ids = sorted(str(record.get("id", "")) for record in copied_records if record.get("id"))
    validation_errors = validate_cybernetic_bundle_contract(copied_records)
    if not copied_records:
        validation_errors.append("no cybernetic records selected for compilation")
    if validation_errors:
        return _cybernetic_compilation_abstention(
            compilation_id,
            source_record_ids,
            sorted(set(validation_errors)),
        )

    by_type = _index_cybernetic_records(copied_records)
    extensions = sorted(
        by_type.get("dynamic_model_extension", {}).values(),
        key=lambda item: str(item.get("id", "")),
    )
    executable_extensions = [
        extension
        for extension in extensions
        if extension.get("execution_status") in {"compiled", "approved"}
    ]
    if not executable_extensions:
        return _cybernetic_compilation_abstention(
            compilation_id,
            source_record_ids,
            ["dynamic_model_extension with compiled or approved execution_status is required"],
        )

    if intended_runtime not in {"rule_engine", "discrete_event", "system_dynamics"}:
        return _cybernetic_compilation_abstention(
            compilation_id,
            source_record_ids,
            [f"unsupported runtime adapter: {intended_runtime}"],
        )

    first_context = copied_records[0]
    branch = source_branch or str(first_context.get("branch_id", ""))
    scope = source_scope or str(first_context.get("scope_id", ""))
    provenance = provenance_id or str(executable_extensions[0].get("provenance_id", ""))
    variables = [
        _compile_cybernetic_variable(record)
        for record in sorted(by_type.get("state_variable", {}).values(), key=lambda item: str(item.get("id", "")))
    ]
    state_spaces = [
        _compile_cybernetic_state_space(record)
        for record in sorted(by_type.get("state_variable", {}).values(), key=lambda item: str(item.get("id", "")))
    ]
    mechanisms = [
        _compile_cybernetic_mechanism(record)
        for record in sorted(by_type.get("feedback_loop", {}).values(), key=lambda item: str(item.get("id", "")))
    ]
    transition_rules = _compile_cybernetic_transition_rules(by_type)
    execution_allowed = any(str(extension.get("execution_status", "")) == "approved" for extension in executable_extensions)
    executable_model_ir = {
        "ir_version": EXECUTABLE_CYBERNETIC_IR_VERSION,
        "id": compilation_id,
        "source_branch": branch,
        "source_scope": scope,
        "source_records": source_record_ids,
        "intended_runtime": intended_runtime,
        "question": question,
        "entities_and_agents": sorted(_cybernetic_entity_refs(copied_records)),
        "variables": variables,
        "state_spaces": state_spaces,
        "events_and_actions": [],
        "mechanisms": mechanisms,
        "transition_rules": transition_rules,
        "constraints": _compile_cybernetic_constraints(by_type),
        "resources": [],
        "observation_functions": _compile_cybernetic_observations(by_type),
        "policies": _compile_cybernetic_policies(by_type),
        "time_model": _compile_cybernetic_time_model(by_type),
        "probability_model": {"kind": "not_declared", "requires_runtime_distribution": False},
        "outputs": _compile_cybernetic_outputs(by_type),
        "assumptions": _compile_cybernetic_assumptions(executable_extensions),
        "unresolved_requirements": [],
        "validation_results": [
            {"check": "cybernetic_bundle_contract", "passed": True, "errors": []},
            {"check": "bounded_selection_only", "passed": True, "source_record_count": len(source_record_ids)},
            {"check": "runtime_side_effects", "passed": True, "side_effects_allowed": False},
        ],
        "compilation_status": "executable",
        "execution_allowed": execution_allowed,
        "side_effects_allowed": False,
        "provenance": {
            "provenance_id": provenance,
            "compiler_ref": CYBERNETIC_COMPILER_ID,
            "source_extension_refs": [str(extension.get("id", "")) for extension in executable_extensions],
        },
    }
    return CyberneticCompilationResult(
        compilation_id=compilation_id,
        status="compiled",
        profile_id=CYBERNETICS_PROFILE_ID,
        profile_version=CYBERNETICS_PROFILE_VERSION,
        compiler_ref=CYBERNETIC_COMPILER_ID,
        source_record_ids=source_record_ids,
        executable_model_ir=executable_model_ir,
    )


def _cybernetic_compilation_abstention(
    compilation_id: str,
    source_record_ids: Sequence[str],
    unresolved_requirements: Sequence[str],
) -> CyberneticCompilationResult:
    return CyberneticCompilationResult(
        compilation_id=compilation_id,
        status="abstained",
        profile_id=CYBERNETICS_PROFILE_ID,
        profile_version=CYBERNETICS_PROFILE_VERSION,
        compiler_ref=CYBERNETIC_COMPILER_ID,
        source_record_ids=list(source_record_ids),
        unresolved_requirements=list(unresolved_requirements),
        errors=list(unresolved_requirements),
    )


def _index_cybernetic_records(records: Sequence[Mapping[str, Any]]) -> Dict[str, Dict[str, Mapping[str, Any]]]:
    by_type: Dict[str, Dict[str, Mapping[str, Any]]] = {}
    for record in records:
        by_type.setdefault(str(record.get("record_type", "")), {})[str(record.get("id", ""))] = record
    return by_type


def _compile_cybernetic_variable(record: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "id": str(record.get("id", "")),
        "owner_ref": str(record.get("target_ref", "")),
        "source_state_type": str(record.get("value_domain", "")),
        "data_type": _cybernetic_data_type(str(record.get("value_type", ""))),
        "domain": _cybernetic_domain(record),
        "unit": str(record.get("unit", "")),
        "observability": str(record.get("observation_basis", "")),
        "initial_value_source": str(record.get("observation_basis", "")),
        "uncertainty": {"epistemic_status": str(record.get("epistemic_status", ""))},
    }


def _cybernetic_data_type(value_type: str) -> str:
    return {
        "number": "Real",
        "integer": "Integer",
        "boolean": "Boolean",
        "enum": "Enum",
    }.get(value_type, value_type or "Unknown")


def _cybernetic_domain(record: Mapping[str, Any]) -> Any:
    if "lower_bound" in record and "upper_bound" in record:
        return [record["lower_bound"], record["upper_bound"]]
    return str(record.get("value_domain", ""))


def _compile_cybernetic_state_space(record: Mapping[str, Any]) -> Dict[str, Any]:
    constraints: List[Dict[str, Any]] = []
    if "lower_bound" in record and "upper_bound" in record:
        constraints.append(
            {
                "kind": "bounded_range",
                "variable_ref": str(record.get("id", "")),
                "lower_bound": record["lower_bound"],
                "upper_bound": record["upper_bound"],
            }
        )
    return {
        "id": f"state_space:{record.get('id', '')}",
        "variable_ref": str(record.get("id", "")),
        "domain": _cybernetic_domain(record),
        "constraints": constraints,
    }


def _compile_cybernetic_mechanism(record: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "id": str(record.get("id", "")),
        "mechanism": str(record.get("mechanism", "")),
        "participants": sorted(
            str(item)
            for item in [
                *record.get("variable_refs", []),
                *record.get("signal_refs", []),
                *record.get("regulator_refs", []),
            ]
        ),
        "polarity": str(record.get("polarity", "")),
        "constraint_ref": str(record.get("constraint_ref", "")),
        "oscillation_risk": str(record.get("oscillation_risk", "unknown")),
    }


def _compile_cybernetic_transition_rules(by_type: Mapping[str, Mapping[str, Mapping[str, Any]]]) -> List[Dict[str, Any]]:
    signals = by_type.get("signal", {})
    regulators = by_type.get("regulator", {})
    loops = by_type.get("feedback_loop", {})
    setpoints = by_type.get("setpoint", {})
    rules: List[Dict[str, Any]] = []
    for signal_id, signal in sorted(signals.items()):
        owner_regulators = [
            regulator
            for regulator in regulators.values()
            if signal_id in set(str(item) for item in regulator.get("action_channel_refs", []))
        ]
        if not owner_regulators:
            continue
        loop_refs = sorted(
            loop_id
            for loop_id, loop in loops.items()
            if signal_id in set(str(item) for item in loop.get("signal_refs", []))
        )
        setpoint_refs = sorted(
            str(item)
            for regulator in owner_regulators
            for item in regulator.get("setpoint_refs", [])
            if str(item) in setpoints
        )
        priority_values = [
            int(setpoints[ref].get("priority", 0))
            for ref in setpoint_refs
            if isinstance(setpoints[ref].get("priority"), int)
        ]
        rules.append(
            {
                "id": f"rule:{signal_id}",
                "trigger": {"signal_ref": signal_id, "source_ref": str(signal.get("source_ref", ""))},
                "guard": {
                    "authority_scopes": sorted(str(regulator.get("authority_scope", "")) for regulator in owner_regulators),
                    "setpoint_refs": setpoint_refs,
                },
                "effects": [
                    {
                        "operation": "set",
                        "variable_ref": str(signal.get("target_ref", "")),
                        "source_signal_ref": signal_id,
                    }
                ],
                "delay": signal.get("delay"),
                "probability": "deterministic",
                "priority": min(priority_values) if priority_values else 0,
                "conflict_policy": "priority_then_stable_id",
                "source_mechanism": loop_refs[0] if loop_refs else "",
                "provenance": str(signal.get("provenance_id", "")),
            }
        )
    return rules


def _compile_cybernetic_constraints(by_type: Mapping[str, Mapping[str, Mapping[str, Any]]]) -> List[Dict[str, Any]]:
    constraints: List[Dict[str, Any]] = []
    for setpoint in sorted(by_type.get("setpoint", {}).values(), key=lambda item: str(item.get("id", ""))):
        constraints.append(
            {
                "id": str(setpoint.get("id", "")),
                "kind": "setpoint",
                "variable_ref": str(setpoint.get("variable_ref", "")),
                "target_range": str(setpoint.get("target_range", "")),
                "priority": setpoint.get("priority"),
            }
        )
    for condition in sorted(by_type.get("viability_condition", {}).values(), key=lambda item: str(item.get("id", ""))):
        constraints.append(
            {
                "id": str(condition.get("id", "")),
                "kind": "viability_condition",
                "variable_ref": str(condition.get("variable_ref", "")),
                "threshold_or_range": str(condition.get("threshold_or_range", "")),
                "recovery_condition": str(condition.get("recovery_condition", "")),
                "failure_interpretation": str(condition.get("failure_interpretation", "")),
            }
        )
    return constraints


def _compile_cybernetic_observations(by_type: Mapping[str, Mapping[str, Mapping[str, Any]]]) -> List[Dict[str, Any]]:
    return [
        {
            "id": f"observe:{record.get('id', '')}",
            "variable_ref": str(record.get("id", "")),
            "basis": str(record.get("observation_basis", "")),
            "sampling_interval": str(record.get("sampling_interval", "")),
        }
        for record in sorted(by_type.get("state_variable", {}).values(), key=lambda item: str(item.get("id", "")))
    ]


def _compile_cybernetic_policies(by_type: Mapping[str, Mapping[str, Mapping[str, Any]]]) -> List[Dict[str, Any]]:
    return [
        {
            "id": str(record.get("policy_ref", "")),
            "regulator_ref": str(record.get("id", "")),
            "authority_scope": str(record.get("authority_scope", "")),
        }
        for record in sorted(by_type.get("regulator", {}).values(), key=lambda item: str(item.get("id", "")))
    ]


def _compile_cybernetic_time_model(by_type: Mapping[str, Mapping[str, Mapping[str, Any]]]) -> Dict[str, Any]:
    intervals = sorted(
        str(record.get("sampling_interval", ""))
        for record in by_type.get("state_variable", {}).values()
        if record.get("sampling_interval")
    )
    delays = sorted(str(record.get("delay", "")) for record in by_type.get("signal", {}).values() if record.get("delay") is not None)
    return {
        "kind": "discrete",
        "resolution": intervals[0] if intervals else "unspecified",
        "ordering": "stable_id",
        "delays": delays,
    }


def _compile_cybernetic_outputs(by_type: Mapping[str, Mapping[str, Mapping[str, Any]]]) -> List[Dict[str, Any]]:
    return [
        {
            "id": f"output:{record.get('id', '')}",
            "variable_ref": str(record.get("id", "")),
            "epistemic_status": str(record.get("epistemic_status", "")),
        }
        for record in sorted(by_type.get("state_variable", {}).values(), key=lambda item: str(item.get("id", "")))
    ]


def _compile_cybernetic_assumptions(extensions: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    assumptions: List[Dict[str, Any]] = []
    for extension in extensions:
        assumptions.append(
            {
                "extension_ref": str(extension.get("id", "")),
                "timing_model_ref": str(extension.get("timing_model_ref", "")),
                "uncertainty_model_ref": str(extension.get("uncertainty_model_ref", "")),
                "equation_refs": list(extension.get("equation_refs", [])),
                "update_rule_refs": list(extension.get("update_rule_refs", [])),
                "validation_ref": str(extension.get("validation_ref", "")),
            }
        )
    return assumptions


def _cybernetic_entity_refs(records: Sequence[Mapping[str, Any]]) -> Set[str]:
    refs: Set[str] = set()
    for record in records:
        for field_name in ("target_ref", "source_ref", "controller_ref", "shape_ref"):
            value = str(record.get(field_name, ""))
            if value:
                refs.add(value)
    return refs


def _record_identifier(record: Mapping[str, Any]) -> str:
    if record.get("id") not in (None, ""):
        return str(record.get("id"))
    envelope = record.get("envelope", {})
    if isinstance(envelope, Mapping):
        return str(envelope.get("id", "") or "")
    return ""


def _extension_context_record(
    extension: Mapping[str, Any],
    variables: Mapping[str, Mapping[str, Any]],
) -> Optional[Mapping[str, Any]]:
    for field_name in ("input_variable_refs", "output_variable_refs"):
        for variable_ref in extension.get(field_name, []) or []:
            variable = variables.get(str(variable_ref))
            if variable is not None:
                return variable
    return None


def _require_same_context(errors: List[str], left: Mapping[str, Any], right: Optional[Mapping[str, Any]], left_label: str, right_label: str) -> None:
    if right is None:
        return
    for field_name in ("scope_id", "temporal_scope", "branch_id"):
        if left.get(field_name) != right.get(field_name):
            errors.append(f"{left_label} {left.get('id')} {field_name} conflicts with {right_label} {right.get('id')}")


def build_cybernetics_profile_v1(*, envelope_id: str, provenance_id: str) -> ProfileDefinition:
    return ProfileDefinition(
        envelope=KernelRecordEnvelope(id=envelope_id, record_kind="profile_definition", type_id=CYBERNETICS_PROFILE_ID, created_at=utc_now(), created_by="service:profile_registry", provenance_id=provenance_id, maturity_status="structured", epistemic_status="not_applicable", governance_status="review_required"),
        profile_id=CYBERNETICS_PROFILE_ID,
        profile_version=CYBERNETICS_PROFILE_VERSION,
        purpose="Describe bounded regulation, feedback, viability, and future execution hooks without asserting a simulator or ungrounded control authority.",
        kernel_records_used=["referent", "scope", "relation_instance", "provenance", "model_branch", "branch_membership"],
        profile_record_types=["state_variable", "signal", "setpoint", "regulator", "feedback_loop", "disturbance", "viability_condition", "dynamic_model_extension"],
        profile_dependencies=[SHAPE_PROFILE_ID],
        invariants=["feedback_requires_mechanism_and_scope", "regulation_requires_closed_references", "viability_requires_recovery_and_failure_semantics", "dynamic_values_preserve_epistemic_status", "execution_extensions_require_explicit_compilation"],
        steward="service:profile_registry",
    )


def build_pattern_profile_v1(*, envelope_id: str, provenance_id: str) -> ProfileDefinition:
    return ProfileDefinition(
        envelope=KernelRecordEnvelope(
            id=envelope_id,
            record_kind="profile_definition",
            type_id=PATTERN_PROFILE_ID,
            created_at=utc_now(),
            created_by="service:profile_registry",
            provenance_id=provenance_id,
            maturity_status="structured",
            epistemic_status="not_applicable",
            governance_status="review_required",
        ),
        profile_id=PATTERN_PROFILE_ID,
        profile_version=PATTERN_PROFILE_VERSION,
        purpose="Represent reusable abstractions over declared Shapes, explicit AntiMatches, and bounded transfer assessments without merging source Shapes.",
        kernel_records_used=["referent", "scope", "relation_instance", "provenance", "model_branch", "branch_membership"],
        profile_record_types=["pattern", "anti_match", "transfer_assessment"],
        profile_dependencies=[SHAPE_PROFILE_ID],
        invariants=[
            "patterns_require_declared_shape_cores",
            "patterns_forbid_shape_merges",
            "anti_matches_record_rejection_basis",
            "transfer_assessments_are_explicit",
        ],
        steward="service:profile_registry",
    )


def build_shape_profile_v1(*, envelope_id: str, provenance_id: str) -> ProfileDefinition:
    return ProfileDefinition(envelope=KernelRecordEnvelope(id=envelope_id,record_kind="profile_definition",type_id=SHAPE_PROFILE_ID,created_at=utc_now(),created_by="service:profile_registry",provenance_id=provenance_id,maturity_status="structured",epistemic_status="not_applicable",governance_status="review_required"),profile_id=SHAPE_PROFILE_ID,profile_version=SHAPE_PROFILE_VERSION,purpose="Represent bounded relational Shapes, their views, derived records, and composite couplings.",kernel_records_used=["referent","scope","relation_instance","provenance","model_branch","branch_membership"],profile_record_types=["shape_core","shape_view","shape_record","dimensional_shape","composite_shape"],profile_dependencies=[ROLE_ASSIGNMENT_PROFILE_ID],invariants=["shape_views_preserve_relation_refs","composite_shapes_declare_couplings","shape_composites_preserve_lifecycle_context","comparison_signatures_are_candidate_aids"],steward="service:profile_registry")


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

    def bootstrap_pattern_profile(self) -> Dict[str, Any]:
        if self.get_profile(PATTERN_PROFILE_ID): return self.get_profile(PATTERN_PROFILE_ID).to_dict()  # type: ignore[union-attr]
        if not self.get_profile(SHAPE_PROFILE_ID): self.bootstrap_shape_profile()
        fragment=self.runtime.capture_source_fragment(content_pointer="memory://foundation/pattern-profile-bootstrap",author_or_origin="service:profile_registry",integrity_hash="sha256:pattern-profile-bootstrap",source_kind="import")
        return self.register(build_pattern_profile_v1(envelope_id=make_id("profile"),provenance_id=str(fragment["envelope"]["provenance_id"])))

    def bootstrap_cybernetics_profile(self) -> Dict[str, Any]:
        if self.get_profile(CYBERNETICS_PROFILE_ID): return self.get_profile(CYBERNETICS_PROFILE_ID).to_dict()  # type: ignore[union-attr]
        if not self.get_profile(SHAPE_PROFILE_ID): self.bootstrap_shape_profile()
        fragment=self.runtime.capture_source_fragment(content_pointer="memory://foundation/cybernetics-profile-bootstrap",author_or_origin="service:profile_registry",integrity_hash="sha256:cybernetics-profile-bootstrap",source_kind="import")
        return self.register(build_cybernetics_profile_v1(envelope_id=make_id("profile"),provenance_id=str(fragment["envelope"]["provenance_id"])))

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
    "PATTERN_PROFILE_ID",
    "PATTERN_PROFILE_VERSION",
    "CYBERNETICS_PROFILE_ID",
    "CYBERNETICS_PROFILE_VERSION",
    "CYBERNETIC_COMPILER_ID",
    "EXECUTABLE_CYBERNETIC_IR_VERSION",
    "ProfileRegistryError",
    "ApplicationProfileBinding",
    "ProfileUpgradeReport",
    "QualityInstanceContract",
    "QualityRefinementContract",
    "SystemBoundaryContract",
    "CompositionAssertionContract",
    "CyberneticCompilationResult",
    "ProfileRegistry",
    "build_field_formation_profile_v1",
    "build_quality_instance_profile_v1",
    "build_composition_profile_v1",
    "build_role_assignment_profile_v1",
    "build_shape_profile_v1",
    "build_pattern_profile_v1",
    "build_cybernetics_profile_v1",
    "validate_quality_instance_contract",
    "validate_quality_refinement_contract",
    "validate_system_boundary_contract",
    "validate_composition_assertion_contract",
    "validate_composition_bundle_contract",
    "validate_role_assignment_contract",
    "validate_influence_assessment_contract",
    "validate_role_influence_bundle_contract",
    "validate_shape_contract",
    "validate_shape_lifecycle_bundle",
    "validate_pattern_contract",
    "validate_anti_match_contract",
    "validate_transfer_assessment_contract",
    "validate_emergent_state_contract",
    "validate_cybernetic_contract",
    "validate_cybernetic_bundle_contract",
    "compile_cybernetic_bundle_to_ir",
    "parse_semver",
    "compare_semver",
    "load_profile_definition",
    "load_conformance_result",
]
