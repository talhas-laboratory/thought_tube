# T10-06 Pattern, AntiMatch, and transfer reasoning

**Task:** `UMF-T10-06-PATTERN-ANTIMATCH`  
**Wave:** `UMF-T10-WAVE-03-STRUCTURAL-INTEL`  
**Date:** 2026-07-22  
**Owner module:** `src/conversation_os/shape_candidate_retrieval.py`

## Verdict

Pattern derivation and separated reasoning records now live on the Shape
candidate retrieval owner. Patterns are derived abstractions over declared
Shape population refs; instantiating Shapes are never mergeable from Pattern
alone.

## API

| Symbol | Role |
|---|---|
| `derive_pattern_from_shapes` | Build `PatternRecord` from ≥2 declared Shape members |
| `classify_shape_pair` | Emit one of `candidate_match` / `validated_membership` / `anti_match` / `transfer_hypothesis` / `rejected_analogy` |
| `revise_anti_match_record` | Branch/scope-aware revision (`active` / `revised` / `withdrawn`) without deleting history |

## Invariants

- `merge_shapes_forbidden` is always `True` on Pattern and reasoning records
- Each invariant requires an `abstraction_contract` + evidence refs
- Low-vocabulary structural pairs can become `candidate_match` / `transfer_hypothesis`
- Lexically similar / structurally incompatible pairs become `anti_match` (with optional projection for `evaluate_anti_match`)
- Rejected analogies are preserved as first-class records

## Verification

```bash
. .venv/bin/activate
python -m pytest tests/test_shape_candidate_retrieval.py -k "pattern or classify or derive or merge" -q
```

Result: **3 passed**.

## Residual (owned by T10-07)

Three pre-existing bundle tests still fail because catalog readiness returns
before `shape_retrieval` is attached (`KeyError: shape_retrieval`) and one
AntiMatch hard-reject path through `build_retrieval_bundle`. Those are the
Wave 3 retrieval-repair targets, not this Pattern typing slice.
