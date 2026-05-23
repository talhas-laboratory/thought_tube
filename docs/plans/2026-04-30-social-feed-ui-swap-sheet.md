# Social Feed UI Swap Sheet

Purpose:
This is the frontend handoff sheet for swapping the current Inner World miniapp UI with a replacement social-feed UI, while keeping the current backend and API contract unchanged.

## Recommended Swap Strategy

Build your replacement UI as a static frontend that talks directly to the existing API.

Do:
- treat the backend as the source of truth
- consume `preview_payload`, `expand_payload`, `post_context`, and `taste_diagnostics`
- assume `/api/feed` gives you enough data to render the primary timeline
- call `/api/thought/:thought_id` only when you need richer detail or thread state

Do not:
- depend on the current `product/inner_world_v1/miniapp/app.js`
- infer fields from UI text when structured fields already exist
- assume hidden pagination, cursoring, or offset support

## Base URLs

Local served miniapp:
- UI: `http://127.0.0.1:8421/`
- API prefix: `http://127.0.0.1:8421/api`

OpenClaw bundle:
- API base is injected into `runtime-config.js`
- frontend should read `window.INNER_WORLD_CONFIG.apiBaseUrl`

## Primary Endpoints

### `GET /api/feed`

Purpose:
Primary timeline surface.

Response shape:

```json
{
  "generated_at": "2026-04-30T00:00:00+00:00",
  "count": 12,
  "thoughts": [FeedThought],
  "diagnostics": {
    "selection": {
      "candidate_pool_count": 48,
      "selected_count": 12,
      "unique_primary_source_count": 9,
      "unique_primary_bubble_count": 7,
      "selected_thought_ids": ["..."],
      "applied_preferred_formats": ["source_backed_card"],
      "taste_adjusted_thought_ids": ["..."]
    },
    "formats": {
      "counts": {
        "sharp_post": 3,
        "discussion_prompt": 2,
        "mini_essay": 4,
        "source_backed_card": 3
      }
    },
    "taste_profile": {
      "event_count": 4,
      "signal_counts": {
        "detail_open": 1,
        "thought_chat": 2,
        "thread_saved": 1,
        "explicit_feedback": 1
      },
      "format_counts": {},
      "format_scores": {},
      "preferred_formats": ["source_backed_card"]
    },
    "taste_posts": {
      "thought-id": {
        "preferred_format": "source_backed_card",
        "post_format": "source_backed_card",
        "format_preference_match": true,
        "lead_rule": "preferred_format_evidence",
        "interaction_rule": "thought_chat_dominant",
        "compactness_rule": "depth_from_chat_and_save",
        "signal_counts": {
          "detail_open": 0,
          "thought_chat": 2,
          "thread_saved": 1,
          "explicit_feedback": 1
        }
      }
    }
  }
}
```

Use in UI:
- render the timeline from `thoughts`
- use `diagnostics` only for optional debug/dev surfaces unless you explicitly want them visible

### `GET /api/thought/:thought_id`

Purpose:
Expanded post detail, article continuity, source snippets, and thread state.

Response shape:

```json
{
  "thought": ThoughtCore,
  "feed_post": FeedPost,
  "primitive": {
    "label": "Pattern",
    "plugin_id": "thought_pipeline"
  },
  "source_snippets": [SourceSnippet],
  "threads": [Thread],
  "active_thread": Thread | null
}
```

Use in UI:
- treat `feed_post` as the expansion companion to the feed row
- use `thought.article_markdown` for deep read
- use `threads` and `active_thread` to show conversation state

### `POST /api/feedback`

Request:

```json
{
  "insight_id": "insight-123",
  "feedback_state": "relevant"
}
```

Response:

```json
{
  "insight_id": "insight-123",
  "feedback_state": "relevant",
  "policy_snapshot": {},
  "taste_profile": {}
}
```

Allowed current feedback states:
- `relevant`
- `revisit_later`
- `dismiss`

Backend note:
- the handler regenerates the daily batch after feedback is recorded

### `POST /api/thought/:thought_id/chat`

Request:

```json
{
  "message": "Push this further.",
  "thread_id": "thread-optional"
}
```

Response:

```json
{
  "thread": Thread,
  "assistant_message": Message,
  "thought": ThoughtCore,
  "context": ThreadContext
}
```

Use in UI:
- start a new scoped thread when `thread_id` is omitted
- continue a saved/draft thread when `thread_id` is present

### `GET /api/thread/:thread_id`

Response:

```json
{
  "thread_id": "thread-123",
  "thought_id": "thought-123",
  "title": "Thought title",
  "status": "draft",
  "created_at": "...",
  "updated_at": "...",
  "character": "...",
  "system_prompt": "...",
  "context_summary": "...",
  "source_refs": ["..."],
  "reasoning_primitive": "thought_pipeline",
  "backend_id": "heuristic",
  "messages": [Message],
  "embedded_source_item_ids": []
}
```

### `POST /api/thread/:thread_id/save`

Response:

```json
{
  "thread_id": "thread-123",
  "status": "saved",
  "embedded_source_item_ids": ["source-item-1"]
}
```

### `POST /api/thread/:thread_id/delete`

Response:

```json
{
  "thread_id": "thread-123",
  "status": "deleted"
}
```

### `GET /api/runtime-overview`

Purpose:
Optional system/status surface.

Use in UI:
- optional top-level debug/status shelf
- not required for the replacement feed itself

## Core Feed Objects

### `FeedThought`

This is the main row in `GET /api/feed`.

Important fields:

```json
{
  "thought_id": "thought-123",
  "insight_id": "insight-123",
  "title": "Title",
  "short_text": "Short copy",
  "article_markdown": "## ...",
  "confidence_score": 0.91,
  "relevance_score": 0.82,
  "novelty_score": 0.74,
  "evidence_status": "supported",
  "feedback_state": "pending",
  "feedback_controls": ["relevant", "dismiss", "revisit_later"],
  "source_refs": ["source://..."],
  "source_item_ids": ["source-item-1"],
  "what_changed": "...",
  "why_it_matters_now": "...",
  "next_action": "...",
  "reasoning_primitive": "Pattern",
  "thread_count": 1,
  "saved_thread_count": 0,
  "post_id": "thought-123",
  "post_format": "source_backed_card",
  "format_reason": "grounded_evidence",
  "reach_mode": "strict",
  "preview_payload": {},
  "expand_payload": {},
  "deep_read_ref": {},
  "post_context": {},
  "taste_shape": {},
  "taste_diagnostics": {}
}
```

### `preview_payload`

Use for collapsed card rendering.

Fields:

```json
{
  "kind": "preview",
  "format": "source_backed_card",
  "title": "Title",
  "short_text": "Compact summary",
  "why_it_matters_now": "...",
  "lead_mode": "evidence",
  "lead_text": "Lead sentence/snippet",
  "cta_label": "Discuss evidence",
  "taste_shape": {
    "preferred_format": "source_backed_card",
    "lead_mode": "evidence",
    "interaction_bias": "thought_chat",
    "compactness": "depth"
  }
}
```

### `expand_payload`

Use for inline expanded state before full article focus.

Fields:

```json
{
  "kind": "expand",
  "format": "source_backed_card",
  "thought_id": "thought-123",
  "title": "Expanded title",
  "subtitle": "Short copy",
  "what_changed": "...",
  "why_it_matters_now": "...",
  "next_action": "...",
  "article_sections": [
    {"heading": "One", "body": "..."}
  ],
  "source_snippets": [SourceSnippet],
  "supporting_meta": [SupportingMeta],
  "opening_focus": "evidence",
  "opening_text": "Opening paragraph/snippet",
  "recommended_interaction": "thought_chat",
  "taste_shape": {
    "preferred_format": "source_backed_card",
    "lead_mode": "evidence",
    "interaction_bias": "thought_chat",
    "compactness": "depth"
  }
}
```

### `post_context`

Bounded, packet-scoped context.

Fields:

```json
{
  "thought_id": "thought-123",
  "reach_mode": "strict",
  "context_summary": "...",
  "primary_bubble_id": "bubble-123",
  "primary_bubble_label": "Bubble label",
  "related_bubble_ids": ["bubble-456"],
  "source_snippets": [SourceSnippet],
  "supporting_meta": [SupportingMeta],
  "tensions": ["..."],
  "contradictions": ["..."],
  "unresolved_questions": ["..."]
}
```

### `taste_diagnostics`

Explain why the post is currently being shaped this way.

Fields:

```json
{
  "preferred_format": "source_backed_card",
  "post_format": "source_backed_card",
  "format_preference_match": true,
  "lead_rule": "preferred_format_evidence",
  "interaction_rule": "thought_chat_dominant",
  "compactness_rule": "depth_from_chat_and_save",
  "signal_counts": {
    "detail_open": 0,
    "thought_chat": 2,
    "thread_saved": 1,
    "explicit_feedback": 1
  }
}
```

## Supporting Objects

### `SourceSnippet`

```json
{
  "source_item_id": "source-item-1",
  "title": "Source title",
  "source_type": "note",
  "source_ref": "source://ref",
  "excerpt": "Short excerpt"
}
```

Note:
- in `post_context.source_snippets`, current rows come from the thread packet and may omit `source_type`
- in `GET /api/thought/:id`, `source_snippets` include `source_type`

### `SupportingMeta`

```json
{
  "meta_id": "meta-1",
  "kind": "tension",
  "label": "Competing force",
  "summary": "Short explanation"
}
```

### `Message`

```json
{
  "message_id": "message-1",
  "role": "user",
  "content": "Message text",
  "created_at": "2026-04-30T00:00:00+00:00"
}
```

## Suggested Frontend State Model

Minimum useful client state:

```ts
type FeedState = {
  feed: FeedThought[]
  activeThoughtId: string | null
  thoughtDetails: Record<string, ThoughtDetail>
  detailErrors: Record<string, string | null>
  loadingThoughtId: string | null
  activeThreadByThoughtId: Record<string, string | null>
}
```

Recommended rendering flow:

1. fetch `/api/feed`
2. render `thoughts[]` from `preview_payload`
3. on expand:
   - use feed row immediately for instant expansion shell
   - fetch `/api/thought/:thought_id`
   - merge in article/thread/source detail
4. on feedback:
   - `POST /api/feedback`
   - refresh `/api/feed`
5. on chat:
   - `POST /api/thought/:thought_id/chat`
   - persist returned `thread.thread_id`

## Stable Assumptions You Can Build Against

Safe assumptions:
- `post_id === thought_id`
- `deep_read_ref.surface === "thought_detail"`
- `reach_mode` currently defaults to `strict`
- `feedback_controls` currently include `relevant`, `dismiss`, and `revisit_later`
- `thought.article_markdown` is the deep-read source of truth

Do not assume:
- paginated feed support
- cursor support
- hidden write endpoints beyond the ones listed here
- stable presence of optional diagnostics fields if the backend is run in degraded/empty mode

## Swap Checklist

When your replacement UI is ready, the easiest swap is:

1. provide:
   - `index.html`
   - `app.js`
   - `styles.css`
   - any local assets
2. point your frontend to:
   - `window.INNER_WORLD_CONFIG.apiBaseUrl`
3. keep your UI independent from the current miniapp script
4. hand me the UI bundle
5. I will mount it into the served miniapp and OpenClaw bundle path

## Current Owner Surfaces

Relevant server and bundle owners:
- [miniapp.py](/Users/talhauddin/software/inner_space/src/conversation_os/miniapp.py)
- [product_inner_world.py](/Users/talhauddin/software/inner_space/src/conversation_os/product_inner_world.py)
- [build_inner_world_openclaw_miniapp.py](/Users/talhauddin/software/inner_space/tools/build_inner_world_openclaw_miniapp.py)

Current living product spec:
- [social feed implementation spec](/Users/talhauddin/software/inner_space/docs/plans/2026-04-30-social-feed-layer-implementation-spec.md)
