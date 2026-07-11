# Motion — Interaction Grammar Extension

**Status:** binding  
**Owner:** talha  
**Parent:** `../sol-frontend/PILLARS.md` (extends Pillar 8)  
**Applies to:** `product/thought_capture_pwa/`  
**Created:** 2026-06-27

Animation in this product is **instrumentation for flow**, not decoration. Agents must treat this file as binding alongside `CONTRACTS.md` for any UI, gesture, or transition work.

---

## Agent decision flow

Before adding or changing any animation:

```text
1. Name the motion primitive(s) from §Primitives — or stop (no ad-hoc motion)
2. Assign tier from §Tiers — reject if tier > surface max
3. Map pillars — must serve P2/P3/P4/P8; must not violate P1/P2 rejections
4. Declare scroll_impact: none | anchor-preserve | forbidden-if-detached
5. Run decision test (§Decision test)
6. If new primitive needed → record DEC in DECISIONS.md before shipping
```

Task packets and PRs must include:

```yaml
motion: [motion.confirm]           # one or more primitives
tier: 1
scroll_impact: none
surface: capture | develop
pillars: [P3, P8]
```

---

## Core rule

**Animation communicates state, continuity, and acknowledgment. It never performs helpfulness, never moves the reader, and never invents a dialect outside the motion primitives.**

---

## Purpose (why motion exists)

| Purpose | Job | Pillar |
|---|---|---|
| **Confirm** | Action registered when haptics unavailable | P3, P8 |
| **Continuity** | User knows where they are spatially | P4, P6, P8 |
| **Disclose** | System state without modal interruption | P2, P3 |
| **Follow-through** | Finger-attached drag + semantic settle | P4 |

Motion is **not** for: delight, branding flair, chatbot personality, or proving the AI is "thinking."

---

## Primitives (interaction grammar vocabulary)

Compose UI from these. Do not create unnamed one-off animations.

| ID | Name | Meaning | Duration tier | Typical trigger |
|---|---|---|---|---|
| `motion.hold` | Hold | Intentional stillness | 0 | raw dump; AI presence 0 |
| `motion.confirm` | Confirm | Action landed | 1 | send, save, tap affordance |
| `motion.follow` | Follow | 1:1 with finger during drag | 0* | pointermove on gesture zone |
| `motion.settle` | Settle | Spring to semantic state or snap back | 2 | pointerup after swipe |
| `motion.reveal` | Reveal | Progressive disclosure | 2 | post-send affordances |
| `motion.expand` | Expand | Depth on object in place | 2 | semantic block open |
| `motion.cross` | Cross | Surface/route change | 3 | Capture → Development |
| `motion.status` | Status | Background state signal | 1 | offline, streaming, detached |

\* `motion.follow` uses transform updates per frame; no CSS transition during drag.

### Maps to Pillar 8 primitives

| Pillar 8 primitive | Motion pair |
|---|---|
| fragment card | `confirm` on send |
| semantic swipe | `follow` → `settle` |
| expand-to-depth | `expand` |
| bottom capture sheet | `reveal` / `settle` |
| haptic confirmation | `confirm` (visual on iOS) |
| lens switcher | `settle` or `cross` |

---

## Tiers (policy)

| Tier | Name | Duration | Capture | Development |
|---|---|---|---|---|
| **0** | Instant | 0ms | ✅ default | ✅ scroll anchors, focus |
| **1** | Micro | 80–150ms | ✅ | ✅ press, confirm, status |
| **2** | Functional | 200–350ms | ⚠️ user-initiated objects only | ✅ reveal, expand, settle |
| **3** | Structural | 250–400ms | ❌ default | ⚠️ `motion.cross` only |
| **4** | Forbidden | — | ❌ | ❌ hero, stagger lists, parallax |

**Capture mode max:** Tier 2 on explicit user gesture; Tier 1 ambient; no Tier 3 unless user escalates surface.

---

## Surface × AI presence policy

| Presence | Name | Allowed motion |
|---|---|---|
| 0 | silent | `motion.hold` only |
| 1 | acknowledgment | `hold`, `confirm` |
| 2 | momentum cue | `hold`, `confirm`, `reveal` (subtle) |
| 3 | reflective assist | + `expand` (Development surface) |
| 4 | active collaborator | + `expand`, limited `cross` |

**Capture route:** cap at presence 2 → no `expand` on assistant content unless user explicitly asks.

---

## Scroll impact (mandatory declaration)

| Value | Meaning | Agent rule |
|---|---|---|
| `none` | Does not touch scroll container | Preferred default |
| `anchor-preserve` | Layout may change; ScrollEngine keeps anchor | Required for `expand` in transcript |
| `forbidden-if-detached` | Must not run when scroll state is `detached` | streaming indicators only |

**Hard reject:** Any animation that changes `scrollTop` or scroll container position without explicit user navigation request. Violates Pillar 2.

---

## Decision test

Ask before shipping:

1. Does this help the user **keep going**, **know where they are**, or **trust an action landed**?
2. Does it avoid moving the reader and avoid chatbot gravity?
3. Is it composed from §Primitives, not invented?
4. Is tier ≤ surface max?
5. Is `scroll_impact` declared and implemented?

If any answer is no → do not ship; revise or record tension in `DECISIONS.md`.

---

## Rejects (binding)

| Reject | Pillar |
|---|---|
| Auto-scroll animation during streaming | P2 |
| Staggered list entrance in Capture | P1, P3 |
| Full-page slide as primary navigation | P4 |
| Bouncy onboarding / celebration on send | P1, P3 |
| Parallax, decorative loops | P8 |
| Per-component random easing curves | P8 |
| Animate `height` on transcript without anchor preserve | P2 |
| Assistant "typing" or thinking animation at presence 0–1 | P3 |

---

## Implementation contract

### Tokens (`src/styles/motion-tokens.css`)

```css
:root {
  --motion-instant: 0ms;
  --motion-micro: 120ms;
  --motion-functional: 280ms;
  --motion-structural: 320ms;
  --ease-settle: cubic-bezier(0.2, 0.9, 0.2, 1);
  --ease-reveal: cubic-bezier(0.0, 0.0, 0.2, 1);
  --motion-press-scale: 0.98;
}
```

### Tool choice

| Kind | Use |
|---|---|
| CSS `transition` | `confirm`, `reveal`, press states — `transform`, `opacity` only |
| `requestAnimationFrame` + `transform` | `follow` during drag |
| Spring / ease on release | `settle` |
| `document.startViewTransition` | `cross` with fallback instant navigate |
| No animation | scroll anchors, Tier 0 paths |

### `prefers-reduced-motion`

- Tier 2–3 → Tier 0 (instant state change)
- Keep `confirm` as instant opacity/state flip, not removal of all feedback

---

## Contract annotation (for CONTRACTS.md consumers)

When extending a contract, add:

```markdown
### Motion
- primitives: [motion.confirm]
- tier_max: 1
- scroll_impact: none
```

---

## Canonical moments (reference implementations)

| Moment | Primitives | Tier | scroll_impact |
|---|---|---|---|
| User sends fragment | `confirm` | 1 | none |
| Saved offline | `status` | 1 | none |
| Affordances after send | `reveal` | 2 | none |
| Card horizontal swipe | `follow` → `settle` | 0 → 2 | none |
| Stream while detached | `status` | 1 | forbidden-if-detached |
| Open semantic block | `expand` | 2 | anchor-preserve |
| Escalate to Development | `cross` | 3 | none |

---

## Provenance

- Pillar 8 interaction grammar: `../sol-frontend/PILLARS.md`
- PWA native-feel layer: `mobile_artifacts/2026-06-27/pwa-thought-capture-source-doc.md` §10
- Gesture springs: `conv_20260627_125956_smooth-microgestures-on-mobile` Theme A
- Scroll Engineering: Pillar 2 — motion must not substitute for scroll state machine (`SCROLL.md`)

---

## Agent obligations summary

1. Read this file when touching UI motion, CSS transitions, gestures, or route transitions.
2. Every motion change lists `motion:`, `tier:`, `scroll_impact:` in task/PR.
3. New primitives require `DECISIONS.md` entry before use.
4. Motion Gate in `GATES.md` must pass before `done`.
