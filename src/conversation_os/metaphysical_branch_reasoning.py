"""Branch inheritance, support, conflict, merge, and inference semantics (§7.2–§7.6)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set

from conversation_os.storage import make_id

MODULE_ID = "branch.metaphysical.reasoning"
BRANCH_CONTRACT_VERSION = "1.0.0"
KERNEL_CONTRACT_VERSION = "1.1.0"

BRANCH_NEUTRAL_RECORD_KINDS = frozenset(
    {
        "source_fragment",
        "referent",
        "scope",
        "provenance",
        "model_branch",
        "branch_membership",
    }
)

INHERITANCE_OUTCOMES = frozenset(
    {"inherited", "asserted", "retracted", "replaced", "hidden", "absent"}
)
SUPPORT_VALUES = frozenset({"supported_only", "opposed_only", "both", "unresolved"})
CONFLICT_KINDS = frozenset(
    {
        "logical_contradiction",
        "measurement_incompatible",
        "perspective_divergence",
        "temporal_change",
        "scope_difference",
        "semantic_ambiguity",
        "causal_competing",
    }
)
MERGE_VERDICTS = frozenset({"compatible", "partially_compatible", "incompatible"})
CONTRADICTION_POLICIES = frozenset({"preserve", "branch", "clarify", "abstain"})
ACTIVE_MEMBERSHIP_KINDS = frozenset({"asserted", "derived"})


class BranchReasoningError(Exception):
    """Base error for branch reasoning operations."""


class BranchNotFoundError(BranchReasoningError):
    pass


class BranchCircularAncestryError(BranchReasoningError):
    pass


class ClaimNotFoundError(BranchReasoningError):
    pass


class SelfConflictError(BranchReasoningError):
    pass


class ScopeNotFoundError(BranchReasoningError):
    pass


class InvalidInferenceOutputStatusError(BranchReasoningError):
    pass


@dataclass
class InheritanceResult:
    record_id: str
    child_branch_id: str
    visibility: str
    effective_membership_kind: Optional[str] = None
    resolved_in_branch_id: Optional[str] = None
    provenance_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "record_id": self.record_id,
            "child_branch_id": self.child_branch_id,
            "visibility": self.visibility,
            "effective_membership_kind": self.effective_membership_kind,
            "resolved_in_branch_id": self.resolved_in_branch_id,
            "provenance_id": self.provenance_id,
        }


@dataclass
@dataclass
class ConflictClassificationResult:
    claim_a_id: str
    claim_b_id: str
    conflict_kind: str
    is_logical_contradiction: bool
    explanation: str = ""
    residual_risk: str = ""
    provenance_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "claim_a_id": self.claim_a_id,
            "claim_b_id": self.claim_b_id,
            "conflict_kind": self.conflict_kind,
            "is_logical_contradiction": self.is_logical_contradiction,
            "explanation": self.explanation,
            "residual_risk": self.residual_risk,
            "provenance_id": self.provenance_id,
        }


@dataclass
class MergeConflictEntry:
    claim_a_id: str
    claim_b_id: str
    conflict_kind: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "claim_a_id": self.claim_a_id,
            "claim_b_id": self.claim_b_id,
            "conflict_kind": self.conflict_kind,
        }


@dataclass
class MergeAssessmentResult:
    branch_a_id: str
    branch_b_id: str
    shared_record_ids: List[str] = field(default_factory=list)
    compatible_additions: List[str] = field(default_factory=list)
    conflicts: List[MergeConflictEntry] = field(default_factory=list)
    divergent_assumptions: List[str] = field(default_factory=list)
    scope_differences: List[str] = field(default_factory=list)
    unresolved_identity_mappings: List[str] = field(default_factory=list)
    merge_verdict: str = "compatible"
    provenance_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "branch_a_id": self.branch_a_id,
            "branch_b_id": self.branch_b_id,
            "shared_record_ids": list(self.shared_record_ids),
            "compatible_additions": list(self.compatible_additions),
            "conflicts": [entry.to_dict() for entry in self.conflicts],
            "divergent_assumptions": list(self.divergent_assumptions),
            "scope_differences": list(self.scope_differences),
            "unresolved_identity_mappings": list(self.unresolved_identity_mappings),
            "merge_verdict": self.merge_verdict,
            "provenance_id": self.provenance_id,
        }


@dataclass
class CandidateClaimOutput:
    proposition: Dict[str, Any]
    branch_id: str
    scope_id: str
    epistemic_status: str
    provenance_id: str
    source_claim_ids: List[str]
    polarity: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "proposition": dict(self.proposition),
            "branch_id": self.branch_id,
            "scope_id": self.scope_id,
            "epistemic_status": self.epistemic_status,
            "provenance_id": self.provenance_id,
            "source_claim_ids": list(self.source_claim_ids),
            "polarity": self.polarity,
        }


@dataclass
class AbstentionRecord:
    reason: str
    explanation: str = ""
    unresolved_claim_ids: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "reason": self.reason,
            "explanation": self.explanation,
            "unresolved_claim_ids": list(self.unresolved_claim_ids),
        }


@dataclass
class ClarificationRequest:
    unresolved_claim_ids: List[str]
    explanation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "unresolved_claim_ids": list(self.unresolved_claim_ids),
            "explanation": self.explanation,
        }


@dataclass
class InferenceResult:
    inference_context_provenance_id: str
    output_claims: List[CandidateClaimOutput] = field(default_factory=list)
    abstention: Optional[AbstentionRecord] = None
    branched_sub_contexts: List[Dict[str, Any]] = field(default_factory=list)
    clarification_request: Optional[ClarificationRequest] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "inference_context_provenance_id": self.inference_context_provenance_id,
            "output_claims": [claim.to_dict() for claim in self.output_claims],
            "abstention": self.abstention.to_dict() if self.abstention else None,
            "branched_sub_contexts": [dict(ctx) for ctx in self.branched_sub_contexts],
            "clarification_request": (
                self.clarification_request.to_dict() if self.clarification_request else None
            ),
        }


@dataclass
class SupportAssessmentResult:
    branch_id: str
    scope_id: str
    claim_proposition: Dict[str, Any]
    support_value: str
    affirmative_claim_ids: List[str] = field(default_factory=list)
    negative_claim_ids: List[str] = field(default_factory=list)
    provenance_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "branch_id": self.branch_id,
            "scope_id": self.scope_id,
            "claim_proposition": dict(self.claim_proposition),
            "support_value": self.support_value,
            "affirmative_claim_ids": list(self.affirmative_claim_ids),
            "negative_claim_ids": list(self.negative_claim_ids),
            "provenance_id": self.provenance_id,
        }


def _membership_index(
    membership_entries: Sequence[Mapping[str, Any]],
) -> Dict[str, Dict[str, Mapping[str, Any]]]:
    index: Dict[str, Dict[str, Mapping[str, Any]]] = {}
    for entry in membership_entries:
        record_id = str(entry.get("record_id", ""))
        branch_id = str(entry.get("branch_id", ""))
        if not record_id or not branch_id:
            continue
        index.setdefault(record_id, {})[branch_id] = entry
    return index


def _ancestor_chain(
    child_branch_id: str,
    branch_ancestry: Sequence[Mapping[str, Any]],
) -> List[str]:
    by_id = {str(row.get("branch_id", "")): str(row.get("parent_branch_id", "") or "") for row in branch_ancestry}
    if child_branch_id not in by_id:
        raise BranchNotFoundError(f"child branch not in ancestry: {child_branch_id}")

    chain: List[str] = []
    seen: Set[str] = set()
    current = by_id.get(child_branch_id, "")
    while current:
        if current in seen:
            raise BranchCircularAncestryError(f"circular ancestry at {current}")
        seen.add(current)
        chain.append(current)
        current = by_id.get(current, "")
    return chain


def _branch_ids_in_tree(branch_ancestry: Sequence[Mapping[str, Any]]) -> Set[str]:
    ids: Set[str] = set()
    for row in branch_ancestry:
        branch_id = str(row.get("branch_id", ""))
        if branch_id:
            ids.add(branch_id)
    return ids


def _propositions_match(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    return (
        str(left.get("predicate", "")) == str(right.get("predicate", ""))
        and list(left.get("arguments", []) or []) == list(right.get("arguments", []) or [])
    )


def resolve_inheritance(
    *,
    child_branch_id: str,
    record_id: str,
    record_kind: str,
    branch_ancestry: Sequence[Mapping[str, Any]],
    membership_entries: Sequence[Mapping[str, Any]],
    effective_scope_id: str = "",
) -> InheritanceResult:
    """Resolve read-visibility for a record in a child branch (§7.2)."""
    if record_kind in BRANCH_NEUTRAL_RECORD_KINDS:
        return InheritanceResult(
            record_id=record_id,
            child_branch_id=child_branch_id,
            visibility="inherited",
            effective_membership_kind=None,
            resolved_in_branch_id=None,
            provenance_id=make_id("prov"),
        )

    ancestors = _ancestor_chain(child_branch_id, branch_ancestry)
    memberships = _membership_index(membership_entries).get(record_id, {})

    def _scope_ok(entry: Mapping[str, Any]) -> bool:
        if not effective_scope_id:
            return True
        return str(entry.get("effective_scope_id", "")) == effective_scope_id

    child_entry = memberships.get(child_branch_id)
    if child_entry and _scope_ok(child_entry):
        kind = str(child_entry.get("membership_kind", ""))
        if kind == "retracted":
            return InheritanceResult(
                record_id=record_id,
                child_branch_id=child_branch_id,
                visibility="retracted",
                effective_membership_kind="retracted",
                resolved_in_branch_id=child_branch_id,
                provenance_id=make_id("prov"),
            )
        if kind == "hidden":
            return InheritanceResult(
                record_id=record_id,
                child_branch_id=child_branch_id,
                visibility="hidden",
                effective_membership_kind="hidden",
                resolved_in_branch_id=child_branch_id,
                provenance_id=make_id("prov"),
            )
        if kind in ACTIVE_MEMBERSHIP_KINDS:
            parent_asserted = any(
                str(memberships.get(branch_id, {}).get("membership_kind", "")) == "asserted"
                for branch_id in ancestors
            )
            visibility = "replaced" if parent_asserted else "asserted"
            return InheritanceResult(
                record_id=record_id,
                child_branch_id=child_branch_id,
                visibility=visibility,
                effective_membership_kind=kind,
                resolved_in_branch_id=child_branch_id,
                provenance_id=make_id("prov"),
            )

    for branch_id in ancestors:
        entry = memberships.get(branch_id)
        if not entry or not _scope_ok(entry):
            continue
        kind = str(entry.get("membership_kind", ""))
        if kind in ACTIVE_MEMBERSHIP_KINDS:
            return InheritanceResult(
                record_id=record_id,
                child_branch_id=child_branch_id,
                visibility="inherited",
                effective_membership_kind=kind,
                resolved_in_branch_id=branch_id,
                provenance_id=make_id("prov"),
            )

    return InheritanceResult(
        record_id=record_id,
        child_branch_id=child_branch_id,
        visibility="absent",
        effective_membership_kind=None,
        resolved_in_branch_id=None,
        provenance_id=make_id("prov"),
    )


def assess_support(
    *,
    branch_id: str,
    scope_id: str,
    claim_proposition: Mapping[str, Any],
    evidence_claims: Sequence[Mapping[str, Any]],
    include_inherited: bool,
    branch_ancestry: Optional[Sequence[Mapping[str, Any]]] = None,
) -> SupportAssessmentResult:
    """Four-valued support assessment within branch and scope (§7.3)."""
    allowed_branches: Set[str] = {branch_id}
    if include_inherited:
        if not branch_ancestry:
            raise BranchNotFoundError("branch_ancestry required when include_inherited is true")
        allowed_branches.update(_ancestor_chain(branch_id, branch_ancestry))

    affirmative: List[str] = []
    negative: List[str] = []

    for claim in evidence_claims:
        if str(claim.get("membership_kind", "")) == "retracted":
            continue
        if str(claim.get("scope_id", "")) != scope_id:
            continue
        if str(claim.get("branch_id", "")) not in allowed_branches:
            continue
        proposition = claim.get("proposition", {})
        if not isinstance(proposition, dict) or not _propositions_match(proposition, claim_proposition):
            continue
        claim_id = str(claim.get("id", ""))
        polarity = str(claim.get("polarity", "affirmative"))
        if polarity == "negative":
            negative.append(claim_id)
        else:
            affirmative.append(claim_id)

    if affirmative and negative:
        support_value = "both"
    elif affirmative:
        support_value = "supported_only"
    elif negative:
        support_value = "opposed_only"
    else:
        support_value = "unresolved"

    return SupportAssessmentResult(
        branch_id=branch_id,
        scope_id=scope_id,
        claim_proposition=dict(claim_proposition),
        support_value=support_value,
        affirmative_claim_ids=sorted(affirmative),
        negative_claim_ids=sorted(negative),
        provenance_id=make_id("prov"),
    )


def _claim_record_id(claim: Mapping[str, Any]) -> str:
    return str(claim.get("id", ""))


def _is_claim_record(record: Mapping[str, Any]) -> bool:
    return str(record.get("record_kind", "claim")) == "claim"


def _scopes_look_temporal(scope_a: str, scope_b: str) -> bool:
    if scope_a == scope_b:
        return False
    temporal_markers = ("_20", "_19", "temporal", "year")
    combined = f"{scope_a} {scope_b}".lower()
    return any(marker in combined for marker in temporal_markers)


def _measurement_predicate(predicate: str) -> bool:
    lowered = predicate.lower()
    return any(token in lowered for token in ("temperature", "measure", "reading", "celsius", "value"))


def classify_conflict(
    *,
    claim_a: Mapping[str, Any],
    claim_b: Mapping[str, Any],
    context_notes: str = "",
) -> ConflictClassificationResult:
    """Classify apparent disagreement between two claims (§7.4)."""
    claim_a_id = _claim_record_id(claim_a)
    claim_b_id = _claim_record_id(claim_b)
    if not claim_a_id or not claim_b_id:
        raise ClaimNotFoundError("both claims must include id")
    if claim_a_id == claim_b_id:
        raise SelfConflictError(f"cannot classify conflict for the same claim: {claim_a_id}")

    proposition_a = claim_a.get("proposition", {})
    proposition_b = claim_b.get("proposition", {})
    if not isinstance(proposition_a, dict) or not isinstance(proposition_b, dict):
        raise ClaimNotFoundError("claims must include proposition dictionaries")

    scope_a = str(claim_a.get("scope_id", ""))
    scope_b = str(claim_b.get("scope_id", ""))
    polarity_a = str(claim_a.get("polarity", "affirmative"))
    polarity_b = str(claim_b.get("polarity", "affirmative"))
    predicate_a = str(proposition_a.get("predicate", ""))
    predicate_b = str(proposition_b.get("predicate", ""))
    args_a = list(proposition_a.get("arguments", []) or [])
    args_b = list(proposition_b.get("arguments", []) or [])
    same_proposition = _propositions_match(proposition_a, proposition_b)
    opposite_polarity = polarity_a != polarity_b

    if context_notes.strip():
        kind = "semantic_ambiguity"
    elif predicate_a == "explains" and predicate_b == "explains" and scope_a == scope_b:
        if polarity_a == "affirmative" and polarity_b == "affirmative" and args_a != args_b:
            kind = "causal_competing"
        else:
            kind = "semantic_ambiguity"
    elif (
        predicate_a == predicate_b
        and args_a
        and args_b
        and args_a[0] == args_b[0]
        and args_a != args_b
        and polarity_a == "affirmative"
        and polarity_b == "affirmative"
        and scope_a == scope_b
        and _measurement_predicate(predicate_a)
    ):
        kind = "measurement_incompatible"
    elif (
        scope_a != scope_b
        and predicate_a == predicate_b
        and args_a
        and args_b
        and args_a[0] == args_b[0]
        and args_a != args_b
        and polarity_a == polarity_b
        and (_scopes_look_temporal(scope_a, scope_b) or predicate_a.startswith("has_"))
    ):
        kind = "temporal_change"
    elif same_proposition and scope_a == scope_b and opposite_polarity:
        claimant_a = str(claim_a.get("claimant", "") or "")
        claimant_b = str(claim_b.get("claimant", "") or "")
        branch_a = str(claim_a.get("branch_id", ""))
        branch_b = str(claim_b.get("branch_id", ""))
        if (claimant_a and claimant_b and claimant_a != claimant_b) or (
            branch_a and branch_b and branch_a != branch_b and (claimant_a or claimant_b)
        ):
            kind = "perspective_divergence"
        else:
            kind = "logical_contradiction"
    elif scope_a != scope_b and same_proposition and opposite_polarity:
        kind = "scope_difference"
    elif same_proposition and scope_a == scope_b and opposite_polarity:
        kind = "logical_contradiction"
    else:
        kind = "semantic_ambiguity"

    is_logical = kind == "logical_contradiction"
    return ConflictClassificationResult(
        claim_a_id=claim_a_id,
        claim_b_id=claim_b_id,
        conflict_kind=kind,
        is_logical_contradiction=is_logical,
        explanation=f"classified as {kind}",
        residual_risk="classification may require human review" if not is_logical else "logical contradiction unresolved",
        provenance_id=make_id("prov"),
    )


def _record_ids(records: Sequence[Mapping[str, Any]]) -> Set[str]:
    return {str(record.get("id", "")) for record in records if str(record.get("id", ""))}


def _claim_records(records: Sequence[Mapping[str, Any]]) -> List[Mapping[str, Any]]:
    return [record for record in records if _is_claim_record(record)]


def assess_merge(
    *,
    branch_a_id: str,
    branch_b_id: str,
    records_a: Sequence[Mapping[str, Any]],
    records_b: Sequence[Mapping[str, Any]],
    branch_a_assumptions: Optional[Sequence[str]] = None,
    branch_b_assumptions: Optional[Sequence[str]] = None,
    scope_id: str = "",
) -> MergeAssessmentResult:
    """Assess branch compatibility without selecting a winner (§7.5)."""
    if not branch_a_id or not branch_b_id:
        raise BranchNotFoundError("both branch ids are required")

    ids_a = _record_ids(records_a)
    ids_b = _record_ids(records_b)
    shared_record_ids = sorted(ids_a & ids_b)

    claims_a = _claim_records(records_a)
    claims_b = _claim_records(records_b)
    if scope_id:
        claims_a = [claim for claim in claims_a if str(claim.get("scope_id", "")) == scope_id]
        claims_b = [claim for claim in claims_b if str(claim.get("scope_id", "")) == scope_id]
        if not claims_a and not claims_b and not shared_record_ids:
            raise ScopeNotFoundError(f"scope not found in either branch: {scope_id}")

    conflicts: List[MergeConflictEntry] = []
    conflict_claim_ids: Set[str] = set()
    for claim_a in claims_a:
        for claim_b in claims_b:
            if _claim_record_id(claim_a) == _claim_record_id(claim_b):
                continue
            classification = classify_conflict(claim_a=claim_a, claim_b=claim_b)
            if classification.conflict_kind == "logical_contradiction":
                conflicts.append(
                    MergeConflictEntry(
                        claim_a_id=classification.claim_a_id,
                        claim_b_id=classification.claim_b_id,
                        conflict_kind=classification.conflict_kind,
                    )
                )
                conflict_claim_ids.add(classification.claim_a_id)
                conflict_claim_ids.add(classification.claim_b_id)

    assumptions_a = list(branch_a_assumptions or [])
    assumptions_b = list(branch_b_assumptions or [])
    set_a = set(assumptions_a)
    set_b = set(assumptions_b)
    divergent_assumptions = [item for item in assumptions_a if item not in set_b]
    divergent_assumptions.extend(item for item in assumptions_b if item not in set_a)

    scopes_a = [str(claim.get("scope_id", "")) for claim in claims_a if claim.get("scope_id")]
    scopes_b = [str(claim.get("scope_id", "")) for claim in claims_b if claim.get("scope_id")]
    set_a = set(scopes_a)
    set_b = set(scopes_b)
    scope_differences: List[str] = []
    for scope in scopes_a:
        if scope not in set_b and scope not in scope_differences:
            scope_differences.append(scope)
    for scope in scopes_b:
        if scope not in set_a and scope not in scope_differences:
            scope_differences.append(scope)

    records_by_id: Dict[str, Mapping[str, Any]] = {}
    for record in list(records_a) + list(records_b):
        record_id = str(record.get("id", ""))
        if record_id:
            records_by_id[record_id] = record

    compatible_additions: List[str] = []
    for record_id in sorted(ids_a ^ ids_b):
        if record_id in conflict_claim_ids:
            continue
        record = records_by_id.get(record_id, {})
        if _is_claim_record(record) and scope_differences and not shared_record_ids:
            continue
        compatible_additions.append(record_id)

    if conflicts:
        merge_verdict = "incompatible"
    elif divergent_assumptions or scope_differences:
        merge_verdict = "partially_compatible"
    else:
        merge_verdict = "compatible"

    return MergeAssessmentResult(
        branch_a_id=branch_a_id,
        branch_b_id=branch_b_id,
        shared_record_ids=shared_record_ids,
        compatible_additions=compatible_additions,
        conflicts=conflicts,
        divergent_assumptions=divergent_assumptions,
        scope_differences=scope_differences,
        unresolved_identity_mappings=[],
        merge_verdict=merge_verdict,
        provenance_id=make_id("prov"),
    )


def _claim_passes_filters(
    claim: Mapping[str, Any],
    *,
    scope_id: str,
    branches: Sequence[str],
    accepted_maturity_statuses: Sequence[str],
    accepted_epistemic_statuses: Sequence[str],
    accepted_governance_statuses: Sequence[str],
) -> bool:
    if str(claim.get("scope_id", "")) != scope_id:
        return False
    if branches:
        claim_branch = str(claim.get("branch_id", branches[0]))
        if claim_branch not in branches:
            return False
    if "maturity_status" in claim:
        maturity = str(claim.get("maturity_status", ""))
        if accepted_maturity_statuses and maturity not in accepted_maturity_statuses:
            return False
    if "epistemic_status" in claim:
        epistemic = str(claim.get("epistemic_status", ""))
        if accepted_epistemic_statuses and epistemic not in accepted_epistemic_statuses:
            return False
    if "governance_status" in claim:
        governance = str(claim.get("governance_status", ""))
        if accepted_governance_statuses and governance not in accepted_governance_statuses:
            return False
    if str(claim.get("membership_kind", "")) == "retracted":
        return False
    return True


def _group_claims_by_proposition(
    claims: Sequence[Mapping[str, Any]],
) -> Dict[tuple, List[Mapping[str, Any]]]:
    grouped: Dict[tuple, List[Mapping[str, Any]]] = {}
    for claim in claims:
        proposition = claim.get("proposition", {})
        if not isinstance(proposition, dict):
            continue
        key = (
            str(proposition.get("predicate", "")),
            tuple(proposition.get("arguments", []) or []),
        )
        grouped.setdefault(key, []).append(claim)
    return grouped


def _candidate_from_claim(
    claim: Mapping[str, Any],
    *,
    branch_id: str,
    scope_id: str,
) -> CandidateClaimOutput:
    proposition = claim.get("proposition", {})
    if not isinstance(proposition, dict):
        proposition = {}
    return CandidateClaimOutput(
        proposition=dict(proposition),
        branch_id=branch_id,
        scope_id=scope_id,
        epistemic_status="candidate",
        provenance_id=make_id("prov"),
        source_claim_ids=[_claim_record_id(claim)] if _claim_record_id(claim) else [],
        polarity=str(claim.get("polarity", "affirmative")),
    )


def run_inference(
    *,
    inference_context: Mapping[str, Any],
    input_claims: Sequence[Mapping[str, Any]],
) -> InferenceResult:
    """Run candidate-only inference with explicit both-handling (§7.6)."""
    output_status = str(inference_context.get("output_status", ""))
    if output_status != "candidate":
        raise InvalidInferenceOutputStatusError(
            f"inference output_status must be candidate, got {output_status!r}"
        )

    scope_id = str(inference_context.get("scope_id", ""))
    branches = list(inference_context.get("branches", []) or [])
    accepted_maturity = list(inference_context.get("accepted_maturity_statuses", []) or [])
    accepted_epistemic = list(inference_context.get("accepted_epistemic_statuses", []) or [])
    accepted_governance = list(inference_context.get("accepted_governance_statuses", []) or [])
    contradiction_policy = str(inference_context.get("contradiction_policy", "preserve"))
    inference_kind = str(inference_context.get("inference_kind", "structural"))
    max_depth = int(inference_context.get("max_depth", 1))
    context_provenance_id = make_id("prov")

    if max_depth < 1:
        return InferenceResult(
            inference_context_provenance_id=context_provenance_id,
            abstention=AbstentionRecord(
                reason="contradiction_policy_halt",
                explanation="max_depth bound prevents traversal",
                unresolved_claim_ids=sorted(
                    {_claim_record_id(claim) for claim in input_claims if _claim_record_id(claim)}
                ),
            ),
        )

    filtered = [
        claim
        for claim in input_claims
        if _claim_passes_filters(
            claim,
            scope_id=scope_id,
            branches=branches,
            accepted_maturity_statuses=accepted_maturity,
            accepted_epistemic_statuses=accepted_epistemic,
            accepted_governance_statuses=accepted_governance,
        )
    ]

    if not filtered:
        return InferenceResult(
            inference_context_provenance_id=context_provenance_id,
            abstention=AbstentionRecord(
                reason="insufficient_evidence",
                explanation="no input claims matched the inference filters",
            ),
        )

    grouped = _group_claims_by_proposition(filtered)
    primary_group = next(iter(grouped.values()))
    affirmative = [claim for claim in primary_group if str(claim.get("polarity", "affirmative")) != "negative"]
    negative = [claim for claim in primary_group if str(claim.get("polarity", "affirmative")) == "negative"]
    both_encountered = bool(affirmative) and bool(negative)

    if both_encountered:
        unresolved_ids = sorted(
            {_claim_record_id(claim) for claim in primary_group if _claim_record_id(claim)}
        )
        branch_id = branches[0] if branches else str(primary_group[0].get("branch_id", "branch_main"))

        if contradiction_policy == "preserve":
            outputs = []
            for claim in affirmative + negative:
                outputs.append(_candidate_from_claim(claim, branch_id=branch_id, scope_id=scope_id))
            return InferenceResult(
                inference_context_provenance_id=context_provenance_id,
                output_claims=outputs,
            )
        if contradiction_policy == "branch":
            sub_contexts = []
            for claim in affirmative + negative:
                sub_contexts.append(
                    {
                        **dict(inference_context),
                        "branches": [str(claim.get("branch_id", branch_id))],
                        "contradiction_policy": "preserve",
                        "source_claim_ids": [_claim_record_id(claim)],
                    }
                )
            return InferenceResult(
                inference_context_provenance_id=context_provenance_id,
                branched_sub_contexts=sub_contexts,
            )
        if contradiction_policy == "clarify":
            return InferenceResult(
                inference_context_provenance_id=context_provenance_id,
                clarification_request=ClarificationRequest(
                    unresolved_claim_ids=unresolved_ids,
                    explanation="both support status requires clarification before inference output",
                ),
            )
        if contradiction_policy == "abstain":
            return InferenceResult(
                inference_context_provenance_id=context_provenance_id,
                abstention=AbstentionRecord(
                    reason="both_support_status",
                    explanation="contradiction policy abstain halted candidate emission",
                    unresolved_claim_ids=unresolved_ids,
                ),
            )

    branch_id = branches[0] if branches else str(filtered[0].get("branch_id", "branch_main"))
    outputs: List[CandidateClaimOutput] = []
    for claim in filtered:
        candidate = _candidate_from_claim(claim, branch_id=branch_id, scope_id=scope_id)
        if inference_kind == "causal_hypothesis":
            predicate = str(candidate.proposition.get("predicate", ""))
            if predicate == "observed":
                candidate.proposition = {
                    "predicate": "hypothesizes",
                    "arguments": list(candidate.proposition.get("arguments", []) or []),
                }
        outputs.append(candidate)

    return InferenceResult(
        inference_context_provenance_id=context_provenance_id,
        output_claims=outputs,
    )


__all__ = [
    "MODULE_ID",
    "BRANCH_CONTRACT_VERSION",
    "KERNEL_CONTRACT_VERSION",
    "BRANCH_NEUTRAL_RECORD_KINDS",
    "BranchReasoningError",
    "BranchNotFoundError",
    "BranchCircularAncestryError",
    "ClaimNotFoundError",
    "SelfConflictError",
    "ScopeNotFoundError",
    "InvalidInferenceOutputStatusError",
    "InheritanceResult",
    "SupportAssessmentResult",
    "ConflictClassificationResult",
    "MergeConflictEntry",
    "MergeAssessmentResult",
    "CandidateClaimOutput",
    "AbstentionRecord",
    "ClarificationRequest",
    "InferenceResult",
    "resolve_inheritance",
    "assess_support",
    "classify_conflict",
    "assess_merge",
    "run_inference",
]
