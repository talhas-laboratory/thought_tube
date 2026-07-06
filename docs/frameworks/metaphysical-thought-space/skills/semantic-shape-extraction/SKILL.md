---
name: semantic-shape-extraction
description: >-
  MTSF semantic shape extraction for Conversation OS. Proposes evidence-backed
  ExtractionDraft records (entities, qualities, relations, candidate shapes,
  stencil drafts) from any raw input. Code validates, quarantines, and
  materializes; never auto-promotes to canonical graph. Use when saving notes,
  importing conversations, reflecting, or ingesting artifacts into the thought graph.
skill_version: "1.0.0"
framework: "mtsf@1.1.0"
schema: "mtsf://schemas/extraction-draft"
references:
  - rubrics/stages.md
  - ../../../schemas/extraction-draft.schema.json
  - ../../../schemas/stencil-draft.schema.json
  - ../../../seed/stencils.json
  - ../../../ontologies/governing-roles.json
  - ../../../ontologies/relation-primitives.json
  - ../../../ontologies/stencil-role-types.json
---

# Semantic Shape Extraction (MTSF)

Extract structured semantic shapes from raw input using a **fixed pipeline**. You are a structured extractor, not a free-form analyst.

## Non-negotiable rules

1. **Output `ExtractionDraft` JSON only** — no essay analysis as the primary artifact.
2. **Never write canonical graph state** — propose drafts; code validates and quarantines.
3. **Every entity, quality, relation, and shape must cite evidence spans** from the source.
4. **Distinguish stable entity identity from temporary activation shape.**
5. **Distinguish intrinsic qualities from contextual/emergent qualities.**
6. **Use closed ontologies** for primitives and roles; custom labels only when standard categories fail (flag in `uncertainties`).
7. **Stencil drafts use role_types, not domain nouns** — see `seed/stencils.json` for exemplars.
8. **Silence is valid** — empty `stencil_drafts` with explained `uncertainties` beats forced structure.
9. **Do not speculate beyond evidence** — no unsupported psychosocial or political interpretations.

## When to invoke

- User saves a note, journal entry, or reflection
- User imports a conversation or artifact
- User uploads reference material for the mind-web
- Session close follow-up needs structured extraction from raw content
- Pattern discovery mode across multiple inputs (batch; compare snapshots)

## Capture modes

| Mode | Stages | Output depth |
|------|--------|--------------|
| `fast` | capture, surface, entities, qualities, candidate_shapes (0–1) | Light snapshot hint only |
| `deep` | all stages incl. relations, quality_roles, stencil_drafts | Full draft + stencil topology |
| `pattern_discovery` | deep + cross-input comparison notes in uncertainties | For batch; compare activation hints |

## Pipeline (run in order)

```text
1. capture          — preserve raw input ref; bind input_id
2. surface          — note tone, medium, obvious tensions (in uncertainties if unclear)
3. entities         — explicit + lightly implied carriers of identity
4. sub_entities     — nested parts (optional in fast mode)
5. qualities        — active quality regions with intensity
6. quality_roles    — defining / modifying / amplifying / etc.
7. relations        — typed edges; map relation_type → primitive when possible
8. candidate_shapes — relational configurations (hypothesis labels)
9. stencil_drafts   — domain-agnostic topology (deep mode only)
10. activation_hint — formation_phase, dominant refs (never overwrite stable entity)
```

Stage rubric: [rubrics/stages.md](rubrics/stages.md)

## Skill input envelope

```json
{
  "input_id": "note-2026-07-06-hallway",
  "input_type": "text",
  "raw_content": "...",
  "capture_mode": "deep",
  "session_id": "optional-session-id",
  "subgraph_id": "personal",
  "context": {
    "user_goal": "capture mood",
    "domain": "personal",
    "tags": []
  }
}
```

## Skill output envelope

Emit a single `ExtractionDraft` object per `schemas/extraction-draft.schema.json`.

Required top-level fields:

- `draft_id`, `input_id`, `input_type`, `capture_mode`
- `provenance.skill_id` = `semantic-shape-extraction`
- `provenance.skill_version` = `1.0.0`
- `provenance.stages_completed` — list stages actually run
- `confidence` — overall 0..1
- `entities`, `qualities`, `relations` (may be empty in fast mode if truly absent)
- `uncertainties`, `user_questions` — preserve ambiguity

Deep mode additionally requires:

- at least one `candidate_shapes` entry when shape signal exists
- `stencil_drafts` when structural pattern is clear (else explain in uncertainties)
- each `stencil_drafts[]` item must satisfy `stencil-draft.schema.json`

## Ontology defaults

Set on every draft:

```json
"ontology_refs": {
  "governing_roles": "mtsf://ontologies/governing-roles@1.0.0",
  "relation_primitives": "mtsf://ontologies/relation-primitives@1.1.0",
  "stencil_role_types": "mtsf://ontologies/stencil-role-types@1.0.0"
}
```

## Relation extraction contract

Always attempt:

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

Code validates `primitive` against `relation-primitives.json`. If mapping is uncertain, set `primitive` to best guess and add `uncertainties`.

## Stencil draft contract (deep mode)

Pattern-match against `seed/stencils.json` before inventing topology.

Minimum viable stencil draft:

- `proposed_name`, `role_entities` (2–7), `relation_topology` (1–12)
- `facet_completeness.causal_geometry: true`
- `evidence.spans` (≥1)
- `confidence`

Use `role_type` from stencil-role-types ontology. Never put "hallway" or "capitalism" in `role_entities`.

## Handoff to code

After emitting JSON, invoke (or request orchestrator to run):

```bash
python3 tools/conversation_os.py mtsf validate-extraction --draft-path path/to/draft.json
python3 tools/conversation_os.py mtsf materialize-extraction --session-id SESSION --draft-path path/to/draft.json
```

Code will:

1. Validate schema and ontology
2. Score quarantine (low confidence, missing evidence, invalid enums)
3. Match `stencil_drafts` fingerprints against seed library
4. Write `memory/sessions/{id}/mtsf/extraction_draft.json`
5. Write `quarantine.json` when promotion gates fail
6. **Not** merge into stable entity graph automatically

## Eval suite

Run regression evals:

```bash
python3 tools/conversation_os.py mtsf run-extraction-evals
```

Fixtures: `evals/semantic-shape-extraction/`

## Failure behavior

| Condition | Action |
|-----------|--------|
| Low confidence (<0.5) | Emit draft + quarantine; ask `user_questions` |
| No structural signal | Omit `stencil_drafts`; document in uncertainties |
| Ambiguous entity/quality boundary | Keep both interpretations in uncertainties |
| Invalid ontology value | Propose nearest enum + flag for code rejection |

## Central principle

> Propose evidence-backed, confidence-scored semantic shapes. Code owns grammar, fingerprints, quarantine, and promotion.
