# Kernel Runtime Operations — KERNEL-003

**Task:** `KERNEL-003-minimal-kernel-runtime-operations`  
**Owner module:** `src/conversation_os/metaphysical_kernel_runtime.py`  
**SDK surface:** `FoundationApplicationSdk.record_identity_uncertainty`

## New public operations

| Operation | Framework | Purpose |
|---|---|---|
| `assert_relation_instance` | §5.6 | Append a validated `RelationInstance`; validates bundle before persistence |
| `record_identity_uncertainty` | §5.13 | Conservative uncertain-identity path: `possibly_same_as` relation, never Referent merge |

## Invariants

- Validation runs against the prospective bundle; **no events appended** on failure.
- `same_as` is **rejected** at runtime until explicit confirmation workflow exists (matches migration downgrade policy).
- Left and right referents must exist and differ.
- Identity relations use `type_id=kernel:identity:possibly_same_as` (or `distinct_from`).

## Consumer path

Applications use the SDK (not private store access):

```python
sdk.record_identity_uncertainty(
    left_referent_id="ref_a",
    right_referent_id="ref_b",
    provenance_id=prov_id,
    confidence=0.6,
    rationale="Alias overlap",
)
```

## Verification

```bash
pytest -q tests/test_metaphysical_kernel_runtime.py
python3 tools/conversation_os.py foundation review
```

## Residual risk

Lifecycle transition operations and staleness propagation remain deferred to KERNEL-004 / KERNEL-005 per contract lock.
