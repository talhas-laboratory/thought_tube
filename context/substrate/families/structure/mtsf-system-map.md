# MTSF Progressive Graph System Map

North star: **qualities + relations → shape** — match on stencil, mean in context.

## Progressive layers

```text
T0  Substrate      events.jsonl, import files           immutable source
T1  Assertions     assertion_store.json                 all claims + evidence
T2  Content graph  content_graph.json                   handles + adjacency
T3  Shape index    shape_index.json                     stencils + wormholes
T4  Activation     activation_snapshot.json, graph.json what is live now
```

## Pipeline order

```text
session close/import
  → ingest (fast|deep)
  → extraction_draft (validate, quarantine)
  → assertion_store + content_graph
  → stencil projection + shape_index
  → activation snapshot
```

## Invariants

Models propose. Code validates, materializes, and owns canonical graph state. Traverse T2 by default; expand into T1/T0 for audit.
