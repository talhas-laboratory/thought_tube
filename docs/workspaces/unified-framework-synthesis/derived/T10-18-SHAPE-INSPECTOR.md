# T10-18 Shape inspector (first slice)

**Task:** `UMF-T10-18-SHAPE-INSPECTOR`  
**Wave:** `UMF-T10-WAVE-04-SAFE-AGENT-USE`  
**Date:** 2026-07-22  
**Owner:** `shape_projection_reader.py`

## Scope

This slice adds a bounded read-only `inspect_shape_projections` helper for already-filtered Shape projections.

## Contract

- Selects by projection id, branch, scope, and source refs.
- Caps projections, entities, qualities, evidence spans, and competing views.
- Separates evidence spans from interpretation metadata.
- Returns entities, qualities, relations, feedback, lifecycle, authority, provenance, and competing candidate/AntiMatch views.
- Does not expose correction, approval, rejection, retraction, promotion, or full-ocean rendering.

## Verification

- `pytest tests/test_shape_projection_reader.py`

Result: `14 passed`.

## Residuals

- Visual graph disclosure and correction action capabilities remain future surface slices.
- Canonical Shape inspection will deepen once canonical projection rows are populated beyond the legacy candidate adapter.
