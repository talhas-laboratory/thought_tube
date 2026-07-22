# ADR: Deprecate legacy Shape profile id

**Status:** accepted for Wave 0–1  
**Date:** 2026-07-22  
**Task:** `UMF-T10-19-RELEASE-DISCIPLINE`  
**Related:** `UMF-T10-01-SHAPE-AUTHORITY`

## Decision

Canonical Shape profile id is:

```text
profile:shape
```

Legacy id:

```text
profile:shape_and_semantic_addressing
```

must be treated as **candidate-only adapter identity** until retirement.

## Why

After T10-00 integration:

- `metaphysical_kernel_profile_registry.py` on the remediation spine defines `SHAPE_PROFILE_ID = "profile:shape"`.
- `shape_projection_reader.py` still declares `CANONICAL_SHAPE_PROFILE_ID = "profile:shape_and_semantic_addressing"` and abstains when that legacy id is unregistered.
- Leaving both as “canonical” recreates the authority split T10-01 exists to close.

## Migration window

| Date | Rule |
|---|---|
| 2026-07-22 | Deprecation recorded; dual-id detection is a release warning. |
| Through T10-01 completion | Reader/SDK may keep a dated legacy adapter; promoted/canonical reads must not use the legacy id. |
| After T10-01 acceptance | New code must not introduce the legacy id. |
| Target retirement | Remove legacy adapter once T10-01 tests prove typed abstention + bootstrap for `profile:shape` and no production caller requires the old id. |

## Enforcement

1. T10-01 owns the reader/SDK cutover and tests.
2. Release manifests record `profile_revision` so dual-id drift is visible.
3. Overview/module manifests for disclosure/Shape imports must remain present (T10-19).

## Non-goals

- This ADR does not enable disclosure rollout flags (T10-08).
- This ADR does not complete canonical Population mapping (T10-02/03).
