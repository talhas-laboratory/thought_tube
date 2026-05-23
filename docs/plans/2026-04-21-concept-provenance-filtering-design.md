# Concept Provenance And Filtering Design

## Purpose

This update addresses two linked gaps:

1. semantically similar conversation concepts can still fragment into separate bubbles
2. bubbles and related knowledge objects do not yet expose strong enough raw-source provenance for agent cross-examination

The goal is to make concept identity more canonical while making every major knowledge object traceable and filterable.

## Scope

V1 of this correction includes:

- canonical concept alias overrides
- stronger concept matching and canonical label normalization
- concept-backed bubble alignment
- bubble provenance packets linking back to raw chunk/source transcript material
- filterable knowledge retrieval across concepts, bubbles, meta records, and thought packets

It does not yet introduce an LLM-backed ontology system.

## Canonical concept identity

The durable anchor remains the `ConceptNode`.

New guardrail:

- `concept_alias_registry.json`

This registry stores manual overrides for:

- canonical label
- aliases that must collapse into that canonical concept
- optional transfer-term hints

During synthesis:

- extracted candidates are normalized through the alias registry
- concept matching considers canonical label + aliases + transfer terms
- canonical labels are reused instead of letting surface phrasing spawn sibling concepts

## Bubble alignment

Concept synthesis must influence bubbles, not sit beside them.

So bubble finalization will add:

- `concept_ids`
- `primary_concept_id`

Bubble duplicate merging should also merge states when they align to the same concept identity, not only when labels/tokens happen to overlap.

This does not fully replace existing seed/token heuristics. It constrains them with a stronger identity layer.

## Provenance packets

Every bubble should expose a provenance packet that lets an agent inspect the raw source material behind it.

The packet includes:

- source registry entries
- chunk excerpts
- source refs grouped by source
- meta members that contributed to the bubble
- related concept nodes
- source transcript/search handles

The principle is:

`bubble -> members -> chunks/source refs -> raw source`

not:

`bubble -> summary only`

## Filtering

Add a filter/search surface across major knowledge components:

- concepts
- bubbles
- meta records
- thought packets

V1 filters:

- query text
- status
- source ref
- session id
- concept id
- bubble id
- component type

This gives agents one place to discover relevant knowledge and then drill into provenance.

## Runtime integration

The implementation should stay inside the existing runtime shape:

- concept synthesis remains in `conversation_synthesis.py`
- bubble provenance extends `context_bubbles.py`
- agent/runtime access extends `product_inner_world.py`
- CLI access extends `cli.py`

## Success criteria

- alias-equivalent concepts collapse into one concept node
- bubbles can align to canonical concepts
- bubble detail exposes raw-source provenance for cross-examination
- agents can filter knowledge objects by semantic query and source constraints
- semantically duplicate content is less likely to form disconnected bubbles
