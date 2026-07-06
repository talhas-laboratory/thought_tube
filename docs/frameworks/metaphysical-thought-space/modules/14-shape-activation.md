# Module 14 — Shape Activation

## Purpose

Specify how **conditions and context** activate which **shape states** on entities — and how activation results are logged, replayed, and promoted.

Without this module, shape states are labels on snapshots. With it, the system **behaves** differently under cold-start vs formalizing-context vs roadblock-signal.

## Core formulation

> Activation selects which configuration of an entity is live in the current field — without changing entity identity or canonical graph state without promotion.

```text
reduce_identity(quality_graph, activation_context) → ShapeActivationResult
```

## Architectural placement

```text
Layer 2 symbolic kernel
  ├── graph store (entities, shapes, stencils)
  ├── shape index (stencil → shape-instances)
  └── activation engine (this module)
        ↑ reads conditions
        ↑ writes matched_conditions on snapshots
```

Models **propose** condition labels and slot fills. Code **commits** rules and activation results.

---

## Inputs: `ActivationContext`

| Field | Source |
|-------|--------|
| `entity_id` | Target entity |
| `active_qualities` | Current quality graph with intensities |
| `local_relations` | Relations within activation neighborhood |
| `context_field` | Session history, domain anchor, KV-equivalent |
| `formation_phase` | Module 04 enum |
| `subgraph_id` | Scoped bubble |
| `meta_move_id` | Optional — Module 15 |
| `meta_shape_id` | Optional — Module 15 |
| `explicit_lens` | Optional user instruction |
| `problem_signal` | Roadblock detected |

---

## Outputs: `ShapeActivationResult`

```json
{
  "entity_id": "entity-context-field",
  "dominant_shape_id": "shape-anchored-start",
  "secondary_shape_ids": ["shape-cold-start"],
  "shape_weights": { "shape-anchored-start": 0.87, "shape-cold-start": 0.12 },
  "active_stencil_ids": ["stencil-star-bottleneck"],
  "matched_conditions": ["cond-relevant-prior-domain"],
  "confidence": 0.87,
  "evidence": ["context domain overlap 0.72 with query"]
}
```

---

## Condition types

See `schemas/shape-activation-condition.schema.json`.

| Type | Use |
|------|-----|
| `context_domain_overlap` | Anchored start |
| `context_domain_orthogonal` | Polluted start |
| `context_absent` | Cold start |
| `quality_threshold` | Intensity-gated shape |
| `relation_pattern` | Topology match (bottleneck, feedback loop) |
| `formation_phase` | Phase-gated activation |
| `meta_move` | User reasoning move active |
| `meta_shape` | Formalizing / adversarial session arc |
| `explicit_lens` | User-named structural or domain lens |
| `problem_signal` | Roadblock shaping |
| `absence_of_isomorph` | Trigger negative inference path |
| `composite` | AND of subpredicates |

---

## Rule precedence

When multiple conditions match, apply in order:

```text
1. explicit_lens
2. meta_move
3. declared_rule (stabilized)
4. discovered_rule (provisional)
5. default_geodesic (highest-density shape for entity)
```

Co-active shapes use **weighted scores**, not winner-take-all — unless user explicitly requests single-shape mode.

---

## Scoring

```text
score(shape) = Σ (condition_match_i × priority_i × weight_i × role_amplifier)
```

- `role_amplifier` from governing roles ontology (triggering, amplifying, suppressing)
- Suppressed shapes receive near-zero weight but remain in `shape_states`

---

## Cadence policy

| Event | Action |
|-------|--------|
| Session message | Update local quality intensities only (lightweight) |
| Formation phase transition | Run `activate()` on touched entities |
| Session close | Write `activation-snapshot` with `matched_conditions` |
| Problem signal detected | Run `activate()` + `shape_problem()` pipeline (Module 16) |

Do **not** snapshot every token — cost and noise.

---

## Three rule sources

### 1. Declared rules (seed)

Hand-authored or promoted from pilots. See `mappings/pilot-learnings.md`.

### 2. Discovered rules

Mined from snapshot recurrence:

```text
whenever meta_shape=formalizing AND entity=thought-ocean
  → activate shape-structural-skeleton (confidence 0.84, n=3 sessions)
```

Promotion requires replay test on held-out sessions.

### 3. Runtime reducer

`reduce_identity()` applies grammar + intensities when no rule matches — default geodesic on quality graph.

---

## Stencil activation

When a full shape activates, project to stencil and update shape index:

```text
activate(full_shape) → project(stencil) → index.update(shape_instance)
```

Cross-domain salience propagation uses **stencil id**, not full shape id.

---

## Integration points

| Module | Integration |
|--------|-------------|
| 04 Thought Field Dynamics | Snapshots carry `matched_conditions`, `active_stencil_ids` |
| 08 Shape System | Stencil projection from full shape |
| 11 Discovery Pipeline | Discovered rules feed condition promotion |
| 13 Intelligence Integration | `reduce_identity` lives in L2 symbolic kernel |
| 15 Meta Reasoning (planned) | `meta_move` / `meta_shape` as activation inputs |
| 16 Problem Shaping (planned) | `problem_signal` triggers ProblemShape pipeline |

---

## Invariants

1. Activation **describes** live configuration; it does not promote to canonical without separate gate
2. `matched_conditions` required on every snapshot where `activate()` ran
3. Silence valid: if max score < threshold, no shape surface to user
4. Contradictory shapes may co-activate with weights (tension is data)

---

## Module outputs

- `schemas/shape-activation-condition.schema.json`
- `schemas/shape-instance.schema.json`
- `reduce_identity` contract (this document)
- Seed rules in `mappings/pilot-learnings.md`

## Implementation checklist

- [ ] `activate(entity_id, activation_context)` in symbolic kernel
- [ ] Condition registry (declared + discovered partitions)
- [ ] Snapshot writer includes `matched_conditions`
- [ ] Replay test: re-run session → compare predicted vs logged shapes
- [ ] Stencil projection on shape activation
