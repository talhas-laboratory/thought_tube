# Inner World Social Feed Layer Implementation Spec

Date: 2026-04-30
Status: living spec
Owner: Inner World v1

## Purpose

Design and implement a private, interest-driven social feed layer for Inner World.

The feed should turn the existing knowledge ocean into engaging written content tailored to the user. It should feel social in pacing, presentation, and feedback, but it should not become a public social network. The "creators" in this feed are context bubbles, knowledge edges, tensions, source fragments, saved threads, and past conversations.

## Product Sentence

Inner World Social Feed is a private synthesis feed where the user's own knowledge ocean writes back to them as sharp posts, discussion prompts, mini-essays, source-backed cards, and threads.

## Current Repo Baseline

The repo already has the core substrate:

- `src/conversation_os/thought_factory.py`
  - `ThoughtPacket` creation
  - `build_feed_rows()`
  - `build_archive_rows()`
  - semantic thought assist hooks
- `src/conversation_os/product_inner_world.py`
  - `generate_daily_batch()`
  - `build_thought_feed()`
  - `record_feedback()`
  - thought detail, thread chat, save/delete thread flows
- `src/conversation_os/context_bubbles.py`
  - interest and topic cluster materialization
- `src/conversation_os/knowledge_layer.py`
  - knowledge nodes, knowledge edges, semantic capsules, context links
- `src/conversation_os/long_form.py`
  - configurable article assembly profiles
- `src/conversation_os/miniapp.py`
  - `/feed`
  - `/archive`
  - `/thought/{id}`
  - `/feedback`
  - thought chat and thread endpoints
- `product/inner_world_v1/miniapp/`
  - current frontend surface

Current local product state observed during discussion:

- `source_registry.jsonl`: 1,439 sources
- `chunk_index.jsonl`: 82,910 chunks
- `analysis_units.jsonl`: 12,885 units
- `context_bubbles.jsonl`: 3,715 bubbles
- `knowledge_nodes.jsonl`: 110,385 nodes
- `knowledge_edges.jsonl`: 962,938 edges
- `thought_packets.jsonl`: 3 packets

## Repo Scan Findings

The repo scan did not reveal a contradiction to the current design direction, but it did change the implementation outlook in useful ways.

### 1. A bounded context packet already exists in miniature

Relevant files:

- `src/conversation_os/thread_context.py`
- `src/conversation_os/product_inner_world.py`

Key finding:

- `build_thread_packet()` already constructs a bounded packet for thought chat:
  - source snippets
  - linked meta
  - tensions
  - contradictions
  - why-it-matters frames
  - unresolved questions
  - bounded system prompt
- `build_thought_context()` already delegates directly to that packet builder.

Implementation consequence:

- `FeedContextPacket` should likely generalize `build_thread_packet()` rather than invent a second scoped retrieval abstraction from scratch.

### 2. Bubble provenance packets are already implemented

Relevant files:

- `src/conversation_os/context_bubbles.py`
- `src/conversation_os/product_inner_world.py`
- `docs/plans/2026-04-21-concept-provenance-filtering-design.md`
- `tests/test_conversation_os.py`

Key finding:

- bubble detail already exposes provenance grouped by source with chunk excerpts and related concepts
- tests already verify bubble provenance visibility

Implementation consequence:

- post context packets should reuse bubble provenance paths for inspectability and evidence drill-down
- the feed layer does not need to invent a new provenance surface

### 3. The short-to-long transition is already partially real

Relevant files:

- `src/conversation_os/models.py`
- `src/conversation_os/thought_factory.py`
- `src/conversation_os/product_inner_world.py`
- `product/inner_world_v1/miniapp/app.js`

Key finding:

- `ThoughtPacket` already includes:
  - `short_text`
  - `article_markdown`
  - `article_sections`
  - `article_profile`
  - `article_config_snapshot`
- the current miniapp already supports in-place feed expansion

Implementation consequence:

- the feed layer should wrap and sharpen the current transition model rather than replace it wholesale
- the missing piece is a first-class `expand` artifact and bounded post context, not article generation from zero

### 4. Prior product docs already committed to feed -> article -> thought-chat

Relevant files:

- `docs/plans/2026-04-14-inner-world-v1-ui-plan.md`
- `docs/plans/2026-04-14-inner-world-v1-build-plan.md`
- `docs/plans/2026-04-14-inner-world-thought-tube-overhaul-plan.md`

Key finding:

- the intended user-facing flow was already:
  - feed
  - article expansion
  - thought-native chat
- thought chat was already supposed to run from a formal context packet
- scoped context rather than full-archive spillover was already a product requirement

Implementation consequence:

- the social feed layer is an architectural clarification and upgrade, not a change in product direction

### 5. Attention budget and diversity rules were already identified as product requirements

Relevant files:

- `docs/plans/2026-04-13-inner-world-product-gap-log.md`

Key finding:

- prior product thinking already called for:
  - daily insight budget
  - novelty quota
  - evidence quota
  - recency diversity rules
  - selective rather than chatty delivery

Implementation consequence:

- diversity and fatigue are not optional refinements
- they should be part of the first real feed ranking pass

## Important Corrections To Prior Review

The existing system is strong substrate, but not yet a finished social feed engine.

- `build_feed_rows()` is a simple sorter and title deduper over existing thought packets. It is not yet a production-quality personalized feed algorithm.
- `/feed` returns a limited feed, but it is not cursor/offset paginated.
- `conversation_learning.py` has useful preference heuristics, but it is not a full writer-voice profile extractor.
- `long_form.py` profiles are structural article profiles, not extracted personal voice profiles.
- Feedback exists, but the UI currently exposes narrower controls than the ranking code can understand.
- External RSS/API ingestion should be deferred or explicitly opt-in because the current product thesis is local-first, manually seeded, and not autonomous external research by default.

## Research Synthesis

### X

Useful principles:

- Candidate sourcing matters as much as ranking.
- Feeds combine explicit user actions, implicit engagement, graph/community embeddings, author/source reputation, filtering, and diversity controls.
- Written content performs when it is concise, conversational, specific, and easy to respond to.
- Hooks, clear claims, short paragraphs, and early reply momentum create engagement.

Inner World translation:

- Source candidates from multiple internal surfaces, not only the top-ranked insights.
- Generate sharp, compact post objects with one idea per card.
- Track whether a thought invited action, expansion, correction, or dismissal.

### Reddit

Useful principles:

- Community fit is central.
- Sorting balances recency, votes, comments, and relevance.
- Discussion-heavy content is different from high-vote content.
- Titles frame the conversation and often determine whether a written post works.

Inner World translation:

- Treat context bubbles as private subreddits.
- Each feed item should know which bubble/community it belongs to.
- Add discussion-prompt cards that invite the user to respond, challenge, or refine.
- Rank some items for "discussion potential," not only insight quality.

### Substack

Useful principles:

- Trust and relationship are the core loop.
- Recommendations, restacks, Notes, replies, comments, reading depth, and subscriber growth are stronger signals than quick likes alone.
- Successful written content tends to have a clear topic promise, a consistent voice, and enough substance to reward attention.

Inner World translation:

- The feed should preserve provenance and confidence so trust compounds.
- Short posts should expand into worthwhile mini-essays or articles.
- The system should learn from depth signals: expanded, read, chatted with, saved, converted to task, revisited.

## Core Product Rule

The feed should not ask:

> What content will maximize scrolling?

It should ask:

> What is the most compelling thing the user's own knowledge ocean can say back right now?

## Architecture Decision

The social feed should be implemented as a dedicated layer on top of the existing Inner World substrate, not permanently woven ad hoc into `product_inner_world.py`.

Initial target module boundary:

- `src/conversation_os/social_feed/`
  - `candidates.py`
  - candidate sourcing from bubbles, edges, tensions, sessions, and archive
- `src/conversation_os/social_feed/ranking.py`
  - ranking, diversity, fatigue, and mix policy
- `src/conversation_os/social_feed/context_packets.py`
  - bounded context packet construction per post
- `src/conversation_os/social_feed/formats.py`
  - short-form and expansion format generation
- `src/conversation_os/social_feed/runtime.py`
  - feed assembly, refresh, and orchestration
- `src/conversation_os/social_feed/models.py`
  - social feed object models

The existing Inner World layers remain responsible for:

- source ingestion
- analysis units
- context bubbles
- knowledge nodes and edges
- long-form article assembly
- thought chat backend

The new social feed layer should be responsible for:

- selecting what becomes a post
- deciding which format each post should take
- shaping the transition from short form to expanded form
- enforcing scoped context boundaries per post
- managing feed-specific feedback and ranking behavior

Opinion:

- This should be a wrapper layer first, not a rewrite.
- Keep `generate_daily_batch()` and current thought generation usable during migration.
- The new layer should initially consume existing thought and knowledge artifacts, then gradually replace the final feed assembly path.

### Slice 1 Implementation Boundary

The engineering guard did not approve creating `src/conversation_os/social_feed/` as the first code move. The current repo owners for this behavior are still `src/conversation_os/product_inner_world.py` and the existing thought/thread packet machinery.

So slice 1 is intentionally implemented inside the current owner surface:

- `src/conversation_os/product_inner_world.py`
- `tests/test_conversation_os.py`

This is a temporary implementation boundary, not the final architecture.

Practical consequence:

- The first shipped behavior should appear as a feed-owned wrapper model in the `/feed` output.
- The extraction to a dedicated `social_feed` package should happen only after the wrapper behavior is stable and verified.

### Integration Path

Recommended first integration:

- slice 1:
  - add feed-owned wrapper payloads directly in `product_inner_world.build_thought_feed()`
  - preserve the `/feed` contract and enrich each thought row with social-feed fields
  - reuse existing bounded thread packet logic rather than splitting context retrieval yet
- later extraction:
  - add `src/conversation_os/social_feed/runtime.py`
  - expose `build_social_feed()` as the new top-level feed assembler
  - let `product_inner_world.build_thought_feed()` delegate to `build_social_feed()`
  - keep `generate_daily_batch()` as the upstream batch/candidate producer for now
  - keep `long_form.py` as the article renderer until feed-specific expansion needs diverge enough to justify a split

What not to do:

- do not split candidate generation, article generation, and feedback into parallel isolated systems immediately
- do not duplicate source retrieval logic in both `product_inner_world.py` and `social_feed/`
- do not replace current thought chat with a second unrelated chat path

## Proposed Feed Objects

The existing `ThoughtPacket` should not be forced to carry the entire social feed feature forever.

Proposed feed-specific objects:

- `FeedCandidate`
  - raw candidate before ranking and formatting
- `FeedPost`
  - the displayed social object
- `FeedContextPacket`
  - the bounded knowledge/context bundle attached to a post
- `FeedExpansion`
  - the expanded article or thread view for a post
- `FeedFeedbackEvent`
  - feed-specific feedback with stronger semantics than current generic feedback

`ThoughtPacket` can remain as an upstream artifact for now, but the social feed layer should own the final post model.

### Recommended Model Boundary

Recommended near-term ownership:

- `ThoughtPacket`
  - upstream thought artifact
  - still produced by current thought pipeline
- `FeedPost`
  - feed-facing artifact shown in UI
  - owns short-form, expansion metadata, ranking metadata, and scoped context ref
- `FeedContextPacket`
  - immutable bounded context snapshot for one post generation cycle
- `FeedExpansion`
  - resolved expanded view payload for article/thread/detail mode

Opinion:

- Keep `ThoughtPacket` because it already encodes useful cross-pipeline output.
- Do not overload `ThoughtPacket` with UI-state, reach policy, or feed-specific explainability fields.
- `FeedPost` should reference `ThoughtPacket` by id rather than copying every field forever.

## Feed Design

### Candidate Sources

The social feed layer should generate candidates from:

- active context bubbles
- dormant high-value bubbles
- surprising knowledge edges
- unresolved tensions and contradictions
- open questions
- recent sessions
- saved or expanded thought threads
- source fragments with high evidence value
- adjacent discoveries across ponds
- resurfaced archive material

### Feed Mix Targets

Initial feed composition target:

- 40% core interests
- 25% adjacent discoveries
- 20% unresolved tensions or questions
- 10% resurfaced archive
- 5% wildcards

These should be configuration defaults, not hard-coded product doctrine.

### Ranking Model

Initial ranking should account for:

- interest affinity
- evidence strength
- novelty
- recency
- source diversity
- bubble diversity
- format fit
- user feedback
- discussion potential
- expansion potential
- fatigue/repetition penalty
- low-confidence penalty

Sketch:

```text
score =
  interest_affinity
  + evidence_strength
  + novelty
  + recency
  + source_diversity
  + format_fit
  + feedback_bonus
  + discussion_potential
  - repetition_penalty
  - fatigue_penalty
  - low_confidence_penalty
```

### Feed Object Formats

Each candidate should be renderable as one or more social objects:

- `sharp_post`
  - X-like compact insight
  - one claim, one hook, short body
- `discussion_prompt`
  - Reddit-like prompt
  - framed as a question, tension, or debate
- `mini_essay`
  - Substack-like note
  - short essay with evidence and point of view
- `thread`
  - 3-7 connected cards
  - useful for unfolding a concept or argument
- `source_backed_card`
  - claim plus evidence snippet
  - optimized for trust
- `action_card`
  - turns insight into a task, experiment, or decision
- `bridge_card`
  - connects two distant bubbles or sources
- `resurfacing_card`
  - brings back a dormant idea with current relevance

### Transitional Post Model

The short-form to long-form transition should feel native and continuous, not like clicking from one unrelated view into another.

Each post should support a staged reveal:

1. `glance`
   - tweet-like card
   - title or hook
   - one compressed claim
   - minimal evidence cue
2. `expand`
   - richer card or note
   - short explanation
   - visible context framing
   - evidence snippets
   - possible discussion prompt
3. `deep read`
   - article or thread surface
   - structured argument
   - bubble-local context
   - source drill-down
4. `interact`
   - thought chat, save, convert to task, connect to topic, refine framing

The user should feel that the expanded article is the same object unfolding, not a separate content type.

Design constraints:

- the hook should survive expansion
- the article should resolve the promise made by the short form
- each expansion stage should add information, not only more words
- the same post should be able to collapse back into a compact surface without losing identity

### Recommended Transition Implementation

Implementation recommendation:

- Generate a single `FeedPost` record with three render payloads:
  - `preview_payload`
  - `expand_payload`
  - `deep_read_ref`
- `preview_payload`
  - fully materialized at feed build time
  - cheap to render
- `expand_payload`
  - fully materialized at feed build time
  - includes context framing and source cues
- `deep_read_ref`
  - resolves on demand into full article or thread detail
  - reuses `long_form.py` and thought detail flows initially

Opinion:

- Do not generate the full article for every possible format variant up front.
- Do generate the preview and first expansion stage up front, because the transition has to feel instant.
- The `expand` stage is where the product will either feel coherent or fake; treat it as a first-class artifact, not a CSS animation on top of the preview card.

Recommended field sketch:

```text
FeedPost
  post_id
  thought_packet_id
  format_kind
  title
  preview_payload
  expand_payload
  deep_read_ref
  context_packet_id
  ranking_features
  feedback_state
```

### Scoped Context Packet

Each post needs isolated scoped context. The system should not expose or use the full knowledge ocean at interaction time unless the user explicitly asks to widen scope.

Every `FeedPost` should carry a `FeedContextPacket` with:

- `primary_bubble_id`
- `bubble_reach_mode`
  - `strict`
  - `adjacent`
  - `cross_bubble`
- `source_item_ids`
- `knowledge_edge_ids`
- `knowledge_node_ids`
- `tension_ids`
- `question_ids`
- `source_snippets`
- `context_summary`
- `why_this_post_now`
- `scope_boundary_note`

Default behavior:

- short-form generation uses only the packet
- article expansion uses only the packet plus explicitly allowed adjacent material
- post chat uses packet-bounded retrieval first
- widening beyond the packet should be a deliberate step, not the default

This gives each post a dedicated mental world:

- small enough to feel coherent
- large enough to feel alive
- bounded enough to trust

### Recommended Context Packet Implementation

The context packet should be materialized when the feed is built, not dynamically recomputed on every interaction.

Reason:

- stable provenance
- predictable post identity
- bounded article/chat expansion
- easier debugging and testing

Recommended packet budgets for first implementation:

- 1 primary bubble
- up to 2 adjacent bubbles only when reach mode allows it
- 6-12 source items
- 3-6 evidence snippets
- 4-8 knowledge nodes
- 2-5 knowledge edges
- 0-3 tensions
- 0-3 open questions

Recommended stored fields:

```text
FeedContextPacket
  context_packet_id
  primary_bubble_id
  reach_mode
  source_item_ids
  evidence_snippets
  node_ids
  edge_ids
  tension_ids
  question_ids
  context_summary
  promise_line
  scope_boundary_note
  generated_at
```

Opinion:

- Packet-bounded by default is the right tradeoff.
- Automatic widening during normal interaction will make the product feel smart in demos and untrustworthy in real use.
- If expansion needs adjacent context, that should already be encoded by `reach_mode=adjacent` at packet build time, not silently widened later.
- Cross-bubble reach should be rare and intentional because it is the fastest path to impressive but incoherent posts.

### Bubble Reach Policy

The context packet should be constructed from a clear reach policy rather than arbitrary retrieval.

Initial reach modes:

- `strict`
  - only the primary bubble and directly attached source fragments
- `adjacent`
  - the primary bubble plus high-confidence neighboring edges and tensions
- `cross_bubble`
  - explicitly surprising bridges across bubbles

Default recommendation:

- `sharp_post`: `strict`
- `discussion_prompt`: `strict` or `adjacent`
- `mini_essay`: `adjacent`
- `bridge_card`: `cross_bubble`
- `resurfacing_card`: `strict`

Opinion:

- `strict` should be the default for most posts.
- `adjacent` should be earned by relevance, not used as a convenience fallback.
- `cross_bubble` should be limited to explicit bridge formats and high-confidence novelty candidates.

### Widening Rules

Widening should require an explicit transition:

- `preview -> expand`
  - no widening
- `expand -> deep_read`
  - use packet reach only
- `deep_read -> chat`
  - use packet reach only by default
- user action `widen scope`
  - allowed to retrieve adjacent or broader bubble context

This preserves the feeling that each post has a local world.

### Feedback Controls

The current `relevant`, `revisit_later`, and `dismiss` controls are not enough for a high-quality social feed.

Target controls:

- `more_like_this`
- `less_like_this`
- `too_obvious`
- `too_vague`
- `wrong_framing`
- `good_but_badly_written`
- `turn_into_article`
- `turn_into_task`
- `connect_to_topic`
- `save`
- `dismiss`
- `revisit_later`

Feedback should affect:

- ranking
- source/bubble affinity
- format preference
- style profile
- repetition/fatigue state
- future candidate generation

## Style And Taste Layer

The feed needs a style profile distinct from long-form structure profiles.

Initial style profile fields:

- preferred sentence length
- preferred directness
- preferred abstraction level
- preferred density
- preferred use of questions
- preferred use of examples
- tolerated ambiguity
- disliked patterns
- successful hooks
- preferred post formats
- preferred expansion formats

Inputs:

- accepted or saved outputs
- user-authored notes
- user corrections
- rewrite feedback from `personal_interface`
- dismissed items
- items expanded, chatted with, or converted to tasks

## UI Direction

The current miniapp is useful but reads more like a knowledge browser than a premium social feed.

Target feed UI:

- vertical scroll surface
- compact cards with strong typographic hierarchy
- expand-in-place or detail panel
- fast feedback controls
- topic/bubble filter
- "why am I seeing this?" provenance panel
- source evidence drawer
- format toggle where useful
- daily batch and archive modes
- clear distinction between grounded, speculative, and needs-review items

## Implementation Slices

### Slice 1: Feed Wrapper Continuity

Goal:
Preserve the current `/feed` surface while making each thought behave like one social post that unfolds across preview, expand, and deep-read.

Actual work in slice 1:

- add feed-owned wrapper fields to feed rows
- expose `post_id`, `post_format`, `reach_mode`, `preview_payload`, `expand_payload`, `deep_read_ref`, and `post_context`
- keep `ThoughtPacket` as the upstream artifact
- keep packet-bounded context with default `reach_mode = strict`
- expose the same feed-post continuity on thought detail

Status:

- in progress
- implemented inside `product_inner_world.py` because the engineering guard rejected a new package as the first move

Opinion:

- This is the right first code slice because it creates the backend continuity contract the UI will rely on.
- It also proves the social-feed model without forcing a larger module extraction too early.

### Slice 2: Internal Feed Quality

Goal:
Make the feed produce varied, non-repetitive, readable cards from the existing knowledge ocean.

Actual first work inside this slice:

- widen the ranked candidate pool before final feed selection
- apply a second-stage backend selector that prefers unseen primary source refs and unseen primary bubbles
- keep the selector deterministic and local to the current feed owner
- expose feed diagnostics in `/feed` so the backend can explain composition before the UI depends on it

Current diagnostics contract:

- `diagnostics.selection.candidate_pool_count`
- `diagnostics.selection.selected_count`
- `diagnostics.selection.unique_primary_source_count`
- `diagnostics.selection.unique_primary_bubble_count`
- `diagnostics.selection.selected_thought_ids`

Later likely work:

- expand packet generation beyond 3 packets
- improve candidate diversity
- penalize same-source clustering
- penalize near-duplicate titles and primitives
- add bubble/source quotas
- add feed diagnostics

Opinion:

- This is the highest-value first slice.
- If the internal feed cannot make 20 strong posts from the current corpus, external ingestion is premature.
- Keep the first diversity pass simple and inspectable.
- Do not move to opaque ranking heuristics before the feed diagnostics are useful.

### Slice 3: Feed Format Layer

Goal:
Represent social content formats explicitly.

Actual first work inside this slice:

- classify `post_format` from real feed row characteristics
- use bounded context signals rather than UI guesses
- expose `format_reason` per post so the contract is inspectable
- expose backend format mix diagnostics in `/feed`

Current backend format contract:

- `post_format`
- `format_reason`

Current format diagnostics contract:

- `diagnostics.formats.counts`

Opinion:

- Implement only 3-4 formats initially:
  - `sharp_post`
  - `discussion_prompt`
  - `mini_essay`
  - `source_backed_card`
- More formats should wait until ranking and scoped context are stable.
- Keep the classifier deterministic until the format signals are trustworthy enough to tune.
- The backend should explain why a post became a discussion prompt or source-backed card.

### Slice 4: Style/Taste Profile

Goal:
Give the feed a user-specific writing taste model.

Actual first work inside this slice:

- track backend feed interaction events:
  - `detail_open`
  - `thought_chat`
  - `thread_saved`
  - `explicit_feedback`
- persist raw learning events to `feed_learning_events.jsonl`
- aggregate a compact feed taste profile in `feed_taste_profile.json`
- expose the taste profile in `/feed` diagnostics so later UI and ranking work can consume it

Current backend taste contract:

- raw events in `feed_learning_events.jsonl`
- compact profile in `feed_taste_profile.json`
- `/feed.diagnostics.taste_profile`

Current taste profile fields:

- `event_count`
- `signal_counts`
- `format_counts`
- `format_scores`
- `preferred_formats`

Opinion:

- Separate "is this interesting?" from "is this written the right way?"
- Otherwise the system will learn the wrong lessons from dismissals.
- The first implementation should learn from explicit feedback plus strong interaction signals before attempting deeper tone modeling.
- This slice provides the learning substrate first. Stronger taste-aware ranking and copy shaping can build on top of it next.

### Slice 5: Taste-Aware Selection

Goal:
Let the learned taste profile slightly influence final feed selection before any UI work consumes it.

Actual backend contract:

- feed candidates are prepared with:
  - `_feed_post`
  - `_taste_score`
- `_taste_score` is derived from:
  - `format_scores`
  - `preferred_formats`
- final selection still respects diversity bands first
- taste only breaks ties within an otherwise equal diversity band
- `/feed.diagnostics.selection` now exposes:
  - `applied_preferred_formats`
  - `taste_adjusted_thought_ids`

Opinion:

- This is the right first application of taste data because it is measurable and easy to inspect.
- Ranking should move before copy shaping.
- The feed should explain when taste changed the winner instead of silently hiding the effect.

### Slice 6: Taste-Aware Payload Shaping

Goal:
Let the learned taste profile shape how a selected post opens and invites interaction, without changing the underlying thought or introducing freeform voice imitation.

Actual backend contract:

- `preview_payload` now carries:
  - `lead_mode`
  - `lead_text`
  - `cta_label`
  - `taste_shape`
- `expand_payload` now carries:
  - `opening_focus`
  - `opening_text`
  - `recommended_interaction`
  - `taste_shape`
- `taste_shape` is deterministic and currently derived from:
  - `preferred_formats`
  - `signal_counts`
- current shaping rules cover:
  - evidence-first presentation
  - question-first presentation
  - synthesis-first presentation
  - compact vs depth-oriented section budgets
  - interaction hints like `thought_chat`, `save_thread`, and `deep_read`

Opinion:

- This is the right place to start because it changes presentation without mutating truth conditions.
- The system should present the same thought differently before it tries to generate new prose in the user’s voice.
- Any shaping rule should remain inspectable in payloads and tests.

### Slice 7: Taste Diagnostics Polish

Goal:
Expose per-post shaping reasons so UI and future workers can inspect why the backend chose a particular opening, compactness mode, or interaction hint.

Actual backend contract:

- each selected feed thought now carries `taste_diagnostics`
- `/feed.diagnostics.taste_posts` mirrors a per-thought summary keyed by `thought_id`
- current taste diagnostics explain:
  - whether the selected post matched the preferred format
  - which lead rule fired
  - which interaction rule fired
  - which compactness rule fired
  - which raw signal counts drove those rules

Opinion:

- Diagnostics should reuse the exact same deterministic shaping logic, not a second explanatory pass.
- This slice is the last backend polish step before UI work because it keeps the surface debuggable.

### Slice 8: Scroll Feed UI

Goal:
Make the primary surface feel like a social feed.

Actual first implementation:

- landed as a served/bundled enhancement layer in:
  - `src/conversation_os/miniapp.py`
  - `tools/build_inner_world_openclaw_miniapp.py`
- kept the existing backend endpoints and base static assets intact
- injected:
  - `feed-ui-enhancement.css`
  - `feed-ui-enhancement.js`
- turned the feed into:
  - compact preview posts
  - inline expand surfaces
  - scoped context side panels
  - per-post taste diagnostics panels
  - deep-read disclosure for full article markdown
  - fast feedback controls in the expanded surface

Opinion:

- The UI should ship only after `expand_payload` is a real artifact.
- Otherwise the frontend will fake continuity that the backend cannot support.
- This first pass is intentionally additive: the enhancement layer can be iterated without destabilizing the base miniapp shell.

### Slice 9: Scheduler

Goal:
Generate the feed automatically on a daily cadence.

Likely work:

- add CLI command or script for scheduled batch generation
- add launchd/systemd/cron sample
- do not run heavy rebuilds on every feed read

### Slice 10: External Discovery Pond

Goal:
Add external RSS/API ingestion only after the internal feed is good.

Constraints:

- opt-in only
- clearly marked external source family
- scored against interest graph before promotion
- does not pollute raw user knowledge by default
- reviewable before durable promotion

## Non-Goals For Initial Implementation

- public social network
- followers or shared inner worlds
- engagement-maximizing dark patterns
- autonomous external research by default
- infinite feed with no trust controls
- replacing the current knowledge layer
- collapsing source and derived layers

## Open Questions

- What is the minimum packet count needed for the feed to feel alive?
- Should format selection be deterministic first or LLM-assisted immediately?
- Should feedback controls be visible on every card or hidden behind a compact menu?
- Should daily feed generation produce a fixed batch or support continuous refresh?
- What is the right data model boundary between `ThoughtPacket` and new feed objects?
- Should external discovery live under plugins, library sources, or a new discovery module?

## Current Recommendation

Start with internal feed quality and format diversity before adding external ingestion.

Reason:
The knowledge ocean is already large. The visible bottleneck is not lack of content; it is converting existing content into varied, engaging, trusted social objects.

## Source Links Used In Research

- X algorithm repository: `https://github.com/twitter/the-algorithm`
- X organic best practices: `https://business.x.com/en/basics/organic-best-practices.html`
- X Articles guide: `https://help.x.com/en/using-x/articles`
- Reddit sort help: `https://support.reddithelp.com/hc/en-us/articles/19695706914196-What-filters-and-sorts-are-available`
- Reddit archived hot formula: `https://raw.githubusercontent.com/reddit-archive/reddit/753b17407e9a9dca09558526805922de24133d53/r2/r2/lib/db/_sorts.pyx`
- Substack Notes guide: `https://support.substack.com/hc/en-us/articles/14564821756308-Getting-started-on-Substack-Notes`
- Substack app guide: `https://support.substack.com/hc/en-us/articles/19291693034004-Getting-started-on-the-Substack-app`
- Substack recommendations: `https://support.substack.com/hc/en-us/articles/5036794583828-How-can-I-recommend-other-publications-on-Substack`
- Substack leaderboards: `https://support.substack.com/hc/en-us/articles/5999320475412-What-are-Substack-leaderboards`
- Substack post stats: `https://support.substack.com/hc/en-us/articles/15853567274772-Guide-to-your-Substack-Posts-page`

## Changelog

### 2026-04-30

- Created living implementation spec.
- Captured repo baseline and corrected prior component review.
- Captured research synthesis for X, Reddit, and Substack.
- Defined feed candidate sources, ranking model, format layer, feedback controls, style profile, UI direction, implementation slices, non-goals, and open questions.
- Locked the first implementation recommendations:
  - preserve `/feed`
  - wrap `ThoughtPacket`
  - make `expand` a first-class mid-layer
  - keep a tight strict packet budget
- Recorded the engineering-guard outcome:
  - slice 1 must land inside `product_inner_world.py` first
  - dedicated `social_feed/` extraction is deferred until the wrapper contract is proven
- Implemented backend feed quality slice 2 in the current owner surface:
  - widened candidate pool before final feed selection
  - added deterministic source/bubble diversity selection
  - added `/feed` diagnostics for backend composition inspection
- Implemented backend format slice 3 in the current owner surface:
  - added deterministic post-format classification from evidence, questions, tensions, and article structure
  - added `format_reason` per feed row
  - added `/feed` format mix diagnostics
- Implemented backend taste-learning slice 4 in the current owner surface:
  - added feed interaction event tracking for detail opens, thought chat, thread saves, and explicit feedback
  - added persisted feed taste profile aggregation
  - exposed the taste profile in `/feed` diagnostics
- Implemented backend taste-aware selection slice 5 in the current owner surface:
  - applied learned format preference as a small tie-break inside final feed selection
  - kept diversity band selection as the stronger rule
  - exposed taste-selection diagnostics showing when taste changed the winner
- Implemented backend taste-aware payload shaping slice 6 in the current owner surface:
  - shaped preview and expand payload openings from the learned taste profile
  - added deterministic `taste_shape` metadata to keep the behavior inspectable
  - added evidence-first and interaction-hint presentation without changing retrieval or article truth
- Implemented backend taste diagnostics polish slice 7 in the current owner surface:
  - added per-post `taste_diagnostics`
  - mirrored per-post shaping explanations in `/feed.diagnostics.taste_posts`
  - kept explanation rules tied to the same deterministic shaping logic
- Implemented scroll feed UI slice 8 as a served/bundled enhancement layer:
  - injected dedicated CSS and JS override assets into the served miniapp and bundle output
  - rendered compact previews from `preview_payload`
  - rendered inline expand surfaces from `expand_payload`, `post_context`, and `taste_diagnostics`
  - kept the `/feed` and `/thought` API contracts unchanged
