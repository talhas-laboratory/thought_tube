# Intelligence Integration — Executive Summary

Full spec: [`docs/frameworks/metaphysical-thought-space/modules/13-intelligence-integration.md`](../../../docs/frameworks/metaphysical-thought-space/modules/13-intelligence-integration.md)

## One-line architecture

**Models interpret → Code governs → Models render under constraint.**

## The scalable stack

1. **Ontology registry** (code) — schemas, relations, roles, versioned
2. **Symbolic kernel** (code) — graph, events, dynamics, motif detection, compile
3. **Intelligence adapters** (models) — extract, embed, render, question — stateless, swappable
4. **Orchestrator** (code) — routes queries to the right pipeline
5. **Surfaces** — never call models directly

## When models vs code

| Models | Code |
|--------|------|
| Unstructured input | Valid structure |
| Fuzzy alignment (embeddings) | Graph math & invariants |
| Naming & rendering | Promotion & audit |
| Soft generation | Deterministic compile (`ArtifactSpec`) |

## Non-negotiable gate

Every model output passes: **schema → ontology → evidence → semantic → epistemic** validation before entering canonical graph.

## Research basis

- Neuro-symbolic memory: LLM for extraction, symbolic engine for lifecycle (NeuSymMS)
- KG + LLM: ontology first, validate before ingest (enterprise GraphRAG patterns)
- Hybrid retrieval: vector seeds graph traversal (GraphRAG / agent memory literature)
- Structured extraction: treat LLM as adversarial; evidence binding reduces hallucination ~60%

## Rollout

A → symbolic kernel → B → extract adapter → C → discovery → D → actualization → E → latent backend (optional)
