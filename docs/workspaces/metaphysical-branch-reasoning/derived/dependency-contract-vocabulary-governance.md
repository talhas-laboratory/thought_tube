# Dependency Contract: Branch Reasoning → Vocabulary Governance

**Provider:** `metaphysical-branch-reasoning`  
**Consumer:** `metaphysical-vocabulary-governance`  
**Status:** **Released** — Branch G5 (`BRANCH-005`)  
**Provider contract version:** `1.0.0`  
**Kernel consumed:** `1.1.0` (`512236d4b089d0a4d04821cca3d068a2d0a539f4`)
**Release packet:** [`BRANCH_RELEASE_DEPENDENCY_CONTRACT.json`](./BRANCH_RELEASE_DEPENDENCY_CONTRACT.json)

## Provider supplies

Branch-scoped inheritance reads (§7.2), four-valued support assessment (§7.3), typed conflict classification (§7.4), merge assessment without winner selection (§7.5), and candidate-only inference with explicit `both` policies (§7.6).

## Consumer obligations

- Preserve branch-local vocabulary interpretations; do not promote one branch mapping as universal truth
- Pin `provider_contract_version` and `release_git_revision` in VOCAB-005
- Use merge/inference outputs as inspectable reports, not silent normalization
- Respect kernel `BranchMembership` and scope facts; vocabulary must not bypass branch isolation

## Compatibility

| Change type | Policy |
|---|---|
| Additive optional fields within `1.0.x` | Consumer may adopt when ready |
| New `ConflictKind` or outcome literal | Minor version bump; consumer gate regression |
| Breaking semantic change | Major version bump + parent decision + consumer gate regression |

## Failure / absence

| Condition | Branch behavior |
|---|---|
| Cross-branch claim without inheritance | Excluded from support assessment |
| Merge of contradictory claims | `merge_verdict=incompatible`; conflicts listed; no winner |
| Inference `output_status` not `candidate` | `InvalidInferenceOutputStatusError` |
| `both` with `abstain` policy | Empty `output_claims`; inspectable abstention |

## Verification consumed from provider

- [`BRANCH_CONFORMANCE_COVERAGE.json`](./BRANCH_CONFORMANCE_COVERAGE.json)
- Table fixtures under `tests/fixtures/metaphysical_branch/`
- Consumer smoke: `tests.test_metaphysical_branch_consumer_smoke::test_vocabulary_governance_consumer_preserves_branch_local_support`

## Known provider limits (Phase 1)

- `BranchEnsemble` weighting (§7.7) not published; weights are task-relative when supplied by consumer
- Merge does not implement a global truth selector
- `max_depth` multi-proposition traversal is single-group only; `max_depth < 1` abstains
- Lifecycle transition policy inherited from kernel deferral

Consumer acknowledgment: [`branch-provider-acknowledgment.md`](../../metaphysical-vocabulary-governance/derived/branch-provider-acknowledgment.md)
