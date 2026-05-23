# Glossary

Related docs:

- [README](README.md)
- [Product Scope](01-product-scope.md)
- [Formation Surface Decision Sheet](05-formation-surface-decision-sheet.md)
- [Formation Interpolation Research](06-formation-interpolation-research.md)

This file is the single editable source of truth for Inner World terminology.

If a term in code, docs, UI copy, or planning material conflicts with this
file, this file wins. Future renames should start here first.

## Root model

Inner World treats knowledge as a set of `formations`.

A `formation` is a structured arrangement of micro-entities across multiple
dimensions. Those micro-entities influence one another and respond to external
pressure. The resulting interaction pattern gives the formation its shape.

A formation can become:

- a thought
- a belief
- a plan
- a question
- a strategy
- a scene
- a mood
- an argument

The system should not assume that all meaningful user knowledge is reducible to
`thoughts`. `Thought` is only one possible kind of formation.

## Canonical terms

- `formation`
  - the main ontological unit of meaning in the system
  - a structured whole made from interacting micro-entities
  - also absorbs: `thought`, `idea`, `unit`, `item`
- `entity`
  - a micro-component inside a formation
  - examples: actor, pressure, goal, rule, resource, symbol, boundary
  - also absorbs: `object`, `micro-entity`, `component`, `part`
- `relation`
  - how entities affect one another
  - examples: supports, inhibits, depends_on, amplifies, contradicts
  - also absorbs: `link`, `edge`, `interaction`, `connection`
- `shape`
  - the abstract interaction pattern of a formation
  - the thing that can recur across different domains
  - also absorbs: `topology`, `pattern`, `arrangement`, `profile`
- `mechanism`
  - the operational account of how a formation behaves
  - use when the emphasis is on causal or cybernetic interaction
  - also absorbs: `system logic`, `causal pattern`, `interaction model`
- `primitive`
  - a reusable reasoning kernel or pattern
  - smaller than a full formation; often part of its shape
  - also absorbs: `reasoning primitive`, `shared primitive`, `core primitive`
- `concept`
  - a reusable abstract anchor derived from one or more formations
  - also absorbs: `concept node`, `anchor`, `abstract idea`
- `bubble`
  - a contextual cluster of related formations, concepts, and tensions
  - also absorbs: `cluster`, `context bubble`, `pond` when used as a local grouping term
- `bridge`
  - a meaningful connection between formations, concepts, or bubbles
  - usually highlights transfer or structural resonance
  - also absorbs: `cross-pollination`, `transfer link`, `bridge object` when not worldbuilding-specific
- `counterpoint`
  - an inverse, opposing, or failure-mode relation
  - preferred over `shadow` in product language
  - also absorbs: `shadow`, `anti-example`, `inverse`, `negative match`
- `tension`
  - an unresolved pressure, tradeoff, or instability inside or around a formation
  - also absorbs: `pressure`, `friction`, `tradeoff`, `instability`
- `constraint`
  - a hard or soft boundary that limits how a formation can evolve
  - also absorbs: `guardrail`, `anti-goal`, `boundary`, `non-goal` when used as a limiting rule
- `lens`
  - a perspective or interpretive filter used to read a formation
  - also absorbs: `frame`, `view`, `reading`, `project lens`
- `capsule`
  - a compact semantic payload built for retrieval or runtime use
  - also absorbs: `semantic capsule`, `payload`, `bundle fragment`
- `card`
  - a durable extracted artifact such as a decision, state, or open question
  - also absorbs: `memory card`, `decision card`, `state card`, `question card`
- `thread`
  - a bounded exploration or continuation around a selected formation
  - also absorbs: `conversation thread`, `thought chat`, `discussion thread`
- `source`
  - raw imported material from which formations and other structures are derived
  - also absorbs: `note`, `document`, `file`, `transcript`, `conversation` when referring to raw material
- `snippet`
  - a short evidence fragment taken from a source
  - also absorbs: `excerpt`, `chunk excerpt`, `source fragment`, `clip`
- `feed post`
  - a rendered surface representation of a formation
  - also absorbs: `thought post`, `feed item`, `card` when used informally in old UI planning

## Preferred language

- Use `formation` as the default root noun in product thinking and new docs.
- Use `thought` only when the surface is specifically about a thought-shaped
  formation.
- Use `mechanism` when describing causal interaction, cybernetics, or internal
  system behavior.
- Use `shape` when describing cross-domain similarity or transfer.
- Use `bubble` for contextual grouping. Do not use `bubble` as a synonym for
  `concept` or `formation`.
- Use `card` only for extracted durable artifacts. Do not use `card` as a
  synonym for feed post.

## Terms to avoid

- avoid `object` as a general product noun
- avoid `content` when a more precise word exists
- avoid `shadow`; prefer `counterpoint`
- avoid using `thought`, `concept`, `bubble`, `card`, and `formation`
  interchangeably

## Rename policy

When terminology changes:

1. Update this file first.
2. Preserve the old term as a migration note only if it still appears in code or
   old docs.
3. Prefer changing UI and docs before internal identifiers unless the code term
   is actively causing confusion.
4. Do not introduce a near-synonym if an existing canonical term already fits.

## Epistemic posture

The system should treat formations as inspectable, revisable, and
evidence-bound.

- A formation is inferred from sources; it is not the source itself.
- A shape is provisional unless supported by evidence, recurrence, or explicit
  user confirmation.
- Tensions and contradictions are part of the structure, not cleanup noise.
- The system should preserve uncertainty instead of flattening it into false
  clarity.
