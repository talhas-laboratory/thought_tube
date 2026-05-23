# Optimal Indexing System Design

Date: 2026-05-22
Status: proposed
Scope: repo-wide indexing architecture

## Purpose

Define the target indexing system for this repo so humans and agents can answer, for every important module and substrate algorithm:

- what it does
- how it works
- what it contains
- what it owns
- what it depends on
- what depends on it
- which layer it belongs to
- which surfaces use it

The system must be inspectable, machine-readable, auto-refreshable, and safe for agents to maintain independently.

## Design goals

- One canonical indexing architecture, not scattered partial maps.
- Human-readable and machine-readable views from the same source of truth.
- Cheap refresh after code or manifest changes.
- Validation strong enough to prevent stale or contradictory indexes.
- Clear separation between:
  - code/module indexing
  - substrate algorithm indexing
  - graph/impact indexing
- Compatible with the current layered architecture:
  - kernel
  - assembly
  - surfaces
  - builder-support

## Non-goals

- Replace source code as the ground truth for implementation behavior.
- Force every helper or package marker into the same documentation burden as substantive modules.
- Turn GitNexus into the canonical source of truth for architecture metadata.
- Encode product-specific policy inside substrate manifests.

## Current state

The repo already has three partial indexing surfaces:

1. Codebase inventory
   - generator: [src/conversation_os/codebase_overview.py](/Users/talhauddin/software/inner_space/src/conversation_os/codebase_overview.py)
   - outputs:
     - [context/substrate/CODEBASE_OVERVIEW.md](/Users/talhauddin/software/inner_space/context/substrate/CODEBASE_OVERVIEW.md)
     - [context/substrate/codebase_map.json](/Users/talhauddin/software/inner_space/context/substrate/codebase_map.json)
     - [context/substrate/AGENT_OPERATING_BRIEF.md](/Users/talhauddin/software/inner_space/context/substrate/AGENT_OPERATING_BRIEF.md)

2. Substrate algorithm library index
   - generator: [tools/substrate_index.py](/Users/talhauddin/software/inner_space/tools/substrate_index.py)
   - sources:
     - [context/substrate/families/](/Users/talhauddin/software/inner_space/context/substrate/families)
   - outputs:
     - [context/substrate/AGENT_INDEX.md](/Users/talhauddin/software/inner_space/context/substrate/AGENT_INDEX.md)
     - [context/substrate/registry.json](/Users/talhauddin/software/inner_space/context/substrate/registry.json)
     - [context/substrate/browse_map.json](/Users/talhauddin/software/inner_space/context/substrate/browse_map.json)

3. Graph and change-impact layer
   - provider: GitNexus
   - value:
     - symbol relationships
     - execution flows
     - impact analysis
     - safer multi-file rename support

What is missing is a canonical module manifest layer that sits between raw code scanning and the human-facing atlas.

## Target architecture

The optimal system has four source layers and four generated views.

### Source layers

1. Code
   - Python modules and selected repo documents remain the implementation truth.

2. Module manifests
   - One manifest per substantive module.
   - This is the canonical architecture metadata for code modules.

3. Substrate manifests
   - Existing algorithm JSON manifests remain the canonical metadata for substrate algorithms.

4. Graph index
   - GitNexus remains the derived execution/dependency graph, not the architecture source of truth.

### Generated views

1. Codebase Overview
   - broad repo inventory
   - quick module summary
   - symbol list
   - import list

2. Codebase Atlas
   - richer per-module architecture view
   - merged from code scan, module manifests, and graph references

3. Substrate Index
   - semantic algorithm browse layer

4. Registry and graph exports
   - machine-readable indexes used by agents and validation tooling

## Filesystem layout

```text
context/substrate/
  modules/
    kernel.storage.json
    kernel.models.json
    kernel.library_tracker.json
    surface.inner_world.product_inner_world.json
    surface.personal.personal_interface.json
    builder.holodeck.holodeck.json
  families/
    ...
  registry/
    module_registry.json
    module_browse_map.json
    dependency_graph.json
    surface_index.json
    owner_index.json
  CODEBASE_OVERVIEW.md
  CODEBASE_ATLAS.md
  AGENT_INDEX.md
  AGENT_OPERATING_BRIEF.md
  README.md
  SCHEMA.md
```

Notes:

- `context/substrate/modules/` holds module manifests and is source of truth.
- `context/substrate/registry/` holds generated machine views and should not be hand-edited.
- `CODEBASE_OVERVIEW.md` remains the fast inventory view.
- `CODEBASE_ATLAS.md` becomes the high-detail narrative/reference surface.

## Module manifest schema

Each substantive module should have one manifest.

Required fields:

- `module_id`
- `path`
- `layer`
- `owner`
- `purpose`
- `status`
- `version`
- `public_api`
- `contains`
- `depends_on`
- `feeds_into`
- `inputs`
- `outputs`
- `state_owned`
- `surfaces_using`

Recommended fields:

- `compatibility_wrappers`
- `notes`
- `adjacent_docs`
- `gitnexus_hints`
- `test_targets`
- `constraints`

### Required field meaning

- `module_id`
  - stable identifier, for example `kernel.governance.library_tracker`

- `path`
  - absolute repo-relative module path, for example `src/conversation_os/library_tracker.py`

- `layer`
  - one of:
    - `kernel`
    - `assembly`
    - `surface`
    - `builder-support`
    - `tooling`
    - `document`

- `owner`
  - short statement of the responsibility boundary the module owns

- `purpose`
  - one paragraph describing the job of the module

- `status`
  - one of:
    - `active`
    - `compatibility`
    - `experimental`
    - `legacy`

- `version`
  - semantic or contract version for the manifest

- `public_api`
  - exported functions, classes, constants, or entrypoints intended for use outside the module

- `contains`
  - main internal responsibility clusters or subdomains inside the module

- `depends_on`
  - other `module_id` values or external systems this module directly relies on

- `feeds_into`
  - downstream modules, surfaces, or pipelines that consume this module’s outputs

- `inputs`
  - key file, object, or event shapes the module expects

- `outputs`
  - key records, files, or structures the module produces

- `state_owned`
  - concrete files, directories, or state surfaces the module is responsible for

- `surfaces_using`
  - surfaces or tools that depend on this module behavior

### Example manifest

```json
{
  "module_id": "kernel.governance.library_tracker",
  "path": "src/conversation_os/library_tracker.py",
  "layer": "kernel",
  "owner": "Library governance, runtime rebuild orchestration, pond routing, and model-role configuration.",
  "purpose": "Own the canonical library-side governance and rebuild behavior for the Conversation OS substrate.",
  "status": "active",
  "version": "1.0.0",
  "public_api": [
    "derive_graph",
    "rederive_library",
    "get_pond_router_status",
    "update_pond_router_config",
    "apply_pond_router_preset",
    "get_dimension_model_role_status",
    "update_dimension_model_role_binding"
  ],
  "contains": [
    "runtime rebuild orchestration",
    "library governance state",
    "dimension model-role bindings",
    "pond routing configuration"
  ],
  "depends_on": [
    "kernel.ingest.vault_ingest",
    "kernel.analysis.analysis_units",
    "kernel.meta.meta_layer",
    "kernel.surface.thought_factory",
    "assembly.runtime_pipeline"
  ],
  "feeds_into": [
    "surface.inner_world.product_inner_world",
    "surface.personal.personal_interface",
    "tooling.cli"
  ],
  "inputs": [
    "vault chunks",
    "runtime config",
    "governance config",
    "dimension bindings"
  ],
  "outputs": [
    "runtime rebuild state",
    "derived graph state",
    "pond routing status",
    "dimension model-role status"
  ],
  "state_owned": [
    "product/inner_world_v1/runtime",
    "product/inner_world_v1/config"
  ],
  "surfaces_using": [
    "inner_world_v1",
    "personal_interface_v1"
  ],
  "compatibility_wrappers": [],
  "test_targets": [
    "tests/test_conversation_os.py"
  ]
}
```

## Generated outputs

### 1. Codebase Overview

Keep the current role:

- fast repo inventory
- tracked areas
- symbol preview
- internal import preview

Do not overload this file with full architectural detail.

### 2. Codebase Atlas

Add a new generated file:

- `context/substrate/CODEBASE_ATLAS.md`

Purpose:

- one richer reference section per substantive module
- summarize architecture metadata from module manifests
- include direct links to:
  - code
  - tests
  - adjacent docs
  - GitNexus process/context references when available

Each module section should show:

- module id
- path
- layer
- purpose
- public API
- owned state
- dependencies
- downstream consumers
- surfaces using it
- compatibility notes

### 3. Module registry JSON

Add generated files under `context/substrate/registry/`:

- `module_registry.json`
  - all manifests in normalized form
- `module_browse_map.json`
  - grouped by layer and owner
- `dependency_graph.json`
  - explicit dependency edges
- `surface_index.json`
  - grouped by surface usage
- `owner_index.json`
  - grouped by architecture owner boundary

### 4. Substrate index

Keep the existing substrate algorithm system unchanged in concept, but align naming and registry structure with the new module manifest layer.

## Refresh pipeline

The indexing system should support both deterministic refresh and watch mode.

### Deterministic refresh

Add a command family such as:

```text
python3 tools/conversation_os.py index refresh
python3 tools/conversation_os.py index validate
python3 tools/conversation_os.py index lookup --query "..."
python3 tools/conversation_os.py index atlas --module-id ...
```

`index refresh` should:

1. refresh the codebase overview
2. load module manifests
3. validate schema and ownership tags
4. refresh module registry outputs
5. refresh the codebase atlas
6. refresh the substrate index
7. optionally annotate graph staleness against GitNexus

### Watch mode

Add a long-running watcher command such as:

```text
python3 tools/conversation_os.py index watch
```

Watch these inputs:

- `src/conversation_os/**/*.py`
- `tools/**/*.py`
- `context/substrate/modules/*.json`
- `context/substrate/families/*/*.json`
- `context/substrate/families/*/*.md`

On change:

- recompute only affected views if possible
- otherwise fall back to full refresh

## Validation rules

Validation is mandatory. Without it, the index will drift.

`index validate` should fail if:

- a substantive tracked module lacks a manifest
- a manifest path does not exist
- a manifest references unknown modules in `depends_on`
- declared public API entries are missing in code
- a module imports across forbidden layer boundaries
- a module is marked `compatibility` but exposes no compatibility wrappers
- a generated index is older than one of its source files

Validation should warn, not fail, if:

- docstrings are weak
- a module summary is generic
- GitNexus has no graph context yet for a module
- a manifest is missing optional fields like `adjacent_docs`

## Layer rules

The index should understand the layered architecture explicitly.

Allowed examples:

- `surface -> assembly`
- `surface -> kernel`
- `assembly -> kernel`
- `builder-support -> kernel`
- `tooling -> kernel`
- `tooling -> assembly`
- `tooling -> surface`

Disallowed examples, unless explicitly marked compatibility:

- `kernel -> surface`
- `kernel -> builder-support`
- `assembly -> surface`

The index validator should enforce these rules.

## GitNexus role

GitNexus should be integrated as an enrichment layer, not as the source of truth.

Use it for:

- `detect_changes`
  - what execution flows are affected by the current diff
- `rename`
  - graph-aware symbol rename
- `query`
  - process and dependency discovery

Do not rely on GitNexus for:

- module purpose
- layer assignment
- architecture ownership
- state ownership
- compatibility intent

Those belong in the module manifests.

Recommended integration:

- manifest field: `gitnexus_hints`
- atlas section: `graph context`
- validator warning when a module is missing any discoverable graph references after indexing matures

## Agent update protocol

This must become a repo rule.

When an agent changes code:

1. decide whether the change affects:
   - public API
   - responsibility boundary
   - dependencies
   - owned state
   - downstream consumers
2. if yes, update the module manifest
3. run `index refresh`
4. run `index validate`
5. only then declare the task complete

If an agent adds a new substantive module:

1. create the code file
2. create the module manifest
3. refresh the index
4. validate layer rules
5. add or update tests

If an agent changes only behavior but not architecture:

- manifest update may not be needed
- refresh is still required

## Ownership policy

Not every file needs a manifest.

Manifest required:

- all substantive runtime modules in `src/conversation_os/`
- important tooling modules in `tools/`
- surface owners
- kernel owners
- assembly owners
- builder-support owners

Manifest optional:

- tiny compatibility wrappers
- simple loader files
- narrowly scoped helper modules

Manifest exempt:

- package markers like `__init__.py`
- generated artifacts
- test modules
- vendor code

## Implementation phases

### Phase 1: module manifest foundation

- create `context/substrate/modules/`
- define manifest schema formally
- seed manifests for highest-value modules:
  - `library_tracker`
  - `product_inner_world`
  - `personal_interface`
  - `miniapp`
  - `cli`
  - `storage`
  - `models`
  - `conversation_synthesis`
  - `meta_layer`
  - `thought_factory`

### Phase 2: registry generator

- implement manifest loader
- implement schema validation
- generate:
  - `module_registry.json`
  - `module_browse_map.json`
  - `dependency_graph.json`
  - `surface_index.json`
  - `owner_index.json`

### Phase 3: atlas generator

- generate `CODEBASE_ATLAS.md`
- merge:
  - codebase scan
  - module manifests
  - substrate references
  - optional GitNexus hints

### Phase 4: command surface

- add:
  - `index refresh`
  - `index validate`
  - `index lookup`
  - `index atlas`
  - `index watch`

### Phase 5: agent discipline

- update [AGENTS.md](/Users/talhauddin/software/inner_space/AGENTS.md)
- require index refresh after substantive architecture edits
- require manifest updates when responsibility changes

### Phase 6: GitNexus enrichment

- add optional graph cross-links
- add diff impact reporting to indexing workflows

## Acceptance criteria

The indexing system is considered complete when:

- every substantive module has a manifest or an explicit exemption
- `index validate` passes on a clean repo
- `CODEBASE_ATLAS.md` gives a useful per-module architecture view
- agents can answer module questions without manually reading multiple files first
- layer violations are caught automatically
- generated indexes remain fresh through watch mode or deterministic refresh
- GitNexus is used for graph insight and impact, but manifest truth remains authoritative

## Recommended next step

Begin with Phase 1 only.

Do not build the atlas first.
Do not build the GitNexus integration first.
Do not expand the current AST summary system into a pseudo-manifest system.

The first correct move is:

1. define the manifest schema in code
2. create the first 8-10 manifests
3. validate them
4. then generate the first registry layer

That is the smallest path that turns the current good indexing foundation into a real auto-maintainable module atlas.
