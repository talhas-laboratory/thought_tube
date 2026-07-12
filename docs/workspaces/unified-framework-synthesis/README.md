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

```bash
# 1. Live workspace first
python3 tools/workspace_coordination.py status --workspace-id unified-framework-synthesis
python3 tools/workspace_coordination.py context --workspace-id unified-framework-synthesis --agent-id <agent> --surface <surface> --session-id <session>

# 2. Canonical framework source
cat docs/workspaces/unified-framework-synthesis/sources/thought-tube-unified-metaphysical-modeling-framework-v1.1.md

# 3. Handoff and build plan
cat docs/workspaces/unified-framework-synthesis/derived/handoff.md
cat docs/workspaces/unified-framework-synthesis/derived/foundation-build-plan.md

# 4. Published continuity projection
cat docs/workspaces/unified-framework-synthesis/CONTINUITY.md

# 5. Focused task pack
cat docs/workspaces/unified-framework-synthesis/continuity/task-pack.md
```

Machine-readable catalog: [`manifest.json`](./manifest.json)
Sync contract: [`derived/sync-contract.md`](./derived/sync-contract.md)

Execution board: [`docs/workboards/unified-metaphysical-foundation/`](../../workboards/unified-metaphysical-foundation/README.md)

---

## Normative foundation

| Document | Status | Purpose |
|---|---|---|
| [`sources/thought-tube-unified-metaphysical-modeling-framework-v1.1.md`](./sources/thought-tube-unified-metaphysical-modeling-framework-v1.1.md) | **Canonical** | Kernel, profiles, applications, invariants, lifecycles, architecture, build order, tests, and migration |
| [`derived/foundation-build-plan.md`](./derived/foundation-build-plan.md) | Active execution bridge | Converts the normative paper into bounded implementation work |
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
