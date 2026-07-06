# Pilot 002 — Baseline vs MTSF Pipeline Comparison

Generated: 2026-07-06T14:50:14+00:00

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
- Extraction source: `mtsf_ingest.agent_skill`
- Entities: 12 (baseline recall by id: 1.0)
- Relations: 18 (baseline recall: 0.9231)
- Active stencils: stencil-antisymmetric-guardrail, stencil-context-warps-topology, stencil-hardening-loop, stencil-phase-transition-bridge, stencil-symmetric-blueprint
- Promotion ready: True

### Entity overlap (ids)

`entity-agent-path`, `entity-context-field`, `entity-dimensional-fiber`, `entity-effective-topology`, `entity-entity-relationship-state`, `entity-eureka-moment`, `entity-hardened-idea`, `entity-latent-manifold`, `entity-structural-shape`, `entity-symmetry-engine`, `entity-synthetic-subconscious`, `entity-thought-ocean`

### Entities in baseline but not pipeline

_none_

### Novel entities in pipeline

_none_

### Gaps closed by pipeline

- machine_readable_stencil_schema
- typed_relation_edges_in_pipeline
- seed_stencil_projection
- shape_instance_bindings

## Pipeline replay — `agent_skill (LLM substitute)`

- Session: `pilot-002-replay-llm-agent`
- Note: Reference agent-skill draft from interactive pass; deep replay now uses built-in agent extractor by default
- Draft: `/workspace/sandbox/2026-07-05-metaphysical-thought-space/experiments/pilot-002-pipeline-replay/pilot-002-agent-skill-draft.json`
- Extraction source: `agent_skill_pass`
- Entities: 12 (baseline recall by id: 1.0)
- Relations: 16 (baseline recall: 0.7692)
- Active stencils: stencil-antisymmetric-guardrail, stencil-context-warps-topology, stencil-hardening-loop, stencil-phase-transition-bridge, stencil-symmetric-blueprint
- Promotion ready: True

### Entity overlap (ids)

`entity-agent-path`, `entity-context-field`, `entity-dimensional-fiber`, `entity-effective-topology`, `entity-entity-relationship-state`, `entity-eureka-moment`, `entity-hardened-idea`, `entity-latent-manifold`, `entity-structural-shape`, `entity-symmetry-engine`, `entity-synthetic-subconscious`, `entity-thought-ocean`

### Entities in baseline but not pipeline

_none_

### Novel entities in pipeline

_none_

### Gaps closed by pipeline

- machine_readable_stencil_schema
- typed_relation_edges_in_pipeline
- seed_stencil_projection
- shape_instance_bindings
