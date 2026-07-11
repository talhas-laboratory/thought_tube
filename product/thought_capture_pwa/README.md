# Thought Capture PWA

New installable thought-capture web app. **Not** an extension of `mobile_surface_v1`.

## Source of truth

Read before writing code:

**[PWA Thought Capture Source Doc](../../mobile_artifacts/2026-06-27/pwa-thought-capture-source-doc.md)**

Also: `docs/workboards/sol-frontend/PILLARS.md`, `CONTRACTS.md`, `SCROLL.md`, `MOTION.md`

## Status

**Phase 1:** complete (MTC-001 shell, MTC-002 scroll, MTC-003 presence).  
**Phase 2:** MTC-004 gestures, MTC-005 post-send, MTC-006 bridge compose, MTC-008 bridge section — done.  
**Phase 3:** MTC-007 develop route — planned.

Plan: `docs/workboards/sol-frontend-mobile-capture/BRIDGE_COMPOSE_PLAN.md`

## Dev (linked — recommended)

One command starts backend + PWA:

```bash
cd product/thought_capture_pwa
npm run dev:linked
```

Then open **http://localhost:5173/capture** (or the port Vite prints if 5173 is busy).

- Backend: `http://127.0.0.1:8422` (proxied as `/api/mobile`)
- Bridge agent off by default (fast operator responses). For full OpenClaw agent:

```bash
INNER_WORLD_BRIDGE_ENABLED=true npm run dev:linked
```

## Dev (PWA only)

```bash
cd product/thought_capture_pwa
npm run dev      # http://localhost:5173 → /capture
```

Requires backend separately on `:8422` for live answers.

## Phase 1 delivered (MTC-001)

- `/capture` immersive shell — vignette, field stream, embedded input, library swipe
- PWA installability — manifest, SW, iOS meta, safe-area
- No required metadata at send

## Phase 1 continued (MTC-002, MTC-003)

1. Dexie stores: `deposits`, `insertions`, `meta`
2. Send → IndexedDB immediately → UI updates → background sync when online
3. Library sections (`now` / `still moving` / `resting`) from local stream
4. Tap library row → reopen on capture field with continuity context
5. Horizontal swipe + nav chip between field and library
6. **ScrollEngine** — `following | detached`, anchor-turn, reopen, jump-to-latest

## Scroll (MTC-002)

```text
src/scroll/
  scroll-types.ts
  scroll-intent-bus.ts
  scroll-engine.ts
  use-scroll-engine.ts
```

Field is a vertical stream. Footer shows `following` / `detached`. Scroll up → detached; **jump to latest** resumes follow.

## Presence (MTC-003)

```text
src/capture/
  capture-mode.ts      # CaptureModeState + classifier
  local-composer.ts    # silent gate on send; nudge/shape compose
  capture-mode-overlay.tsx
```

- **Send** — deposit only (no auto paragraphs)
- **nudge** — light coupled insertion (presence ≤2)
- **shape** — block facets from deposit (develop phase)
- Dev debug in nav when `VITE_CAPTURE_MODE_DEBUG=true` (off by default)

## Gestures (MTC-004)

Library pane still uses horizontal swipe (`swipe-surface.tsx`). Per-unit thread/center/facet lens navigation removed — field is deposit + insertion only.

## Post-send (MTC-005)

Optional `continue · nudge · shape` row for 5s after send (`motion.reveal`).

## Bridge section (MTC-008 done)

All outbound bridge I/O routes through `src/bridge/`:

| Module | Role |
|--------|------|
| `index.ts` | Public facade — only import from outside `bridge/` |
| `section-adapter.ts` | Session + deposit sync |
| `transport.ts` | HTTP (internal) |
| `types.ts` | `mobile_capture` surface profile + provenance |

```bash
npm test   # vitest — provenance + profile
```

Env: `VITE_BRIDGE_SECTION_API_BASE`, `VITE_BRIDGE_SECTION_SYNC_ENABLED=false` for local-only.

## Bridge compose (MTC-006 — done)

Invited **nudge/shape** calls `POST /api/mobile/compose` (server runs `run_reasoning`, returns coupled insertion). v0: not auto-compose on silent deposit.

```bash
# When testing compose locally (backend required)
INNER_WORLD_BRIDGE_ENABLED=true python3 tools/run_inner_world_miniapp.py
VITE_BRIDGE_SECTION_SYNC_ENABLED=true VITE_BRIDGE_SECTION_COMPOSE_ENABLED=true npm run dev
```

## Deploy (production)

Deploy to **https://notes.talhaslaboratory.xyz** on the OpenClaw server (cloudflared + Inner World backend on `:8422`):

```bash
# From a machine that can SSH to the OpenClaw host (home LAN / tailnet)
python3 tools/deploy_thought_capture_pwa_to_openclaw.py
```

Options:

```bash
python3 tools/deploy_thought_capture_pwa_to_openclaw.py --capture-hostname notes.talhaslaboratory.xyz
python3 tools/deploy_thought_capture_pwa_to_openclaw.py --skip-build   # if dist/ already built
python3 tools/deploy_thought_capture_pwa_to_openclaw.py --remote talha@talhas-laboratory
```

What it does:

1. `npm ci && npm run build` (production env → `/api/mobile` on same origin)
2. Rsync `src/`, `tools/`, `product/thought_capture_pwa/dist/` to the server
3. Configure capture authentication and print the resulting username/password
4. Enable bridge execution through the `thought_tube_router` OpenClaw agent
5. Patch cloudflared ingress + DNS for the subdomain
6. Restart `inner-world.service` and all active tunnel connectors

After deploy: open **https://notes.talhaslaboratory.xyz/capture**, enter the printed credentials, then Add to Home Screen.

Library and deposits persist in **IndexedDB on device** (`thought_capture_pwa`). Online deposits sync to `/api/mobile`; compose runs through the bridge with bounded session context and the connected OpenClaw agent. Local composition is an offline fallback, not the normal answer path.

## Next

- **MTC-007** — `/develop` route stub
- Serve `dist/` over HTTPS for real PWA install testing (e.g. `npx serve dist` behind tunnel)

## Holodeck

- Element: `frontend`
- Holodeck: `sol-frontend`
- Workboard: `docs/workboards/sol-frontend-mobile-capture/`
