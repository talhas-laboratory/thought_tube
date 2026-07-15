"""Vocabulary registry, mapping, and extension safety (framework v1.1 §8)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence

from conversation_os.storage import make_id

MODULE_ID = "vocabulary.metaphysical.governance"
VOCAB_CONTRACT_VERSION = "1.0.0"
KERNEL_CONTRACT_VERSION = "1.1.0"
BRANCH_CONTRACT_VERSION = "1.0.0"

VOCABULARY_LEVELS = frozenset(
    {"kernel", "governed_shared", "workspace", "model_local", "raw_expression"}
)
MAPPING_KINDS = frozenset({"equivalent", "narrower", "broader", "overlaps", "analogous"})
KERNEL_PROTECTED_PARENTS = frozenset({"core:claim", "core:state_type", "core:source_fragment"})
DISJOINT_PARENT_PAIRS = frozenset({frozenset({"core:claim", "core:state_type"})})
DEFAULT_ABSTENTION_CONFIDENCE_THRESHOLD = 0.5

NAMESPACE_PREFIX_TO_LEVEL = {
    "core": ("kernel", 1, "metaphysical-kernel-ontology"),
    "shared": ("governed_shared", 2, None),
    "workspace": ("workspace", 3, None),
    "model_local": ("model_local", 4, None),
    "raw": ("raw_expression", 5, None),
}


class VocabularyGovernanceError(Exception):
    """Base error for vocabulary governance operations."""


class KernelRedefinitionForbiddenError(VocabularyGovernanceError):
    pass


class DisjointTypeViolationError(VocabularyGovernanceError):
    pass


class DestructiveEditForbiddenError(VocabularyGovernanceError):
    pass


class BranchLocalCoercionForbiddenError(VocabularyGovernanceError):
    pass


@dataclass
class VocabularyLevelClassification:
    level: int
    name: str
    promotion_authority: Optional[str] = None
    promotion_required: bool = False
    default_exposure: Optional[str] = None
    global_exposure: Optional[bool] = None
    forced_normalization: Optional[bool] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "level": self.level,
            "name": self.name,
            "promotion_authority": self.promotion_authority,
            "promotion_required": self.promotion_required,
            "default_exposure": self.default_exposure,
            "global_exposure": self.global_exposure,
            "forced_normalization": self.forced_normalization,
        }


@dataclass
class RawExpression:
    id: str
    text: str
    source_fragment_id: str = ""
    captured_at: str = ""
    provenance_id: str = ""
    alias_of: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "text": self.text,
            "source_fragment_id": self.source_fragment_id,
            "captured_at": self.captured_at,
            "provenance_id": self.provenance_id,
            "alias_of": self.alias_of,
        }


@dataclass
class VocabularyEntry:
    id: str
    namespace_level: str
    definition: str = ""
    scope_id: str = ""
    branch_context: str = ""
    steward: str = ""
    governance_status: str = "local"
    maturity_status: str = "structured"
    epistemic_status: str = "candidate"
    version: str = "1.0.0"
    provenance_id: str = ""
    display_labels: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "namespace_level": self.namespace_level,
            "definition": self.definition,
            "scope_id": self.scope_id,
            "branch_context": self.branch_context,
            "steward": self.steward,
            "governance_status": self.governance_status,
            "maturity_status": self.maturity_status,
            "epistemic_status": self.epistemic_status,
            "version": self.version,
            "provenance_id": self.provenance_id,
            "display_labels": dict(self.display_labels),
        }


@dataclass
class TermMapping:
    id: str
    source_type_or_expression: str
    target_type: Optional[str]
    mapping_kind: str
    scope_id: str
    confidence: float
    provenance_id: str = ""
    created_by: str = ""
    governance_status: str = "local"
    version: str = "1.0.0"
    rationale: str = ""
    branch_context: str = ""
    identity_confirmation: str = ""
    context_notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "source_type_or_expression": self.source_type_or_expression,
            "target_type": self.target_type,
            "mapping_kind": self.mapping_kind,
            "scope_id": self.scope_id,
            "confidence": self.confidence,
            "provenance_id": self.provenance_id,
            "created_by": self.created_by,
            "governance_status": self.governance_status,
            "version": self.version,
            "rationale": self.rationale,
            "branch_context": self.branch_context,
            "identity_confirmation": self.identity_confirmation,
            "context_notes": self.context_notes,
        }


@dataclass
class MappingAssessmentResult:
    implies_identity: bool
    allows_canonical_substitution: bool
    preserves_source_expression: bool
    identity_confirmation_required: bool = False
    implies_equivalence: bool = False
    abstention_required: bool = False
    provenance_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "implies_identity": self.implies_identity,
            "allows_canonical_substitution": self.allows_canonical_substitution,
            "preserves_source_expression": self.preserves_source_expression,
            "identity_confirmation_required": self.identity_confirmation_required,
            "implies_equivalence": self.implies_equivalence,
            "abstention_required": self.abstention_required,
            "provenance_id": self.provenance_id,
        }


@dataclass
class BranchMappingSeparationResult:
    exposed_as_global: bool
    distinct_target_types: bool
    preserves_source_expression: bool
    provenance_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "exposed_as_global": self.exposed_as_global,
            "distinct_target_types": self.distinct_target_types,
            "preserves_source_expression": self.preserves_source_expression,
            "provenance_id": self.provenance_id,
        }


@dataclass
class TypeExtensionValidationResult:
    validation_result: str
    specializes_kernel: bool = False
    error_code: str = ""
    provenance_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "validation_result": self.validation_result,
            "specializes_kernel": self.specializes_kernel,
            "error_code": self.error_code,
            "provenance_id": self.provenance_id,
        }


@dataclass
class LookupResult:
    source_expression: str
    mapping: Optional[TermMapping] = None
    raw_expression: Optional[RawExpression] = None
    canonical_view_label: Optional[str] = None
    abstention_required: bool = False
    provenance_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_expression": self.source_expression,
            "mapping": self.mapping.to_dict() if self.mapping else None,
            "raw_expression": self.raw_expression.to_dict() if self.raw_expression else None,
            "canonical_view_label": self.canonical_view_label,
            "abstention_required": self.abstention_required,
            "provenance_id": self.provenance_id,
        }


@dataclass
class PromotionRubric:
    stable_usage: bool = False
    clear_definition: bool = False
    distinct_identity: bool = False
    demonstrated_reuse: bool = False
    compatibility_with_existing_terms: bool = False
    assigned_steward: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stable_usage": self.stable_usage,
            "clear_definition": self.clear_definition,
            "distinct_identity": self.distinct_identity,
            "demonstrated_reuse": self.demonstrated_reuse,
            "compatibility_with_existing_terms": self.compatibility_with_existing_terms,
            "assigned_steward": self.assigned_steward,
        }


@dataclass
class PromotionRecord:
    id: str
    source_term: str
    source_level: str
    target_level: str
    target_term: str = ""
    rubric: PromotionRubric = field(default_factory=PromotionRubric)
    review_outcome: str = "pending"
    decline_reason: str = ""
    steward: str = ""
    branch_context: str = ""
    governance_status: str = "local"
    epistemic_status: str = "candidate"
    provenance_id: str = ""
    prior_source_level: str = ""
    affected_records: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "source_term": self.source_term,
            "source_level": self.source_level,
            "target_level": self.target_level,
            "target_term": self.target_term,
            "rubric": self.rubric.to_dict(),
            "review_outcome": self.review_outcome,
            "decline_reason": self.decline_reason,
            "steward": self.steward,
            "branch_context": self.branch_context,
            "governance_status": self.governance_status,
            "epistemic_status": self.epistemic_status,
            "provenance_id": self.provenance_id,
            "prior_source_level": self.prior_source_level,
            "affected_records": list(self.affected_records),
        }


@dataclass
class PromotionReviewResult:
    promotion_status: str
    source_term_still_addressable: bool = True
    prior_level_retained_in_provenance: bool = True
    local_term_usable: bool = True
    not_invalidated: bool = True
    exposed_as_global: bool = False
    governance_status: str = ""
    epistemic_status_unchanged: str = ""
    provenance_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "promotion_status": self.promotion_status,
            "source_term_still_addressable": self.source_term_still_addressable,
            "prior_level_retained_in_provenance": self.prior_level_retained_in_provenance,
            "local_term_usable": self.local_term_usable,
            "not_invalidated": self.not_invalidated,
            "exposed_as_global": self.exposed_as_global,
            "governance_status": self.governance_status,
            "epistemic_status_unchanged": self.epistemic_status_unchanged,
            "provenance_id": self.provenance_id,
        }


@dataclass
class PromotionPolicyStatus:
    promotion_required: bool
    local_vocabulary_usable: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "promotion_required": self.promotion_required,
            "local_vocabulary_usable": self.local_vocabulary_usable,
        }


@dataclass
class DeprecationRecord:
    id: str
    deprecated_term: str
    replacement_term: str = ""
    effective_scope: str = ""
    migration_plan: str = ""
    reversible: bool = True
    provenance_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "deprecated_term": self.deprecated_term,
            "replacement_term": self.replacement_term,
            "effective_scope": self.effective_scope,
            "migration_plan": self.migration_plan,
            "reversible": self.reversible,
            "provenance_id": self.provenance_id,
        }


@dataclass
class EvolutionMigrationReport:
    id: str
    prior_definition: str
    new_definition: str
    compatibility_class: str = "additive"
    affected_records: List[str] = field(default_factory=list)
    migration_plan: str = ""
    reversible: bool = True
    semantic_loss_warnings: List[str] = field(default_factory=list)
    stale_dependents: List[str] = field(default_factory=list)
    steward: str = ""
    review_decision: str = "pending"
    provenance_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "prior_definition": self.prior_definition,
            "new_definition": self.new_definition,
            "compatibility_class": self.compatibility_class,
            "affected_records": list(self.affected_records),
            "migration_plan": self.migration_plan,
            "reversible": self.reversible,
            "semantic_loss_warnings": list(self.semantic_loss_warnings),
            "stale_dependents": list(self.stale_dependents),
            "steward": self.steward,
            "review_decision": self.review_decision,
            "provenance_id": self.provenance_id,
        }


@dataclass
class EvolutionValidationResult:
    validation_result: str
    prior_definition_addressable: bool = True
    stale_dependents_listed: bool = False
    reversible: bool = True
    semantic_loss_warnings_nonempty: bool = False
    error_code: str = ""
    provenance_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "validation_result": self.validation_result,
            "prior_definition_addressable": self.prior_definition_addressable,
            "stale_dependents_listed": self.stale_dependents_listed,
            "reversible": self.reversible,
            "semantic_loss_warnings_nonempty": self.semantic_loss_warnings_nonempty,
            "error_code": self.error_code,
            "provenance_id": self.provenance_id,
        }


@dataclass
class EvolutionReversalResult:
    reversal_recorded: bool
    restored_definition_addressable: bool
    provenance_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "reversal_recorded": self.reversal_recorded,
            "restored_definition_addressable": self.restored_definition_addressable,
            "provenance_id": self.provenance_id,
        }


def _namespace_prefix(type_id: str) -> str:
    if ":" not in type_id:
        return ""
    return type_id.split(":", 1)[0]


def classify_vocabulary_level(term: Mapping[str, Any]) -> VocabularyLevelClassification:
    """Classify a term into one of five vocabulary levels (§8.1)."""
    namespace_level = str(term.get("namespace_level", ""))
    if namespace_level == "raw_expression" or (term.get("text") and not term.get("type_id")):
        return VocabularyLevelClassification(
            level=5,
            name="raw_expression",
            forced_normalization=False,
        )

    type_id = str(term.get("type_id", term.get("id", "")))
    prefix = _namespace_prefix(type_id)
    if namespace_level in VOCABULARY_LEVELS:
        level_name = namespace_level
    elif prefix in NAMESPACE_PREFIX_TO_LEVEL:
        level_name = NAMESPACE_PREFIX_TO_LEVEL[prefix][0]
    else:
        level_name = "workspace"

    level_num = {
        "kernel": 1,
        "governed_shared": 2,
        "workspace": 3,
        "model_local": 4,
        "raw_expression": 5,
    }[level_name]

    promotion_authority = "metaphysical-kernel-ontology" if level_num == 1 else None
    promotion_required = level_name == "governed_shared"
    default_exposure = "scope_local" if level_name == "workspace" else None
    global_exposure = False if level_name == "model_local" else None

    return VocabularyLevelClassification(
        level=level_num,
        name=level_name,
        promotion_authority=promotion_authority,
        promotion_required=promotion_required,
        default_exposure=default_exposure,
        global_exposure=global_exposure,
    )


def capture_raw_expression(
    *,
    expression_id: str,
    text: str,
    source_fragment_id: str = "",
    captured_at: str = "",
    alias_of: str = "",
) -> RawExpression:
    """Capture level-5 raw expression verbatim (§6.10, §27.15)."""
    return RawExpression(
        id=expression_id,
        text=text,
        source_fragment_id=source_fragment_id,
        captured_at=captured_at,
        alias_of=alias_of,
        provenance_id=make_id("prov"),
    )


def register_vocabulary_entry(
    *,
    entry_id: str,
    namespace_level: str,
    definition: str = "",
    scope_id: str = "",
    branch_context: str = "",
    steward: str = "",
    governance_status: str = "local",
    maturity_status: str = "structured",
    epistemic_status: str = "candidate",
    version: str = "1.0.0",
    display_labels: Optional[Mapping[str, str]] = None,
) -> VocabularyEntry:
    """Register a governed vocabulary entry."""
    if namespace_level not in VOCABULARY_LEVELS:
        raise VocabularyGovernanceError(f"unknown vocabulary level: {namespace_level}")
    return VocabularyEntry(
        id=entry_id,
        namespace_level=namespace_level,
        definition=definition,
        scope_id=scope_id,
        branch_context=branch_context,
        steward=steward,
        governance_status=governance_status,
        maturity_status=maturity_status,
        epistemic_status=epistemic_status,
        version=version,
        provenance_id=make_id("prov"),
        display_labels=dict(display_labels or {}),
    )


def _mapping_from_dict(data: Mapping[str, Any]) -> TermMapping:
    return TermMapping(
        id=str(data.get("id", make_id("map"))),
        source_type_or_expression=str(data.get("source_type_or_expression", "")),
        target_type=(str(data["target_type"]) if data.get("target_type") is not None else None),
        mapping_kind=str(data.get("mapping_kind", "analogous")),
        scope_id=str(data.get("scope_id", "")),
        confidence=float(data.get("confidence", 1.0)),
        provenance_id=str(data.get("provenance_id", make_id("prov"))),
        created_by=str(data.get("created_by", "")),
        governance_status=str(data.get("governance_status", "local")),
        version=str(data.get("version", "1.0.0")),
        rationale=str(data.get("rationale", "")),
        branch_context=str(data.get("branch_context", "")),
        identity_confirmation=str(data.get("identity_confirmation", "")),
        context_notes=str(data.get("context_notes", "")),
    )


def create_term_mapping(mapping: Mapping[str, Any]) -> TermMapping:
    """Create a non-destructive term mapping record (§8.3)."""
    kind = str(mapping.get("mapping_kind", ""))
    if kind not in MAPPING_KINDS:
        raise VocabularyGovernanceError(f"unknown mapping_kind: {kind}")
    return _mapping_from_dict(mapping)


def assess_mapping(
    mapping: Mapping[str, Any],
    *,
    abstention_threshold: float = DEFAULT_ABSTENTION_CONFIDENCE_THRESHOLD,
) -> MappingAssessmentResult:
    """Evaluate mapping consequences without rewriting source terms (§8.3)."""
    record = _mapping_from_dict(mapping)
    kind = record.mapping_kind
    has_identity_confirmation = bool(record.identity_confirmation.strip())
    target_missing = record.target_type is None
    low_confidence = record.confidence < abstention_threshold

    abstention_required = target_missing or low_confidence or bool(record.context_notes.strip() and low_confidence)
    if target_missing:
        abstention_required = True

    implies_identity = kind == "equivalent" and has_identity_confirmation
    identity_confirmation_required = kind == "equivalent" and not has_identity_confirmation
    implies_equivalence = kind == "equivalent" and has_identity_confirmation
    allows_canonical_substitution = (
        not abstention_required
        and kind in {"equivalent", "narrower", "broader"}
        and (kind != "equivalent" or has_identity_confirmation)
    )

    if kind in {"analogous", "overlaps"}:
        allows_canonical_substitution = False
        implies_equivalence = False

    return MappingAssessmentResult(
        implies_identity=implies_identity,
        allows_canonical_substitution=allows_canonical_substitution,
        preserves_source_expression=True,
        identity_confirmation_required=identity_confirmation_required,
        implies_equivalence=implies_equivalence,
        abstention_required=abstention_required,
        provenance_id=make_id("prov"),
    )


def assess_branch_mapping_separation(
    mapping_a: Mapping[str, Any],
    mapping_b: Mapping[str, Any],
) -> BranchMappingSeparationResult:
    """Verify branch-local mappings for the same phrase remain separated (§8.4)."""
    a = _mapping_from_dict(mapping_a)
    b = _mapping_from_dict(mapping_b)
    same_source = a.source_type_or_expression == b.source_type_or_expression
    distinct_targets = a.target_type != b.target_type
    different_branches = bool(a.branch_context) and bool(b.branch_context) and a.branch_context != b.branch_context
    exposed_as_global = not different_branches and same_source and distinct_targets
    if different_branches:
        exposed_as_global = False
    return BranchMappingSeparationResult(
        exposed_as_global=exposed_as_global,
        distinct_target_types=distinct_targets,
        preserves_source_expression=same_source,
        provenance_id=make_id("prov"),
    )


def validate_type_extension(extension: Mapping[str, Any]) -> TypeExtensionValidationResult:
    """Validate workspace type extensions without kernel redefinition (§8.5)."""
    if extension.get("redefines_kernel_kind"):
        return TypeExtensionValidationResult(
            validation_result="invalid",
            error_code="kernel_redefinition_forbidden",
            provenance_id=make_id("prov"),
        )

    parents = [str(parent) for parent in extension.get("parent_types", []) or []]
    parent_set = frozenset(parents)
    for disjoint in DISJOINT_PARENT_PAIRS:
        if disjoint.issubset(parent_set):
            return TypeExtensionValidationResult(
                validation_result="invalid",
                error_code="disjoint_type_violation",
                provenance_id=make_id("prov"),
            )

    if "disjoint_parents_violated" in list(extension.get("constraints", []) or []):
        return TypeExtensionValidationResult(
            validation_result="invalid",
            error_code="disjoint_type_violation",
            provenance_id=make_id("prov"),
        )

    target_kernel_kind = str(extension.get("target_kernel_kind", ""))
    if target_kernel_kind in {"source_fragment", "claim", "state"}:
        return TypeExtensionValidationResult(
            validation_result="invalid",
            error_code="kernel_redefinition_forbidden",
            provenance_id=make_id("prov"),
        )

    specializes = "core:state_type" in parents and not extension.get("redefines_kernel_kind")
    return TypeExtensionValidationResult(
        validation_result="valid",
        specializes_kernel=specializes,
        provenance_id=make_id("prov"),
    )


def lookup_with_mapping(
    *,
    expression: str,
    scope_id: str,
    branch_context: str = "",
    mappings: Sequence[Mapping[str, Any]] = (),
    raw_expressions: Sequence[Mapping[str, Any]] = (),
    abstention_threshold: float = DEFAULT_ABSTENTION_CONFIDENCE_THRESHOLD,
) -> LookupResult:
    """Return source expression and mapping metadata; canonical label is view-only (§8.3)."""
    raw_match: Optional[RawExpression] = None
    for row in raw_expressions:
        row_id = str(row.get("id", ""))
        row_text = str(row.get("text", ""))
        if expression == row_id or expression == f"raw:{row_text}" or expression.endswith(row_id):
            raw_match = capture_raw_expression(
                expression_id=row_id or make_id("raw"),
                text=row_text,
                source_fragment_id=str(row.get("source_fragment_id", "")),
                alias_of=str(row.get("alias_of", "")),
            )
            break

    selected: Optional[TermMapping] = None
    for row in mappings:
        record = _mapping_from_dict(row)
        if record.source_type_or_expression != expression:
            continue
        if record.scope_id and record.scope_id != scope_id:
            continue
        if record.branch_context and branch_context and record.branch_context != branch_context:
            continue
        selected = record
        break

    assessment = assess_mapping(selected.to_dict(), abstention_threshold=abstention_threshold) if selected else None
    abstention_required = assessment.abstention_required if assessment else False
    canonical_view = selected.target_type if selected and not abstention_required else None

    return LookupResult(
        source_expression=expression,
        mapping=selected,
        raw_expression=raw_match,
        canonical_view_label=canonical_view,
        abstention_required=abstention_required,
        provenance_id=make_id("prov"),
    )


def _rubric_from_proposal(proposal: Mapping[str, Any]) -> PromotionRubric:
    return PromotionRubric(
        stable_usage=bool(proposal.get("stable_usage", False)),
        clear_definition=bool(proposal.get("clear_definition", False)),
        distinct_identity=bool(proposal.get("distinct_identity", False)),
        demonstrated_reuse=bool(proposal.get("demonstrated_reuse", False)),
        compatibility_with_existing_terms=bool(proposal.get("compatibility", proposal.get("compatibility_with_existing_terms", False))),
        assigned_steward=bool(proposal.get("steward")),
    )


def _rubric_satisfied(rubric: PromotionRubric) -> bool:
    return all(
        (
            rubric.stable_usage,
            rubric.clear_definition,
            rubric.distinct_identity,
            rubric.demonstrated_reuse,
            rubric.compatibility_with_existing_terms,
            rubric.assigned_steward,
        )
    )


def propose_promotion(proposal: Mapping[str, Any]) -> PromotionRecord:
    """Create a pending promotion record with rubric fields (§8.2)."""
    source_level = str(proposal.get("source_level", "workspace"))
    return PromotionRecord(
        id=str(proposal.get("id", make_id("promo"))),
        source_term=str(proposal.get("source_term", "")),
        source_level=source_level,
        target_level=str(proposal.get("target_level", "governed_shared")),
        target_term=str(proposal.get("target_term", "")),
        rubric=_rubric_from_proposal(proposal),
        review_outcome="pending",
        steward=str(proposal.get("steward", "")),
        branch_context=str(proposal.get("branch_context", "")),
        governance_status=str(proposal.get("governance_status", "local")),
        epistemic_status=str(proposal.get("epistemic_status", "candidate")),
        provenance_id=make_id("prov"),
        prior_source_level=source_level,
    )


def review_promotion(proposal: Optional[Mapping[str, Any]]) -> PromotionReviewResult:
    """Review promotion proposal; declined promotion leaves local term usable (§8.2)."""
    if proposal is None:
        return PromotionReviewResult(
            promotion_status="not_applicable",
            provenance_id=make_id("prov"),
        )

    explicit_outcome = str(proposal.get("review_outcome", ""))
    decline_reason = str(proposal.get("decline_reason", ""))
    branch_context = str(proposal.get("branch_context", ""))
    source_level = str(proposal.get("source_level", ""))

    if decline_reason == "branch_local_coercion_forbidden" or (
        branch_context and source_level == "model_local" and explicit_outcome == "declined"
    ):
        return PromotionReviewResult(
            promotion_status="declined",
            local_term_usable=True,
            not_invalidated=True,
            exposed_as_global=False,
            provenance_id=make_id("prov"),
        )

    if explicit_outcome == "declined":
        return PromotionReviewResult(
            promotion_status="declined",
            local_term_usable=True,
            not_invalidated=True,
            provenance_id=make_id("prov"),
        )

    rubric = _rubric_from_proposal(proposal)
    governance_only_approval = bool(proposal.get("governance_status")) and "epistemic_status" in proposal
    approved = explicit_outcome == "approved" and (_rubric_satisfied(rubric) or governance_only_approval)

    if approved:
        governance_status = str(proposal.get("governance_status", "approved_for_scope"))
        epistemic = str(proposal.get("epistemic_status", "candidate"))
        return PromotionReviewResult(
            promotion_status="approved",
            source_term_still_addressable=True,
            prior_level_retained_in_provenance=True,
            governance_status=governance_status,
            epistemic_status_unchanged=epistemic,
            provenance_id=make_id("prov"),
        )

    return PromotionReviewResult(
        promotion_status="declined",
        local_term_usable=True,
        not_invalidated=True,
        provenance_id=make_id("prov"),
    )


def assess_promotion_policy() -> PromotionPolicyStatus:
    """Promotion is optional; local vocabulary remains usable without global approval (§8.2)."""
    return PromotionPolicyStatus(promotion_required=False, local_vocabulary_usable=True)


def record_deprecation(deprecation: Mapping[str, Any]) -> DeprecationRecord:
    """Record deprecation with explicit migration plan (§8.6)."""
    return DeprecationRecord(
        id=str(deprecation.get("id", make_id("depr"))),
        deprecated_term=str(deprecation.get("deprecated_term", "")),
        replacement_term=str(deprecation.get("replacement_term", "")),
        effective_scope=str(deprecation.get("effective_scope", "")),
        migration_plan=str(deprecation.get("migration_plan", "")),
        reversible=bool(deprecation.get("reversible", True)),
        provenance_id=make_id("prov"),
    )


def publish_evolution_report(report: Mapping[str, Any]) -> EvolutionValidationResult:
    """Publish versioned evolution report; reject destructive in-place edits (§8.6)."""
    if report.get("destructive_in_place"):
        return EvolutionValidationResult(
            validation_result="invalid",
            error_code="destructive_edit_forbidden",
            provenance_id=make_id("prov"),
        )

    prior = str(report.get("prior_definition", ""))
    new = str(report.get("new_definition", ""))
    stale = list(report.get("stale_dependents", []) or [])
    warnings = list(report.get("semantic_loss_warnings", []) or [])
    reversible = bool(report.get("reversible", True))

    return EvolutionValidationResult(
        validation_result="valid",
        prior_definition_addressable=bool(prior),
        stale_dependents_listed=bool(stale),
        reversible=reversible,
        semantic_loss_warnings_nonempty=bool(warnings),
        provenance_id=make_id("prov"),
    )


def record_evolution_reversal(reversal: Mapping[str, Any]) -> EvolutionReversalResult:
    """Record reversible rollback to a prior definition version (§8.6)."""
    restored = str(reversal.get("restored_definition", ""))
    return EvolutionReversalResult(
        reversal_recorded=bool(reversal.get("original_report_id")),
        restored_definition_addressable=bool(restored),
        provenance_id=make_id("prov"),
    )


__all__ = [
    "MODULE_ID",
    "VOCAB_CONTRACT_VERSION",
    "KERNEL_CONTRACT_VERSION",
    "BRANCH_CONTRACT_VERSION",
    "VOCABULARY_LEVELS",
    "MAPPING_KINDS",
    "VocabularyGovernanceError",
    "KernelRedefinitionForbiddenError",
    "DisjointTypeViolationError",
    "DestructiveEditForbiddenError",
    "BranchLocalCoercionForbiddenError",
    "VocabularyLevelClassification",
    "RawExpression",
    "VocabularyEntry",
    "TermMapping",
    "MappingAssessmentResult",
    "BranchMappingSeparationResult",
    "TypeExtensionValidationResult",
    "LookupResult",
    "PromotionRubric",
    "PromotionRecord",
    "PromotionReviewResult",
    "PromotionPolicyStatus",
    "DeprecationRecord",
    "EvolutionMigrationReport",
    "EvolutionValidationResult",
    "EvolutionReversalResult",
    "classify_vocabulary_level",
    "capture_raw_expression",
    "register_vocabulary_entry",
    "create_term_mapping",
    "assess_mapping",
    "assess_branch_mapping_separation",
    "validate_type_extension",
    "lookup_with_mapping",
    "propose_promotion",
    "review_promotion",
    "assess_promotion_policy",
    "record_deprecation",
    "publish_evolution_report",
    "record_evolution_reversal",
]
