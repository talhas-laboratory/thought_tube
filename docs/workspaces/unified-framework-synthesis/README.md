# Unified Metaphysical Framework — Foundation Workspace

**Workspace ID:** `unified-framework-synthesis`  
**Status:** Active — canonical foundation and schema-lock phase  
**Coordination authority:** canonical workspace service  
**Git projection:** `docs/workspaces/unified-framework-synthesis/`

This workspace is the focal point for translating the unified metaphysical modeling framework into an executable software foundation and application-building platform.

The workspace has one normative source:

> [`Thought Tube Unified Metaphysical Modeling Framework v1.1`](./sources/thought-tube-unified-metaphysical-modeling-framework-v1.1.md)

All earlier framework documents remain preserved as intellectual lineage, comparison material, migration evidence, and implementation history. They are not parallel runtime frameworks.

---

## Quick start (foreign agent)

**Protocol:** [`docs/workspaces/WORKSPACE-AGENT-PROTOCOL.md`](../WORKSPACE-AGENT-PROTOCOL.md)

```bash
# 0. Repo + projection freshness
git fetch origin && git checkout main && git pull origin main
source ~/.config/inner-space-workspace.env 2>/dev/null || true

# 1. Live workspace first
python3 tools/workspace_coordination.py context \
  --workspace-id unified-framework-synthesis \
  --agent-id <agent> --surface <surface> --session-id <session>

python3 tools/workspace_projection_sync.py check --workspace-id unified-framework-synthesis

# 2. Canonical framework source
cat docs/workspaces/unified-framework-synthesis/sources/thought-tube-unified-metaphysical-modeling-framework-v1.1.md

# 3. Handoff and build plan
cat docs/workspaces/unified-framework-synthesis/derived/handoff.md
cat docs/workspaces/unified-framework-synthesis/derived/foundation-build-plan.md
cat docs/workspaces/unified-framework-synthesis/derived/program-workspace-hierarchy-plan.md
cat docs/workspaces/unified-framework-synthesis/derived/TEN_OUT_OF_TEN_GAP_PROGRAM.md

# 4. Published continuity projection (after sync)
cat docs/workspaces/unified-framework-synthesis/CONTINUITY.md

# 5. Focused task pack
cat docs/workspaces/unified-framework-synthesis/continuity/task-pack.md
```

Machine-readable catalog: [`manifest.json`](./manifest.json)
Sync contract: [`derived/sync-contract.md`](./derived/sync-contract.md)

Execution board: [`docs/workboards/unified-metaphysical-foundation/`](../../workboards/unified-metaphysical-foundation/README.md)

## Program hierarchy

This workspace is the parent program. The first active child workspaces are:

- [`metaphysical-kernel-ontology`](../metaphysical-kernel-ontology/README.md)
- [`metaphysical-branch-reasoning`](../metaphysical-branch-reasoning/README.md)
- [`metaphysical-vocabulary-governance`](../metaphysical-vocabulary-governance/README.md)

The full program catalog and deferred children are declared in [`manifest.json`](./manifest.json) and governed by the [program workspace hierarchy plan](./derived/program-workspace-hierarchy-plan.md).

---

## Normative foundation

| Document | Status | Purpose |
|---|---|---|
| [`sources/thought-tube-unified-metaphysical-modeling-framework-v1.1.md`](./sources/thought-tube-unified-metaphysical-modeling-framework-v1.1.md) | **Canonical** | Kernel, profiles, applications, invariants, lifecycles, architecture, build order, tests, and migration |
| [`derived/foundation-build-plan.md`](./derived/foundation-build-plan.md) | Active execution bridge | Converts the normative paper into bounded implementation work |
| [`derived/program-workspace-hierarchy-plan.md`](./derived/program-workspace-hierarchy-plan.md) | Proposed program operating model | Defines the parent workspace, nine child programs, workboards, dependencies, gates, rollup, and rollout |
| [`derived/TEN_OUT_OF_TEN_GAP_PROGRAM.md`](./derived/TEN_OUT_OF_TEN_GAP_PROGRAM.md) | Current system-level gap authority | Defines the integration, population, retrieval, safety, benchmark, operations, and release work required for a ten-out-of-ten system candidate |
| [`derived/T10-00-RECONCILIATION-MATRIX.md`](./derived/T10-00-RECONCILIATION-MATRIX.md) | Wave 0 integration authority | Declares merge spine, Population import, overlap dispositions, and same-checkout verification |
| [`derived/ADR-SHAPE-PROFILE-ID-DEPRECATION.md`](./derived/ADR-SHAPE-PROFILE-ID-DEPRECATION.md) | Accepted Wave 0 ADR | Deprecates legacy `profile:shape_and_semantic_addressing` in favor of `profile:shape` |
| [`derived/T10-WAVE-01-GOLDEN-TRACE.md`](./derived/T10-WAVE-01-GOLDEN-TRACE.md) | Wave 1 exit evidence | Archives the hermetic ingest→canonical-apply→retrieve (+rollback) golden production trace |
| [`derived/T10-04-CORPUS-OCEAN-READINESS.md`](./derived/T10-04-CORPUS-OCEAN-READINESS.md) | Wave 2 T10-04 evidence | CorpusCatalog ocean readiness: family digests, ambiguous-placement fail-closed, legacy candidate-only, dependency indexes |
| [`derived/T10-05-INDEX-CONTRACTS.md`](./derived/T10-05-INDEX-CONTRACTS.md) | Wave 2 T10-05 evidence | Hybrid index port readiness on CorpusCatalog: replaceable ports, fail-closed required indexes, no full-ocean scan |
| [`derived/T10-09-TEMPORAL-REVISION.md`](./derived/T10-09-TEMPORAL-REVISION.md) | Wave 2 T10-09 evidence | Content-addressed corpus epoch, stale projection rules, and contradiction surfacing |
| [`derived/T10-06-PATTERN-ANTIMATCH.md`](./derived/T10-06-PATTERN-ANTIMATCH.md) | Wave 3 T10-06 evidence | Pattern derivation + separated candidate/membership/AntiMatch/transfer records; merge forbidden |
| [`derived/T10-07-SHAPE-RETRIEVAL.md`](./derived/T10-07-SHAPE-RETRIEVAL.md) | Wave 3 T10-07 evidence | Typed shape_retrieval always present; focused audit failures green |
| [`derived/T10-14-FIRST-COMPARATIVE-BENCHMARK.md`](./derived/T10-14-FIRST-COMPARATIVE-BENCHMARK.md) | Wave 3 T10-14 evidence | First structural-vs-lexical/vector comparative benchmark; thresholds locked pre-eval |
| [`derived/T10-08-DISCLOSURE-ACTIVATION.md`](./derived/T10-08-DISCLOSURE-ACTIVATION.md) | Wave 4 T10-08 evidence | Bridge-only disclosure/receipt shadow activation with config-only rollback |
| [`derived/T10-12-AUTH-PRIVACY.md`](./derived/T10-12-AUTH-PRIVACY.md) | Wave 4 T10-12 evidence | Fail-closed Shape-aware retrieval and evidence-port authorization with audit-only denials |
| [`derived/T10-13-CONCURRENCY.md`](./derived/T10-13-CONCURRENCY.md) | Wave 4 T10-13 evidence | Shape Population optimistic record versions, stale-writer conflicts, and idempotent human approval replay |
| [`derived/T10-17-AGENT-HARNESS.md`](./derived/T10-17-AGENT-HARNESS.md) | Wave 4 T10-17 evidence | Minimal intent-oriented agent harness over the application SDK with typed statuses and privileged tools excluded |
| [`derived/T10-18-SHAPE-INSPECTOR.md`](./derived/T10-18-SHAPE-INSPECTOR.md) | Wave 4 T10-18 evidence | Bounded Shape inspector separating evidence, interpretation, provenance, authority, and competing views |
| [`derived/T10-10-CYBERNETIC-COMPILE.md`](./derived/T10-10-CYBERNETIC-COMPILE.md) | Wave 5 T10-10 evidence | Minimal executable cybernetic compilation into deterministic IR with abstention and no runtime side effects |
| [`derived/T10-11-OUTCOME-LEARNING.md`](./derived/T10-11-OUTCOME-LEARNING.md) | Wave 5 T10-11 evidence | Offline outcome-learning policy proposals with safety/minority regression blocks and no runtime mutation |
| [`continuity/task-pack.md`](./continuity/task-pack.md) | Active handoff | Supplies the next focused implementation context |

## Historical framework sources

| Framework | Current status | Original path | Workspace copy |
|-----------|--------|----------------|----------------|
| **MTSF** | Operational predecessor; migration source | [`docs/frameworks/metaphysical-thought-space/`](../../frameworks/metaphysical-thought-space/README.md) | Use original tree |
| **SDS** | Historical dynamics design; migration source | [`docs/frameworks/system-dynamic-signature/SDS-v1.0-report.md`](../../frameworks/system-dynamic-signature/SDS-v1.0-report.md) | [`sources/sds-v1.0-report.md`](./sources/sds-v1.0-report.md) |
| **ThoughtShape** | Historical semantic grammar; migration source | [`docs/frameworks/thought-shape/ThoughtShape-framework-v1.md`](../../frameworks/thought-shape/ThoughtShape-framework-v1.md) | [`sources/thoughtshape-framework-v1.md`](./sources/thoughtshape-framework-v1.md) |

---

## Historical synthesis and comparison

| Document | Path |
|----------|------|
| Three-framework comparison (Jul 8) | [`sources/three-framework-comparative-evaluation.md`](./sources/three-framework-comparative-evaluation.md) |
| Unified pre-build synthesis — superseded by v1.1 | [`sources/unified-framework-synthesis.md`](./sources/unified-framework-synthesis.md) |
| Product thesis index | [`docs/product-thesis/07-unified-framework-synthesis.md`](../../product-thesis/07-unified-framework-synthesis.md) |

---

## Deep analyses (chat thread — not elsewhere)

| Analysis | Path |
|----------|------|
| **Primitive decomposition** (~120–140 pieces, pre-rearrange) | [`analyses/framework-primitive-decomposition.md`](./analyses/framework-primitive-decomposition.md) |
| **Epistemology & overlap** | [`analyses/epistemology-and-overlap.md`](./analyses/epistemology-and-overlap.md) |
| **Fresh comparison** (Jul 10, epistemology + chat layers) | [`analyses/fresh-comparison-jul-10.md`](./analyses/fresh-comparison-jul-10.md) |
| **SDS non-movement problem** | [`analyses/sds-non-movement-problem.md`](./analyses/sds-non-movement-problem.md) |
| **Reasoning-step capture** (Thought Trace) | [`analyses/reasoning-step-capture.md`](./analyses/reasoning-step-capture.md) |
| **Inner Space Curator** | [`analyses/inner-space-curator.md`](./analyses/inner-space-curator.md) |
| **Community pipeline** | [`analyses/community-pipeline.md`](./analyses/community-pipeline.md) |
| **Cross-agent workspace** | [`analyses/cross-agent-workspace-design.md`](./analyses/cross-agent-workspace-design.md) |

---

## Continuity & handoff

| Artifact | Path |
|----------|------|
| Full Cursor thread transcript | [`continuity/thread-transcript.md`](./continuity/thread-transcript.md) |
| Task pack | [`continuity/task-pack.md`](./continuity/task-pack.md) |
| Continuity index | [`docs/continuity/INDEX.md`](../../continuity/INDEX.md) |
| Agent boot guide | [`docs/cross-agent/README.md`](../../cross-agent/README.md) |

---

## Related prototypes & references

| Item | Path |
|------|------|
| Pilot 003 reasoning signature | [`sandbox/.../pilot-003-meta-reasoning-pass/README.md`](../../sandbox/2026-07-05-metaphysical-thought-space/experiments/pilot-003-meta-reasoning-pass/README.md) |
| Philosophical framework → product | [`docs/plans/2026-05-18-philosophical-framework-to-product.md`](../../plans/2026-05-18-philosophical-framework-to-product.md) |
| Holodeck architecture | [`docs/plans/2026-04-26-holodeck-workspace-architecture.md`](../../plans/2026-04-26-holodeck-workspace-architecture.md) |
| Formation surface decisions | [`docs/product-thesis/05-formation-surface-decision-sheet.md`](../../product-thesis/05-formation-surface-decision-sheet.md) |

---

## Foundation architecture (locked)

```text
APPLICATIONS  Thought Trace · Curator · World Studio · future products
PROFILES      Field · Formation · Shape · Transformation · Pattern
              Agent · Conversation · Personal Formation · Execution
KERNEL        Source · identity · scope · state · occurrence · relation
              claim · perspective · evidence · provenance · branch · types
```

---

## Locked decisions

1. Version 1.1 is the normative foundation.
2. One universal kernel supports governed profiles and application projections.
3. Historical frameworks map into the canonical model; they are not runtime layers.
4. Unity applies to identity and provenance, not one imposed truth.
5. Profiles may extend but not redefine kernel semantics.
6. Applications may compose profiles but not create parallel stores.
7. Build order follows the conformance-gated phases in the paper and build plan.
8. Cross-agent continuity lives in this workspace, its live workspace service record, and its published task pack.

---

## Immediate implementation boundary

1. Lock machine-readable contracts for the eight-record MVP, `BranchMembership`, `StateCommitment`, and orthogonal lifecycle axes.
2. Define `ProfileDefinition` and conformance validation.
3. Create migration fixtures for MTSF, SDS, ThoughtShape, and existing Conversation OS records.
4. Implement the Phase 1 capture/identity/branch vertical slice.
5. Do not begin broad application surfaces until the foundation gates pass.

---

## PR & session

- **Live coordination ID:** `unified-framework-synthesis`
- **Session lineage:** `cursor-unified-framework-synthesis-4f48` (historical synthesis thread)
- **Current task pack ID:** `unified-metaphysical-foundation-schema-lock`
