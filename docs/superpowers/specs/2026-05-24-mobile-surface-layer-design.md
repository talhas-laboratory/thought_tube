# Mobile Surface Layer Design

Date: 2026-05-24

## Goal
Build a separate private mobile-first PWA surface alongside the existing Inner
World miniapp, deployed on its own `talhaslaboratory.xyz` subdomain, optimized
for effortless thought capture, a highly relevant personal feed, and a clean
return path into saved material and prior conversations.

## Product Shape
The surface is a three-tab app:

1. `Capture`
2. `Feed`
3. `Library`

This is not a general chatbot, a dashboard, or a graph lab. The surface should
feel like a calm personal mobile environment where the fastest action is to
capture a thought, the default return surface is a personalized feed, and the
history surface stays organized enough to revisit useful material quickly.

## Core Principle
Use a separate frontend surface and subdomain, but reuse the existing Inner
World runtime and data model wherever the current system already has the right
owner.

That means:
- keep thought generation, feed shaping, thread context, and provenance inside
  the existing Conversation OS owners
- add a new mobile surface owner and API namespace instead of stretching the
  current miniapp directly
- keep the v1 data path append-first and evidence-bound

## Recommended Architecture

### Surface ownership
Add a new surface family for the mobile app rather than treating it as a minor
variant of `miniapp.py`.

Recommended owners:
- `src/conversation_os/mobile_surface.py`
  - mobile-surface HTTP handler
  - mobile-surface route wiring
  - static asset serving for the new app
- `src/conversation_os/mobile_surface_api.py`
  - `/api/mobile/*` JSON handlers
  - surface-specific request/response shaping
- `product/mobile_surface_v1/`
  - frontend assets for the new PWA

The current Inner World miniapp remains intact and continues to own its
existing routes and UI bundle.

### API namespace
Use a dedicated namespace:
- `/api/mobile/capture`
- `/api/mobile/feed`
- `/api/mobile/feed/<item_id>`
- `/api/mobile/library`
- `/api/mobile/conversations`
- `/api/mobile/conversation/<thread_id>`
- `/api/mobile/thought/<thought_id>/chat`
- `/api/mobile/session`

This keeps the new surface explicit and prevents accidental coupling with the
current miniapp API contracts.

## Tab Design

### 1. Capture
Purpose:
Make it effortless to drop a thought into the system from a phone.

Behavior:
- open directly to a single high-priority input surface
- submit without forcing a chat flow
- offer `Continue conversation` only after successful capture
- show the newest resulting artifact or conversation option without blocking the
  capture action itself

V1 contract:
- capture writes an append-only event or session turn first
- any derived thought packet, feed candidate, or library artifact is created by
  existing downstream owners after the write

Why:
The repo already treats conversations and session events as canonical source.
The mobile surface should preserve that discipline rather than inventing a
parallel raw-thought store.

### 2. Feed
Purpose:
Show the most relevant thing the user's own knowledge base can say back right
now.

Behavior:
- personalized internal-only feed in v1
- compact cards with enough context to decide whether to open, save, dismiss,
  or revisit later
- article/detail expansion and scoped follow-up entry points where useful

V1 ranking inputs:
- explicit `relevant`, `dismiss`, and `revisit_later` feedback
- saved threads
- recent captures
- existing thought packets
- existing evidence and confidence metadata
- recency and diversity balancing

Out of v1:
- live web ingestion
- external news or search ranking
- broad public-social mechanics

### 3. Library
Purpose:
Provide a stable return surface for prior useful material.

Behavior:
Split the library into three clear buckets:
- captured thoughts
- conversations
- saved or relevant feed items

Why:
Without explicit buckets, the library becomes a flat archive and loses the
return behavior the product needs.

## Auth And Privacy
The v1 surface is private single-user software.

Required rule:
- no anonymous access to capture, feed, library, or conversation endpoints

Recommended implementation order:
1. prefer existing home-server or reverse-proxy auth if one already protects the
   Inner World environment cleanly
2. otherwise add a minimal app-level session gate for this surface
3. optionally front it later with Cloudflare Access if the operator model wants
   edge identity instead of only origin-side gating

The auth choice must be explicit before deployment. This is not optional
polish.

## Data Contracts

### Capture write path
On submit:
1. create or attach to a live mobile session
2. append the captured text as canonical source material
3. return a small acknowledgment payload with:
   - `capture_id`
   - `session_id`
   - `created_at`
   - `continue_conversation_available`
   - optional linked `thought_id` or `thread_id` if immediately available

The capture endpoint should not depend on the full feed pipeline completing
before it responds.

### Feed read path
The feed endpoint should assemble a mobile-specific surface payload using
existing thought and ranking owners where possible.

Each feed item should include:
- stable item id
- title or lead
- compact summary
- evidence status
- confidence
- source or domain label
- primary action hint
- saved state
- feedback state if known

### Library read path
The library endpoint should return grouped sections:
- `captures`
- `conversations`
- `saved_items`

Each section should be independently paginable later, but v1 can start with
simple bounded lists.

## Frontend Direction
This should be a mobile-first PWA, not a desktop dashboard shrunk onto a phone.

V1 expectations:
- installable manifest
- serviceable standalone shell
- responsive small-screen layout
- one-thumb-friendly primary actions
- fast load from a server-hosted static bundle

V1 does not require:
- full offline write sync
- offline-first feed materialization
- tablet/desktop-optimized secondary workflows

## Deployment Model
Deploy the new surface as a separate live-served frontend bundle on the home
server, with its own subdomain under `talhaslaboratory.xyz`.

Recommended shape:
1. build frontend assets into a dedicated product directory
2. serve those assets from the repo's runtime on the home server
3. route the new subdomain to the new mobile surface handler
4. keep Cloudflare DNS/proxy configuration separate from the current miniapp
   route

Required deployment work:
- subdomain selection
- origin service mapping on the home server
- TLS and DNS through Cloudflare
- rollback path to disable only the new surface without touching the existing
  app

## Non-Goals
- replacing the existing Inner World miniapp
- building a general home screen chatbot
- exposing raw graph or substrate internals as the main mobile surface
- broad external ingestion in v1
- multi-user collaboration
- public feed behavior

## Success Condition
The mobile surface is successful when:
- a thought can be captured from the phone in one short action
- the user can optionally continue into conversation without chat being the
  default requirement
- the home feed feels meaningfully personalized from internal data only
- saved material and prior conversations are easy to revisit
- the surface is privately accessible on its own subdomain without affecting the
  current miniapp
