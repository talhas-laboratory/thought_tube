# Layered Transition Plan

Date: 2026-05-19

## Purpose

This plan describes how to transition the current repo from a mixed prototype into a layered architecture without deleting valuable work.

The transition goal is:

- preserve the working architectural parts already implemented
- stop treating the current Inner World surface as the architecture itself
- extract reusable cognition and governance into a cleaner kernel
- introduce an explicit assembly layer for composition and versioning
- keep current surfaces as reference implementations during migration
- make it easy to find, edit, version, and assemble the correct pieces later

This is an extraction-and-stratification program, not a rewrite.

## Core Decision

The repo should be treated as:

- `implemented substrate candidates`
- `current reference surfaces`
- `builder-support systems`
- `runtime state`
- `lab residue and historical artifacts`

The new architecture should be:

`kernel capabilities -> assembly contracts and recipes -> surface products -> builder-support systems`

The current repo is not discarded. It becomes the source inventory from which the cleaner system is extracted.

## What Exists Today

The repo already contains real architectural value:

- ingestion and source tracking
- analysis unit generation
- conversation deltas and abstractions
- meta-layer extraction
- concept and knowledge structures
- thought and long-form shaping
- governance and review mechanics
- runtime rebuild/orchestration logic
- working browser surfaces
- deployment and packaging tools
- builder-support systems like Holodeck and engineering guard

The problem is not lack of architecture. The problem is entanglement.

Current entanglements:

- reusable logic and product logic live in the same owner surfaces
- `src/conversation_os/product_inner_world.py` acts as both product owner and composition hub
- `product/inner_world_v1/` mixes product contract, config, runtime state, pipelines, exports, portable packs, and artifacts
- the browser surface is real, but too much of the surrounding composition is implicit rather than contract-based
- repo residue lives too close to active architecture
- versioning happens mainly at repo level rather than module and recipe level

## Target Architecture

### 1. Kernel

The kernel contains reusable capabilities that survive across multiple surfaces.

Kernel responsibilities:

- ingestion
- source registry and provenance
- structural analysis and unitization
- meta extraction
- knowledge structures
- governance and review
- reasoning operators
- runtime primitives
- content-shaping primitives
- cost and policy tracking

Kernel rule:

- a kernel module must not know which surface product is using it

### 2. Assembly

Assembly becomes a first-class layer.

Assembly responsibilities:

- module registry
- module manifests
- dependency resolution
- recipe loading
- environment/config loading
- runtime composition
- adapter wiring
- packaging hooks
- surface bootstrap

Assembly rule:

- assembly decides how parts are combined, but does not own product meaning

### 3. Surface Products

Surface products are the human-facing products built on top of the kernel through assembly.

Near-term surfaces:

- current Inner World feed and article surface
- World Studio
- Personal Interface
- future founder tool
- future builder tool
- future general cognitive tool

Surface rule:

- a surface may own UX, language, defaults, and workflow shape
- a surface must not silently own general cognition logic that should live below it

### 4. Builder-Support / Adjacent Systems

This layer remains explicit and separate.

It includes:

- Holodeck
- engineering guard
- codebase overview
- substrate indexing
- task pack and workspace support
- deployment/operator bridges
- MCP adapters that are about operating or exposing systems rather than defining the main product

Builder-support rule:

- these systems are critical, but they are not the product kernel

### 5. Runtime State

Runtime state remains canonical, but it must be clearly separated from code and recipes.

Runtime state responsibilities:

- session/event memory
- product-local derived data
- canonical source registries
- meta records
- knowledge graphs
- feed and thought runtime records

Runtime rule:

- state is consumed by kernel and surfaces, but does not define architecture

### 6. Lab / Artifacts / Residue

This layer remains accessible, but quarantined.

It includes:

- outputs
- exports
- scratch runs
- backups
- portable packs
- imported conversation corpora
- historical snapshots

Lab rule:

- useful reference is preserved, but residue must not drive live architecture by accident

## Target Ownership Boundaries

### Kernel Candidate Modules

These should be migrated toward explicit kernel ownership first:

- `storage.py`
- `models.py`
- `analysis.py`
- `analysis_units.py`
- `vault_ingest.py`
- `conversation_learning.py`
- `conversation_deltas.py`
- `conversation_threads.py`
- `meta_objects.py`
- `meta_layer.py`
- `operators.py`
- `knowledge_layer.py`
- `context_bubbles.py`
- `thread_abstractions.py`
- `conversation_synthesis.py`
- `thought_factory.py`
- `judgment.py`
- `review_queue.py`
- `policy_engine.py`
- `library_tracker.py`
- `long_form.py`
- `cost_tracker.py`
- `thread_context.py`

### Assembly Candidate Modules

These should be made explicitly compositional:

- `cli.py`
- `routing.py`
- `pipeline_runner.py`
- `pipelines.py`
- `runtime_pipeline.py`
- `plugins.py`
- `chat_backends.py`
- `miniapp.py`
- `openclaw_miniapp.py`
- `services/openclaw_sync.py`
- `vault_adapters/openclaw_conversations.py`

### Surface Owners

These should remain surface-owned, but be thinned:

- `product_inner_world.py`
- `worldbuilding_studio.py`
- `personal_interface.py`
- `product/inner_world_v1/miniapp/`
- `product/personal_interface_v1/`

### Builder-Support Owners

These should remain explicit adjacent systems:

- `holodeck.py`
- `engineering_guard.py`
- `codebase_overview.py`
- `worldbuilding_studio_mcp.py`
- `personal_interface_mcp.py`
- `tools/substrate_index.py`
- `context/task_packs/`
- `context/workspaces/`

## Transition Principles

- Do not delete the current product first.
- Keep the current Inner World surface as the reference implementation during extraction.
- Move contracts before moving code.
- Extract only modules that have a clear responsibility.
- Generalize only what can plausibly be reused by at least two surfaces.
- Preserve provenance, runtime state, and review/governance behavior.
- Separate code, state, recipes, and residue physically as well as conceptually.
- Make every extracted module identifiable, owned, and versioned.
- Prefer shadow composition before destructive replacement.
- Every migration step must leave the repo runnable.

## What Must Change

### 1. Composition Must Stop Being Implicit

Today, too much composition is spread across product owners, runtime code, tools, and config folders.

The new system needs:

- explicit module manifests
- explicit surface recipes
- explicit dependency resolution
- explicit runtime wiring

### 2. Product Owners Must Be Thinned

Current product owners should lose responsibilities that belong lower down.

Examples:

- `product_inner_world.py` should stop acting as a broad owner of reusable runtime shaping
- `product/inner_world_v1/config/` should evolve from ad hoc config into recipe-driven assembly input
- current pipeline specs should be reviewed for whether they are product recipes or kernel operators

### 3. State Must Be Cleanly Distinguished From Code

The current product tree contains:

- runtime state
- product logic
- config
- exports
- portable packs
- backups

That is workable for a prototype, but not for a layered system.

The transition should move toward:

- code in owned code layers
- recipes/config in assembly-owned locations
- state in canonical state locations
- exports and packs in artifact locations

### 4. The Repo Needs Stable Module Identity

Each reusable module needs:

- `module_id`
- `owner`
- `purpose`
- `inputs`
- `outputs`
- `dependencies`
- `status`
- `version`
- `used_by`

Without this, the cleaner assembly layer will still be hard to navigate.

### 5. Surfaces Need Recipes

A surface must become an assembly recipe, not just a directory plus custom wiring.

Every major surface should eventually have:

- recipe manifest
- versioned module references
- policy defaults
- UI/surface adapter list
- runtime dependencies

### 6. Builder-Support Needs Its Own Lane

Holodeck and similar systems should remain visible and first-class, but not hidden inside product or kernel stories.

That prevents two failure modes:

- product logic getting polluted by build-time tools
- important build systems getting ignored because they are not part of the user-facing product

## Recommended Repository Shape

This is the target conceptual structure. It can be achieved incrementally and does not require an immediate filesystem rewrite.

```text
src/
  kernel/
    ingest/
    analysis/
    meta/
    knowledge/
    governance/
    reasoning/
    runtime/
    shaping/

  assembly/
    registry/
    manifests/
    resolver/
    recipes/
    bootstrap/
    adapters/

  surfaces/
    inner_world/
    world_studio/
    personal_interface/
    founder_tool/
    builder_tool/
    cognitive_tool/

  builder_support/
    holodeck/
    engineering_guard/
    codebase_overview/
    substrate_index/
    operator_bridges/

state/
  memory/
  product/

recipes/
  inner_world.v1.yaml
  world_studio.v1.yaml
  founder_tool.v0.yaml
  builder_tool.v0.yaml
  cognitive_tool.v0.yaml

lab/
  outputs/
  scratch/
  runs/
  backups/
  portable/
  imported_corpora/
```

This target shape is the direction, not the first patch.

## Workstreams

The transition should run as parallel workstreams with strict sequencing at the boundaries.

### Workstream A: Contracts and Inventory

Goal:

- define module identity before code movement

Outputs:

- module manifest schema
- module inventory for kernel, assembly, surfaces, builder-support
- owner matrix
- dependency map

### Workstream B: Kernel Extraction

Goal:

- isolate reusable cognition and governance capabilities from current product owners

Outputs:

- extracted modules with stable interfaces
- tests around preserved behavior
- reduced surface owner responsibilities

### Workstream C: Assembly Layer Introduction

Goal:

- create a real composition layer rather than scattered wiring

Outputs:

- recipe format
- resolver/bootstrap logic
- environment/config loading rules
- surface composition entrypoints

### Workstream D: Surface Refactoring

Goal:

- reclassify current surfaces as recipes and adapters over extracted capabilities

Outputs:

- `inner_world` reference recipe
- thinned surface owners
- surface-specific adapters for feed, archive, article, chat, and studio flows

### Workstream E: Builder-Support Formalization

Goal:

- preserve adjacent systems without letting them contaminate the product/kernel boundary

Outputs:

- builder-support lane in code and docs
- ownership rules for Holodeck and operator tools
- clear integration points with the substrate

### Workstream F: State and Artifact Separation

Goal:

- stop code, runtime state, and residue from living in one ambiguous surface

Outputs:

- state location policy
- artifact location policy
- migration rules for exports, portable packs, and runs

### Workstream G: Documentation and Governance

Goal:

- make the architecture self-describing and enforceable

Outputs:

- updated architecture docs
- migration checklists
- engineering guard criteria updates
- overview/index changes so agents can find the new layers

## Migration Phases

### Phase 0: Freeze the Reference Model

Goal:

- stabilize the current system enough to extract from it safely

Actions:

- designate current `Inner World v1` as the reference surface
- designate current feed UI and related browser flow as reference surface behavior
- document current runtime entrypoints and data dependencies
- stop broad opportunistic refactors while extraction begins

Exit criteria:

- the current reference surface can still be run locally
- the current data and pipeline dependencies are documented
- the system has a named baseline to compare against

### Phase 1: Build the Contract Layer

Goal:

- define what a module is before moving modules

Actions:

- create a module manifest format
- create a recipe manifest format
- assign initial module IDs to kernel and assembly candidates
- define dependency declaration rules
- define surface recipe declaration rules
- define builder-support manifest rules

Exit criteria:

- a reader can answer what exists, who owns it, and what depends on it
- at least the first tranche of modules is identity-stable without moving code yet

### Phase 2: Extract the Smallest Stable Kernel Slice

Goal:

- extract the least controversial reusable parts first

Recommended first slice:

- `storage.py`
- `models.py`
- `analysis_units.py`
- `meta_objects.py`
- `cost_tracker.py`
- `judgment.py`

Reason:

- these are easier to define cleanly and less likely to embed surface assumptions

Actions:

- wrap or relocate behind clear kernel interfaces
- add preservation tests
- update current surface owner imports with minimal disruption

Exit criteria:

- the first kernel slice exists as an explicitly owned layer
- current surfaces still run against it

### Phase 3: Extract the Core Substrate Path

Goal:

- move the real cognition path below the surface layer

Recommended second slice:

- `vault_ingest.py`
- `analysis.py`
- `conversation_deltas.py`
- `conversation_threads.py`
- `meta_layer.py`
- `operators.py`
- `knowledge_layer.py`
- `thread_abstractions.py`
- `conversation_synthesis.py`
- `thought_factory.py`
- `review_queue.py`
- `policy_engine.py`
- `library_tracker.py`

Actions:

- define capability boundaries inside the substrate path
- split direct product assumptions out of module APIs where needed
- preserve file/state compatibility during migration
- make cross-module dependencies explicit

Exit criteria:

- substrate logic can be described without reference to Inner World feed/article/chat UX
- current surface owners consume it rather than owning it

### Phase 4: Introduce the Assembly Layer

Goal:

- turn scattered wiring into a real composition system

Actions:

- define assembly entrypoints
- create registry/resolver/bootstrap components
- move config loading rules into assembly ownership
- classify pipeline specs as either kernel operators or surface recipes
- create initial recipe files for `inner_world` and `world_studio`

Likely assembly owners:

- `cli.py`
- `routing.py`
- `pipeline_runner.py`
- `pipelines.py`
- `runtime_pipeline.py`
- `plugins.py`
- `chat_backends.py`
- packaging/sync tools

Exit criteria:

- the current reference surface can be described as a recipe over modules
- new surfaces no longer need to be hand-wired from scratch

### Phase 5: Thin the Surface Owners

Goal:

- reduce surface modules to real product concerns

Actions:

- reduce `product_inner_world.py` to surface-specific assembly and payload shaping
- keep feed, archive, article, and thought-chat surface behavior in surface adapters
- ensure World Studio keeps only world-specific product logic
- keep Personal Interface as its own surface owner

Exit criteria:

- surface owners are smaller and easier to reason about
- shared cognition logic no longer lives primarily inside surface owners

### Phase 6: Formalize Builder-Support

Goal:

- preserve critical adjacent systems without confusing them with product code

Actions:

- group Holodeck, engineering guard, codebase overview, indexing tools, and operator bridges under a builder-support story
- define how builder-support modules are allowed to depend on kernel and assembly
- keep them out of product recipes unless explicitly required

Exit criteria:

- builder-support systems are easy to find and maintain
- product architecture does not absorb build-time concerns by accident

### Phase 7: Separate State and Residue

Goal:

- stop the product tree from doubling as a code surface and artifact dump

Actions:

- define canonical locations for runtime state
- define canonical locations for artifacts, exports, runs, backups, and portable packs
- migrate references and docs gradually
- preserve compatibility shims where needed

Exit criteria:

- code, recipes, runtime state, and residue are physically distinguishable
- new contributors can tell what is live architecture versus historical output

### Phase 8: Launch the First Clean New Surface

Goal:

- prove the architecture by building one new surface cleanly

Recommended candidate:

- founder tool or builder tool, depending on which requires fewer net-new primitives

Actions:

- compose the surface only through recipes, adapters, and existing extracted modules
- refuse product-specific logic leaking back into the kernel
- document the gaps that still require new kernel or assembly capability

Exit criteria:

- one new surface is assembled without repeating the original architecture mess
- the team can trace every part of the surface back to a module or recipe

## Versioning Strategy

Versioning needs three levels.

### Module Version

Use for extracted reusable modules.

Each module should declare:

- `module_id`
- `version`
- `contract_version`
- `status`

### Recipe Version

Use for the surface composition recipe.

Each recipe should declare:

- `recipe_id`
- `version`
- `module references`
- `policy defaults`
- `adapter list`

### Surface Release Version

Use for an actual shipped surface state.

Each surface release should declare:

- `surface_id`
- `release_version`
- `recipe_version`
- `runtime compatibility notes`

## Editing and Discoverability Rules

To make the new architecture workable, every extracted module should be easy to find and safe to modify.

Rules:

- each reusable module gets one owner location
- each reusable module gets one manifest
- each recipe declares the exact modules it uses
- each surface owns adapters and UX, not invisible shared cognition logic
- builder-support modules must be identifiable as non-surface systems
- overview and registry docs must be updated as modules move

## Data and Runtime Compatibility Strategy

The transition should preserve working runtime behavior while structure changes around it.

Rules:

- do not break existing session/event memory
- do not rewrite raw source registries unless necessary
- prefer compatibility adapters over immediate data moves
- treat current `product/inner_world_v1/data/` as active canonical state until a new state layout is ready
- only migrate state locations once code owners are already stable
- preserve provenance fields, review state, and governance metadata

## Testing and Verification Strategy

Every phase should preserve behavior, not just produce cleaner folders.

Verification lanes:

- unit tests for extracted modules
- regression tests for current reference surface flows
- state compatibility tests
- recipe resolution tests
- packaging/bootstrap tests
- architecture guard checks for owner-surface discipline

High-value reference tests should cover:

- ingesting source material
- building analysis units
- extracting meta layer
- rebuilding knowledge/concept state
- producing feed/thought payloads
- article expansion
- reference UI/API boot
- World Studio evidence-to-canon flow

## Major Risks

### Risk 1: False Abstraction

Danger:

- product-specific assumptions get renamed as kernel modules

Mitigation:

- require clear contracts and at least plausible multi-surface reuse before promoting a module into kernel

### Risk 2: Platform Too Early

Danger:

- too much time spent designing a general platform before one clean assembly path exists

Mitigation:

- extract only what supports the next reference or new surface milestone

### Risk 3: Losing Working Behavior

Danger:

- cleanup removes the subtle logic that makes the current system useful

Mitigation:

- keep the reference surface running throughout migration
- add behavioral regression checks before major owner moves

### Risk 4: State Corruption

Danger:

- moving architecture and moving state at the same time breaks compatibility

Mitigation:

- move code boundaries first
- move state locations only after stable adapters exist

### Risk 5: Builder-Support Gets Forgotten

Danger:

- Holodeck and build-time operator systems disappear from the architecture story

Mitigation:

- keep builder-support as an explicit category, not a footnote

### Risk 6: Residue Recontaminates the New Structure

Danger:

- outputs, backups, portable packs, and imported corpora keep influencing active architecture decisions

Mitigation:

- physically quarantine and label them
- keep live recipes and live state separate

## First 12 Concrete Moves

1. Write and adopt a module manifest schema.
2. Write and adopt a surface recipe schema.
3. Mark `Inner World v1` as the reference surface in architecture docs.
4. Inventory first-wave kernel candidates with IDs, owners, and dependency notes.
5. Inventory assembly candidates with IDs, owners, and dependency notes.
6. Define builder-support ownership and allowed dependency directions.
7. Add preservation tests around the smallest stable kernel slice.
8. Extract the first kernel slice behind explicit interfaces without changing behavior.
9. Introduce a minimal assembly registry/resolver for the reference surface.
10. Express the current Inner World surface as a first recipe, even if backed by compatibility adapters.
11. Thin `product_inner_world.py` by moving one clear capability path below it.
12. Choose and scope the first clean new surface to validate the architecture.

## Dependency Direction Rules

Allowed dependency flow:

- kernel -> kernel
- assembly -> kernel
- surface -> assembly
- surface -> kernel through assembly-owned contracts
- builder-support -> kernel
- builder-support -> assembly

Disallowed or strongly discouraged flow:

- kernel -> surface
- kernel -> builder-support
- surface -> raw residue/artifact paths as architecture dependencies
- assembly -> product-specific meaning rules that belong in surfaces

## Exit State

The transition is complete when:

- reusable substrate capabilities are identifiable and versioned
- composition is handled through an explicit assembly layer
- surface products are recipes plus adapters rather than fused owner modules
- builder-support systems have their own clear lane
- runtime state and residue are clearly separated
- one new surface has been built cleanly from extracted parts
- the current reference surface still works or has been intentionally superseded

## Recommended Immediate Next Deliverables

The best next planning artifacts after this document are:

- `module-manifest-spec`
- `surface-recipe-spec`
- `kernel extraction inventory`
- `assembly layer bootstrap design`
- `reference surface regression checklist`
- `first new surface selection memo`

## Bottom Line

The cleanest path is not:

- keep building on the current fused repo
- delete everything and start over
- call the current product a platform without changing its structure

The cleanest path is:

- freeze the current system as a reference surface
- define module and recipe contracts
- extract the smallest stable kernel first
- introduce a real assembly layer
- thin the current product owners
- preserve builder-support as its own lane
- build the first new surface through the new composition path

That gives continuity, architectural clarity, and a realistic path from messy prototype to reusable system.
