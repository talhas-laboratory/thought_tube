# Primitive Catalogue and Framework Reference

**Workspace:** `unified-framework-synthesis-4f48`  
**Status:** Canonical reference — pre-synthesis inventory (Jul 2026)  
**Date:** 2026-07-11  
**Purpose:** One deep document describing the full primitive catalogue (~120–140 named pieces), each source framework (MTSF, SDS, ThoughtShape), chat-layer additions, overlap mapping, and how they compose under the unified stack.

**Related:**

- [framework-primitive-decomposition.md](./framework-primitive-decomposition.md) — source inventory (abbreviated tables)
- [sources/unified-framework-synthesis.md](../sources/unified-framework-synthesis.md) — canonical pre-build synthesis
- [sources/three-framework-comparative-evaluation.md](../sources/three-framework-comparative-evaluation.md) — side-by-side comparison
- [epistemology-and-overlap.md](./epistemology-and-overlap.md) — epistemic alignment and divergence

---

## Table of contents

1. [Executive summary](#1-executive-summary)
2. [The unified stack](#2-the-unified-stack)
3. [Framework I — MTSF](#3-framework-i--mtsf-metaphysical-thought-space-framework)
4. [Framework II — SDS](#4-framework-ii--sds-system-dynamic-signature)
5. [Framework III — ThoughtShape](#5-framework-iii--thoughtshape)
6. [Chat-layer additions (Jul 2026 design thread)](#6-chat-layer-additions-jul-2026-design-thread)
7. [The unified kernel object](#7-the-unified-kernel-object-thoughtobject)
8. [Full primitive catalogue (A–K)](#8-full-primitive-catalogue-ak)
9. [Overlap map — same thing, different names](#9-overlap-map--same-thing-different-names)
10. [Framework ownership matrix](#10-framework-ownership-matrix)
11. [Naming collisions to avoid](#11-naming-collisions-to-avoid)
12. [Philosophical commitments](#12-philosophical-commitments)
13. [Implementation posture in this repo](#13-implementation-posture-in-this-repo)
14. [Open synthesis work](#14-open-synthesis-work)
15. [Source index](#15-source-index)

---

## 1. Executive summary

Thought Tube / Inner World is **not three products and not three ontologies**. It is one meaning operating system with three framework perspectives and optional overlays:

| Framework | Role | Core question | Status |
|-----------|------|---------------|--------|
| **MTSF** | Substrate — persistence, discovery, actualization | What exists in mind-space, and how does it become artifact? | **Operational** — kernel in repo, gap evals, graph/assertion store |
| **ThoughtShape** | Grammar — phenomenological meaning configuration | What is the multidimensional relational configuration of meaning? | **Design** — v1.0 spec, no dedicated schema in repo |
| **SDS** | Overlay — motion, analogy, intervention | What transformation is happening, and what cross-domain analogies hold? | **Design** — v1.0 report, partial types in `models.py` |

The primitive catalogue inventories **~120–140 named pieces** before deduplication:

| Source | Unique pieces | Shared / mappable |
|--------|---------------|-------------------|
| MTSF | ~25 | ~45 |
| SDS | ~20 | ~45 |
| ThoughtShape | ~18 | ~45 |
| Chat additions | ~10 | — |

**Locked discipline:** synthesize into one ontology first; extend MTSF store; do not build parallel storage systems or product surfaces before schema lock.

---

## 2. The unified stack

```text
NETWORK     Community pipeline (mimic → signature → cluster → connect)
SURFACES    Thought Trace + Inner Space Curator
GRAMMAR     ThoughtShape (Dimension × Station × Facet = StateClaim)
OVERLAY     SDS on demand (loops, analogies, intervention, non-movement)
SUBSTRATE   MTSF (events, assertions, graph, shapes, discovery, provenance)
```

### Core formulas

```text
Station × Dimension × Facet = StateClaim
ThoughtShape (grammar view) = relations between StateClaims across dimensions
Shape (unified primitive)     = relation topology across StateClaims
Stencil                       = abstract pattern of a shape (cross-domain match key)
```

### Compressed ontology pipeline

```text
Field → Entity → Dimension → Frame → Station → Facet/Subsystem
     → StateClaim → Relation → Event → Expression → Update
```

### Operational runtime pipeline

```text
Capture → Hold → Differentiate → Shape → Locate → Compare
       → Transform → Express → Evaluate → Update
```

### Capture loop (Thought Trace)

```text
Drop → Hold → Trace → Mirror → Prompt → Repeat
```

### Three views on one persisted object

```text
                    ┌─────────────────────────────┐
                    │   Unified ThoughtObject      │
                    │   (MTSF-backed store)        │
                    └──────────────┬──────────────┘
                                   │
         ┌─────────────────────────┼─────────────────────────┐
         │                         │                         │
  ThoughtShape view           MTSF view                SDS view (optional)
  dimensions, facets,         entities, shapes,         loops, archetypes,
  lenses, tensions            stencils, discovery       analogies, intervention
```

---

## 3. Framework I — MTSF (Metaphysical Thought-Space Framework)

### 3.1 Identity

| Field | Value |
|-------|-------|
| **Full name** | Metaphysical Thought-Space Framework |
| **Core unit** | Shape / stencil on entities + qualities + relations |
| **Primary question** | What exists in mind-space, and how does it become artifact? |
| **Status** | Operational — kernel implemented; 13/13 gap-closure evals referenced in comparative docs |
| **Canonical tree** | `docs/frameworks/metaphysical-thought-space/` (large; may be maintained outside this workspace snapshot) |

### 3.2 What MTSF optimizes for

- **Durability** — cross-session memory
- **Discovery** — candidate shapes without pre-known templates
- **Actualization** — constraint-binding to produce artifacts
- **Provenance** — evidence-backed assertions; quarantined analogical matches
- **Silence** — unresolved contradiction is valid output

### 3.3 Three spaces

| Space | Role | Critical invariant |
|-------|------|-------------------|
| **Metaphysical** | Pre-formed possibility | Not the same as embedding space |
| **Latent** | Operational bridge (embeddings, transformers) | **Latent ≠ metaphysical** |
| **Actual** | Artifacts and externalized outputs | Where actualization lands |

### 3.4 MTSF pipeline

```text
Field → Entity → Quality → Relation → Shape → Stencil → Artifact
```

Graph layers (0–4):

| Layer | Contents |
|-------|----------|
| 0 | Events |
| 1 | Session graph |
| 2 | Content graph |
| 3 | Global graph |
| 4 | Meta graph |

Processing pipeline:

```text
ingest → extraction → validation → projection → progressive graph
      → activation → discovery → actualization
```

### 3.5 MTSF ontological primitives

| Primitive | Description |
|-----------|-------------|
| **ThoughtField** | Pre-material activation zone with temporal trace |
| **IdeaEntity** | Identity + qualities + relations + intensity + temporal_state |
| **SubEntity** | Typed recursive nested carrier |
| **QualityRegion** | Ten quality types as navigable regions |
| **QualityRole** | Governing categorical operator on qualities |
| **Assertion** | Evidence-backed qualified claim in assertion store |
| **EvidenceSpan** | Text span backing an assertion |
| **Contradiction** | Unresolved pressure (may remain) |

### 3.6 MTSF structural composites

| Composite | Description |
|-----------|-------------|
| **Shape** | Selected qualities + relation configuration + intensity + context + time |
| **CandidateShape** | Provisional shape from discovery (no pre-known template) |
| **Stencil** | Abstract pattern projection of full shape |
| **ShapeInstance** | Live binding of shape to entity/context |
| **ProblemShape** | Problem signal structured for analogical match |
| **ActivationSnapshot** | Point-in-time activation state |
| **Subgraph** | Extracted graph fragment (layers 0–4) |
| **Artifact** | Externalized actualization output |

### 3.7 MTSF relations

22 relation primitives across **four levels**: entity, quality, artifact, meta.

Relation families: structural, causal, associative, hierarchical, temporal, cross-register.

Representative primitives: `contains`, `part_of`, `causes`, `enables`, `contradicts`, `analogous_to`, `activates`, `precedes`, `co_occurs`, `bridges_register`, etc.

### 3.8 MTSF operations

`capture`, `populate`, `extract`, `discover`, `project`, `activate`, `actualize`, `promote`, `expand`, `follow`, `reduce_identity`, `merge_stencil`

### 3.9 MTSF invariants (13)

1. Latent ≠ metaphysical
2. Entities infinite; relation grammars partially standardizable
3. Qualities are regions; words are pointers
4. Shapes provisional until stabilized
5. One entity, many co-active shapes
6. Relations form objects
7. Discovery without pre-known template
8. Generation = constraint-binding
9. Stencil ≠ full shape
10. Meta graph ≠ content graph
11. Cross-domain via shape index, not entity mesh
12. Silence is valid
13. Contradiction may remain

### 3.10 MTSF eval suite (G01–G13)

Gap-closure evals referenced across workspace docs:

| Eval area | Examples |
|-----------|----------|
| Embeddings / adjacency | Semantic neighborhood without flattening ontology |
| Cross-register bridge | G03 — bridges between registers |
| Discovery | Cluster shapes, topology candidates, fuzzy stencil merge |
| Extraction | Live extraction, inferred shapes |
| Utility | Utility bar, downstream hooks |
| Cross-session | Cross-session discovery |

### 3.11 MTSF epistemic bet

| Question | MTSF answer |
|----------|-------------|
| Primary unit of truth | Shape / stencil |
| Latent space | Bridge only — not metaphysically real |
| Match validation | Stencil + utility eval |
| Observer role | Secondary (activation context) |
| Main failure mode | Over-structure |

### 3.12 MTSF strengths and weaknesses

**Strengths:** running kernel; assertion store; content/global graph; discovery without template; session-to-session memory.

**Weaknesses:** flat entity/quality model relative to ThoughtShape; thin lens catalog; causal dynamics and intervention secondary; no faceted multidimensionality as first-class.

### 3.13 Example — brand recognition (MTSF view)

```text
Entity: brand (hub across sessions)
Qualities: recognition (high), meaning (low), stability (variable)
Shape: surface-familiarity-without-semantic-depth configuration
Stencil: surface-without-depth (cross-session match key)
Persists to: assertion store, content graph, global graph
```

---

## 4. Framework II — SDS (System-Dynamic Signature)

### 4.1 Identity

| Field | Value |
|-------|-------|
| **Full name** | System-Dynamic Signature Framework |
| **Core unit** | Movement signature / system in motion |
| **Primary question** | What transformation is happening, and what cross-domain analogies hold? |
| **Status** | Design v1.0 — report in `docs/frameworks/system-dynamic-signature/SDS-v1.0-report.md`; `SystemDynamicSignature` type exists in `src/conversation_os/models.py` |
| **Version** | 1.0 (2026-07-08) |

### 4.2 What SDS optimizes for

- **Transformation** — what is changing, not only what exists
- **Cross-domain transfer** — structural alignment, not semantic similarity
- **Anti-matches** — explicit rejection of false analogies
- **Observer lens** — extraction is constitutively framed
- **Constraints and absences** — blockages as first-class (**non-movement problem**)
- **User-validated memory** — living archetype library

### 4.3 SDS pipeline

```text
Field → Entities+Roles → States → Causal Relations → Feedback Loops
     → Movement Archetype → Analogies → Transfer Ledger → Intervention
```

### 4.4 Four architecture tiers

| Tier | Function |
|------|----------|
| 1 | LLM extraction → typed graph proposal |
| 2 | Analogy generation from abstracted signature |
| 3 | Hybrid 5-layer evaluation |
| 4 | Living library (user-validated archetypes) |

### 4.5 SDS ontological primitives

| Primitive | Description |
|-----------|-------------|
| **Role** | Functional position in system (not identity) |
| **State** | Typed node value with evidence |
| **Constraint** | Hard limit on transition |
| **Signal** | Observable system output |
| **Receiver** | Target of signal / effect |
| **Bottleneck** | Rate-limiting node |
| **Observer** | Constitutive extraction stance |
| **Goal** | Explicit system objective |
| **Missing information** | Flagged absence in extraction |

### 4.6 SDS structural composites

| Composite | Description |
|-----------|-------------|
| **System-Dynamic Signature** | Full typed graph: entities, states, relations, loops |
| **FeedbackLoop** | Circular causal chain |
| **MovementSignature** | Extracted transformation pattern |
| **MovementArchetype** | Library-stored abstract movement |
| **TransferLedger** | Record of cross-domain transfer attempts |
| **AntiMatch** | Explicit rejected analogy |
| **InterventionPattern** | Actionable intervention from source domain |

### 4.7 SDS graph typing

**Node types:** `entity`, `state`, `constraint`, `resource`, `observer`, `goal`, `signal`, `receiver`, `bottleneck`

**Edge types (10):**

`causes`, `amplifies`, `inhibits`, `depends_on`, `transforms_into`, `competes_with`, `enables`, `constrains`, `delays`, `feeds_back_into`

### 4.8 SDS movement primitives (18)

`accumulate`, `decompose`, `recombine`, `translate`, `constrain`, `release`, `amplify`, `dampen`, `delay`, `invert`, `filter`, `stabilize`, `destabilize`, `differentiate`, `integrate`, `externalize`, `internalize`

Composite patterns compose these (e.g. signal dilution through accumulation).

### 4.9 SDS 5-layer evaluator

1. Structural alignment
2. Causal coherence
3. Boundary fit
4. Observer lens consistency
5. Transfer ledger / anti-match check

### 4.10 SDS operations

`extract_signature`, `match_archetype`, `generate_analogy`, `evaluate_transfer`, `record_anti_match`, `propose_intervention`, `update_library`

### 4.11 SDS invariants

- Observer lens is **constitutive**
- **Non-movement is first-class** — what is blocked matters as much as what moves
- Anti-matches required for safe transfer
- Structural alignment beats semantic similarity

### 4.12 SDS epistemic bet

| Question | SDS answer |
|----------|-------------|
| Primary unit of truth | Movement signature |
| Latent space | Metaphor only |
| Match validation | 5-layer evaluator + transfer ledger |
| Observer role | Constitutive |
| Main failure mode | False analogy |

### 4.13 Non-movement problem (unique SDS contribution)

> What is blocked, absent, or prevented is as important as what moves.

| Framework | Absence handling |
|-----------|------------------|
| MTSF | Contradiction may remain; silence valid — no dedicated absence primitive |
| ThoughtShape | Tension, Hold — phenomenological pressure |
| SDS | Constraint, bottleneck, anti-match, missing info, inhibits edge |

### 4.14 Example — brand recognition (SDS view)

```text
Loop: awareness → logo recall ↑ → meaning unchanged → trust gap widens
Archetype: signal_without_semantics
Non-movement: recognition → comprehension transition blocked (no semantic bridge)
Anti-match: "maze" rejected (implies hidden path; here there may be none)
Intervention: clarify lead signal before amplifying distribution
```

### 4.15 SDS strengths and weaknesses

**Strengths:** best false-analogy guard; intervention design; cybernetic rigor; causal motion.

**Weaknesses:** no persistent mind substrate; no faceted multidimensional entity model; not fully implemented as runtime overlay.

---

## 5. Framework III — ThoughtShape

### 5.1 Identity

| Field | Value |
|-------|-------|
| **Full name** | ThoughtShape Framework for Thought Tube |
| **Core unit** | Multidimensional meaning-shape |
| **Primary question** | What is the relational configuration of meaning across dimensions, and how do lenses access it? |
| **Status** | Design v1.0 — `docs/frameworks/thought-shape/ThoughtShape-framework-v1.md` |
| **Philosophical root** | Maqām → Ḥāl → Tajallī (Station → StateClaim → Event) |

### 5.2 What ThoughtShape optimizes for

- **Multidimensionality** — same entity, many valid layers
- **Faceted precision** — logo recognition ≠ meaning recognition
- **Progressive resolution** — depth only when earned
- **Lens routing** — structured access modes, not free-form prompts
- **Tension and valence** — felt charge preserved
- **Provenance and confidence** — anti-hallucination by design

### 5.3 ThoughtShape pipeline

```text
Field → Entity → Dimension → Frame → Station → Facet/Subsystem
     → StateClaim → Relation → Event → Expression → Update
```

### 5.4 Core formula

```text
Station × Dimension × Facet = StateClaim
Thought-shape = relations between StateClaims across dimensions
```

### 5.5 Full ontology expansion

```text
ThoughtShape = Field + Entity + Dimension + Frame + Station + Facet/Subsystem
             + StateClaim + Relation + Event + Expression + Provenance + Confidence
             + Tension + Valence + Salience + TemporalContour + Telos + Modality
```

### 5.6 ThoughtShape ontological primitives

| Primitive | Description |
|-----------|-------------|
| **Dimension** | First-class meaning layer (psychological, brand, financial, narrative…) |
| **Station** | Possibility-space where meaning varies (recognition, trust, clarity…) |
| **Facet** | Aspect within station × dimension |
| **StateClaim** | state + weight + salience + valence + confidence + evidence |
| **CrossDimensionalRelation** | Relation across dimensions — core shape mechanism |
| **TemporalContour** | How meaning evolves over time |
| **ExpressionSurface** | Output routing target per lens |
| **Valence** | Affective charge |
| **Salience** | Pre-formed pressure / attention weight |
| **Telos** | Directional purpose |
| **Modality** | Mode of being (possible, actual, counterfactual…) |

### 5.7 ThoughtShape structural composites

| Composite | Description |
|-----------|-------------|
| **ThoughtShape** | Full multidimensional meaning configuration |
| **Projection** | Station × Dimension → localized meaning |
| **LensView** | Same shape accessed through lens catalog |
| **ExpressionBundle** | Lens-routed output package |

### 5.8 ThoughtShape relations and dynamics

- Directional influence between StateClaims
- Cross-dimensional relations (not necessarily causal)
- **Tension** as unresolved relation pressure

### 5.9 ThoughtShape operations

`Capture` → `Hold` → `Differentiate` → `Shape` → `Locate` → `Compare` → `Transform` → `Express` → `Evaluate` → `Update`

Note: **Shape** here is both a **verb** (relate facets) and maps to the unified **Shape** primitive (topology).

### 5.10 Lens catalog (7 product access modes)

| Lens | Activates | Routes to |
|------|-----------|-----------|
| Founder | psychology, origin, conviction, wound | manifesto, pitch, narrative |
| Product | user behavior, value clarity, onboarding | feature, UX, requirement |
| Risk | fragility, assumptions, failure paths | mitigation, tests |
| Financial | CAC, conversion, retention | unit-economics |
| Story | character, conflict, arc | scene, narrative |
| Visual | symbol, atmosphere, composition | moodboard, metaphor |
| Brand | recognition facets, trust, symbolism | positioning, messaging |

**Invariant:** lens is access mode, not a free-form prompt. All lenses operate on the **same** underlying shape.

### 5.11 Progressive depth (levels 1–6)

| Level | State |
|-------|-------|
| 1 | Raw field — "something feels off" |
| 2 | Basic shape — Entity → Station → unstable |
| 3 | Dimensional — dimension + station |
| 4 | Faceted — multiple StateClaims per station |
| 5 | Subsystem — expanded facet internals |
| 6 | Cross-dimensional — relations across dimensions |

### 5.12 ThoughtShape design principles

1. Thought is not a sentence
2. Thought is not flat
3. Stations project across dimensions
4. Stations split into facets
5. Facets become subsystems progressively
6. Relations create shape
7. Cross-dimensional relations are essential
8. Provenance is mandatory
9. Lenses are access modes, not prompts
10. Progressive resolution — **Hold before Differentiate**

### 5.13 ThoughtShape epistemic bet

| Question | ThoughtShape answer |
|----------|---------------------|
| Primary unit of truth | StateClaim topology |
| Match validation | Lens fidelity to shape |
| Observer role | Constitutive (frame + lens) |
| Main failure mode | Flatten dimensions |

### 5.14 Example — brand recognition (ThoughtShape view)

```text
Entity: Brand
Dimension: Brand
Station: Recognition
Facets: logo=high, meaning=low, category=confused
Tension: visual familiarity vs semantic instability
Cross-dimensional chain: meaning → positioning → conversion → founder confidence
```

### 5.15 ThoughtShape strengths and weaknesses

**Strengths:** richest product-facing grammar; lens routing; facet precision; Hold semantics.

**Weaknesses:** no implementation; no formal discovery pipeline; no actualization bridge to artifacts without MTSF.

---

## 6. Chat-layer additions (Jul 2026 design thread)

Primitives and composites introduced in the unified synthesis design thread — not part of the three original framework specs, but locked into the product architecture.

### 6.1 Capture and trace primitives

| Primitive | Description |
|-----------|-------------|
| **ReasoningStep** | Atomic capture unit (not session, not formation) |
| **ReasoningMove** | ground, triangulate, bridge, formalize, invert, stall, cannot-bridge… |
| **ReasoningTrace** | Ordered chain of ReasoningSteps |
| **ReasoningSignature** | Person-level recurring reasoning topology |
| **HoldRecord** | Capture-time hold state persistence |

**ReasoningStep fields (design):**

| Field | Purpose |
|-------|---------|
| `raw_text` | Exactly what user said |
| `hold_state` | pre-clear / partial / crystallizing / settled |
| `reasoning_move` | move vocabulary |
| `prompted_by` | link to prior step(s) |
| `move_type` | extends, revises, contrasts, grounds, bridges |
| `provenance` | user / inferred / confirmed |

### 6.2 Curator primitives

| Primitive | Description |
|-----------|-------------|
| **PlacedFragment** | Content placed in inner topology |
| **CuratorSpace** | Inner topology of placed fragments |

**Curator verbs:** place, tend, revisit, release, compose

### 6.3 Community primitives

| Primitive | Description |
|-----------|-------------|
| **Cluster** | Reasoning-topology group (not demographic) |
| **ClusterLane** | Product variant per cluster |
| **MimicProfile** | Bot interrogation style per person |
| **CommunityFlywheel** | social → mimic → signature → cluster → connect |

### 6.4 Product surfaces

| Surface | Question | Unit | Ritual character |
|---------|----------|------|------------------|
| **Thought Trace** | How did I get here? | ReasoningStep | Forensic instrument |
| **Inner Space Curator** | What world am I building by what I attend to? | PlacedFragment | Mirror / alchemical practice |
| **Community pipeline** | Who thinks like me? | ReasoningSignature → Cluster | Network flywheel |

### 6.5 Alchemical mapping

| Alchemical move | Runtime operation | Surface |
|-----------------|-------------------|---------|
| Intake | Capture / Drop | Trace, Curator |
| Nigredo | Hold | Trace |
| Separatio | Differentiate | Trace |
| Coniunctio | Shape / Relate | Trace |
| Mortificatio | Release / prune | Curator |
| Sublimatio | Stencil / archetype | Kernel + SDS overlay |
| Coagulatio | Formation / canon | Kernel |
| Circulatio | Revisit / feed loop | Curator |

---

## 7. The unified kernel object (ThoughtObject)

### 7.1 Definition

**ThoughtObject** is the canonical persisted record in the MTSF-backed store. It is the envelope for one unit of meaning work — an idea, brand, product thesis, self-formation, research program, etc.

**Status:** schema **not yet locked** (P0 gap). No `ThoughtObject` type in code today.

### 7.2 ThoughtObject vs Shape vs ThoughtShape

| Term | Level | Meaning |
|------|-------|---------|
| **ThoughtObject** | Container | Whole persisted kernel record (one store, three projections) |
| **Shape** | Structure inside object | Relation topology across StateClaims |
| **ThoughtShape** | Grammar / view | Full multidimensional meaning configuration |
| **Formation** | Outcome | Stabilized whole emerging from multiple steps / state-claims |
| **Stencil** | Pattern | Abstracted shape for cross-domain matching |

```text
ThoughtObject
├── Entity / carrier
├── StateClaims
├── Relations
├── Shape (topology)
│   └── Stencil (abstract pattern)
├── Formation (when crystallized)
├── ReasoningSteps + trace
├── ReasoningSignature (person-level, may span objects)
└── SDS overlay (optional): loops, constraints, archetypes, interventions
```

### 7.3 Unified primitive definitions (canonical names)

| Primitive | Definition |
|-----------|------------|
| **Field** | Pre-clear possibility; meaningful but not yet resolved |
| **Entity** | Carrier of meaning (person, brand, idea, product, self) |
| **Dimension** | Layer of interpretation |
| **Frame** | Interpretive stance / lens active now |
| **Station** | Possibility-space where a kind of meaning can vary |
| **Facet** | Specific aspect within station × dimension |
| **Subsystem** | Facet expanded when reasoning requires depth |
| **StateClaim** | Qualified condition with evidence, confidence, weight, salience, valence |
| **Relation** | Directional influence within or across dimensions |
| **Event** | State change, disclosure, transformation (Tajallī) |
| **Tension** | Unresolved pressure inside the shape |
| **Expression** | External surface (sentence, scene, spec, ritual, UI…) |
| **Provenance** | Source of structural knowledge |
| **Formation** | Stabilized whole from multiple steps / state-claims |
| **Shape** | Relation topology across state-claims |
| **Stencil** | Abstract pattern of shape (cross-domain match key) |
| **ReasoningStep** | Atomic capture unit with move type and trace links |
| **ReasoningSignature** | Recurring move sequence for a person |
| **MovementSignature** | SDS overlay: system in motion, loops, archetype |

### 7.4 Unified invariants

1. Save before interpret — T0 append on every drop
2. Hold is valid — ambiguity is not failed extraction
3. Progressive depth — facet → subsystem only when earned
4. Provenance everywhere
5. Silence / contradiction may remain
6. Lens is access mode, not free-form prompt
7. Reasoning trace is editable
8. One ontology — no parallel entity registries

### 7.5 Implementation layer stack (T0–T4)

```text
T0  events.jsonl              — every drop, immediately
T0+ hold + reasoning_step     — step graph, move types
T1  assertions / state_claims  — evidence-backed claims
T1+ reasoning_signature       — per-user move profile
T2  content graph handles      — thin, expandable
T3  shapes / stencils          — when stable enough
T4  cluster assignment         — community layer
SDS overlay (optional)         — motion / analogy on request
```

---

## 8. Full primitive catalogue (A–K)

The catalogue organizes all ~120–140 named pieces into eleven functional categories. Items marked **(shared)** appear under multiple framework names — see [§9](#9-overlap-map--same-thing-different-names).

### A. Ontological primitives — what exists

#### A.1 Shared ontological map (~45 concepts)

| Universal concept | MTSF | SDS | ThoughtShape |
|-------------------|------|-----|--------------|
| Pre-clear zone | ThoughtField | Field / possibility cloud | Field |
| Carrier | IdeaEntity | Entity | Entity |
| Nested carrier | SubEntity | (recursive VSM) | Subsystem |
| Qualified region | QualityRegion | State | StateClaim |
| Evidence | EvidenceSpan | evidence span | evidence on StateClaim |
| Pre-formed pressure | (implicit) | Signal | Salience |
| Unresolved pressure | Contradiction | Constraint / failure mode | Tension |
| Change moment | Temporal activation | State transition | Event (Tajallī) |
| Interpretive stance | ActivationContext | ObserverLens | Frame |
| Access mode | (partial) | observer_lens | Lens |
| Valid silence | Silence invariant | low confidence flag | Hold |
| Provenance | Assertion provenance | evidence coverage | StateClaim provenance |
| Confidence | quarantine tier | confidence score | confidence |
| Valence / affect | (via quality intensity) | (weak) | Valence |
| Goal / telos | potential_actualizations | Goal | Telos |
| Modality | (implicit) | (implicit) | Modality |

#### A.2 MTSF-only ontological

ThoughtField, IdeaEntity, SubEntity, QualityRegion, QualityRole, Assertion, EvidenceSpan

#### A.3 SDS-only ontological

Role, State, Constraint, Signal, Receiver, Bottleneck, Observer, Goal, Missing information

#### A.4 ThoughtShape-only ontological

Dimension, Station, Facet, StateClaim, CrossDimensionalRelation, TemporalContour, ExpressionSurface

#### A.5 Chat-only ontological

ReasoningStep, ReasoningMove, ReasoningTrace, ReasoningSignature, HoldRecord, PlacedFragment, Cluster, ClusterLane, MimicProfile

---

### B. Structural composites — assemblies

#### B.1 MTSF composites

Shape, CandidateShape, Stencil, ShapeInstance, ProblemShape, ActivationSnapshot, Subgraph, Artifact

#### B.2 SDS composites

System-Dynamic Signature, FeedbackLoop, MovementSignature, MovementArchetype, TransferLedger, AntiMatch, InterventionPattern

#### B.3 ThoughtShape composites

ThoughtShape, Projection, LensView, ExpressionBundle

#### B.4 Chat composites

ThoughtObject (pending schema lock), CaptureSession, CuratorSpace, CommunityFlywheel

---

### C. Relations and dynamics — how things connect and move

#### C.1 MTSF relations

- **Count:** 22 primitives, 4 levels (entity, quality, artifact, meta)
- **Families:** structural, causal, associative, hierarchical, temporal, cross-register
- **Examples:** contains, part_of, causes, enables, contradicts, analogous_to, activates, precedes, co_occurs, bridges_register

#### C.2 SDS edges (10 types)

causes, amplifies, inhibits, depends_on, transforms_into, competes_with, enables, constrains, delays, feeds_back_into

#### C.3 SDS movement primitives (18)

accumulate, decompose, recombine, translate, constrain, release, amplify, dampen, delay, invert, filter, stabilize, destabilize, differentiate, integrate, externalize, internalize

#### C.4 ThoughtShape relations

- Directional influence between StateClaims
- Cross-dimensional relations (not necessarily causal)
- Tension as unresolved relation pressure

#### C.5 Chat dynamics

| Dynamic | Description |
|---------|-------------|
| `prompted_by` | ReasoningStep link to prior step(s) |
| `move_type` | extends, revises, contrasts, grounds, bridges |
| `revisitation` | Curator evidence of gravity |
| `cluster_affinity` | Signature distance for grouping |

---

### D. Patterns and abstractions

| Level | MTSF | SDS | ThoughtShape |
|-------|------|-----|--------------|
| Abstract pattern | Stencil | MovementArchetype | Relation topology |
| Match surface | Shape index | Transfer ledger | Compare operation |
| False match guard | Quarantine tier | AntiMatch library | (via SDS overlay) |
| Problem pattern | ProblemShape | Failure mode archetype | Tension pattern |
| User pattern memory | Session/global graph | 4-tier living library | Lens history |

**Named cross-framework pattern examples:**

| Pattern intent | MTSF | SDS | ThoughtShape |
|----------------|------|-----|--------------|
| Surface without depth | surface-without-depth | signal_without_semantics | high logo + low meaning |
| Cross-register bridge | metaphysical-actual-bridge | translation_failure | cross-dim bridge |
| Accumulation without integration | shape drift | dilution_through_accumulation | facet spread without integration |

---

### E. Epistemic machinery — how claims are justified

| Machinery | MTSF | SDS | ThoughtShape |
|-----------|------|-----|--------------|
| Evidence model | Assertion + span | State + span | StateClaim evidence |
| Confidence | Quarantine tiers | Coverage score | confidence field |
| Valid silence | Invariant #12 | Missing info flag | Hold operation |
| Contradiction policy | May remain unresolved | Failure mode node | Tension preserved |
| Provenance chain | Assertion store | Transfer ledger | Update trail |
| Validation | Schema + ontology + 13 evals | 5-layer hybrid evaluator | Lens fidelity rubric |
| Anti-premature structure | Fast/deep modes | Abstraction levels | Hold + progressive depth |

---

### F. Interpretive machinery — how stance changes extraction

| Machinery | MTSF | SDS | ThoughtShape |
|-----------|------|-----|--------------|
| Extraction stance | ActivationContext | ObserverLens (constitutive) | Frame |
| Lens catalog | (none predefined) | (none) | 7 lenses |
| Lens affects extraction | Partial | Yes | Yes |
| Lens affects output | No | No (analogy separate) | Yes (core) |
| Identity reduction | reduce_identity() | Role remapping | Station×Dimension projection |
| Progressive resolution | Fast → deep | Abstraction levels 1–6 | Levels 1–6 explicit |

---

### G. Operations — verbs and pipelines

| Framework | Operations |
|-----------|------------|
| **MTSF** | capture, populate, extract, discover, project, activate, actualize, promote, expand, follow, reduce_identity, merge_stencil |
| **SDS** | extract_signature, match_archetype, generate_analogy, evaluate_transfer, record_anti_match, propose_intervention, update_library |
| **ThoughtShape** | Capture → Hold → Differentiate → Shape → Locate → Compare → Transform → Express → Evaluate → Update |
| **Chat / Trace** | Drop, Hold, Trace, Mirror, Prompt |
| **Chat / Curator** | Place, Tend, Revisit, Release, Compose |
| **Chat / Community** | Mimic, Cluster, Connect |

---

### H. Spaces and layers — where things live

#### H.1 MTSF spaces

Metaphysical, Latent (bridge only), Actual; graph layers 0–4; ingest→actualization pipeline.

#### H.2 SDS layers

LLM extraction → analogy → evaluation → living library.

#### H.3 ThoughtShape layers

Field → Entity → Dimension → Station → Facet/Subsystem → StateClaim → Relation → Event → Expression

#### H.4 Product stack layers

NETWORK → SURFACES → GRAMMAR → OVERLAY → SUBSTRATE (see [§2](#2-the-unified-stack))

---

### I. Invariants — rules that must not break

#### I.1 MTSF (13) — see [§3.9](#39-mtsf-invariants-13)

#### I.2 SDS — see [§4.11](#411-sds-invariants)

#### I.3 ThoughtShape — see [§5.12](#512-thoughtshape-design-principles) and Hold-before-Differentiate

#### I.4 Unified / chat

- One ontology, three views — not three stores
- Synthesize before building surfaces
- ReasoningStep is atomic capture unit
- Mimic style, not content

---

### J. Outputs — what the system produces

| Output | MTSF | SDS | ThoughtShape | Chat |
|--------|------|-----|--------------|------|
| Persistent memory | Assertion store, content graph | Living library tiers | Update trail | Session + signature |
| Discovery | CandidateShape, shape index | Archetype match | Compare retrieval | Cluster map |
| Artifact | Actualization output | Intervention pattern | Expression surface | Product lane |
| Analogy | Quarantined analogical_match | Transfer + anti-match | (via SDS overlay) | — |
| User-facing | (thin) | Intervention text | Lens-routed expression | Trace timeline, curator space |
| Network | — | — | — | People matching by reasoning topology |

---

### K. Philosophical commitments

#### K.1 Lineage by framework

| Tradition | MTSF | SDS | ThoughtShape |
|-----------|------|-----|--------------|
| Aristotle (potentiality/actuality) | Strong | Strong | Implicit |
| Kant (schematism) | Stencil | **Primary** | Frame |
| Gentner (structure mapping) | Stencil match | **Primary** | Compare |
| Cybernetics / Meadows | Thin | **Core** | Cross-dim chains |
| Maqām/Ḥāl/Tajallī | Partial | Partial | **Root** |
| Gendlin (felt sense) | Silence | Weak | **Hold** |
| VSM / systems thinking | Module nesting | Recursive boundary | Subsystem expansion |

#### K.2 Shared epistemological commitments

- Meaning is relational, not atomistic
- Pre-explicit thought is real
- Context / lens / frame changes extraction
- Provenance and confidence are mandatory
- Progressive depth — do not over-structure early
- Cross-domain insight is structural, not keyword-based

#### K.3 Divergent epistemic bets — see framework sections [§3.11](#311-mtsf-epistemic-bet), [§4.12](#412-sds-epistemic-bet), [§5.13](#513-thoughtshape-epistemic-bet)

---

## 9. Overlap map — same thing, different names

| Universal concept | MTSF | SDS | ThoughtShape |
|-------------------|------|-----|--------------|
| Pre-clear zone | ThoughtField | Field | Field |
| Carrier | Entity | Entity+Role | Entity |
| Qualified claim | Assertion | State+evidence | StateClaim |
| Abstract pattern | Stencil | MovementArchetype | Relation topology |
| Interpretive stance | ActivationContext | ObserverLens | Frame+Lens |
| Unresolved pressure | Contradiction | Constraint/failure | Tension |
| Valid silence | Silence invariant | Low confidence | Hold |
| Change | Temporal activation | State transition | Event |
| Output | Artifact | Intervention | Expression |

**Synthesis rule:** collapse shared ontological primitives to **one canonical name** per concept in the ThoughtObject schema; retain framework-specific names only as **projection aliases** in views, not as parallel stores.

---

## 10. Framework ownership matrix

Who should own what in the unified architecture:

| Concern | Owner | Notes |
|---------|-------|-------|
| Persistence, events, graph | **MTSF** | Canonical store |
| Facets, dimensions, lenses, Hold UX | **ThoughtShape** | Product grammar |
| Loops, analogy, intervention, non-movement | **SDS** | On-demand overlay |
| Per-drop capture, trace | **Chat / Trace** | ReasoningStep on T0+ |
| Inner topology curation | **Chat / Curator** | PlacedFragment rituals |
| Clustering, mimic bot | **Chat / Community** | ReasoningSignature → Cluster |
| Cross-domain false-analogy guard | **SDS** | Anti-match + 5-layer eval |
| Discovery without template | **MTSF** | CandidateShape pipeline |
| Lens-routed expression | **ThoughtShape** | 7-lens catalog |
| Session-to-session memory | **MTSF** | Assertion + content graph |

### Primitives unique to one framework (do not duplicate)

| Framework | Unique contributions |
|-----------|---------------------|
| **MTSF** | metaphysical/latent/actual spaces, promotion gates, discovery without template, reduce_identity(), 13 gap evals, assertion store, content graph layers |
| **SDS** | transfer ledger, anti-matches, 5-layer evaluator, system boundary, 18 movement primitives, living library tiers, non-movement problem |
| **ThoughtShape** | Dimension, Station×Facet formula, 7-lens catalog, valence, Hold operation, cross-dimensional relation as core, expression routing |
| **Chat** | ReasoningStep, ReasoningSignature, Cluster, mimic questioning, PlacedFragment, CuratorSpace, CommunityFlywheel |

---

## 11. Naming collisions to avoid

| Term | Confusion | Resolution |
|------|-----------|------------|
| **Shape** vs **ThoughtShape** | Shape = topology primitive or MTSF composite; ThoughtShape = full grammar/framework | Use **Shape** for topology; **ThoughtShape** for framework/grammar view only |
| **Shape** (noun) vs **Shape** (verb) | ThoughtShape pipeline includes Shape as operation | Context: operation = relate facets; noun = topology |
| **State** | SDS State vs StateClaim vs Ḥāl | Canonical: **StateClaim** in unified ontology; SDS State maps at overlay |
| **Entity** | MTSF IdeaEntity vs generic Entity | Canonical: **Entity**; MTSF IdeaEntity is substrate implementation detail |
| **Field** | ThoughtField vs Field vs embedding field | Canonical: **Field** (pre-clear zone); latent embedding space is **not** Field |
| **Lens** vs **Frame** vs **ObserverLens** | Three stance primitives | **Frame** (unified) + lens catalog (ThoughtShape); SDS **ObserverLens** at overlay extraction |
| **Formation** vs **ThoughtObject** | Formation = stabilized outcome; ThoughtObject = container | Formation crystallizes *inside* ThoughtObject |
| **Stencil** vs **MovementArchetype** | Same intent, different abstraction level | Both map to **Stencil** at unified layer; SDS archetype attaches as overlay metadata |

---

## 12. Philosophical commitments

### One underlying reality, three perspectives

- **ThoughtShape** — what meaning *is* (phenomenological grammar)
- **MTSF** — what the system *remembers* (persistence and discovery)
- **SDS** — what the system *infers about motion* (dynamics and intervention)

### Maqām → Ḥāl → Tajallī mapping

| Arabic | Unified | MTSF | SDS | ThoughtShape |
|--------|---------|------|-----|--------------|
| Maqām | Station | Quality type / role slot | State variable / role container | Station |
| Ḥāl | StateClaim | Quality intensity / region | State node value | StateClaim |
| Tajallī | Event | Actualization / activation | State transition / loop firing | Event |

ThoughtShape makes the triad **operational** by adding dimension, facet, and cross-dimensional relation.

---

## 13. Implementation posture in this repo

| Component | Repo status |
|-----------|-------------|
| MTSF kernel (graph, events, extraction) | Partial — `src/conversation_os/` modules, `models.py` shape types |
| `CandidateShape`, `SystemDynamicSignature` | Present in `models.py` |
| `ThoughtObject`, `ReasoningStep`, `HoldRecord` | **Not implemented** — schema lock pending |
| SDS runtime overlay | **Not implemented** |
| ThoughtShape schema | **Not implemented** — design docs only |
| Pilot 003 reasoning signature | Sandbox prototype (referenced; path may be outside snapshot) |
| Personal Interface | Operational — extend to reasoning-move calibration |

---

## 14. Open synthesis work

This catalogue is **descriptive**, not yet **normative**. Pending next steps from the workspace:

1. **Rearrange** primitives into one unified framework document with canonical names
2. **Lock schemas:** ThoughtObject, ReasoningStep, ReasoningSignature, Cluster
3. **Update glossary:** `docs/product-thesis/02-glossary.md`
4. **Phase 1 capture kernel:** ReasoningStep per drop, Hold record, trace links on session append
5. **Deduplicate** ~45 shared ontological primitives into single types in assertion store

**Success condition (from holodeck summary):** unified framework locked; schemas drafted; capture kernel specified.

---

## 15. Source index

| Document | Path |
|----------|------|
| This catalogue | `analyses/primitive-catalogue-and-framework-reference.md` |
| Abbreviated decomposition | `analyses/framework-primitive-decomposition.md` |
| Unified synthesis | `sources/unified-framework-synthesis.md` |
| Three-framework comparison | `sources/three-framework-comparative-evaluation.md` |
| Epistemology | `analyses/epistemology-and-overlap.md` |
| SDS non-movement | `analyses/sds-non-movement-problem.md` |
| Thought Trace | `analyses/reasoning-step-capture.md` |
| Inner Space Curator | `analyses/inner-space-curator.md` |
| Community pipeline | `analyses/community-pipeline.md` |
| Symbiotic reasoning extension | `analyses/2026-07-10-symbiotic-reasoning-pipelines-and-idea-formation.md` |
| ThoughtShape v1 | `docs/frameworks/thought-shape/ThoughtShape-framework-v1.md` |
| SDS v1 | `docs/frameworks/system-dynamic-signature/SDS-v1.0-report.md` |
| MTSF tree | `docs/frameworks/metaphysical-thought-space/` |
| Workspace manifest | `manifest.json` |

---

*End of catalogue. For handoff constraints and next actions, see [derived/handoff.md](../derived/handoff.md) and [continuity/task-pack.md](../continuity/task-pack.md).*
