# Repo Organization and Self-Updating Index Plan

Date: 2026-06-11
Status: proposed
Scope: repo-wide organization, indexing, generated-state boundaries

Update: runtime/artifact boundary migration completed on 2026-06-11 for the first live tranche. Canonical runtime state now lives under `runtime/product_state/` and canonical export/backup/portable artifacts now live under `artifacts/`.

## Purpose

This plan defines how to organize the repo around what the project is becoming:
a semantic operating layer with reusable kernel capabilities, assembly/runtime
composition, product surfaces, builder-support systems, and local runtime state.

The goal is not a cosmetic folder cleanup. The goal is a repo that agents and
humans can navigate, update, and extend without confusing source, generated
state, experiments, private memory, and deployable products.

## Current Reading

The repo already contains a useful architecture, but the physical layout does
not consistently express it.

What is strong:

- `context/substrate/` already contains module manifests, substrate algorithm
  manifests, generated atlases, a module registry, owner index, surface index,
  and dependency graph.
- `src/conversation_os/codebase_overview.py` already refreshes and validates
  the module index.
- `tools/substrate_index.py` already refreshes and watches substrate algorithm
  indexes.
- `docs/plans/layered-transition-2026-05-19/` already defines the right target
  architecture: kernel -> assembly -> surfaces -> builder-support -> runtime
  state.
- The reasoning bridge work has started to make live runtime behavior
  inspectable through `ContextState`, `ActiveFieldState`, `bridge_behaviors`,
  routing, pipelines, and learning events.

What is weak:

- `src/conversation_os/` is physically flat even though the manifest registry
  now describes layers and owners.
- `product/inner_world_v1/` mixes source assets, config, runtime data, exports,
  backups, portable bundles, and run artifacts.
- `docs/` mixes active plans, historical plans, research, transcripts, and
  generated or imported corpora.
- Root-level artifacts such as standalone dated markdown files and
  `frameworks synthesis/` are not clearly classified.
- The generated index currently tracks `src/conversation_os`, `tools`, and a
  small set of root docs, but does not deeply classify product assets, docs,
  plugins, tests, runtime state, and generated artifacts.
- `.gitignore` correctly treats `context/`, `memory/`, `vaults/`, `output/`,
  `tmp/`, and product data as generated or local, but this creates ambiguity
  because some canonical tracked substrate files also live under `context/`.

## Organizing Principle

Every path should belong to exactly one class:

- `source`: implementation, reusable specs, product assets, tests
- `contract`: schemas, manifests, recipes, product contracts
- `docs`: human reasoning, plans, research, decisions, guides
- `runtime_state`: local/private state produced by running the system
- `generated_index`: derived indexes that can be rebuilt
- `artifact`: exports, packs, screenshots, run outputs, backups
- `scratch`: temporary work that should not be indexed as architecture
- `archive`: preserved historical material, not active source

The index system should know this class for every important file or directory.

## Target Folder Structure

```text
.
  AGENTS.md
  README.md
  PRODUCT_THESIS.md
  SESSION_PROTOCOL.md
  CONTEXT_ROUTING.md
  TENETS.md
  pyproject.toml

  src/
    conversation_os/
      kernel/
        foundation/
        ingest/
        analysis/
        meta/
        knowledge/
        reasoning/
        synthesis/
        routing/
        policy/
        runtime/
        governance/
      assembly/
        bootstrap/
        runtime/
        adapters/
        development/
      surfaces/
        inner_world/
        personal_interface/
        thoughtboard/
        worldbuilding/
      builder_support/
        codebase/
        guard/
        holodeck/
        plugins/
      tooling_adapters/
        mcp/
        openclaw/
      compatibility/

  products/
    inner_world_v1/
      contract/
      config/
      pipelines/
      surfaces/
        miniapp/
        openclaw_bundle_template/
      recipes/
    personal_interface_v1/
      contract/
      config/
      recipes/
    mobile_surface_v1/
      app/
      config/
    thoughtboard_v1/
      contract/
      config/
      surfaces/

  docs/
    product-thesis/
    plans/
      active/
      historical/
    research/
      active/
      archive/
    guides/
    decisions/
    transcripts/
      archive/
    building-diary/
    superpowers/

  context/
    substrate/
      source/
        algorithms/
        modules/
        recipes/
      generated/
        CODEBASE_OVERVIEW.md
        CODEBASE_ATLAS.md
        AGENT_INDEX.md
        AGENT_OPERATING_BRIEF.md
        registry/
      schemas/

  runtime/
    memory/
    product_state/
      inner_world_v1/
      personal_interface_v1/
      thoughtboard_v1/
    workspaces/
    task_packs/
    vaults/

  artifacts/
    outputs/
    exports/
    portable_packs/
    backups/
    mobile_artifacts/
    playwright/

  plugins/
    art/
    entrepreneurship/
    research/

  tests/
    kernel/
    assembly/
    surfaces/
    builder_support/
    integration/

  tools/
    cli/
    indexes/
    runtime/
    deployment/
    migrations/

  scratch/
```

This is the target shape, not the first migration step. The first step should
add classification and index rules before moving code.

## Practical Near-Term Structure

The near-term path should avoid breaking imports. Keep the flat Python package
working while adding navigational structure around it.

Near-term layout:

```text
src/conversation_os/
  *.py                         # keep current imports stable
  services/
  vault_adapters/

context/substrate/
  modules/                     # source manifests for code modules
  families/                    # source manifests/specs for substrate algorithms
  registry/                    # generated machine indexes
  CODEBASE_OVERVIEW.md         # generated human index
  CODEBASE_ATLAS.md            # generated human atlas
  AGENT_OPERATING_BRIEF.md     # generated agent brief

product/
  inner_world_v1/
    config/                    # source/config
    miniapp/                   # source/static surface
    pipelines/                 # source/runtime specs
    data/                      # local runtime state
    runs/                      # generated run artifacts
    exports/                   # generated exports
    backups/                   # generated backups
    portable/                  # generated portable packs
  personal_interface_v1/
    config/                    # source/config
    data/                      # local runtime state
  mobile_surface_v1/
    src/                       # source if Vite app is canonical
    scripts/
    package.json
    node_modules/              # ignored dependency
  thoughtboard_v1/
```

The near-term rule is:

- do not move Python modules yet
- do not move product source assets yet
- do move or ignore generated state cleanly
- expand indexes so every important existing path has a role

## Index Architecture

The repo should have one orchestrated index command that refreshes several
specialized indexes.

```text
tools/index_repo.py
  refresh
  validate
  watch
  doctor
```

Internally it should coordinate:

1. `code index`
   - source: Python modules, tests, tools
   - current owner: `src/conversation_os/codebase_overview.py`
   - output: module registry, dependency graph, codebase overview, atlas

2. `substrate algorithm index`
   - source: `context/substrate/families/**/*.json|md`
   - current owner: `tools/substrate_index.py`
   - output: algorithm registry, family indexes, agent index

3. `product surface index`
   - source: `product/*/README.md`, `product/*/config`, miniapp files,
     package manifests, surface recipes
   - output: `context/substrate/registry/product_surface_index.json`

4. `docs index`
   - source: `docs/**/*.md`, root docs
   - output: `context/substrate/registry/docs_index.json`
   - fields: path, doc_type, status, date, related modules, related products

5. `state boundary index`
   - source: local runtime dirs
   - output: `context/substrate/registry/state_boundary_index.json`
   - fields: path, class, owner, ignored, rebuildable, contains_private_data

6. `artifact index`
   - source: `outputs`, `output`, `mobile_artifacts`, generated bundles,
     backups, portable packs
   - output: `context/substrate/registry/artifact_index.json`
   - fields: path, artifact_type, producer, retention_policy

7. `repo health index`
   - source: all above
   - output: `context/substrate/registry/repo_health.json`
   - fields: stale indexes, missing manifests, orphan docs, unclassified paths,
     generated files outside allowed locations

## Intelligent Update Loop

The self-updating system should be deterministic first, model-assisted later.

### Phase 1: deterministic watcher

Add one watcher that fingerprints classified inputs.

```text
watch inputs:
  src/**
  tools/**
  tests/**
  docs/**
  product/** excluding data/runs/exports/backups/node_modules
  context/substrate/modules/**
  context/substrate/families/**
  plugins/**
```

On change:

1. detect changed paths
2. map paths to index families
3. refresh only affected indexes
4. validate freshness and schema
5. write a compact update event

Output:

```text
context/substrate/registry/index_events.jsonl
```

### Phase 2: classification assistant

For unclassified paths, generate a candidate classification:

```json
{
  "path": "docs/research/example.md",
  "suggested_class": "docs",
  "suggested_doc_type": "research",
  "suggested_status": "active",
  "confidence": 0.72,
  "reason": "dated research doc under docs/research"
}
```

This should not auto-move files. It should create reviewable suggestions.

Output:

```text
context/substrate/registry/index_suggestions.jsonl
```

### Phase 3: agent-facing router

Expose an index query surface:

```bash
python3 tools/conversation_os.py repo-index query --path src/conversation_os/reasoning_bridge.py
python3 tools/conversation_os.py repo-index query --concept bridge_behavior
python3 tools/conversation_os.py repo-index health
python3 tools/conversation_os.py repo-index classify-untracked
```

This becomes the navigation layer for future agents.

## What To Index

Everything should be indexed, but not everything should be indexed the same
way.

### Full module index

- `src/conversation_os/**/*.py`
- `tools/**/*.py`
- reusable package scripts

Fields:

- path
- module id
- layer
- owner
- public API
- dependencies
- state owned
- tests
- products using it

### Product index

- `product/*/README.md`
- `product/*/CONTRACT.md`
- `product/*/config/**`
- `product/*/pipelines/**`
- `product/*/miniapp/**`
- `product/mobile_surface_v1/package.json`
- `product/mobile_surface_v1/src/**`

Fields:

- product id
- surface type
- source paths
- runtime state paths
- generated artifact paths
- commands
- owning modules

### Docs index

- root docs
- `docs/product-thesis/**`
- `docs/plans/**`
- `docs/research/**`
- `docs/guides/**`
- `docs/superpowers/**`

Fields:

- path
- doc type
- date
- status
- product area
- related module ids
- source/reference/generated

### State boundary index

- `memory/**`
- `context/task_packs/**`
- `context/workspaces/**`
- `runtime/product_state/**`
- `artifacts/**`
- `vaults/**`
- `output/**`
- `outputs/**`
- `tmp/**`

Fields:

- path
- owner
- private
- rebuildable
- retention
- should_git_ignore

### Artifact index

- portable packs
- OpenClaw bundles
- backups
- mobile artifacts
- screenshots
- exports

Fields:

- producer
- command
- input refs
- retention policy
- safe to delete

## `.gitignore` Policy

The ignore file should stop treating an entire top-level folder as one class
when that folder contains both canonical source and generated state.

Proposed correction:

```gitignore
# Generated Conversation OS state
context/task_packs/
context/workspaces/
memory/
mobile_artifacts/
output/
outputs/
tmp/
vaults/

# Generated substrate indexes remain tracked only when explicitly committed.
# New generated registry files should be created by index tools and reviewed.

# Generated product state
runtime/product_state/inner_world_v1/data/
runtime/product_state/inner_world_v1/runs/
runtime/product_state/personal_interface_v1/data/
runtime/product_state/development_layer_v1/data/
artifacts/exports/inner_world_v1/exports/
artifacts/exports/inner_world_v1/portable/
artifacts/exports/inner_world_v1/openclaw_bundle/
artifacts/backups/inner_world_v1/backups/

# Dependencies
node_modules/
product/mobile_surface_v1/node_modules/
```

This makes `context/substrate/**` easier to maintain as canonical source plus
generated index output.

## Migration Plan

### Phase 0: freeze current map

Deliverables:

- refresh all existing indexes
- export current module registry and surface index
- create a state-boundary report
- identify unclassified top-level paths

No moves.

### Phase 1: index everything in place

Deliverables:

- add `repo_index.py` or extend `codebase_overview.py` into a repo-wide index
  orchestrator
- add product, docs, state-boundary, and artifact indexes
- add `repo-index refresh|validate|watch|health`
- add tests for classification and freshness

No source moves yet.

### Phase 2: clean generated state boundaries

Deliverables:

- tighten `.gitignore`
- move obvious local artifacts into `artifacts/` or ignore them in place
- classify `frameworks synthesis/` as either `docs/research/archive` or
  `docs/product-thesis/archive`
- move root orphan markdown into `docs/research/archive` or
  `docs/building-diary`
- document retention rules for `runs`, `backups`, `portable`, and `outputs`

Moves allowed, but only for docs/artifacts/state, not Python modules.

### Phase 3: product folder cleanup

Deliverables:

- split product source from product state in-place or through a controlled
  `products/` migration
- decide whether `product/mobile_surface_v1` is canonical source; if yes, track
  package files and source, ignore dependencies and build output
- add product manifests for each product surface
- add commands into the product index

### Phase 4: package-level code migration

Deliverables:

- introduce physical packages matching the logical layers
- move modules in small tranches with compatibility wrappers
- update manifests after each tranche
- run full focused tests after each tranche

Suggested order:

1. `kernel/foundation`
2. `kernel/reasoning`
3. `assembly/runtime`
4. `surfaces/personal_interface`
5. `surfaces/inner_world`
6. `builder_support/codebase`

This is intentionally later because physical Python moves are the highest-risk
part.

### Phase 5: self-healing index

Deliverables:

- watcher process for index refresh
- health report with stale/unclassified/noisy-path warnings
- optional pre-commit hook
- optional background systemd service
- optional model-assisted classification suggestions

## Validation Rules

The repo should be considered organized only when:

- every tracked Python module has a manifest or explicit exemption
- every product has a product manifest
- every docs file has a doc classification
- generated state is ignored or explicitly marked as tracked source
- no top-level orphan files remain except canonical root docs
- `repo-index validate` and `repo-overview validate` both pass
- index freshness is checked after every significant code or manifest change

## Proposed Commands

```bash
python3 tools/conversation_os.py repo-index refresh
python3 tools/conversation_os.py repo-index validate
python3 tools/conversation_os.py repo-index watch --interval 2
python3 tools/conversation_os.py repo-index health
python3 tools/conversation_os.py repo-index classify-untracked
python3 tools/conversation_os.py repo-index query --path src/conversation_os/reasoning_bridge.py
python3 tools/conversation_os.py repo-index query --concept bridge_behavior
```

Keep existing commands as compatibility:

```bash
python3 tools/conversation_os.py repo-overview refresh
python3 tools/conversation_os.py repo-overview validate
python3 tools/substrate_index.py refresh
python3 tools/substrate_index.py watch
```

Eventually `repo-index refresh` should call both existing systems.

## First Implementation Slice

The first code slice should be small:

1. Add `src/conversation_os/repo_index.py`.
2. Add data classes or plain dictionaries for:
   - path classification
   - product surface entry
   - docs entry
   - state boundary entry
   - artifact entry
   - health report
3. Add CLI command family:
   - `repo-index refresh`
   - `repo-index validate`
   - `repo-index health`
4. Generate:
   - `context/substrate/registry/repo_index.json`
   - `context/substrate/registry/docs_index.json`
   - `context/substrate/registry/product_surface_index.json`
   - `context/substrate/registry/state_boundary_index.json`
   - `context/substrate/registry/artifact_index.json`
   - `context/substrate/REPO_ORGANIZATION.md`
5. Tests:
   - classification of canonical source paths
   - classification of generated state paths
   - validation catches unclassified top-level files
   - refresh output is deterministic

## Open Decisions

1. Should canonical product folders remain under `product/` or move to
   `products/`?
2. Should `context/substrate/generated/` be introduced, or should generated
   files stay at the top of `context/substrate/` for compatibility?
3. Should `docs/plans` be split physically into `active` and `historical`, or
   should status live in docs index metadata first?
4. Should `frameworks synthesis/` become product-thesis archive, research
   archive, or a named corpus under `docs/research/archive`?
5. Should `memory/` remain at repo root for local dev, or move under
   `runtime/memory/` with compatibility paths?

## Recommendation

Do not start by moving code.

Start by indexing the whole repo in place and making the source/state/artifact
boundaries explicit. Once the index can tell us what every path is, physical
reorganization becomes a controlled migration instead of a risky cleanup.

The organizing path should be:

`classify -> index -> validate -> quarantine generated state -> migrate source in tranches`

This matches the product thesis: preserve raw material, keep provenance, create
inspectable structure, and only promote or move things through governed,
reviewable steps.
