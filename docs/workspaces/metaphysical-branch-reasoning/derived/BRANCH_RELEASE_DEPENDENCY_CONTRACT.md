# Branch Release Dependency Contract — G5

**Task:** `BRANCH-005-release-branch-dependency-contract`  
**Provider:** `metaphysical-branch-reasoning`  
**Contract version:** `1.0.0`  
**Machine packet:** [`BRANCH_RELEASE_DEPENDENCY_CONTRACT.json`](./BRANCH_RELEASE_DEPENDENCY_CONTRACT.json)

This document is the **consumable G5 release** for Phase 1 branch reasoning. Vocabulary and later profile programs may pass integration gates against the version and SHA named here.

## Release identity

| Field | Value |
|---|---|
| `provider_contract_version` | `1.0.0` |
| `kernel_contract_version_consumed` | `1.1.0` |
| `compatibility_class` | Additive within `1.0.x` |
| `release_git_revision` | `e3784b72f7f51bea8f62a6637419634d6e096fe8` |
| Conformance evidence | [`BRANCH_CONFORMANCE_COVERAGE.json`](./BRANCH_CONFORMANCE_COVERAGE.json) |

## What consumers may depend on

- Public contract lock ([`BRANCH_PUBLIC_CONTRACT_LOCK.md`](./BRANCH_PUBLIC_CONTRACT_LOCK.md)) v1.0.0
- Runtime module `src/conversation_os/metaphysical_branch_reasoning.py`
- Operations documented in [`BRANCH_RUNTIME_OPERATIONS.md`](./BRANCH_RUNTIME_OPERATIONS.md)
- Table and adversarial fixtures under `tests/fixtures/metaphysical_branch/`

## Supported operations

| Operation | Function | Section |
|---|---|---|
| InheritanceQuery | `resolve_inheritance` | §7.2 |
| SupportAssessment | `assess_support` | §7.3 |
| ConflictRecord | `classify_conflict` | §7.4 |
| MergeAssessment | `assess_merge` | §7.5 |
| InferenceContext/Result | `run_inference` | §7.6 |

## Core invariants (non-negotiable)

1. Inheritance is a read rule — never physical duplication
2. Support is four-valued; `both` is never collapsed implicitly
3. Negation is explicit (`polarity=negative`)
4. Merge reports conflicts; **never selects a winner**
5. Inference output is always `candidate` epistemic status
6. Branch-neutral sources may share IDs across branches (§27.16)
7. Ensemble weights (when used) are **task-relative** — not a global truth selector

## Forbidden interpretations

- Using merge verdict to silently adopt one branch over another
- Resolving `both` by fluency, majority, or narrative coherence
- Treating cross-branch coexistence as equivalence or causality
- Promoting inference output to `supported`, `committed`, or `state`
- Using branch ensemble weight as universal truth probability

## Known Phase 1 limits

| Risk | Limit |
|---|---|
| BRANCH-R-001 | Scope hierarchy inheritance compatibility unspecified |
| BRANCH-R-002 | `BranchEnsemble` normalization deferred; consumer supplies weights |
| BRANCH-R-005 | `max_depth < 1` abstains; multi-proposition depth traversal not published |

## Verification ladder

```bash
pytest -q tests/test_metaphysical_branch_reasoning.py tests/test_metaphysical_branch_conformance.py \
  tests/test_metaphysical_branch_consumer_smoke.py tests/test_branch_release_contract.py \
  tests/test_metaphysical_kernel_contracts.py tests/test_metaphysical_kernel_runtime.py
```

## Consumer smoke proof

| Consumer | Test |
|---|---|
| `metaphysical-vocabulary-governance` | `test_vocabulary_governance_consumer_preserves_branch_local_support` |

## Downstream contract

| Consumer | Provider contract | Consumer acknowledgment |
|---|---|---|
| Vocabulary governance | [`dependency-contract-vocabulary-governance.md`](./dependency-contract-vocabulary-governance.md) | [`branch-provider-acknowledgment.md`](../../metaphysical-vocabulary-governance/derived/branch-provider-acknowledgment.md) |

## Kernel dependency

Branch G5 consumes Kernel G5 (`1.1.0`, revision `512236d4b089d0a4d04821cca3d068a2d0a539f4`). See [`kernel-provider-acknowledgment.md`](./kernel-provider-acknowledgment.md).
