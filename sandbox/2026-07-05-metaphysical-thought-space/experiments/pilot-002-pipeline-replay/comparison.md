# Pilot 002 — Baseline vs MTSF Pipeline Comparison

Generated: 2026-07-06T14:17:43+00:00

## Baseline

- Artifact: Pilot 002 `third-space.json` (manual Formation Agent pass)
- Entities: 12
- Relations: 14
- Activation snapshots: 10
- Candidate pattern: `cand-synthetic-subconscious`

## Pipeline replay — `fast`

- Session: `pilot-002-replay-fast`
- Extraction source: `mtsf_ingest.fast`
- Entities: 6 (baseline recall by id: 0.5)
- Relations: 0 (baseline recall: 0.0)
- Active stencils: stencil-context-warps-topology
- Promotion ready: True

### Entity overlap (ids)

`entity-context-field`, `entity-effective-topology`, `entity-latent-manifold`, `entity-symmetry-engine`, `entity-synthetic-subconscious`, `entity-thought-ocean`

### Entities in baseline but not pipeline

`entity-agent-path`, `entity-dimensional-fiber`, `entity-entity-relationship-state`, `entity-eureka-moment`, `entity-hardened-idea`, `entity-structural-shape`

### Novel entities in pipeline

_none_

### Gaps closed by pipeline

- machine_readable_stencil_schema
- seed_stencil_projection
- shape_instance_bindings

## Pipeline replay — `deep`

- Session: `pilot-002-replay-deep`
- Extraction source: `mtsf_ingest.deep_heuristic`
- Entities: 6 (baseline recall by id: 0.5)
- Relations: 2 (baseline recall: 0.0769)
- Active stencils: stencil-context-warps-topology
- Promotion ready: True

### Entity overlap (ids)

`entity-context-field`, `entity-effective-topology`, `entity-latent-manifold`, `entity-symmetry-engine`, `entity-synthetic-subconscious`, `entity-thought-ocean`

### Entities in baseline but not pipeline

`entity-agent-path`, `entity-dimensional-fiber`, `entity-entity-relationship-state`, `entity-eureka-moment`, `entity-hardened-idea`, `entity-structural-shape`

### Novel entities in pipeline

_none_

### Gaps closed by pipeline

- machine_readable_stencil_schema
- typed_relation_edges_in_pipeline
- seed_stencil_projection
- shape_instance_bindings
