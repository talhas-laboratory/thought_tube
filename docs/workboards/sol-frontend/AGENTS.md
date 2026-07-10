# Agent Rules — SOL Frontend

## Pillar-first discipline

- Every task packet must list `pillars: [P1, P2, ...]` using pillar numbers from `PILLARS.md`.
- Capture/PWA work must follow `../sol-frontend-mobile-capture/SCROLL.md` for scroll/streaming and `MOTION.md` for UI motion.
- Every PR-sized change should state which pillar rejection it avoids.
- If work cannot map to a pillar, stop and ask whether it belongs in this workspace.

## Surface boundaries

- Capture mode and Development mode are different surfaces — do not merge their UX defaults.
- Mobile (`mobile_surface_v1`) and miniapp may differ in chrome but must share semantic payloads.
- Do not fork ontology for surface convenience.

## Evidence

- Scroll and gesture work needs manual mobile verification notes or recording paths.
- Feed work must cite payload fields (`preview_payload`, `expand_payload`, etc.).
- Promote research into element space with `#ingest` when a decision becomes durable.

## Updates

- Append `UPDATES.jsonl` for meaningful progress.
- Edit task files for current state.
- Record tensions between pillars in `DECISIONS.md`, not in chat only.
