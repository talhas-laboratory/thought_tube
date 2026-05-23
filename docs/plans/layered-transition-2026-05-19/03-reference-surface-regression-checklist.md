# Reference Surface Regression Checklist

Date: 2026-05-19

## Purpose

This checklist defines the behavior that must keep working while the current system is being extracted into the new layered architecture.

The reference surface is:

- current `Inner World v1`
- including the feed UI already built
- plus its associated archive, article, chat, and supporting backend/runtime flows

The point of this checklist is not perfect QA completeness.

The point is to prevent cleanup work from silently destroying the behavior that made the prototype valuable in the first place.

## Reference Surface Scope

Core reference files and surfaces:

- [product/inner_world_v1/README.md](/Users/talhauddin/software/inner_space/product/inner_world_v1/README.md)
- [product/inner_world_v1/miniapp/](/Users/talhauddin/software/inner_space/product/inner_world_v1/miniapp/)
- [src/conversation_os/product_inner_world.py](/Users/talhauddin/software/inner_space/src/conversation_os/product_inner_world.py)
- [src/conversation_os/miniapp.py](/Users/talhauddin/software/inner_space/src/conversation_os/miniapp.py)
- [tools/run_inner_world_backend.py](/Users/talhauddin/software/inner_space/tools/run_inner_world_backend.py)
- [tools/run_inner_world_miniapp.py](/Users/talhauddin/software/inner_space/tools/run_inner_world_miniapp.py)

## Regression Rule

No extraction step should be considered complete if it passes architectural cleanup goals but breaks the reference surface behavior below.

## Behavioral Check Groups

### 1. Launch and Boot

Must still work:

- local backend start path
- local miniapp start path
- CLI launch path for Inner World serve flow

Checks:

- backend boots without import or config regressions
- miniapp assets still load
- API routes needed by the UI are still present

### 2. Source and Library Visibility

Must still work:

- governed source visibility filtering
- source registry access
- chunk/runtime filtering behavior

Checks:

- hidden or excluded sources do not leak back into runtime payloads
- visible sources remain available to downstream surfaces

### 3. Analysis and Meta Path

Must still work:

- loading analysis units
- loading meta records
- preserving runtime source filtering on those records

Checks:

- analysis-unit-backed flows do not return empty or malformed payloads
- meta-layer-backed flows still resolve expected records

### 4. Knowledge and Thought Path

Must still work:

- thought packet construction
- feed row construction
- archive row construction
- concept and context-linked thought shaping

Checks:

- feed payload still returns ranked thought entries
- archive payload still resolves expected thought rows
- key payload shapes do not break the UI contract

### 5. Feed UI

Must still work:

- current feed surface renders
- feed item list loads
- thought cards remain readable and populated
- basic interaction path remains intact

Checks:

- feed response payload is accepted by the UI
- no breaking contract change to expected JSON shape
- current feed visual hierarchy is not accidentally removed during backend extraction

### 6. Archive Surface

Must still work:

- surfaced thought archive loads
- basic filtering or browsing remains usable

Checks:

- archive rows still materialize
- archive route still returns data in expected shape

### 7. Article Expansion

Must still work:

- selected thought can still expand into long-form explanation

Checks:

- long-form generation path still executes
- expansion payload remains consumable by the current UI

### 8. Scoped Thought Chat

Must still work:

- a thought-grounded chat path still resolves source refs and reasoning context

Checks:

- chat backend selection still works
- scoped context does not disappear during module movement
- saved thread writeback path is not unintentionally broken

### 9. World Studio Adjacency

Must still work where shared substrate is touched:

- shared substrate extraction must not break World Studio runtime if shared modules are moved

Checks:

- shared ingest, meta, or knowledge changes do not obviously break World Studio command paths

### 10. Packaging and Deployability

Must still work:

- local run path
- backend packaging path
- OpenClaw miniapp build path if touched by extraction work

Checks:

- packaging tools still resolve the code they expect

## Verification Levels

Use three levels depending on the scope of the extraction step.

### Level A: Narrow Extraction

Use when moving small kernel utilities.

Minimum checks:

- imports still resolve
- reference commands still start
- feed payload path still runs

### Level B: Shared Substrate Extraction

Use when moving analysis, meta, knowledge, or thought-shaping modules.

Minimum checks:

- launch checks
- analysis/meta checks
- feed payload checks
- archive checks
- article expansion checks

### Level C: Assembly or Surface Refactor

Use when changing recipes, runtime composition, or surface-owned adapters.

Minimum checks:

- full launch and boot
- feed UI smoke test
- archive smoke test
- article expansion smoke test
- scoped thought chat smoke test
- packaging path check

## Failure Rule

If an extraction step breaks the reference surface:

- do not mark the step complete
- record the breakage against the migration tranche
- either add a compatibility adapter or narrow the extraction

The migration should not trade functionality for cleanliness without explicit approval.

## Recommended Initial Regression Baseline

Before the first extraction tranche starts, capture:

- the commands used to launch the current surface
- a sample feed payload
- a sample archive payload
- a sample article expansion payload
- a sample scoped chat path
- any critical config assumptions

That baseline becomes the comparison surface for later extractions.
