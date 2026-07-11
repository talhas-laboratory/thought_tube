# Contracts — Mobile Thought Capture

Binding interfaces for `product/thought_capture_pwa/`. Scroll policy: `SCROLL.md`. Motion policy: `MOTION.md`. Implementations must satisfy these contracts before tasks move to `done`.

---

## CaptureSurface

**Pillars:** P1, P3, P6

### Layout invariants

- Full viewport height; no persistent sidebar or document chrome
- One dominant content object (current thought frame) in focus
- Dark surround / vignette; spotlight on active content
- Input embedded in scene bottom (elastic textarea, not rigid form)
- Bottom action row: send + optional voice (voice stub OK in v1)

### Copy invariants

- No "Create a note" framing
- Placeholder shifts subtly by inferred mode (not instructional walls of text)
- Empty state: invitation to dump, not categorize

### Surface boundary

- Capture route must not show Development tools (outlines, metadata panels, branch trees)
- Transition to Development is explicit user action or mode escalation signal

### Rejects

- Document-editor mental model at entry
- Required tags/categories before send
- Level 4 AI presence by default

### Motion

- primitives: `motion.hold`, `motion.confirm`, `motion.reveal`
- tier_max: 2 (reveal only after user send)
- scroll_impact: `none`
- See `MOTION.md` §Surface × AI presence — capture caps at presence 2

---

## ScrollEngine

**Pillars:** P2  
**Canonical spec:** `SCROLL.md` (full framework — this section is summary)

### State

```typescript
type ScrollFollowState = "following" | "detached";
```

### Transitions to `detached`

Any of: user scrolls away from live edge, selects text, focuses input, opens link, searches, expands block, taps message, interacts with media.

### Transitions to `following`

User at live edge (within threshold) OR explicit "Jump to latest" action.

### Turn layout rules

1. On new user message: scroll anchor places user message near **top** of viewport
2. Assistant stream grows into space below without moving detached reader
3. Offscreen streaming: show indicator + jump affordance
4. Layout shifts (images, markdown, lazy history): preserve anchor element + offset
5. Reopen: land on last **user** message, not absolute bottom

### Engineering contract

```text
Reader position is state.
Auto-follow is conditional.
Layout shifts must preserve anchors.
Streaming must not override intent.
```

### Motion

- primitives: `motion.status` (offscreen stream indicator only)
- tier_max: 1
- scroll_impact: `forbidden-if-detached`
- **Reject:** animated scroll position changes

---

## GestureZone

**Pillars:** P4, P8

### Constants

```typescript
const EDGE_GUARD_PX = 32; // 24–44 range; 32 default
```

### Rules

- Attach gestures to `.gesture-zone` elements (thought cards, lens peek), not `document`
- CSS: `touch-action: pan-y` on gesture zones
- Movement via `transform: translateX()` only during drag
- Direction lock: if `abs(dx) > abs(dy)` after threshold, horizontal wins
- On `pointerdown`: reject if `clientX < EDGE_GUARD || clientX > width - EDGE_GUARD`
- Spring release on `pointerup`; threshold commit for lens/branch switch
- Non-gesture fallback always visible (chevrons, tabs, or handles)

### Rejects

- Full-page horizontal carousel as primary nav
- Edge swipe as main interaction
- `preventDefault` on document touchstart as core strategy

### Motion

- primitives: `motion.follow`, `motion.settle`
- tier_max: 2
- scroll_impact: `none`
- During drag: no CSS transition; use `transform` + rAF

---

## CaptureModeState

**Pillars:** P1, P3

### Shape

```typescript
type CaptureMode =
  | "raw_dump"
  | "exploration"
  | "clarification"
  | "development"
  | "emotional_processing"
  | "task_conversion";

type ResponseContract =
  | "no_response"
  | "acknowledgment_only"
  | "continuation_cue"
  | "clarification"
  | "summary"
  | "structural_extraction"
  | "emotional_mirroring"
  | "option_generation"
  | "conversion"
  | "deeper_reasoning";

type AiPresenceLevel = 0 | 1 | 2 | 3 | 4;

interface CaptureModeState {
  mode: CaptureMode;
  response_contract: ResponseContract;
  ai_presence: AiPresenceLevel;
  goal_state: "preserve_flow" | "sharpen_meaning" | "build_artifact" | "contain";
  confidence: number; // 0–1 heuristic
}
```

### v1 implementation

- Client-side heuristic classifier on last N messages (no ML required)
- Default in capture route: `raw_dump` + `minimal_ack`/`no_response` + presence 0–1
- Escalate to presence 3–4 only on Development route or explicit user affordance ("ask AI", "expand")
- Bridge hook: emit `capture_mode_state` in session context for `prepare_turn`

### Default capture mapping

| Mode | Default contract | Max presence in capture |
|---|---|---|
| raw_dump | no_response or acknowledgment_only | 1 |
| exploration | continuation_cue | 2 |
| clarification | summary | 2 |
| development | structural_extraction | 4 (→ Development surface) |
| emotional_processing | emotional_mirroring | 2 |
| task_conversion | conversion | 3 (→ Development surface) |

### Motion

- primitives: driven by `ai_presence` — see `MOTION.md` §Surface × AI presence
- tier_max: maps from presence level (0 → hold only; 4 → expand allowed on develop route)
- scroll_impact: `none` for presence signals; assistant content uses `anchor-preserve` if in transcript

---

## SemanticBlock (phase 3)

**Pillars:** P6, P7

Expandable paragraph unit for Development Surface answers.

```typescript
interface SemanticBlock {
  id: string;
  label: string;
  compressed: string;      // one sentence default
  expanded?: string;       // loaded on demand
  actions: ("expand" | "branch" | "save" | "turn_into_spec" | "continue")[];
}
```

Default assistant output in Development: 3–7 blocks, not one wall of text.

### Motion

- primitives: `motion.expand`
- tier_max: 2
- scroll_impact: `anchor-preserve`
