# social_feed_UI Integration Plan

Purpose:
Swap [`social_feed_UI`](https://github.com/talhas-laboratory/social_feed_UI) in as the replacement frontend for the current Inner World social feed backend, while preserving the current Python API contract.

Related docs:
- [UI swap sheet](/Users/talhauddin/software/inner_space/docs/plans/2026-04-30-social-feed-ui-swap-sheet.md)
- [social feed implementation spec](/Users/talhauddin/software/inner_space/docs/plans/2026-04-30-social-feed-layer-implementation-spec.md)

## Summary

This is a good fit.

The repo already matches the core integration pattern we want:
- React frontend
- direct fetch calls to `window.INNER_WORLD_CONFIG.apiBaseUrl`
- feed-first surface
- `/feed`, `/thought/:id`, `/feedback`, and `/thought/:id/chat` already modeled

The swap is not zero-work. The main gap is not backend compatibility. The main gap is product and runtime cleanup:
- remove AI Studio / Gemini server assumptions
- remove fake composer behavior
- either disable or reinterpret `organize` mode
- consume more of the backend’s structured fields
- serve built static assets from the current Inner World backend

My recommendation:
- keep `social_feed_UI` as the frontend source repo
- adapt it there
- build a static `dist/`
- mount that built output in `inner_space`

## Fit Assessment

### Already aligned

Frontend repo:
- [/tmp/social_feed_UI/src/lib/api.ts](/tmp/social_feed_UI/src/lib/api.ts)
- [/tmp/social_feed_UI/src/lib/mockAPI.ts](/tmp/social_feed_UI/src/lib/mockAPI.ts)
- [/tmp/social_feed_UI/src/App.tsx](/tmp/social_feed_UI/src/App.tsx)

Good signs:
- already reads `window.INNER_WORLD_CONFIG.apiBaseUrl`
- already uses the correct endpoint pattern
- already models `preview_payload` and `expand_payload`
- already has a feed/expand/chat interaction model

### Current mismatches

1. It includes its own runtime server:
- [/tmp/social_feed_UI/server.ts](/tmp/social_feed_UI/server.ts)

We do not want:
- Gemini dependence
- separate Express server
- extra `/api/cognition` endpoint

2. The composer is fake
- `handleCommit()` clears local state only
- there is no create-post backend endpoint in `inner_space`

3. `organize` mode is not a real backend mode
- current backend only exposes one scoped thought chat endpoint
- there is no separate organizer agent endpoint

4. It underuses backend-specific context fields
- `post_context`
- `taste_diagnostics`
- thread save/delete lifecycle
- runtime overview

## Recommended Architecture

### Source of truth

Keep:
- `social_feed_UI` as the maintained frontend source repo

Keep:
- `inner_space` as the only backend and only served API

Do not keep:
- `social_feed_UI/server.ts` in the final runtime path

### Final runtime

Target runtime shape:

1. build `social_feed_UI` with `vite build`
2. serve the built `dist/` from the current Inner World miniapp server
3. generate `runtime-config.js` exactly like the current miniapp path does
4. point the UI to:
   - `/api/feed`
   - `/api/thought/:thought_id`
   - `/api/feedback`
   - `/api/thought/:thought_id/chat`
   - `/api/thread/:thread_id`
   - `/api/thread/:thread_id/save`
   - `/api/thread/:thread_id/delete`
   - `/api/runtime-overview`

## File-by-File Plan

## 1. Frontend repo: `social_feed_UI`

### `src/lib/api.ts`

Status:
- mostly correct already

Keep:
- `getApiBaseUrl()`
- `fetchFeed()`
- `fetchThoughtDetail()`
- `sendFeedback()`
- `chatWithThought()`

Change:
1. add:
   - `fetchRuntimeOverview()`
   - `fetchThreadDetail(threadId)`
   - `saveThread(threadId)`
   - `deleteThread(threadId)`

2. tighten response assumptions around:
   - `feed_post`
   - `post_context`
   - `taste_diagnostics`
   - `active_thread`

3. keep mock mode for standalone dev, but expand mocks to match the real backend better

### `src/lib/mockAPI.ts`

Status:
- good starting point

Change:
1. add realistic:
   - `post_context`
   - `taste_diagnostics`
   - `thread_count`
   - `saved_thread_count`
   - `feedback_controls`

2. add mock detail responses that include:
   - `source_snippets`
   - `active_thread`
   - `threads`
   - `feed_post`

Reason:
- replacement UI should be testable without the backend and still resemble the real contract

### `src/App.tsx`

Status:
- this is the main adaptation surface

Keep:
- feed-first layout
- expand/collapse behavior
- discuss thread concept
- markdown deep-read rendering

Change:
1. remove fake composer semantics
   - either remove the composer entirely for slice 1
   - or relabel it as a local scratch surface if you explicitly want that

My recommendation:
- remove or hard-disable it in the swap version

2. reinterpret `organize`
   - current backend has no dedicated organizer endpoint

Options:
- recommended: map `organize` to a different UI framing on the same `/thought/:id/chat` endpoint
- simpler: remove `organize` button for first swap

3. consume backend fields more directly:
   - collapsed cards should use:
     - `preview_payload.title`
     - `preview_payload.lead_text`
     - `preview_payload.cta_label`
     - `post_format`
     - `evidence_status`
   - expanded cards should use:
     - `expand_payload.opening_text`
     - `expand_payload.what_changed`
     - `expand_payload.why_it_matters_now`
     - `expand_payload.next_action`
     - `expand_payload.recommended_interaction`
   - side/context areas should use:
     - `post_context.context_summary`
     - `post_context.source_snippets`
     - `post_context.tensions`
     - `post_context.contradictions`
     - `post_context.unresolved_questions`
   - optional diagnostics shelf should use:
     - `taste_diagnostics.lead_rule`
     - `taste_diagnostics.interaction_rule`
     - `taste_diagnostics.compactness_rule`

4. support saved thread lifecycle
   - add save action for active thread
   - optionally add delete action for threads

5. use `active_thread` correctly
   - if present, render it first
   - otherwise fall back to first thread

6. make feedback button set exactly:
   - `relevant`
   - `revisit_later`
   - `dismiss`

7. optionally add a runtime/debug panel driven by `/api/runtime-overview`
   - keep this optional and secondary

### `src/main.tsx`

Status:
- fine as is

Likely no change needed.

### `src/index.css`

Status:
- visually coherent

Change:
- only if needed for backend-specific UI elements:
  - context shelf
  - taste diagnostics shelf
  - saved thread controls

### `vite.config.ts`

Status:
- mostly fine

Change:
1. remove unused Gemini define once `server.ts` is gone:
   - `process.env.GEMINI_API_KEY`

2. optionally set build output conventions if needed for embedding

Likely:
- no major structural change required

### `server.ts`

Status:
- should not be part of the final swap runtime

Action:
- remove from final integration path
- keep only if you want a separate local frontend-dev mode for that repo

My recommendation:
- keep it only as temporary standalone dev tooling
- do not ship it in the actual swap

### `package.json`

Change:
1. keep:
   - `build`
   - `preview`
   - `lint`

2. revise:
   - `dev`
   - `start`

Recommended:
- `dev`: `vite`
- remove runtime dependence on `tsx server.ts`

Reason:
- the final deployed runtime should be the existing Python server, not Express

## 2. Backend repo: `inner_space`

### `src/conversation_os/miniapp.py`

Current role:
- serves the API
- serves static frontend assets

Change for final swap:
1. add support for serving a replacement built frontend directory
2. point `serve_miniapp(..., static_dir=...)` at the built `social_feed_UI/dist`
3. continue generating:
   - `runtime-config.js`

Do not change:
- endpoint semantics
- `/feed`
- `/thought/:id`
- `/feedback`
- thread routes

### `tools/build_inner_world_openclaw_miniapp.py`

Current role:
- builds bundle for OpenClaw

Change for final swap:
1. switch bundle source from current miniapp assets to the built `social_feed_UI/dist`
2. still inject:
   - `runtime-config.js`
3. still emit:
   - `app.json`
   - `README.md`

### `src/conversation_os/openclaw_miniapp.py`

Only change if needed.

If bundle source path becomes configurable, this module may need a small extension.

### Current enhancement layer in `miniapp.py`

Important note:
- we recently added an injected enhancement layer for the current miniapp shell

If `social_feed_UI` becomes the real replacement:
- that enhancement layer should be removed or bypassed for the replacement UI path
- it was useful as a bridge, not as the long-term frontend architecture

## Integration Modes

## Mode A: quickest integration

Use case:
- fastest way to test the new UI against the backend

Steps:
1. adapt `social_feed_UI`
2. run `vite build`
3. serve its `dist/` from `inner_space` via `static_dir`
4. verify API contract live

Pros:
- fast
- minimal backend changes

Cons:
- bundle/build tooling still needs one more integration pass

## Mode B: full replacement

Use case:
- final production path

Steps:
1. adapt `social_feed_UI`
2. build `dist/`
3. teach:
   - `miniapp.py`
   - `build_inner_world_openclaw_miniapp.py`
   to use the replacement `dist/`
4. remove old enhancement layer from the primary path

Pros:
- cleanest final architecture
- no duplicate UI layers

Cons:
- slightly more swap wiring

Recommendation:
- do Mode A first
- then finalize with Mode B

## Minimum Adaptation Checklist

Before wiring the swap, the frontend repo should do these:

1. remove or disable fake composer
2. remove or reinterpret organizer mode
3. add thread save/delete API calls
4. render `post_context`
5. render `taste_diagnostics`
6. ensure all API calls use `window.INNER_WORLD_CONFIG.apiBaseUrl`
7. ensure `vite build` emits a static-only app with no Express dependency

## Verification Plan

### Frontend repo verification

In `social_feed_UI`:
1. `npm install`
2. `npm run lint`
3. `npm run build`

### Swap verification in `inner_space`

1. mount built `dist/`
2. load local miniapp
3. verify:
   - feed loads
   - expand works
   - detail fetch works
   - feedback works
   - chat works
   - save thread works
   - delete thread works
   - no Gemini/Express server path is required

## My Recommendation

Best next step:

1. adapt `social_feed_UI` first
2. do not touch the backend contract
3. once the UI repo is ready, integrate its built output into `inner_space`

This keeps the swap disciplined:
- frontend changes in the frontend repo
- serving and bundle changes in `inner_space`

## Handoff

Once you want the actual swap implementation, the handoff inputs should be:

1. the prepared `social_feed_UI` repo state
2. the built `dist/` or the commit to build from
3. this integration plan
4. the [UI swap sheet](/Users/talhauddin/software/inner_space/docs/plans/2026-04-30-social-feed-ui-swap-sheet.md)
