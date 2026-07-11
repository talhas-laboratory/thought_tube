# Primitives, Frameworks, and Unified Vision

**Workspace:** `unified-framework-synthesis-4f48`  
**Status:** Reference guide — pre-synthesis (Jul 2026)  
**Date:** 2026-07-11

A readable guide to **what every primitive is**, **what it does**, **how each framework works**, and **the unified vision** they compose into.

**Companion (deeper reference):** [primitive-catalogue-and-framework-reference.md](./primitive-catalogue-and-framework-reference.md)

---

## Table of contents

1. [The unified vision](#1-the-unified-vision)
2. [The three frameworks](#2-the-three-frameworks)
3. [Complete primitive registry](#3-complete-primitive-registry)
4. [How primitives map across frameworks](#4-how-primitives-map-across-frameworks)
5. [Related documents](#5-related-documents)

---

## 1. The unified vision

### 1.1 What we are building

Thought Tube / Inner World is **one meaning operating system** — not three products, not three ontologies, not three databases.

A person’s thought is a **living, multidimensional meaning-shape**. People lose thoughts when capture asks for the wrong granularity at the wrong time. The system must:

- hold ambiguity without flattening it
- trace reasoning step by step
- curate inner space as a mirror, not a filing cabinet
- eventually cluster people by **how they think**, not only what they think about

### 1.2 One object, three views

Everything persists as a single **ThoughtObject** in the MTSF-backed store. Three frameworks are **projections** on that object — not parallel registries:

```text
                    ┌─────────────────────────────┐
                    │      ThoughtObject           │
                    │   (one canonical store)      │
                    └──────────────┬──────────────┘
                                   │
         ┌─────────────────────────┼─────────────────────────┐
         │                         │                         │
  ThoughtShape view           MTSF view                SDS view (optional)
  what meaning IS           what the system          what the system
  (grammar, lenses,         REMEMBERS                INFERS about MOTION
   facets, tensions)        (graph, shapes,          (loops, archetypes,
                             discovery)               analogies, intervention)
```

**Rule:** one ontology, three views — stack them, do not compete.

### 1.3 The product stack

```text
NETWORK     Community pipeline — mimic → signature → cluster → connect
SURFACES    Thought Trace + Inner Space Curator
GRAMMAR     ThoughtShape — Dimension × Station × Facet = StateClaim
OVERLAY     SDS on demand — loops, analogies, intervention, non-movement
SUBSTRATE   MTSF — events, assertions, graph, shapes, discovery, provenance
```

### 1.4 Core formulas

```text
Station × Dimension × Facet = StateClaim
Shape = relation topology across StateClaims
Stencil = abstract pattern of a shape (cross-domain match key)
```

### 1.5 Build discipline

1. **Synthesize first** — rearrange ~120–140 decomposed primitives into one canonical ontology
2. **Lock schemas** — ThoughtObject, ReasoningStep, ReasoningSignature, Cluster
3. **Build capture kernel** — per-drop ReasoningStep, Hold record, trace links
4. **Then surfaces** — Thought Trace, Inner Space Curator, community pipeline
5. **Never** — parallel ontologies, three storage systems, or surfaces before schema lock

### 1.6 Product surfaces (one kernel, three rituals)

| Surface | User question | Atomic unit | Character |
|---------|---------------|-------------|-----------|
| **Thought Trace** | How did I get here? | ReasoningStep | Forensic replay instrument |
| **Inner Space Curator** | What world am I building by what I attend to? | PlacedFragment | Mirror / alchemical practice |
| **Community pipeline** | Who thinks like me? | ReasoningSignature → Cluster | Network flywheel |

### 1.7 Locked decisions

- MTSF = canonical **store**; extend its schema for ThoughtShape primitives
- ThoughtShape = product **grammar** and lens routing
- SDS = **optional overlay** when motion, analogy, or intervention is needed
- ReasoningStep = atomic **capture** unit (not session, not formation)
- Cross-agent continuity lives in this workspace + `docs/continuity/`

### 1.8 Success condition

Unified framework locked → schemas drafted → capture kernel specified → surfaces built on kernel, not beside it.

---

## 2. The three frameworks

### 2.1 MTSF — Metaphysical Thought-Space Framework

| | |
|---|---|
| **Role** | Substrate — persistence, discovery, actualization |
| **Core unit** | Shape / stencil on entities + qualities + relations |
| **Core question** | What exists in mind-space, and how does it become artifact? |
| **Status** | **Operational** — kernel in repo, assertion store, content graph, gap evals |
| **Canonical docs** | `docs/frameworks/metaphysical-thought-space/` |

**What it is:** MTSF is the **memory and discovery engine**. It models pre-material thought as navigable structure across three spaces:

- **Metaphysical** — pre-formed possibility (not embedding space)
- **Latent** — operational bridge (embeddings, transformers) — *latent ≠ metaphysical*
- **Actual** — artifacts and externalized outputs

**Pipeline:**

```text
Field → Entity → Quality → Relation → Shape → Stencil → Artifact
```

**What it optimizes for:** durability across sessions; discovery of candidate shapes without pre-known templates; actualization (binding constraints to produce artifacts); provenance; valid silence (unresolved contradiction may remain).

**Primary unit of truth:** shape / stencil.

**Main failure mode:** over-structure — forcing form before the thought supports it.

**Unique contributions:** assertion store, content graph layers 0–4, discovery without template, promotion gates, 13 gap-closure evals (G01–G13), `reduce_identity()`.

---

### 2.2 SDS — System-Dynamic Signature Framework

| | |
|---|---|
| **Role** | Overlay — motion, analogy, intervention |
| **Core unit** | Movement signature / system in motion |
| **Core question** | What transformation is happening, and what cross-domain analogies hold? |
| **Status** | **Design v1.0** — full report in repo; `SystemDynamicSignature` type in `models.py` |
| **Canonical docs** | `docs/frameworks/system-dynamic-signature/SDS-v1.0-report.md` |

**What it is:** SDS treats input as a **system in motion** — entities with roles, states, causal relations, feedback loops, constraints, and failure modes. It extracts a **movement archetype** and matches it against a living library for cross-domain analogy and intervention.

**Pipeline:**

```text
Field → Entities+Roles → States → Causal Relations → Feedback Loops
     → Movement Archetype → Analogies → Transfer Ledger → Intervention
```

**What it optimizes for:** transformation (not just existence); structural cross-domain transfer (not semantic similarity); anti-matches (explicit rejection of false analogies); constitutive observer lens; **non-movement** (blockages, absences, bottlenecks as first-class).

**Primary unit of truth:** movement signature.

**Main failure mode:** false analogy — poetic matches without structural alignment.

**Unique contributions:** transfer ledger, anti-match library, 5-layer hybrid evaluator, 18 movement primitives, living archetype library, non-movement problem.

**When to attach:** on demand, when a shape needs loops, intervention paths, or cross-domain transfer — not as a second store.

---

### 2.3 ThoughtShape — Product meaning grammar

| | |
|---|---|
| **Role** | Grammar — phenomenological meaning configuration |
| **Core unit** | Multidimensional meaning-shape |
| **Core question** | What is the relational configuration of meaning across dimensions? |
| **Status** | **Design v1.0** — spec in repo; no dedicated schema yet |
| **Canonical docs** | `docs/frameworks/thought-shape/ThoughtShape-framework-v1.md` |

**What it is:** ThoughtShape models thought as a **dynamic, multidimensional meaning-shape** — not a sentence, not flat text. It adds **dimension**, **station**, and **facet** as first-class layers so the same entity (e.g. a brand) can be read across psychological, financial, narrative, and brand layers simultaneously.

**Philosophical root:** Maqām → Ḥāl → Tajallī → Station → StateClaim → Event.

**Pipeline:**

```text
Field → Entity → Dimension → Frame → Station → Facet/Subsystem
     → StateClaim → Relation → Event → Expression → Update
```

**Runtime operations:**

```text
Capture → Hold → Differentiate → Shape → Locate → Compare
       → Transform → Express → Evaluate → Update
```

**What it optimizes for:** faceted precision (logo recognition ≠ meaning recognition); progressive depth (Hold before Differentiate); lens routing (7 product lenses as structured access modes, not prompts); tension and valence preserved.

**Primary unit of truth:** StateClaim topology.

**Main failure mode:** flatten dimensions — collapsing multidimensional meaning into one layer.

**Unique contributions:** Dimension × Station × Facet formula, 7-lens catalog, Hold operation, cross-dimensional relations as core shape mechanism, expression-surface routing.

---

### 2.4 Chat-layer additions (Jul 2026 design thread)

Not separate frameworks — **product primitives** added during the unified synthesis thread:

| Addition | Purpose |
|----------|---------|
| **ReasoningStep / Trace** | Per-drop capture; rebuild reasoning chain |
| **Inner Space Curator** | Place, tend, revisit, release — inner topology |
| **Community pipeline** | Mimic-reasoning bot → signature → cluster → connect |
| **ThoughtObject** | Unified kernel envelope (schema pending) |

---

## 3. Complete primitive registry

Each entry: **what it is** (definition) and **function** (what it does in the system).

**Legend — source tags:** `[U]` unified canonical · `[M]` MTSF · `[S]` SDS · `[T]` ThoughtShape · `[C]` chat/design thread · `[shared]` appears in multiple frameworks under different names

---

### 3.1 Ontological primitives — things that exist

#### Shared / unified ontological primitives

| Primitive | What it is | Function | Source |
|-----------|------------|----------|--------|
| **Field** | Pre-clear zone of possibility — vague feeling, intuition, half-formed sense | Holds meaning before it earns structure; valid without resolution | [U] shared |
| **Entity** | Carrier of meaning — person, brand, idea, product, self | Anchors all claims and relations to a subject | [U] shared |
| **Subsystem** | Facet expanded with internal structure when depth is earned | Allows progressive resolution without early over-structure | [U] shared |
| **StateClaim** | Qualified condition: state + weight + salience + valence + confidence + evidence | Atomic asserted meaning at a point in station×dimension×facet | [U] ← Assertion/State |
| **Evidence** | Text span or source backing a claim | Grounds claims; enables confidence scoring | [U] shared |
| **Salience** | Pre-formed pressure / attention weight on a claim | Signals what wants attention before it is fully articulated | [U] shared |
| **Tension** | Unresolved pressure inside a shape (e.g. familiarity vs comprehension) | Preserves contradiction as structural fact, not error | [U] shared |
| **Event** | State change, disclosure, transformation (Tajallī) | Records moments when meaning shifts or becomes visible | [U] shared |
| **Frame** | Interpretive stance active right now | Localizes extraction and access to the current lens/context | [U] shared |
| **Lens** | Structured access mode into a multidimensional shape | Routes which dimensions/stations activate and which outputs surface | [U] ← ThoughtShape |
| **Hold** | Valid state of preserved ambiguity | Prevents premature structure; "meaningful but not clear" is OK | [U] ← ThoughtShape |
| **Provenance** | Source trail for structural knowledge | Anti-hallucination; tracks confirmed vs inferred vs contradicted | [U] shared |
| **Confidence** | Scored certainty on a claim or extraction | Drives quarantine, missing-info flags, and user review | [U] shared |
| **Valence** | Affective charge on a claim | Preserves felt sense, not just propositional content | [T] |
| **Telos** | Directional purpose or goal-state | Orients meaning toward what the thought is trying to become | [U] shared |
| **Modality** | Mode of being (possible, actual, counterfactual…) | Separates what is from what could be or was | [T] |

#### MTSF ontological primitives

| Primitive | What it is | Function | Source |
|-----------|------------|----------|--------|
| **ThoughtField** | Pre-material activation zone with temporal trace | MTSF-specific field with persistence hooks for discovery | [M] |
| **IdeaEntity** | Entity with qualities, relations, intensity, temporal_state | Primary MTSF carrier in assertion/graph store | [M] |
| **SubEntity** | Typed recursive nested carrier | Models systems-within-systems in MTSF graph | [M] |
| **QualityRegion** | One of ten quality types as a navigable region | Locates meaning within MTSF quality topology | [M] |
| **QualityRole** | Governing categorical operator on qualities | Structures how qualities combine in a shape | [M] |
| **Assertion** | Evidence-backed qualified claim in assertion store | MTSF unit of persisted, queryable truth | [M] |
| **EvidenceSpan** | Text span backing an assertion | Links natural language to structured claims | [M] |
| **Contradiction** | Unresolved opposing claims | May remain unresolved per invariant #13 | [M] |

#### SDS ontological primitives

| Primitive | What it is | Function | Source |
|-----------|------------|----------|--------|
| **Role** | Functional position in a system (not identity) | Enables cross-domain mapping by function, not noun | [S] |
| **State** | Typed node value with evidence | Snapshot of a condition in the dynamic system | [S] |
| **Constraint** | Hard limit on a state transition | Models non-movement — what cannot happen | [S] |
| **Signal** | Observable system output | What the system emits or expresses outward | [S] |
| **Receiver** | Target of a signal or effect | Who or what interprets the signal | [S] |
| **Bottleneck** | Rate-limiting node in a flow | Identifies where movement stalls | [S] |
| **Observer** | Constitutive interpreting position | Shapes what gets extracted — not optional metadata | [S] |
| **Goal** | Explicit system objective | Target state the system is moving toward | [S] |
| **Missing information** | Flagged absence in extraction | Scores incomplete evidence; prevents false confidence | [S] |

#### ThoughtShape ontological primitives

| Primitive | What it is | Function | Source |
|-----------|------------|----------|--------|
| **Dimension** | First-class layer of interpretation (brand, financial, psychological…) | Same entity, many valid layers simultaneously | [T] |
| **Station** | Possibility-space where a kind of meaning varies (recognition, trust, clarity…) | Maqām — where Ḥāl (StateClaim) can differ | [T] |
| **Facet** | Specific aspect within station × dimension | Splits recognition into logo vs meaning vs category, etc. | [T] |
| **CrossDimensionalRelation** | Relation across dimensions, not only within one | Core mechanism of deep shape — how brand recognition affects conversion | [T] |
| **TemporalContour** | How meaning evolves over time | Tracks trajectory, not just snapshot | [T] |
| **ExpressionSurface** | Output routing target per lens | Where shaped meaning becomes manifesto, feature, scene, etc. | [T] |

#### Chat / capture ontological primitives

| Primitive | What it is | Function | Source |
|-----------|------------|----------|--------|
| **ReasoningStep** | Single drop in a reasoning chain | Atomic capture unit — not session, not formation | [C] |
| **ReasoningMove** | Named move type (ground, triangulate, bridge, formalize, invert…) | Classifies how the user is thinking at this step | [C] |
| **ReasoningTrace** | Ordered chain of ReasoningSteps | Reconstructs "how I got here" | [C] |
| **ReasoningSignature** | Person-level recurring reasoning topology | Clusters users; tunes mimic-bot questioning style | [C] |
| **HoldRecord** | Persisted hold state at capture time | First-class ambiguity, not empty draft | [C] |
| **PlacedFragment** | Content placed in inner topology | Unit of Inner Space Curator | [C] |
| **Cluster** | Group defined by reasoning topology, not demographics | Community segmentation and product lanes | [C] |
| **ClusterLane** | Product variant shell for a cluster | Same kernel, different ritual per cluster | [C] |
| **MimicProfile** | Bot interrogation style calibrated to a person | Mimics reasoning moves, not content | [C] |

---

### 3.2 Structural composites — assemblies built from primitives

| Primitive | What it is | Function | Source |
|-----------|------------|----------|--------|
| **ThoughtObject** | Unified kernel record in MTSF-backed store | Single persisted envelope for one unit of meaning work | [C] pending schema |
| **Formation** | Stabilized whole from multiple steps / state-claims | Crystallized outcome — Coagulatio in alchemical chain | [U] |
| **Shape** | Relation topology across StateClaims | Structural wiring of meaning — not the whole thought | [U] |
| **Stencil** | Abstract pattern of a shape | Cross-domain match key; retrieval without keywords | [U] |
| **ThoughtShape** (composite) | Full multidimensional meaning configuration | Complete grammar view of an entity's meaning | [T] |
| **CandidateShape** | Provisional shape from discovery | Holds unknown patterns before template exists | [M] |
| **ShapeInstance** | Live binding of shape to entity/context | Which shape is active now for this entity | [M] |
| **ProblemShape** | Problem signal structured for analogical match | Routes problems to stencil/archetype libraries | [M] |
| **ActivationSnapshot** | Point-in-time activation state | Freezes what was live at a moment | [M] |
| **Subgraph** | Extracted graph fragment (layers 0–4) | Bounded query/view over MTSF graph | [M] |
| **Artifact** | Externalized actualization output | What leaves the system as product, doc, scene, etc. | [M] |
| **System-Dynamic Signature** | Full typed graph: entities, states, relations, loops | Complete SDS extraction of a system in motion | [S] |
| **FeedbackLoop** | Circular causal chain | Models reinforcing or balancing dynamics | [S] |
| **MovementSignature** | Extracted transformation pattern | Abstract description of how change proceeds | [S] |
| **MovementArchetype** | Library-stored abstract movement | Reusable cross-domain pattern (growing grammar) | [S] |
| **TransferLedger** | Record of cross-domain transfer attempts | Tracks what transferred, what broke, what was rejected | [S] |
| **AntiMatch** | Explicitly rejected analogy | Prevents false cross-domain matches | [S] |
| **InterventionPattern** | Actionable intervention from source domain | "What to do" derived from structural analogy | [S] |
| **Projection** | Station × Dimension → localized meaning | Shows how same station reads differently per layer | [T] |
| **LensView** | Same shape accessed through one lens | Product-facing slice of full ThoughtShape | [T] |
| **ExpressionBundle** | Lens-routed output package | Groups expressions for a given access mode | [T] |
| **CaptureSession** | Drop → Hold → Trace sequence | Bounded capture episode | [C] |
| **CuratorSpace** | Inner topology of placed fragments | Spatial model of user's inner world | [C] |
| **CommunityFlywheel** | social → mimic → signature → cluster pipeline | Network growth and product mutation loop | [C] |
| **IdeaWorld** | Bounded projection over ThoughtObject + related records | Larger conceptual environment (thesis, film, worldview) — not a second store | [C] extension |

---

### 3.3 Relations — how primitives connect

#### MTSF relations (22 types, 4 levels)

| Primitive | What it is | Function | Source |
|-----------|------------|----------|--------|
| **contains** | Parent envelops child | Hierarchical nesting | [M] |
| **part_of** | Child belongs to parent | Inverse hierarchy | [M] |
| **causes** | One element produces another | Causal chain in MTSF graph | [M] |
| **enables** | Makes possible without necessitating | Precondition relation | [M] |
| **contradicts** | Opposing claims coexist | Tension without forced resolution | [M] |
| **analogous_to** | Structural similarity claim | Discovery and quarantined match | [M] |
| **activates** | Brings into active consideration | Shape/quality activation | [M] |
| **precedes** | Temporal ordering | Sequence in reasoning or time | [M] |
| **co_occurs** | Co-present without causation | Association without direction | [M] |
| **bridges_register** | Links across register/space | Cross-metaphysical-actual bridge | [M] |
| *(+ 12 more across entity, quality, artifact, meta levels)* | | | [M] |

#### SDS edge types (10)

| Primitive | What it is | Function | Source |
|-----------|------------|----------|--------|
| **causes** | Necessary or sufficient production | Directed causation | [S] |
| **amplifies** | Increases magnitude or rate | Reinforcing dynamics | [S] |
| **inhibits** | Decreases or blocks | Dampening / prevention | [S] |
| **depends_on** | Required precondition | Unmet dependency = non-movement | [S] |
| **transforms_into** | State change or metamorphosis | Core transition edge | [S] |
| **competes_with** | Resource or attention competition | Rivalry dynamics | [S] |
| **enables** | Makes possible | Affordance without force | [S] |
| **constrains** | Limits possible states | Hard boundary on movement | [S] |
| **delays** | Introduces temporal lag | Models slow feedback | [S] |
| **feeds_back_into** | Circular causal influence | Closes feedback loops | [S] |

#### ThoughtShape relations

| Primitive | What it is | Function | Source |
|-----------|------------|----------|--------|
| **Directional influence** | One StateClaim affects another | Within-dimension wiring | [T] |
| **Cross-dimensional relation** | Influence across dimensions | Deepest shape mechanism | [T] |
| **Tension (as relation pressure)** | Unresolved relation between claims | Holds conflict as structure | [T] |

#### Chat / trace dynamics

| Primitive | What it is | Function | Source |
|-----------|------------|----------|--------|
| **prompted_by** | Link from step to prior step(s) | Builds reasoning chain backward | [C] |
| **move_type** | extends, revises, contrasts, grounds, bridges | Classifies link semantics between steps | [C] |
| **revisitation** | Evidence of return to prior fragment | Curator "gravity" — what pulls attention back | [C] |
| **cluster_affinity** | Distance between reasoning signatures | Groups compatible thinkers | [C] |

---

### 3.4 Movement primitives (SDS)

| Primitive | What it is | Function | Source |
|-----------|------------|----------|--------|
| **accumulate** | Gather or increase quantity | Growth / collection dynamics | [S] |
| **decompose** | Break into parts | Analysis / reduction | [S] |
| **recombine** | Assemble parts into new wholes | Synthesis after decomposition | [S] |
| **translate** | Map between forms or domains | Cross-domain transfer | [S] |
| **constrain** | Limit or bound | Non-movement / boundary | [S] |
| **release** | Remove constraint or allow flow | Unblock transition | [S] |
| **amplify** | Increase signal or effect | Reinforcement | [S] |
| **dampen** | Decrease or stabilize | Negative feedback | [S] |
| **delay** | Introduce temporal lag | Slow dynamics | [S] |
| **invert** | Reverse direction or polarity | Counter-pattern | [S] |
| **filter** | Selectively pass or block | Signal selection | [S] |
| **stabilize** | Maintain state against perturbation | Homeostasis | [S] |
| **destabilize** | Introduce variability or crisis | Change trigger | [S] |
| **differentiate** | Distinguish or separate | Separatio — split facets | [S][T] |
| **integrate** | Unify or merge | Coniunctio — combine claims | [S] |
| **externalize** | Make internal state visible/actionable | Output / expression | [S] |
| **internalize** | Absorb external pattern into structure | Learning / incorporation | [S] |

---

### 3.5 Patterns and abstractions

| Primitive | What it is | Function | Source |
|-----------|------------|----------|--------|
| **Stencil** (pattern) | Abstract shape pattern | Cross-session / cross-domain retrieval key | [M][U] |
| **MovementArchetype** (pattern) | Abstract movement pattern | SDS library entry for analogy | [S] |
| **Relation topology** (pattern) | Recurring cross-claim structure | ThoughtShape compare / retrieve | [T] |
| **Shape index** | Index of known shapes | MTSF discovery and match surface | [M] |
| **Transfer ledger** (pattern memory) | History of transfer attempts | Validates or rejects analogies over time | [S] |
| **AntiMatch library** | Store of rejected analogies | False-match guard | [S] |
| **Living library** | User-validated archetype tiers | SDS accumulated memory | [S] |
| **Quarantine tier** | Confidence gate on assertions | MTSF false-match / low-evidence guard | [M] |
| **ProblemShape / failure mode archetype** | Recurring problem topology | Routes to intervention or stencil | [M][S] |
| **Tension pattern** | Recurring unresolved pressure shape | e.g. surface-without-depth | [T] |

**Named cross-framework pattern examples:**

| Pattern | MTSF name | SDS name | ThoughtShape reading |
|---------|-----------|----------|---------------------|
| Surface without depth | surface-without-depth | signal_without_semantics | high logo recognition + low meaning |
| Cross-register bridge | metaphysical-actual-bridge | translation_failure | cross-dimensional bridge |
| Accumulation without integration | shape drift | dilution_through_accumulation | facet spread without integration |

---

### 3.6 Epistemic machinery — how the system knows

| Primitive | What it is | Function | Source |
|-----------|------------|----------|--------|
| **Assertion store** | Persistent evidence-backed claims | MTSF canonical T1 truth layer | [M] |
| **Quarantine tier** | Low-confidence holding area | Prevents bad claims entering canon | [M] |
| **Evidence span** | Text backing a state or claim | Grounds extraction in source | [M][S][T] |
| **Missing info flag** | Marked absence in extraction | Valid silence with explicit incompleteness | [S] |
| **5-layer evaluator** | Structural + causal + boundary + lens + ledger checks | SDS analogy validation pipeline | [S] |
| **13 gap evals (G01–G13)** | MTSF closure test suite | Proves kernel handles discovery, bridge, dedup, etc. | [M] |
| **Lens fidelity rubric** | Does lens output match shape? | ThoughtShape expression quality gate | [T] |
| **Fast / deep modes** | Progressive extraction depth | Anti-premature-structure in MTSF | [M] |
| **Abstraction levels 1–6** | SDS progressive resolution before archetype match | Avoids over-fitting movement too early | [S] |
| **Progressive depth levels 1–6** | ThoughtShape resolution ladder | Field → facet → cross-dimensional | [T] |
| **Update trail** | History of claim revisions | Provenance over time | [T] |

---

### 3.7 Interpretive machinery — how stance shapes extraction

| Primitive | What it is | Function | Source |
|-----------|------------|----------|--------|
| **ActivationContext** | MTSF context for shape activation | Selects which shape/stencil is live | [M] |
| **ObserverLens** | SDS constitutive extraction frame | Chef vs chemist vs systems_abstractor yield different graphs | [S] |
| **Frame** | Unified interpretive stance | What lens/context is active now | [U] |
| **Lens catalog** | Seven product lenses (Founder, Product, Risk…) | Structured access modes into same shape | [T] |
| **reduce_identity()** | MTSF identity compression | Collapses entity to role for matching | [M] |
| **Role remapping** | SDS identity → function | Cross-domain alignment by role, not noun | [S] |
| **Station×Dimension projection** | ThoughtShape localization | Same station, different reading per layer | [T] |

---

### 3.8 Operations — what the system does

#### MTSF operations

| Operation | What it is | Function |
|-----------|------------|----------|
| **capture** | Ingest raw input | T0 append — save before interpret |
| **populate** | Fill entity/quality structure | Progressive graph building |
| **extract** | Pull structure from text | LLM / rules → assertions |
| **discover** | Find candidate shapes without template | Unknown-pattern retrieval |
| **project** | Apply stencil to entity | Abstract → concrete binding |
| **activate** | Bring shape live in context | Context-dependent shape selection |
| **actualize** | Bind constraints → artifact | Output generation |
| **promote** | Elevate draft to canon | Assertion promotion |
| **expand** | Deepen graph (facets, relations) | Progressive depth |
| **follow** | Traverse graph by intent | Navigation / routing |
| **reduce_identity** | Compress entity for match | Cross-session alignment |
| **merge_stencil** | Combine stencil patterns | Pattern fusion |

#### SDS operations

| Operation | What it is | Function |
|-----------|------------|----------|
| **extract_signature** | Build SDS from input | Layer 1 — structured proposal |
| **match_archetype** | Find movement pattern in library | Layer 2 — retrieval |
| **generate_analogy** | Propose cross-domain matches | Layer 2 — creative transfer |
| **evaluate_transfer** | Run 5-layer validation | Layer 3 — quality control |
| **record_anti_match** | Store rejected analogy | False-match memory |
| **propose_intervention** | Derive action from analogy | Actionable output |
| **update_library** | Add validated archetype | Layer 4 — living memory |

#### ThoughtShape operations

| Operation | What it is | Function |
|-----------|------------|----------|
| **Capture** | Receive raw thought material | Entry point |
| **Hold** | Preserve ambiguity | Anti-premature-structure |
| **Differentiate** | Split into facets/dimensions | Separatio |
| **Shape** | Wire relations between claims | Coniunctio — build topology |
| **Locate** | Place claim in station×dimension×facet | Structural addressing |
| **Compare** | Retrieve similar shapes/tensions | Discovery by structure |
| **Transform** | Change claim or relation | Active reasoning move |
| **Express** | Route to expression surface | Lens output |
| **Evaluate** | Check fidelity / coherence | Quality gate |
| **Update** | Revise claims with provenance | Living shape |

#### Chat / product operations

| Operation | What it is | Function | Surface |
|-----------|------------|----------|---------|
| **Drop** | User releases a thought fragment | Intake | Trace |
| **Hold** | System preserves without forcing structure | Ambiguity | Trace |
| **Trace** | Link step into reasoning chain | Replay | Trace |
| **Mirror** | Reflect back to user | Confirmation | Trace |
| **Prompt** | Ask next reasoning-tuned question | Move continuation | Trace |
| **Place** | Put fragment in inner topology | Spatial curation | Curator |
| **Tend** | Attend to placed fragment over time | Care / maintenance | Curator |
| **Revisit** | Return to prior fragment | Gravity / circulatio | Curator |
| **Release** | Remove or prune fragment | Mortificatio | Curator |
| **Compose** | Arrange fragments into whole | Inner synthesis | Curator |
| **Mimic** | Bot copies user's reasoning style in questions | Calibration | Community |
| **Cluster** | Assign signature to topology group | Segmentation | Community |
| **Connect** | Match people by compatible reasoning moves | Network | Community |

---

### 3.9 Spaces and layers — where things live

| Primitive | What it is | Function | Source |
|-----------|------------|----------|--------|
| **Metaphysical space** | Pre-formed possibility | What could be — not embeddings | [M] |
| **Latent space (bridge)** | Operational ML bridge | Embeddings/transformers — **not** metaphysical | [M] |
| **Actual space** | Externalized artifacts | What has been made real | [M] |
| **Graph layer 0** | Events | Raw append log | [M] |
| **Graph layer 1** | Session graph | Within-session structure | [M] |
| **Graph layer 2** | Content graph | Persistent content handles | [M] |
| **Graph layer 3** | Global graph | Cross-session discovery | [M] |
| **Graph layer 4** | Meta graph | System reflection — ≠ content graph | [M] |
| **SDS tier 1** | LLM extraction | Proposal generation | [S] |
| **SDS tier 2** | Analogy generation | Cross-domain candidates | [S] |
| **SDS tier 3** | Evaluation | Validation | [S] |
| **SDS tier 4** | Living library | User-validated memory | [S] |
| **T0 events.jsonl** | Immediate append log | Save before interpret | [U] impl |
| **T1 assertions** | Evidence-backed claims | Stable truth layer | [U] impl |
| **T2 content graph** | Thin expandable handles | Linkage | [U] impl |
| **T3 shapes/stencils** | When stable enough | Pattern layer | [U] impl |
| **T4 cluster assignment** | Community layer | Network segmentation | [U] impl |

---

### 3.10 Invariants — rules the system must not break

| Invariant | What it is | Function | Source |
|-----------|------------|----------|--------|
| Latent ≠ metaphysical | Embedding space is bridge only | Prevents category error in ontology | [M] |
| Silence is valid | Unresolved state is OK output | Anti-forced-structure | [M][U] |
| Contradiction may remain | Opposing claims can coexist | Honest epistemics | [M][U] |
| Stencil ≠ full shape | Abstract ≠ complete instance | Prevents over-generalization | [M] |
| Meta graph ≠ content graph | System data separate from user meaning | Clean architecture | [M] |
| Observer lens is constitutive | Stance shapes extraction | Epistemic humility | [S] |
| Non-movement is first-class | Blockage matters as much as flow | SDS unique contribution | [S] |
| Anti-matches required | Must record rejected analogies | Safe cross-domain transfer | [S] |
| Hold before Differentiate | Ambiguity before splitting | ThoughtShape progressive depth | [T] |
| Lens is access mode | Not a free-form prompt | Structured product routing | [T][U] |
| One ontology | No parallel registries | Unified vision core rule | [U] |
| ReasoningStep is atomic | Capture unit is per-drop | Trace design | [U] |
| Mimic style not content | Bot copies moves, not answers | Community ethics | [U] |
| Save before interpret | T0 on every drop | Data safety | [U] |
| Provenance everywhere | No hallucinated inner world | Trust | [U] |

---

### 3.11 Outputs — what the system produces

| Output | What it is | Function | Source |
|--------|------------|----------|--------|
| **Persistent memory** | Cross-session stored structure | Continuity | [M] |
| **CandidateShape** | Discovered unknown pattern | Novelty without template | [M] |
| **Artifact** | Externalized product of actualization | Deliverable | [M] |
| **Intervention pattern** | Actionable principle from analogy | "What to do" | [S] |
| **Analogy + transfer record** | Cross-domain match with ledger | Insight with accountability | [S] |
| **Expression surface** | Lens-routed output (manifesto, feature, scene…) | User-facing meaning | [T] |
| **Trace timeline** | Visual/structural replay of steps | Thought Trace UI | [C] |
| **Curator space** | Inner topology visualization | Inner Space Curator UI | [C] |
| **Cluster map** | Reasoning-topology groups | Community segmentation | [C] |
| **People matching** | Connect by compatible reasoning moves | Network value | [C] |

---

## 4. How primitives map across frameworks

When the same reality appears under different names, use the **unified canonical name** in the ThoughtObject schema:

| Unified (canonical) | MTSF | SDS | ThoughtShape |
|---------------------|------|-----|--------------|
| Field | ThoughtField | Field | Field |
| Entity | IdeaEntity | Entity + Role | Entity |
| StateClaim | Assertion | State + evidence | StateClaim |
| Shape (topology) | Shape | (via movement graph) | Relation topology |
| Stencil | Stencil | MovementArchetype | (via Compare) |
| Frame / Lens | ActivationContext | ObserverLens | Frame + Lens |
| Tension | Contradiction | Constraint / failure mode | Tension |
| Hold / silence | Silence invariant | Low confidence / missing info | Hold |
| Event | Temporal activation | State transition | Event (Tajallī) |
| Expression | Artifact | Intervention text | Expression surface |

**Synthesis target:** ~45 shared ontological primitives → one name each. Framework-specific names become view aliases, not separate stores.

---

## 5. Related documents

| Document | Purpose |
|----------|---------|
| [primitive-catalogue-and-framework-reference.md](./primitive-catalogue-and-framework-reference.md) | Deep reference with examples and architecture detail |
| [framework-primitive-decomposition.md](./framework-primitive-decomposition.md) | Original inventory tables |
| [sources/unified-framework-synthesis.md](../sources/unified-framework-synthesis.md) | Canonical pre-build synthesis |
| [epistemology-and-overlap.md](./epistemology-and-overlap.md) | Epistemic alignment |
| [derived/handoff.md](../derived/handoff.md) | Agent handoff and next actions |
| [../README.md](../README.md) | Workspace entry point |

---

*~120–140 named primitives before deduplication. Rearrangement into one normative unified framework — pending schema lock.*
