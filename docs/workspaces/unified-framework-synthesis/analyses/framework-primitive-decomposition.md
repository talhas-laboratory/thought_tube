# Framework Primitive Decomposition

**Status:** Pre-synthesis inventory (Jul 2026)  
**Next step:** Rearrange into one unified framework

Full decomposition of MTSF, SDS, ThoughtShape, and chat additions into atomic parts before synthesis.

---

## Inventory summary

| Source | Unique pieces | Shared primitives |
|--------|---------------|-------------------|
| MTSF | ~25 | ~45 mappable |
| SDS | ~20 | ~45 mappable |
| ThoughtShape | ~18 | ~45 mappable |
| Chat additions | ~10 | — |
| **Total** | **~120–140 named pieces** | before deduplication |

---

## A. Ontological primitives

### Shared (≈45 mapped across names)

| Universal | MTSF | SDS | ThoughtShape |
|-----------|------|-----|--------------|
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

### MTSF-only ontological

| Primitive | Description |
|-----------|-------------|
| ThoughtField | Pre-material activation zone with temporal trace |
| IdeaEntity | Identity + qualities + relations + intensity + temporal_state |
| SubEntity | Typed recursive nested carrier |
| QualityRegion | 10 quality types as navigable regions |
| QualityRole | Governing categorical operator on qualities |
| Assertion | Evidence-backed qualified claim in assertion store |
| EvidenceSpan | Text span backing an assertion |

### SDS-only ontological

| Primitive | Description |
|-----------|-------------|
| Role | Functional position in system (not identity) |
| State | Typed node value with evidence |
| Constraint | Hard limit on transition |
| Signal | Observable system output |
| Receiver | Target of signal / effect |
| Bottleneck | Rate-limiting node |
| Observer | Constitutive extraction stance |
| Goal | Explicit system objective |
| Missing information | Flagged absence in extraction |

### ThoughtShape-only ontological

| Primitive | Description |
|-----------|-------------|
| Dimension | First-class meaning layer (psychological, brand, financial…) |
| Station | Possibility-space where meaning varies (recognition, trust…) |
| Facet | Aspect within station×dimension |
| StateClaim | state + weight + salience + valence + confidence + evidence |
| CrossDimensionalRelation | Relation across dimensions (core shape mechanism) |
| TemporalContour | How meaning evolves over time |
| ExpressionSurface | Output routing target per lens |

### Chat-only ontological

| Primitive | Surface |
|-----------|---------|
| ReasoningStep | Thought Trace atomic unit |
| ReasoningMove | ground, triangulate, bridge, formalize, invert… |
| ReasoningTrace | Ordered chain of ReasoningSteps |
| ReasoningSignature | Person-level reasoning topology |
| HoldRecord | Capture-time hold state persistence |
| PlacedFragment | Inner Space Curator placed content |
| Cluster | Reasoning-topology group |
| ClusterLane | Product variant per cluster |
| MimicProfile | Bot interrogation style per person |

---

## B. Structural composites

### MTSF composites

| Composite | Description |
|-----------|-------------|
| Shape | Selected qualities + relation configuration + intensity + context + time |
| CandidateShape | Provisional shape from discovery (no pre-known template) |
| Stencil | Abstract pattern projection of full shape |
| ShapeInstance | Live binding of shape to entity/context |
| ProblemShape | Problem signal structured for analogical match |
| ActivationSnapshot | Point-in-time activation state |
| Subgraph | Extracted graph fragment (layers 0–4) |
| Artifact | Externalized actualization output |

### SDS composites

| Composite | Description |
|-----------|-------------|
| System-Dynamic Signature | Full typed graph of entities, states, relations, loops |
| FeedbackLoop | Circular causal chain |
| MovementSignature | Extracted transformation pattern |
| MovementArchetype | Library-stored abstract movement |
| TransferLedger | Record of cross-domain transfer attempts |
| AntiMatch | Explicit rejected analogy |
| InterventionPattern | Actionable intervention from source domain |

### ThoughtShape composites

| Composite | Description |
|-----------|-------------|
| ThoughtShape | Full multidimensional meaning configuration |
| Projection | Station × Dimension → localized meaning |
| LensView | Same shape accessed through lens catalog |
| ExpressionBundle | Lens-routed output package |

### Chat composites

| Composite | Description |
|-----------|-------------|
| ThoughtObject | Unified kernel object (pending schema lock) |
| CaptureSession | Drop→Hold→Trace sequence |
| CuratorSpace | Inner topology of placed fragments |
| CommunityFlywheel | Social→mimic→signature→cluster pipeline |

---

## C. Relations and dynamics

### MTSF relations (22 primitives, 4 levels)

Levels: entity, quality, artifact, meta.

Relation families: structural, causal, associative, hierarchical, temporal, cross-register.

Key primitives: `contains`, `part_of`, `causes`, `enables`, `contradicts`, `analogous_to`, `activates`, `precedes`, `co_occurs`, `bridges_register`, etc.

### SDS edges (10 types)

`causes`, `amplifies`, `inhibits`, `depends_on`, `transforms_into`, `competes_with`, `enables`, `constrains`, `delays`, `feeds_back_into`

### SDS movement primitives (18)

`accumulate`, `decompose`, `recombine`, `translate`, `constrain`, `release`, `amplify`, `dampen`, `delay`, `invert`, `filter`, `stabilize`, `destabilize`, `differentiate`, `integrate`, `externalize`, `internalize`, (+ composite patterns)

### ThoughtShape relations

- Directional influence between StateClaims
- Cross-dimensional relations (not necessarily causal)
- Tension as unresolved relation pressure

### Chat dynamics

| Dynamic | Description |
|---------|-------------|
| prompted_by | ReasoningStep link to prior step(s) |
| move_type | extends, revises, contrasts, grounds, bridges |
| revisitation | Curator evidence of gravity |
| cluster_affinity | Signature distance for grouping |

---

## D. Patterns and abstractions

| Level | MTSF | SDS | ThoughtShape |
|-------|------|-----|--------------|
| Abstract pattern | Stencil | MovementArchetype | Relation topology |
| Match surface | Shape index | Transfer ledger | Compare operation |
| False match guard | Quarantine tier | AntiMatch library | (via SDS overlay) |
| Problem pattern | ProblemShape | Failure mode archetype | Tension pattern |
| User pattern memory | Session/global graph | 4-tier living library | Lens history |

### Named pattern examples (shared intent)

- `surface-without-depth` / `signal_without_semantics` / high-logo + low-meaning
- `metaphysical-actual-bridge` / `translation_failure` / cross-dim bridge
- `dilution_through_accumulation` / shape drift / facet spread without integration

---

## E. Epistemic machinery

| Machinery | MTSF | SDS | ThoughtShape |
|-----------|------|-----|--------------|
| Evidence model | Assertion + span | State + span | StateClaim evidence |
| Confidence | Quarantine tiers | Coverage score | confidence field |
| Valid silence | Invariant #12 | Missing info flag | Hold operation |
| Contradiction policy | May remain unresolved | Failure mode node | Tension preserved |
| Provenance chain | Assertion store | Transfer ledger | Update trail |
| Validation | Schema + ontology + evals | 5-layer hybrid evaluator | Lens fidelity rubric |
| Anti-premature structure | Fast/deep modes | Abstraction levels | Hold + progressive depth |

### SDS 5-layer evaluator

1. Structural alignment
2. Causal coherence
3. Boundary fit
4. Observer lens consistency
5. Transfer ledger / anti-match check

### MTSF eval suite

13 gap-closure evals (G01–G13): embeddings, adjacency, cross-register bridge, cluster shapes, hallway extract, pair discrimination, topology candidates, fuzzy stencil merge, inferred shapes, live extraction, utility bar, cross-session discovery, downstream hooks.

---

## F. Interpretive machinery

| Machinery | MTSF | SDS | ThoughtShape |
|-----------|------|-----|--------------|
| Extraction stance | ActivationContext | ObserverLens (constitutive) | Frame |
| Lens catalog | (none predefined) | (none) | 7 lenses (Founder, Product, Risk, Financial, Story, Visual, Brand) |
| Lens affects extraction | Partial | Yes | Yes |
| Lens affects output | No | No (analogy separate) | Yes (core) |
| Identity reduction | reduce_identity() | Role remapping | Station×Dimension projection |
| Progressive resolution | Fast → deep | Abstraction levels 1–6 | Levels 1–6 explicit |

### ThoughtShape lens routing

Each lens activates dimensions/stations/facets and routes to expression surfaces (manifesto, feature, mitigation, unit-economics, scene, moodboard, positioning).

---

## G. Operations

### MTSF operations

`capture`, `populate`, `extract`, `discover`, `project`, `activate`, `actualize`, `promote`, `expand`, `follow`, `reduce_identity`, `merge_stencil`

### SDS operations

`extract_signature`, `match_archetype`, `generate_analogy`, `evaluate_transfer`, `record_anti_match`, `propose_intervention`, `update_library`

### ThoughtShape operations

`Capture` → `Hold` → `Differentiate` → `Shape` → `Locate` → `Compare` → `Transform` → `Express` → `Evaluate` → `Update`

### Chat operations

| Operation | Surface |
|-----------|---------|
| Drop | Thought Trace intake |
| Hold | Preserve ambiguity |
| Trace | Link reasoning steps |
| Mirror | Reflect back to user |
| Prompt | Next reasoning-tuned question |
| Place / Tend / Revisit / Release / Compose | Inner Space Curator |
| Mimic | Waitlist bot interrogation |
| Cluster | Assign signature to topology group |
| Connect | Match compatible reasoning moves |

---

## H. Spaces and layers

### MTSF spaces

| Space | Role |
|-------|------|
| Metaphysical | Pre-formed possibility |
| Latent | Operational bridge (embeddings, transformers) — **not** metaphysical |
| Actual | Artifacts and externalized outputs |

Graph layers 0–4: events, session graph, content graph, global graph, meta graph.

Pipeline layers: ingest → extraction → validation → projection → progressive graph → activation → discovery → actualization.

### SDS layers (4 tiers)

1. LLM extraction → typed graph
2. Analogy generation
3. Evaluation
4. Living library (user-validated archetypes)

### ThoughtShape layers

Field → Entity → Dimension → Station → Facet/Subsystem → StateClaim → Relation → Event → Expression

### Chat stack layers (product)

```text
NETWORK     Community pipeline
SURFACES    Thought Trace + Inner Space Curator
GRAMMAR     ThoughtShape
OVERLAY     SDS (on demand)
SUBSTRATE   MTSF
```

---

## I. Invariants

### MTSF (13)

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

### SDS

- Observer lens is constitutive
- Non-movement is first-class
- Anti-matches required for safe transfer
- Structural alignment beats semantic similarity

### ThoughtShape

- Thought is not a sentence
- Thought is not flat
- Stations project across dimensions
- Hold before Differentiate
- Same shape, multiple lens outputs

### Chat / unified

- One ontology, three views — not three stores
- Synthesize before building surfaces
- ReasoningStep is atomic capture unit
- Mimic style, not content

---

## J. Outputs

| Output | MTSF | SDS | ThoughtShape | Chat |
|--------|------|-----|--------------|------|
| Persistent memory | Assertion store, content graph | Living library tiers | Update trail | Session + signature |
| Discovery | CandidateShape, shape index | Archetype match | Compare retrieval | Cluster map |
| Artifact | Actualization output | Intervention pattern | Expression surface | Product lane |
| Analogy | Quarantined analogical_match | Transfer + anti-match | (via SDS overlay) | — |
| User-facing | (thin) | Intervention text | Lens-routed expression | Trace timeline, curator space |
| Network | — | — | — | People matching by reasoning topology |

---

## K. Philosophical commitments

| Tradition | MTSF | SDS | ThoughtShape |
|-----------|------|-----|--------------|
| Aristotle (potentiality/actuality) | Strong (3 spaces) | Strong (states/transitions) | Implicit |
| Kant (schematism) | Stencil projection | **Primary** (archetype) | Frame |
| Gentner (structure mapping) | Stencil match | **Primary** | Compare |
| Cybernetics / Meadows | Thin | **Core** (feedback loops) | Cross-dim chains |
| Maqām / Ḥāl / Tajallī | Partial | Partial | **Root** (Station/StateClaim/Event) |
| Gendlin (felt sense) | Silence invariant | Weak | **Hold** |
| VSM / systems thinking | Module nesting | Recursive system boundary | Subsystem expansion |

### Shared epistemological commitments

- Meaning is relational, not atomistic
- Pre-explicit thought is real
- Context localizes meaning
- Provenance mandatory
- Ambiguity can remain
- Cross-domain insight is structural
- Progressive depth — do not over-structure early

### Divergent epistemic bets

| Question | MTSF | SDS | ThoughtShape |
|----------|------|-----|--------------|
| Primary unit of truth | Shape/stencil | Movement signature | StateClaim topology |
| Latent space real? | No (bridge only) | Metaphor only | Not addressed |
| What validates match? | Stencil + utility eval | 5-layer + transfer ledger | Lens fidelity |
| Observer role | Secondary | Constitutive | Constitutive |
| Main failure mode | Over-structure | False analogy | Flatten dimensions |

---

## Overlap map (same thing, different names)

| Universal | MTSF | SDS | ThoughtShape |
|-----------|------|-----|--------------|
| Pre-clear zone | ThoughtField | Field | Field |
| Carrier | Entity | Entity+Role | Entity |
| Qualified claim | Assertion | State+evidence | StateClaim |
| Abstract pattern | Stencil | MovementArchetype | Relation topology |
| Interpretive stance | ActivationContext | ObserverLens | Frame+Lens |
| Unresolved pressure | Contradiction | Constraint/failure | Tension |
| Valid silence | Silence invariant | Low confidence | Hold |
| Change | Temporal activation | State transition | Event |
| Output | Artifact | Intervention | Expression |

---

## Primitives unique to one framework

**MTSF only:** metaphysical/latent/actual spaces, wormholes, promotion gates, discovery without template, reduce_identity(), 13 gap evals, assertion store, content graph layers

**SDS only:** transfer ledger, anti-matches, 5-layer evaluator, system boundary, movement primitive vocabulary (18), living library tiers, non-movement problem

**ThoughtShape only:** Dimension, Station×Facet formula, lens catalog (7), valence, Hold operation, cross-dimensional relation as core, expression routing

**Chat only:** ReasoningStep, ReasoningSignature, Cluster, mimic questioning, PlacedFragment, CuratorSpace, CommunityFlywheel

---

## Not yet done

Rearrangement into **one unified framework** with single ontology, pipeline, and schema — pending next step.

See also:

- [epistemology-and-overlap.md](./epistemology-and-overlap.md)
- [fresh-comparison-jul-10.md](./fresh-comparison-jul-10.md)
- [sds-non-movement-problem.md](./sds-non-movement-problem.md)
- [sources/three-framework-comparative-evaluation.md](../sources/three-framework-comparative-evaluation.md)
- [sources/unified-framework-synthesis.md](../sources/unified-framework-synthesis.md)
