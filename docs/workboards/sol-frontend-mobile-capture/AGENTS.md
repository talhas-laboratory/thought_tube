# Agent Rules — Mobile Thought Capture

## Pillar + contract + scroll + motion + aesthetic + composition discipline

- Read parent `PILLARS.md` before any edit
- Read `COMPOSITION.md` before stream layout, assist rendering, utterance weight, or deposit coupling
- Read `AESTHETICS.md` before capture layout, copy, typography, or visual hierarchy
- Read `LIBRARY.md` before library overview, warmth sections, row anatomy, or return-from-library behavior
- Read `SCROLL.md` before transcript layout, streaming, auto-scroll, reopen, or anchor logic
- Read `MOTION.md` before any transition, gesture release, CSS animation, or route change animation
- Name `pillars` and `contract` in every task packet and PR description
- Name `scroll_primitives`, `intent_signals`, `layout_rules` when changing scroll behavior
- Name `motion:`, `tier:`, `scroll_impact:` when adding or changing UI motion
- Name `aesthetic_primitives:` when changing visual/copy design; `literal_metaphor: none` unless DEC says otherwise
- Name `composition_primitives:`, `utterance_types:`, `composition_phase:` when changing stream or assist layout
- Name `library_sections:` when changing library grouping, row labels, or reopen behavior
- If a change serves neither pillars nor scroll/motion/aesthetic/composition primitives → it belongs outside this subproject
- New scroll, motion, aesthetic, or composition primitives require `DECISIONS.md` entry before first use

## Scroll quick check

```text
Primitive named? → follow_state respected? → intent signals wired? → Rules 1–9,11–13? → No animated scroll?
```

Reject ad-hoc `transition: all`, unnamed keyframes, and scroll-position animation.

## Capture vs Development

- `/capture` route: presence 0–2 default, immersive shell, motion tier max 2 (user-initiated only)
- `/develop` route: presence 3–4 allowed, `motion.expand` and `motion.cross` permitted
- Never merge UX or motion defaults across routes

## Mobile verification

- Scroll and gesture work requires manual notes: device or viewport, iOS Safari if possible
- Edge guard behavior must be explicitly tested
- Motion: verify `prefers-reduced-motion` degrades to Tier 0

## Deferred topics (do not implement here)

- Bridge subscription / Kimi API key product
- Capability builder / mental environment config
- Full primitive runtime UI generation

Record interest in these as `DECISIONS.md` deferrals with link to backend element.
