# Surface Recipe Spec

Date: 2026-05-19

## Purpose

This document defines how a surface product is assembled from reusable modules, adapters, policies, and runtime assumptions.

The recipe is the contract that replaces implicit product wiring.

It exists so that a surface can be:

- described without reading scattered code
- assembled repeatably
- versioned independently from the whole repo
- compared against other surfaces
- upgraded without losing track of what it depends on

## Scope

This spec applies to:

- current reference surfaces expressed in transitional form
- future clean surfaces built through the new architecture
- builder-facing or internal surfaces if they are assembled from reusable modules

This spec does not apply to:

- raw state folders
- exports or runs
- one-off demo scripts

## Core Principle

A surface is not the same thing as a directory.

A surface recipe is:

- the declarative description of a product assembly
- over a set of versioned modules
- with named adapters
- with explicit policies
- with runtime assumptions and state dependencies

## Required Fields

Every recipe must define:

- `recipe_id`
- `surface_id`
- `name`
- `status`
- `version`
- `target_layer`
- `purpose`
- `module_refs`
- `adapter_refs`
- `policy_defaults`
- `runtime_dependencies`
- `state_dependencies`
- `entrypoints`

## Field Definitions

### `recipe_id`

Stable machine-readable identifier for the recipe.

Examples:

- `recipe.inner_world.v1`
- `recipe.world_studio.v1`
- `recipe.founder_tool.v0`

### `surface_id`

Stable identifier for the human-facing product surface.

Examples:

- `surface.inner_world`
- `surface.world_studio`
- `surface.personal_interface`

### `name`

Human-readable name.

### `status`

One of:

- `candidate`
- `active`
- `transitional`
- `deprecated`
- `reference_only`

For the current migration, `inner_world` should initially be `transitional` because it is still partly hand-wired.

### `version`

Recipe version, independent from module versions and surface release version.

Change recipe version when:

- module selection changes
- adapter selection changes
- policy defaults change
- runtime dependency expectations change

### `target_layer`

Usually `surface`.

This field exists mainly to keep recipe concepts from being confused with module manifests.

### `purpose`

One or two sentences describing what the surface does for users.

### `module_refs`

List of reusable modules the surface depends on.

Each module reference should describe:

- `module_id`
- `version_range`
- `required`
- `notes`

### `adapter_refs`

List of surface-owned adapters or thin product-specific owners.

Examples:

- feed payload shaper
- archive adapter
- article expansion adapter
- miniapp API adapter

Each adapter reference should describe:

- `adapter_id`
- `repo_paths`
- `purpose`
- `depends_on`

### `policy_defaults`

Named settings or governance defaults the surface expects.

Examples:

- contradiction review required
- source visibility rules
- chat backend default
- ranking mode

### `runtime_dependencies`

External or runtime-level assumptions required to operate.

Examples:

- local backend service
- OpenClaw gateway support
- miniapp server
- runtime config availability

### `state_dependencies`

Named runtime state surfaces the recipe expects.

Examples:

- `memory/events`
- `memory/sessions`
- `product/inner_world_v1/data/source_registry.jsonl`
- `product/inner_world_v1/data/meta_layer/*`

### `entrypoints`

Commands, server routes, or handlers that activate the surface.

Examples:

- `python3 tools/run_inner_world_miniapp.py`
- `python3 tools/run_inner_world_backend.py`
- `python3 tools/conversation_os.py inner-world serve`

## Optional Fields

Recommended once recipe management matures:

- `ui_blocks`
- `release_notes`
- `compatibility_notes`
- `environment_variables`
- `packaging_targets`
- `observability_checks`
- `migration_notes`

## Format

Recommended initial format:

- YAML

Suggested location:

- `recipes/surfaces/`
- or `src/assembly/recipes/`

The recipe storage path may evolve, but the schema should stabilize before new surfaces are built.

## Example Recipe

```yaml
recipe_id: recipe.inner_world.v1
surface_id: surface.inner_world
name: Inner World v1 Reference Surface
status: transitional
version: 0.1.0
target_layer: surface
purpose: Presents evidence-backed thoughts as a feed, archive, article expansion, and scoped chat surface over the conversation substrate.
module_refs:
  - module_id: kernel.analysis.analysis_units
    version_range: ">=0.1.0"
    required: true
    notes: Provides canonical unitization for downstream shaping.
  - module_id: kernel.meta.meta_layer
    version_range: ">=0.1.0"
    required: true
    notes: Provides meta records used for synthesis and thought shaping.
  - module_id: assembly.runtime.pipeline_runner
    version_range: ">=0.1.0"
    required: true
    notes: Executes the runtime pipeline used by the surface.
adapter_refs:
  - adapter_id: surface.inner_world.feed_payload
    repo_paths:
      - src/conversation_os/product_inner_world.py
    purpose: Shapes thought packets into feed-facing payloads.
    depends_on:
      - kernel.shaping.thought_factory
      - assembly.runtime.pipeline_runner
policy_defaults:
  contradiction_review: required
  source_visibility: governed
  chat_backend: heuristic
runtime_dependencies:
  - local Python backend
  - browser miniapp host
state_dependencies:
  - memory/events
  - memory/sessions
  - product/inner_world_v1/data
entrypoints:
  - python3 tools/run_inner_world_miniapp.py
  - python3 tools/run_inner_world_backend.py
  - python3 tools/conversation_os.py inner-world serve
```

## Recipe Rules

- one surface may have multiple recipe versions over time
- one recipe may reference many modules
- a recipe may reference transitional adapters while the architecture is still being extracted
- a recipe must never hide a critical dependency in prose only

## Transitional Recipe Guidance

For current surfaces, the first recipe may still reference old file paths and compatibility adapters.

That is acceptable.

The recipe exists first to expose the assembly shape, not to pretend the migration is already complete.

## Recipe vs Surface Release

Do not confuse:

- `recipe version`
- `surface release version`

The recipe says how the surface is assembled.

The surface release says what was actually shipped or used at a specific point in time.

## Minimum Adoption Rule

No new clean surface should be started without a recipe.

No major change to an existing reference surface should happen without either:

- updating the recipe
- or explicitly marking the recipe as temporarily out of sync

## Immediate First Recipes

The first recipes that should be written are:

- `recipe.inner_world.v1`
- `recipe.world_studio.v1`

Then:

- `recipe.founder_tool.v0`
- `recipe.builder_tool.v0`
- `recipe.cognitive_tool.v0`

Those future recipes should reuse the same kernel and assembly modules wherever possible rather than recreating product logic.
