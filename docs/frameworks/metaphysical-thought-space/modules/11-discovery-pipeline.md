# Module 11 — Discovery Pipeline

## Purpose

Operationalize bottom-up shape discovery so users need not know the pattern in advance.

## Problem statement

Meaningful shapes are **temporary activation patterns**. They appear, shift, decay, merge, disappear. Search-only systems fail.

## Pipeline

```text
capture_traces
  → detect_recurring_activations
  → infer_candidate_shapes
  → test_across_contexts
  → stabilize_useful_shapes
  → search_by_shapes
  → translate_into_artifacts
```

## Top-down vs bottom-up

| Direction | Flow |
|-----------|------|
| Top-down | user defines shape → system finds matches |
| Bottom-up | system observes traces → detects structure → proposes candidate shape |

## Bottom-up signal types

| Detector input | Looks for |
|----------------|-----------|
| recurring entities | corridors, windows, distant figures |
| recurring qualities | empty, sacred, cold, vast, watched |
| recurring relations | normality hides threat; distance intensifies longing |
| recurring transformations | safety → imprisonment; beauty → decay |
| recurring tensions | intimacy vs distance; purity vs corruption |

## Shape detectors (not only search)

| Detector | Function |
|----------|----------|
| similarity | shared qualities |
| contrast | meaningful oppositions |
| recurrence | repeated motifs over time |
| tension | unresolved polarities |
| transformation | repeated state changes |
| missing-link | entities that should connect but don't |
| cluster | groups around shared qualities |
| outlier | anomaly that explains deeper pattern |
| temporal_drift | how shape changes over time |
| cross_domain_translation | same relational shape in another medium |

## Activation snapshots

Capture momentary field state:

```text
activation_snapshot:
  time: 14:32
  dominant_entities: [empty_hallway, childhood, fluorescent_light]
  dominant_qualities: [uncanny, nostalgic, artificial, quiet]
  dominant_relations:
    - artificiality weakens warmth
    - silence intensifies absence
    - childhood_memory reframes commercial_space
  candidate_shape: abandoned_public_nostalgia
```

Track drift:
```text
15:10 — candidate_shape shifted:
  from: abandoned_public_nostalgia
  to: artificial_spaces_as_emotional_containers
```

## Active exploration (shape-revealing questions)

- Is this more about emptiness, nostalgia, artificiality, or absence?
- Does the space feel peaceful, abandoned, or watched?
- Is the key tension human absence or hidden presence?

Infer silently from usage when possible; don't over-question.

## Module outputs

- Detector interface spec
- Snapshot cadence policy
- Candidate pattern confidence thresholds
- Integration with `schemas/activation-snapshot.schema.json`
