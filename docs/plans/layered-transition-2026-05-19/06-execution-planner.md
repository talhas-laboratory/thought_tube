# Transition Execution Planner

Date: 2026-05-19

## Purpose

This document is the live execution surface for the layered transition.

It tracks:

- what has already been implemented
- what is next
- what is blocked
- what verification has been completed

It is intentionally operational rather than philosophical.

## Current State

Completed implementation slices:

- `storage.py`
  - explicit module identity
  - explicit public API
  - regression test
- `models.py`
  - explicit module identity
  - explicit public model export surface
  - regression test
- `cost_tracker.py`
  - explicit module identity
  - explicit public API
  - regression test
- `meta_layer.py`
  - explicit module identity
  - explicit public API for the owner surface
  - regression test
- `analysis_units.py`
  - explicit module identity
  - explicit public API
  - regression test
- `runtime_pipeline.py`
  - explicit assembly module identity
  - explicit public API
  - regression test
- `pipelines.py`
  - explicit assembly module identity
  - explicit public API
  - regression test
- `pipeline_runner.py`
  - explicit assembly module identity
  - explicit public API
  - regression test
- `analysis.py`
  - explicit substrate module identity
  - explicit public API
  - regression test
- `conversation_deltas.py`
  - explicit substrate module identity
  - explicit public API
  - regression test
- `conversation_threads.py`
  - explicit substrate module identity
  - explicit public API
  - regression test
- `Inner World surface recipe`
  - loadable recipe in current product owner path
  - recipe materialization test

## Verified So Far

Completed regression lanes:

- targeted storage boundary tests
- targeted models boundary tests
- targeted cost-tracker boundary tests
- targeted meta-layer boundary tests
- targeted analysis-units boundary tests
- targeted runtime-pipeline boundary tests
- targeted pipeline-spec boundary tests
- targeted pipeline-runner boundary tests
- targeted analysis boundary tests
- targeted conversation-deltas boundary tests
- targeted conversation-threads boundary tests
- targeted surface-recipe materialization tests
- runtime pipeline regression lane
- cost tracking regression lane
- personal interface regression lane
- worldbuilding studio regression lane
- full `tests/test_conversation_os.py`
- full `tests/test_personal_interface.py`
- full `tests/test_worldbuilding_studio.py`

## Active Tranche 1 Status

### Completed

- `kernel.foundation.storage`
- `kernel.foundation.models`
- `kernel.runtime.cost_tracker`
- `kernel.meta.meta_layer`
- `kernel.analysis.analysis_units`
- `kernel.analysis.session_analysis`
- `kernel.analysis.conversation_deltas`
- `kernel.analysis.conversation_threads`
- `recipe.inner_world.v1` transitional loader
- `assembly.runtime.runtime_pipeline`
- `assembly.runtime.pipelines`
- `assembly.runtime.pipeline_runner`

### Next In Sequence

- `kernel.reasoning.judgment`
- `kernel.meta.meta_objects`

### Still Pending

- `kernel.reasoning.judgment`
- `kernel.meta.meta_objects`

### Blocked or Deferred

- `meta_objects.py` direct formalization
  - reason: engineering guard currently prefers the nearer owner path
  - current mitigation: formalize `meta_layer.py` first, then revisit
- `judgment.py` direct formalization
  - reason: engineering guard currently prefers nearer owner paths such as `runtime_pipeline.py` or `product_inner_world.py`
  - current mitigation: formalize the owner-adjacent assembly path first, then revisit
  - latest status: still blocked after reassessment at the current checkpoint
- `meta_objects.py` direct formalization reassessment
  - latest status: still blocked after reassessment at the current checkpoint

## Execution Order

1. Reassess whether `judgment.py` can now be formalized directly.
2. Reassess whether `meta_objects.py` can now be formalized directly.
3. If either remains blocked, decide whether to complete tranche 1 through owner-approved adjacent surfaces instead of forcing the direct file boundary.
4. Choose the next clean owner-approved module on the substrate path or stop at this checkpoint and cut a new execution tranche.

## Current Checkpoint

This checkpoint leaves the transition in a materially stronger state:

- core kernel foundations are explicit
- the first substrate-processing module is explicit
- the first surface recipe is loadable
- the runtime assembly path is now explicit across config, specs, and execution
- direct formalization of `judgment.py` and `meta_objects.py` remains blocked by ownership rules

The most likely next execution tranche is:

- either formalize one of the owner-recommended paths around `judgment`
- or start tranche 2 through already-approved owner modules instead of forcing the remaining tranche 1 files
- the substrate path from session analysis through deltas and threads is now explicit enough to support a broader verification checkpoint
- the broader verification checkpoint has now passed

## Completion Rule For A Slice

A slice is complete only when:

- guard approved the edit surface
- module boundary is explicit in code
- compatibility is preserved
- regression tests passed
- planner status is updated

## Notes

- Do not force new owner paths until the current ownership constraints are cleared by the guard.
- Prefer owner-approved in-place formalization over speculative extraction.
- Preserve current runtime behavior at all times.
