# MTSF v1.1 Amendment

**Status:** active amendment to v1.0.0  
**Date:** 2026-07-06  
**Sources:** Pilot 001–003, Gemini latent-topology conversation, framework review session

This document records extensions to the Metaphysical Thought-Space Framework after pressure-testing v1.0 against real conversation transforms, meta reasoning passes, mind-web scale requirements, and cross-domain problem-solving.

v1.0 remains valid. v1.1 **adds** layers and schemas without invalidating existing modules.

---

## Essence (north star)

```text
Everything decomposes into categorized qualities and relations.
Their configuration is a shape.
Shapes are domain-agnostic at the stencil layer.
Entities are where shapes land in a life.
Activation determines what is live.
The mind-web is a federated graph of instances connected by shared stencils.
Problem-solving is stencil match + missing-slot transfer + domain translation.
```

---

## Summary of changes

| Area | v1.0 | v1.1 |
|------|------|------|
| Shape | Single `shape` record | **Stencil** (agnostic core) + **full shape** (contextual skin) |
| Cross-domain links | Implicit in discovery | **Shape index** + `instantiates` wormholes |
| Activation | Snapshots only | **Activation conditions** + `reduce_identity()` contract |
| Graph layers | Content only | **Content + meta + event log** (cross-linked, not merged) |
| Scale | Single graph implied | **Scoped subgraphs / bubbles** |
| Problem-solving | Artifact actualization | **Problem shaping + analogical transfer** |
| Discovery | Always-on implied | **Batch, quarantined, silence as valid output** |
| Promotion | Mentioned | **Explicit merge gates + provisional default** |

---

## New architectural layers

```text
Layer 0 — Grammar (ontology registry: qualities, roles, relation primitives)
Layer 1 — Content graph (entities, qualities, relations, full shapes)
Layer 2 — Shape index (stencils, shape-instances, cross-domain wormholes)
Layer 3 — Meta graph (reasoning moves, stances, signatures) [Module 15 — planned]
Layer 4 — Event log (activations, promotions, merges, snapshots)
```

**Rule:** Meta graph cross-links to content graph. Never merge layers.

---

## New artifacts (v1.1)

### Schemas (implemented in this amendment)

| Schema | Purpose |
|--------|---------|
| `stencil.schema.json` | Domain-agnostic shape core for matching |
| `shape-activation-condition.schema.json` | Condition → shape binding |
| `shape-instance.schema.json` | Entity ↔ stencil instance in subgraph |
| `problem-shape.schema.json` | Roadblock abstraction for transfer pipeline |
| `analogical-match.schema.json` | Structural match + slot diff + translation proposal |

### Schemas (extended)

| Schema | Changes |
|--------|---------|
| `shape.schema.json` | `stencil_id`, `domain_skin`, `dynamics_class`, `symmetry_profile` |
| `entity.schema.json` | `subgraph_id`, `scope`, `alias_of`, `parent_operator_id` |
| `activation-snapshot.schema.json` | `matched_conditions`, `active_stencil_ids`, `meta_shape_id`, `subgraph_id` |

### Modules

| ID | Module | Status |
|----|--------|--------|
| 14 | [Shape Activation](modules/14-shape-activation.md) | **Implemented** |
| 15 | Meta Reasoning Layer | Planned |
| 16 | Problem Shaping & Analogical Transfer | Planned |
| 17 | Mind-Web Operations | Planned |

### Ontology

- Relation primitive added: **`instantiates`** (entity → stencil, entity → shape-instance)
- Dynamics classes enumerated in `stencil.schema.json`
- Structural quality role bucket documented in Module 14

---

## Stencil vs full shape

**Problem:** Cross-domain matching requires domain-agnostic structure. Local meaning requires context.

**Resolution:**

```text
stencil  = role-typed entities + relation topology + dynamics class + symmetry profile
full_shape = stencil + domain_skin + emotional/aesthetic qualities + time + context
```

- **Match** on stencil (orthogonal search: low semantic, high structural similarity)
- **Mean** with full shape (activation, artifacts, user-facing surface)
- **Ingest** extracts full shape; kernel projects to stencil for index

### Progressive facet extraction (default)

When abstracting a note or problem into a stencil, extract facets **in order**:

1. Causal geometry (nodes, directed edges)
2. Temporal dynamics (feedback, growth class, phase)
3. Constraint landscape (tension, tradeoffs, bottlenecks)
4. Cybernetic feedback (control loops, mediation)

Promote each facet when user or code confirms. Do not force single-facet choice upfront.

---

## Shape index and wormholes

Cross-domain connection without explicit entity links:

```text
entity_A (subgraph: work) --instantiates--> stencil_S <--instantiates-- entity_B (subgraph: personal)
```

The stencil is the wormhole. Entities stay local to their bubble.

**Shape index operations:**

- `index_stencil(stencil)` — register or merge near-duplicate stencils
- `find_orthogonal_matches(stencil, max_semantic, min_structural)` — cross-domain search
- `propagate_salience(stencil_id, session_context)` — boost latent entities sharing stencil

---

## Activation engine (Module 14)

`reduce_identity(quality_graph, activation_context) → ShapeActivationResult`

**Inputs:** active qualities, local relations, context field, formation phase, optional meta move/shape, explicit user lens

**Outputs:** dominant shape, secondary shapes (weighted), matched conditions, confidence, evidence

**Rule precedence:**

```text
explicit_lens > meta_move > declared_rule > discovered_rule > default_geodesic
```

**Cadence:** Snapshots on session close and formation phase transitions — not every token.

Seed rules from Pilot 002–003 documented in `mappings/pilot-learnings.md`.

---

## Meta reasoning layer (Module 15 — planned)

From Pilot 003:

- Entity types: `reasoning_move`, `reasoning_signature`, `epistemic_stance`, `meta_shape`
- Cross-links: `move --produced--> content_entity`
- Invariant: **reasoning pattern describes; does not prescribe**
- Gated: activate only after turn threshold + confidence

---

## Problem shaping pipeline (Module 16 — planned)

```text
detect_roadblock
  → shape_problem() → ProblemShape (stencil + problem_signal)
  → search_stencils(prefer_orthogonal=true)
  → diff_missing_slots(current, matches)
  → if no positive match: negative_inference(shadows) → bounding_box
  → translate_to_domain() → ProposalBundle
  → validate → quarantine → user promotes
```

LLM: abstraction, slot filling, translation narrative.  
Code: index, diff, validate, commit.

---

## Mind-web operations (Module 17 — planned)

- Subgraph federation (`subgraph.schema.json` — planned)
- Promotion pipeline: provisional → quarantined → promoted
- Merge 5-test gate: identity invariance, role distinctness, lossy compression, evidence co-reference, stabilization threshold
- Contradiction native: co-active opposing shapes allowed
- Silence policy: no surface when confidence below threshold

---

## New invariants (v1.1)

9. Stencil ≠ full shape — match on stencil, mean in context  
10. Meta graph ≠ content graph  
11. Implicit cross-domain links go through shape index, not entity mesh  
12. Silence is valid system output  
13. Contradiction may remain unresolved  
14. Models propose slot fillers; code owns stencil grammar and promotion  

---

## Rollout alignment (Module 13 update)

| Phase | Deliverable |
|-------|-------------|
| A | Kernel + validators + snapshots + subgraph scoping |
| B | Extract + quarantine + stencil on ingest |
| C | Shape index + declared activation rules (Module 14) |
| D | Meta pass (gated) + problem shaping (Module 16) |
| E | Discovered rules + negative inference (research) |

---

## Pilot consolidation notes

| Pilot | Contribution to v1.1 |
|-------|---------------------|
| 001 | Core ontology, formation agent, three spaces |
| 002 | Thought ocean layers, symmetry engine, synthetic subconscious, context shapes |
| 003 | Meta moves, progressive stencil facets, gap-move correlation |

Merge candidates (provisional, not auto-applied):

- `latent-space` ↔ `latent-manifold` → alias
- `associative-shape` ↔ `structural-shape` → shapes on one entity
- `formation-agent` → parent; subconscious + symmetry → mode shapes

---

## Version

```json
{
  "framework": "metaphysical-thought-space",
  "version": "1.1.0",
  "amends": "1.0.0",
  "contract_version": "2"
}
```
