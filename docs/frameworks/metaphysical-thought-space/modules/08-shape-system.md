# Module 08 — Shape System

## Purpose

Define shapes as relational activation configurations — searchable, discoverable, multi-scale, and provisional.

## Core distinction

| Mode | Description |
|------|-------------|
| Known-shape search | User defines pattern; system finds matches |
| Unknown-shape discovery | System infers pattern from traces |

> The system should not require the user to know what they are thinking. It should help reveal the shape of what is trying to become thinkable.

## What a shape is

Not a tag cluster. A **relational configuration**:

Bad: `empty + building + silence`

Good: `social_function + human_absence + residual_memory → haunting`

## Shape formal definition

```text
Shape = selected_qualities + relation_configuration + intensity_weights + context + time
```

## Shape vs entity

- **Entity** = carrier (stable identity)
- **Shape** = current or possible mode of appearance

## Latent shape

A pattern not explicitly named but implied by repeated activations:

```text
latent_shape:
  name: not_yet_known
  evidence: [recurring motifs, relations, qualities]
  possible_abstraction: absence_inside_social_infrastructure
```

## Five shape operations

| Operation | Function |
|-----------|----------|
| shape_search | Find known patterns |
| shape_discovery | Infer unknown patterns from traces |
| shape_stabilization | Temporary activation → reusable pattern |
| shape_translation | Same pattern across domains and scales |
| shape_evolution | Track pattern change over time |

## Shapes as hypotheses

```text
candidate_pattern:
  confidence: medium
  evidence: 14 references, 6 recurring qualities, 3 repeated relation-types
  stability: unstable_but_strengthening
  possible_names: [artificial_nostalgia, commercial_liminality, abandoned_public_memory]
```

Do not force premature naming.

## Partial activation search

User provides fragment → system matches nearby configurations:

```text
vastness + silence + distance + low_threat + emotional_suspension
```

## Multi-scale patterns

Same relational shape at different granularities:

**Example: boundary crossing**
- word level: before/after
- scene level: enters forbidden room
- film level: ordinary world → dream world
- life level: childhood → adulthood
- architecture: outside → threshold → inner chamber

Scale types: micro, scene, project, identity, cultural, metaphysical.

## Traces for inference

- repeated words, moods, images, symbolic motifs
- repeated emotional tensions, relation-types, aesthetic qualities
- recurring transformations
- repeated pull toward certain artifact forms

## Example inferred pattern

Collection: empty malls, airport terminals, hotel corridors, fluorescent light, childhood nostalgia, artificial plants, silence, low-res images, 2000s interiors.

Inferred: *"artificial nostalgia: public interiors abandoned, familiar, commercial, emotionally suspended."*

## Module outputs

- `shape.schema.json`
- `candidate-pattern.schema.json`
- Shape operation enum
- Scale enum
