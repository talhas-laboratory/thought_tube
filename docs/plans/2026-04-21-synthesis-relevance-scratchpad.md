# Synthesis Relevance Scratchpad

## Why this exists

The codebase already has partial building blocks for abstraction, transfer, and knowledge linking, but it does not yet have the full synthesis-and-relevance system we discussed:

- store important ideas as `instance + abstraction + transfer shape`
- analyze how new content touches older content
- let agents retrieve ideas by structural relevance, not just literal similarity
- turn synthesis into explicit merge/update operations on the existing knowledge world

This scratchpad records that gap so implementation can proceed from a clear contract.

## What already exists

### Abstraction and routing primitives

- `thread_abstractions.py`
  - project lenses already exist, including `reasoning_routing`
  - threads can collapse upward via `abstracts_to`
- `knowledge_layer.py`
  - knowledge edges already include `transfers_to`
  - the graph already carries meta nodes, source nodes, abstractions, and bubble links
- `meta_layer.py`
  - meta objects already include `transfer_target`
  - runtime already promotes some patterns into cross-domain transfer hints
- `operators.py`
  - primitive rules already emit `transfer_targets`
- `long_form.py`
  - there is already a `pattern-and-transfer` module

### What this means

The repo is not starting from zero.

It already has:

- a partial abstraction graph
- a partial transfer vocabulary
- a partial knowledge graph
- a partial weighted runtime/module system

## What is still missing

### 1. A first-class synthesis packet

We do not yet have one durable object that says:

- what this new conversation means
- what is confirmed vs inferred vs contested vs open
- what existing knowledge it touches
- what merge/update operations are proposed

### 2. Touch classification against existing knowledge

We need explicit touch types for how new material affects old material, for example:

- `reinforces`
- `clarifies`
- `extends`
- `reframes`
- `contradicts`
- `changes_priority`
- `routes_across`
- `spawns_new_node`

Right now the graph has some link kinds, but not this explicit update semantics layer.

### 3. Transfer shape / cross-domain retrieval contract

We do not yet store ideas in the three-part shape:

- `specific instance`
- `abstract pattern`
- `transfer shape`

Without that, an agent may find the idea only when the new query sounds similar, instead of finding it through shared structure.

### 4. Structural relevance retrieval

We do not yet have a retrieval layer that intentionally searches in stages like:

1. literal match
2. concept match
3. structural or mechanism match
4. graph walk across abstraction/transfer edges
5. rerank by current task usefulness

### 5. Session-to-runtime merge bridge

Imported conversations are now parsed and analyzed much better, but they still do not automatically become governed runtime updates inside Inner World.

The missing bridge is:

- session understanding
- synthesis packet generation
- touch analysis against the current world
- governed merge into runtime knowledge objects

## Implementation direction

The next implementation should not be "add another summary."

It should introduce a modular synthesis path that can sit between session ingestion and runtime merge:

1. extract local meaning from the conversation
2. compare it against existing runtime knowledge
3. classify touches
4. produce a synthesis packet
5. convert approved synthesis outputs into graph nodes, edges, and merge operations

## Specific TODOs

- Define a `SynthesisPacket` schema.
- Define a `TouchOperation` schema.
- Define how `specific instance`, `abstract pattern`, and `transfer shape` are stored.
- Define retrieval scoring for structural relevance.
- Define how session imports are promoted into runtime synthesis.
- Define review/governance rules so inferred merges do not silently become truth.

## Working principle

The target is:

`new conversation -> synthesis packet -> touch operations -> governed merge -> richer runtime retrieval`

Not:

`new conversation -> generic summary -> isolated storage`
