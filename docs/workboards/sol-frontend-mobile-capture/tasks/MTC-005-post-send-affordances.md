# MTC-005 — Post-send soft affordances

**Status:** `done`  
**Contract:** `CaptureSurface`  
**Pillars:** P1, P6  
**Phase:** 2  
**motion:** `motion.reveal`  
**tier:** 2  
**scroll_impact:** `none`  
**aesthetic_primitives:** `optional_deepen`, `invited_assist`

## Problem

After send, user should see optional deepen paths without forced assist or chatbot paragraphs.

## Delivered

| Module | Role |
|--------|------|
| `capture/post-send-affordances.tsx` | `continue` · `nudge` · `shape` row |
| `capture-page.tsx` | 5s reveal window after deposit; dismiss on scroll/type |

## Behavior

- Send → `motion.reveal` row above input for 5s
- **continue** — dismiss (default rhythm: keep depositing)
- **nudge** / **shape** — invoke composition on focus deposit, then dismiss
- Same chips mirrored on locus unit while window open
- Auto-dismiss on scroll, input focus, library select

## Acceptance criteria

- [x] Non-forced affordances after send
- [x] No auto assistant paragraph on send (MTC-003)
- [x] Dismissible without engaging assist

## Verification

- [ ] Send deposit → optional row appears above input
- [ ] Tap continue → row hides; field stays user-only
- [ ] Tap nudge/shape → coupled insertion; row hides
- [ ] Scroll or focus input → row hides
