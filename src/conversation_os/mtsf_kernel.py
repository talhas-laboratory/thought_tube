from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

MODULE_ID = "kernel.mtsf.activation"
CONTRACT_VERSION = "1.1.0"
PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "ActivationContext",
    "ActivationCondition",
    "EntityActivationRecord",
    "ShapeActivationResult",
    "default_seed_conditions_path",
    "load_activation_conditions",
    "load_seed_conditions",
    "evaluate_predicate",
    "reduce_identity",
    "activate",
    "build_activation_snapshot",
    "replay_pilot_002_scenarios",
    "run_replay_scenarios",
)
__all__ = list(PUBLIC_API)

RULE_SOURCE_RANK = {
    "explicit_lens": 5,
    "meta_move": 4,
    "meta_shape": 3,
    "declared": 2,
    "seed_pilot": 2,
    "discovered": 1,
}


@dataclass
class ActivationContext:
    entity_id: str
    context_domain_overlap: float = 0.0
    context_domain_orthogonal: float = 0.0
    context_absent: bool = False
    formation_phase: Optional[str] = None
    meta_move_id: Optional[str] = None
    meta_shape_id: Optional[str] = None
    explicit_lens: Optional[str] = None
    problem_signal: bool = False
    subgraph_id: Optional[str] = None
    session_id: Optional[str] = None
    quality_intensities: Dict[str, float] = field(default_factory=dict)


@dataclass
class EntityActivationRecord:
    id: str
    shape_state_ids: List[str] = field(default_factory=list)
    default_shape_id: Optional[str] = None


@dataclass
class ActivationCondition:
    id: str
    entity_id: str
    activates_shape_id: str
    predicate: Dict[str, Any]
    priority: float = 0.5
    weight: float = 0.5
    rule_source: str = "declared"
    status: str = "provisional"

    @classmethod
    def from_dict(cls, row: Dict[str, Any]) -> "ActivationCondition":
        return cls(
            id=str(row["id"]),
            entity_id=str(row["entity_id"]),
            activates_shape_id=str(row["activates_shape_id"]),
            predicate=dict(row["predicate"]),
            priority=float(row.get("priority", 0.5)),
            weight=float(row.get("weight", 0.5)),
            rule_source=str(row.get("rule_source", "declared")),
            status=str(row.get("status", "provisional")),
        )


@dataclass
class ShapeActivationResult:
    entity_id: str
    dominant_shape_id: Optional[str]
    secondary_shape_ids: List[str]
    shape_weights: Dict[str, float]
    matched_conditions: List[str]
    confidence: float
    evidence: List[str]
    active_stencil_ids: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def default_seed_conditions_path(root: Path) -> Path:
    return (
        root
        / "docs"
        / "frameworks"
        / "metaphysical-thought-space"
        / "seed"
        / "activation-conditions.json"
    )


def load_activation_conditions(path: Path) -> List[ActivationCondition]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("conditions", [])
    return [ActivationCondition.from_dict(row) for row in rows]


def load_seed_conditions(root: Path) -> List[ActivationCondition]:
    return load_activation_conditions(default_seed_conditions_path(root))


def evaluate_predicate(predicate: Dict[str, Any], ctx: ActivationContext) -> bool:
    predicate_type = str(predicate.get("type", ""))

    if predicate_type == "context_absent":
        return bool(ctx.context_absent)

    if predicate_type == "context_domain_overlap":
        minimum = float(predicate.get("min_overlap_score", 0.6))
        return ctx.context_domain_overlap >= minimum and not ctx.context_absent

    if predicate_type == "context_domain_orthogonal":
        minimum = float(predicate.get("min_overlap_score", 0.6))
        return ctx.context_domain_orthogonal >= minimum and not ctx.context_absent

    if predicate_type == "meta_move":
        return bool(ctx.meta_move_id) and ctx.meta_move_id == predicate.get("meta_move_id")

    if predicate_type == "meta_shape":
        return bool(ctx.meta_shape_id) and ctx.meta_shape_id == predicate.get("meta_shape_id")

    if predicate_type == "explicit_lens":
        return bool(ctx.explicit_lens) and ctx.explicit_lens == predicate.get("lens")

    if predicate_type == "formation_phase":
        return bool(ctx.formation_phase) and ctx.formation_phase == predicate.get("formation_phase")

    if predicate_type == "problem_signal":
        return bool(ctx.problem_signal)

    if predicate_type == "quality_threshold":
        quality_id = str(predicate.get("quality_id", ""))
        minimum = float(predicate.get("min_intensity", 0.5))
        return ctx.quality_intensities.get(quality_id, 0.0) >= minimum

    if predicate_type == "composite":
        subpredicates = predicate.get("subpredicates", [])
        return all(evaluate_predicate(sub, ctx) for sub in subpredicates)

    return False


def _predicate_rule_rank(predicate: Dict[str, Any]) -> int:
    predicate_type = str(predicate.get("type", ""))
    if predicate_type == "explicit_lens":
        return RULE_SOURCE_RANK["explicit_lens"]
    if predicate_type == "meta_move":
        return RULE_SOURCE_RANK["meta_move"]
    if predicate_type == "meta_shape":
        return RULE_SOURCE_RANK["meta_shape"]
    return 0


def _condition_rank(condition: ActivationCondition) -> int:
    explicit = _predicate_rule_rank(condition.predicate)
    if explicit:
        return explicit
    return RULE_SOURCE_RANK.get(condition.rule_source, 0)


def reduce_identity(
    entity: EntityActivationRecord,
    ctx: ActivationContext,
    conditions: Sequence[ActivationCondition],
    *,
    surface_threshold: float = 0.35,
) -> ShapeActivationResult:
    return activate(entity, ctx, conditions, surface_threshold=surface_threshold)


def activate(
    entity: EntityActivationRecord,
    ctx: ActivationContext,
    conditions: Sequence[ActivationCondition],
    *,
    surface_threshold: float = 0.35,
) -> ShapeActivationResult:
    applicable = [c for c in conditions if c.entity_id == entity.id and c.status != "deprecated"]
    shape_weights: Dict[str, float] = {}
    matched: List[str] = []
    evidence: List[str] = []

    for condition in applicable:
        if not evaluate_predicate(condition.predicate, ctx):
            continue
        rank_boost = 1.0 + (_condition_rank(condition) * 0.05)
        score = condition.priority * condition.weight * rank_boost
        shape_weights[condition.activates_shape_id] = (
            shape_weights.get(condition.activates_shape_id, 0.0) + score
        )
        matched.append(condition.id)
        evidence.append(
            f"{condition.id} -> {condition.activates_shape_id} (score={score:.3f})"
        )

    if not shape_weights:
        fallback = entity.default_shape_id or (entity.shape_state_ids[0] if entity.shape_state_ids else None)
        if fallback:
            shape_weights[fallback] = 0.25
            evidence.append(f"default_geodesic -> {fallback}")

    ranked = sorted(shape_weights.items(), key=lambda item: item[1], reverse=True)
    dominant = ranked[0][0] if ranked else None
    secondary = [shape_id for shape_id, weight in ranked[1:] if weight >= surface_threshold]
    confidence = ranked[0][1] if ranked else 0.0
    if confidence > 1.0:
        confidence = min(confidence, 1.0)

    return ShapeActivationResult(
        entity_id=entity.id,
        dominant_shape_id=dominant,
        secondary_shape_ids=secondary,
        shape_weights=dict(ranked),
        matched_conditions=matched,
        confidence=confidence,
        evidence=evidence,
    )


def build_activation_snapshot(
    *,
    snapshot_id: str,
    session_id: Optional[str],
    subgraph_id: Optional[str],
    formation_phase: Optional[str],
    meta_shape_id: Optional[str],
    results: Sequence[ShapeActivationResult],
) -> Dict[str, Any]:
    matched_conditions: List[str] = []
    active_stencil_ids: List[str] = []
    for result in results:
        matched_conditions.extend(result.matched_conditions)
        active_stencil_ids.extend(result.active_stencil_ids)

    return {
        "id": snapshot_id,
        "session_id": session_id,
        "subgraph_id": subgraph_id,
        "formation_phase": formation_phase,
        "meta_shape_id": meta_shape_id,
        "matched_conditions": sorted(set(matched_conditions)),
        "active_stencil_ids": sorted(set(active_stencil_ids)),
        "shape_activation_results": [result.to_dict() for result in results],
    }


def replay_pilot_002_scenarios() -> List[Dict[str, Any]]:
    return [
        {
            "name": "cold_start",
            "entity": EntityActivationRecord(
                id="entity-context-field",
                shape_state_ids=["shape-cold-start", "shape-anchored-start", "shape-polluted-start"],
                default_shape_id="shape-cold-start",
            ),
            "context": ActivationContext(
                entity_id="entity-context-field",
                context_absent=True,
            ),
            "expected_dominant": "shape-cold-start",
            "expected_conditions": ["cond-cold-start"],
        },
        {
            "name": "anchored_start",
            "entity": EntityActivationRecord(
                id="entity-context-field",
                shape_state_ids=["shape-cold-start", "shape-anchored-start", "shape-polluted-start"],
            ),
            "context": ActivationContext(
                entity_id="entity-context-field",
                context_domain_overlap=0.72,
            ),
            "expected_dominant": "shape-anchored-start",
            "expected_conditions": ["cond-anchored-start"],
        },
        {
            "name": "polluted_start",
            "entity": EntityActivationRecord(
                id="entity-context-field",
                shape_state_ids=["shape-cold-start", "shape-anchored-start", "shape-polluted-start"],
            ),
            "context": ActivationContext(
                entity_id="entity-context-field",
                context_domain_orthogonal=0.8,
            ),
            "expected_dominant": "shape-polluted-start",
            "expected_conditions": ["cond-polluted-start"],
        },
        {
            "name": "formalizing_thought_ocean",
            "entity": EntityActivationRecord(
                id="entity-thought-ocean",
                shape_state_ids=[
                    "shape-raw-manifold",
                    "shape-structural-skeleton",
                    "shape-knowledge-reef",
                ],
                default_shape_id="shape-raw-manifold",
            ),
            "context": ActivationContext(
                entity_id="entity-thought-ocean",
                meta_shape_id="meta-shape-formalizing",
                formation_phase="artifact_formation",
            ),
            "expected_dominant": "shape-structural-skeleton",
            "expected_conditions": ["cond-formalizing-skeleton"],
        },
        {
            "name": "symmetry_extension",
            "entity": EntityActivationRecord(
                id="entity-symmetry-engine",
                shape_state_ids=["shape-positive-isomorph", "shape-negative-shadow"],
            ),
            "context": ActivationContext(
                entity_id="entity-symmetry-engine",
                meta_move_id="move-symmetry-extension",
            ),
            "expected_dominant": "shape-positive-isomorph",
            "expected_conditions": ["cond-symmetric-blueprint"],
        },
        {
            "name": "inversion_guardrail",
            "entity": EntityActivationRecord(
                id="entity-symmetry-engine",
                shape_state_ids=["shape-positive-isomorph", "shape-negative-shadow"],
            ),
            "context": ActivationContext(
                entity_id="entity-symmetry-engine",
                meta_move_id="move-inversion",
            ),
            "expected_dominant": "shape-negative-shadow",
            "expected_conditions": ["cond-antisymmetric-guardrail"],
        },
        {
            "name": "explicit_lens_overrides_meta",
            "entity": EntityActivationRecord(
                id="entity-symmetry-engine",
                shape_state_ids=["shape-positive-isomorph", "shape-negative-shadow"],
            ),
            "context": ActivationContext(
                entity_id="entity-symmetry-engine",
                meta_move_id="move-inversion",
                explicit_lens="structural_isomorph",
            ),
            "expected_dominant": "shape-positive-isomorph",
            "expected_conditions": ["cond-antisymmetric-guardrail", "cond-explicit-structural-lens"],
        },
    ]


def run_replay_scenarios(
    root: Path,
    scenarios: Optional[Sequence[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    conditions = load_seed_conditions(root)
    selected = list(scenarios or replay_pilot_002_scenarios())
    runs: List[Dict[str, Any]] = []
    passed = 0

    for scenario in selected:
        entity: EntityActivationRecord = scenario["entity"]
        context: ActivationContext = scenario["context"]
        result = activate(entity, context, conditions)
        dominant_ok = result.dominant_shape_id == scenario.get("expected_dominant")
        expected_conditions = set(scenario.get("expected_conditions", []))
        condition_ok = expected_conditions.issubset(set(result.matched_conditions))
        ok = dominant_ok and condition_ok
        if ok:
            passed += 1
        runs.append(
            {
                "name": scenario["name"],
                "ok": ok,
                "expected_dominant": scenario.get("expected_dominant"),
                "actual_dominant": result.dominant_shape_id,
                "expected_conditions": sorted(expected_conditions),
                "matched_conditions": result.matched_conditions,
                "confidence": result.confidence,
                "evidence": result.evidence,
            }
        )

    return {
        "experiment": "pilot-002-activation-replay",
        "total": len(selected),
        "passed": passed,
        "failed": len(selected) - passed,
        "runs": runs,
    }
