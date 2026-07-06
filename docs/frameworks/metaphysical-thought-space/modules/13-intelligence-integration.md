# Module 13 — Intelligence Integration

How intelligence models combine with code to operationalize MTSF at scale.

## Design principle

> **Models interpret. Code governs. Models render under constraint.**

Intelligence models are probabilistic interpreters over language, image, and latent geometry.  
Code is the deterministic owner of ontology, graph state, dynamics, invariants, and audit trail.

Neither replaces the other. The scalable system is a **compiler pipeline**:

```text
vague_input
  → [model] parse / propose
  → [code] validate / normalize / merge
  → [code] graph + dynamics + inference
  → [model] render / paraphrase / question (optional)
  → [code] verify / snapshot / feedback
  → artifact + updated field
```

Latent space and transformers are **backends** for specific stages — not the metaphysical layer itself.

---

## Intelligence roles in MTSF

| Role | Best tool | MTSF stage | Why |
|------|-----------|------------|-----|
| **Perception** | LLM, VLM | ingest | Turn messy utterance/media into candidate structure |
| **Alignment** | Embeddings | quality regions, partial shapes | Fuzzy match without collapsing labels |
| **Routing** | Small classifier or rules+embeddings | query planning | Pick retrieval path (vector / graph / temporal) |
| **Extraction** | LLM + structured output | entity/quality/relation candidates | High recall on unstructured material |
| **Naming** | LLM | candidate shapes | Propose `possible_names`; never auto-commit |
| **Questioning** | LLM | discovery | Shape-revealing questions when confidence low |
| **Rendering** | LLM, diffusion, audio models | actualization | `ArtifactSpec` → concrete medium |
| **Steering** | LoRA / prompt / RLHF | actualization | Bend style without changing graph truth |
| **Governance** | **Code only** | all | Schema, invariants, promotion rules, epistemics |
| **Dynamics** | **Code only** | thought field | Activation, intensity drift, snapshots |
| **Inference** | **Code primary**, embeddings assist | association, motifs | Weighted graph math; vectors for similarity |
| **Audit** | **Code only** | all | Evidence binding, provenance, replay |

---

## When to use models vs code

### Use intelligence models when

- Input is **unstructured** (natural language, image, audio, latent vector)
- Task is **interpretive** (what mood is here? what connects these references?)
- Task is **generative under soft constraints** (write a paragraph from this shape)
- You need **recall** over infinite personal phrasing
- You need **cross-domain translation** at the surface-text level
- You accept **confidence scores**, not guarantees

### Use code when

- Structure must be **valid** (relation level, entity identity, shape kind)
- Behavior must be **replayable** (activation snapshots, temporal order)
- Rules must be **auditable** (promotion, contradiction, epistemic guards)
- Math must be **explicit** (association weights, salience, role composition)
- State must **persist** across sessions without model drift
- You need **deterministic** outcomes for the same graph state

### Never delegate to models alone

- Ontology truth (what relation types exist)
- Shape stabilization (candidate → stored)
- Entity promotion (shape → entity)
- Contradiction resolution policy
- Claims about metaphysical vs latent vs actual space
- Final authority on what the user "meant"

---

## The contract: Thought Graph IR

All model outputs must pass through a single intermediate representation (IR) owned by code.

```text
ThoughtGraphIR {
  entities: Entity[]
  quality_regions: QualityRegion[]
  relations: Relation[]
  shapes: Shape[]
  activations: ActivationSnapshot[]
  candidates: CandidatePattern[]   // hypothesis only
  artifact_specs: ArtifactSpec[]   // constraint bundles, not final media
  provenance: ProvenanceRecord[]   // source span, model_id, confidence
}
```

**Rule:** Models write *proposals*. Code writes *canonical state*.

---

## Layered architecture (scalable)

```text
┌─────────────────────────────────────────────────────────┐
│ L5  Surfaces — chat, studio, APIs, batch jobs           │
├─────────────────────────────────────────────────────────┤
│ L4  Orchestrator — route query, plan pipeline stage     │
├─────────────────────────────────────────────────────────┤
│ L3  Intelligence adapters — LLM, embed, VLM, latent     │
│     (stateless, swappable, versioned)                   │
├─────────────────────────────────────────────────────────┤
│ L2  Symbolic kernel — graph, dynamics, algebra, motifs  │
│     (deterministic, event-sourced, auditable)           │
├─────────────────────────────────────────────────────────┤
│ L1  Ontology registry — schemas, relations, roles       │
│     (versioned JSON + validators)                       │
└─────────────────────────────────────────────────────────┘
```

### L1 — Ontology registry (code)

- MTSF schemas, relation primitives, governing roles
- Versioned; extraction prompts reference ontology version
- **Ontology before extraction** (retrofitting is expensive)

### L2 — Symbolic kernel (code)

- Graph store: entities, qualities, relations, shapes
- Event log: activation snapshots, promotions, merges
- Engines:
  - `reduce_identity(quality_graph) -> dominant_shape`
  - `association_strength(A, B) -> score`
  - `detect_motifs(snapshots) -> CandidatePattern[]`
  - `actualize_compile(shape, medium) -> ArtifactSpec`
- Invariant enforcer (see below)

### L3 — Intelligence adapters (models)

Each adapter is a thin, replaceable interface:

```text
ExtractAdapter      : raw -> ProposalBundle
EmbedAdapter        : text -> vector
AlignAdapter        : vector, regions -> nearest QualityRegion[]
RenderAdapter       : ArtifactSpec -> bytes | text
QuestionAdapter     : low_confidence_field -> clarifying_question
LatentAdapter       : vector ops, steer, decode (optional backend)
```

Adapters are **stateless**. All memory lives in L2.

### L4 — Orchestrator (code + light routing model)

Query router selects pipeline:

| Query type | Path |
|------------|------|
| "What is forming?" | snapshots → motif detectors → candidates |
| "Find sacred decay" | embed partial shape → graph match → results |
| "Make this a film shot" | shape → compile spec → render adapter |
| "Why does this feel X?" | quality graph → relation trace → explain (model narrates **over** code trace) |

Routing can be rules-first; add a small classifier only when rules fail.

### L5 — Surfaces

UI/API never calls models directly. Always: `surface -> orchestrator -> kernel`.

---

## Pipeline stages (model/code split)

### 1. Ingest

| Step | Owner |
|------|-------|
| Receive raw material | code |
| Propose entities, qualities, relations | **model** (structured extraction) |
| Map labels → quality regions | **embed** + code merge |
| Validate against schema | **code** |
| Evidence-bind spans to source | **code** |
| Merge into graph | **code** |

### 2. Activate (thought field dynamics)

| Step | Owner |
|------|-------|
| Update intensities, emergence order | **code** |
| Nonlinear activation side effects | **code** (optionally model suggests links → code confirms) |
| Write activation snapshot | **code** |

### 3. Discover

| Step | Owner |
|------|-------|
| Recurrence / cluster / tension detection | **code** (+ embed for fuzzy quality match) |
| Name candidate pattern | **model** (proposes labels) |
| Register as `CandidatePattern` | **code** (hypothesis, confidence, evidence) |
| Ask clarifying question if low confidence | **model** (optional) |

### 4. Stabilize

| Step | Owner |
|------|-------|
| Promote candidate → stored shape | **code** (threshold + evidence count) |
| Promote shape → entity | **code** (recurrence + richness rules) |
| User confirm / reject | code + surface |

### 5. Actualize

| Step | Owner |
|------|-------|
| `shape -> ArtifactSpec` | **code** (deterministic compile) |
| `ArtifactSpec -> draft artifact` | **model** (render) |
| Verify spec compliance | **code** |
| Feedback → graph update | **code** (+ model may propose relation edits → validated) |

---

## Validation sandwich (required)

Every model touch point uses the same gate:

```text
1. Schema validation     — types, enums, required fields
2. Ontology validation   — relation level, primitive allowed, role legal
3. Evidence validation   — extracted span exists in source (where applicable)
4. Semantic validation   — code rules (e.g. intensity 0..1, no orphan relations)
5. Epistemic validation  — block overclaim language in stored facts
6. Repair loop           — 1–2 retries with validator errors fed back to model
7. Quarantine            — low confidence → review queue, not canonical graph
```

Research consensus: **LLM extracts candidates; validators own the trust boundary.**

---

## Hybrid retrieval (three layers)

Aligns with MTSF's entity + relation + temporal field:

| Layer | Technology | Use |
|-------|------------|-----|
| **Vector** | Embeddings | Partial shape search, quality region nearness, fuzzy recall |
| **Graph** | Symbolic store | Multi-hop relations, motif match, cross-domain archetypes |
| **Episodic** | Event snapshots | "What was active when?", drift, recurrence over time |

**Pattern:** embed query → seed nodes → graph traverse → rank by association formula (code).

Do not use vector-only RAG as the memory system; MTSF memory is **configured graphs over time**.

---

## Model placement for latent space / transformers

| Capability | Placement |
|------------|-----------|
| Contextualization | Extract + align stages (quality meaning shifts by context) |
| Embedding geometry | Quality region alignment, partial shape search |
| Composition | Render stage under `ArtifactSpec` constraints |
| Steering | Render adapter config (LoRA/prompt), not graph mutation |
| Decode / actualize | Render adapter only |
| Training / feedback | Offline or async — update profiles, not live ontology |

Transformers never **are** the thought-space. They **service** specific adapters.

---

## Invariants (code-enforced)

1. `CandidatePattern` cannot write directly to canonical shape without promotion
2. Custom poetic relations stored with `custom_phrase` + mapped `primitive`
3. Model confidence ≠ truth; store both, display both differently
4. Same graph state + same compile → same `ArtifactSpec` (deterministic)
5. Latent operations tagged `space: latent` — never `space: metaphysical`
6. Explainability = export code trace (relations, roles, weights); model narrates optionally

---

## Scalability tactics

| Concern | Approach |
|---------|----------|
| Cost | Route cheap models for extract; expensive for render only |
| Latency | Async extract jobs; sync only for query/compile |
| Drift | Version ontology + prompts + adapters together |
| Multi-tenant | Scoped graphs per user/world; shared ontology registry |
| Scale graph | Event sourcing; snapshot aggregates; index embeddings separately |
| Human review | Quarantine queue for low-confidence extractions |
| Testing | Golden graphs + property tests on kernel; model evals separate |

---

## Suggested rollout

### Phase A — Symbolic kernel only
Graph IR, validators, snapshots, association math, motif detectors (rule-based).  
No LLM required to prove architecture.

### Phase B — Extract adapter
Structured extraction → validation sandwich → merge.  
Embeddings for quality region alignment.

### Phase C — Discovery + questions
Candidate naming, clarifying questions, stabilization UI.

### Phase D — Actualization compiler + render adapters
`ArtifactSpec` per medium; text first, then image/audio.

### Phase E — Latent backend (optional)
Steering/decoding as replaceable render backend — not core truth.

---

## Anti-patterns

| Anti-pattern | Why it fails |
|--------------|--------------|
| LLM as database of meaning | Drift, hallucination, no audit |
| Vector RAG as thought-space | Loses relation configuration |
| End-to-end generate from prompt | Skips shape; no discovery replay |
| Schema after extraction | Entity type explosion, costly normalize |
| Model decides promotion | Violates "shapes are hypotheses" |
| One model does everything | No separation of interpret / govern / render |

---

## Final formulation

> **MTSF scales when intelligence models are adapters around a deterministic thought-graph compiler — not when the framework is implemented as prompts.**

Models provide **perception, alignment, naming, and rendering**.  
Code provides **ontology, state, dynamics, inference, validation, and memory**.

The scalable system is the **Thought Graph IR** plus a **validation sandwich** plus **swappable adapters** — with transformers and latent space used only where geometry and context actually help.
