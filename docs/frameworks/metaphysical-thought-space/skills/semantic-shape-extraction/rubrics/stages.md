# Semantic Shape Extraction — Stage Rubrics

Use these narrow prompts per pipeline stage. Each stage outputs JSON fragments that merge into `ExtractionDraft`.

---

## 1. capture

- Preserve `raw_content` or `raw_content_ref` unchanged.
- Assign `input_id`, `input_type`, `capture_mode`, `session_id`, `subgraph_id`.
- Do not interpret yet.

---

## 2. surface

- Note medium (prose, dialogue, scene description).
- List obvious tensions or poles if present.
- Put tentative readings in `uncertainties`, not as facts.

---

## 3. entities

Extract **carriers of identity** (nouns or stable subjects):

- Explicit: named things in the text
- Implied: only when strongly supported (e.g. "fluorescent light" → entity)

For each entity:

```json
{
  "proposed_id": "entity-hallway",
  "name": "hallway",
  "type": "composite",
  "stable_identity": ["architectural passage"],
  "confidence": 0.9,
  "evidence": { "spans": ["empty hallway"] }
}
```

Rules:

- Do not invent entities absent from evidence.
- `stable_identity` is durable; do not put momentary mood here.

---

## 4. sub_entities

Nested parts of composites:

- `type: sub_entity`
- `parent_entity_ref` required
- Use for: light, silence-as-field, inner critic, etc.

Skip in `fast` mode unless obvious.

---

## 5. qualities

Extract **active quality regions** with intensity 0..1:

```json
{
  "quality_id": "quality-watched",
  "quality_type": "emotional",
  "intensity": 0.82,
  "kind": "emergent",
  "entity_ref": "entity-hallway",
  "labels": ["watched", "tense"],
  "evidence": { "spans": ["peaceful but also watched"] }
}
```

Rules:

- Qualities are regions, not single words only.
- Mark `kind`: intrinsic vs contextual vs emergent.

---

## 6. quality_roles

Assign governing roles from `governing-roles.json`:

```json
{
  "quality_ref": "quality-empty",
  "entity_ref": "entity-hallway",
  "role": "defining",
  "confidence": 0.8,
  "evidence": { "spans": ["empty hallway"] }
}
```

Roles: defining, modifying, amplifying, dampening, contrasting, latent, dominant, etc.

---

## 7. relations

Extract **typed relational structure**:

```json
{
  "source_ref": "quality-empty",
  "target_ref": "quality-watched",
  "level": "quality_quality",
  "relation_type": "amplifies",
  "primitive": "intensifies",
  "domain_expression": "emptiness intensifies watchedness",
  "weight": 0.78,
  "confidence": 0.72,
  "evidence": { "spans": ["peaceful but also watched"] }
}
```

Rules:

- Prefer standard `relation_type` + `primitive` pairs.
- `domain_expression` preserves local wording.
- Relations explain shape — not a list of associations.

---

## 8. candidate_shapes

Hypothesis-level relational configurations:

```json
{
  "proposed_id": "cand-uncanny-calm",
  "possible_names": ["uncanny calm", "artificial solitude"],
  "relational_configuration": "empty + artificial light + quiet → watched stillness",
  "entity_refs": ["entity-hallway"],
  "quality_refs": ["quality-empty", "quality-watched"],
  "confidence": 0.76,
  "evidence": { "spans": ["feels peaceful but also watched"] }
}
```

Do not force a name if confidence is low — use `possible_names` array.

---

## 9. stencil_drafts (deep mode)

Project to **domain-agnostic topology**. Consult `seed/stencils.json`.

Example pattern (context warps felt landscape):

```json
{
  "proposed_name": "emptiness modulates watched stillness",
  "role_entities": [
    { "role_type": "field" },
    { "role_type": "landscape" }
  ],
  "relation_topology": [
    {
      "source_role_ref": "field",
      "target_role_ref": "landscape",
      "primitive": "modulates"
    }
  ],
  "dynamics_class": "gradient",
  "symmetry_profile": "asymmetric",
  "facet_completeness": { "causal_geometry": true },
  "confidence": 0.74,
  "evidence": {
    "spans": ["empty hallway", "peaceful but also watched"],
    "source_refs": ["seed:stencil-context-warps-topology"]
  }
}
```

Rules:

- Match seed exemplar when structurally similar; note in `evidence.source_refs`.
- Max 7 roles, 12 edges.
- No domain nouns in role_entities.

---

## 10. activation_hint

Temporary activation only — never overwrite stable entity:

```json
{
  "formation_phase": "partial_population",
  "dominant_entity_refs": ["entity-hallway"],
  "active_quality_refs": ["quality-empty", "quality-watched"]
}
```

Pair with session `activation_snapshot` on materialize — do not merge into entity `stable_identity`.
