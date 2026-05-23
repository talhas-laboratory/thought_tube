# Bounded OpenClaw Semantic Assist Architecture

## Purpose

This document explains the bounded OpenClaw semantic assist layer now wired into Inner World.

The goal is to raise user-visible semantic quality without turning the full-library derive path into an LLM-driven system.

The specific product effect is:

- better surfaced bubble labels
- better surfaced thought titles and short texts
- fewer generic fallback phrases like `Something in X...` or `X keeps leaning toward Y`
- no uncontrolled token burn across large libraries

This architecture deliberately does **not** use model calls inside the heavy deterministic graph-building stages.

## Core Design Decision

Inner World now uses a split architecture:

- `deterministic substrate + derive`
  - chunk normalization
  - meta layer extraction
  - thread abstractions
  - context bubbles
  - knowledge edges
  - promotion candidate generation

- `bounded semantic assist`
  - only for a very small number of surfaced artifacts after deterministic derivation has already completed

This is the central rule:

`models may improve surface semantics, but they do not control the core library graph build`

That rule preserves:

- rebuild stability
- inspectability
- governance and pruning behavior
- predictable cost on large corpora

## Why This Placement

The current system's main weakness is not substrate storage anymore. The main weakness is semantic quality at the surfaced layer.

The deterministic system is already strong at:

- ingesting and governing sources
- cleaning runtime conversation text
- building reproducible graph artifacts
- selective rederive

But it is still weak at:

- naming generic or conceptless bubbles well
- turning weak promotion candidates into clearly human-readable surfaced thoughts
- rejecting generic but technically valid surfaced candidates

So the model layer is inserted exactly where semantic interpretation matters most and computational load is smallest:

1. after bubbles already exist
2. after promotion rows already exist

It is **not** inserted into:

- chunk ingestion
- meta-layer extraction
- bubble clustering
- edge building
- full graph generation

## Current Owner Modules

The bounded semantic assist lives in these owner modules:

- [context_bubbles.py](/Users/talhauddin/software/inner_space/src/conversation_os/context_bubbles.py)
- [thought_factory.py](/Users/talhauddin/software/inner_space/src/conversation_os/thought_factory.py)

OpenClaw model invocation is performed through direct `openclaw agent ... --json` calls inside those owners.

Supporting existing runtime configuration is read from:

- [runtime.json](/Users/talhauddin/software/inner_space/product/inner_world_v1/config/runtime.json)

## Bubble Assist

### Scope

Bubble assist only runs on a very small top set of bubbles that are likely user-visible and still semantically weak.

Candidate signals include:

- no `primary_concept_id`
- generic or weak label
- generic thesis
- enough support to be worth salvaging

### Timing

Bubble assist runs **after**:

- seed selection
- related attachment
- duplicate-label merge
- pruning
- final bubble object creation
- edge construction

So the bubble structure, membership, and graph relationships stay deterministic.

Only the final visible label can be improved.

### Effect

For selected bubbles:

- the existing label is preserved as `raw_label`
- the model may write a better `semantic_label`
- the bubble's user-visible `label` is replaced with the improved semantic label
- the assist payload is stored in `semantic_assist`

If the assist fails, times out, or produces junk:

- nothing breaks
- the raw deterministic bubble label remains

## Thought Assist

### Scope

Thought assist only runs on a very small top set of surfaced thought candidates that are weak, generic, or likely to need semantic rescue.

Typical candidates include:

- generic fallback titles
- generic fallback short text
- `ready_for_review` rows near the surfacing threshold
- weak but grounded rows that might become good with better naming

### Timing

Thought assist runs inside [build_thought_packets](/Users/talhauddin/software/inner_space/src/conversation_os/thought_factory.py) after:

- promotion rows are already produced
- evidence and review judgments already exist
- source snippets are already attached

So the model does not decide the whole graph.

It only helps with the last-mile semantic packaging.

### Effect

The model returns one of:

- `promote`
- `review`
- `reject`

And may also supply:

- `title`
- `short_text`
- `reason`
- `confidence`

Behavior:

- `promote`
  - improved title/short text may be used
- `review`
  - improved text may still be used if it passes the existing surfacing gates
- `reject`
  - candidate is dropped from thought packet surfacing

This means the assist can both:

- improve weak good candidates
- suppress generic low-quality candidates

## Token-Burn Control

This layer is intentionally compute-bounded.

Controls:

- only selected surfaced artifacts are eligible
- per-run caps are read from runtime config
- cached fingerprints prevent repeat calls on unchanged candidates
- deterministic pipeline still does the heavy lifting

Current config knobs include:

- `semantic_assist.enabled`
- `semantic_assist.bubble_label_limit`
- `semantic_assist.thought_candidate_limit`
- `semantic_assist.agent`
- `semantic_assist.thinking`
- `semantic_assist.timeout_seconds`
- `semantic_assist.snippet_limit`
- `semantic_assist.snippet_chars`

If not explicitly enabled, assist defaults to active only when the runtime backend is already using an OpenClaw backend.

## Caching

Two caches are persisted in runtime data:

- `product/inner_world_v1/data/semantic_bubble_titles.json`
- `product/inner_world_v1/data/semantic_thought_assists.json`

Each cache entry stores:

- stable id
- input fingerprint
- returned payload
- update timestamp

If the deterministic input fingerprint has not changed, the cached result is reused and no model call is made.

This makes reruns cheap after the first assist pass.

## Failure Model

This layer is optional and fail-soft.

If OpenClaw:

- is unavailable
- times out
- returns invalid JSON
- returns low-quality output

then the system falls back to the deterministic result.

The architecture therefore maintains this invariant:

`the semantic assist may improve outputs, but it must never be required for the system to function`

## Data Flow

### Bubble path

1. deterministic bubble build finishes
2. top weak bubbles are selected
3. chunk evidence snippets are assembled
4. OpenClaw is asked for a better label
5. result is cached
6. user-visible bubble label is updated if valid

### Thought path

1. deterministic promotion rows are ranked
2. top weak/generic candidates are selected
3. source snippets are assembled
4. OpenClaw is asked to `promote|review|reject` and optionally rewrite title/short text
5. result is cached
6. thought packet builder uses improved text or rejects the candidate

## What Remains Unchanged

This design intentionally does **not** change:

- library ingestion
- source governance
- chunk governance
- normalized runtime chunk view
- meta-layer extraction rules
- bubble memberships
- bubble edges
- knowledge nodes
- knowledge edges
- runtime pipeline orchestration

Those remain deterministic and governable.

## Testing Strategy

The assist layer is tested with focused acceptance tests plus the existing full suite.

Key tests:

- assisted bubble relabeling for generic surfaced bubbles
- bounded thought assist call count
- thought assist rejection behavior
- full regression run of `tests.test_conversation_os`

The important contract tested is:

- the assist improves surfaced quality where possible
- the deterministic runtime still works without it
- model calls stay bounded
- caches prevent repeated unnecessary calls

## Why This Is The Right First Step

This is not the final semantic intelligence architecture for Inner World.

It is the correct first insertion point because it gives:

- immediate semantic quality lift
- low risk
- low cost
- easy rollback
- no destabilization of the library graph

If future work proves this layer valuable, the next expansions should still remain strategic:

1. concept-merge arbitration
2. stronger bubble-title rescue
3. higher-quality promotion gating

The system should only move deeper into model-assisted semantics after those bounded surfaced-layer gains are validated.
