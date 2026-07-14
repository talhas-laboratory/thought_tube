# Mobile Surface Redesign Design

## Goal

Redesign the Inner World mobile surface as a new React-based PWA frontend that keeps the current backend and `/api/mobile/*` contract, but replaces the existing UI with a tighter, more app-like experience:

- almost no non-functional copy
- `Capture` that starts as a blank ChatGPT-like conversation surface
- `Feed` that feels Twitter-like and content-first
- `Library` as a quiet archive tab
- equal-weight floating bottom tab bar
- medium liquid-glass chrome with smooth springy, slightly jumpy interactions

## Scope

This design changes the mobile frontend only.

In scope:

- new React frontend stack for the mobile surface
- new app shell, screen layout, component structure, motion, and styling
- same mobile auth flow and same `/api/mobile/*` endpoints
- same deployment target and subdomain

Out of scope:

- changing how feed posts are generated
- changing ranking logic or personalization logic
- changing backend data models
- changing the existing desktop miniapp surface

## Product Shape

The mobile PWA has three tabs:

- `Capture`
- `Feed`
- `Library`

`Capture` is the default tab.

The app should feel like a native mobile product, not a web document. Chrome should be light, visual hierarchy should be clear, and the screen should privilege content and action over explanation.

## Architecture

### Frontend

Build a new React-based frontend bundle for the mobile surface.

Recommended stack direction:

- React
- Vite for bundling
- a lightweight animation layer with spring support
- CSS or a tightly-scoped styling solution that preserves design control

The frontend should replace the current vanilla mobile shell, not sit beside it as an alternate experience.

### Backend

Keep the existing backend endpoints and behavior:

- `POST /api/mobile/session`
- `POST /api/mobile/session/logout`
- `GET /api/mobile/feed`
- `GET /api/mobile/library`
- `POST /api/mobile/capture`
- `POST /api/mobile/conversations/:session_id/reply`
- `POST /api/mobile/feedback`

The frontend adapts to the existing response shapes rather than requiring backend redesign in this phase.

### Deployment

Keep the same deployment model:

- same backend service
- same Cloudflare route
- same `mobile.talhaslaboratory.xyz`

The PWA root, manifest, service worker, and live shell should all resolve to the same canonical root-hosted mobile surface.

## Screen Design

### Capture

`Capture` starts as a blank chat-like composer surface.

Before first message:

- no explanatory paragraphs
- no decorative intro copy
- no dashboard panels
- input is the focal point

After first message:

- the same screen becomes a conversation thread
- messages stack vertically in a ChatGPT-like conversational layout
- assistant replies should feel quiet and concise
- the design should be calmer and more refined than a literal ChatGPT clone

This screen should support:

- first capture
- continued replies
- smooth transition from blank state to live thread

### Feed

The feed should feel closer to Twitter than to a dashboard or a card catalog.

Current post type for this phase:

- tweet-style
- no title
- body text only by default

What should be removed from the default post:

- tags
- source chips
- post-format labels
- thread counts
- metadata banners
- system explanations

Interaction:

- tapping a post expands it inline on the same screen
- expansion reveals more of the content itself, not metadata
- the expanded state can expose deeper body text and minimal secondary actions

The feed should read as a stream of posts, not as a set of system objects.

### Library

`Library` is the archive tab.

It should include:

- past conversations
- saved/relevant surfaced items

It should be simpler and quieter than the feed, but still use the same visual system.

The goal is utility and return, not density.

## Navigation

Remove the top tab strip.

Use a floating bottom tab bar:

- `Capture`
- `Feed`
- `Library`

All three tabs should have equal weight.

Do not make `Capture` oversized or center-dominant.

The bar should feel like app chrome rather than a footer:

- translucent
- softly layered
- elevated from the background
- touch-friendly

## Visual Direction

The new surface should feel:

- app-like
- deliberate
- minimal
- fast
- content-first

It should not feel:

- verbose
- dashboard-like
- card-heavy in an enterprise sense
- academically explained

### Liquid Glass Translation

Use a medium-strength liquid-glass treatment translated from iOS idioms into web/PWA form.

Apply glass primarily to:

- bottom tab bar
- input surfaces
- overlays and sheets
- selected navigation or control chrome

Do not make the feed posts themselves heavily glassy.

Posts should remain mostly solid for readability.

The result should feel iOS-inspired, not like a novelty effect.

## Motion

Motion should feel smooth, springy, and slightly jumpy in a tactile iOS sense.

Desired feel:

- quick lift
- soft settle
- slight rebound

Apply this to:

- bottom tab selection
- feed post expansion
- blank capture becoming a thread
- reply composer reveal
- lightweight save/relevant interactions

Avoid:

- busy animation
- long floaty transitions
- animating large text blocks in distracting ways

Animate containers, opacity, scale, and position rather than making text reflow feel unstable.

## Copy Discipline

Remove almost all non-functional copy.

Keep only copy that is necessary to:

- label an action
- avoid ambiguity
- orient the user in a minimal way

Do not include framing copy like:

- product manifestos
- metaphor-heavy intros
- “reading room” or “private stream” language
- extra descriptive panels above the main interaction

## Feed Content Rules

In this phase, the feed supports multiple future post types conceptually, but only one rendered post type is active:

- tweet-style body-only posts

The architecture should leave room for additional post formats later, but the initial UI should not expose that complexity.

The feed should look like a coherent stream even if the backend still provides richer metadata internally.

## Responsive and Viewport Rules

No horizontal overflow anywhere.

This is a hard requirement, not polish.

Rules:

- every primary container must remain inside the viewport
- bottom bar must remain fully bounded on narrow screens
- all flex and grid children that need to shrink must have `min-width: 0`
- long text must wrap safely
- overlays and sheets must use bounded width and height
- expanded feed content must not push layout sideways
- the app must remain usable across narrow mobile widths and larger desktop preview widths

## Interaction Summary

- App opens to `Capture`
- `Capture` begins blank
- First user message creates the thread
- `Feed` shows a Twitter-like stream of body-only posts
- Tapping a post expands more content inline
- `Library` provides saved/relevant items and past conversations
- Bottom floating tab bar is the persistent app switcher

## Technical Constraints

- keep backend contract unchanged
- keep auth model unchanged
- keep deployment target unchanged
- rebuild frontend instead of layering hacks on top of the current shell

## Success Criteria

The redesign is successful if:

- the mobile surface no longer feels like the current verbose card-based design
- `Capture` feels like a clean blank-to-thread conversation surface
- `Feed` feels like a Twitter-like content stream
- default posts show content only, without system clutter
- the bottom floating tab bar feels native and balanced
- liquid-glass treatment improves chrome without hurting readability
- motion feels smooth and slightly elastic
- the app has no horizontal overbleed on supported viewports
- the existing backend and deployment continue to work unchanged
