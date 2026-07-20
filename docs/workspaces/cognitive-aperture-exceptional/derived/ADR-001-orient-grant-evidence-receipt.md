# ADR-001 — Orient → Grant → Evidence → Receipt

**Status:** accepted (workspace lock)  
**Date:** 2026-07-17  
**Workspace:** `cognitive-aperture-exceptional`

## Context

The repo has strong selective-disclosure doctrine and multiple partial mechanisms (bridge policy, retrieval bundles, task packs, Holodeck contextualize, kernel bounded views). Conversation and research evaluation converged on a four-layer law. Implementation still blurs these layers and fails open in places.

## Decision

All disclosure work in this program treats four jobs as separate:

1. **Orient** — thin state + posture prose places the model in a situational frame  
2. **Grant** — authorization of layers/refs/budgets/envelope mode  
3. **Evidence** — high-SNR material actually opened under the grant  
4. **Receipt** — frozen audit/handoff record (packet/contract)

Execution prompts may include (1)+(3) and thin constraints.  
Receipts may include grant details and omit reasons.  
Omit/suppressed content must not appear in execution prompts.

## Non-decisions / non-claims

- Inner World structure is not the LLM’s residual-stream geometry  
- Text orientation is soft conditioning, not guaranteed activation steering  
- Exceptional v1 does not require learned rerankers or weight-space steering

## Consequences

- `build_retrieval_bundle` must support fail-empty under bounded/strict  
- `token_budget` and envelope modes must be enforced  
- Frame/compose contracts must be amended to match this order  
- New surfaces must call a shared disclose path rather than invent scorers  
- Eval suites for negative aperture, leak, and budget obedience become release gates

## Alternatives considered

| Alternative | Why rejected |
|-------------|--------------|
| Fat context packets as primary steer | Becomes Prompt #2; harms signal density |
| Long-context ocean stuffing | Context rot / lost-in-the-middle |
| Single blended ControlPacket mind | Collapses grant/evidence/receipt; hard to test |

## Links

- [`GAP_MAP.md`](./GAP_MAP.md)
- `docs/product/semantic-operating-layer/FRAME_CONTRACTS.md`
- `docs/product-thesis/07-state-dependent-reasoning-architecture.md`
