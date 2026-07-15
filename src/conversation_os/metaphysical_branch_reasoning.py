"""Branch inheritance and support semantics (framework v1.1 §7.2–§7.3)."""

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
ACTIVE_MEMBERSHIP_KINDS = frozenset({"asserted", "derived"})


class BranchReasoningError(Exception):
    """Base error for branch reasoning operations."""


class BranchNotFoundError(BranchReasoningError):
    pass


class BranchCircularAncestryError(BranchReasoningError):
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


__all__ = [
    "MODULE_ID",
    "BRANCH_CONTRACT_VERSION",
    "KERNEL_CONTRACT_VERSION",
    "BRANCH_NEUTRAL_RECORD_KINDS",
    "BranchReasoningError",
    "BranchNotFoundError",
    "BranchCircularAncestryError",
    "InheritanceResult",
    "SupportAssessmentResult",
    "resolve_inheritance",
    "assess_support",
]
