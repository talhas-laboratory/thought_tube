# CONTEXT ROUTING

Task routing in this repo is deterministic and task-scoped.

## Inputs to routing

- task request
- task type
- optional domain overlays
- active product thesis
- repo tenets
- reference docs from memory indexes
- recent sessions
- relevant memory cards
- active plans

## Routing rules

1. Include tenets and product thesis in every task pack.
2. Include current state, open questions, decision register, and domain map as reference docs.
3. Rank sessions and cards by lexical overlap with the request plus domain matches.
4. Fall back to the most recent sessions and highest-value decision/state cards when lexical overlap is weak.
5. Prefer accepted plans over exploratory notes.
6. Prefer direct source refs over summaries when both are available.
7. Cap the pack to the smallest useful set.

## Required outputs

Every task pack must tell the next agent:

- what is being built
- why it matters
- what has already been decided
- what is still open
- which raw sessions matter most

## Non-goals

- no whole-archive dump by default
- no plugin-specific routing logic in the core router
- no hidden selection rules
