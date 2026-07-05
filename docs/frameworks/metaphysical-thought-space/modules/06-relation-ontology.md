# Module 06 — Relation Ontology

## Purpose

Provide an open, layered grammar for how inner objects connect — the semantic skeleton.

## Core thesis

> Sub-entities are highly individual, but relation-types between them can be partially standardized.

> Thought entities are individually infinite, but their interactions follow recurring relational grammars.

## Metaphor

- Sub-entities = flesh
- Relations = bones and nerves
- Intensities = energy
- Temporal sequence = life of the thought

## Four relation levels

| Level | Pattern | Example |
|-------|---------|---------|
| 1. entity ↔ entity | Associative mapping | abandoned church resembles monastery hallway |
| 2. quality ↔ entity | What shapes an entity | sacredness defines church; decay modifies church |
| 3. quality ↔ quality | Internal object formation | silence intensifies reverence; decay contrasts purity |
| 4. entity ↔ artifact | Thought to output | sacred loneliness materializes-as wide shot with empty sky |

## Relation record fields

```text
relation_type, source, target, weight, confidence, context,
polarity, temporality, source_evidence, role
```

**Role values:** defines | modifies | supports | destabilizes | resolves

Weights are practical, not claims of objective measurement.

## Three-layer vocabulary architecture

### Layer 1 — Universal primitives

Stable backbone. See `ontologies/relation-primitives.json`.

### Layer 2 — Domain-specific types

Film, music, design, psychology dialects. See `ontologies/relation-domain-extensions.json`.

### Layer 3 — User-specific language

Custom poetic phrases mapped to standard types; original phrase preserved.

Example record:
```text
standard_relation_type: symbolizes
custom_relation_phrase: "makes it feel ancient and unreachable"
confidence: medium
evidence: user phrase, image, memory, output
intensity: 0.78
direction: A → B
time: emerged later
```

## Cross-domain hierarchy

```text
concrete_instance → domain_specific_relation → cross_domain_archetype → broad_relational_category
```

Examples:
- syncopation → music rhythm disruption → expectation break → tension relation
- foreshadowing → narrative setup → early signal with future payoff → temporal relation
- affordance → design action possibility → enables behavior → functional relation

**Limitation:** Cross-domain categories capture structural similarity, not full equivalence.

## Ten broad relational categories

See `ontologies/relation-categories.json` for full archetype lists:

1. Boundary relations
2. Force relations
3. Temporal relations
4. Similarity and echo relations
5. Tension relations
6. Resolution relations
7. Transformation relations
8. Interpretive relations
9. Functional relations
10. Emergence relations

## Composite relations

One utterance may decompose into multiple atomic relations:

> "empty hallway makes childhood memory feel sacred but unreachable"

→ evokes distance, intensifies unreachability, anchors sacredness, transforms loss into reverence

## Completeness

The list is **not closed**. Reasons:
- Domain-specific relations (syncopates, foreshadows, projects)
- Personal/poetic relations ("blue light forgives the room")
- Composite multi-force relations

## Object formation via relations

> A metaphysical object is a weighted relational graph of qualities whose internal interactions produce its emergent identity.

The relation ontology is not only for navigation — it **forms objects**.

## Relation ontology questions

- What qualities define this object? (core)
- What qualities only decorate it? (peripheral)
- What qualities are in tension? (conflict)
- What intensifies/suppresses? (amplification/dampening)
- What creates emergent meaning? (combination)
