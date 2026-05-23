# Module Manifest Spec

Date: 2026-05-19

## Purpose

This document defines the minimum contract for describing a reusable module in the layered architecture.

The module manifest is the identity surface for reusable parts. It exists so that modules can be:

- found reliably
- versioned deliberately
- edited safely
- assembled predictably
- reviewed without guessing ownership

Without a manifest, the new assembly layer will still be built on implicit repo knowledge.

## Scope

This spec applies to:

- kernel modules
- assembly modules
- builder-support modules
- reusable surface adapters that are intended to be referenced by recipes

This spec does not apply to:

- raw runtime state files
- exports
- backups
- transient runs
- one-off scratch scripts with no planned reuse

## Core Principle

A module is not just a file or a folder.

A module is:

- a named capability
- with a stable owner
- with declared inputs and outputs
- with known dependencies
- with a clear status
- with a version that changes intentionally

## Required Fields

Every module manifest must define:

- `module_id`
- `name`
- `layer`
- `owner`
- `status`
- `version`
- `contract_version`
- `purpose`
- `repo_paths`
- `entrypoints`
- `inputs`
- `outputs`
- `dependencies`
- `used_by`

## Field Definitions

### `module_id`

Stable machine-readable identifier.

Rules:

- lowercase
- dot-separated
- no spaces
- should express layer and capability, not a filename

Examples:

- `kernel.analysis.analysis_units`
- `kernel.meta.meta_layer`
- `assembly.runtime.pipeline_runner`
- `builder_support.context.holodeck`

### `name`

Human-readable display name.

Examples:

- `Analysis Units`
- `Meta Layer Extractor`
- `Pipeline Runner`

### `layer`

One of:

- `kernel`
- `assembly`
- `surface`
- `builder_support`

This field forces an explicit architectural classification.

### `owner`

The canonical owning surface or team boundary.

For now this should usually be a code owner path or logical owner group such as:

- `src/kernel/analysis`
- `src/assembly/runtime`
- `src/builder_support/holodeck`
- `surface/inner_world`

Before the refactor, this can be a transitional owner description such as:

- `src/conversation_os`
- `product/inner_world_v1`

### `status`

One of:

- `candidate`
- `active`
- `transitional`
- `deprecated`
- `reference_only`

Meaning:

- `candidate`: identified but not yet trusted as a stable reusable module
- `active`: stable and intended for reuse
- `transitional`: in use during migration, but contract still settling
- `deprecated`: being retired
- `reference_only`: preserved for comparison, not for active reuse

### `version`

Semantic version for implementation behavior.

Example:

- `1.2.0`

Use version changes when implementation behavior changes in a way that matters to consumers.

### `contract_version`

Version for the external contract shape.

Example:

- `1.0`

This changes less often than implementation version and is the key assembly-facing compatibility marker.

### `purpose`

One or two sentences describing the capability in product-agnostic terms.

Good:

- `Produces canonical analysis units from ingested source records.`

Bad:

- `Helps the feed work better.`

### `repo_paths`

Paths that currently contain the implementation.

This allows the manifest to remain stable while code moves during migration.

### `entrypoints`

Named functions, commands, or classes that expose the module capability.

Example:

- `build_analysis_units(root)`
- `load_analysis_units(root)`

### `inputs`

Declared incoming artifacts or contracts, not implementation trivia.

Examples:

- `source_registry rows`
- `chunk_index rows`
- `runtime root path`

Each input should describe:

- `name`
- `kind`
- `required`
- `notes`

### `outputs`

Declared result artifacts or returned contracts.

Examples:

- `analysis_units.jsonl`
- `in-memory analysis unit rows`
- `materialized thread packet`

Each output should describe:

- `name`
- `kind`
- `notes`

### `dependencies`

Declared module-level dependencies, not just imports.

Each dependency should describe:

- `module_id`
- `dependency_type`
- `notes`

Allowed dependency types:

- `hard`
- `soft`
- `runtime_only`
- `build_only`

### `used_by`

Named consumers that depend on this module.

Examples:

- `recipe.inner_world.v1`
- `surface.world_studio`
- `builder_support.engineering_guard`

## Optional Fields

These are recommended once the system matures:

- `description`
- `constraints`
- `state_reads`
- `state_writes`
- `policy_touches`
- `observability`
- `test_surfaces`
- `migration_notes`
- `supersedes`
- `replaced_by`

## Manifest Format

Recommended initial format:

- YAML

Reason:

- easy to read in repo
- easy to diff
- easy to load from Python

Suggested location:

- `recipes/modules/`
- or `src/assembly/manifests/modules/`

The exact storage path can be finalized later, but the schema should stabilize before broad extraction begins.

## Example Manifest

```yaml
module_id: kernel.analysis.analysis_units
name: Analysis Units
layer: kernel
owner: src/conversation_os
status: transitional
version: 0.1.0
contract_version: "1.0"
purpose: Produces canonical analysis units from ingested source records for downstream synthesis and retrieval.
repo_paths:
  - src/conversation_os/analysis_units.py
entrypoints:
  - build_analysis_units(root)
  - load_analysis_units(root)
inputs:
  - name: source_registry_rows
    kind: runtime_state
    required: true
    notes: Source registry rows from the active library state.
  - name: chunk_index_rows
    kind: runtime_state
    required: true
    notes: Chunk rows derived during ingest.
outputs:
  - name: analysis_units_rows
    kind: runtime_state
    notes: Canonical analysis units used by downstream layers.
dependencies:
  - module_id: kernel.ingest.vault_ingest
    dependency_type: hard
    notes: Reads source and chunk index structures produced by ingest.
used_by:
  - recipe.inner_world.v1
  - recipe.world_studio.v1
```

## Identity Rules

- `module_id` must survive file moves
- one manifest per reusable module
- one reusable module may own multiple files
- one file may not silently define multiple unrelated modules without an explicit split plan

## Versioning Rules

Increment `version` when:

- behavior changes
- output shape changes
- important internal dependency changes alter module behavior

Increment `contract_version` when:

- required inputs change
- output contract changes
- compatibility expectations for consumers change

Do not change either version for:

- comment-only edits
- pure internal refactors with preserved behavior and preserved contract

## Dependency Rules

Manifest dependencies must follow the architecture direction:

- kernel may depend on kernel
- assembly may depend on kernel
- surface adapters may depend on assembly and kernel through contracts
- builder-support may depend on kernel and assembly

Manifest review should reject:

- kernel modules depending on surface modules
- kernel modules depending on builder-support modules
- assembly modules owning product-specific meaning rules

## Transitional Use

During migration, some manifests will describe code that still lives in old locations.

That is expected.

The manifest should reflect:

- current repo path
- target layer
- current status
- migration notes

The contract must stabilize before the file location does.

## Minimum Adoption Rule

No module should be extracted into the new architecture unless it has a manifest.

No recipe should depend on an unmanifested reusable module except through an explicit temporary compatibility note.

## Immediate First Use

The first modules that should receive manifests are:

- `storage.py`
- `models.py`
- `analysis_units.py`
- `meta_objects.py`
- `cost_tracker.py`
- `judgment.py`

These are the smallest stable kernel candidates and the safest place to validate the manifest system.
