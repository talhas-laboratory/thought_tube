# Formation Interpolation Research

Related docs:

- [README](README.md)
- [Glossary](02-glossary.md)
- [Formation Surface Decision Sheet](05-formation-surface-decision-sheet.md)

## Purpose

This report surveys literature-backed techniques for the background
`subconscious` layer: the part of the system that should interpolate across
formations and entities, surface cross-pollinations, and propose new candidate
conclusions before the feed renders anything for the user.

The question is not only `how do we find similar things?` but also:

- how do we retrieve structurally relevant formations
- how do we align their internal roles
- how do we generate a useful synthesis
- how do we use tension, contradiction, and asymmetry as productive signals
- how do we control this process so it does not become noisy or ornamental

## Executive summary

The literature does not point to one magic interpolation method. It points to a
stack.

The strongest overall pattern is:

1. retrieve candidate formations cheaply
2. align them by relational structure, not just surface meaning
3. induce an abstract schema or shared shape
4. generate a blend, adaptation, or explanatory hypothesis
5. test it against tensions, contradictions, and evidence
6. retain only compact, inspectable outputs

The most useful additions beyond the already discussed `isomorphic shape
matching` and `antisymmetric pattern finding` are:

- two-stage analogical retrieval
- schema induction from multiple analogs
- case-based adaptation
- frame-slot completion
- conceptual metaphor transfer
- conceptual combination by thematic relation
- contradiction-driven synthesis
- abductive hypothesis generation
- role-based similarity
- motif discovery over formation graphs

Not every item below is a direct generation technique. Some are control
principles for managing search breadth, compression, and noise.

## Technique families

### 1. Structure mapping

Core idea:
- match formations by the relations among entities, not by surface similarity

Why it matters:
- this is the cleanest theoretical basis for `isomorphic shape matching`
- it supports role alignment, transfer, and inference projection

What it adds:
- entity-to-entity correspondence by role
- structure-preserving bridge generation
- transfer of causal or relational patterns across domains

Relevant warning:
- pure structural matching can produce elegant but irrelevant analogies if
  purpose and context are not used as constraints

Sources:
- Dedre Gentner's structure-mapping theory
- the Structure-Mapping Engine description by Falkenhainer, Forbus, and Gentner

### 2. Two-stage analogical retrieval

Core idea:
- use a cheap first-pass retrieval to gather many approximate candidates, then a
  second structural pass to select the few that truly match

Why it matters:
- this is likely the most practical background retrieval policy for the system
- it avoids expensive structural comparison against the full knowledge ocean

What it adds:
- fast broad candidate recall
- deeper structural reranking only on shortlisted formations
- a principled separation between semantic nearness and structural relevance

Repo relevance:
- this is a strong fit for a future `retrieve broadly, verify structurally`
  bridge in `conversation_synthesis`

Source:
- Forbus and Gentner's `MAC/FAC` model of similarity-based retrieval

### 3. Schema induction from multiple analogs

Core idea:
- compare two or more analogous cases to induce a more abstract shared schema

Why it matters:
- this is one of the cleanest mechanisms for discovering a reusable `shape`
  rather than merely spotting a pairwise similarity
- it suggests that the system should compare clusters of formations, not just
  pairs

What it adds:
- generalized patterns from repeated local matches
- stronger abstraction when multiple examples support the same shape
- better transfer than single-example analogies

Key implication:
- the system should sometimes synthesize over `triplets` or `small sets`, not
  only dyads

Source:
- Gick and Holyoak on schema induction and analogical transfer

### 4. Conceptual blending

Core idea:
- selectively project structure from two or more inputs into a new blended space
  with emergent structure of its own

Why it matters:
- this is one of the best theories for actual `pollination`
- unlike strict analogy, blending allows the result to be genuinely novel
  rather than only transferred

What it adds:
- double-scope synthesis
- emergent structure
- projection plus compression
- generation of a new formation, not just a bridge

Important detail:
- Fauconnier and Turner explicitly describe emergent structure as arising
  through `composition`, `pattern completion`, and `elaboration`

Source:
- Fauconnier and Turner on conceptual integration and blending

### 5. Case-based reasoning

Core idea:
- retrieve a prior case, reuse part of its solution pattern, revise it to fit the
  new context, then retain the improved case

Why it matters:
- this turns cross-pollination into an iterative memory loop rather than a
  one-off insight generator

What it adds:
- adaptation, not just retrieval
- revision after testing
- retention of improved transformations

Strong use case:
- when the system finds a structurally similar formation that already led to a
  decision, insight, or question pattern

Source:
- Kolodner and later CBR overviews organized around `retrieve`, `reuse`,
  `revise`, `retain`

### 6. Frame-slot completion

Core idea:
- represent familiar situations as frames with expected roles, defaults, and
  attachable local variations

Why it matters:
- many formations will be sparse, partial, or under-specified
- frame logic gives the system a disciplined way to infer missing roles without
  pretending the inference is certain

What it adds:
- role expectations
- default completion
- compatibility checks for added entities
- local variation attached to a more stable global structure

Strong use case:
- filling in likely missing entity roles in a formation packet before matching
  it

Source:
- Minsky's `A Framework for Representing Knowledge`

### 7. Conceptual metaphor transfer

Core idea:
- understand one domain in terms of another, especially when the source domain
  provides a stronger inferential structure

Why it matters:
- this is a disciplined version of cross-domain transfer
- it explains how abstract formations can borrow structure from concrete,
  embodied, or spatial domains

What it adds:
- transfer from spatial, object, motion, and force structures into abstract
  reasoning
- a reusable way to enrich under-specified formations with stronger structural
  language

Risk:
- metaphor can over-shape reasoning if treated as truth instead of lens

Source:
- Lakoff and Johnson on the metaphorical structure of the human conceptual
  system

### 8. Spreading activation

Core idea:
- activate a seed set of concepts or entities and let activation spread through
  a semantic or relational network

Why it matters:
- this is a good model for the background `drift` or `subconscious adjacency`
  layer
- it can surface distant candidates the user did not explicitly query

What it adds:
- associative recall
- soft discovery of nearby regions
- graded relevance rather than binary matching

Good constraint:
- the spread should be query- or tension-constrained, not global and naive

Source:
- Collins and Loftus on spreading activation

### 9. Remote association and bisociation

Core idea:
- creativity emerges when previously separate associative elements or frames are
  linked into a useful new combination

Why it matters:
- this is one of the oldest direct accounts of `aha` generation
- it supports deliberate search for distant but productive co-activation

What it adds:
- remote associative recall
- bridging between unrelated matrices
- novelty from non-obvious co-occurrence

Useful distinction:
- `association` gives proximity
- `bisociation` gives collision between previously separate frames

Sources:
- Mednick on the associative basis of the creative process
- Koestler on bisociation in `The Act of Creation`

### 10. Conceptual combination

Core idea:
- create a new concept by combining two concepts through a relation, a property
  transfer, or a hybrid merge

Why it matters:
- this is more local and compositional than full conceptual blending
- it is useful for turning small entity pairs into compact feed-worthy
  formulations

What it adds:
- thematic relation binding
- property transfer
- hybrid formation creation

Strong use case:
- combining a modifier formation and a head formation into a compact new
  expression

Sources:
- Wisniewski on how concepts combine
- Gagne and Shoben's `CARIN` relation-selection account

### 11. Contradiction-driven synthesis

Core idea:
- treat conflict, trade-off, or opposition as the engine of invention, then
  search for transformations that remove or reframe the contradiction

Why it matters:
- this is the best formal ancestor for the `counterpoint` and `tension` parts
  of the ontology
- it makes `antisymmetric pattern finding` operational instead of poetic

What it adds:
- contradiction extraction
- inversion and separation moves
- systematic generation of alternative structures

Important nuance:
- TRIZ is domain-specific in origin, but the core move of abstracting a conflict
  and searching a library of resolution patterns generalizes well

Sources:
- Altshuller's contradiction work and the `40 Principles`

### 12. Abductive hypothesis generation

Core idea:
- start from surprising or unresolved facts and generate a plausible explanatory
  hypothesis

Why it matters:
- many useful feed posts should not just connect formations; they should offer a
  possible explanation for why the connection matters

What it adds:
- explanatory candidate generation
- pressure toward coherent hypothesis formation
- a way to turn anomalies and tensions into provisional insights

Best use:
- after matching or blending has already produced an interesting but unresolved
  relation

Source:
- Peirce on abduction as studying facts and devising a theory to explain them

### 13. Role-based similarity

Core idea:
- two entities can be similar because they occupy similar roles in different
  local structures, even if they are not connected to the same neighbors

Why it matters:
- this is more flexible than direct overlap
- it is extremely useful for entity-level interpolation across distant
  formations

What it adds:
- structural role matching
- looser equivalence classes
- better long-range bridge discovery

Strong use case:
- matching `gatekeeper`, `buffer`, `catalyst`, or `bottleneck` entities across
  otherwise unrelated formations

Sources:
- regular equivalence and later role-similarity work

### 14. Motif discovery

Core idea:
- detect small recurrent substructures that appear more often than expected

Why it matters:
- motifs give a compact library of micro-shapes that can be tracked across the
  ocean
- this is a good bridge between graph structure and formation shape

What it adds:
- reusable micro-patterns
- frequency-based discovery of canonical interaction shapes
- better grounding for `primitive` and `mechanism` discovery

Risk:
- frequency alone is not enough; some motifs are common because of graph growth
  mechanics, not because they are meaningful

Sources:
- Milo and colleagues on network motifs
- later critiques that motifs are informative but not automatically independent
  functional units

### 15. Approximate graph matching

Core idea:
- compare substructures even when they are not perfectly isomorphic

Why it matters:
- real formations will almost never line up exactly
- the system needs graded structural similarity, not exact symbolic equality

What it adds:
- inexact matching
- tolerance for missing or extra entities
- scoring for near-isomorphism

Typical implementations:
- subgraph isomorphism search
- graph edit distance
- role-aware or partition-aware matching

Sources:
- Ullmann on subgraph isomorphism
- later graph-edit-distance work

### 16. Pattern-language recombination

Core idea:
- represent recurring resolutions to recurring conflicts as named patterns that
  can be recombined into larger wholes

Why it matters:
- this is a powerful way to make the system's recurring `solutions` legible
- it is especially useful once the system begins to accumulate repeated
  high-quality formation outputs

What it adds:
- reusable named patterns
- composition of local resolutions into larger structures
- a vocabulary for stable good solutions under recurring forces

Source:
- Christopher Alexander's `A Pattern Language`

## Control principles rather than direct generators

### 17. Requisite variety

Core idea:
- the regulator must have at least enough variety to handle the variety in what
  it is trying to regulate

Why it matters here:
- the interpolation system should widen search when the formation space is rich
  and ambiguous, and narrow it when the task is clear
- this is a control principle for search breadth, not a synthesis operator

Source:
- W. Ross Ashby on requisite variety

### 18. Variety attenuation and amplification

Core idea:
- a viable system alternates between broadening available options and
  compressing them into manageable forms

Why it matters here:
- the subconscious layer should expand candidate space, then contract it into a
  few feed-worthy outputs

Source:
- Stafford Beer and management cybernetics

## What the literature suggests for this system

The literature strongly suggests that the background layer should not be built
as one giant `semantic similarity` pass.

It should be a multi-step synthesis loop:

1. use `spreading activation`, cheap semantic retrieval, and role cues to gather
   candidates
2. use `structure mapping`, `regular equivalence`, and approximate graph
   matching to verify shape alignment
3. use `schema induction` to extract a shared abstract shape when multiple
   examples support it
4. use `conceptual blending`, `conceptual combination`, `case adaptation`, or
   `abduction` to generate a candidate conclusion
5. use `contradiction-driven` checks to test whether the candidate survives
   counterpoint and tension
6. use `pattern-language` and `motif` libraries to compress recurring good
   outputs into reusable primitives

## Most promising shortlist

If we prioritize only the strongest candidates for early system design, the
shortlist is:

- `two-stage analogical retrieval`
- `structure mapping`
- `schema induction`
- `conceptual blending`
- `case-based reasoning`
- `contradiction-driven synthesis`
- `abductive hypothesis generation`
- `role-based similarity`
- `motif discovery`
- `approximate graph matching`

Secondary but still valuable:

- `conceptual metaphor transfer`
- `frame-slot completion`
- `conceptual combination`
- `spreading activation`
- `pattern-language recombination`

Control layer:

- `requisite variety`
- `variety attenuation / amplification`

## Bottom line

The best reading of the literature is that `subconscious` synthesis should be a
stacked system with different operators for:

- retrieval
- alignment
- abstraction
- generation
- contradiction testing
- compression

The biggest mistake would be to reduce the whole problem to embeddings alone.
The literature consistently points toward a mixed architecture where structural
matching, abstraction, blending, contradiction, and adaptive control each play
a different role.

## Sources

- [Dedre Gentner, structure mapping via the Structure-Mapping Engine summary PDF](https://groups.psych.northwestern.edu/gentner/papers/FalkenhainerGentner86.pdf)
- [Forbus and Gentner, `MAC/FAC: A Model of Similarity-based Retrieval`](https://www.sciencedirect.com/science/article/pii/0364021395900160)
- [Gick and Holyoak, `Schema induction and analogical transfer`](https://deepblue.lib.umich.edu/items/196ea13e-fb69-4a74-a6f9-864c81aed465)
- [Fauconnier and Turner, `Conceptual Integration and Formal Expression`](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1650417)
- [Fauconnier and Turner, `Conceptual Blending, Form and Meaning` PDF](https://tecfa.unige.ch/tecfa/maltt/cofor-1/textes/Fauconnier-Turner03.pdf)
- [Lakoff and Johnson, `The Metaphorical Structure of the Human Conceptual System` PDF](https://opessoa.fflch.usp.br/sites/opessoa.fflch.usp.br/files/Lakoff-Johnson-Metaphorical-Structure.pdf)
- [Minsky, `A Framework for Representing Knowledge` PDF](https://www.plexusinternational.org/files/download/minsky%201974%20framework%20for%20knowledge.pdf)
- [Case-based reasoning overview and the `retrieve, reuse, revise, retain` cycle](https://www.cambridge.org/core/journals/knowledge-engineering-review/article/abs/retrieval-reuse-revision-and-retention-in-casebased-reasoning/832332507628AE30DB2486FD75651C7A)
- [Mednick, `The associative basis of the creative process`](https://www.researchgate.net/publication/9116359_The_Associative_Basis_of_the_Creative_Process)
- [Koestler, `The Act of Creation` overview](https://books.google.com/books/about/The_Act_of_Creation.html?id=tJC5pDXFY8oC)
- [Wisniewski, `When Concepts Combine`](https://www.mendeley.com/catalogue/4abf46b8-d908-3967-a7e8-8e0c45995c0f/)
- [Gagne and Shoben via `CARIN` summary](https://pmc.ncbi.nlm.nih.gov/articles/PMC1284915/)
- [Collins and Loftus spreading activation summary](https://www.cognitivepsychology.com/Spreading_Activation)
- [Altshuller `40 Principles` overview](https://triz.org/principles/)
- [Network motifs literature summary and original line of work](https://explorer.bee.oregonstate.edu/Topic/InfluenceNetworks/Documents/NetworkMotifsSimpleBuildingBlocks.pdf)
- [Regular equivalence for role-based similarity](https://www.mdpi.com/2076-3417/9/1/117)
- [Ullmann on subgraph isomorphism](https://explorer.cs.umn.edu/subgraph/p31-ullmann.pdf)
- [Christopher Alexander, `A Pattern Language`](https://www.patternlanguage.com/bookstore/pattern-language.html)
- [Ashby on requisite variety](https://ashby.info/Ashby-Mechanisms_of_intelligence.pdf)
- [Stafford Beer background reference](https://www.nature.com/articles/222395c0)
