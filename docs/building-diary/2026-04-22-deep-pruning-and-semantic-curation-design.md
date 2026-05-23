# Deep Pruning And Semantic Curation Design

## Purpose

The project needs a deep pruning system that can remove or exclude bad substrate not only by metadata, but also by contents and semantic meaning.

This is different from simple search or source deletion. The purpose is to let the operator clean the active reasoning corpus at multiple levels while keeping raw provenance and making downstream impact visible before changes are applied.

## Problem

Current runtime artifacts can be polluted by:

- transcript wrappers
- generic speaker labels
- metadata residue
- profile scaffolding
- imported JSON/meta artifacts
- low-signal repeated assistant/user boilerplate

When these survive ingestion, they can later show up as:

- bad bubbles
- weak concepts
- noisy edges
- misleading thought candidates

## Design goal

Support pruning across four layers:

- `source-level`
- `chunk-level`
- `semantic-level`
- `derived-level`

The system must be:

- reversible when possible
- provenance-aware
- impact-previewable
- selective in rebuild scope

## Prune levels

### 1. Source-level pruning

Whole source items can be:

- excluded from runtime
- excluded from bubbles
- excluded from concepts
- archived
- hard deleted only when explicitly intended

### 2. Chunk-level pruning

Within a source, specific chunks can be:

- dropped from semantic derivation
- marked as boilerplate
- marked as transcript scaffolding
- marked as metadata-only residue

### 3. Semantic-level pruning

The operator should be able to remove or suppress material by meaning, for example:

- transcript framing
- user-profile residue
- UI labels
- generic meta-observatory artifacts
- repeated non-semantic wrappers

### 4. Derived-level pruning

Derived objects should be invalidatable when their substrate is pruned:

- concepts
- bubbles
- edges
- thought candidates
- surfaced thoughts

## Filter modes

### Metadata filters

- source family
- source type
- import date
- path
- session id
- actor or speaker
- file type

### Content filters

- contains phrase
- regex or marker pattern
- repeated wrappers
- exact transcript phrases like `You Said`

### Semantic filters

- semantic similarity to scaffolding or residue
- concept match
- “looks like profile material”
- “looks like transcript boilerplate”
- “looks like low-value metadata”

## Prune statuses

Use statuses instead of only deletion:

- `active`
- `downweighted`
- `excluded_from_bubbles`
- `excluded_from_concepts`
- `excluded_from_runtime`
- `archived`
- `deleted`

This supports both safe experimentation and irreversible cleanup when needed.

## Impact preview

Before applying a prune action, the system should show:

- affected source count
- affected chunk count
- affected concepts
- affected bubbles
- affected edges
- affected thoughts

This is the most important control surface because pruning changes meaning, not just storage.

## Operator flows

### Flow: remove generic bubble residue

1. Filter bubbles by bad labels like `You Said`, `Label`, `Text`, `Source`.
2. Inspect their provenance.
3. Trace back to source/chunk families causing them.
4. Apply a prune or exclusion policy.
5. Rebuild affected layers.

### Flow: clean a source family

1. Filter all sources in a family such as transcript wrappers.
2. Preview the downstream derived objects they influence.
3. Exclude them from concepts and bubbles.
4. Rebuild concepts, bubbles, and knowledge edges.

### Flow: remove only semantic residue inside otherwise useful sources

1. Open the source.
2. Prune or suppress only the low-value chunks.
3. Keep the rest of the source active.
4. Rebuild the affected semantic layers.

## Suggested surfaces

### CLI

- `inner-world prune preview --query ...`
- `inner-world prune apply --source-ref ... --status excluded_from_bubbles`
- `inner-world prune chunk --chunk-id ... --reason transcript_scaffolding`
- `inner-world prune semantic --class transcript_residue --apply`

### UI

A future library manager should provide:

- semantic filter search
- source family drill-down
- impact preview panel
- soft-prune vs hard-delete controls
- selective rederive action

## Guardrails

- no raw-source mutation by default
- no derived delete without provenance
- soft prune should be preferred first
- every prune action should be reversible unless marked hard delete

## Success criteria

- the operator can prune by metadata, contents, or semantic meaning
- noisy bubble/concept residue can be traced and removed systematically
- pruning one source family does not require manual filesystem cleanup
- downstream rebuild scope is selective and inspectable
- corpus quality can improve over time without losing raw history
