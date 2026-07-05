# Module 10 — Quality Roles

## Purpose

Formalize qualities as **role-bearing operators** in entity and shape formation — not passive descriptors.

## Core distinction

| Layer | What it is |
|-------|------------|
| Quality | What is present |
| Relation | How it connects |
| Role | What function it plays in forming entity or shape |

> Quality has role **inside a specific entity-shape under a specific context** — not permanently attached to the quality itself.

## Initial role taxonomy (descriptive)

| Role | Function |
|------|----------|
| defining | Core identity; entity unrecognizable without it |
| modifying | Changes flavor without changing base entity |
| activating | Wakes entity/quality in context |
| relational | Exists only from configuration |
| stabilizing | Holds identity across shapes |
| destabilizing | Pulls toward transformation |
| dominant | Organizes current shape |
| latent | Present but inactive |
| generative | Guides artifact form |

## Governing role ontology (seven classes)

See `ontologies/governing-roles.json` for full minimal set and subtypes.

### 1. Identity roles
core/defining, stabilizing, boundary-setting, anchoring

### 2. Shape roles
modifier, dominant, accent, background, latent

### 3. Activation roles
triggering, amplifying, dampening, foregrounding, suppressing

### 4. Relational roles
mediating, contrasting, fusing, reframing, polarizing

### 5. Directional roles
attractor, repeller, vector, threshold, drift-force

### 6. Transformational roles
mutating, destabilizing, resolving, fragmenting, integrating

### 7. Generative roles
visualizing, narrativizing, sonifying, spatializing, formalizing, symbolizing

## Entity-forming vs shape-forming qualities

| Class | Function | Example (home) |
|-------|----------|----------------|
| entity-forming | Stable identity | belonging, origin, return, familiarity |
| shape-forming | Current appearance | warm (safety), empty (loss), locked (prison) |

## Quality-in-context record

```text
Quality-in-context:
  quality: silence
  entity: empty_hallway
  role: amplifier
  target: unease
  relation: silence intensifies unease
  intensity: 0.8
  confidence: 0.7
  context: dim light, no people, long corridor
```

## Role requirements

Roles must be:
- **contextual** — same quality, different roles
- **weighted** — strength/intensity
- **temporal** — change over time
- **multi-role** — several roles at once
- **open-ended** — custom roles when standard set fails

## Risk: over-formalization

Use a **small governing role ontology** with expandable subtypes. Too many roles → unusable; too few → vague.

## Final formulation

> Qualities are role-bearing operators. Their governing role determines whether they define, stabilize, modify, activate, intensify, destabilize, reframe, resolve, or materialize the entity.

```text
entity = qualities + roles_those_qualities_play + intensity + relations + temporal_activation
```
