# Shape Signature Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a kernel-owned shape signature layer that derives typed system-dynamic signatures from existing source-backed material, projects them into structural graph artifacts, and upgrades structural matching and memory without breaking current Inner World surfaces.

**Architecture:** Keep the repo's current source-of-truth model intact: sessions, source chunks, and analysis units remain canonical, while shape signatures become rebuildable derived artifacts. Implement the new layer as kernel modules plus file-backed JSONL artifacts, then integrate it into the existing runtime pipeline, synthesis layer, and review/memory surfaces in thin slices.

**Tech Stack:** Python, existing JSON/JSONL artifact storage, repo runtime pipeline, dataclasses in `models.py`, existing review/governance surfaces, deterministic scoring helpers, optional LLM adapters later

---

## Scope and sequencing

This plan intentionally does **not** build a separate FastAPI/Postgres service first.

First implementation target:

- file-backed kernel modules
- rebuildable runtime integration
- deterministic structural matching
- governed shape memory

Deferred:

- service extraction
- external database persistence
- UI surfaces
- full analogy generation workflows
- knowledge-layer structural reranking beyond a thin optional hook

## Execution gates

Before any code task starts, run the repo-required guard with the smallest
plausible edit surface for that task.

Required preflight:

```bash
python3 tools/conversation_os.py repo-overview refresh
python3 tools/conversation_os.py engineering-guard assess \
  --request "<task-specific request>" \
  --purpose "<concrete user/system effect>" \
  --proposed-paths "<comma-separated task paths>"
```

Rules:

- If the guard is not `ready`, narrow the task before editing code.
- Do not group unrelated tasks under one guard assessment.
- Run `repo-overview refresh` again after adding new modules or manifests.
- Run `repo-overview validate` before claiming the implementation branch is ready.

Implementation should stop after each task if a test failure implies changing a
module outside the listed files. Reassess ownership instead of expanding the
edit surface casually.

## File map

### New files

- `src/conversation_os/shape_signatures.py`
  - extract and persist `SystemDynamicSignature` rows from analysis/meta inputs
- `src/conversation_os/shape_graph.py`
  - project signatures into node/edge rows and expose deterministic overlap helpers
- `src/conversation_os/shape_memory.py`
  - own file-backed memory items, anti-matches, and validation updates
- `context/substrate/modules/kernel.shape.shape_signatures.json`
  - module manifest for signature extraction ownership
- `context/substrate/modules/kernel.shape.shape_graph.json`
  - module manifest for graph projection and scoring ownership
- `context/substrate/modules/kernel.shape.shape_memory.json`
  - module manifest for memory and anti-match ownership
- `tests/test_shape_signatures.py`
  - unit tests for extraction, graph projection, deterministic scoring, and memory updates

### Modified files

- `src/conversation_os/models.py`
  - add dataclasses for signature, graph, evaluation, and memory artifacts
- `src/conversation_os/runtime_pipeline.py`
  - add a `shape_signatures` runtime component after `thread_abstractions`
- `src/conversation_os/conversation_synthesis.py`
  - attach signature refs to candidates and update matching to use structural scores
- `src/conversation_os/knowledge_layer.py`
  - optional later hook only; do not modify until the synthesis path proves the
    new structural score is useful
- `src/conversation_os/product_inner_world.py`
  - do not modify in the first pass; surface status can wait until kernel behavior is stable
- `tests/test_conversation_os.py`
  - add integration coverage for pipeline rebuild and session artifact materialization if needed

### Existing files to read carefully before editing

- `src/conversation_os/analysis_units.py`
- `src/conversation_os/meta_layer.py`
- `src/conversation_os/meta_objects.py`
- `src/conversation_os/thread_abstractions.py`
- `src/conversation_os/review_queue.py`
- `docs/plans/2026-05-24-shape-signature-layer-design.md`

## Runtime artifact layout

These are the new derived artifacts the implementation should produce:

- `product/inner_world_v1/data/shape_reasoning/shape_signatures.jsonl`
- `product/inner_world_v1/data/shape_reasoning/shape_graph_nodes.jsonl`
- `product/inner_world_v1/data/shape_reasoning/shape_graph_edges.jsonl`
- `product/inner_world_v1/data/shape_reasoning/shape_memory.jsonl`
- `product/inner_world_v1/data/shape_reasoning/review_queue.jsonl`
- `memory/sessions/<session_id>/analysis/shape_signatures.json`
- `memory/sessions/<session_id>/analysis/shape_reasoning.json`

## Task 1: Add kernel dataclasses and artifact paths

**Files:**
- Modify: `src/conversation_os/models.py`
- Test: `tests/test_shape_signatures.py`

- [ ] **Step 1: Write failing schema tests**

Add tests that instantiate and round-trip:

- `SystemDynamicSignature`
- `ShapeGraphNode`
- `ShapeGraphEdge`
- `ShapeMemoryItem`
- `AnalogyEvaluationPacket`

Include assertions that:

- required fields are present
- `to_dict()` preserves the expected keys
- optional fields default correctly
- nested lists remain plain JSON-serializable dictionaries after `to_dict()`
- confidence and score fields can be compared as floats

- [ ] **Step 2: Run schema tests to verify failure**

Run:

```bash
pytest tests/test_shape_signatures.py -k schema -v
```

Expected:

- failure because the new dataclasses do not yet exist

- [ ] **Step 3: Add new dataclasses to `models.py`**

Add dataclasses for:

- `EvidenceSpan`
- `SignatureEntity`
- `SignatureState`
- `SignatureRelation`
- `SignatureFeedbackLoop`
- `SignatureConstraint`
- `SignatureAbsence`
- `SignatureAffordance`
- `CandidateShape`
- `AlternativeInterpretation`
- `SystemDynamicSignature`
- `ShapeGraphNode`
- `ShapeGraphEdge`
- `AnalogyEvaluationPacket`
- `ShapeMemoryItem`

Rules:

- keep names repo-native and explicit
- use existing dataclass style and `to_dict()` pattern
- keep the contracts file-backed and serialization-friendly
- do not introduce Pydantic or SQL dependencies in this slice
- keep IDs as strings, matching existing repo artifact style

- [ ] **Step 4: Re-run schema tests**

Run:

```bash
pytest tests/test_shape_signatures.py -k schema -v
```

Expected:

- PASS for the new schema tests

- [ ] **Step 5: Commit**

```bash
git add src/conversation_os/models.py tests/test_shape_signatures.py
git commit -m "feat: add shape signature dataclasses"
```

## Task 2: Implement file-backed signature extraction

**Files:**
- Create: `src/conversation_os/shape_signatures.py`
- Create: `context/substrate/modules/kernel.shape.shape_signatures.json`
- Modify: `src/conversation_os/models.py`
- Test: `tests/test_shape_signatures.py`

- [ ] **Step 1: Write failing extraction tests**

Cover:

- extraction from a small synthetic source with evidence-backed meta records
- preservation of `constraints`, `absences`, and `affordances`
- presence of `candidate_shapes`, `alternative_interpretations`, and `confidence`
- artifact write/read round-trip to `shape_signatures.jsonl`

Use a fixture case close to:

- product feature accumulation
- missing primary path
- user confusion under overload

- [ ] **Step 2: Run extraction tests to verify failure**

Run:

```bash
pytest tests/test_shape_signatures.py -k extraction -v
```

Expected:

- failure because the extractor module and helpers do not yet exist

- [ ] **Step 3: Implement `shape_signatures.py`**

Add:

- path helpers for the new artifact family
- `load_shape_signatures(root: Path) -> list[dict]`
- `build_shape_signatures(root: Path) -> dict`
- `build_session_shape_signatures(root: Path, session_id: str) -> dict`
- `load_session_shape_signatures(root: Path, session_id: str) -> list[dict]`
- extraction helpers that read:
  - analysis units
  - meta records
  - thread abstractions where useful

Behavior:

- build provisional signatures from evidence-backed clusters
- preserve `source_refs`, `chunk_ids`, and evidence snippets
- attach `status="provisional"` by default
- store alternative interpretations instead of flattening uncertainty
- use deterministic heuristic extraction in this slice
- do not call an LLM yet
- write per-session analysis artifacts only for closed sessions or explicit session calls

Manifest:

- add a module manifest with `module_id: kernel.shape.shape_signatures`
- set `layer: kernel`
- set owner to signature extraction and persistence
- list `analysis_units`, `meta_layer`, `thread_abstractions`, `models`, and `storage` as dependencies

- [ ] **Step 4: Re-run extraction tests**

Run:

```bash
pytest tests/test_shape_signatures.py -k extraction -v
```

Expected:

- PASS for extraction and persistence behavior

- [ ] **Step 5: Commit**

```bash
git add src/conversation_os/shape_signatures.py context/substrate/modules/kernel.shape.shape_signatures.json tests/test_shape_signatures.py
git commit -m "feat: add shape signature extraction"
```

## Task 3: Implement graph projection and deterministic scoring

**Files:**
- Create: `src/conversation_os/shape_graph.py`
- Create: `context/substrate/modules/kernel.shape.shape_graph.json`
- Modify: `src/conversation_os/models.py`
- Test: `tests/test_shape_signatures.py`

- [ ] **Step 1: Write failing graph and scoring tests**

Cover:

- every entity/state/constraint/absence becomes a node
- every relation becomes an edge
- edge endpoints must reference valid node keys
- deterministic scoring ranks `overproduced_song` above `maze` for a signal dilution case
- no-role-overlap candidates are rejected before later evaluation

- [ ] **Step 2: Run graph tests to verify failure**

Run:

```bash
pytest tests/test_shape_signatures.py -k "graph or scoring" -v
```

Expected:

- failure because graph projection and score helpers do not yet exist

- [ ] **Step 3: Implement graph and score helpers**

Add:

- `signature_to_graph(signature: dict) -> tuple[list[dict], list[dict]]`
- `validate_shape_graph(nodes: list[dict], edges: list[dict]) -> list[str]`
- `role_fit_score(...)`
- `edge_type_overlap(...)`
- `operation_overlap(...)`
- `feedback_fit(...)`
- `anti_match_penalty(...)`
- `deterministic_match_score(...)`
- `load_shape_graph_nodes(root: Path) -> list[dict]`
- `load_shape_graph_edges(root: Path) -> list[dict]`
- `build_shape_graph(root: Path) -> dict`

Rules:

- support constraints, absences, and affordances from v1
- keep scoring deterministic and explainable
- return component scores, not only one scalar
- graph rows are derived from signatures and can be rebuilt
- graph validation warnings should be returned as data, not raised, unless references are impossible to resolve

Manifest:

- add a module manifest with `module_id: kernel.shape.shape_graph`
- set `layer: kernel`
- set owner to graph projection and deterministic structural scoring
- list `shape_signatures`, `models`, and `storage` as dependencies

- [ ] **Step 4: Re-run graph and scoring tests**

Run:

```bash
pytest tests/test_shape_signatures.py -k "graph or scoring" -v
```

Expected:

- PASS
- explicit assertion that `overproduced_song > maze`

- [ ] **Step 5: Commit**

```bash
git add src/conversation_os/shape_graph.py context/substrate/modules/kernel.shape.shape_graph.json tests/test_shape_signatures.py
git commit -m "feat: add shape graph projection and deterministic scoring"
```

## Task 4: Wire the new layer into the runtime pipeline

**Files:**
- Modify: `src/conversation_os/runtime_pipeline.py`
- Modify: `src/conversation_os/cli.py`
- Modify: `src/conversation_os/product_inner_world.py` only if current runtime execution dispatch lives there
- Test: `tests/test_conversation_os.py`

- [ ] **Step 1: Write failing runtime integration tests**

Cover:

- runtime pipeline config includes a `shape_signatures` component
- component order is after `thread_abstractions` and before `conversation_concepts`
- running the rebuild produces the new artifact files

- [ ] **Step 2: Run runtime integration tests to verify failure**

Run:

```bash
pytest tests/test_conversation_os.py -k shape_signatures -v
```

Expected:

- failure because the runtime component is not yet registered

- [ ] **Step 3: Register the new component**

Update:

- default runtime pipeline component list
- runtime execution dispatch
- any status summary helpers that enumerate component artifacts

Only add minimal CLI exposure if already required by the runtime execution path.
If runtime dispatch lives in `product_inner_world.py`, add only the smallest
call to `build_shape_signatures()` and `build_shape_graph()` and leave browser
payloads unchanged.

- [ ] **Step 4: Re-run runtime integration tests**

Run:

```bash
pytest tests/test_conversation_os.py -k shape_signatures -v
```

Expected:

- PASS

- [ ] **Step 5: Commit**

```bash
git add src/conversation_os/runtime_pipeline.py src/conversation_os/cli.py tests/test_conversation_os.py
git commit -m "feat: add shape signatures runtime component"
```

## Task 5: Integrate shape signatures into `conversation_synthesis`

**Files:**
- Modify: `src/conversation_os/conversation_synthesis.py`
- Modify: `src/conversation_os/models.py`
- Modify: `src/conversation_os/shape_graph.py` if a helper must be generalized for synthesis
- Test: `tests/test_shape_signatures.py`
- Test: `tests/test_conversation_os.py`

- [ ] **Step 1: Write failing synthesis tests**

Cover:

- `FormationCandidate` can carry signature refs or derived structural fields
- `match_shapes()` prefers structural compatibility over shallow token overlap
- a structurally valid but lexically different candidate can outrank a lexically similar anti-match

- [ ] **Step 2: Run synthesis tests to verify failure**

Run:

```bash
pytest tests/test_shape_signatures.py -k synthesis -v
```

Expected:

- failure because synthesis still uses mostly lexical scoring

- [ ] **Step 3: Update synthesis matching**

Implement minimal changes so that:

- broad candidate retrieval remains unchanged at first
- `FormationCandidate` can reference one or more signatures
- `match_shapes()` consults structural scores when available
- lexical overlap remains as fallback or tie-break only
- `ShapeMatch.reasons` records whether structural scoring was used
- weak structural matches still flow through existing review behavior

Do not rewrite the whole synthesis module in this slice.

- [ ] **Step 4: Re-run synthesis tests**

Run:

```bash
pytest tests/test_shape_signatures.py -k synthesis -v
```

Expected:

- PASS

- [ ] **Step 5: Commit**

```bash
git add src/conversation_os/conversation_synthesis.py src/conversation_os/models.py tests/test_shape_signatures.py tests/test_conversation_os.py
git commit -m "feat: use shape signatures in synthesis matching"
```

## Task 6: Add shape memory and anti-match updates

**Files:**
- Create: `src/conversation_os/shape_memory.py`
- Create: `context/substrate/modules/kernel.shape.shape_memory.json`
- Modify: `src/conversation_os/review_queue.py`
- Modify: `src/conversation_os/shape_signatures.py`
- Test: `tests/test_shape_signatures.py`

- [ ] **Step 1: Write failing memory tests**

Cover:

- accepted shape reasoning artifact increases validation count
- rejected analogy becomes an anti-match
- wrong-shape feedback lowers confidence or records an alternative interpretation
- missing-constraint feedback persists a reusable constraint hint

- [ ] **Step 2: Run memory tests to verify failure**

Run:

```bash
pytest tests/test_shape_signatures.py -k memory -v
```

Expected:

- failure because memory and feedback update helpers do not yet exist

- [ ] **Step 3: Implement file-backed memory helpers**

Add:

- `load_shape_memory(root: Path) -> list[dict]`
- `record_shape_feedback(...) -> dict`
- `upsert_shape_memory_item(...) -> dict`
- `find_shape_memory_matches(...) -> list[dict]`
- scoped memory update helpers for:
  - `global_seed`
  - `domain_lens`
  - `user`
  - `project`

Rules:

- keep memory updates explicit and reversible
- persist anti-matches as first-class data
- do not silently mutate the original raw signature
- store feedback as an event-like append or explicit memory update payload
- do not require user identity plumbing beyond existing available IDs in this slice

Manifest:

- add a module manifest with `module_id: kernel.shape.shape_memory`
- set `layer: kernel`
- set owner to validated shape memory, anti-matches, and feedback updates
- list `shape_signatures`, `shape_graph`, `models`, and `storage` as dependencies

- [ ] **Step 4: Re-run memory tests**

Run:

```bash
pytest tests/test_shape_signatures.py -k memory -v
```

Expected:

- PASS

- [ ] **Step 5: Commit**

```bash
git add src/conversation_os/shape_memory.py context/substrate/modules/kernel.shape.shape_memory.json src/conversation_os/review_queue.py src/conversation_os/shape_signatures.py tests/test_shape_signatures.py
git commit -m "feat: add shape memory and anti-match updates"
```

## Task 7: Decide whether knowledge-layer reranking is ready

**Files:**
- Modify: `docs/plans/2026-05-24-shape-signature-layer-implementation-plan.md` if deferring
- Modify: `src/conversation_os/knowledge_layer.py` only if synthesis tests show a clear retrieval gap
- Modify: `src/conversation_os/shape_graph.py` only if a reusable scoring helper is already proven
- Test: `tests/test_shape_signatures.py` only if code is changed

- [ ] **Step 1: Review evidence from Tasks 5 and 6**

Check:

- Does `match_shapes()` now have enough structural signal for the first useful product?
- Are candidate pairs failing because retrieval missed the right neighbors?
- Are poor matches happening after retrieval because scoring is weak?
- Are there at least two concrete call sites for a knowledge-layer structural reranker?

- [ ] **Step 2: Choose the path**

If the issue is scoring after retrieval, stop here and defer knowledge-layer
changes.

If the issue is candidate recall, continue with a thin reranking hook.

- [ ] **Step 3: Write failing retrieval tests only if continuing**

Cover:

- broad candidate retrieval still works without signatures
- when signatures are present, reranking prefers structural relevance
- anti-match penalties can downrank misleading neighbors

- [ ] **Step 4: Run retrieval tests to verify failure**

Run:

```bash
pytest tests/test_shape_signatures.py -k retrieval -v
```

Expected:

- failure because retrieval does not yet consume structural signals

- [ ] **Step 5: Add thin reranking only**

Implement:

- keep `build_retrieval_bundle()` broad and cheap
- keep `select_candidate_pairs()` as the broad pair selector
- add optional structural reranking hooks after candidate collection

Do not replace the knowledge layer's existing retrieval architecture.

- [ ] **Step 6: Re-run retrieval tests**

Run:

```bash
pytest tests/test_shape_signatures.py -k retrieval -v
```

Expected:

- PASS

- [ ] **Step 7: Commit**

```bash
git add src/conversation_os/knowledge_layer.py src/conversation_os/shape_graph.py tests/test_shape_signatures.py
git commit -m "feat: add structural reranking hooks for retrieval"
```

## Task 8: Full regression and artifact verification

**Files:**
- Modify only if failures require it
- Test: `tests/test_shape_signatures.py`
- Test: `tests/test_conversation_os.py`

- [ ] **Step 1: Run the focused new suite**

Run:

```bash
pytest tests/test_shape_signatures.py -v
```

Expected:

- PASS

- [ ] **Step 2: Run affected existing suites**

Run:

```bash
pytest tests/test_conversation_os.py -v
```

Expected:

- PASS

- [ ] **Step 3: Run targeted repo readiness checks**

Run:

```bash
python3 tools/conversation_os.py repo-overview refresh
python3 tools/conversation_os.py repo-overview validate
```

Expected:

- overview refresh succeeds
- validation reports no stale or broken tracked surfaces
- module manifest count reflects the new modules
- no missing manifest warnings for `shape_signatures`, `shape_graph`, or `shape_memory`

- [ ] **Step 4: Inspect artifact generation manually**

Verify that the following exist after a test rebuild:

- `product/inner_world_v1/data/shape_reasoning/shape_signatures.jsonl`
- `product/inner_world_v1/data/shape_reasoning/shape_graph_nodes.jsonl`
- `product/inner_world_v1/data/shape_reasoning/shape_graph_edges.jsonl`
- `product/inner_world_v1/data/shape_reasoning/shape_memory.jsonl`

Also verify that generated runtime artifacts are not accidentally committed
unless the repo already tracks equivalent generated fixtures for the tested path.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "test: verify shape signature layer integration"
```

## Risks to watch during implementation

- Do not let `meta_layer` become the owner of full structural records.
- Do not move shape logic into `product_inner_world.py`; keep it kernel-owned.
- Do not replace broad retrieval with expensive structural checks too early.
- Do not silently promote weak matches into durable truth.
- Do not flatten `constraints`, `absences`, and `affordances` into freeform notes.
- Do not let lexical summaries like `transfer_shape` remain the only structural signal once the new layer exists.

## Success criteria

By the end of this plan:

- the repo can derive typed shape signatures from existing source-backed material
- signatures project into validated graph artifacts
- synthesis matching becomes structurally stronger without breaking current surfaces
- review and anti-match memory become first-class parts of the reasoning loop
- the runtime pipeline can rebuild the new layer deterministically

## Recommended execution order

1. Task 1
2. Task 2
3. Task 3
4. Task 4
5. Task 5
6. Task 6
7. Task 7
8. Task 8
