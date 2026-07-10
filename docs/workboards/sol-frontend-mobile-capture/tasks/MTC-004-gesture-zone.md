# MTC-004 — GestureZone on thought frame

**Status:** `done`  
**Contract:** `GestureZone`  
**Pillars:** P4, P8  
**Phase:** 2  
**motion:** `motion.follow`, `motion.settle`  
**tier:** 2  
**scroll_impact:** `none`

## Problem

Horizontal microgestures must live on thought objects, not the whole page — with iOS edge guard and vertical scroll preserved.

## Delivered

| Module | Role |
|--------|------|
| `src/gesture/gesture-types.ts` | `EDGE_GUARD_PX`, lens types |
| `src/gesture/gesture-engine.ts` | Edge guard, direction lock, lens commit |
| `src/gesture/use-horizontal-gesture.ts` | React hook |
| `src/gesture/gesture-zone.tsx` | 3-pane lens peek (thread \| center \| facet) |
| `capture/composition-unit.tsx` | Thread/facet panels + unit body |
| `capture-field.tsx` | GestureZone on locus unit only |
| `swipe-surface.tsx` | Refactored to shared gesture engine |

## Behavior

- **Locus unit only** — horizontal drag reveals adjacent lenses
- **thread** (swipe left) — up to 2 preceding deposits
- **facet** (swipe right) — browse state + inferred mode/contract
- **Fallback chips** — `‹ thread` · `center` · `facet ›` (non-gesture path)
- `touch-action: pan-y` on `.gesture-zone`
- 32px screen-edge guard on pointerdown

## Acceptance criteria

- [x] Edge guard rejects pointerdown in margin
- [x] `touch-action: pan-y` on gesture zones
- [x] Fallback control for lens navigation
- [x] Transform-only drag; settle transition on release

## Verification

```bash
cd product/thought_capture_pwa && npm test && npm run dev
```

- [ ] Horizontal drag on locus deposit (not screen edge) reveals thread/facet
- [ ] Vertical scroll in field still works when dy > dx
- [ ] Fallback chips switch lenses without drag
- [ ] Library pane swipe still works at page level
