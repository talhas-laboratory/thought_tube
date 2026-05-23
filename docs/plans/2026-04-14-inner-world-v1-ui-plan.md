# Inner World v1 UI Plan

Date: 2026-04-14
Status: review

## Core UI Direction

The miniapp should feel like social media for yourself by yourself.

The user should not land in a dashboard.
The user should land in a private thought feed.

Each surfaced thought has three states:

1. short-form thought card
2. expanded longform thought article
3. thought-native chat thread

## Primary Surfaces

### 1. Thought Feed

Purpose:
The home screen.

Behavior:

- shows a ranked stream of compact thought cards
- each card feels tweet-like in density and scan speed
- each card is authored by the system for the user only
- each card is selective, not high-volume

Each thought card must show:

- title or lead line
- one short explanation of what changed
- evidence status
- confidence
- domain label
- one lightweight action hint

Primary actions:

- expand
- save
- dismiss
- revisit later

### 2. Thought Article

Purpose:
The detailed explanation of a thought.

Behavior:

- opens from a thought card
- feels more like a substack-style article than a modal
- explains the short thought in full

The article view must show:

- the original short thought
- detailed explanation
- source refs
- reasoning primitive used
- surprise score
- confidence score
- why it matters now
- one next action

Primary actions:

- open source refs
- start thought chat
- save thought
- dismiss thought

### 3. Thought Chat

Purpose:
Let the user interrogate, challenge, extend, and refine one thought.

Behavior:

- chat belongs to one thought, not the whole product
- chat assistant should feel like the thought speaking from its own evidence and primitives
- chat uses scoped context, not full-archive spillover

The chat context should include:

- the selected thought
- linked source refs
- relevant source items
- relevant reasoning primitives
- directly related conversation fragments
- thread history for that thought only

Primary actions:

- send message
- save thread
- delete thread
- reopen article

## State Model

### Thought states

- `surfaced`
- `saved`
- `dismissed`
- `revisit_later`
- `archived`

### Thread states

- `active`
- `saved`
- `deleted`

Rules:

- deleting a thread does not delete the underlying thought
- saving a thread writes a new linked artifact back into the library
- saved thread content becomes new source material with provenance

## Route Map

- `/inner-world`
  - thought feed
- `/inner-world/thought/:thoughtId`
  - longform thought article
- `/inner-world/thought/:thoughtId/chat`
  - thought-native chat
- `/inner-world/archive`
  - archived thoughts and saved threads
- `/inner-world/sources/:sourceId`
  - source drill-down
- `/inner-world/settings`
  - feed cadence, export, conservative mode, overlay defaults

## Interaction Principles

- Feed first, not dashboard first.
- Short thought first, detail on demand.
- Chat belongs to a thought, not to the whole archive.
- Save should strengthen the library.
- Delete should stay reversible at the thread level.
- The UI should feel intimate, calm, and highly legible.

## v1 Non-Goals

- public or shared feed
- infinite noisy social loop
- graph canvas as the default surface
- general-purpose chatbot home screen
- autonomous posting without user review
