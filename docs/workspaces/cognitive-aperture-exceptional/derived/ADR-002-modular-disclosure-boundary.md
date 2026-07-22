# ADR-002 — Modular Disclosure Boundary

**Status:** accepted
**Date:** 2026-07-19
**Workspace:** `cognitive-aperture-exceptional`

## Context

The aperture program originally assumed an available knowledge ocean and proposed a shared `disclose()` kernel across product surfaces. Current inspection shows an empty local runtime corpus, an interrupted materialization pipeline, a legacy heuristic Shape-signature system, and a canonical framework SDK that correctly abstains because the Shape profile is not registered.

Allowing the aperture layer to repair ingestion or define another Shape store would create a large, coupled subsystem and competing semantic authority.

## Decision

The aperture program owns disclosure only.

It consumes versioned, branch- and scope-aware read interfaces for corpus readiness, candidate search, canonical Shape projections, and evidence resolution. It does not ingest sources, create canonical records, promote Shapes, manage embeddings, or own source truth.

The legacy `meta_layer` Shape pipeline may supply provisional candidates through an adapter. Canonical Shape identity and promotion remain owned by the Unified Metaphysical Framework Shape and Semantic Addressing profile. The knowledge layer is a derived retrieval projection, not a third canonical store.

The shared disclosure service is an orchestration boundary. Surface-specific behavior remains in adapters.

## Consequences

- Corpus and Shape readiness become explicit release gates.
- Dependency unavailability produces abstention, never broader fallback.
- `disclose()` depends on ports rather than importing product surfaces.
- Bridge and Holodeck are the first conformance consumers.
- Feed, task-pack, and World Studio adoption are deferred until parity is proven.
- Raw source text is stored once and referenced by derived projections and receipts.

## Non-decisions

- This ADR does not choose an embedding provider or vector database.
- It does not redesign canonical Shape semantics.
- It does not require learned reranking.
- It does not require all queries to use Shape reasoning.

## Links

- [`ADR-001`](./ADR-001-orient-grant-evidence-receipt.md)
- [`GAP_MAP.md`](./GAP_MAP.md)
- [`Modular Cognitive Aperture Design`](../../../plans/2026-07-19-cognitive-aperture-modular-disclosure-design.md)
