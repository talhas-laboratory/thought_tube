# Gates — Mobile Thought Capture

Inherits parent Pillar Gate from `../sol-frontend/GATES.md`.

## Contract Gate

- Implementation matches the relevant section of `CONTRACTS.md`
- TypeScript types or module names align with contract identifiers where applicable

## Capture Gate (phase 1+)

- `/capture` route exists and is distinct from demo/atlas view
- Layout passes CaptureSurface invariants (manual checklist in task packet)
- No required categorization at send

## Scroll Gate (phase 1+)

Inherits rules from `SCROLL.md`.

- `Following` / `Detached` states observable in UI
- Intent signals from §Intent signals detach auto-follow
- Jump-to-latest resumes `following` via `scroll.jump-latest`
- New user turn uses `scroll.anchor-turn` near viewport top (instant, not animated)
- Streaming while detached uses `scroll.hold` + `scroll.indicator` only
- Layout shifts use `scroll.preserve-anchor` (rule 12)
- Reopen uses `scroll.reopen` at last user turn (rule 11)
- Types/defaults align with `product/thought_capture_pwa/src/scroll/scroll-types.ts`

## Gesture Gate (phase 2+)

- Edge guard rejects pointerdown in margin
- `touch-action: pan-y` on gesture zones
- Fallback control exists for every gesture action

## Mode Gate (phase 2+)

- Heuristic mode state logged or visible in dev panel
- Fragment dump does not trigger level-4 assistant paragraph

## Motion Gate

- Every UI motion maps to a primitive in `MOTION.md` §Primitives
- Task/PR lists `motion:`, `tier:`, `scroll_impact:`
- Tier ≤ surface max (Capture: no Tier 3 unless user escalates)
- No animated scroll position changes (ScrollEngine / P2)
- `prefers-reduced-motion` tested or noted in verification
- Tokens from `product/thought_capture_pwa/src/styles/motion-tokens.css` — no stray duration literals

## Composition Gate (stream / assist UI)

- Stream cites primitives from `COMPOSITION.md` §Primitives
- System output is `coupled_insertion` under provoking deposit — no orphan assist
- Utterance type named per render (`deposit`, `cue`, `ack`, `block_cluster`, …)
- Capture: ≤1 insertion per deposit; presence ≤2; no block walls
- Active `composition_unit` (focus + coupled assist) reads at full insertion weight
- Phase transition uses `deepen_gate`, not new chat container

## Aesthetic Gate (capture UI)

- Visual/copy cites primitives from `AESTHETICS.md` §Primitives
- No literal metaphor in UI (path, walk, nature, journal tropes) unless DEC approves
- Capture honors `open_field`, `primary_locus`, `receding_context`, `quiet_default`
- Tokens from `product/thought_capture_pwa/src/styles/aesthetic-tokens.css` use role names only

## Library Gate (library UI)

Inherits rules from `LIBRARY.md`.

- Sections use warmth model: `now`, `still_moving`, `resting` — not composition-state folders
- Row primary label is user deposit text; state badge only (`open` · `waiting` · `shaped`)
- No chat thread list, AI titles, topic folders, or card grid in v1
- Return to field uses `scroll.reopen` at selected user deposit
- Horizontal adjacency from capture; edge guard + `touch-action: pan-y` on list
- `receding_context` visible across sections (focus row ≠ resting row weight)

## Done Gate

- Acceptance criteria in `SPEC.md` checked
- `artifacts/` contains verification notes
- Parent `sol-frontend` task index updated if scope completed
