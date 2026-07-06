from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from .mtsf_stencils import (
    compute_structural_fingerprint,
    load_seed_stencils,
    load_stencil_role_types,
    validate_stencil_record,
)
from .storage import ensure_dir, read_json, session_dir, write_json

MODULE_ID = "kernel.mtsf.extraction"
CONTRACT_VERSION = "1.0.0"
SKILL_ID = "semantic-shape-extraction"
SKILL_VERSION = "1.0.0"
PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "SKILL_ID",
    "SKILL_VERSION",
    "QuarantineDecision",
    "ValidationReport",
    "default_extraction_evals_dir",
    "default_skill_path",
    "load_governing_roles",
    "load_relation_primitives",
    "normalize_stencil_draft",
    "validate_extraction_draft",
    "assess_quarantine",
    "match_stencil_drafts_to_seed",
    "materialize_extraction_draft",
    "run_extraction_evals",
)
__all__ = list(PUBLIC_API)

FAST_STAGES = {"capture", "surface", "entities", "qualities", "candidate_shapes"}
DEEP_STAGES = FAST_STAGES | {
    "sub_entities",
    "quality_roles",
    "relations",
    "stencil_drafts",
    "activation_hint",
}
QUARANTINE_CONFIDENCE_THRESHOLD = 0.5


@dataclass
class QuarantineDecision:
    quarantine: bool
    reasons: List[str] = field(default_factory=list)
    promotion_ready: bool = False


@dataclass
class ValidationReport:
    ok: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    stencil_matches: List[Dict[str, Any]] = field(default_factory=list)


def default_extraction_evals_dir(root: Path) -> Path:
    return (
        root
        / "docs"
        / "frameworks"
        / "metaphysical-thought-space"
        / "evals"
        / "semantic-shape-extraction"
    )


def default_skill_path(root: Path) -> Path:
    return (
        root
        / "docs"
        / "frameworks"
        / "metaphysical-thought-space"
        / "skills"
        / "semantic-shape-extraction"
        / "SKILL.md"
    )


def load_governing_roles(root: Path) -> Set[str]:
    path = (
        root
        / "docs"
        / "frameworks"
        / "metaphysical-thought-space"
        / "ontologies"
        / "governing-roles.json"
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    roles: Set[str] = set()
    for row in payload.get("minimal_set", []):
        roles.add(str(row["role"]))
    for class_rows in payload.get("role_classes", {}).values():
        for role in class_rows.get("roles", []):
            roles.add(str(role))
    for role in payload.get("descriptive_roles", {}):
        roles.add(str(role))
    return roles


def load_relation_primitives(root: Path) -> Set[str]:
    path = (
        root
        / "docs"
        / "frameworks"
        / "metaphysical-thought-space"
        / "ontologies"
        / "relation-primitives.json"
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {str(item) for item in payload.get("primitives", [])}


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "item"


def _entity_refs(draft: Dict[str, Any]) -> Set[str]:
    refs: Set[str] = set()
    for key in ("entities", "sub_entities"):
        for row in draft.get(key, []):
            refs.add(str(row.get("proposed_id", "")))
    return {ref for ref in refs if ref}


def _quality_refs(draft: Dict[str, Any]) -> Set[str]:
    return {str(row.get("quality_id", "")) for row in draft.get("qualities", []) if row.get("quality_id")}


def _required_stages(capture_mode: str) -> Set[str]:
    if capture_mode == "fast":
        return set(FAST_STAGES)
    if capture_mode == "deep":
        return set(DEEP_STAGES)
    return set(DEEP_STAGES)


def normalize_stencil_draft(draft: Dict[str, Any]) -> Dict[str, Any]:
    normalized = json.loads(json.dumps(draft))
    role_entities = normalized.get("role_entities", [])
    type_counts: Dict[str, int] = {}
    role_ref_to_id: Dict[str, str] = {}

    for index, row in enumerate(role_entities):
        role_type = str(row.get("role_type", ""))
        role_id = str(row.get("role_id", "")).strip()
        if not role_id:
            count = type_counts.get(role_type, 0) + 1
            type_counts[role_type] = count
            role_id = f"r-{_slug(role_type)}-{count}"
            row["role_id"] = role_id
        role_ref_to_id[role_type] = role_id
        role_ref_to_id[role_id] = role_id

    for edge in normalized.get("relation_topology", []):
        source_ref = str(edge.get("source_role_ref", edge.get("source_role_id", "")))
        target_ref = str(edge.get("target_role_ref", edge.get("target_role_id", "")))
        edge["source_role_id"] = role_ref_to_id.get(source_ref, source_ref)
        edge["target_role_id"] = role_ref_to_id.get(target_ref, target_ref)

    facet = normalized.setdefault("facet_completeness", {})
    facet.setdefault("causal_geometry", True)
    return normalized


def _validate_stencil_draft_item(
    draft: Dict[str, Any],
    *,
    allowed_role_types: Set[str],
    allowed_primitives: Set[str],
) -> List[str]:
    errors: List[str] = []
    normalized = normalize_stencil_draft(draft)
    if not draft.get("proposed_name"):
        errors.append("stencil_draft missing proposed_name")
    evidence = draft.get("evidence", {})
    if not evidence.get("spans"):
        errors.append("stencil_draft missing evidence.spans")

    for row in normalized.get("role_entities", []):
        role_type = str(row.get("role_type", ""))
        if role_type and role_type not in allowed_role_types:
            errors.append(f"stencil_draft unknown role_type: {role_type}")

    for edge in normalized.get("relation_topology", []):
        primitive = str(edge.get("primitive", ""))
        if primitive and primitive not in allowed_primitives:
            errors.append(f"stencil_draft unknown primitive: {primitive}")

    canonical = {
        "id": str(draft.get("proposed_id", draft.get("proposed_name", "stencil-draft"))),
        "name": str(draft.get("proposed_name", "stencil-draft")),
        "role_entities": normalized.get("role_entities", []),
        "relation_topology": normalized.get("relation_topology", []),
        "facet_completeness": normalized.get("facet_completeness", {"causal_geometry": True}),
        "evidence": {"source_refs": evidence.get("source_refs", ["draft"])},
        "views": {
            "gist": draft.get("proposed_name", "stencil draft"),
            "mermaid_topology": "flowchart LR",
            "slot_table": [{"slot_id": "r", "role_type": "source"}],
        },
    }
    errors.extend(validate_stencil_record(canonical, allowed_role_types=allowed_role_types))
    return errors


def validate_extraction_draft(root: Path, draft: Dict[str, Any]) -> ValidationReport:
    errors: List[str] = []
    warnings: List[str] = []

    for field_name in ("draft_id", "input_id", "input_type", "capture_mode", "confidence"):
        if field_name not in draft:
            errors.append(f"missing required field: {field_name}")

    if not draft.get("raw_content") and not draft.get("raw_content_ref"):
        errors.append("raw_content or raw_content_ref required")

    provenance = draft.get("provenance", {})
    if provenance.get("skill_id") != SKILL_ID:
        warnings.append(f"provenance.skill_id expected {SKILL_ID}")
    stages = set(provenance.get("stages_completed", []))
    capture_mode = str(draft.get("capture_mode", ""))
    missing_stages = _required_stages(capture_mode) - stages
    if missing_stages and capture_mode in {"fast", "deep"}:
        warnings.append(f"missing recommended stages for {capture_mode}: {sorted(missing_stages)}")

    governing_roles = load_governing_roles(root)
    relation_primitives = load_relation_primitives(root)
    stencil_role_types = load_stencil_role_types(root)
    entity_refs = _entity_refs(draft)
    quality_refs = _quality_refs(draft)

    for entity in draft.get("entities", []) + draft.get("sub_entities", []):
        if not entity.get("evidence", {}).get("spans"):
            errors.append(f"entity {entity.get('proposed_id', '?')} missing evidence.spans")
        parent = entity.get("parent_entity_ref")
        if parent and parent not in entity_refs:
            errors.append(f"entity {entity.get('proposed_id')} parent not found: {parent}")

    for quality in draft.get("qualities", []):
        if not quality.get("evidence", {}).get("spans"):
            errors.append(f"quality {quality.get('quality_id', '?')} missing evidence.spans")
        entity_ref = quality.get("entity_ref")
        if entity_ref and entity_ref not in entity_refs:
            warnings.append(f"quality {quality.get('quality_id')} entity_ref not found: {entity_ref}")

    for row in draft.get("quality_roles", []):
        role = str(row.get("role", ""))
        if role and role not in governing_roles:
            warnings.append(f"quality_role unknown role: {role}")
        if not row.get("evidence", {}).get("spans"):
            errors.append(f"quality_role for {row.get('quality_ref')} missing evidence.spans")

    for relation in draft.get("relations", []):
        if not relation.get("evidence", {}).get("spans"):
            errors.append("relation missing evidence.spans")
        primitive = str(relation.get("primitive", ""))
        if primitive and primitive not in relation_primitives:
            warnings.append(f"relation unknown primitive: {primitive}")
        for ref_key in ("source_ref", "target_ref"):
            ref = str(relation.get(ref_key, ""))
            if ref and ref not in entity_refs and ref not in quality_refs:
                warnings.append(f"relation {ref_key} not found in draft refs: {ref}")

    for shape in draft.get("candidate_shapes", []):
        if not shape.get("possible_names"):
            errors.append(f"candidate_shape {shape.get('proposed_id')} missing possible_names")
        if not shape.get("evidence", {}).get("spans"):
            errors.append(f"candidate_shape {shape.get('proposed_id')} missing evidence.spans")

    stencil_matches = match_stencil_drafts_to_seed(root, draft.get("stencil_drafts", []))
    for index, stencil_draft in enumerate(draft.get("stencil_drafts", [])):
        stencil_errors = _validate_stencil_draft_item(
            stencil_draft,
            allowed_role_types=stencil_role_types,
            allowed_primitives=relation_primitives,
        )
        for err in stencil_errors:
            errors.append(f"stencil_drafts[{index}]: {err}")

    if capture_mode == "deep" and draft.get("candidate_shapes") and not draft.get("stencil_drafts"):
        warnings.append("deep mode with candidate_shapes but no stencil_drafts")

    return ValidationReport(
        ok=not errors,
        errors=errors,
        warnings=warnings,
        stencil_matches=stencil_matches,
    )


def assess_quarantine(draft: Dict[str, Any], report: ValidationReport) -> QuarantineDecision:
    reasons: List[str] = []
    confidence = float(draft.get("confidence", 0.0))
    if confidence < QUARANTINE_CONFIDENCE_THRESHOLD:
        reasons.append(f"confidence below {QUARANTINE_CONFIDENCE_THRESHOLD}")
    if report.errors:
        reasons.append("validation errors present")
    if len(report.warnings) >= 5:
        reasons.append("high warning count")

    quarantine = bool(reasons)
    promotion_ready = not quarantine and confidence >= 0.75
    return QuarantineDecision(
        quarantine=quarantine,
        reasons=reasons,
        promotion_ready=promotion_ready,
    )


def match_stencil_drafts_to_seed(
    root: Path,
    stencil_drafts: Sequence[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    seed_rows = load_seed_stencils(root)
    seed_by_id = {str(row["id"]): row for row in seed_rows}
    seed_fingerprints = {
        stencil_id: compute_structural_fingerprint(row) for stencil_id, row in seed_by_id.items()
    }
    matches: List[Dict[str, Any]] = []

    for index, draft in enumerate(stencil_drafts):
        normalized = normalize_stencil_draft(draft)
        canonical = {
            "id": str(draft.get("proposed_id", f"draft-{index}")),
            "name": str(draft.get("proposed_name", "draft")),
            "role_entities": normalized.get("role_entities", []),
            "relation_topology": normalized.get("relation_topology", []),
            "dynamics_class": draft.get("dynamics_class"),
            "symmetry_profile": draft.get("symmetry_profile"),
        }
        fingerprint = compute_structural_fingerprint(canonical)
        best_id: Optional[str] = None
        best_score = 0.0
        for seed_id, seed_fp in seed_fingerprints.items():
            score = 1.0 if seed_fp == fingerprint else 0.0
            if score > best_score:
                best_score = score
                best_id = seed_id

        declared_refs = [
            ref.replace("seed:", "")
            for ref in draft.get("evidence", {}).get("source_refs", [])
            if str(ref).startswith("seed:")
        ]
        matches.append(
            {
                "draft_index": index,
                "proposed_name": draft.get("proposed_name"),
                "fingerprint": fingerprint,
                "best_seed_match_id": best_id,
                "structural_score": best_score,
                "declared_seed_refs": declared_refs,
            }
        )
    return matches


def materialize_extraction_draft(
    root: Path,
    session_id: str,
    draft: Dict[str, Any],
) -> Dict[str, Any]:
    report = validate_extraction_draft(root, draft)
    quarantine = assess_quarantine(draft, report)
    payload = dict(draft)
    payload["status"] = "quarantined" if quarantine.quarantine else "validated"
    payload["validation"] = {
        "ok": report.ok,
        "errors": report.errors,
        "warnings": report.warnings,
        "stencil_matches": report.stencil_matches,
    }
    payload["quarantine"] = {
        "quarantine": quarantine.quarantine,
        "reasons": quarantine.reasons,
        "promotion_ready": quarantine.promotion_ready,
    }

    artifact_dir = session_dir(root, session_id) / "mtsf"
    ensure_dir(artifact_dir)
    draft_path = artifact_dir / "extraction_draft.json"
    write_json(draft_path, payload)

    refs: Dict[str, str] = {"mtsf_extraction_draft": str(draft_path)}
    if quarantine.quarantine:
        quarantine_path = artifact_dir / "quarantine.json"
        write_json(
            quarantine_path,
            {
                "session_id": session_id,
                "draft_id": draft.get("draft_id"),
                "reasons": quarantine.reasons,
                "validation_errors": report.errors,
                "validation_warnings": report.warnings,
            },
        )
        refs["mtsf_quarantine"] = str(quarantine_path)

    return {
        "session_id": session_id,
        "artifact_refs": refs,
        "validation_ok": report.ok,
        "quarantine": quarantine.quarantine,
        "promotion_ready": quarantine.promotion_ready,
        "stencil_matches": report.stencil_matches,
    }


def _load_eval_fixture(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _check_expectations(
    draft: Dict[str, Any],
    report: ValidationReport,
    quarantine: QuarantineDecision,
    expectations: Dict[str, Any],
) -> List[str]:
    failures: List[str] = []
    if expectations.get("validation_must_pass") and not report.ok:
        failures.append(f"validation failed: {report.errors}")
    if expectations.get("quarantine_must_pass") and quarantine.quarantine:
        failures.append(f"unexpected quarantine: {quarantine.reasons}")

    entities = draft.get("entities", []) + draft.get("sub_entities", [])
    if len(entities) < int(expectations.get("min_entities", 0)):
        failures.append(f"expected min_entities={expectations.get('min_entities')}, got {len(entities)}")

    entity_blob = " ".join(str(row.get("name", "")).lower() for row in entities)
    for fragment in expectations.get("required_entity_name_fragments", []):
        if fragment.lower() not in entity_blob:
            failures.append(f"missing required entity fragment: {fragment}")
    for fragment in expectations.get("forbidden_entity_name_fragments", []):
        if fragment.lower() in entity_blob:
            failures.append(f"forbidden entity fragment present: {fragment}")

    quality_blob = " ".join(
        " ".join(row.get("labels", []) + [str(row.get("quality_id", ""))]).lower()
        for row in draft.get("qualities", [])
    )
    for fragment in expectations.get("required_quality_fragments", []):
        if fragment.lower() not in quality_blob:
            failures.append(f"missing required quality fragment: {fragment}")

    if len(draft.get("relations", [])) < int(expectations.get("min_relations", 0)):
        failures.append("insufficient relations")
    if len(draft.get("candidate_shapes", [])) < int(expectations.get("min_candidate_shapes", 0)):
        failures.append("insufficient candidate_shapes")
    if len(draft.get("stencil_drafts", [])) < int(expectations.get("min_stencil_drafts", 0)):
        failures.append("insufficient stencil_drafts")
    if len(draft.get("stencil_drafts", [])) > int(expectations.get("stencil_drafts_max", 999)):
        failures.append("too many stencil_drafts for mode")

    if len(draft.get("uncertainties", [])) > int(expectations.get("max_uncertainties", 999)):
        failures.append("too many uncertainties")

    required_seed_refs = expectations.get("required_stencil_seed_refs", [])
    if required_seed_refs:
        refs = []
        for stencil in draft.get("stencil_drafts", []):
            refs.extend(stencil.get("evidence", {}).get("source_refs", []))
        joined = " ".join(refs)
        for seed_ref in required_seed_refs:
            if seed_ref not in joined:
                failures.append(f"missing required stencil seed ref: {seed_ref}")

    return failures


def run_extraction_evals(root: Path) -> Dict[str, Any]:
    evals_dir = default_extraction_evals_dir(root)
    fixtures = sorted(evals_dir.glob("eval-*.json"))
    runs: List[Dict[str, Any]] = []
    passed = 0

    for fixture_path in fixtures:
        fixture = _load_eval_fixture(fixture_path)
        draft_path = evals_dir / str(fixture["reference_draft_path"])
        draft = json.loads(draft_path.read_text(encoding="utf-8"))
        report = validate_extraction_draft(root, draft)
        quarantine = assess_quarantine(draft, report)
        failures = _check_expectations(draft, report, quarantine, fixture.get("expectations", {}))
        ok = not failures
        if ok:
            passed += 1
        runs.append(
            {
                "id": fixture.get("id", fixture_path.stem),
                "ok": ok,
                "validation_ok": report.ok,
                "quarantine": quarantine.quarantine,
                "failures": failures,
                "warnings": report.warnings,
                "stencil_matches": report.stencil_matches,
            }
        )

    return {
        "suite": "semantic-shape-extraction",
        "total": len(fixtures),
        "passed": passed,
        "failed": len(fixtures) - passed,
        "runs": runs,
    }
