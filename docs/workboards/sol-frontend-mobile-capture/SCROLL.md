# Scroll Engineering — Interaction Framework

**Status:** binding  
**Owner:** talha  
**Parent:** `../sol-frontend/PILLARS.md` (Pillar 2)  
**Applies to:** `product/thought_capture_pwa/`  
**Created:** 2026-06-27

Scroll position is **sacred state**. Agents must treat this file as binding alongside `CONTRACTS.md` and `MOTION.md` for any transcript, streaming, layout, or navigation work.

**Core invariant:** Never move the reader against their intent.

---

## Agent decision flow

Before changing scroll behavior, streaming layout, or transcript structure:

```text
1. Identify scroll primitive(s) from §Primitives — or stop (no ad-hoc scroll logic)
2. Declare follow_state: following | detached
3. List intent_signals that must detach
4. Check layout rule from §Fifteen rules — which rule(s) apply?
5. Verify motion subordinate to scroll (MOTION.md scroll_impact)
6. Run decision test (§Decision test)
7. New primitive → DECISIONS.md before shipping
```

Task packets and PRs touching scroll/streaming must include:

```yaml
scroll_primitives: [scroll.anchor-turn, scroll.preserve-anchor]
follow_state: detached          # expected default during read
intent_signals: [select, scroll]
layout_rules: [4, 6, 12]        # rule numbers from §Fifteen rules
pillars: [P2]
```

---

## Engineering contract

```text
Reader position is state.
Auto-follow is conditional (Following | Detached).
Layout shifts must preserve anchors.
Streaming must not override intent.
Navigation must be recoverable.
```

---

## State machine

```typescript
type ScrollFollowState = "following" | "detached";

interface ScrollEngineState {
  follow_state: ScrollFollowState;
  anchor_element_id: string | null;
  anchor_offset_px: number;
  live_edge_threshold_px: number; // default 48
  last_user_turn_id: string | null;
}
```

### Transitions to `detached`

On **any** intent signal (§Intent signals) → set `follow_state: detached`. Do not animate scroll position as part of the transition.

### Transitions to `following`

- User within `live_edge_threshold_px` of live edge, **or**
- Explicit `scroll.jump-latest` action

### Forbidden

- Programmatic `scrollTop` / `scrollIntoView` while `detached` unless user initiated navigation
- Default `following` on mount without checking reopen rules

---

## Primitives (scroll vocabulary)

| ID | Name | Job |
|---|---|---|
| `scroll.follow` | Follow | While `following`, keep live edge in view during stream |
| `scroll.detach` | Detach | Enter `detached`; stop all auto-follow |
| `scroll.hold` | Hold | No scroll mutation — reader stays put |
| `scroll.anchor-turn` | Anchor turn | New user message placed near **top** of viewport |
| `scroll.preserve-anchor` | Preserve anchor | Layout shift compensates so anchor stays visually fixed |
| `scroll.indicator` | Indicator | Offscreen stream / new content signal (no scroll) |
| `scroll.jump-latest` | Jump latest | User resumes `following` at live edge |
| `scroll.reopen` | Reopen | Restore at last **user** turn, not absolute bottom |
| `scroll.navigate` | Navigate | User-initiated jump (search, link, message tap) |

Compose behavior from primitives. Do not add unnamed `scrollIntoView` calls.

### Motion coupling

| Scroll primitive | Allowed motion | MOTION scroll_impact |
|---|---|---|
| `scroll.indicator` | `motion.status` | `forbidden-if-detached` optional |
| `scroll.anchor-turn` | none (instant) | Tier 0 |
| `scroll.preserve-anchor` | none | Tier 0 — instant compensation |
| `scroll.jump-latest` | optional `motion.confirm` | user-initiated only |

---

## Intent signals (detach triggers)

Not just scrolling. **Any** of these → `scroll.detach`:

| Signal | Detection |
|---|---|
| `scroll` | User scrolls away from live edge |
| `select` | Text selection start/change |
| `type` | Input focus / composition |
| `keyboard` | Keyboard navigation |
| `link` | Link tap / open |
| `search` | Search UI active |
| `expand` | Block expand/collapse |
| `tap-message` | Message tap (navigation intent) |
| `media` | Media/code block interaction |
| `regenerate` | Regenerate / branch / retry start |
| `error` | Error surface interaction |

Register signals in one `ScrollIntentBus` — do not scatter detach logic across components.

---

## Fifteen rules (source contract)

From Smooth Microgestures conversation (msgs 13–14). Each implementation must map to rule numbers.

| # | Rule | Primitive(s) |
|---|---|---|
| 1 | Move only when reader asked to move | `scroll.hold`, `scroll.navigate` |
| 2 | Follow only while following | `scroll.follow`, `scroll.detach` |
| 3 | Every interaction is intent | §Intent signals |
| 4 | Start new turn near top of viewport | `scroll.anchor-turn` |
| 5 | Stream answer into space below | `scroll.follow` (if following) |
| 6 | Keep previous turn partially visible | layout padding above anchor |
| 7 | New content may arrive offscreen | `scroll.hold`, `scroll.indicator` |
| 8 | Show what's happening out of view | `scroll.indicator` |
| 9 | Easy return to latest | `scroll.jump-latest` |
| 10 | Jump anywhere in long threads | `scroll.navigate` (phase 3) |
| 11 | Reopen at last meaningful turn | `scroll.reopen` |
| 12 | Preserve place on layout change | `scroll.preserve-anchor` |
| 13 | Interruptions don't steal position | `scroll.detach` on regenerate/error |
| 14 | Responsive in long threads | virtualize + preserve anchor |
| 15 | Accessible without noise | focus order, live regions — no scroll spam |

**v1 minimum:** rules 1–9, 11–13. Rule 10 (search/jump) is phase 3.

---

## Decision test

1. If the user is reading mid-thread, does this change move them without consent?
2. Is `follow_state` respected for the full streaming lifecycle?
3. On layout shift (image load, markdown, code block), does anchor preservation run?
4. Does motion stay subordinate (no animated scroll — see MOTION.md)?
5. Is reopen behavior `scroll.reopen` not blind bottom snap?

Any **no** → do not ship.

---

## Rejects (binding)

| Reject | Rule |
|---|---|
| Auto-scroll as default | 1, 2 |
| Stream tokens yank viewport while detached | 7, 2 |
| `scrollIntoView({ block: 'end' })` on every message | 4, 11 |
| Regenerate without position warning | 13 |
| Animate `scrollTop` | MOTION + P2 |
| Dispose anchor on lazy-load without preserve | 12 |
| Following state without live-edge check | 2 |

---

## Implementation contract

### Module layout

```text
product/thought_capture_pwa/src/scroll/
  scroll-engine.ts       # state machine + anchor math
  scroll-intent-bus.ts   # intent signal → detach
  use-scroll-engine.ts   # React hook for transcript container
  scroll-types.ts        # types (canonical)
```

### Anchor turn (rule 4)

On new user message while `following`:

1. Identify user message element
2. Set `scrollTop` so message top ≈ `viewport_top + anchor_padding` (e.g. 12–24px)
3. **Instant** — no animation (Tier 0)

While `detached`: do not run anchor turn for assistant content.

### Preserve anchor (rule 12)

On height change above anchor:

```text
delta = newAnchorTop - previousAnchorTop
scrollTop += delta
```

Use `ResizeObserver` on anchor element and siblings that affect layout.

### Indicator (rules 7–8)

When streaming and `detached`:

- Show chip/badge: "New response" or pulse dot
- `scroll.indicator` + `motion.status` only
- Tap → `scroll.jump-latest`

### Reopen (rule 11)

```text
default: scroll to last user message (scroll.reopen)
not: scroll to document bottom
```

---

## Constants (defaults)

```typescript
export const SCROLL_DEFAULTS = {
  LIVE_EDGE_THRESHOLD_PX: 48,
  ANCHOR_TOP_PADDING_PX: 16,
  JUMP_LATEST_BEHAVIOR: "instant" as const,
};
```

Canonical file: `product/thought_capture_pwa/src/scroll/scroll-types.ts`

---

## Surface policy

| Surface | Scroll default |
|---|---|
| Capture transcript | `following` only at live edge after send |
| Capture (reading history) | `detached` |
| Development transcript | same machine, may allow rule 10 earlier |
| Capture shell (non-transcript) | no ScrollEngine — overscroll contained |

---

## Provenance

- Pillar 2: `../sol-frontend/PILLARS.md`
- Conversation rules 1–15: `conv_20260627_125956_smooth-microgestures-on-mobile` msgs 13–14
- Motion subordination: `MOTION.md`
- Contract summary: `CONTRACTS.md` §ScrollEngine

---

## Agent obligations

1. Read this file before transcript, streaming, or layout shift work.
2. List `scroll_primitives`, `intent_signals`, `layout_rules` in task/PR.
3. Scroll Gate in `GATES.md` must pass before `done`.
4. Never implement scroll behavior only in MOTION.md — scroll owns position; motion owns feedback.
