# Module 09 — Association Engine

## Purpose

Formalize how associative connection strength is computed between objects.

## Core rule

> The more meaningful qualities two objects share, the stronger their associative connection usually is.

Refined:

> Associative connection depends on shared qualities weighted by intensity, rarity, role, context, and personal relevance.

## Simple formula

```text
associative_strength = shared_qualities × quality_intensity × quality_rarity × role_similarity × context_relevance
```

## Complete formula

```text
Association(A, B) =
  similarity_links
  + contrast_links
  + causal_links
  + symbolic_links
  + temporal_links
  + functional_links
  + personal_memory_links
```

Shared qualities are only **one pathway** of association.

## Weighting factors

| Factor | Effect |
|--------|--------|
| Generic shared quality (large, bright) | Weak association |
| Semantically loaded shared quality (sacred, liminal, post-human) | Strong association |
| Intensity match | silence 0.9 ↔ 0.8 stronger than ↔ 0.2 |
| Role similarity | silence-as-reverence ≠ silence-as-threat |
| Rare quality-combination | Stronger than isolated shared traits |
| Constellation match | blue-grey + sacred + abandoned + vast > blue + big |

## Association types (beyond similarity)

| Type | Example |
|------|---------|
| similarity | shared qualities |
| contrast | fire ↔ water (oppositional, not similar) |
| complementarity | key ↔ door (functional fit) |
| causality | childhood home ↔ grief (memory link) |
| symbolic mapping | one represents the other |

## Implementation notes

- Compare quality regions, not only labels
- Weight defining/core qualities higher than peripheral
- Include contrast and functional links in graph traversal
- Personal memory links are user-specific, high weight when present

## Module outputs

- Association type enum
- Weighting function spec (inputs: quality fields, roles, context)
- Link record schema (extends relation schema)
