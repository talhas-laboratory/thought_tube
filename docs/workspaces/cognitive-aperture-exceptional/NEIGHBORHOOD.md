# Active Neighborhood — Cognitive Aperture

This file is the **landscape sketch** for agents. It tells you which region of the repo/product you are in, what belongs here, and when you may widen.

It is orientation + grant, not an evidence dump.

---

## 1. Where you are

```text
Product: Inner Space / Inner World
  └─ Semantic Operating Layer (bridge = control plane)
       └─ Cognitive aperture / selective disclosure hardening
            └─ THIS WORKSPACE: cognitive-aperture-exceptional
```

**Sister neighborhoods (adjacent, not default):**

| Neighbor | Relationship | Open when |
|----------|--------------|-----------|
| `docs/product/semantic-operating-layer/` | Contract home for Frame/Policy/Envelope | Amending contracts (CAE-000 follow-ons) |
| `docs/product-thesis/` | Why bridge + ocean exist | Product wording disputes |
| `unified-framework-synthesis` | Metaphysical kernel / bounded views | Only for G8 wire-or-demote |
| `holodeck-productization` | Holodeck as product | Not this program’s v1 focus |
| World Studio | Compile/retrieval strictness | Out of scope unless explicitly tasked |

---

## 2. In-neighborhood (default grant)

### Concepts you must keep loaded

- Orient / grant / evidence / receipt  
- Fail-empty vs fail-open  
- Context rot / lost-in-the-middle (why selective beats stuffing)  
- One disclose kernel vs parallel scorers  
- C1–C12 exceptional scorecard  
- Phase 1 P0: CAE-001 → 002 → 003 → 004  

### Files in the default grant

| Role | Path |
|------|------|
| Boot | `AGENT_BOOT.md` |
| Landscape | `NEIGHBORHOOD.md` (this file) |
| Law | `derived/ADR-001-orient-grant-evidence-receipt.md` |
| Plan | `derived/GAP_MAP.md` |
| Continuity | `CONTINUITY.md` |
| Workboard | `docs/workboards/cognitive-aperture-exceptional/` |
| Contracts | `docs/product/semantic-operating-layer/FRAME_CONTRACTS.md` |
| Decision log | `docs/product/semantic-operating-layer/DECISIONS.md` |

### Code in the default grant

| Module | Why |
|--------|-----|
| `knowledge_layer.py` | Retrieval membrane / fail-empty |
| `reasoning_bridge.py` | Policy, budgets, envelopes, bundle assembly |
| `chat_backends.py` | Execution compose / leak |
| `models.py` | `ContextPolicy` fields |
| Bridge/policy tests under `tests/` | Prove enforcement |

---

## 3. Out-of-neighborhood (blocked unless task widens)

Do **not** open by default:

- Full metaphysical framework paper (5000+ lines)  
- World Studio master library / portable packs  
- SDS / ThoughtShape comparative corpus  
- Entire `docs/plans/` history  
- Full knowledge ocean / capsule dumps  
- Mobile PWA redesign, Telegram agent, deployment ops  
- Activation-steering / RepE implementation (Phase 4 only)  

If you need background, prefer the **one-paragraph** summaries in `analyses/2026-07-17-thread-synthesis.md` over reopening source corpora.

---

## 4. Widen rules (explicit aperture expansion)

Widen **one notch** only when:

| Trigger | Allowed widen |
|---------|----------------|
| Implementing CAE-001 | Retrieval tests + capsule/pond helpers in `knowledge_layer.py` |
| Implementing CAE-002 | Compose tests that mention FrameBundle / suppressed blocks |
| Implementing CAE-003 | `bridge_prepare.py`, `bridge_session_retention.py` if budget fields flow there |
| G5 disclose() facade | `holodeck.py` contextualize path |
| G8 bounded_view decision | `metaphysical_kernel_runtime.py` + short kernel docs |
| Contract wording fight | Product thesis §07 only |

After widening, return to default grant. Do not stay ocean-wide.

---

## 5. Posture map (how to think here)

| If the user/task asks… | Posture |
|------------------------|---------|
| “What should we build?” | Point at Phase 1 order; don’t invent Phase 4 |
| “Are packets the answer?” | Receipts yes; primary steer no — see ADR |
| “Is layering needed?” | Already assumed; talk enforcement & measurement |
| “Evaluate again?” | Update C-grades in gap map with code evidence |
| “Dump more context?” | Refuse; add to grant table or evidence task instead |

---

## 6. Evidence on demand (open only for the active task)

| Task | Open these next |
|------|-----------------|
| CAE-001 | `build_retrieval_bundle` (~L813–950), negative tests to add |
| CAE-002 | `compose_execution_message` suppressed section (~L1011+), tests requiring leak |
| CAE-003 | `_budget_for_depth`, `_default_allowed_layers_for_envelope`, `ContextPolicy.token_budget` |
| CAE-004 | Compose order in `chat_backends.py`; orientation fields on control packet |
| Eval harness | `GAP_MAP.md` §G6 suites |

---

## 7. Receipt for this neighborhood

If you change the neighborhood definition, update:

1. This file  
2. `AGENT_BOOT.md` grant tables  
3. `CONTINUITY.md` next action  
4. Holodeck context records (when available)

---

## 8. Instant self-check

You are in the correct neighborhood if you can answer without searching the repo:

1. What are the four disclosure layers?  
2. What are the three P0 code failures?  
3. What is the next Phase 1 task id?  
4. What must never appear in the execution prompt?

If you cannot, re-read `AGENT_BOOT.md` §§0–6 before coding.
