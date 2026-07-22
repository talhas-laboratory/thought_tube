from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from .storage import utc_now


MODULE_ID = "kernel.disclosure.shape_projection_reader"
CONTRACT_VERSION = "1.0"
CANONICAL_SHAPE_PROFILE_ID = "profile:shape"
CANONICAL_SHAPE_PROFILE_VERSION = "1.0.0"
LEGACY_SHAPE_PROFILE_ID = "profile:shape_and_semantic_addressing"
LEGACY_ADAPTER_VERSION = "1.0"
LEGACY_RETIREMENT_DATE = "2026-08-22"
MIGRATION_DECISION_ID = "CAE-014-legacy-retained-until-canonical-profile"
ABSTENTION_CODES = (
    "absent",
    "incompatible",
    "corrupt",
    "unauthorized",
    "empty",
    "unexpected_failure",
)
PROJECTION_KINDS = (
    "candidate",
    "promoted",
    "pattern_membership",
    "anti_match",
    "unavailable",
)
READINESS_STATES = (
    "available",
    "legacy_only",
    "unavailable",
    "abstained",
)
PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "CANONICAL_SHAPE_PROFILE_ID",
    "CANONICAL_SHAPE_PROFILE_VERSION",
    "LEGACY_SHAPE_PROFILE_ID",
    "LEGACY_ADAPTER_VERSION",
    "LEGACY_RETIREMENT_DATE",
    "MIGRATION_DECISION_ID",
    "ABSTENTION_CODES",
    "PROJECTION_KINDS",
    "READINESS_STATES",
    "read_shape_projections",
    "migration_decision",
)
__all__ = list(PUBLIC_API)

# Operational failures only. Programming defects (AttributeError, TypeError,
# NameError, ImportError, etc.) must propagate to fail release gates.
_OPERATIONAL_ERRORS = (OSError, ValueError, KeyError, RuntimeError)


def migration_decision() -> Dict[str, Any]:
    return {
        "decision_id": MIGRATION_DECISION_ID,
        "status": "accepted",
        "legacy_adapter_version": LEGACY_ADAPTER_VERSION,
        "canonical_profile_id": CANONICAL_SHAPE_PROFILE_ID,
        "legacy_profile_id": LEGACY_SHAPE_PROFILE_ID,
        "retirement_date": LEGACY_RETIREMENT_DATE,
        "summary": (
            "Legacy meta_layer Shape signatures remain a provisional candidate source. "
            f"Canonical authority is {CANONICAL_SHAPE_PROFILE_ID}. The legacy id "
            f"{LEGACY_SHAPE_PROFILE_ID} is candidate-only until retirement on "
            f"{LEGACY_RETIREMENT_DATE} once adapter conformance passes and no production "
            "caller requires the old id. The aperture never promotes legacy rows."
        ),
        "retirement_trigger": (
            f"{CANONICAL_SHAPE_PROFILE_ID} registered with adapter conformance; "
            f"retire {LEGACY_SHAPE_PROFILE_ID} adapter after {LEGACY_RETIREMENT_DATE} "
            "when no production caller requires the old id"
        ),
        "promotion_allowed": False,
    }


def _status_payload(
    *,
    available: bool,
    abstention_code: Optional[str],
    abstention_reason: Optional[str],
    profile_version: Optional[str] = None,
    projections: Optional[List[Dict[str, Any]]] = None,
    errors: Optional[List[str]] = None,
) -> Dict[str, Any]:
    return {
        "profile_id": CANONICAL_SHAPE_PROFILE_ID,
        "profile_version": profile_version,
        "expected_profile_version": CANONICAL_SHAPE_PROFILE_VERSION,
        "available": available,
        "abstention_code": abstention_code,
        "abstention_reason": abstention_reason,
        "projections": list(projections or []),
        "errors": list(errors or []),
    }


def _versions_compatible(registered: str, requested: str) -> bool:
    from .metaphysical_kernel_profile_registry import parse_semver

    registered_parts = parse_semver(registered)
    requested_parts = parse_semver(requested)
    return registered_parts[0] == requested_parts[0]


def _canonical_profile_status(
    root: Path,
    *,
    authorized: bool = True,
    profile_version: Optional[str] = None,
    bootstrap: bool = False,
) -> Dict[str, Any]:
    if not authorized:
        return _status_payload(
            available=False,
            abstention_code="unauthorized",
            abstention_reason="shape projection read unauthorized for caller",
        )

    try:
        from .metaphysical_kernel_contracts import validate_profile_definition
        from .metaphysical_kernel_profile_registry import ProfileRegistry
        from .metaphysical_kernel_runtime import FoundationRuntime

        runtime = FoundationRuntime(root)
        registry = ProfileRegistry(runtime)
        if bootstrap and registry.get_profile(CANONICAL_SHAPE_PROFILE_ID) is None:
            registry.bootstrap_shape_profile()

        requested_version = str(profile_version or CANONICAL_SHAPE_PROFILE_VERSION).strip()
        profile = registry.get_profile(
            CANONICAL_SHAPE_PROFILE_ID,
            version=requested_version if profile_version else None,
        )
        if profile is None:
            if profile_version:
                any_version = registry.get_profile(CANONICAL_SHAPE_PROFILE_ID)
                if any_version is not None:
                    return _status_payload(
                        available=False,
                        abstention_code="incompatible",
                        abstention_reason=(
                            f"incompatible:{CANONICAL_SHAPE_PROFILE_ID}@{requested_version} "
                            f"unavailable; registered {any_version.profile_version}"
                        ),
                        profile_version=any_version.profile_version,
                        errors=[f"requested_version_unavailable:{requested_version}"],
                    )
            return _status_payload(
                available=False,
                abstention_code="absent",
                abstention_reason=f"{CANONICAL_SHAPE_PROFILE_ID} not registered",
            )

        if not _versions_compatible(profile.profile_version, requested_version):
            return _status_payload(
                available=False,
                abstention_code="incompatible",
                abstention_reason=(
                    f"{CANONICAL_SHAPE_PROFILE_ID}@{profile.profile_version} incompatible with "
                    f"requested {requested_version}"
                ),
                profile_version=profile.profile_version,
                errors=[f"major_version_mismatch:{profile.profile_version}:{requested_version}"],
            )

        validation_errors = validate_profile_definition(profile)
        if validation_errors:
            return _status_payload(
                available=False,
                abstention_code="corrupt",
                abstention_reason=f"{CANONICAL_SHAPE_PROFILE_ID} failed profile validation",
                profile_version=profile.profile_version,
                errors=list(validation_errors),
            )

        projections: List[Dict[str, Any]] = []
        if not projections:
            return _status_payload(
                available=True,
                abstention_code="empty",
                abstention_reason="canonical shape projections empty for query",
                profile_version=profile.profile_version,
                projections=projections,
            )
        return _status_payload(
            available=True,
            abstention_code=None,
            abstention_reason=None,
            profile_version=profile.profile_version,
            projections=projections,
        )
    except _OPERATIONAL_ERRORS as exc:
        return _status_payload(
            available=False,
            abstention_code="unexpected_failure",
            abstention_reason=f"operational failure reading {CANONICAL_SHAPE_PROFILE_ID}: {exc}",
            errors=[exc.__class__.__name__, str(exc)],
        )


def _source_metadata_by_ref(root: Path) -> Dict[str, Dict[str, Any]]:
    from .library_tracker import _row_branch_id, _row_scope_id
    from .vault_ingest import load_source_registry_raw

    lookup: Dict[str, Dict[str, Any]] = {}
    for row in load_source_registry_raw(root):
        source_ref = str(row.get("source_ref", "") or "").strip()
        if not source_ref:
            continue
        lookup[source_ref] = {
            "branch_id": _row_branch_id(row),
            "scope_id": _row_scope_id(row),
            "content_hash": str(row.get("content_hash", "") or "").strip(),
        }
    return lookup


def _abstraction_contract(signature: Dict[str, Any]) -> str:
    observer_lens = str(signature.get("observer_lens", "") or "").strip()
    candidate_shapes = list(signature.get("candidate_shapes", []) or [])
    rationale = ""
    if candidate_shapes:
        rationale = str(candidate_shapes[0].get("rationale", "") or "").strip()
    if observer_lens and rationale:
        return f"{observer_lens}: {rationale}"
    return observer_lens or rationale or "unspecified"


def _scale_from_signature(signature: Dict[str, Any]) -> str:
    attributes = signature.get("attributes")
    if isinstance(attributes, dict):
        for key in ("scale", "abstraction_scale", "system_scale"):
            value = str(attributes.get(key, "") or "").strip()
            if value:
                return value
    entity_count = len(list(signature.get("entities", []) or []))
    loop_count = len(list(signature.get("feedback_loops", []) or []))
    if entity_count or loop_count:
        return f"entities={entity_count};feedback_loops={loop_count}"
    return "unspecified"


def _legacy_candidate_projection(
    signature: Dict[str, Any],
    *,
    source_metadata: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    source_ref = str(signature.get("source_ref", "") or "").strip()
    metadata = source_metadata.get(source_ref, {})
    branch_id = str(signature.get("branch_id") or metadata.get("branch_id") or "").strip()
    scope_id = str(signature.get("scope_id") or metadata.get("scope_id") or "").strip()
    maturity_status = "candidate"
    stored_status = str(signature.get("status", "") or "").strip().lower()
    if stored_status in {"validated", "promoted", "pattern"}:
        maturity_status = "candidate"
    return {
        "projection_id": str(signature.get("signature_id", "") or "").strip(),
        "kind": "candidate",
        "maturity_status": maturity_status,
        "promotion_allowed": False,
        "pattern_membership": False,
        "source_ref": source_ref,
        "source_kind": str(signature.get("source_kind", "") or "").strip(),
        "branch_id": branch_id,
        "scope_id": scope_id,
        "system_boundary": str(signature.get("system_boundary", "") or "").strip(),
        "abstraction_contract": _abstraction_contract(signature),
        "scale": _scale_from_signature(signature),
        "evidence_spans": list(signature.get("evidence_spans", []) or []),
        "provenance": {
            "content_hash": metadata.get("content_hash") or None,
            "source_anchor_id": str(signature.get("source_anchor_id", "") or "").strip() or None,
        },
        "legacy_signature_status": stored_status or "provisional",
        "legacy_profile_id": LEGACY_SHAPE_PROFILE_ID,
        "adapter_version": LEGACY_ADAPTER_VERSION,
    }


def _legacy_anti_match_projection(row: Dict[str, Any], record: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "projection_id": f"anti-match:{row.get('memory_id', '')}:{record.get('candidate_meta_id', '')}",
        "kind": "anti_match",
        "maturity_status": "rejected_match",
        "promotion_allowed": False,
        "pattern_membership": False,
        "shape_name": str(row.get("shape_name", "") or "").strip(),
        "scope": str(row.get("scope", "") or "").strip(),
        "scope_key": str(row.get("scope_key", "") or "").strip(),
        "branch_id": str(record.get("branch_id") or row.get("branch_id") or "").strip(),
        "scope_id": str(record.get("scope_id") or row.get("scope_id") or row.get("scope_key") or "").strip(),
        "anchor_meta_id": str(record.get("anchor_meta_id", "") or "").strip(),
        "candidate_meta_id": str(record.get("candidate_meta_id", "") or "").strip(),
        "anti_match_penalty": float(record.get("anti_match_penalty", 0.0) or 0.0),
        "legacy_profile_id": LEGACY_SHAPE_PROFILE_ID,
        "adapter_version": LEGACY_ADAPTER_VERSION,
    }


def _matches_branch_scope(
    row: Dict[str, Any],
    *,
    branch_id: str,
    scope_id: str,
) -> bool:
    if branch_id and str(row.get("branch_id", "") or "").strip() not in {"", branch_id}:
        return False
    if scope_id and str(row.get("scope_id", "") or "").strip() not in {"", scope_id}:
        if str(row.get("scope_key", "") or "").strip() not in {"", scope_id}:
            return False
    return True


def _load_legacy_projections(
    root: Path,
    *,
    branch_id: str = "",
    scope_id: str = "",
    source_refs: Optional[Iterable[str]] = None,
    include_anti_match: bool = True,
) -> Dict[str, Any]:
    from .meta_layer import load_shape_memory, load_shape_signatures

    normalized_branch = str(branch_id or "").strip()
    normalized_scope = str(scope_id or "").strip()
    allowed_refs = {str(item).strip() for item in list(source_refs or []) if str(item).strip()}
    source_metadata = _source_metadata_by_ref(root)

    candidate_rows: List[Dict[str, Any]] = []
    for signature in load_shape_signatures(root):
        source_ref = str(signature.get("source_ref", "") or "").strip()
        if allowed_refs and source_ref not in allowed_refs:
            continue
        projection = _legacy_candidate_projection(signature, source_metadata=source_metadata)
        if normalized_branch or normalized_scope:
            if not _matches_branch_scope(projection, branch_id=normalized_branch, scope_id=normalized_scope):
                continue
        candidate_rows.append(projection)

    anti_match_rows: List[Dict[str, Any]] = []
    if include_anti_match:
        for row in load_shape_memory(root):
            for record in list(row.get("attributes", {}).get("anti_match_records", []) or []):
                anti_match = _legacy_anti_match_projection(row, dict(record))
                if normalized_branch or normalized_scope:
                    if not _matches_branch_scope(
                        anti_match,
                        branch_id=normalized_branch,
                        scope_id=normalized_scope,
                    ):
                        continue
                anti_match_rows.append(anti_match)

    return {
        "adapter_version": LEGACY_ADAPTER_VERSION,
        "legacy_profile_id": LEGACY_SHAPE_PROFILE_ID,
        "promotion_allowed": False,
        "candidate_projections": candidate_rows,
        "anti_match_projections": anti_match_rows,
    }


def read_shape_projections(
    root: Path,
    *,
    branch_id: str = "",
    scope_id: str = "",
    source_refs: Optional[Iterable[str]] = None,
    include_legacy: bool = True,
    include_anti_match: bool = True,
    authorized: bool = True,
    profile_version: Optional[str] = None,
    bootstrap: bool = False,
) -> Dict[str, Any]:
    """Read branch/scope-bound Shape projections for aperture disclosure.

    Canonical reads use FoundationRuntime + ProfileRegistry for profile:shape.
    Typed abstentions distinguish absent, incompatible, corrupt, unauthorized,
    empty, and unexpected operational failure. Programming defects propagate.
    Legacy meta_layer signatures are candidate-only and never promoted.
    """
    canonical = _canonical_profile_status(
        root,
        authorized=authorized,
        profile_version=profile_version,
        bootstrap=bootstrap,
    )
    legacy = (
        _load_legacy_projections(
            root,
            branch_id=branch_id,
            scope_id=scope_id,
            source_refs=source_refs,
            include_anti_match=include_anti_match,
        )
        if include_legacy
        else {
            "adapter_version": LEGACY_ADAPTER_VERSION,
            "legacy_profile_id": LEGACY_SHAPE_PROFILE_ID,
            "promotion_allowed": False,
            "candidate_projections": [],
            "anti_match_projections": [],
        }
    )

    has_legacy = bool(legacy["candidate_projections"] or legacy["anti_match_projections"])
    if canonical["available"]:
        readiness_state = "available"
        retrieval_allowed = True
        abstention_reason = canonical["abstention_reason"] if canonical["abstention_code"] == "empty" else None
    elif has_legacy:
        readiness_state = "legacy_only"
        retrieval_allowed = True
        abstention_reason = canonical["abstention_reason"]
    else:
        readiness_state = "unavailable" if not include_legacy else "abstained"
        retrieval_allowed = False
        abstention_reason = canonical["abstention_reason"] or "no_shape_projections_available"

    return {
        "schema_version": CONTRACT_VERSION,
        "contract_id": "ShapeProjectionReader",
        "readiness_state": readiness_state,
        "retrieval_allowed": retrieval_allowed,
        "abstention_code": canonical.get("abstention_code"),
        "abstention_reason": abstention_reason,
        "canonical": canonical,
        "legacy": legacy,
        "filters": {
            "branch_id": str(branch_id or "").strip() or None,
            "scope_id": str(scope_id or "").strip() or None,
            "source_refs": sorted({str(item).strip() for item in list(source_refs or []) if str(item).strip()}),
            "include_legacy": include_legacy,
            "include_anti_match": include_anti_match,
            "authorized": authorized,
            "profile_version": str(profile_version or "").strip() or None,
            "bootstrap": bootstrap,
        },
        "migration_decision": migration_decision(),
        "generated_at": utc_now(),
    }
