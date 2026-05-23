# Tranche 1 Module Manifests

Date: 2026-05-19

## Purpose

This document instantiates the first migration tranche from the layered transition program.

It gives the safest kernel candidates explicit identity, ownership, dependency, and versioning data so they can be treated as real architectural units rather than just files in the repo.

These manifests are transitional by design. They describe the current implementation locations while establishing the target module identity.

## Tranche Overview

This tranche covers:

- `storage.py`
- `models.py`
- `meta_objects.py`
- `cost_tracker.py`
- `judgment.py`
- `analysis_units.py`

These are the first modules because they are relatively small, broadly reusable, and low risk compared with the more entangled synthesis, knowledge, and surface owner modules.

## Manifest Set

### 1. `kernel.foundation.storage`

```yaml
module_id: kernel.foundation.storage
name: Storage Utilities
layer: kernel
owner: src/conversation_os
status: transitional
version: 0.1.0
contract_version: "1.0"
purpose: Provides the shared filesystem, JSON, JSONL, directory, and identifier utilities used across the repo.
repo_paths:
  - src/conversation_os/storage.py
entrypoints:
  - utc_now()
  - repo_root_from(start)
  - slugify(value)
  - make_id(prefix)
  - ensure_dir(path)
  - read_json(path, default)
  - write_json(path, payload)
  - append_jsonl(path, payload)
  - read_jsonl(path)
  - write_jsonl(path, rows)
  - write_markdown(path, content)
inputs:
  - name: path
    kind: filesystem
    required: true
    notes: Filesystem target used for reads, writes, and directory creation.
  - name: payload
    kind: structured_data
    required: false
    notes: JSON, JSONL, or markdown content depending on the entrypoint.
outputs:
  - name: file_content
    kind: filesystem
    notes: Written JSON, JSONL, or markdown files.
  - name: path
    kind: filesystem
    notes: Paths created or returned by helper functions.
dependencies: []
used_by:
  - kernel.foundation.models
  - kernel.runtime.cost_tracker
  - kernel.analysis.analysis_units
  - recipe.inner_world.v1
```

### 2. `kernel.foundation.models`

```yaml
module_id: kernel.foundation.models
name: Shared Data Models
layer: kernel
owner: src/conversation_os
status: transitional
version: 0.1.0
contract_version: "1.0"
purpose: Defines the shared dataclasses and serialization shapes used by session, memory, knowledge, and runtime records.
repo_paths:
  - src/conversation_os/models.py
entrypoints:
  - ConversationEvent.to_dict()
  - SessionManifest.to_dict()
  - TaskContextPack.to_dict()
  - MemoryCard.to_dict()
  - InsightCandidate.to_dict()
  - SurfacedInsight.to_dict()
  - ThoughtFeedItem.to_dict()
  - ThoughtThreadMessage.to_dict()
  - ThoughtThread.to_dict()
  - SourceRegistryEntry.to_dict()
  - ChunkRecord.to_dict()
  - MetaLayerRecord.to_dict()
  - ConversationThread.to_dict()
  - ConversationThreadLink.to_dict()
  - ProjectLens.to_dict()
  - ThreadAbstraction.to_dict()
  - ThreadAbstractionLink.to_dict()
  - KnowledgeNode.to_dict()
  - KnowledgeEdge.to_dict()
  - ContextBubble.to_dict()
  - BubbleMembership.to_dict()
  - BubbleEdge.to_dict()
  - BubbleTransition.to_dict()
  - LLMCostEvent.to_dict()
  - ThoughtPacket.to_dict()
  - ConceptNode.to_dict()
  - ConceptEdge.to_dict()
  - TouchOperation.to_dict()
  - SynthesisPacket.to_dict()
  - DimensionSpec.to_dict()
  - ModelRoleBinding.to_dict()
  - ChunkDimensionProfile.to_dict()
  - DimensionRun.to_dict()
inputs:
  - name: record fields
    kind: structured_data
    required: true
    notes: Constructor fields for each dataclass.
outputs:
  - name: serialized_dict
    kind: structured_data
    notes: JSON-ready dictionaries for persistence and runtime payloads.
dependencies:
  - module_id: kernel.foundation.storage
    dependency_type: hard
    notes: Shared serialization helpers and identifiers rely on storage utilities.
used_by:
  - kernel.analysis.analysis_units
  - kernel.meta.meta_layer
  - kernel.knowledge.knowledge_layer
  - recipe.inner_world.v1
  - recipe.world_studio.v1
```

### 3. `kernel.meta.meta_objects`

```yaml
module_id: kernel.meta.meta_objects
name: Meta Layer Vocabulary
layer: kernel
owner: src/conversation_os
status: transitional
version: 0.1.0
contract_version: "1.0"
purpose: Defines the canonical kinds and file mappings for meta-layer records and review statuses.
repo_paths:
  - src/conversation_os/meta_objects.py
entrypoints:
  - META_LAYER_KINDS
  - META_LAYER_FILES
  - REVIEW_STATUSES
inputs: []
outputs:
  - name: meta_layer_kind_list
    kind: structured_data
    notes: Canonical list of supported meta-layer kinds.
  - name: meta_layer_file_map
    kind: structured_data
    notes: Canonical mapping from meta kinds to JSONL filenames.
dependencies: []
used_by:
  - kernel.meta.meta_layer
  - kernel.knowledge.library_tracker
  - recipe.inner_world.v1
```

### 4. `kernel.runtime.cost_tracker`

```yaml
module_id: kernel.runtime.cost_tracker
name: LLM Cost Tracker
layer: kernel
owner: src/conversation_os
status: transitional
version: 0.1.0
contract_version: "1.0"
purpose: Tracks actual and equivalent model usage cost events for runtime accounting and summaries.
repo_paths:
  - src/conversation_os/cost_tracker.py
entrypoints:
  - ensure_cost_tracker_bootstrap(root)
  - load_cost_config(root)
  - estimate_token_count(value)
  - record_actual_cost(...)
  - record_equivalent_cost(...)
  - list_cost_events(root, limit)
  - get_cost_summary(root)
inputs:
  - name: runtime_root
    kind: filesystem
    required: true
    notes: Repo root used to locate cost config and cost event storage.
  - name: cost_event_data
    kind: structured_data
    required: true
    notes: Component, operation, provider, model, token counts, and metadata.
outputs:
  - name: cost_event_record
    kind: structured_data
    notes: Serialized LLMCostEvent rows written to JSONL.
  - name: cost_summary
    kind: structured_data
    notes: Aggregated usage and cost totals.
dependencies:
  - module_id: kernel.foundation.storage
    dependency_type: hard
    notes: Uses shared JSON and JSONL helpers and ID generation.
  - module_id: kernel.foundation.models
    dependency_type: hard
    notes: Serializes LLMCostEvent instances.
used_by:
  - assembly.runtime.pipeline_runner
  - recipe.inner_world.v1
  - builder_support.engineering_guard
```

### 5. `kernel.reasoning.judgment`

```yaml
module_id: kernel.reasoning.judgment
name: Run Classification
layer: kernel
owner: src/conversation_os
status: transitional
version: 0.1.0
contract_version: "1.0"
purpose: Classifies runtime packets into evidence and review states for downstream routing and surface decisions.
repo_paths:
  - src/conversation_os/judgment.py
entrypoints:
  - classify_run(packet)
inputs:
  - name: packet
    kind: structured_data
    required: true
    notes: Runtime packet containing evaluation reports and review state.
outputs:
  - name: run_classification
    kind: structured_data
    notes: Approval, evidence, confidence, novelty, relevance, fidelity, and genericity scores.
dependencies: []
used_by:
  - assembly.runtime.pipeline_runner
  - kernel.knowledge.review_queue
  - recipe.inner_world.v1
```

### 6. `kernel.analysis.analysis_units`

```yaml
module_id: kernel.analysis.analysis_units
name: Analysis Units
layer: kernel
owner: src/conversation_os
status: transitional
version: 0.1.0
contract_version: "1.0"
purpose: Groups chunk index rows into canonical analysis units for downstream synthesis and retrieval.
repo_paths:
  - src/conversation_os/analysis_units.py
entrypoints:
  - load_analysis_units(root)
  - build_analysis_units(root, max_chars, max_chunks)
inputs:
  - name: chunk_index_rows
    kind: runtime_state
    required: true
    notes: Ordered chunk index rows produced by ingest.
  - name: runtime_root
    kind: filesystem
    required: true
    notes: Repo root used to locate the analysis unit store.
outputs:
  - name: analysis_units_rows
    kind: runtime_state
    notes: Canonical grouped analysis units written to JSONL.
  - name: analysis_unit_summary
    kind: structured_data
    notes: Counts for chunk and analysis-unit totals.
dependencies:
  - module_id: kernel.foundation.storage
    dependency_type: hard
    notes: Uses JSONL read/write helpers.
  - module_id: kernel.foundation.models
    dependency_type: soft
    notes: Emits structured rows compatible with shared models and downstream consumers.
used_by:
  - kernel.meta.meta_layer
  - kernel.knowledge.knowledge_layer
  - recipe.inner_world.v1
  - recipe.world_studio.v1
```

## Tranche Notes

- These manifests are intentionally conservative.
- They preserve current repo paths so the migration can start without a filesystem rewrite.
- The first tranche is about proving that module identity is possible, not about finishing the final folder layout.
- The manifest values should be treated as the initial contract, not as immutable truth forever.

## Next Step

Once these six manifests are accepted, the next useful artifacts are:

- a dependency-direction rule sheet
- a state boundary spec
- a versioning policy
- the first recipe file for `recipe.inner_world.v1`
