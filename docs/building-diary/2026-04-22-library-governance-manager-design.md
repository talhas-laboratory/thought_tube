# Library Governance Manager Design

## Purpose

The project needs a first-class library governance layer between raw ingested sources and runtime derivation.

The goal is not just to ingest material. The goal is to manage what counts as active reasoning substrate, how material is normalized, how sources are grouped or excluded, and how rederivation happens after governance changes.

## Problem

Today the system is good at:

- capturing sources
- chunking them
- deriving meta, bubbles, and knowledge edges

But it is weak at:

- curating the corpus after ingestion
- changing source status safely
- filtering by semantic role
- reclassifying low-value or scaffolding material
- rerunning only the affected parts of the runtime after governance changes

As the library grows, that becomes a structural problem.

## Design goal

Introduce a `library manager` that governs four layers:

- `raw library`
  Original imported files, conversations, notes, and source registry rows. These remain untouched.
- `normalized library`
  Cleaned and analysis-ready views of those sources.
- `governance layer`
  Filters, tags, statuses, source-family rules, manual overrides, and semantic policies.
- `runtime view`
  The subset and representation of library material that the active Inner World runtime is allowed to use.

## Core objects

### Source policy record

Each source should be governable with fields like:

- `source_ref`
- `source_type`
- `source_family`
- `governance_status`
- `normalization_profile`
- `semantic_role`
- `include_in_runtime`
- `include_in_bubbles`
- `include_in_concepts`
- `include_in_long_form`
- `notes`
- `manual_overrides`

### Collection

A collection groups sources for governance and rebuild targeting, for example:

- imported conversations
- user memory docs
- meta-observatory artifacts
- scaffolding and transcript wrappers

### Normalization profile

A reusable profile describing how sources of a certain family should be cleaned before they enter runtime derivation.

Examples:

- chat transcript normalization
- user-profile normalization
- JSON/meta-artifact suppression

## Required capabilities

### 1. Semantic filtering

The manager must filter sources by:

- metadata
- path or family
- semantic class
- inferred role
- source contents
- concept relevance

### 2. Source status control

Sources should be markable as:

- `active`
- `background`
- `downweighted`
- `exclude_from_bubbles`
- `exclude_from_concepts`
- `exclude_from_runtime`
- `archived`

### 3. Normalization governance

The manager must let you apply or change normalization policy without rewriting raw sources.

### 4. Selective rederivation

After governance changes, the system should rerun only affected layers when possible:

- normalization
- chunking
- concept synthesis
- bubble building
- knowledge layer
- thought generation

## Operator flows

### Flow: identify corpus residue

1. Filter sources or derived objects by semantic query or source family.
2. Inspect provenance to see what raw material is causing bad outputs.
3. Mark that material with governance rules.
4. Rebuild only affected layers.

### Flow: reclassify a source family

1. Select a family such as imported user-profile docs.
2. Assign `semantic_role=scaffolding`.
3. Exclude from bubbles and concepts.
4. Recompute affected runtime layers.

### Flow: activate a new collection

1. Create or select a collection.
2. Assign normalization profile and inclusion policy.
3. Rebuild the runtime subset that depends on it.

## Suggested surfaces

### CLI

- `inner-world library status`
- `inner-world library filter --query ...`
- `inner-world library govern --source-ref ... --status ...`
- `inner-world library govern-family --family ... --exclude-from-bubbles true`
- `inner-world library rederive --affected-only`

### UI

A future library-manager surface should support:

- source search
- semantic filters
- family filters
- status editing
- preview of downstream impact
- rederive controls

## Guardrails

- Raw originals remain immutable.
- Governance changes are reversible.
- Every exclusion or override keeps provenance.
- Derived runtime should state which governance profile it was built from.

## Success criteria

- sources can be filtered by semantic role, not just by path
- low-value source families can be downweighted or excluded without manual file surgery
- runtime rebuilds can target only the affected layers
- provenance remains inspectable after governance changes
- future corpus maintenance stops being ad hoc and becomes a first-class system
