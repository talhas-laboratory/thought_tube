# Formation Surface Decision Sheet

Related docs:

- [README](README.md)
- [Glossary](02-glossary.md)
- [Product Scope](01-product-scope.md)
- [Formation Interpolation Research](06-formation-interpolation-research.md)

This is the living decision sheet for the new lightweight surface. Update this
file first when terminology, scope, or implementation order changes.

## Locked decisions

| ID | Status | Decision | Why | Primary surface | Notes |
|---|---|---|---|---|---|
| FS1 | `locked` | `formation` is the root noun | It is broad enough to include thoughts, plans, moods, arguments, scenes, and other meaningful structures. | glossary, UI copy, new docs | absorbs `thought` and `idea` |
| FS2 | `locked` | The user surface is feed-first, with background synthesis hidden underneath | The feed should stay clean, concise, and immediately legible. | feed UI, post composer | presentation layer only |
| FS3 | `locked` | Background processing is modular: extraction -> shape matching -> cross-pollination -> post composition -> ranking -> rendering | Each stage should have a narrow contract so the system can evolve without rewiring everything. | synthesis pipeline | easy to extend later |
| FS4 | `locked` | Feed posts are limited to a small fixed set of post types | A small vocabulary keeps the surface coherent and easy to scan. | composer, renderer | observation, bridge, counterpoint, question, synthesis |
| FS5 | `locked` | The initial scoped ocean excludes OpenClaw conversations | The first product slice should stay focused on the user's private knowledge base. | source routing, visibility control | use the scoped corpus only |
| FS6 | `locked` | Posts must be compact, context-complete, and free of irrelevant clutter | The surface should read like a sharp tweet, not a diagnostic dump. | post formatting | one main claim, enough context |
| FS7 | `locked` | Reuse the existing feed UI as the entry surface | This keeps the first version lightweight and avoids a rewrite. | miniapp | evolve incrementally |
| FS8 | `locked` | The system should cross-pollinate formations with similar isomorphic shapes in the background | Human discovery often comes from interpolation across structurally similar ideas. | matching, synthesis, ranking | structural similarity beats keyword similarity |
| FS9 | `locked` | Every surfaced artifact must remain inspectable and adjustable later | The system should preserve trust, provenance, and the ability to rename things later. | data model, decision sheet | no hidden one-way decisions |
| FS10 | `locked` | Split thesis docs must use repo-relative links | Product docs need to survive clones, server mirrors, and normal Markdown renderers. | all thesis docs | no machine-local absolute paths |
| FS11 | `locked` | The root thesis must preserve a compatibility summary when sections move out | Existing references to `PRODUCT_THESIS.md` should still land on useful guidance even after refactors. | root thesis index | keep relocation map in place |
| FS12 | `locked` | The synthesis pipeline must stay explicit and staged | Retrieval, matching, operator choice, synthesis, stress testing, and rendering should remain separate steps. | synthesis pipeline | no monolithic magic function |
| FS13 | `locked` | Operator selection must return a structured decision, not a bare string | The system needs rationale, confidence, and fallback behavior, not only an operator label. | synthesis pipeline | use a typed operator decision |
| FS14 | `locked` | Surface output must reuse existing thought packet and feed item contracts | The repo already has stable surface objects; do not create a parallel post model unless the current one proves insufficient. | models, thought factory | avoid `FormationPost` duplication |
| FS15 | `locked` | Failed or weak synthesis candidates must enter reviewable storage | Candidate failures are useful evidence and should not disappear silently. | review queue, synthesis artifacts | route weak outputs into review surfaces |
| FS16 | `locked` | Deterministic synthesis comes before model-assisted phrasing | Core matching, scoring, operator routing, and stress tests should be explainable without an LLM in the loop. | synthesis pipeline | model assist is optional cold-path polish |

## Open decisions

| ID | Status | Question | Why it matters | Likely owner |
|---|---|---|---|---|
| OD1 | `open` | Should an expanded item open into a formation view, a clean detail drawer, or a lab-style inspection panel? | This decides how deep the first click should go. | feed UI |
| OD2 | `open` | Which ranking signal should dominate first: relevance, novelty, surprise, or evidence strength? | This controls what the surface feels like day to day. | ranking layer |
| OD3 | `open` | Should synthesis run continuously, on a schedule, or only when new material arrives? | This affects freshness, compute cost, and perceived intelligence. | background pipeline |
| OD4 | `open` | Which source families are allowed in the first visible corpus? | This determines the scope of the feed and what the user trusts it to know. | source visibility |

## Implementation order

1. Keep the glossary canonical and update this sheet first whenever terms
   change.
2. Define the minimal data contracts for formation extraction, shape matching,
   cross-pollination, post composition, and ranking.
3. Reuse the current feed UI as the first presentation surface.
4. Add the minimal post composer and the small fixed post-type vocabulary.
5. Wire source scoping so the feed only sees the approved corpus.
6. Add a deeper formation detail path only if the feed needs it.
7. Preserve portability and compatibility in thesis docs: repo-relative links in
   split files, plus a relocation summary in the root thesis.
8. Build the formation synthesis path on top of existing review and feed
   contracts rather than creating a parallel surface model.

## Implementation plan

### Module ownership

- `knowledge_layer.py`
  - owns candidate retrieval, governance, alias resolution, and evidence-backed
    candidate pair generation
- `conversation_synthesis.py`
  - owns shape comparison, operator routing, synthesis artifacts, and reviewable
    touch results
- `formation_synthesis.py`
  - should be the new sibling module for interpolation operators only
- `thought_factory.py`
  - owns surface shaping only and should emit the final thought packets and feed
    rows
- `models.py`
  - owns typed contracts for the pipeline

### Corrected pipeline

1. `retrieve_candidates`
2. `match_shapes`
3. `choose_operator`
4. `synthesize_candidate`
5. `stress_test_candidate`
6. `emit_thought_packet`

### Corrected contracts

- add internal contracts in `models.py` for:
  - `FormationCandidate`
  - `ShapeMatch`
  - `OperatorDecision`
  - `SynthesisCandidate`
  - `StressTestResult`
- do not add a new top-level `FormationPost` yet
- map successful results into the existing thought surface contracts:
  - `ThoughtPacket`
  - `ThoughtFeedItem`

### Corrected function boundaries

- `retrieve_candidates(root: Path, seed_packet: dict, limit: int = 24) -> list[FormationCandidate]`
  - use a structured seed packet, not a bare string
- `match_shapes(anchor: FormationCandidate, candidates: list[FormationCandidate]) -> list[ShapeMatch]`
  - match against an anchor, not an undirected candidate bag
- `choose_operator(match: ShapeMatch) -> OperatorDecision`
  - return operator key, confidence, rationale, and fallback
- `synthesize_candidate(match: ShapeMatch, decision: OperatorDecision) -> SynthesisCandidate`
- `stress_test_candidate(candidate: SynthesisCandidate) -> StressTestResult`
- `emit_thought_packet(candidate: SynthesisCandidate, stress: StressTestResult) -> dict | None`
  - final surface shaping belongs in `thought_factory.py`

### Storage and review

- successful synthesis artifacts should flow into existing thought packet and
  feed paths
- weak, contradictory, or underspecified candidates should flow into existing
  review surfaces rather than being dropped
- the first implementation should reuse:
  - concept graph touch operations
  - concept review queue
  - product review queue

### First implementation slice

1. add the new internal dataclasses in `models.py`
2. add a new `formation_synthesis.py` with deterministic operator stubs
3. wire `retrieve_candidates` to existing `select_candidate_pairs`
4. wire `emit_thought_packet` to existing `thought_factory.py` output shape
5. store weak outputs in the existing review queue instead of surfacing them

## Editing rule

- If a decision is fully settled, mark it `locked`.
- If a choice still affects implementation, keep it `open`.
- If a later rename or scope shift is likely, put the old term in a note rather
  than changing the canonical term in multiple places.
