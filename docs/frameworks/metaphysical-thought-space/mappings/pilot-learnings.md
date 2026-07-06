# Pilot learnings → MTSF v1.1 seeds

Mappings from sandbox pilots to declared activation rules, merge candidates, and stencil patterns.

**Status:** provisional seeds — not canonical until replay-validated.

---

## Activation rule seeds (Pilot 002)

| Condition ID | Entity | Activates shape | Predicate |
|--------------|--------|-----------------|-----------|
| `cond-cold-start` | `entity-context-field` | `shape-cold-start` | `context_absent` |
| `cond-anchored-start` | `entity-context-field` | `shape-anchored-start` | `context_domain_overlap`, min 0.6 |
| `cond-polluted-start` | `entity-context-field` | `shape-polluted-start` | `context_domain_orthogonal`, min 0.6 |
| `cond-formalizing-skeleton` | `entity-thought-ocean` | `shape-structural-skeleton` | `meta_shape=meta-shape-formalizing` |
| `cond-symmetric-blueprint` | `entity-symmetry-engine` | `shape-positive-isomorph` | `meta_move=move-symmetry-extension` |
| `cond-antisymmetric-guardrail` | `entity-symmetry-engine` | `shape-negative-shadow` | `meta_move=move-inversion` |
| `cond-negative-inference` | `entity-hardened-idea` | (sculpt mode) | `meta_move=move-negative-inference` |

Evidence session: `import-69ea1f64f744`

---

## Meta move → content entity (Pilot 003 cross-links)

| Move | Produced / modulated entity |
|------|----------------------------|
| `move-triangulation` | `entity-context-field` |
| `move-escalate-abstraction` | `entity-effective-topology` |
| `move-product-bridge` | `entity-thought-ocean` |
| `move-human-model-validation` | `entity-synthetic-subconscious`, `entity-eureka-moment` |
| `move-formalization-demand` | `entity-structural-shape`, `entity-entity-relationship-state` |
| `move-symmetry-extension` | `entity-symmetry-engine` |

---

## Merge candidates (provisional)

| Action | Entities | Rationale |
|--------|----------|-----------|
| alias | `entity-latent-space` ↔ `entity-latent-manifold` | Same identity, different lens |
| nest shapes | `entity-shape` + `entity-structural-shape` | Hypothesis vs stencil phases |
| relate | `entity-thought-space` hosts `entity-thought-ocean` | Architecture vs personal instance |
| nest modes | `entity-formation-agent` parent of subconscious + symmetry | Operator vs modes |

Apply only via merge 5-test gate (see MTSF-v1.1-amendment.md).

---

## Stencil dynamics classes (recurring in pilots)

- `star_topology` + `bottleneck` — team approval, central node congestion
- `feedback_reinforcing` — interest on debt, population growth
- `reservoir` + depleting phase — burnout, budget deficit
- `broken_symmetry` — effort ≠ output
- `tight_coupling` — fragility, single point of failure

---

## Progressive facet default

From Pilot 003 meta answer:

```text
causal_geometry → temporal_dynamics → constraint_landscape → cybernetic_feedback
```

Promote facet on `move-process-confirmation` or code threshold.

---

## Problem-shaping triggers

| Signal | Roadblock type |
|--------|----------------|
| explicit blockage language | `bottleneck` or `deadlock` |
| `move-negative-inference` | `novel_unmapped` |
| high `unresolvedness` on entity | `constraint_conflict` |
| `move-inversion` without symmetric match | `broken_symmetry` |
