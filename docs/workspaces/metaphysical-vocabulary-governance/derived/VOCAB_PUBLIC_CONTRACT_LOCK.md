# Vocabulary Governance — Public Contract Lock v1.0.0

**Task:** `VOCAB-001-atomic-obligation-and-governance-lock`  
**Workspace:** `metaphysical-vocabulary-governance`  
**Authority:** [Framework v1.1](../../unified-framework-synthesis/sources/thought-tube-unified-metaphysical-modeling-framework-v1.1.md) §8, §6.10, §22, §27.15  
**Kernel contract consumed:** [`KERNEL_PUBLIC_CONTRACT_LOCK.md`](../../metaphysical-kernel-ontology/derived/KERNEL_PUBLIC_CONTRACT_LOCK.md) `CONTRACT_VERSION=1.1.0`  
**Branch contract consumed:** [`BRANCH_PUBLIC_CONTRACT_LOCK.md`](../../metaphysical-branch-reasoning/derived/BRANCH_PUBLIC_CONTRACT_LOCK.md) `BRANCH_CONTRACT_VERSION=1.0.0`  
**Obligation register:** [`VOCABULARY_OBLIGATION_REGISTER.md`](./VOCABULARY_OBLIGATION_REGISTER.md)

This document locks the **public vocabulary governance contract boundary** after VOCAB-001. Downstream programs (profiles, Conversation/Formation, Shape, Pattern, Agent) may depend on the version, record kinds, mapping semantics, promotion rubric, invariants, and explicit deferrals named here. They must not embed private normalization or identity-collapse logic.

No runtime owner module is introduced by VOCAB-001. The planned owner is `src/conversation_os/metaphysical_vocabulary_governance.py` (`MODULE_ID=vocabulary.metaphysical.governance`), subject to engineering guard approval at VOCAB-002.

---

## Contract version

| Field | Value |
|---|---|
| `VOCAB_CONTRACT_VERSION` | `1.0.0` |
| Semantic authority | Framework v1.1 §8, §6.10, §22, §27.15 |
| Kernel dependency | `1.1.0` (`kernel.metaphysical.records`) |
| Branch dependency | `1.0.0` (`branch.metaphysical.reasoning`) |
| Compatibility | Additive within 1.0.x; breaking changes require contract version bump and parent decision |

---

## Vocabulary levels (§8.1)

| Level | Name | Valid in | Promotion authority |
|---|---|---|---|
| 1 | `kernel` | Universal kernel types | Kernel program only |
| 2 | `governed_shared` | Cross-workspace reuse | Steward + promotion record |
| 3 | `workspace` | Project/organization scope | Workspace steward |
| 4 | `model_local` | Single branch/model | Branch/model steward |
| 5 | `raw_expression` | Capture-time language | Provenance on capture |

Levels are **not** a quality ranking. They define where a term is valid and what governance is required to reuse it elsewhere.

---

## Kernel types consumed (read-only; do not redefine)

| Kernel type | Section | Used by |
|---|---|---|
| `SourceFragment` | §5.1 | Raw expression provenance |
| `Referent` | §5.2 | Token identity boundaries |
| `Scope` | §5.3 | Mapping and entry scope |
| `Provenance` | §5.10 | Mapping, promotion, evolution trace |
| `ModelBranch` | §5.11 | Branch-local vocabulary context |
| `Claim`, `State` | §5.7, §5.4 | Extension safety boundary (must not redefine) |
| `type_id` (opaque reference) | §5.12 | Type extension target until TypeDefinition ships in kernel |

`TypeDefinition` as a first-class kernel record is **deferred** to this vocabulary program. Phase 1 uses governed `type_id` strings with namespace prefixes (`core:`, `shared:`, `workspace:`, `model_local:`).

---

## Branch types consumed (read-only)

| Branch concept | Section | Used by |
|---|---|---|
| Branch-local interpretation | §7 | Model-local vocabulary (level 4) |
| `assess_support` / branch isolation | §7.3 | Branch-local mapping exposure policy |
| Merge without winner | §7.5 | Promotion must not collapse branch readings |

Vocabulary records **branch_context** when a mapping or entry is model-local. Branch-local mappings are not exposed as global by default (§8.4).

---

## Public record contracts

### 1. VocabularyEntry — governed term record

**Purpose:** Register a term at a vocabulary level with stewardship and scope.

| Field | Type | Required | Notes |
|---|---|---|---|
| `id` | `str` | yes | Stable term identifier (`namespace:local_name`) |
| `namespace_level` | `VocabularyLevel` | yes | One of five levels |
| `display_labels` | `dict[str, str]` | no | Locale → label (view only) |
| `definition` | `str` | yes for levels 2–4 | Human-readable definition |
| `scope_id` | `str` | yes for workspace/model_local | |
| `branch_context` | `str` | when level=model_local | |
| `steward` | `str` | yes for governed_shared | |
| `governance_status` | `GovernanceStatus` | yes | §22 governance axis |
| `maturity_status` | `MaturityStatus` | yes | §22 maturity axis |
| `epistemic_status` | `EpistemicStatus` | yes | §22 epistemic axis |
| `version` | `str` | yes | Semver or dated version |
| `provenance_id` | `str` | yes | |

**Invariants:** Governance approval does not imply epistemic resolution (§22).

---

### 2. RawExpression — level 5 capture

| Field | Type | Required |
|---|---|---|
| `id` | `str` | yes |
| `text` | `str` | yes — preserved **verbatim** |
| `source_fragment_id` | `str` | yes |
| `captured_at` | `str` | yes |
| `provenance_id` | `str` | yes |
| `alias_of` | `str` | no |

**Invariants:** Forced normalization is forbidden (§6.10, §27.15).

---

### 3. TermMapping — §8.3

| Field | Type | Required |
|---|---|---|
| `id` | `str` | yes |
| `source_type_or_expression` | `str` | yes |
| `target_type` | `str \| null` | no when abstaining |
| `mapping_kind` | `MappingKind` | yes |
| `scope_id` | `str` | yes |
| `branch_context` | `str` | when branch-local |
| `confidence` | `float` | yes |
| `provenance_id` | `str` | yes |
| `created_by` | `str` | yes |
| `governance_status` | `GovernanceStatus` | yes |
| `version` | `str` | yes |
| `rationale` | `str` | yes |
| `identity_confirmation` | `str` | only when establishing identity |

**MappingKind values:**

| Value | Meaning | Identity implication |
|---|---|---|
| `equivalent` | Same intended meaning in scope | Identity only with `identity_confirmation` |
| `narrower` | Source is more specific | No identity |
| `broader` | Source is more general | No identity |
| `overlaps` | Partial overlap | No equivalence |
| `analogous` | Similar role, different concept | No identity |

**Invariants:**
- Mapping is a **record**, not a rewrite.
- Lookup MUST return source expression and mapping metadata; canonical label is a **view**, not a silent substitution.
- `analogous` and `overlaps` MUST NOT behave as identity.

---

### 4. PromotionRecord — §8.2

| Field | Type | Required |
|---|---|---|
| `id` | `str` | yes |
| `source_term` | `str` | yes |
| `source_level` | `VocabularyLevel` | yes |
| `target_level` | `VocabularyLevel` | yes |
| `target_term` | `str` | when approved |
| `rubric` | `PromotionRubric` | yes |
| `review_outcome` | `approved \| declined \| pending` | yes |
| `decline_reason` | `str` | when declined |
| `steward` | `str` | yes |
| `provenance_id` | `str` | yes |
| `affected_records` | `list[str]` | when approved |

**Promotion rubric criteria (all must be satisfied for approval):**

1. `stable_usage`
2. `clear_definition`
3. `distinct_identity`
4. `demonstrated_reuse`
5. `compatibility_with_existing_terms`
6. `assigned_steward`
7. `review_outcome = approved`

**Invariants:** Promotion is **optional**. Declined promotion MUST NOT invalidate the local term.

---

### 5. DeprecationRecord — §8.6

| Field | Type | Required |
|---|---|---|
| `id` | `str` | yes |
| `deprecated_term` | `str` | yes |
| `replacement_term` | `str` | no |
| `effective_scope` | `str` | yes |
| `migration_plan` | `str` | yes |
| `reversible` | `bool` | yes |
| `provenance_id` | `str` | yes |

---

### 6. TypeExtension — §8.5

| Field | Type | Required |
|---|---|---|
| `id` | `str` | yes |
| `parent_types` | `list[str]` | yes |
| `namespace_level` | `VocabularyLevel` | yes |
| `constraints` | `list[str]` | no |
| `disjoint_with` | `list[str]` | no |
| `validation_result` | `valid \| invalid` | on validation |

**Invariants:** MUST NOT redefine `Claim`, `State`, `SourceFragment`, or other kernel record semantics.

---

### 7. EvolutionMigrationReport — §8.6

| Field | Type | Required |
|---|---|---|
| `id` | `str` | yes |
| `prior_definition` | `str` | yes |
| `new_definition` | `str` | yes |
| `compatibility_class` | `str` | yes |
| `affected_records` | `list[str]` | yes |
| `migration_plan` | `str` | yes |
| `reversible` | `bool` | yes |
| `semantic_loss_warnings` | `list[str]` | yes |
| `stale_dependents` | `list[str]` | yes |
| `steward` | `str` | yes |
| `review_decision` | `str` | yes |
| `provenance_id` | `str` | yes |

**Invariants:** Prior definitions remain addressable; destructive in-place type edit is forbidden.

---

## Operation contracts (planned; VOCAB-002+)

| Operation | Purpose | Introduced |
|---|---|---|
| `register_vocabulary_entry` | Create governed term | VOCAB-002 |
| `capture_raw_expression` | Level-5 verbatim capture | VOCAB-002 |
| `create_term_mapping` | Non-destructive mapping record | VOCAB-002 |
| `lookup_with_mapping` | Return source + metadata | VOCAB-002 |
| `propose_promotion` | Start promotion workflow | VOCAB-003 |
| `review_promotion` | Approve/decline with rubric | VOCAB-003 |
| `validate_type_extension` | Extension safety check | VOCAB-002 |
| `publish_evolution_report` | Version change with impact | VOCAB-003 |

---

## Failure and absence behavior

| Condition | Behavior |
|---|---|
| `mapping_kind=analogous` or `overlaps` | MUST NOT imply identity or equivalence |
| `equivalent` without `identity_confirmation` | Mapping only; no identity collapse |
| Ambiguous mapping (`confidence` below threshold or `target_type=null`) | Abstain from canonical substitution; preserve raw |
| Promotion declined | Local term remains usable in valid scope |
| Kernel redefinition attempted | `kernel_redefinition_forbidden` |
| Branch-local term without promotion | MUST NOT expose as global |
| Disjoint parent types | `disjoint_type_violation` |

---

## Forbidden interpretations

- Treating `analogous` as `same_as`
- Forced normalization of raw expressions
- Promoting branch-local terms without governed promotion record
- Using mapping fluency or majority as identity proof
- Redefining kernel record kinds via workspace extension
- Canonical identity implying canonical interpretation (§8.4)

---

## Outcome tables (fixture reference)

| Table | Fixture file | Section |
|---|---|---|
| Mapping outcomes | `tests/fixtures/metaphysical_vocabulary/mapping_outcome_table.json` | §8.3 |
| Promotion outcomes | `tests/fixtures/metaphysical_vocabulary/promotion_outcome_table.json` | §8.2 |
| Extension safety | `tests/fixtures/metaphysical_vocabulary/extension_safety_outcome_table.json` | §8.5 |
| Preservation | `tests/fixtures/metaphysical_vocabulary/preservation_outcome_table.json` | §6.10, §27.15 |
| Level classification | `tests/fixtures/metaphysical_vocabulary/level_classification_outcome_table.json` | §8.1 |

Master index: `tests/fixtures/metaphysical_vocabulary/vocab_contract_fixtures.json`

---

## Deferred items (not in 1.0.0 public surface)

| Item | Reason |
|---|---|
| `TypeDefinition` kernel record integration | Kernel defers; vocabulary owns until extension |
| Automated promotion scoring | Steward review required in Phase 1 |
| Cross-workspace namespace federation | Workspace scope only |
| Runtime registry implementation | VOCAB-002 after guard approval |

---

## Residual risks

| Risk ID | Description | Mitigation |
|---|---|---|
| VOCAB-R-001 | Namespace prefix conventions may need parent harmonization | Document prefixes; revisit at VOCAB-002 |
| VOCAB-R-002 | Confidence threshold for abstention unspecified numerically | Consumer supplies threshold in Phase 1 |
| VOCAB-R-003 | Shape/Pattern stale propagation owner unspecified | Evolution report lists stale_dependents; consumer owns refresh |

---

## Verification commands (VOCAB-001)

```bash
python3 tools/conversation_os.py repo-overview refresh
python3 tools/conversation_os.py engineering-guard assess \
  --request "VOCAB-001 contract document and fixtures" \
  --purpose "Deliver vocabulary contract tables before runtime; no Python source changes." \
  --proposed-paths "docs/workspaces/metaphysical-vocabulary-governance/derived/VOCAB_PUBLIC_CONTRACT_LOCK.md,tests/fixtures/metaphysical_vocabulary/vocab_contract_fixtures.json"
pytest -q tests/test_vocab_contract_fixtures.py
```

---

## Consumer boundary

Profile and application programs may draft against this contract. They cannot pass their own G5 integration until VOCAB-005 publishes merge SHA evidence. Until then, consume `VOCAB_CONTRACT_VERSION=1.0.0` and this document as the semantic boundary.
