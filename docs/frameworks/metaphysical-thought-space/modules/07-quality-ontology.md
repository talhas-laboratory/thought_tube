# Module 07 — Quality Ontology

## Purpose

Define how idea-entities carry meaning through qualities — not as physical properties but as semantic-affective structures.

## Core formulation

> An idea-entity is not defined only by what it is, but by what qualities it carries, how intensely, how they change over time, and which emerge from relations.

## Quality vs physical property

| Physical object | Idea-entity |
|-----------------|-------------|
| color, size, weight, texture, position, material, temperature | mood, intensity, clarity, symbolic charge, abstraction level, emotional tone, direction, stability, relation-density, unresolvedness, generative potential |

## Ten quality types

See `ontologies/quality-types.json`:

1. **sensory** — perception-like imagination (bright, hollow, echoing)
2. **emotional** — how it feels (sad, reverent, uncanny)
3. **symbolic** — meaning-charge (sacred, forbidden, ancestral)
4. **formal** — shape/structure (layered, fragmented, recursive)
5. **temporal** — behavior over time (recurring, fading, suspended)
6. **relational** — relation-density (central, anchoring, unresolved)
7. **functional** — role in thought-space (anchors, reveals, transforms)
8. **ontological** — felt reality (vivid, dreamlike, archetypal)
9. **generative** — artifact readiness (visualizable, narrativizable, interface-ready)
10. **meta-state** — clarity, intensity, stability, unresolvedness, generative potential (scalar state dimensions)

## Intrinsic vs contextual/emergent

| Kind | Description |
|------|-------------|
| intrinsic | Seems to belong to entity itself (knife → sharpness) |
| contextual/emergent | Appears from relations and field (knife beside sleeping person → threatening) |

Same entity, field changes qualities (red light: romantic / dangerous / sacred / uncanny / bureaucratic).

## Qualities as semantic regions (not labels)

Three layers:

1. **underlying quality-pattern** — what you point at (eeriness, sacredness)
2. **semantic framing** — interpretation (uncanny, off, liminal, haunted)
3. **linguistic expression** — actual wording ("something feels off")

> Quality = a semantic region that can be described from multiple angles.

### Mapping types

- **many-to-one:** different descriptions → same quality region
- **one-to-many:** same word → different quality clusters by context ("warm")

### Quality region record

```text
core_quality_region, possible_labels, nearby_synonyms, contrast_terms,
associated_imagery, associated_emotions, intensity, contextual_shifts
```

## Qualities are internally associative

Qualities are mini-entities / sub-fields:

```text
entity → qualities → sub-qualities → associations → relations
```

Sacredness bundle: elevation, stillness, purity, reverence, distance, ritual, light, silence, order, awe.

## Intensity

Qualities have degree, not binary presence:

```text
empty_city_street: silent 0.9, threatening 0.6, nostalgic 0.3, sacred 0.1, cinematic 0.8
```

Qualities shift over time (lonely → peaceful as dominance changes).

## Universal vs particular (trope theory)

- **Universal quality types:** sadness, warmth, threat (standardized categories)
- **Particular quality instances:** the specific sadness of an unchanged childhood room (cannot fully reduce to label)

## Object formation (relational + weighted)

Not: `object = A + B + C`

But:
```text
object = qualities + relations_between_qualities + weighted_importance
```

Silence alone insufficient:
- silence + warmth + safety = peace
- silence + darkness + hidden presence = fear
- silence + vastness + ritual = sacredness
- silence + social absence + longing = loneliness

## Emergent object identity

```text
object_identity = core_qualities + relational_configuration + weighted_salience
                + temporal_stability + contextual_interpretation
```

> A metaphysical object is an emergent configuration of qualities whose relations create meaning, while intensity and importance determine which meaning becomes dominant.

## Cross-domain translation

Artifacts form by translating qualities across domains:

| Domain | sacred loneliness qualities → |
|--------|-------------------------------|
| film | wide shot, minimal movement, distant figure, huge sky |
| music | slow tempo, reverb, sparse piano, low drone |
| architecture | large empty chamber, cool stone, high ceiling |
| writing | short sentences, restrained language, distance imagery |
| branding | minimal layout, negative space, muted palette |
| interface | spacious UI, slow transitions, quiet typography |

## Example entity schema

See `schemas/entity.schema.json` and worked example in Module 05.
