"""Historical and current-state migration into metaphysical kernel bundles (v1.1 Appendix F).

Authority: docs/workspaces/unified-framework-synthesis/sources/
thought-tube-unified-metaphysical-modeling-framework-v1.1.md#appendix-f
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Sequence

from conversation_os.metaphysical_kernel_contracts import validate_fixture_bundle

MODULE_ID = "kernel.metaphysical.migration"
CONTRACT_VERSION = "1.1.0"
MAPPING_AUTHORITY = (
    "docs/workspaces/unified-framework-synthesis/sources/"
    "thought-tube-unified-metaphysical-modeling-framework-v1.1.md#appendix-f"
)

SOURCE_FAMILIES = frozenset({"mtsf", "thoughtshape", "sds", "conversation_os"})


@dataclass
class MappingRule:
    source_family: str
    source_type: str
    source_id: str
    target_record_kind: str
    target_id: str
    mapping_confidence: float
    semantic_loss_warnings: List[str] = field(default_factory=list)
    reversible: bool = True
    inverse_mapping: Optional[Dict[str, str]] = None

    def to_dict(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "source_family": self.source_family,
            "source_type": self.source_type,
            "source_id": self.source_id,
            "target_record_kind": self.target_record_kind,
            "target_id": self.target_id,
            "mapping_confidence": self.mapping_confidence,
            "semantic_loss_warnings": list(self.semantic_loss_warnings),
            "reversible": self.reversible,
        }
        if self.inverse_mapping:
            payload["inverse_mapping"] = dict(self.inverse_mapping)
        return payload


@dataclass
class MigrationResult:
    fixture_id: str
    source_family: str
    kernel_bundle: Dict[str, Any]
    mapping_rules: List[MappingRule]
    loss_report: List[str]
    reversible: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fixture_id": self.fixture_id,
            "source_family": self.source_family,
            "kernel_bundle": self.kernel_bundle,
            "mapping_rules": [rule.to_dict() for rule in self.mapping_rules],
            "loss_report": list(self.loss_report),
            "reversible": self.reversible,
        }


def _empty_bundle() -> Dict[str, List[Any]]:
    return {
        "source_fragments": [],
        "provenances": [],
        "referents": [],
        "scopes": [],
        "model_branches": [],
        "branch_memberships": [],
        "claims": [],
        "states": [],
        "state_commitments": [],
        "relation_instances": [],
        "profile_definitions": [],
        "profile_conformance_results": [],
    }


def _envelope(
    record_id: str,
    record_kind: str,
    type_id: str,
    *,
    created_at: str,
    created_by: str,
    provenance_id: str,
    maturity_status: str,
    epistemic_status: str,
    governance_status: str,
) -> Dict[str, Any]:
    return {
        "id": record_id,
        "record_kind": record_kind,
        "type_id": type_id,
        "created_at": created_at,
        "created_by": created_by,
        "provenance_id": provenance_id,
        "maturity_status": maturity_status,
        "epistemic_status": epistemic_status,
        "governance_status": governance_status,
    }


def _append_branch_membership(
    bundle: MutableMapping[str, Any],
    *,
    membership_id: str,
    record_id: str,
    branch_id: str,
    scope_id: str,
    provenance_id: str,
    created_at: str,
    membership_kind: str = "asserted",
    introduced_by: str = "service:migration",
) -> None:
    bundle["branch_memberships"].append(
        {
            "envelope": _envelope(
                membership_id,
                "branch_membership",
                "core:branch_membership",
                created_at=created_at,
                created_by=introduced_by,
                provenance_id=provenance_id,
                maturity_status="structured",
                epistemic_status="not_applicable",
                governance_status="local",
            ),
            "record_id": record_id,
            "branch_id": branch_id,
            "membership_kind": membership_kind,
            "effective_scope_id": scope_id,
            "introduced_by": introduced_by,
            "membership_provenance_id": provenance_id,
        }
    )


def migrate_mtsf(
    fixture_id: str,
    source_records: Mapping[str, Any],
    *,
    branch_id: str = "branch_main",
    scope_id: str = "scope_migration",
    created_at: str = "2026-07-12T00:00:00Z",
) -> MigrationResult:
    """Map MTSF IdeaEntity, Assertion, EvidenceSpan, and CandidateShape."""
    bundle = _empty_bundle()
    rules: List[MappingRule] = []
    loss_report: List[str] = []

    idea = dict(source_records.get("idea_entity", {}) or {})
    assertion = dict(source_records.get("assertion", {}) or {})
    evidence = dict(source_records.get("evidence_span", {}) or {})
    candidate_shape = dict(source_records.get("candidate_shape", {}) or {})

    entity_id = str(idea.get("entity_id", "mtsf-entity-unknown"))
    assertion_id = str(assertion.get("assertion_id", "mtsf-assert-unknown"))
    prov_id = f"prov_{fixture_id}"
    sf_id = f"sf_{fixture_id}"

    bundle["source_fragments"].append(
        {
            "envelope": _envelope(
                sf_id,
                "source_fragment",
                "core:source_fragment",
                created_at=created_at,
                created_by="service:migration",
                provenance_id=prov_id,
                maturity_status="raw",
                epistemic_status="not_applicable",
                governance_status="local",
            ),
            "media_type": "text",
            "content_pointer": str(evidence.get("source_ref", f"migration://{fixture_id}")),
            "author_or_origin": "migration:mtsf",
            "captured_at": created_at,
            "integrity_hash": f"sha256:{fixture_id}",
            "source_kind": "import",
        }
    )
    rules.append(
        MappingRule(
            "mtsf",
            "EvidenceSpan",
            sf_id,
            "source_fragment",
            sf_id,
            1.0,
            semantic_loss_warnings=[],
        )
    )

    bundle["provenances"].append(
        {
            "envelope": _envelope(
                prov_id,
                "provenance",
                "core:provenance",
                created_at=created_at,
                created_by="service:migration",
                provenance_id=prov_id,
                maturity_status="structured",
                epistemic_status="not_applicable",
                governance_status="local",
            ),
            "source_refs": [sf_id],
            "derivation_steps": [{"step": "mtsf_import", "source_family": "mtsf"}],
        }
    )

    ref_id = f"ref_{entity_id}"
    bundle["referents"].append(
        {
            "envelope": _envelope(
                ref_id,
                "referent",
                "core:referent",
                created_at=created_at,
                created_by="service:migration",
                provenance_id=prov_id,
                maturity_status="structured",
                epistemic_status="unassessed",
                governance_status="local",
            ),
            "canonical_label": str(idea.get("label", entity_id)),
            "aliases": [],
            "identity_policy_id": f"mtsf:{entity_id}",
        }
    )
    rules.append(
        MappingRule(
            "mtsf",
            "IdeaEntity",
            entity_id,
            "referent",
            ref_id,
            float(idea.get("confidence", 1.0) or 1.0),
            semantic_loss_warnings=["systemhood preserved in identity_policy_id only"],
            inverse_mapping={"referent_id": ref_id, "mtsf_entity_id": entity_id},
        )
    )

    bundle["scopes"].append(
        {
            "envelope": _envelope(
                scope_id,
                "scope",
                "core:scope",
                created_at=created_at,
                created_by="service:migration",
                provenance_id=prov_id,
                maturity_status="structured",
                epistemic_status="not_applicable",
                governance_status="local",
            ),
            "modal_scope": "actual",
            "domain": str(idea.get("systemhood", "")),
        }
    )

    bundle["model_branches"].append(
        {
            "envelope": _envelope(
                branch_id,
                "model_branch",
                "core:model_branch",
                created_at=created_at,
                created_by="service:migration",
                provenance_id=prov_id,
                maturity_status="structured",
                epistemic_status="not_applicable",
                governance_status="local",
            ),
            "parent_branch_id": "",
            "branch_kind": "main",
        }
    )

    claim_id = f"cl_{assertion_id}"
    predicate = str(assertion.get("predicate", "relates"))
    arguments = [str(assertion.get("subject", ref_id)), str(assertion.get("object", ""))]
    bundle["claims"].append(
        {
            "envelope": _envelope(
                claim_id,
                "claim",
                "core:claim",
                created_at=created_at,
                created_by="service:migration",
                provenance_id=prov_id,
                maturity_status="differentiating",
                epistemic_status="candidate",
                governance_status="local",
            ),
            "proposition": {"predicate": predicate, "arguments": arguments},
            "claimant": "migration:mtsf",
            "branch_id": branch_id,
            "scope_id": scope_id,
            "polarity": "affirmative",
        }
    )
    _append_branch_membership(
        bundle,
        membership_id=f"bm_{claim_id}",
        record_id=claim_id,
        branch_id=branch_id,
        scope_id=scope_id,
        provenance_id=prov_id,
        created_at=created_at,
    )
    rules.append(
        MappingRule(
            "mtsf",
            "Assertion",
            assertion_id,
            "claim",
            claim_id,
            float(assertion.get("confidence", 0.5) or 0.5),
            semantic_loss_warnings=["Assertion never migrates directly to State"],
            inverse_mapping={"claim_id": claim_id, "mtsf_assertion_id": assertion_id},
        )
    )

    if candidate_shape:
        shape_name = str(candidate_shape.get("shape_name", ""))
        loss_report.append(
            f"MTSF CandidateShape `{shape_name}` deferred to ShapeCore profile projection"
        )
        rules.append(
            MappingRule(
                "mtsf",
                "CandidateShape",
                shape_name or "unknown_shape",
                "profile:shape_core",
                f"profile_target:{shape_name}",
                float(candidate_shape.get("confidence", 0.5) or 0.5),
                semantic_loss_warnings=[
                    "CandidateShape requires ShapeCore plus ShapeRecord lifecycle profile"
                ],
                reversible=True,
            )
        )

    return MigrationResult(fixture_id, "mtsf", bundle, rules, loss_report, reversible=True)


def migrate_thoughtshape(
    fixture_id: str,
    source_records: Mapping[str, Any],
    *,
    branch_id: str = "branch_main",
    scope_id: str = "scope_migration",
    created_at: str = "2026-07-12T00:00:00Z",
) -> MigrationResult:
    """Map ThoughtShape Hold and StateClaim without collapsing Hold into State."""
    bundle = _empty_bundle()
    rules: List[MappingRule] = []
    loss_report: List[str] = []

    hold = dict(source_records.get("hold", {}) or {})
    state_claim = dict(source_records.get("state_claim", {}) or {})
    station = str(source_records.get("station", "unknown_station"))
    dimension = str(source_records.get("dimension", "unknown_dimension"))
    facet = str(source_records.get("facet", "unknown_facet"))

    prov_id = f"prov_{fixture_id}"
    sf_id = f"sf_{fixture_id}"

    maturity = "held" if hold.get("status") == "unresolved" else "raw"
    bundle["source_fragments"].append(
        {
            "envelope": _envelope(
                sf_id,
                "source_fragment",
                "core:source_fragment",
                created_at=created_at,
                created_by="service:migration",
                provenance_id=prov_id,
                maturity_status=maturity,
                epistemic_status="not_applicable",
                governance_status="local",
            ),
            "media_type": "text",
            "content_pointer": f"migration://thoughtshape/{fixture_id}",
            "author_or_origin": "migration:thoughtshape",
            "captured_at": created_at,
            "integrity_hash": f"sha256:{fixture_id}",
            "source_kind": "import",
        }
    )

    if hold:
        rules.append(
            MappingRule(
                "thoughtshape",
                "Hold",
                str(hold.get("hold_id", f"hold_{fixture_id}")),
                "source_fragment",
                sf_id,
                1.0,
                semantic_loss_warnings=["Hold maps to Field profile hold operation metadata"],
            )
        )
        loss_report.append("ThoughtShape Hold preserved as held SourceFragment, not State")

    bundle["provenances"].append(
        {
            "envelope": _envelope(
                prov_id,
                "provenance",
                "core:provenance",
                created_at=created_at,
                created_by="service:migration",
                provenance_id=prov_id,
                maturity_status="structured",
                epistemic_status="not_applicable",
                governance_status="local",
            ),
            "source_refs": [sf_id],
            "derivation_steps": [
                {
                    "step": "thoughtshape_import",
                    "semantic_address": {
                        "station": station,
                        "dimension": dimension,
                        "facet": facet,
                    },
                }
            ],
        }
    )

    bundle["scopes"].append(
        {
            "envelope": _envelope(
                scope_id,
                "scope",
                "core:scope",
                created_at=created_at,
                created_by="service:migration",
                provenance_id=prov_id,
                maturity_status="structured",
                epistemic_status="not_applicable",
                governance_status="local",
            ),
            "modal_scope": "actual",
            "semantic_address": {
                "station": station,
                "dimension": dimension,
                "facet": facet,
            },
        }
    )

    bundle["model_branches"].append(
        {
            "envelope": _envelope(
                branch_id,
                "model_branch",
                "core:model_branch",
                created_at=created_at,
                created_by="service:migration",
                provenance_id=prov_id,
                maturity_status="structured",
                epistemic_status="not_applicable",
                governance_status="local",
            ),
            "parent_branch_id": "",
            "branch_kind": "main",
        }
    )

    if state_claim:
        claim_id = f"cl_ts_{fixture_id}"
        bundle["claims"].append(
            {
                "envelope": _envelope(
                    claim_id,
                    "claim",
                    "core:claim",
                    created_at=created_at,
                    created_by="service:migration",
                    provenance_id=prov_id,
                    maturity_status="differentiating",
                    epistemic_status="candidate",
                    governance_status="local",
                ),
                "proposition": {
                    "predicate": "has_state_value",
                    "arguments": [station, dimension, facet, str(state_claim.get("state", ""))],
                },
                "claimant": "migration:thoughtshape",
                "branch_id": branch_id,
                "scope_id": scope_id,
                "polarity": "affirmative",
            }
        )
        _append_branch_membership(
            bundle,
            membership_id=f"bm_{claim_id}",
            record_id=claim_id,
            branch_id=branch_id,
            scope_id=scope_id,
            provenance_id=prov_id,
            created_at=created_at,
        )
        rules.append(
            MappingRule(
                "thoughtshape",
                "StateClaim",
                f"{station}:{dimension}:{facet}",
                "claim",
                claim_id,
                float(state_claim.get("confidence", 0.5) or 0.5),
                semantic_loss_warnings=[
                    "weight and salience deferred to ValenceAssessment and SalienceAssessment profiles",
                    "StateClaim does not migrate to State without StateCommitment",
                ],
            )
        )
        loss_report.append("StateClaim migrated as branch-scoped Claim only")

    return MigrationResult(fixture_id, "thoughtshape", bundle, rules, loss_report, reversible=True)


def migrate_sds(
    fixture_id: str,
    source_records: Mapping[str, Any],
    *,
    branch_id: str = "branch_main",
    scope_id: str = "scope_migration",
    created_at: str = "2026-07-12T00:00:00Z",
) -> MigrationResult:
    """Map SDS SystemDynamicSignature records into kernel Referent, Claim, RelationInstance."""
    bundle = _empty_bundle()
    rules: List[MappingRule] = []
    loss_report: List[str] = []

    signature = dict(source_records.get("signature", {}) or {})
    memory_item = dict(source_records.get("shape_memory", {}) or {})
    analogy = dict(source_records.get("analogy_evaluation", {}) or {})

    signature_id = str(signature.get("signature_id", fixture_id))
    prov_id = f"prov_{signature_id}"
    created = str(signature.get("created_at", created_at))

    evidence_spans = list(signature.get("evidence_spans", []) or [])
    if not evidence_spans:
        evidence_spans = [{"source_ref": signature.get("source_ref", ""), "text": signature.get("summary", "")}]

    source_fragment_ids: List[str] = []
    for index, span in enumerate(evidence_spans):
        sf_id = f"sf_{signature_id}_{index}"
        source_fragment_ids.append(sf_id)
        bundle["source_fragments"].append(
            {
                "envelope": _envelope(
                    sf_id,
                    "source_fragment",
                    "core:source_fragment",
                    created_at=created,
                    created_by="service:migration",
                    provenance_id=prov_id,
                    maturity_status="raw",
                    epistemic_status="not_applicable",
                    governance_status="local",
                ),
                "media_type": "text",
                "content_pointer": str(span.get("source_ref", signature.get("source_ref", ""))),
                "author_or_origin": "migration:sds",
                "captured_at": created,
                "integrity_hash": f"sha256:{sf_id}",
                "source_kind": "import",
            }
        )
        rules.append(
            MappingRule(
                "sds",
                "EvidenceSpan",
                str(span.get("chunk_id", sf_id)),
                "source_fragment",
                sf_id,
                1.0,
            )
        )

    bundle["provenances"].append(
        {
            "envelope": _envelope(
                prov_id,
                "provenance",
                "core:provenance",
                created_at=created,
                created_by="service:migration",
                provenance_id=prov_id,
                maturity_status="structured",
                epistemic_status="not_applicable",
                governance_status="local",
            ),
            "source_refs": source_fragment_ids,
            "derivation_steps": [{"step": "sds_import", "signature_id": signature_id}],
        }
    )

    bundle["scopes"].append(
        {
            "envelope": _envelope(
                scope_id,
                "scope",
                "core:scope",
                created_at=created,
                created_by="service:migration",
                provenance_id=prov_id,
                maturity_status="structured",
                epistemic_status="not_applicable",
                governance_status="local",
            ),
            "modal_scope": "actual",
            "domain": str(signature.get("system_boundary", "")),
            "task": str(signature.get("observer_lens", "")),
        }
    )

    bundle["model_branches"].append(
        {
            "envelope": _envelope(
                branch_id,
                "model_branch",
                "core:model_branch",
                created_at=created,
                created_by="service:migration",
                provenance_id=prov_id,
                maturity_status="structured",
                epistemic_status="not_applicable",
                governance_status="local",
            ),
            "parent_branch_id": "",
            "branch_kind": "main",
        }
    )

    entity_id_map: Dict[str, str] = {}
    for entity in signature.get("entities", []) or []:
        if not isinstance(entity, dict):
            continue
        source_entity_id = str(entity.get("entity_id", ""))
        ref_id = f"ref_{source_entity_id}"
        entity_id_map[source_entity_id] = ref_id
        bundle["referents"].append(
            {
                "envelope": _envelope(
                    ref_id,
                    "referent",
                    "core:referent",
                    created_at=created,
                    created_by="service:migration",
                    provenance_id=prov_id,
                    maturity_status="structured",
                    epistemic_status="unassessed",
                    governance_status="local",
                ),
                "canonical_label": str(entity.get("label", source_entity_id)),
                "aliases": [],
                "identity_policy_id": f"sds:{source_entity_id}",
            }
        )
        rules.append(
            MappingRule(
                "sds",
                "SignatureEntity",
                source_entity_id,
                "referent",
                ref_id,
                float(entity.get("confidence", 0.5) or 0.5),
                inverse_mapping={"referent_id": ref_id, "sds_entity_id": source_entity_id},
            )
        )

    for sds_state in signature.get("states", []) or []:
        if not isinstance(sds_state, dict):
            continue
        state_id = str(sds_state.get("state_id", ""))
        claim_id = f"cl_sds_state_{state_id}"
        bundle["claims"].append(
            {
                "envelope": _envelope(
                    claim_id,
                    "claim",
                    "core:claim",
                    created_at=created,
                    created_by="service:migration",
                    provenance_id=prov_id,
                    maturity_status="differentiating",
                    epistemic_status="candidate",
                    governance_status="local",
                ),
                "proposition": {
                    "predicate": "has_condition",
                    "arguments": [state_id, str(sds_state.get("label", ""))],
                },
                "claimant": "migration:sds",
                "branch_id": branch_id,
                "scope_id": scope_id,
                "polarity": "affirmative",
            }
        )
        _append_branch_membership(
            bundle,
            membership_id=f"bm_{claim_id}",
            record_id=claim_id,
            branch_id=branch_id,
            scope_id=scope_id,
            provenance_id=prov_id,
            created_at=created,
        )
        rules.append(
            MappingRule(
                "sds",
                "SignatureState",
                state_id,
                "claim",
                claim_id,
                float(sds_state.get("confidence", 0.5) or 0.5),
                semantic_loss_warnings=["SDS State migrates as Claim until StateCommitment exists"],
            )
        )

    for relation in signature.get("relations", []) or []:
        if not isinstance(relation, dict):
            continue
        rel_id = str(relation.get("relation_id", ""))
        ri_id = f"ri_{rel_id}"
        participants = []
        source_ref = entity_id_map.get(str(relation.get("source_id", "")), str(relation.get("source_id", "")))
        target_ref = entity_id_map.get(str(relation.get("target_id", "")), str(relation.get("target_id", "")))
        participants.append({"role": "source", "ref": source_ref})
        participants.append({"role": "target", "ref": target_ref})
        bundle["relation_instances"].append(
            {
                "envelope": _envelope(
                    ri_id,
                    "relation_instance",
                    f"sds:{relation.get('edge_type', 'relates')}",
                    created_at=created,
                    created_by="service:migration",
                    provenance_id=prov_id,
                    maturity_status="structured",
                    epistemic_status="candidate",
                    governance_status="local",
                ),
                "type_id": f"sds:{relation.get('edge_type', 'relates')}",
                "participants": participants,
                "scope_id": scope_id,
                "qualifiers": {"operation": str(relation.get("operation", ""))},
            }
        )
        rules.append(
            MappingRule(
                "sds",
                "SignatureRelation",
                rel_id,
                "relation_instance",
                ri_id,
                float(relation.get("confidence", 0.5) or 0.5),
            )
        )

    for loop in signature.get("feedback_loops", []) or []:
        if not isinstance(loop, dict):
            continue
        loop_id = str(loop.get("loop_id", ""))
        loss_report.append(f"SDS feedback loop `{loop_id}` deferred to TransformationProcess profile")
        rules.append(
            MappingRule(
                "sds",
                "SignatureFeedbackLoop",
                loop_id,
                "profile:transformation_process",
                f"profile_target:{loop_id}",
                float(loop.get("confidence", 0.5) or 0.5),
                semantic_loss_warnings=["feedback loop requires TransformationProcess profile"],
            )
        )

    for shape in signature.get("candidate_shapes", []) or []:
        if not isinstance(shape, dict):
            continue
        shape_name = str(shape.get("shape_name", ""))
        loss_report.append(f"SDS movement signature `{shape_name}` deferred to Pattern profile")
        rules.append(
            MappingRule(
                "sds",
                "CandidateShape",
                shape_name,
                "profile:pattern",
                f"profile_target:{shape_name}",
                float(shape.get("confidence", 0.5) or 0.5),
                semantic_loss_warnings=["movement signature maps to TransformationShape or Pattern"],
            )
        )

    if memory_item:
        for anti_match in memory_item.get("anti_matches", []) or []:
            loss_report.append(f"SDS anti-match `{anti_match}` deferred to AntiMatch profile record")
            rules.append(
                MappingRule(
                    "sds",
                    "AntiMatch",
                    str(anti_match),
                    "profile:anti_match",
                    f"profile_target:{anti_match}",
                    1.0,
                    semantic_loss_warnings=["anti-match is not identity; preserved as profile projection"],
                )
            )

    if analogy:
        analogy_id = str(analogy.get("analogy_id", ""))
        claim_id = f"cl_analogy_{analogy_id}"
        bundle["claims"].append(
            {
                "envelope": _envelope(
                    claim_id,
                    "claim",
                    "core:claim",
                    created_at=created,
                    created_by="service:migration",
                    provenance_id=prov_id,
                    maturity_status="differentiating",
                    epistemic_status="candidate",
                    governance_status="local",
                ),
                "proposition": {
                    "predicate": "analogy_transfer",
                    "arguments": [analogy_id, str(analogy.get("verdict", ""))],
                },
                "claimant": "migration:sds",
                "branch_id": branch_id,
                "scope_id": scope_id,
                "polarity": "affirmative",
            }
        )
        _append_branch_membership(
            bundle,
            membership_id=f"bm_{claim_id}",
            record_id=claim_id,
            branch_id=branch_id,
            scope_id=scope_id,
            provenance_id=prov_id,
            created_at=created,
        )
        rules.append(
            MappingRule(
                "sds",
                "AnalogyEvaluationPacket",
                analogy_id,
                "claim",
                claim_id,
                float(analogy.get("confidence", 0.5) or 0.5),
                semantic_loss_warnings=[
                    "analogy preserved as transfer claim, never as Referent identity"
                ],
            )
        )

    return MigrationResult(fixture_id, "sds", bundle, rules, loss_report, reversible=True)


def migrate_conversation_os(
    fixture_id: str,
    source_records: Mapping[str, Any],
    *,
    branch_id: str = "branch_main",
    scope_id: str = "scope_migration",
    created_at: str = "2026-07-12T00:00:00Z",
) -> MigrationResult:
    """Map Conversation OS session, events, concept, and formation records."""
    bundle = _empty_bundle()
    rules: List[MappingRule] = []
    loss_report: List[str] = []

    session = dict(source_records.get("session", {}) or {})
    events = list(source_records.get("events", []) or [])
    concept = dict(source_records.get("concept", {}) or {})
    formation = dict(source_records.get("formation_candidate", {}) or {})
    knowledge = dict(source_records.get("workspace_knowledge", {}) or {})

    session_id = str(session.get("session_id", fixture_id))
    prov_id = f"prov_{session_id}"
    started = str(session.get("started_at", created_at))

    source_fragment_ids: List[str] = []
    for index, event in enumerate(events):
        if not isinstance(event, dict):
            continue
        event_id = str(event.get("event_id", f"event_{index}"))
        sf_id = f"sf_{event_id}"
        source_fragment_ids.append(sf_id)
        bundle["source_fragments"].append(
            {
                "envelope": _envelope(
                    sf_id,
                    "source_fragment",
                    "core:source_fragment",
                    created_at=str(event.get("timestamp", started)),
                    created_by=str(event.get("actor", "user:unknown")),
                    provenance_id=prov_id,
                    maturity_status="raw",
                    epistemic_status="not_applicable",
                    governance_status="local",
                ),
                "media_type": "text",
                "content_pointer": f"memory://events/{session_id}/{event_id}",
                "author_or_origin": str(event.get("actor", "user:unknown")),
                "captured_at": str(event.get("timestamp", started)),
                "integrity_hash": f"sha256:{event_id}",
                "source_kind": "user_input",
            }
        )
        rules.append(
            MappingRule(
                "conversation_os",
                "ConversationEvent",
                event_id,
                "source_fragment",
                sf_id,
                1.0,
                inverse_mapping={"source_fragment_id": sf_id, "event_id": event_id},
            )
        )

    if not source_fragment_ids:
        sf_id = f"sf_{session_id}"
        source_fragment_ids.append(sf_id)
        bundle["source_fragments"].append(
            {
                "envelope": _envelope(
                    sf_id,
                    "source_fragment",
                    "core:source_fragment",
                    created_at=started,
                    created_by="service:migration",
                    provenance_id=prov_id,
                    maturity_status="raw",
                    epistemic_status="not_applicable",
                    governance_status="local",
                ),
                "media_type": "text",
                "content_pointer": f"memory://sessions/{session_id}",
                "author_or_origin": "migration:conversation_os",
                "captured_at": started,
                "integrity_hash": f"sha256:{session_id}",
                "source_kind": "import",
            }
        )

    bundle["provenances"].append(
        {
            "envelope": _envelope(
                prov_id,
                "provenance",
                "core:provenance",
                created_at=started,
                created_by="service:migration",
                provenance_id=prov_id,
                maturity_status="structured",
                epistemic_status="not_applicable",
                governance_status="local",
            ),
            "source_refs": source_fragment_ids,
            "derivation_steps": [{"step": "conversation_os_import", "session_id": session_id}],
        }
    )

    bundle["scopes"].append(
        {
            "envelope": _envelope(
                scope_id,
                "scope",
                "core:scope",
                created_at=started,
                created_by="service:migration",
                provenance_id=prov_id,
                maturity_status="structured",
                epistemic_status="not_applicable",
                governance_status="local",
            ),
            "modal_scope": "actual",
            "task": str(session.get("title", "")),
        }
    )

    bundle["model_branches"].append(
        {
            "envelope": _envelope(
                branch_id,
                "model_branch",
                "core:model_branch",
                created_at=started,
                created_by="service:migration",
                provenance_id=prov_id,
                maturity_status="structured",
                epistemic_status="not_applicable",
                governance_status="local",
            ),
            "parent_branch_id": "",
            "branch_kind": "main",
        }
    )

    if concept:
        concept_id = str(concept.get("concept_id", ""))
        ref_id = f"ref_{concept_id}"
        bundle["referents"].append(
            {
                "envelope": _envelope(
                    ref_id,
                    "referent",
                    "core:referent",
                    created_at=started,
                    created_by="service:migration",
                    provenance_id=prov_id,
                    maturity_status="structured",
                    epistemic_status="unassessed",
                    governance_status="local",
                ),
                "canonical_label": str(concept.get("label", concept_id)),
                "aliases": list(concept.get("aliases", []) or []),
                "identity_policy_id": f"concept:{concept_id}",
            }
        )
        rules.append(
            MappingRule(
                "conversation_os",
                "ConceptNode",
                concept_id,
                "referent",
                ref_id,
                float(concept.get("confidence", 0.5) or 0.5),
                semantic_loss_warnings=["abstract_pattern preserved in separate claim, not identity"],
            )
        )
        claim_id = f"cl_concept_{concept_id}"
        bundle["claims"].append(
            {
                "envelope": _envelope(
                    claim_id,
                    "claim",
                    "core:claim",
                    created_at=started,
                    created_by="service:migration",
                    provenance_id=prov_id,
                    maturity_status="differentiating",
                    epistemic_status="candidate",
                    governance_status="local",
                ),
                "proposition": {
                    "predicate": "abstract_pattern",
                    "arguments": [ref_id, str(concept.get("abstract_pattern", ""))],
                },
                "claimant": "migration:conversation_os",
                "branch_id": branch_id,
                "scope_id": scope_id,
                "polarity": "affirmative",
            }
        )
        _append_branch_membership(
            bundle,
            membership_id=f"bm_{claim_id}",
            record_id=claim_id,
            branch_id=branch_id,
            scope_id=scope_id,
            provenance_id=prov_id,
            created_at=started,
        )

    if formation:
        candidate_id = str(formation.get("candidate_id", ""))
        claim_id = f"cl_formation_{candidate_id}"
        bundle["claims"].append(
            {
                "envelope": _envelope(
                    claim_id,
                    "claim",
                    "core:claim",
                    created_at=started,
                    created_by="service:migration",
                    provenance_id=prov_id,
                    maturity_status="differentiating",
                    epistemic_status="candidate",
                    governance_status="local",
                ),
                "proposition": {
                    "predicate": "formation_interpretation",
                    "arguments": [str(formation.get("label", "")), str(formation.get("summary", ""))],
                },
                "claimant": "migration:conversation_os",
                "branch_id": branch_id,
                "scope_id": scope_id,
                "polarity": "affirmative",
            }
        )
        _append_branch_membership(
            bundle,
            membership_id=f"bm_{claim_id}",
            record_id=claim_id,
            branch_id=branch_id,
            scope_id=scope_id,
            provenance_id=prov_id,
            created_at=started,
        )
        rules.append(
            MappingRule(
                "conversation_os",
                "FormationCandidate",
                candidate_id,
                "claim",
                claim_id,
                float(formation.get("candidate_score", 0.5) or 0.5),
            )
        )

    if knowledge:
        record_id = str(knowledge.get("record_id", ""))
        claim_id = f"cl_knowledge_{record_id}"
        bundle["claims"].append(
            {
                "envelope": _envelope(
                    claim_id,
                    "claim",
                    "core:claim",
                    created_at=started,
                    created_by="service:migration",
                    provenance_id=prov_id,
                    maturity_status="differentiating",
                    epistemic_status="candidate",
                    governance_status="local",
                ),
                "proposition": {
                    "predicate": str(knowledge.get("claim_posture", "asserts")),
                    "arguments": [record_id, str(knowledge.get("statement", ""))],
                },
                "claimant": str(knowledge.get("actor", "workspace")),
                "branch_id": branch_id,
                "scope_id": scope_id,
                "polarity": "affirmative",
            }
        )
        _append_branch_membership(
            bundle,
            membership_id=f"bm_{claim_id}",
            record_id=claim_id,
            branch_id=branch_id,
            scope_id=scope_id,
            provenance_id=prov_id,
            created_at=started,
        )
        rules.append(
            MappingRule(
                "conversation_os",
                "WorkspaceKnowledgeRecord",
                record_id,
                "claim",
                claim_id,
                float(knowledge.get("confidence", 0.5) or 0.5),
                semantic_loss_warnings=["workspace knowledge record is claim posture, not adopted State"],
            )
        )
        loss_report.append("Workspace knowledge migrated as Claim; State requires StateCommitment")

    return MigrationResult(fixture_id, "conversation_os", bundle, rules, loss_report, reversible=True)


def migrate_source_fixture(fixture: Mapping[str, Any]) -> MigrationResult:
    """Dispatch migration by source_family."""
    fixture_id = str(fixture.get("fixture_id", "unknown"))
    source_family = str(fixture.get("source_family", ""))
    source_records = dict(fixture.get("source_records", {}) or {})
    options = dict(fixture.get("options", {}) or {})

    if source_family == "mtsf":
        return migrate_mtsf(fixture_id, source_records, **options)
    if source_family == "thoughtshape":
        return migrate_thoughtshape(fixture_id, source_records, **options)
    if source_family == "sds":
        return migrate_sds(fixture_id, source_records, **options)
    if source_family == "conversation_os":
        return migrate_conversation_os(fixture_id, source_records, **options)
    raise ValueError(f"unsupported source_family: {source_family}")


def _states_without_commitment(bundle: Mapping[str, Any]) -> List[str]:
    state_ids = {item["envelope"]["id"] for item in bundle.get("states", []) if isinstance(item, dict)}
    committed = {
        item.get("resulting_state_id")
        for item in bundle.get("state_commitments", [])
        if isinstance(item, dict)
    }
    commitment_linked = {
        item.get("commitment_id")
        for item in bundle.get("states", [])
        if isinstance(item, dict) and item.get("commitment_id")
    }
    uncommitted = []
    for state_id in sorted(state_ids):
        if state_id not in committed and state_id not in commitment_linked:
            uncommitted.append(state_id)
    return uncommitted


def _analogy_identity_violations(rules: Sequence[MappingRule]) -> List[str]:
    violations: List[str] = []
    for rule in rules:
        if rule.source_type in {"AnalogyEvaluationPacket", "Analogy"} and rule.target_record_kind == "referent":
            violations.append(
                f"analogy `{rule.source_id}` illegally mapped to referent `{rule.target_id}`"
            )
    return violations


def validate_migration_result(result: MigrationResult) -> List[str]:
    """Validate migrated kernel bundle and Gate F1 invariants."""
    errors = list(validate_fixture_bundle(result.kernel_bundle))
    errors.extend(_analogy_identity_violations(result.mapping_rules))
    errors.extend(
        f"state `{state_id}` lacks StateCommitment"
        for state_id in _states_without_commitment(result.kernel_bundle)
    )
    if not result.mapping_rules:
        errors.append("migration produced no mapping rules")
    return errors


def validate_migration_fixture(fixture: Mapping[str, Any]) -> List[str]:
    """Validate a migration fixture bundle including optional expected kernel checks."""
    errors: List[str] = []
    fixture_id = str(fixture.get("fixture_id", ""))
    source_family = str(fixture.get("source_family", ""))

    if not fixture_id:
        errors.append("fixture_id is required")
    if source_family not in SOURCE_FAMILIES:
        errors.append(f"unsupported source_family: {source_family}")

    if errors:
        return errors

    if fixture.get("expect_failure"):
        try:
            result = migrate_source_fixture(fixture)
        except ValueError as exc:
            return [str(exc)] if str(fixture.get("expected_error_substring", "")) in str(exc) else [
                f"unexpected error: {exc}"
            ]
        errors.extend(validate_migration_result(result))
        expected = str(fixture.get("expected_error_substring", ""))
        if expected and not any(expected in error for error in errors):
            errors.append(f"expected failure substring not found: {expected}")
        if not errors:
            errors.append("fixture expected failure but migration passed")
        return errors

    result = migrate_source_fixture(fixture)
    errors.extend(validate_migration_result(result))

    expected_loss = list(fixture.get("expected_loss_report", []) or [])
    for item in expected_loss:
        if item not in result.loss_report:
            errors.append(f"expected loss report item missing: {item}")

    expected_counts = fixture.get("expected_record_counts")
    if isinstance(expected_counts, dict):
        for key, expected_count in expected_counts.items():
            actual_count = len(result.kernel_bundle.get(key, []) or [])
            if actual_count != expected_count:
                errors.append(
                    f"kernel_bundle.{key} count {actual_count} != expected {expected_count}"
                )

    return errors


__all__ = [
    "MODULE_ID",
    "CONTRACT_VERSION",
    "MAPPING_AUTHORITY",
    "SOURCE_FAMILIES",
    "MappingRule",
    "MigrationResult",
    "migrate_mtsf",
    "migrate_thoughtshape",
    "migrate_sds",
    "migrate_conversation_os",
    "migrate_source_fixture",
    "validate_migration_result",
    "validate_migration_fixture",
]
