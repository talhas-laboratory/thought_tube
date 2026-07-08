# MTSF Gap Plan — Honest closure checklist

**Status:** open (2026-07-08)  
**Purpose:** Name what is broken or missing, define acceptance criteria, and tie each gap to an automated closure test.

## Executive summary

The MTSF **design** describes embedding-grounded semantic neighborhoods that form relational shapes. The **runtime** still admits entities by keyword/seed gates, links sessions by exact name alias, and emits shapes from template triggers. Until semantic geometry is operational, shapes are mostly decorative outside Pilot 002 topology discourse.

**Definition of done for this plan:** `python3 tools/conversation_os.py mtsf run-gap-closure-evals` reports **all required gaps closed**.

---

## Target architecture (closure state)

```text
Input → extract entities/qualities/relations (semantic LLM primary)
      → embed entity carriers (+ evidence spans)
      → semantic kNN adjacency (global)
      → cluster cohesive neighborhoods + relation glue
      → candidate relational shapes + stencil projection
      → activation on seed + discovered entities
      → promote merges/aliases as durable graph events
```

---

## Gap register

| ID | Priority | Gap | Acceptance criteria | Test |
|----|----------|-----|---------------------|------|
| **G01** | P0 | No entity embeddings at ingest | After deep ingest, each entity has `embedding_ref` or session `mtsf/entity_embeddings.json` with ≥1 vector per entity | `gap-G01-entity-embeddings.json` |
| **G02** | P0 | No semantic adjacency on graph | `global_content_graph.adjacency.semantic` populated from kNN (not name-only); edges cite `cosine ≥ threshold` | `gap-G02-semantic-adjacency.json` |
| **G03** | P0 | Cross-register bridge requires keywords | Pair (`subconscious maze`, `context field` prose) links in semantic adjacency **without** shared keywords in either text | `gap-G03-cross-register-bridge.json` |
| **G04** | P0 | Candidate shapes are keyword templates | Candidate shape on hallway OR topology input has `provenance.source=semantic_cluster` (not keyword-only) | `gap-G04-cluster-candidate-shapes.json` |
| **G05** | P0 | Short sensory input silenced | Hallway one-liner yields ≥2 grounded entities via `auto` pipeline | `gap-G05-hallway-semantic-extract.json` |
| **G06** | P1 | Discrimination collapses when extract empty | Hallway vs grocery: entity overlap < 0.5 **and** at least one side has ≥2 entities | `gap-G06-pair-discrimination.json` |
| **G07** | P1 | Topology lacks input-level shapes | Topology triangulation text yields ≥1 `candidate_shapes` with relational_configuration | `gap-G07-topology-candidate-shapes.json` |
| **G08** | P1 | Stencil merge requires exact fingerprint | Hallway uncanny stencil merges to seed at structural_score ≥ 0.8 (fuzzy), not 1.0 only | `gap-G08-fuzzy-stencil-merge.json` |
| **G09** | P1 | Discovered entities stuck at `shape-observed` | Non-catalog entity with rich qualities gets shape label ≠ `shape-observed` when cluster cohesion ≥ threshold | `gap-G09-inferred-discovered-shape.json` |
| **G10** | P1 | Extraction evals don't run live pipeline | `run-extraction-evals` includes ≥1 live-input replay (not reference-only) | `gap-G10-live-extraction-eval.json` |
| **G11** | P2 | Shape utility suite below bar | `run-shape-utility-evals --llm auto` passes ≥5/6 | `gap-G11-shape-utility-bar.json` |
| **G12** | P2 | Discovery pipeline not implemented | Recurring motif across 2 sessions promotes `candidate_shape` with `cross_session_refs` | `gap-G12-cross-session-discovery.json` |
| **G13** | P2 | Shapes don't drive behavior | Traversal or task-pack consumes `dominant_shape_id` / active stencil (integration smoke) | `gap-G13-shape-downstream-hook.json` |

---

## Phase plan

### Phase 0 — Semantic substrate (G01–G03)

1. Add `embed_entity_carriers()` after materialize: name + stable_identity + evidence spans.
2. Persist `memory/sessions/{id}/mtsf/entity_embeddings.json`.
3. Add `refresh_semantic_adjacency()` alongside alias refresh; store cosine on edges.
4. **Do not** remove symbolic evidence/quarantine gates.

### Phase 1 — Shapes from geometry (G04–G07, G05–G06)

1. Replace keyword `_detect_*_candidate_shapes` with cluster cohesion + relation requirement.
2. Wire semantic LLM as primary when backend available (`force` in batch).
3. Hallway + pair discrimination evals must pass.

### Phase 2 — Stencils & discovery (G08–G09, G12)

1. Fuzzy stencil merge in `mtsf_projector` (threshold 0.8 default).
2. Infer discovered-entity shapes from local quality graph.
3. Cross-session recurrence miner → provisional candidate promotion.

### Phase 3 — Product closure (G10–G11, G13)

1. Extend extraction eval runner with live pipeline cases.
2. Shape utility bar ≥5/6 on auto.
3. One downstream consumer (graph-follow `--intent` or task-pack hint).

---

## What we are **not** fixing in this plan

- Replacing the event substrate or collapsing source/derived layers
- Vector DB as primary store (embeddings remain derived index)
- Domain-specific branching in core capture modules
- Pilot 002 replay harness removal (it stays as regression)

---

## Running closure tests

```bash
python3 tools/conversation_os.py mtsf run-gap-closure-evals
python3 tools/conversation_os.py mtsf run-gap-closure-evals --gap G01,G02,G03
```

Unit tests (CI):

```bash
PYTHONPATH=src python3 -m unittest tests.test_mtsf_gap_closure -v
```

**Expected today:** most gap tests **fail** — that is correct. They are the acceptance bar, not a description of current behavior.
