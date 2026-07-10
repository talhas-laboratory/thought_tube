# Social Feed UI Adaptation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Adapt the visual and interaction language of `talhas-laboratory/social_feed_UI` onto the deployed Inner World mobile surface without changing the current `/api/mobile/*` contract or deployment model.

**Architecture:** Keep the existing static PWA shell in `product/mobile_surface_v1` and port the strongest interface patterns from `social_feed_UI` into that shell rather than transplanting the React/Vite app wholesale. Reuse the current miniapp/mobile runtime, auth, and deploy path; replace the rendered shell, layout hierarchy, and interaction patterns so the experience feels like the social feed app while still serving `Capture`, `Feed`, and `Library`.

**Tech Stack:** Static HTML/CSS/vanilla JS PWA, current `miniapp.py` mobile serving path, current `/api/mobile/*` endpoints, Python HTTP tests in `tests/test_conversation_os.py`.

---

## Recommended Adaptation Strategy

Use `social_feed_UI` as a **design donor**, not as a direct runtime dependency.

Why:
- The current deployed surface is already wired for auth, hosting, PWA installability, and `/api/mobile/*`.
- The donor repo is built around React, Vite, Tailwind, mock/local API branches, and Firebase/Gemini-adjacent scaffolding we do not need.
- A direct transplant would introduce a second frontend stack and force a needless rebuild of serving/deploy paths that already work.

What to port:
- The feed card language from `src/App.tsx`
- The inline composer / expanded composer behavior
- The expanded thread / discussion treatment
- The darker social-stream visual rhythm and motion vocabulary
- The dense-but-readable meta strip, actions, and list hierarchy

What not to port:
- Firebase wiring
- Gemini/local mock API code
- The donor repo’s `/feed`, `/thought/:id`, `/thought/:id/chat` assumptions
- Desktop-twitter layout as-is
- Any layout that can horizontally overflow on small screens

## File Mapping

### Donor Files

- `social_feed_UI/src/App.tsx`
  - Primary source for page structure, card hierarchy, composer, expanded thread, feed actions
- `social_feed_UI/src/index.css`
  - Primary source for dark palette, font roles, spacing rhythm, scrollbar treatment
- `social_feed_UI/src/lib/api.ts`
  - Reference only for client-side fetch shape and UI state transitions, not endpoint reuse

### Target Files

- `product/mobile_surface_v1/index.html`
  - Replace the current editorial-paper shell with the adapted social feed shell
- `product/mobile_surface_v1/styles.css`
  - Rebuild tokens, layout, card styling, tab behavior, thread view, composer states, and viewport containment rules
- `product/mobile_surface_v1/app.js`
  - Rework renderers and interaction flow to match the new UI shape while keeping current mobile API endpoints
- `src/conversation_os/miniapp.py`
  - Keep serving behavior stable; only touch if the HTML injection path or mobile-shell containment assist still needs to exist
- `tests/test_conversation_os.py`
  - Update UI-serving assertions to match the new shell and add viewport-safety regression checks where practical

## Adaptation Rules

- `Capture`, `Feed`, and `Library` remain the top-level IA. Do not collapse back into the donor repo’s `Home/Profile` framing.
- `Capture` stays frictionless first. Conversation appears only after capture, not before.
- `Feed` is the most visually donor-like tab.
- `Library` reuses the donor card vocabulary, but with archive semantics instead of social/profile semantics.
- Every container must be viewport-safe:
  - no fixed widths wider than parent
  - no child that relies on content width to size its parent
  - all flex/grid children that can shrink must get `min-width: 0`
  - pills, chips, metadata rows, and action rows must wrap
  - long source refs, timestamps, and mono labels must break or clip safely
  - overlays, drawers, and composer surfaces must use bounded width and height

## Task 1: Restructure the Mobile HTML Shell

**Files:**
- Modify: `product/mobile_surface_v1/index.html`
- Reference: donor `social_feed_UI/src/App.tsx`
- Test: `tests/test_conversation_os.py`

- [ ] Replace the current intro-card + stacked panel shell with a social-stream structure:
  - top app frame
  - compact masthead
  - tab nav
  - dedicated capture composer area
  - feed stream container
  - library stack container
  - thread conversation surface
- [ ] Keep IDs required by the current JS contract where possible to minimize churn:
  - `#login-form`
  - `#capture-form`
  - `#thread-view`
  - `#reply-form`
  - `#feed-list`
  - `#library-sections`
- [ ] Add semantic wrapper elements that make layout control explicit:
  - `app-frame`
  - `stream-shell`
  - `stream-column`
  - `composer-card`
  - `thread-sheet`
  - `library-stack`
- [ ] Ensure no structural container depends on absolute positioning for primary layout.

## Task 2: Rebuild the Visual System in CSS

**Files:**
- Modify: `product/mobile_surface_v1/styles.css`
- Reference: donor `social_feed_UI/src/index.css`, `social_feed_UI/src/App.tsx`

- [ ] Replace the current paper/editorial aesthetic with the donor app’s darker, denser feed tone.
- [ ] Introduce a clearer token system:
  - background layers
  - card surfaces
  - border tones
  - text hierarchy
  - action states
  - thread role colors
- [ ] Port the donor repo’s interaction feel:
  - rounded stream cards
  - higher-contrast actions
  - tighter feed rhythm
  - more explicit active states
- [ ] Add hard viewport-containment rules:
  - `html, body { overflow-x: hidden; }`
  - `*`, `*::before`, `*::after { box-sizing: border-box; }`
  - `min-width: 0` on cards, rows, tab strips, text wrappers, buttons inside flex/grid
  - `max-width: 100%` on all cards, sheets, forms, media-free blocks
  - `overflow-wrap: anywhere` on chips, meta lines, thread copy, saved item summaries
  - wrapping behavior on action rows and meta strips
  - bounded widths for any modal/sheet pattern with safe-area padding
- [ ] Add responsive breakpoints that preserve containment instead of merely scaling:
  - sub-360px phones
  - standard phones
  - tablet portrait
  - larger desktop preview widths

## Task 3: Rework Client Rendering and Interaction Flow

**Files:**
- Modify: `product/mobile_surface_v1/app.js`
- Reference: donor `social_feed_UI/src/App.tsx`, `social_feed_UI/src/lib/api.ts`

- [ ] Rebuild `renderFeed()` so feed items look and behave like donor feed cards:
  - meta strip
  - stronger title hierarchy
  - summary block
  - source chips
  - compact action row
- [ ] Rebuild `renderThread()` to mirror the donor thread presentation:
  - clearer role markers
  - denser message blocks
  - better separation of user vs assistant replies
- [ ] Keep the current mobile endpoint usage unchanged:
  - `GET /feed`
  - `GET /library`
  - `POST /capture`
  - `POST /conversations/:session_id/reply`
  - `POST /feedback`
- [ ] Add class hooks needed for stateful UI:
  - active tab
  - thread available / empty
  - capture submitted
  - loading / refreshing
- [ ] Do not import donor code directly. Recreate the behavior in the current bundle.

## Task 4: Adapt Library Into the Donor Card Vocabulary

**Files:**
- Modify: `product/mobile_surface_v1/index.html`
- Modify: `product/mobile_surface_v1/styles.css`
- Modify: `product/mobile_surface_v1/app.js`

- [ ] Keep the current grouped buckets:
  - captures
  - conversations
  - saved items
- [ ] Render each bucket using the same visual language as the feed so the app feels like one system.
- [ ] Make library rows scan quickly on mobile:
  - short titles first
  - summary/preview second
  - low-noise metadata third
- [ ] Ensure long capture content and preview strings wrap safely inside card bounds.

## Task 5: Add Explicit Overflow Regression Coverage

**Files:**
- Modify: `tests/test_conversation_os.py`

- [ ] Update the existing mobile-shell serving assertions so they match the new visual shell markers.
- [ ] Add assertions that confirm the served mobile HTML includes the new structural classes or markers needed for containment.
- [ ] Add assertions that the served CSS includes core overflow-safety rules, for example:
  - `overflow-x: hidden`
  - `min-width: 0`
  - `overflow-wrap: anywhere`
  - wrapping action/meta rows

## Task 6: Verify Locally Before Deploy

**Files:**
- Modify: none

- [ ] Run focused tests for the mobile miniapp and mobile asset serving.
- [ ] Run the repo overview refresh/validate cycle after the UI changes.
- [ ] Open the mobile surface locally and check at minimum:
  - 320px width
  - 375px width
  - 430px width
  - tablet portrait width
- [ ] Confirm there is no horizontal scroll and no card/button/chip bleed in:
  - auth gate
  - capture tab
  - thread view
  - feed tab
  - library tab

## Task 7: Deploy and Live-Check the Remote Surface

**Files:**
- Modify: none unless deploy path regressions appear
- Use: `tools/deploy_inner_world_to_openclaw.py`

- [ ] Deploy the updated mobile surface to `mobile.talhaslaboratory.xyz`.
- [ ] Verify the public hostname still serves the mobile shell at `/`.
- [ ] Verify unauthenticated API access still returns `401` on `/api/mobile/feed`.
- [ ] Check the live surface on a narrow mobile viewport and confirm no overbleed remains.

## Success Criteria

- The deployed mobile surface visibly feels derived from `social_feed_UI`.
- The app still uses the existing mobile backend contract unchanged.
- `Capture`, `Feed`, and `Library` remain the top-level structure.
- The UI has no horizontal overflow or container bleed on supported viewports.
- Mobile auth, feed loading, capture submission, reply flow, and library refresh still work after the adaptation.
