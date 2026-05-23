# First Extraction Tranche Inventory

Date: 2026-05-19

## Purpose

This document defines the first concrete extraction wave for the layered transition.

It is intentionally conservative.

The first tranche should prove that:

- the manifest system works
- the recipe system can point to extracted modules
- the current reference surface can survive extraction
- the repo can gain cleaner boundaries without destabilizing the live system

## Tranche Strategy

This first tranche should only include modules that are:

- clearly useful
- relatively self-contained
- low in product-specific assumptions
- high in reuse potential
- low in migration risk

This tranche is not the place to solve the full architecture.

It is the place to validate the migration method.

## Tranche 1 Goals

- assign module manifests to the safest kernel candidates
- establish dependency recording discipline
- create the first recipe references against those manifests
- preserve full compatibility with the current Inner World reference surface

## Tranche 1 Modules

### 1. `storage.py`

- Proposed module ID: `kernel.foundation.storage`
- Current path: `src/conversation_os/storage.py`
- Why in tranche 1:
  - foundational utility layer
  - broad reuse potential
  - relatively low product entanglement
- Extraction action:
  - manifest first
  - preserve current import compatibility
  - do not refactor behavior aggressively
- Dependencies:
  - none at architectural layer level
- Used by:
  - nearly everything
- Validation:
  - imports resolve
  - JSON/JSONL and markdown write paths still function

### 2. `models.py`

- Proposed module ID: `kernel.foundation.models`
- Current path: `src/conversation_os/models.py`
- Why in tranche 1:
  - shared datatypes
  - high reuse potential
  - key for later contract cleanup
- Extraction action:
  - manifest first
  - document shared model consumers
  - avoid semantic rewrites
- Dependencies:
  - foundational only
- Validation:
  - model imports resolve
  - current runtime flows still deserialize and serialize as expected

### 3. `analysis_units.py`

- Proposed module ID: `kernel.analysis.analysis_units`
- Current path: `src/conversation_os/analysis_units.py`
- Why in tranche 1:
  - strong kernel candidate
  - central to multiple future surfaces
  - already conceptually separable from the feed UI
- Extraction action:
  - manifest
  - declare state reads and output contract
  - preserve current runtime behavior
- Dependencies:
  - ingest-derived state
  - storage utilities
- Validation:
  - analysis unit load/build path still works
  - downstream consumers do not break

### 4. `meta_objects.py`

- Proposed module ID: `kernel.meta.meta_objects`
- Current path: `src/conversation_os/meta_objects.py`
- Why in tranche 1:
  - vocabulary/constants surface
  - low-risk structural module
- Extraction action:
  - manifest
  - declare as shared vocabulary dependency
- Dependencies:
  - minimal
- Validation:
  - meta-layer imports still resolve

### 5. `cost_tracker.py`

- Proposed module ID: `kernel.runtime.cost_tracker`
- Current path: `src/conversation_os/cost_tracker.py`
- Why in tranche 1:
  - clear single-purpose capability
  - useful across many surfaces and builder-support tools
- Extraction action:
  - manifest
  - document state writes and summary outputs
- Dependencies:
  - storage utilities
- Validation:
  - cost summary and event listing still resolve

### 6. `judgment.py`

- Proposed module ID: `kernel.reasoning.judgment`
- Current path: `src/conversation_os/judgment.py`
- Why in tranche 1:
  - clear bounded capability
  - useful test case for a lightweight reasoning module
- Extraction action:
  - manifest
  - define input/output contract precisely
- Dependencies:
  - minimal
- Validation:
  - run classification behavior remains stable

## Tranche 1 Non-Goals

Do not include yet:

- `product_inner_world.py`
- `worldbuilding_studio.py`
- `miniapp.py`
- `runtime_pipeline.py`
- `pipeline_runner.py`
- `knowledge_layer.py`
- `conversation_synthesis.py`
- `thought_factory.py`
- `library_tracker.py`

Reason:

- those modules are more entangled
- they depend on clear manifest discipline first
- some of them sit closer to assembly or surface ownership

## Tranche 1 Deliverables

- manifest files for all six tranche modules
- first recipe draft that references at least some of these modules
- compatibility notes for unchanged imports
- regression results against the reference surface checklist
- dependency notes for tranche 2 planning

## Tranche 1 Ordering

Suggested execution order:

1. `storage.py`
2. `models.py`
3. `meta_objects.py`
4. `cost_tracker.py`
5. `judgment.py`
6. `analysis_units.py`

Reason:

- start with the safest foundational surfaces
- end with the first meaningful data-producing kernel module

## Tranche 1 Verification

Minimum required checks after the tranche:

- reference surface launch paths still work
- analysis unit path still works
- feed payload path still works
- no import breakages in current product owners

## Tranche 2 Preview

If tranche 1 succeeds, the next likely candidates are:

- `analysis.py`
- `vault_ingest.py`
- `conversation_deltas.py`
- `conversation_threads.py`
- `meta_layer.py`

That second wave begins the actual substrate path, but only after the manifest and recipe system has been proven on safer modules.

## Ownership and Tracking Rule

Each tranche module should get:

- a manifest
- a named owner
- a migration status
- a verification note

No tranche module should be marked complete based only on file movement.

Completion means:

- contract exists
- compatibility is preserved
- regression checks passed
- recipe references can point to the module cleanly
