# Agent Boot — Cognitive Aperture Exceptional

**Mission:** build a reliable modular disclosure service
**Workspace:** `cognitive-aperture-exceptional`
**Coordination:** live API is authoritative
**Design:** [`Modular Cognitive Aperture Design`](../../plans/2026-07-19-cognitive-aperture-modular-disclosure-design.md)
**Executable handoff:** [`derived/EXECUTION_HANDOFF.md`](./derived/EXECUTION_HANDOFF.md)

## Orientation

You are building the doorway into the knowledge world, not the knowledge world itself.

```text
Orient -> Grant -> Evidence -> Receipt
```

- **Orient:** bounded state/posture from the current turn and authorized local continuity.
- **Grant:** one immutable effective policy after defaults, permissions, scope, and denials.
- **Evidence:** admitted, budgeted, provenance-backed blocks opened lazily.
- **Receipt:** separate audit record; never the primary steering prompt.

## Ownership boundary

This workspace owns grant normalization, candidate admission, evidence budgeting, execution-safe projection, receipts, and adapters.

It does not own source ingestion, canonical records, Shape promotion, embeddings, ontology, or surface presentation. Do not repair a missing dependency by creating a parallel store here.

## Locked invariants

1. No positive match means no evidence.
2. Confidence alone never admits a candidate.
3. Denials always win.
4. Execution cannot represent suppressed content.
5. Raw source text is stored once.
6. Shape candidates retain candidate status, branch, scope, boundary, and provenance.
7. Budgets select whole evidence blocks deterministically.
8. Incognito performs no ocean retrieval or durable learning.
9. Dependency failure abstains; it never broadens retrieval.
10. Surface adapters cannot bypass the effective grant.

## Authority map

| Need | Read |
|---|---|
| Canonical implementation plan | [`derived/GAP_MAP.md`](./derived/GAP_MAP.md) |
| Disclosure law | [`derived/ADR-001-orient-grant-evidence-receipt.md`](./derived/ADR-001-orient-grant-evidence-receipt.md) |
| Modular boundary | [`derived/ADR-002-modular-disclosure-boundary.md`](./derived/ADR-002-modular-disclosure-boundary.md) |
| Landscape and widen rules | [`NEIGHBORHOOD.md`](./NEIGHBORHOOD.md) |
| Completion gates and decisions | [`../../workboards/cognitive-aperture-exceptional/`](../../workboards/cognitive-aperture-exceptional/README.md) |
| Coordination status | live workspace API |

## Boot sequence

1. Query live context and projection freshness.
2. Read this file, ADR-002, and the active task packet.
3. Read `GATES.md` and `DECISIONS.md`.
4. Confirm the task is a ready leaf and its dependencies have evidence.
5. For runtime work, refresh the repo overview and pass the engineering guard.
6. Execute the smallest task path and record exact verification.

## Delivery sequence

```text
Stage A: contracts + corpus/Shape readiness + baselines
Stage B: leak isolation + grant matrix + fail-empty + budgets + orientation
Stage C: shared service + Bridge/Holodeck + receipts + state + performance
Stage D: feed/task-pack/bounded-view/operator adapters
```

Do not begin Stage B until the Stage A gate passes. Do not extract a shared service until the Bridge path is proven and Holodeck is ready as the second consumer.

## Known current hazards

- seed corpus `cognitive_aperture_chat_converter_v1` is materialized; its completed pipeline and known retrieval regression are recorded in `derived/CHAT_CONVERTER_SEED_CORPUS_V1.md`;
- retrieval confidence currently makes all capsules positive;
- bounded defaults to the same layers as open;
- token budget is not enforced at execution;
- suppressed frame blocks are rendered into execution;
- legacy Shape signatures and canonical framework Shapes are not unified;
- several surfaces maintain parallel selectors.

## Handoff minimum

- update live task with state and evidence;
- publish and check projections;
- commit and push the bounded change;
- record commands, results, artifacts, rollback, and residual risks;
- point the next agent here and at the active task packet.

## Compass

> Store truth once. Admit explicitly. Resolve lazily. Budget deterministically. Execute safely. Audit separately.
