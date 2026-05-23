# Inner World Building Taskboard

Migrated on `2026-04-22` from:

- `/Users/talhauddin/software/inner_space/docs/plans/2026-04-14-inner-world-v1-taskboard.md`

Status legend:

- `planned`
- `ready`
- `blocked`
- `in_progress`
- `done`

Related continuity docs:

- [Building Diary Index](./README.md)
- [2026-04-22 Building Session Diary](./2026-04-22-building-session-diary.md)

## Current Blockers

| ID | Status | Task | Slice | Depends On | Verification |
|---|---|---|---|---|---|
| B1 | `blocked` | Add the miniapp pond inspection and manual correction panel on top of the existing chunk pond routing API | current | pond runtime, pond API control plane | Engineering guard explicitly clears the existing miniapp frontend asset surface (`product/inner_world_v1/miniapp/app.js`, `product/inner_world_v1/miniapp/styles.css`) as the approved ownership path. Backend and API control are already in place; the blocked part is UI ownership approval, not technical feasibility. |

## Product and UX

| ID | Status | Task | Slice | Depends On | Verification |
|---|---|---|---|---|---|
| P1 | `planned` | Lock v1 user, job, and product sentence | S1 | none | Thesis and scope docs agree |
| P2 | `planned` | Finalize insight contract | S1 | P1 | Every surfaced insight field is mandatory |
| P3 | `planned` | Finalize feed-native UI pattern: feed, article, thought chat | S1 | P1, P2 | UI spec reviewed and no dashboard-first conflicts remain |
| P4 | `planned` | Finalize v1 screen list and route map | S2, S5 | P1, P2, P3 | Screen map reviewed and no deferred feature leaks into v1 |

## OpenClaw Substrate

| ID | Status | Task | Slice | Depends On | Verification |
|---|---|---|---|---|---|
| O1 | `planned` | Define exact server folder layout in existing OpenClaw workspace | S2 | P1 | Layout doc maps each component to a real path |
| O2 | `planned` | Define gateway integration contract | S2 | O1 | Request/response flow documented against port `18789` |
| O3 | `planned` | Define miniapp entrypoint and runtime contract | S2 | O1, P4 | Miniapp path, runtime owner, and deploy path are explicit |
| O4 | `planned` | Define service/runbook for local and server startup | S8 | O2, O3 | Runbook can boot components in order |

## Intake and Normalization

| ID | Status | Task | Slice | Depends On | Verification |
|---|---|---|---|---|---|
| I1 | `planned` | Lock supported v1 input surfaces | S3 | P1 | Input matrix reviewed |
| I2 | `planned` | Replace line-based chunking with semantic chunking | S3 | I1 | Deterministic chunk tests pass |
| I3 | `planned` | Guarantee stable source IDs and provenance | S3 | I1 | Provenance trace test passes |
| I4 | `planned` | Add import failure and unsupported-input handling | S3 | I1 | Negative tests pass |

## Analysis and Ranking

| ID | Status | Task | Slice | Depends On | Verification |
|---|---|---|---|---|---|
| A1 | `planned` | Improve duplicate suppression and cross-document preference | S4 | I2, I3 | Repeated fragments no longer dominate |
| A2 | `planned` | Formalize reasoning-primitives mapping | S4 | A1 | Each surfaced insight has a valid primitive |
| A3 | `planned` | Split ranking into evidence, novelty, usefulness, surprise | S4 | A1 | Score breakdown is inspectable |
| A4 | `planned` | Define grounded vs speculative threshold policy | S4 | A3 | Threshold tests pass |
| A5 | `planned` | Build candidate withholding rules for weak items | S4 | A4 | Weak candidates do not surface |

## Delivery and Feedback

| ID | Status | Task | Slice | Depends On | Verification |
|---|---|---|---|---|---|
| D1 | `planned` | Ship thought feed generator with compact post rendering | S5 | A2, A4, P3 | Feed items are valid and selective |
| D2 | `planned` | Ship longform article expansion view | S5 | D1, P4 | Any feed thought expands into a detailed article |
| D3 | `planned` | Ship thought-native chat with scoped context routing | S5 | D2, O2 | Chat stays scoped to the selected thought context |
| D4 | `planned` | Ship thread save and delete behavior | S5 | D3 | Save creates linked artifacts, delete removes thread only |
| D5 | `planned` | Ship archive and thread history with drill-down | S5 | D2, D4 | Old thoughts and saved threads are discoverable |
| D6 | `planned` | Ship feedback actions and reranking loop | S5 | D1 | Ranking changes after explicit feedback |
| D7 | `planned` | Enforce attention budget policy | S7 | D1 | Feed respects caps and grounded-first rules |

## Research Overlay

| ID | Status | Task | Slice | Depends On | Verification |
|---|---|---|---|---|---|
| R1 | `planned` | Finalize research ontology and primitives | S6 | A2 | Research fixture produces mechanism-oriented output |
| R2 | `planned` | Tune research ranking heuristics | S6 | A3, R1 | Research output favors contradictions, gaps, synthesis |

## Art Overlay

| ID | Status | Task | Slice | Depends On | Verification |
|---|---|---|---|---|---|
| AR1 | `planned` | Finalize art ontology and primitives | S6 | A2 | Art fixture produces direction-oriented output |
| AR2 | `planned` | Tune art ranking heuristics | S6 | A3, AR1 | Art output favors motifs, references, mood, composition |

## Entrepreneurship Overlay

| ID | Status | Task | Slice | Depends On | Verification |
|---|---|---|---|---|---|
| E1 | `planned` | Finalize entrepreneurship ontology and primitives | S6 | A2 | Entrepreneurship fixture produces strategic output |
| E2 | `planned` | Tune entrepreneurship ranking heuristics | S6 | A3, E1 | Output favors wedge, friction, retention, distribution |

## Trust and Governance

| ID | Status | Task | Slice | Depends On | Verification |
|---|---|---|---|---|---|
| T1 | `planned` | Add explainability and why-am-I-seeing-this surfaces | S7 | D1 | Insight drill-down exposes evidence and scoring context |
| T2 | `planned` | Add export and reversibility guarantees | S7 | I3, D5 | Export contains complete inspectable state |
| T3 | `planned` | Add conservative default policy and kill switches | S7 | T1 | Policy doc and config flags exist |

## Evaluation and Ops

| ID | Status | Task | Slice | Depends On | Verification |
|---|---|---|---|---|---|
| V1 | `planned` | Define metric spec and event model | S8 | D6 | Every metric has a stored signal |
| V2 | `planned` | Create domain fixtures and regression tests | S8 | R2, AR2, E2 | Fixture test suite passes |
| V3 | `planned` | Create deploy and recovery runbooks | S8 | O4, T2 | Runbook can be followed step by step |

## Library Governance and Curation

| ID | Status | Task | Slice | Depends On | Verification |
|---|---|---|---|---|---|
| L1 | `planned` | Build a [library governance manager](./2026-04-22-library-governance-manager-design.md) for semantic filtering, normalization policy, source status control, and selective rederivation | S9 | I1, I3, T2 | Sources can be filtered, tagged, excluded, or reclassified without touching raw originals |
| L2 | `planned` | Build a [deep pruning and semantic curation system](./2026-04-22-deep-pruning-and-semantic-curation-design.md) for source, chunk, semantic, and derived-layer pruning with impact previews | S9 | L1 | Prune actions can target metadata, contents, or meaning, show downstream impact, and rebuild affected layers safely |

## Holodeck Incubation Workspace

| ID | Status | Task | Slice | Depends On | Verification |
|---|---|---|---|---|---|
| H1 | `planned` | Build the [Holodeck workspace architecture](../plans/2026-04-26-holodeck-workspace-architecture.md) as a typed incubation environment with operator tools, deterministic board/diary/test/handoff projections, and workspace-scoped task-pack generation | S10 | T2, V1 | An agent can create a Holodeck, link artifacts and sessions, manage work items and tests through typed records, materialize derived views, and hand off work through a Holodeck-scoped task pack |
| H2 | `planned` | Add a founder incubation template on top of Holodeck core without branching the core workspace model | S10 | H1 | Founder-specific wedge, moat, launch, and GTM fields exist as template behavior while core workspace schema remains lens-neutral |
| H3 | `planned` | Add explicit promotion flow from Holodeck-local knowledge into repo-global cards, plans, and task packs | S10 | H1 | Local knowledge stays isolated by default and only becomes global through explicit promotion records with provenance |

## Critical Path

`P1 -> P2 -> P3 -> P4 -> O1 -> O2/O3 -> I1 -> I2/I3 -> A1 -> A3 -> A4 -> D1 -> D2 -> D3 -> D4 -> D5 -> D6 -> T1/T2 -> V1/V2/V3`

Current extension path for corpus governance:

`I1/I3 -> T2 -> L1 -> L2`

## First Acceptance Milestone

The first useful alpha exists when:

- `D1` is done
- `D2` is done
- `D3` is done
- `D4` is done
- one overlay task from each domain is done: `R1`, `AR1`, `E1`
- `T1` and `T2` are done

At that point, the product is usable even if ranking is still being tuned.
