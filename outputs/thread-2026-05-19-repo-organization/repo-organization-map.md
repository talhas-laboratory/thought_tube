# Repo Organization Map

Date: 2026-05-19

## Purpose

This document classifies the current repo into a cleaner future architecture without deleting existing work.

The goal is not to pretend the repo is already clean. The goal is to:

- preserve working architectural pieces
- separate reusable substrate from current product surfaces
- keep adjacent builder systems visible
- keep artifact-heavy and historical areas from contaminating future assembly work
- ensure nothing in the repo is left unclassified

## Architecture Categories

### 1. Kernel / Substrate

Reusable cognition, storage, ingestion, synthesis, governance, and structural reasoning parts that should survive across multiple future surfaces.

### 2. Assembly / Composition

Wiring, contracts, registries, routing, configuration, adapters, packaging logic, and runtime orchestration that decide how kernel parts become a surface.

### 3. Surface Products

Actual product-facing implementations, UX surfaces, and product-specific owners.

### 4. Builder-Support / Adjacent Systems

Important modules and tools that are not the main Inner Space / Thought Tube surface, but materially support building, contextualizing, operating, or scaling the system.

This is the category that includes things like Holodeck.

### 5. Documentation / Architecture Intelligence

Thesis docs, plans, guides, research, decision records, and design notes. These are not runtime modules, but they are part of the organizational system.

### 6. Runtime State / Canonical Working Data

Structured state produced or consumed by the current runtime and session system.

### 7. Lab / Artifacts / Residue

Experiments, scratch work, portable exports, snapshots, backups, generated outputs, corpus imports, and historical material that is useful for reference but should not be treated as clean architecture.

### 8. Infra / Repo Meta / Environment

Packaging, tests, service files, git metadata, dependency shims, and machine-local support.

## Root-Level Assignment

| Path | Category | Role |
| --- | --- | --- |
| `src/` | Kernel / Substrate + Assembly + Surface Products + Builder-Support | Main code ownership surface. |
| `product/` | Surface Products + Runtime State + Lab / Artifacts | Current product implementations and their local state. |
| `tools/` | Assembly / Composition + Builder-Support + Infra | Launchers, packagers, deployment tools, indexing tools, analysis runners. |
| `docs/` | Documentation / Architecture Intelligence | Plans, thesis, guides, research, diaries. |
| `context/` | Documentation / Architecture Intelligence + Builder-Support | Generated substrate indexes, task packs, workspace packs. |
| `memory/` | Runtime State / Canonical Working Data | Conversation OS session, event, card, and index state. |
| `plugins/` | Assembly / Composition | Domain overlays and configuration-driven specialization. |
| `pipelines/` | Assembly / Composition | Top-level pipeline documentation surface. |
| `ops/` | Infra / Repo Meta / Environment | Service/unit files and deployment support. |
| `tests/` | Infra / Repo Meta / Environment | Verification surface. |
| `mobile_artifacts/` | Lab / Artifacts / Residue | Bridge-side captured notes and operational artifacts. |
| `output/` | Lab / Artifacts / Residue | Historical analyzer outputs and visual checks. |
| `outputs/` | Lab / Artifacts / Residue | Ad hoc deliverables created during work sessions. |
| `tmp/` | Lab / Artifacts / Residue | Scratch builders, imported corpora, local UI checks. |
| `vaults/` | Lab / Artifacts / Residue | Snapshot vaults and raw source snapshots. |
| `README.md` | Documentation / Architecture Intelligence | Human repo entrypoint. |
| `PRODUCT_THESIS.md` | Documentation / Architecture Intelligence | Thesis entrypoint. |
| `CONTEXT_ROUTING.md` | Documentation / Architecture Intelligence | Routing doctrine. |
| `SESSION_PROTOCOL.md` | Documentation / Architecture Intelligence | Session doctrine. |
| `TENETS.md` | Documentation / Architecture Intelligence | Repo principles. |
| `AGENTS.md` | Documentation / Architecture Intelligence | Agent operating rules. |
| `pyproject.toml` | Infra / Repo Meta / Environment | Python packaging and project metadata. |
| `.git/` | Infra / Repo Meta / Environment | Active git metadata. |
| `.git.abandoned-full-import-20260505/` | Lab / Artifacts / Residue | Abandoned import-era git snapshot. |
| `.gitnexus/` | Infra / Repo Meta / Environment | Repo tooling metadata. |
| `.vendor/` | Infra / Repo Meta / Environment | Vendored support runtime. |
| `.pytest_cache/` | Infra / Repo Meta / Environment | Test cache. |
| `node_modules/` | Infra / Repo Meta / Environment | Local dependency shim created for workbook tooling; not product architecture. |
| `.claude/` | Infra / Repo Meta / Environment | Agent/editor support residue. |
| `2026-04-25_brainwalk_michael-jackson-and-space-exploration.md` | Lab / Artifacts / Residue | Standalone working note outside the structured doc system. |

## `src/conversation_os` Module Assignment

### Kernel / Substrate

These modules look like long-term reusable substrate candidates.

| Module | Why |
| --- | --- |
| `storage.py` | Base filesystem/json/jsonl utilities and repo root resolution. |
| `models.py` | Core shared datatypes for events, sessions, cards, insights. |
| `analysis.py` | Transcript materialization and session analysis base logic. |
| `analysis_units.py` | Canonical unitization of source material. |
| `vault_ingest.py` | Ingestion path from external/raw material into structured library input. |
| `conversation_learning.py` | User/assistant behavior extraction and preference learning primitives. |
| `conversation_deltas.py` | Structured change and expectation extraction from conversations. |
| `conversation_threads.py` | Thread building and source-linked conversational grouping. |
| `meta_objects.py` | Meta object vocabulary/constants. |
| `meta_layer.py` | Meta extraction and record production. |
| `operators.py` | Reusable reasoning/operator extraction logic. |
| `knowledge_layer.py` | Knowledge graph / node-edge layer. |
| `context_bubbles.py` | Higher-order clustering and context grouping. |
| `thread_abstractions.py` | Higher-level condensation over raw thread traces. |
| `conversation_synthesis.py` | Formation/synthesis layer over extracted material. |
| `thought_factory.py` | Thought-shaping production logic. |
| `judgment.py` | Lightweight judgment classification utility. |
| `review_queue.py` | Governance queue over promoted or reviewable artifacts. |
| `policy_engine.py` | Policy snapshot/update support. |
| `library_tracker.py` | Source-family tracking, governance, and library state control. |
| `long_form.py` | Long-form expansion engine; should likely become a reusable content-shaping subsystem. |
| `cost_tracker.py` | Shared runtime cost accounting. |
| `thread_context.py` | Thread-level context helper logic. |

### Assembly / Composition

These modules mostly wire, route, adapt, configure, or compose other parts.

| Module | Why |
| --- | --- |
| `cli.py` | Primary orchestration/control plane entry surface over all subsystems. |
| `routing.py` | Task and context routing composition logic. |
| `pipeline_runner.py` | Pipeline execution wiring rather than a specific reasoning primitive. |
| `pipelines.py` | Pipeline spec loading/bootstrap. |
| `runtime_pipeline.py` | Runtime rebuild orchestration/config rather than domain meaning itself. |
| `plugins.py` | Plugin discovery/loading layer. |
| `chat_backends.py` | Backend adapter layer for heuristic/OpenClaw/gateway chat execution. |
| `miniapp.py` | UI handler/composition layer between backend and browser surface. |
| `openclaw_miniapp.py` | Bundle builder/installer for OpenClaw app packaging. |
| `services/openclaw_sync.py` | Sync adapter between local repo and OpenClaw-side material. |
| `vault_adapters/openclaw_conversations.py` | Source adapter for one vault family. |

### Surface Products

These are product owners or strong product-specific domain engines.

| Module | Why |
| --- | --- |
| `product_inner_world.py` | Main owner for the current Inner World surface and runtime payloads. |
| `worldbuilding_studio.py` | Product-specific worldbuilding surface logic and packets. |
| `personal_interface.py` | Product-specific personal interface surface and runtime state. |

### Builder-Support / Adjacent Systems

These are important, but they are not the main Inner World/Thought Tube surface.

| Module | Why |
| --- | --- |
| `holodeck.py` | Workspace contextualization and build-support system; adjacent to main product but strategically important. |
| `worldbuilding_studio_mcp.py` | External/control adapter for World Studio. |
| `personal_interface_mcp.py` | External/control adapter for Personal Interface. |
| `engineering_guard.py` | Build-discipline and owner-surface safety system for development itself. |
| `codebase_overview.py` | Generated overview and codebase indexing support for development/navigation. |

### Infra / Repo Meta / Environment

| Module | Why |
| --- | --- |
| `__init__.py` | Package marker. |
| `services/__init__.py` | Namespace/package marker. |
| `vault_adapters/__init__.py` | Namespace/package marker. |

## Product Tree Assignment

### `product/inner_world_v1`

This directory is not one thing. It contains several categories at once.

| Subpath | Category | Role |
| --- | --- | --- |
| `README.md` | Surface Products | Human-facing definition of current Inner World v1 surface. |
| `CONTRACT.md` | Surface Products | Product contract/behavior surface. |
| `FEEDBACK_MODEL.md` | Surface Products | Surface-level feedback model tied to current product loop. |
| `config/` | Assembly / Composition | Product recipe/config layer for current surface. |
| `data/analysis_units.jsonl` and related structured records | Runtime State / Canonical Working Data | Active working state for the current pipeline. |
| `data/meta_layer/`, `data/concept_graph/`, `data/dimensions/`, `data/worldbuilding_studio/`, `data/threads/` | Runtime State / Canonical Working Data | Canonical derived working state for runtime behaviors. |
| `exports/` | Lab / Artifacts / Residue | Generated user-facing exports from runtime state. |
| `miniapp/` | Surface Products | Current primary browser surface implementation for Inner World and World Studio. |
| `openclaw_bundle/` | Assembly / Composition | Built packaging target for OpenClaw deployment. |
| `pipelines/` | Assembly / Composition | Surface-owned pipeline specs, especially current thought/feed shaping. |
| `portable/` | Lab / Artifacts / Residue | Portable/handoff/export packs, useful but not clean runtime architecture. |
| `runs/` | Lab / Artifacts / Residue | Historical run artifacts and packet traces. |
| `backups/` | Lab / Artifacts / Residue | Historical state snapshots; keep for reference, not as active architecture. |

### `product/personal_interface_v1`

| Subpath | Category | Role |
| --- | --- | --- |
| `README.md` | Surface Products | Product definition for the personal interface surface. |
| `data/` if present in runtime | Runtime State / Canonical Working Data | Product-local state for that surface. |

## Tools Assignment

### Assembly / Composition Tools

| Tool | Why |
| --- | --- |
| `tools/conversation_os.py` | Main CLI launcher into the control plane. |
| `tools/run_inner_world_backend.py` | Launches backend runtime. |
| `tools/run_inner_world_miniapp.py` | Launches local UI surface. |
| `tools/build_inner_world_openclaw_miniapp.py` | Builds assembly output for OpenClaw. |
| `tools/sync_inner_world_ui_to_openclaw.py` | Synchronizes UI assembly artifact to target environment. |
| `tools/tunnel_inner_world_openclaw.py` | Connectivity helper for active surface use. |
| `tools/run_personal_interface_mcp.py` | Launch path for Personal Interface MCP adapter. |
| `tools/substrate_index.py` | Rebuilds substrate browse/index layer. |

### Builder-Support / Adjacent Systems Tools

| Tool | Why |
| --- | --- |
| `tools/build_world_studio_portable_pack.py` | Builder/export tool for the World Studio adjacent ecosystem. |
| `tools/build_world_studio_master_library.py` | Builder/export tool for World Studio system/library handoff. |
| `tools/build_unified_server_vault.py` | Library/source consolidation support. |
| `tools/deploy_inner_world_to_openclaw.py` | Deployment/operator bridge rather than product logic. |
| `tools/meta_observatory_pdf_analyzer.py` | Specialized analyzer for external material. |
| `tools/run_semantic_credit_sweep.py` | Specialized analysis/ops utility. |
| `tools/run_three_state_showcase.py` | Showcase/demo support tool. |

### Infra / Repo Meta / Environment

| Path | Category | Role |
| --- | --- | --- |
| `tools/__pycache__/` | Infra / Repo Meta / Environment | Python cache residue. |

## Plugin Assignment

| Path | Category | Role |
| --- | --- | --- |
| `plugins/README.md` | Assembly / Composition | Explains plugin/overlay system. |
| `plugins/art/`, `plugins/entrepreneurship/`, `plugins/research/` | Assembly / Composition | Domain overlays for ontology, evaluation, retrieval policy, prompts, and templates. |
| Each plugin's `plugin.json`, `ontology.md`, `evaluation.md`, `retrieval_policy.json`, `prompts/`, `templates/` | Assembly / Composition | Product/domain specialization assets, not kernel reasoning. |

## Documentation Assignment

### Product Thesis and Canonical Product Docs

| Path | Category | Role |
| --- | --- | --- |
| `PRODUCT_THESIS.md` | Documentation / Architecture Intelligence | Entry point into current product thesis set. |
| `docs/product-thesis/` | Documentation / Architecture Intelligence | Canonical current product definition, glossary, bridge requirements, surface decisions, interpolation research. |

### Architecture / Plan / Design Docs

| Path | Category | Role |
| --- | --- | --- |
| `docs/plans/` | Documentation / Architecture Intelligence | Main architectural and implementation decision archive. |
| `docs/plans/2026-05-18-philosophical-framework-to-product.md` | Documentation / Architecture Intelligence | Recent mapping from philosophical framework into product behavior. |
| `docs/plans/*holodeck*` | Documentation / Architecture Intelligence | Design archive for builder-support adjacent system. |
| `docs/plans/*inner-world*`, `*social-feed*`, `*conversation-os*`, `*semantic*` | Documentation / Architecture Intelligence | Product and substrate design evolution. |

### Guides

| Path | Category | Role |
| --- | --- | --- |
| `docs/guides/worldbuilding-studio-agent-workflow.md` | Documentation / Architecture Intelligence | Operating guide for a surface product. |
| `docs/guides/worldbuilding-studio-operator-manuscript.md` | Documentation / Architecture Intelligence | Human operator playbook. |

### Research

| Path | Category | Role |
| --- | --- | --- |
| `docs/research/` | Documentation / Architecture Intelligence | Structured research inputs used to shape architecture and surfaces. |
| `docs/research/substack-article-structure-2026-04-16/` | Documentation / Architecture Intelligence | Long-form/article surface research. |
| `docs/research/conversation-corpus-2026-04-17/` | Documentation / Architecture Intelligence | Corpus review reference set. |
| `docs/research/session-driven-update-run-2026-04-18/` | Documentation / Architecture Intelligence | Pipeline behavior reference set. |
| `docs/research/single-conversation-semantic-run-2026-04-18/` | Documentation / Architecture Intelligence | Narrow semantic run analysis set. |

### Building Diary

| Path | Category | Role |
| --- | --- | --- |
| `docs/building-diary/` | Documentation / Architecture Intelligence | Historical build log, useful for intent/history, not runtime behavior. |

### Superpowers Specs

| Path | Category | Role |
| --- | --- | --- |
| `docs/superpowers/specs/` | Documentation / Architecture Intelligence | Design notes related to build workflows and Holodeck support. |

## Context Assignment

`context/` is a builder-facing intelligence layer, not a product surface.

| Subpath | Category | Role |
| --- | --- | --- |
| `context/README.md` | Documentation / Architecture Intelligence | Explains the context layer. |
| `context/substrate/` | Documentation / Architecture Intelligence + Builder-Support | Generated browse indexes, family registries, schema, agent briefings. |
| `context/task_packs/` | Builder-Support / Adjacent Systems | Canonical handoff/continuity packs used to route work. |
| `context/workspaces/` | Builder-Support / Adjacent Systems + Runtime State | Holodeck/workspace contextualization records and support artifacts. |

## Memory Assignment

`memory/` is canonical runtime/session state for the Conversation OS, even though much of it is archival.

| Subpath | Category | Role |
| --- | --- | --- |
| `memory/README.md` | Runtime State / Canonical Working Data | Explains the memory layer. |
| `memory/events/` | Runtime State / Canonical Working Data | Raw event stream for sessions. |
| `memory/sessions/` | Runtime State / Canonical Working Data | Materialized session records. |
| `memory/cards/` | Runtime State / Canonical Working Data | Decision/state/insight cards. |
| `memory/indexes/` | Runtime State / Canonical Working Data | Deterministic indexes like pond matrix and current state. |
| `memory/workspaces/` | Runtime State / Canonical Working Data + Builder-Support | Workspace-linked memory context. |

## Tests Assignment

| Path | Category | Role |
| --- | --- | --- |
| `tests/conftest.py` | Infra / Repo Meta / Environment | Shared test harness. |
| `tests/test_conversation_os.py` | Infra / Repo Meta / Environment | Broad substrate/runtime verification. |
| `tests/test_worldbuilding_studio.py` | Infra / Repo Meta / Environment | Surface-specific verification. |
| `tests/test_personal_interface.py` | Infra / Repo Meta / Environment | Adjacent surface verification. |
| `tests/test_long_form.py` | Infra / Repo Meta / Environment | Long-form subsystem verification. |
| `tests/test_engineering_guard.py` | Infra / Repo Meta / Environment | Builder-safety system verification. |
| `tests/__pycache__/` | Infra / Repo Meta / Environment | Cache residue. |

## Lab / Artifacts / Residue Assignment

### Historical and Generated Product Residue

| Path | Category | Role |
| --- | --- | --- |
| `product/inner_world_v1/backups/` | Lab / Artifacts / Residue | Historical snapshots of runtime/product state. |
| `product/inner_world_v1/runs/` | Lab / Artifacts / Residue | Historical execution traces and run artifacts. |
| `product/inner_world_v1/exports/` | Lab / Artifacts / Residue | Rendered exports of current state. |
| `product/inner_world_v1/portable/` | Lab / Artifacts / Residue | Portable packs and handoff artifacts. |

### External Inputs, Snapshots, and Scratch Work

| Path | Category | Role |
| --- | --- | --- |
| `mobile_artifacts/` | Lab / Artifacts / Residue | Mobile bridge-side captured notes and incident artifacts. |
| `output/` | Lab / Artifacts / Residue | Historical analyzer and Playwright outputs. |
| `outputs/` | Lab / Artifacts / Residue | Session-generated deliverables, including this organization map's sibling artifacts. |
| `tmp/chat_converter_2026_05/` | Lab / Artifacts / Residue | Imported conversation corpus used for analysis, not active architecture. |
| `tmp/inner-world-ui-check/` | Lab / Artifacts / Residue | UI scratch/check environment. |
| `tmp/build_philosophical_framework_sheet.mjs` | Lab / Artifacts / Residue | One-off builder script created during analysis work. |
| `tmp/inner_world_gpt_openapi.json` | Lab / Artifacts / Residue | Generated or imported interface artifact. |
| `vaults/server-unified-vault-2026-04-14/` | Lab / Artifacts / Residue | Large reference snapshot of unified raw material. |
| `.git.abandoned-full-import-20260505/` | Lab / Artifacts / Residue | Abandoned import state. |

## Infra / Repo Meta / Environment Assignment

| Path | Category | Role |
| --- | --- | --- |
| `pyproject.toml` | Infra / Repo Meta / Environment | Packaging/runtime definition. |
| `ops/systemd/inner-world.service.sample` | Infra / Repo Meta / Environment | Service definition template. |
| `.git/` | Infra / Repo Meta / Environment | Repo metadata. |
| `.gitnexus/` | Infra / Repo Meta / Environment | Tool metadata. |
| `.vendor/mcp_py/` | Infra / Repo Meta / Environment | Vendored dependency support. |
| `.pytest_cache/` | Infra / Repo Meta / Environment | Test cache. |
| `node_modules/` | Infra / Repo Meta / Environment | Local dependency shim, not architecture. |
| `.claude/` | Infra / Repo Meta / Environment | Agent/editor local support area. |

## What This Means For Transition Planning

### Highest-confidence future kernel candidates

- `storage.py`
- `models.py`
- `analysis.py`
- `analysis_units.py`
- `vault_ingest.py`
- `conversation_deltas.py`
- `conversation_threads.py`
- `meta_layer.py`
- `operators.py`
- `knowledge_layer.py`
- `context_bubbles.py`
- `thread_abstractions.py`
- `conversation_synthesis.py`
- `review_queue.py`
- `library_tracker.py`
- `long_form.py`

### Strong assembly candidates

- `cli.py`
- `routing.py`
- `runtime_pipeline.py`
- `pipeline_runner.py`
- `pipelines.py`
- `chat_backends.py`
- plugin overlays
- product config trees
- OpenClaw packaging/bundle builders

### Current surface owners that should not be mistaken for kernel

- `product_inner_world.py`
- `worldbuilding_studio.py`
- `personal_interface.py`
- `product/inner_world_v1/miniapp/`
- `product/personal_interface_v1/`

### Adjacent builder systems that deserve preservation

- `holodeck.py`
- `engineering_guard.py`
- `codebase_overview.py`
- `context/task_packs/`
- `context/workspaces/`
- deployment and packaging tools

## Practical Reading Of The Repo

The repo is not "one messy app." It is a mixed environment containing:

1. a real reusable substrate core
2. a current product implementation
3. a set of builder-support systems
4. a large amount of research, runtime state, and artifact residue

That means the clean transition is not:

- delete everything
- treat everything as product
- treat everything as kernel

The clean transition is:

- preserve kernel candidates
- preserve assembly logic
- keep current surfaces as reference implementations
- explicitly retain adjacent builder systems
- quarantine residue and artifact-heavy zones

## Bottom Line

Nothing in the repo should remain "uncategorized" after this pass:

- `src/` is a mix of kernel, assembly, surface owners, and builder-support modules
- `product/` is a mix of live surfaces, runtime data, packaging, and residue
- `tools/` are mostly assembly and builder-support
- `docs/` and `context/` are architecture intelligence
- `memory/` is canonical runtime/session state
- `plugins/` are assembly-time overlays
- `tests/` and `ops/` are environment and verification
- `mobile_artifacts/`, `output/`, `outputs/`, `tmp/`, `vaults/`, backups, runs, and portable packs are residue/reference layers

This map is the correct starting point for extracting a cleaner architecture without losing what already works.
