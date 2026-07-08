# Gap closure evals

One fixture per gap in `GAP_PLAN.md`. Each fixture defines an automated check that must pass before the gap is considered closed.

## Fixture schema

```json
{
  "gap_id": "G01",
  "title": "short name",
  "phase": "P0",
  "required": true,
  "check": {
    "type": "artifact_field | pipeline | graph_adjacency | stencil_merge | suite_pass_rate | cross_session",
    "...": "type-specific fields"
  }
}
```

## Check types

| type | Verifies |
|------|----------|
| `artifact_field` | Post-ingest artifact exists and matches schema |
| `pipeline` | Live extraction/activation metrics on input text |
| `graph_adjacency` | Global graph adjacency kind populated with evidence |
| `stencil_merge` | Fuzzy merge score against seed stencil |
| `suite_pass_rate` | Another eval suite meets pass threshold |
| `cross_session` | Two-session recurrence / promotion behavior |
