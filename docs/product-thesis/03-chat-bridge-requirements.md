# Chat Bridge Requirements

Related docs:

- [README](README.md)
- [Glossary](02-glossary.md)
- [OpenClaw Conversation Synthesis](04-openclaw-conversation-synthesis.md)

## Purpose

The chat bridge layer is a thin runtime layer between live conversation and the
existing Inner World knowledge system.

It exists to:

- improve continuity across turns
- categorize messy input in context
- individualize output to the current user and moment
- reduce capture friction
- preserve trust through explicit confidence, review, and correction paths

It should extend the existing Inner World layers. It should not replace the
knowledge layer, meta-layer, context bubbles, or judged-thought pipeline.

## Product outcomes

The bridge layer should produce these user-visible outcomes:

- the user repeats context less often
- vague references like `this` or `that` resolve more accurately
- chat answers are less generic and more personally useful
- capture-worthy fragments become provisional memory without heavy packaging
- the system remains fast enough to use in normal conversation
- the user can see, correct, discard, or promote system interpretations

## Core principles

- Use the existing knowledge ocean as a source of context, not as a per-turn
  compute obligation.
- Keep live chat state ephemeral by default.
- Promote into durable memory only through explicit or high-confidence
  reviewable paths.
- Separate fast per-turn regulation from slower deep processing.
- Prefer adaptive depth over maximum depth.
- Fail conservatively when context is weak, stale, or conflicting.

## Required runtime layers

Every chat turn may draw from these layers, in this order:

1. current turn
2. recent conversation window
3. working context
4. current thread or session context
5. relevant context bubble or pond
6. semantic capsules
7. meta-layer records
8. source evidence
9. durable interaction profile

The bridge must not pull every layer deeply on every turn. It must retrieve the
smallest useful bundle for the current task.

## Required bridge capabilities

The bridge layer must provide:

1. `working context`
   - track active topic, active question, active tension, unresolved references,
     current mode, and open capture candidates
2. `adaptive context depth`
   - choose between focused, contextual, and deep retrieval depending on the
     turn and current confidence
3. `input categorization`
   - classify each turn by intent, content type, durability, and confidence
4. `output personalization`
   - shape answer style, initiative, and follow-up behavior using current mode
     plus learned user preferences
5. `provisional capture`
   - create lightweight interpretation cards for capture-worthy fragments before
     durable promotion
6. `learning boundaries`
   - separate session-local adaptation from durable preference learning
7. `inspectability`
   - record which layers influenced the answer and why
8. `fallback behavior`
   - degrade to focused mode when context quality is low or retrieval exceeds
     budget

## User-facing controls

The bridge should expose behavior controls, not implementation controls.

Required modes:

- `Focused`
  - use only the current conversation unless the user asks for more
- `Contextual`
  - use related memory when it materially improves continuity or relevance
- `Deep`
  - search broader Inner World memory and reasoning layers
- `Incognito`
  - do not save, learn, or promote from the exchange

Default mode should be `Contextual`.

## Efficiency requirements

The bridge must enforce a per-turn context budget:

- maximum retrieval depth
- maximum capsule count
- maximum source snippet count
- maximum latency overhead
- maximum token budget before the answer backend runs

Default chat must stay lightweight. When the budget is exceeded, the bridge
must reduce depth before it delays the answer.

Deep retrieval, full meta extraction, graph updates, and durable learning
rebuilds belong to the cold path, not the hot path.

## Reliability requirements

The bridge must emit explicit context switch events whenever active topic,
intent, depth, or memory scope changes.

Each context switch must record:

- previous state
- new state
- trigger
- confidence
- retrieval sources
- rollback path

The bridge must also:

- score staleness for reused context
- avoid durable capture on low confidence
- distinguish inferred meaning from quoted user language
- preserve raw source text separately from normalized interpretation
- allow correction, discard, merge, and promotion actions

## Learning requirements

The bridge should learn in two tiers:

- `session-local adaptation`
  - temporary adjustments for the current thread or session
- `durable user learning`
  - stable preferences and interaction patterns learned only from repeated
    evidence, explicit feedback, or consistent corrections

One-off behavior should not immediately rewrite the durable user model.

## Suggested bridge state

The bridge layer should maintain small, inspectable runtime artifacts such as:

- `working_context.json`
- `context_switch_events.jsonl`
- `capture_candidates.jsonl`
- `interaction_profile.json`
- `bridge_runtime.json`

These artifacts are runtime surfaces for chat regulation. They are not a second
knowledge ocean.

## Acceptance criteria

The bridge layer is successful only if it improves both directions:

- `categorization quality`
  - better intent and meaning assignment for ambiguous turns
- `answer quality`
  - more continuity, less repetition, better personalization
- `capture quality`
  - more useful provisional captures with less user packaging
- `trust quality`
  - clearer confidence, provenance, and correction surfaces
- `runtime quality`
  - normal chat remains fast and predictable

## Evaluation standard

The bridge must be evaluated with scripted conversations that include:

- topic shifts
- ambiguous references
- corrections
- interruptions
- privacy-sensitive turns
- capture-worthy fragments
- false-memory temptations
- deep-context requests

The system should only expand beyond v1 once these evaluations show that the
user explains less while receiving more relevant, more trustworthy responses.
