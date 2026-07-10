# Conversation Decomposition — Smooth Microgestures on Mobile

Source bundle: `mobile_artifacts/2026-06-27/conv_20260627_125956_smooth-microgestures-on-mobile/`  
ChatGPT share: https://chatgpt.com/share/6a3e8f67-acf0-83ed-bca1-d654bc4c49ce  
Ingested: `2026-06-27`  
Messages: 23 (11 user turns)

This document decomposes the conversation into buildable units for the **Mobile Thought Capture** subproject. Each unit maps to frontend pillars (`docs/workboards/sol-frontend/PILLARS.md`).

---

## Conversation arc

```text
1. Gesture feasibility (mobile web)
2. iOS edge-swipe safety
3. Capture layout + AI behavior reformulation  ← primary product spec
4. Bridge / subscription / mental environment   ← adjacent (backend, out of v1 UI)
5. Capability builder / multimodal lenses       ← adjacent (runtime, phase 2+)
6. Semantic-zoom answer blocks                  ← development surface behavior
7. Scroll Engineering pillar adoption           ← engineering contract
```

---

## Theme A — Object-level microgestures (msgs 1–4)

**Question:** Can mobile web do smooth left-right microgestures? Will back gesture conflict?

**Decisions extracted:**

| Decision | Detail |
|---|---|
| Gestures are viable | Use `PointerEvents`, `transform: translateX`, `requestAnimationFrame`, springs |
| Vertical vs horizontal | Vertical scroll = depth; horizontal = adjacent semantic state on an object |
| Edge guard | 24–44px from left/right edges — do not start custom horizontal gestures there |
| `touch-action: pan-y` | Preserve vertical scroll while capturing horizontal drag on gesture zones |
| Object not page | Drag thought cards, lens peek, branch preview — not full-page carousels |
| Always fallback | Buttons, tabs, handles for every gesture affordance |
| No edge `preventDefault` hacks | Do not build product on fighting Safari back navigation |

**Pillars:** P4, P8  
**Build unit:** `GestureZone` contract + thought-card horizontal drag prototype  
**Artifact root:** `product/thought_capture_pwa/src/gesture/`

---

## Theme B — Capture Surface layout (msgs 5–6, image upload)

**User intent:** Use uploaded screenshot layout for thought dumping. Reformulate AI chat from ground up.

**Layout primitives (from screenshot analysis):**

- Full-screen focus, dark surround / spotlight on content
- One dominant content object per frame
- Very low interface noise
- Input embedded in the scene (not a rigid form)
- Lightweight bottom action area
- Feels like a passing frame, not a formal note

**Core product sentence:**

> The system should feel like a place where thoughts can land before they are understood.

**Two-surface architecture (non-negotiable):**

| Surface | Job | Default AI presence |
|---|---|---|
| **Capture** | Raw dumping, pre-intentional | Level 0–2 (silent to momentum cue) |
| **Development** | Structure, branching, collaboration | Level 3–4 (reflective to active) |

**Three layers (lifecycle):**

```text
Layer 1 Capture     → fast, immersive, low-friction
Layer 2 Development → AI collaboration, structuring, branching
Layer 3 Organization → connections, memory, retrieval (later)
```

**Pillars:** P1, P3, P6  
**Build unit:** `CaptureSurface` route + immersive shell replacing atlas-demo as capture mode  
**Out of scope v1:** Full Development Surface (stub entry only)

---

## Theme C — AI behavior model (msg 6, extended assistant reply)

**Wrong default (normal chat):** every input is a prompt; AI always answers visibly.

**Right default (thought capture):** infer cognitive mode + response contract; optimize continuation.

### Capture modes (infer probabilistically)

| Mode | Signals | AI behavior |
|---|---|---|
| `raw_dump` | fragments, fast bursts, mixed topics | stay out of the way; silent or minimal ack |
| `exploration` | "maybe", "what if", analogies | light branches, don't collapse early |
| `clarification` | self-correction, "what am I trying to say" | compress, restate, sharpen |
| `development` | "expand", "turn into", structure requests | explicit collaboration |
| `emotional_processing` | affect-rich, symbolic language | contain, don't over-rationalize |
| `task_conversion` | action orientation, "make this into" | operational, structured output |

### Response contracts

`no_response` · `acknowledgment_only` · `continuation_cue` · `clarification` · `summary` · `structural_extraction` · `emotional_mirroring` · `option_generation` · `conversion` · `deeper_reasoning`

### AI presence levels

| Level | Name | Example |
|---|---|---|
| 0 | silent | background store + infer only |
| 1 | acknowledgment | "got it" or visual only |
| 2 | momentum cue | "keep going", "two threads emerging" |
| 3 | reflective assist | light summary / structure |
| 4 | active collaborator | full reasoning (Development only by default) |

### Mode router state (backend target)

```yaml
mode: raw_dump
response_contract: minimal_ack
ai_presence: low
goal_state: preserve_flow
background_tasks:
  - store_fragment
  - detect_entities
  - detect_open_loops
```

**Pillars:** P1, P3  
**Build unit:** `CaptureModeRouter` (v1: client heuristics + bridge hook stub)  
**UI guidance (not dialogue-only):** elastic field, post-send soft affordances, progressive revelation

### Risks if wrong

| Failure | Symptom |
|---|---|
| Too chatty | User composes for the AI |
| Too interpretive | AI colonizes thought before it forms |
| Too structured | User feels evaluated early |
| Too passive | System feels dead |
| Too visible | AI becomes the center |

---

## Theme D — Bridge / subscription / mental environment (msgs 7–10)

**User intent:** Bridge as product via subscription model (Kimi); users prompt their mental environment; capability builder from primitives.

**Decisions extracted:**

- Product generates scoped API keys; provider keys stay server-side
- Model assembles from **fixed infrastructure primitives**, not arbitrary code
- User instructions → capability spec → runtime UI generation
- Nine-layer pipeline: Capture → Mode Router → Mental Environment → Capability Builder → Primitive Runtime → Model Adapter → Memory → Evaluator → UI Renderer

**Pillars:** P5 (substrate fidelity)  
**Status:** **Adjacent — not in Mobile Thought Capture v1**  
**Track in:** backend element, `sol-backend` holodeck  
**Promote when:** Capture Surface + Scroll Engineering ship

---

## Theme E — Semantic-zoom answers (msgs 11–12)

**User intent:** AI answers as expandable semantic documents, not flat walls of text.

**Decisions extracted:**

- Default answer = compressed semantic overview (5–7 blocks)
- Each paragraph is a semantic object with expand/branch/save actions
- Default: light steering, not full explanation
- Spatial model: vertical depth, horizontal adjacency on objects

**Pillars:** P6, P7, P8  
**Build unit:** `SemanticBlock` component (Development Surface)  
**Status:** Phase 2 — after Capture Surface shell

---

## Theme F — Scroll Engineering (msgs 13–14)

**User pasted:** 15-rule streaming chat experience contract.

**Adopted as Pillar 2** in `PILLARS.md`.

**Core invariant:** Never move the reader against their intent.

**States:** `Following` | `Detached`

**Intent signals (detach auto-follow):** scroll away, select text, type, keyboard nav, open link, search, expand/collapse, tap message, media interaction

**Engineering contract:**

```text
Reader position is state.
Auto-follow is conditional.
Layout shifts must preserve anchors.
Streaming must not override intent.
Navigation must be recoverable.
```

**Pillars:** P2  
**Build unit:** `ScrollEngine` module in `product/thought_capture_pwa/src/scroll/`  
**Priority:** First implementation slice after capture shell scaffold

---

## Scope matrix

| Unit | In v1 subproject | Phase |
|---|---|---|
| Capture Surface shell | yes | 1 | **done** (`thought_capture_pwa`) |
| Scroll Engineering | yes | 1 | **done** |
| GestureZone on thought objects | yes | 2 | **done** |
| CaptureModeRouter (heuristic stub) | yes | 2 | partial (MTC-003 local; MTC-006 bridge compose pending) |
| Post-send soft affordances | yes | 2 | **done** |
| Development Surface | stub only | 3 |
| SemanticBlock answers | yes | 3 |
| Bridge subscription / capabilities | no | backend |
| Mental environment builder | no | runtime |

---

## Message index

| Msg | Role | Topic |
|---|---|---|
| 1 | user | Gesture feasibility |
| 2 | assistant | Techniques + Thought Tube pattern |
| 3 | user | Back gesture concern |
| 4 | assistant | Edge guard + object gestures |
| 5 | user | Layout screenshot + AI reformulation |
| 6 | assistant | Full capture/development spec (15 sections) |
| 7 | user | Bridge + Kimi + mental environment |
| 8–10 | assistant | Capability primitives, pipeline |
| 11–12 | user/assistant | Semantic-zoom answer model |
| 13 | user | Scroll Engineering 15 rules |
| 14 | assistant | Scroll Engineering pillar confirmation |

---

## Provenance

- Bundle: `mobile_artifacts/2026-06-27/conv_20260627_125956_smooth-microgestures-on-mobile/`
- Prior research brief: `mobile_artifacts/2026-06-27/frontend-chat-converter-research-brief.md`
- Parent pillars: `docs/workboards/sol-frontend/PILLARS.md`
