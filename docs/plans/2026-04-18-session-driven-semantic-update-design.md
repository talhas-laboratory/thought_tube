# Session-Driven Semantic Update Design

## Purpose

This update adds a human-usable thematic layer above raw conversation threads.

The immediate problem was not that the system lacked thread detection. The problem was that raw threads were still too close to conversational surface form:

- too granular
- too token-driven
- not project-readable
- too permissive when attaching approved assistant context back onto user intent

The goal of this update is to preserve low-level conversational flow while adding a second-order compression layer that turns those traces into project-meaningful thematic objects.

## Design Decision

Keep the existing `conversation_threads` layer.

Do not reinterpret it as the human-facing output. Treat it as a diagnostic trace layer for:

- returns
- interruptions
- cross-file continuation
- local user-flow continuity

Add a new `thread_abstractions` layer above it. This is the primary thematic surface.

The resulting stack is:

`conversation substrate`
-> `meta layer`
-> `conversation threads`
-> `thread abstractions`
-> `context bubbles`
-> `knowledge graph`

## What Changed

### 1. Project lens taxonomy

Added a fixed v1 project lens taxonomy in:

- `product/inner_world_v1/config/project_lenses.json`

The lens set is:

- `interaction_model`
- `cognitive_fidelity`
- `context_bubble_organization`
- `reasoning_routing`
- `user_model_and_taste`
- `interface_expression`
- `answer_shape_governance`
- `emergent_misc`

This gives raw thread compression a stable target vocabulary instead of leaving it entirely emergent.

### 2. Thread abstractions

Added:

- `src/conversation_os/thread_abstractions.py`
- `product/inner_world_v1/data/thread_abstractions.jsonl`
- `product/inner_world_v1/data/thread_abstraction_links.jsonl`

Each abstraction stores:

- project lens assignment
- thesis
- child raw thread ids
- source refs
- delta intent keys
- dominant tensions
- answer-shape constraints
- approved-context meta refs
- expectation ids
- resolution state
- confidence

Raw threads are intentionally allowed to stay somewhat fine-grained. The abstraction layer is what compresses them into usable project categories.

### 3. Granularity correction

Raw threads with the same primary lens are now allowed to merge upward more aggressively when they come from the same source and do not express clearly distinct tensions.

This is deliberate.

The prior behavior preserved too much local variation and produced multiple adjacent micro-threads that were all really expressions of one larger pressure field.

### 4. Exact context attachment

The `context_for` logic in `knowledge_layer.py` is now stricter.

Direct `context_for` edges now require:

- shared `delta_intent_keys`

They are further ranked by:

- shared delta intent
- shared priority tokens
- same raw thread membership
- same abstract thread membership

And they are capped to at most two semantic-line targets per approved-context record.

This turns approved assistant context into a narrow resolution attachment rather than a broad neighborhood smear.

### 5. Project-aware bubbles

`context_bubbles` now consume `thread_abstractions`.

Each bubble can now persist:

- `primary_abstract_thread_id`
- `supporting_thread_ids`
- `project_lens_keys`

Approved-context-derived seeds are also excluded from anchor creation, so user-led semantic material remains the primary organizing line.

### 6. Runtime visibility

Runtime and export surfaces now expose:

- conversation threads
- thread abstraction artifacts
- project lenses

This makes the new layer inspectable from CLI/runtime state instead of leaving it implicit inside the graph builder.

## Why This Architecture

This design keeps the conversation system layered correctly:

- raw capture stays raw
- local thread detection stays local
- abstraction happens one layer up
- bubble formation can become project-aware without losing grounding

This is better than trying to force the first thread layer to become “smart enough” on its own.

If the first layer over-merges, user-flow detail is lost.

If it never compresses, the output remains unreadable.

The abstraction layer solves that by keeping both:

- concrete conversational movement
- higher-order thematic structure

## Immediate Outcomes

The implementation should make the system better at:

- reducing thread over-fragmentation
- reading conversations through project themes instead of token clusters
- attaching approved assistant context only to the exact resolved user intent
- exposing theme-level thread structure to bubbles and downstream runtime consumers

## Deferred Work

This update does not yet add:

- LLM-backed thread abstraction
- bubble ranking based on abstract-thread centrality
- feed ranking that explicitly uses project lenses
- task-pack generation enriched with abstract-thread context

Those are valid follow-ons, but they are not required for the first architectural correction.
