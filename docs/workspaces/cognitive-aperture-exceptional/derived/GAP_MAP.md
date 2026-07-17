# Gap Map — Good → Exceptional Cognitive Aperture

**Workspace:** `cognitive-aperture-exceptional`  
**Holodeck:** `cognitive-aperture-exceptional`  
**Status:** living plan  
**Date locked:** 2026-07-17  
**Audience:** implementers, reviewers, foreign agents

---

## 0. Purpose of this document

This is the coordination and planning authority for hardening selective disclosure from:

- **Good:** strong doctrine, partial bridge plumbing, multiple aperture-like mechanisms  
to  
- **Exceptional:** one measurable aperture engine that places foreign intelligence in the right neighborhood of a vast private world

It is deliberately forward-looking across product, runtime, eval, research, ops, and multi-agent dimensions.

---

## 1. North star

### Exceptional product sentence

A system that can place any foreign model into the **correct neighborhood** of a vast private Inner World, with almost no distractors, thin orientation, hard budgets, and a receipt — and can **prove** that over time.

### Governing loop (locked)

```text
Evidence → State → Orient (prose/posture)
                 → Grant (what may open)
                 → Evidence bundle (what opened)
                 → Execution
                 → Evaluation
                 → Promotion
                 → Receipt / packet (audit + handoff)
```

### Architectural law

| Layer | Job | Must not do |
|-------|-----|-------------|
| **State + posture** | Place intelligence in a situational frame | Narrate the whole Inner World |
| **Disclosure grant** | Authorize refs/layers/budgets | Ship library contents |
| **Evidence bundle** | Supply high-SNR opened material | Pad with confidence fillers |
| **Packet / contract** | Freeze boundary for audit & handoff | Act as primary steering mind |

### Research alignment (non-negotiable reading)

| Finding | Implication |
|---------|-------------|
| Concepts behave as directions in activation space (RepE / steering) | Thin orientation can soft-shift neighborhoods; do not overclaim literal residual control |
| ICL ≈ latent task inference (approximate, not perfect Bayes) | State/prose should set task/posture before evidence |
| Lost-in-the-middle + Context Rot | Distractors actively harm; fail-empty beats fail-open |
| Selective retrieval / hybrid RAG | Aperture chooser is first-class product intelligence |
| Persona prose < activation vectors for precision | Prose is v1 steer; activation steering is optional later tier |

---

## 2. Exceptional characteristics (scorecard)

These are the dimensions that define “exceptional.” Current grades reflect code as of 2026-07-17 research evaluation.

| ID | Characteristic | Exceptional meaning | Now | Target |
|----|----------------|---------------------|-----|--------|
| **C1** | Aperture intelligence | Chooser optimizes neighborhood hit-rate under uncertainty | D+ | A |
| **C2** | Orient-before-evidence | Thin posture/landscape before any ocean material | C | A |
| **C3** | Fail-empty disclosure | No relevant match → open nothing | F | A |
| **C4** | High signal density | Every token earns place; distractors treated as harm | D | A |
| **C5** | One disclosure kernel | All surfaces call `disclose()` | D | A |
| **C6** | Grant ≠ evidence ≠ receipt | Clean object separation | D+ | A |
| **C7** | True budget enforcement | Token/layer/depth bite; `open ≠ bounded ≠ strict ≠ incognito` | C− | A |
| **C8** | No suppression leak | Withheld content never reaches execution prompt | F | A |
| **C9** | State continuity | Live purpose/tension/object across turns & surfaces | C | A− |
| **C10** | Provenance + reversibility | Source-backed opens; reviewable promotion/demotion | B | A |
| **C11** | Cross-surface sameness | Chat, feed, Holodeck, agents, studio feel one world | C | A− |
| **C12** | Measurable neighborhood hit-rate | Eval suite proves aperture quality over baselines | D | A |

**Composite now:** ~C− engine / B vision  
**Composite exceptional bar:** ≥A− on C1–C8 and ≥B+ on C9–C12

---

## 3. Current-state inventory (what exists)

### 3.1 Strong assets (keep)

| Asset | Location | Why it matters |
|-------|----------|----------------|
| Doctrine | `TENETS.md`, `CONTEXT_ROUTING.md` | Task-scoped context is law |
| Product thesis loop | `docs/product-thesis/` | Semantic OS formula already correct |
| Bridge policy object | `models.ContextPolicy`, `reasoning_bridge` | Real control-plane sketch |
| Layer allow/deny | `reasoning_bridge._apply_layer_policy` | Tested |
| Pond neighbor gate | `knowledge_layer.build_retrieval_bundle` | Membrane exists when ponds exist |
| Kernel bounded views | `metaphysical_kernel_runtime.query_bounded_view` | Best fail-closed projector (unwired) |
| Frame contracts (draft) | `docs/product/semantic-operating-layer/FRAME_CONTRACTS.md` | Names the right pipeline |
| Task-pack caps | `routing.build_task_pack` | Crude but real handoff aperture |
| Holodeck local workspaces | `holodeck.py` | Coordination surface for this work |

### 3.2 Parallel mechanisms (must converge)

```text
A. Bridge spine          ControlPacket + ContextPolicy + get_context_bundle
B. Ocean retrieval       build_retrieval_bundle (capsules/ponds)
C. Task packs            keyword handoff (no ContextPolicy)
D. Kernel bounded_view   epistemic projector (isolated)
E. Holodeck / Feed / Portable   own scorers and caps
```

Exceptional requires **A+B unified as kernel**, with C/E calling it, and D optionally backing global epistemic projection.

### 3.3 Known implementation failures (still true)

| Failure | Evidence | Blocks |
|---------|----------|--------|
| Fail-open seeds | `knowledge_layer.py`: confidence always scores; empty match forces `ranked[:3]` | C3, C4 |
| Dead `token_budget` | Parsed/steered; never truncates in bridge/compose | C7 |
| `bounded ≡ open` layers | `_default_allowed_layers_for_envelope` | C7 |
| Suppression leak | `chat_backends.compose_execution_message` includes “Suppressed frame blocks” | C8 |
| FrameSpec post-hoc | Built after retrieval; preview-only | C2, C6 |
| Heuristic path weak policy | Many turns lack real ControlPacket policy | C1, C2 |
| No neighborhood metrics | Unit tests prove plumbing, not hit-rate | C12 |

---

## 4. Target architecture

### 4.1 Single disclose kernel

```text
disclose(
  query: str,
  state: ActiveState,          # topic, purpose, tension, posture, object
  grant: DisclosureGrant,      # layers, limits, cross_ocean, allow/deny refs
  mode: EnvelopeMode           # open | bounded | strict | incognito
) -> DisclosedBundle
```

`DisclosedBundle` fields:

- `orientation` — thin prose/posture block actually used
- `grant_applied` — effective grant after envelope
- `evidence` — opened blocks with provenance + scores + why-included
- `omitted` — structured omit reasons (audit-only; **never** in execution prompt)
- `metrics` — token counts, layer counts, empty?/hit estimates
- `receipt_ref` — id for packet materialization

### 4.2 Compose order (execution)

```text
1. Orientation (state + posture prose)
2. Steering constraints (thin)
3. Evidence blocks (only granted & opened)
4. User turn
---
Audit surface (not execution): omitted reasons, full grant, FrameBundle
```

### 4.3 Object split (implementation shapes)

| Object | Owner module (proposed) | Persisted? |
|--------|-------------------------|------------|
| `ActiveState` | `reasoning_bridge` / active_field | session |
| `DisclosureGrant` | evolve from `ContextPolicy` | packet |
| `EvidenceBundle` | evolve from retrieval + layer trim | packet |
| `DisclosureReceipt` | evolve from ControlPacket/FrameBundle | packet + audit |
| `disclose()` | **new thin kernel module** or `knowledge_layer` + bridge facade | n/a |

**Minimality rule:** prefer extending `ContextPolicy` + `build_retrieval_bundle` + compose path before inventing a large new subsystem. Introduce `disclose()` only when ≥2 surfaces call it (bridge + Holodeck minimum).

### 4.4 Surface adoption matrix

| Surface | Today | Exceptional |
|---------|-------|-------------|
| Bridge / chat / mobile compose | Own bundle path | Calls `disclose()` |
| Holodeck contextualize | Own term scorer | Calls `disclose()` with workspace grant |
| Feed / FeedContextPacket | Ad hoc lookups | Per-post grant via `disclose()` |
| Task packs | Keyword + fallback fill | Optional evidence enrichment via `disclose()`; still capped handoff |
| World Studio compile | Loose selective retrieval | Grant-scoped evidence only |
| Kernel bounded_view | Isolated | Optional backend for global/epistemic layer |

---

## 5. Gap catalog (detailed)

Each gap has: problem, why it blocks exceptional, target, acceptance tests, risks, dependencies.

### G0 — Architecture lock (docs + contracts)

**Problem:** Orient/grant/evidence/receipt is agreed in conversation but not locked as build contract.  
**Target:** This gap map + Frame contract amendment + short ADR.  
**Acceptance:**

- [ ] ADR records the four-layer law and non-claims (latent space ≠ Inner World)
- [ ] `FRAME_CONTRACTS.md` updated: FrameSpec may be preview; disclosure order is orient→grant→evidence→receipt
- [ ] Compose contract forbids suppressed content in execution prompts

**Depends on:** nothing  
**Risk:** docs drift from code if no tests follow

---

### G1 — Fail-empty retrieval (C3, C4) — **P0**

**Problem:** `build_retrieval_bundle` adds confidence to every capsule and falls back to top-ranked seeds.  
**Target:**

1. Require positive query evidence (token/alias/structural hit) before seeding
2. If no seeds after threshold → empty bundle (`count=0`, `empty_reason=no_positive_match`)
3. Remove forced `ranked[:3]` fallback for bounded/strict modes
4. Pond-less capsules excluded under `bounded`/`strict` (fail closed on missing membrane metadata)

**Owner paths:** `src/conversation_os/knowledge_layer.py`, tests  
**Acceptance:**

- [ ] Unrelated query against populated capsules returns `count=0`
- [ ] Empty query returns empty under bounded/strict
- [ ] Alias hits still work
- [ ] Deep/open mode policy explicitly documented if any soft fallback remains (prefer none)

**Eval metric:** distractor inclusion rate → near 0 on negative suite  
**Risk:** recall drop; mitigate with better aliasing + pond metadata backfill job

---

### G2 — Real token budgets + envelope distinctness (C7) — **P0**

**Problem:** `token_budget` is decorative; `open` and `bounded` share layer defaults.  
**Target:**

| Mode | Default layers | Default cross_ocean | Learning default |
|------|----------------|---------------------|------------------|
| open | session, workspace, user, global | policy | on (guarded) |
| bounded | session, workspace (+ user only if granted) | false | on (guarded) |
| strict | session (+ explicit pins) | false | off/session-local |
| incognito | session ephemeral | false | off |

**Enforcement:**

- Truncate evidence/events to `token_budget` before compose
- Record `truncated=true` + dropped block ids in receipt only
- Tests: `open ≠ bounded ≠ strict ≠ incognito` for layers **and** persistence

**Owner paths:** `models.py`, `reasoning_bridge.py`, `chat_backends.py`, tests  
**Acceptance:**

- [ ] Oversized bundle truncated to budget
- [ ] Bounded cannot pull global without explicit grant
- [ ] Incognito: no retrieval call, no durable learning side effects

---

### G3 — Kill suppression leak (C8) — **P0**

**Problem:** Execution prompt includes “Suppressed frame blocks.”  
**Target:**

- Execution sees only orientation + allowed evidence
- Omitted/suppressed available on audit/inspect tools only (`bridge_inspect_request`, Holodeck status, debug MCP)

**Acceptance:**

- [ ] Compose unit test asserts suppressed labels/content absent from execution message
- [ ] Inspect/audit path still shows omit reasons
- [ ] Delete or rewrite tests that currently require leak

---

### G4 — Orient-before-evidence compose (C2, C6) — **P0/P1**

**Problem:** Retrieval and fat packet fields dominate; orientation is not first-class.  
**Target:**

1. Build thin `orientation_block` from ActiveState (topic, purpose, posture, tension, landscape note ≤ N tokens)
2. Compose order: orientation → constraints → evidence → user
3. FrameSpec becomes grant/selectors input when available; until then, ControlPacket posture fields feed orientation
4. Pins/exclusions apply during assembly, not only as receipts

**Acceptance:**

- [ ] Snapshot tests show orientation precedes evidence
- [ ] Orientation token cap enforced
- [ ] Removing evidence still leaves coherent posture (smoke)

---

### G5 — Unify disclose kernel (C5) — **P1**

**Problem:** Parallel scorers (bridge, Holodeck, feed, task pack).  
**Target:**

Phase A: extract shared function used by bridge + Holodeck contextualize  
Phase B: feed assist / FeedContextPacket  
Phase C: optional task-pack enrichment (not replacement of handoff narrative)

**Acceptance:**

- [ ] ≥2 surfaces call same kernel
- [ ] Holodeck no longer uses independent term-seed scoring for ocean/static context
- [ ] Policy/grant honored identically across callers (shared tests)

**Risk:** big-bang rewrite — avoid; facade first

---

### G6 — Aperture intelligence quality (C1, C12) — **P1**

**Problem:** Lexical/confidence scoring ≠ neighborhood selection.  
**Target chooser signals (v1):**

- Positive lexical/alias overlap (required gate)
- Pond coherence with active object
- Link governance / promoted bridges only for cross-pond
- Recency / session attachment soft boost
- Explicit pins
- **Negative evidence:** near-duplicate distractors demoted

**Out of v1:** learned rerankers, embedding-only ocean walks without grant

**Eval harness (new):**

| Suite | Measures |
|-------|----------|
| `aperture_negative` | Unrelated queries → empty |
| `aperture_positive` | Gold pond/capsule sets → recall@k |
| `distractor_harm` | Add N distractors → answer/posture degradation |
| `budget_obedience` | Token/layer caps never exceeded |
| `leak_suite` | Suppressed never in execution |
| `envelope_matrix` | Mode distinctness |

**Acceptance:** publish baseline numbers before claiming exceptional

---

### G7 — State continuity across surfaces (C9, C11) — **P1/P2**

**Problem:** State exists in bridge session objects but is not the product center.  
**Target:**

- ActiveState schema: purpose, topic, object_id, tension, posture, depth, lens
- Persist per session/workspace with retention policy
- Feed/Holodeck/chat can read same ActiveState when scoped
- Turn updates state explicitly (append-only events)

**Acceptance:**

- [ ] Multi-turn test: posture/tension survives and conditions next grant
- [ ] Workspace-scoped state visible to Holodeck contextualize

---

### G8 — Wire or demote kernel bounded_view (epistemic) — **P2**

**Problem:** Best fail-closed projector is unwired; claiming shared architecture is false.  
**Options:**

- **A (preferred later):** use bounded_view as epistemic backend when grant asks for graph-true global slice  
- **B:** document as separate kernel capability; stop implying bridge uses it

**Acceptance:** explicit decision recorded; if A, one bridge path integration test

---

### G9 — Task-pack aperture upgrade — **P2**

**Problem:** Fallback fills unrelated cards/sessions; no grant object.  
**Target:**

- Keep narrative handoff (what/why/decided/open)
- Fail empty on relevance for optional evidence section
- Optional `disclose()` enrichment under pack budget
- Atlas gate remains (index readiness)

**Acceptance:** unrelated request does not fabricate “relevant” cards without labeling fallback

---

### G10 — Observability & receipts — **P1**

**Problem:** Hard to prove aperture quality in production.  
**Target receipt fields:**

- orientation hash/text
- grant effective
- evidence ids + scores + include reasons
- omit reasons (audit)
- budgets requested/applied
- empty_reason
- surface + session + workspace ids

**Tools:** bridge inspect, Holodeck status, MCP inspect  
**Acceptance:** one turn fully reconstructible from receipt

---

### G11 — Forward research track (optional exceptional+) — **P3**

Not required for exceptional v1; category-defining later:

1. Contrastive posture vectors (honesty/exploration/decision) via activation steering on owned models  
2. Learned aperture reranker trained on accept/reject feedback  
3. Multimodal capsule retrieval (where World Studio already gestured)  
4. Self-routing: model requests widen/narrow grant with policy governor  
5. Formal neighborhood metrics tied to user “felt orientation” studies

**Rule:** do not block v1 exceptional bar on these.

---

## 6. Phased roadmap

### Phase 0 — Lock (docs / contracts) — **now**

**Outcome:** shared language and acceptance bar  
**Work:**

0.1 This workspace + Holodeck + gap map  
0.2 ADR: orient/grant/evidence/receipt  
0.3 Amend Frame/compose contracts (no suppression in execution)  
0.4 Eval suite skeletons (empty tests ok)

**Exit:** implementers can start G1–G3 without rediscovering doctrine

---

### Phase 1 — Stop the bleeding (P0 runtime) 

**Outcome:** disclosure stops lying  
**Work order (strict):**

1. **G1** fail-empty retrieval  
2. **G3** suppression leak kill  
3. **G2** token budgets + envelope distinctness  
4. **G4** orient-first compose (minimal)

**Exit metrics:**

- Negative aperture suite green  
- Leak suite green  
- Budget obedience green on bridge path  
- Bounded ≠ open in tests

**Why this order:** fail-empty + leak + budgets are the research-critical harms; orientation polish after honesty.

---

### Phase 2 — One kernel + measurement (P1)

**Outcome:** exceptional becomes measurable and portable across surfaces  

1. Extract `disclose()` facade (bridge + Holodeck) — **G5 Phase A**  
2. Aperture eval harness with published baselines — **G6**  
3. Receipts/observability — **G10**  
4. ActiveState continuity MVP — **G7**  
5. Feed adoption — **G5 Phase B**

**Exit metrics:**

- ≥2 surfaces on kernel  
- Hit-rate / distractor-harm baselines published in workspace derived/  
- Receipt reconstructs a turn

---

### Phase 3 — Product sameness + epistemic integrity (P2)

**Outcome:** one world feeling; honest architecture claims  

1. Task-pack relevance honesty — **G9**  
2. bounded_view wire-or-demote decision + action — **G8**  
3. World Studio compile grant discipline (if in scope)  
4. Cross-surface ActiveState  
5. Operator dashboards / Holodeck views for aperture metrics

**Exit:** C1–C8 at A−/A; C9–C12 at B+/A−

---

### Phase 4 — Category-defining (P3, optional)

Activation steering, learned rerankers, self-routing grants, human orientation studies — only after Phase 3 exit.

---

## 7. Work breakdown (task seeds)

Use these as live tasks when API is available. Do not hand-edit Status in markdown.

| Task ID | Title | Phase | Priority | Primary paths |
|---------|-------|-------|----------|---------------|
| CAE-000 | Lock ADR + contract amendments | 0 | high | `docs/workspaces/cognitive-aperture-exceptional/derived/`, `docs/product/semantic-operating-layer/` |
| CAE-001 | Fail-empty retrieval + tests | 1 | critical | `knowledge_layer.py`, tests |
| CAE-002 | Remove suppression leak + fix tests | 1 | critical | `chat_backends.py`, tests |
| CAE-003 | Enforce token_budget + envelope matrix | 1 | critical | `reasoning_bridge.py`, `models.py`, tests |
| CAE-004 | Orient-first compose MVP | 1 | high | `chat_backends.py`, `reasoning_bridge.py` |
| CAE-005 | Extract disclose() for bridge+Holodeck | 2 | high | new/facade + `holodeck.py` |
| CAE-006 | Aperture eval harness + baselines | 2 | high | `tests/`, `derived/baselines/` |
| CAE-007 | Disclosure receipts + inspect | 2 | medium | bridge inspect paths |
| CAE-008 | ActiveState continuity MVP | 2 | medium | session/bridge state |
| CAE-009 | FeedContextPacket on disclose() | 2 | medium | feed/long_form paths |
| CAE-010 | Task-pack relevance honesty | 3 | medium | `routing.py` |
| CAE-011 | bounded_view wire-or-demote | 3 | medium | kernel + docs decision |
| CAE-012 | Cross-surface state + metrics board | 3 | low | Holodeck UI/docs |

---

## 8. Dimension checklists (forward-looking)

### 8.1 Product

- [ ] User-visible depth controls map to envelope modes
- [ ] “Widen / narrow context” is an explicit user/agent act, not silent creep
- [ ] Feed posts declare scope boundary
- [ ] Agent handoffs remain narrative + capped, not ocean exports

### 8.2 Runtime / correctness

- [ ] Fail-empty default for bounded/strict
- [ ] Budgets truncate deterministically
- [ ] Pond metadata backfilled for top capsules
- [ ] Heuristic classify either emits policy or inherits safe default grant

### 8.3 Evaluation

- [ ] Golden aperture fixtures (positive/negative/distractor)
- [ ] CI gate on leak_suite + budget_obedience
- [ ] Published baseline JSON per release
- [ ] Canary: random unrelated prompts in staging → empty global layer

### 8.4 Multi-agent / Holodeck

- [ ] This workspace registered live when API returns
- [ ] Tasks claimed with path scopes before edits
- [ ] Projections published after mutations
- [ ] Handoffs include gap-map section pointer + current phase exit criteria

### 8.5 Research honesty

- [ ] Docs never claim Inner World == model latent space
- [ ] Orientation described as soft conditioning, not residual rotation (unless P3 ships)
- [ ] Cite context-rot / lost-in-middle as rationale for fail-empty

### 8.6 Security / privacy

- [ ] Incognito: no ocean, no durable learn
- [ ] Receipts may contain sensitive evidence — retention policy defined
- [ ] Suppressed content not logged into execution transcripts

### 8.7 Performance

- [ ] disclose() p95 budget for hot path
- [ ] Capsule index warm path; no full ocean scan per turn
- [ ] Eval suites run in CI under time cap

### 8.8 Migration / compatibility

- [ ] Feature flags: `fail_empty_retrieval`, `enforce_token_budget`, `compose_no_suppressed`
- [ ] Shadow mode: compute empty decisions without enforcing (metrics only)
- [ ] Rollback path if recall regressions spike

---

## 9. Risks and anti-patterns

| Risk | Mitigation |
|------|------------|
| Recall collapse after fail-empty | Alias governance + pond backfill + positive-suite gates |
| Big-bang kernel rewrite | Facade; adopt surfaces incrementally |
| Docs theater without tests | Phase 1 exit = suites green |
| Packet fattening returns | Hard compose allowlist; receipt ≠ prompt |
| Overclaiming latent geometry | ADR non-claim; review checklist |
| Live API offline | Local Holodeck + git workspace; register later |
| Parallel “temporary” scorers | Ban new scorers once disclose() exists |

---

## 10. Definition of Done — Exceptional v1

All must be true:

1. **C3/C7/C8** at A (fail-empty, real budgets, no leak)  
2. **C2/C6** at A− (orient-first; grant/evidence/receipt separated in code)  
3. **C5** at A− (≥2 surfaces on one kernel)  
4. **C1/C12** at B+/A− (chooser improved; baselines published)  
5. ADR + contracts match runtime  
6. Bridge path CI gates: leak, budget, negative aperture  
7. No docs claim latent-space identity with Inner World  

Phase 3/4 items may remain open without blocking “exceptional v1.”

---

## 11. Immediate next actions

1. **When laboratory host is online:** register live workspace, create CAE-000… tasks, publish projections.  
2. **CAE-000:** write ADR + amend Frame/compose contracts.  
3. **CAE-001 → CAE-003:** Phase 1 P0 code in that order on a feature branch.  
4. Keep this gap map updated when grades change; append baselines under `derived/baselines/`.

---

## 12. Source thread (provenance)

This map synthesizes:

- Repo doctrine (`TENETS`, `CONTEXT_ROUTING`, product thesis, Frame contracts)
- Runtime evaluation of retrieval/bridge/compose/task-pack/kernel (2026-07-17)
- Product vision: semantic OS / apertures over one ocean
- Architecture split: state+posture / grant / evidence / receipt
- Frontier research alignment: RepE/steering, ICL latent-task views, context rot / lost-in-middle, selective retrieval

Holodeck workspace created locally: `cognitive-aperture-exceptional` (2026-07-17T23:57:11Z).
