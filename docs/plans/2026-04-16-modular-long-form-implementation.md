# Modular Long-Form Implementation Design

## Goal

Replace the current hardcoded article-expansion formatter with a modular, substrate-aware long-form generation system that:

- fits the rest of the Inner World framework
- stays inspectable
- is user-adjustable
- remains generic enough to work across research, art, entrepreneurship, and adjacent deep-thinker content
- can be rendered by the existing frontend with minimal breakage

## Current state

Today, long-form generation is effectively one function:

- `src/conversation_os/thought_factory.py::_article_markdown(...)`

It builds one fixed article shape:

1. title
2. short intro
3. `The Pull`
4. `Why It Keeps Staying Alive`
5. `Fragments Underneath It`
6. `What Stays Open`
7. `If You Follow It`

This has three limits:

1. structure is not modular
2. structure is not user-adjustable
3. structure does not explicitly consume the new substrate library or long-form blueprint

The frontend already renders `thought.article_markdown`, so we do not need a new rendering model first. We need a better generation model that can still emit markdown plus structured metadata.

## Target architecture

Implement long-form generation as one orchestration layer sitting above four specific execution layers:

1. `LongFormOrchestrator`
2. `LongFormConfigLoader`
3. `LongFormContextBuilder`
4. `LongFormModuleAssembler`
5. `LongFormRenderer`

### 0. LongFormOrchestrator

Purpose:

- sit above context extraction and output rendering
- decide how the article should be formulated at a higher level
- coordinate config resolution, context construction, module assembly, and final rendering

This is the control layer.

It should not be where the prose details live.

It should decide:

- which profile is active
- which modules are enabled
- which order they run in
- which resolved payload gets persisted

That keeps the article-shaping logic modular and inspectable instead of burying structure decisions inside a formatter.

### 1. LongFormConfigLoader

Purpose:

- load the default blueprint from:
  - `docs/research/substack-article-structure-2026-04-16/long_form/long_form_blueprint.json`
- resolve module manifests
- apply profile defaults
- apply per-user overrides later

Output:

- one resolved article config

### 2. LongFormContextBuilder

Purpose:

- transform a thought packet and its nearby source material into a richer article context object

Input sources:

- promotion row / thought packet
- source snippets
- meta refs
- contradictions
- unresolved questions
- reasoning primitive

New derived context fields:

- `signal_frame`
- `object_field`
- `transformation_path`
- `decisions`
- `guardrails`
- `tensions`
- `contradictions`
- `evidence_ladder`
- `open_questions`
- `pattern_transfer`

This layer is where the selected abstraction algorithms are applied in article terms.

### 3. LongFormModuleAssembler

Purpose:

- build article sections from the resolved config and article context

Each module should be a dedicated function or class, for example:

- `build_promise_frame(context, module_config)`
- `build_entry_vector(context, module_config)`
- `build_thesis_and_reader_map(context, module_config)`
- `build_object_field(context, module_config)`
- `build_tension_and_stakes(context, module_config)`
- `build_evidence_ladder(context, module_config)`
- `build_pattern_and_transfer(context, module_config)`
- `build_decisions_and_implications(context, module_config)`
- `build_open_questions_and_boundaries(context, module_config)`
- `build_close_and_next_move(context, module_config)`

Each module returns a structured section object, not raw markdown.

Suggested shape:

```json
{
  "module_id": "tension-and-stakes",
  "title": "The central tension",
  "enabled": true,
  "weight": "core",
  "markdown": "## The central tension\n...",
  "source_refs": [],
  "evidence_refs": [],
  "data": {}
}
```

### 4. LongFormRenderer

Purpose:

- convert ordered section objects into `article_markdown`
- also persist machine-usable structure for the frontend and future agents

Output fields:

- `article_markdown`
- `article_sections`
- `article_profile`
- `article_module_order`
- `article_config_snapshot`

## Ideal data model changes

Extend `ThoughtPacket` with optional fields:

- `article_sections: List[Dict]`
- `article_profile: str`
- `article_module_order: List[str]`
- `article_config_snapshot: Dict[str, Any]`

This keeps backwards compatibility:

- the frontend can continue rendering `article_markdown`
- new UI work can progressively adopt `article_sections`

## Where to implement

### New module

Add a new file:

- `src/conversation_os/long_form.py`

Responsibilities:

- blueprint loading
- module manifest loading
- context building
- section assembly
- markdown rendering

Keep `thought_factory.py` slim by making it call:

```python
article = build_long_form_article(root, row, snippets, title, short_text)
```

Then assign:

- `article["markdown"]`
- `article["sections"]`
- `article["profile"]`
- `article["module_order"]`
- `article["config_snapshot"]`

### Minimal touch in existing generation

Update:

- `src/conversation_os/thought_factory.py`

Change:

- replace `_article_markdown(...)`

With:

- `_build_article_payload(...)`

That function should delegate to `long_form.py`.

## Mapping the substrate algorithms into generation

Use these mappings:

### `signal-frame-extractor`

Feeds:

- headline tuning
- subtitle
- thesis compression
- opening scope boundary

### `object-model-projection`

Feeds:

- object-field module
- section planning
- named components in the body

### `transformation-path-extractor`

Feeds:

- body order
- reader map
- sequence logic between sections

### `decision-commitment-extractor`

Feeds:

- default positions
- implications
- closing commitment

### `guardrail-antigoal-extractor`

Feeds:

- anti-genericity layer
- scope boundaries
- “what this is not” or “what this should not become”

### `tension-map-extractor`

Feeds:

- stakes
- pressure
- middle-body energy

### `contradiction-pair-extractor`

Feeds conditionally:

- explicit contradiction section
- review pressure block

Only enable if contradiction density crosses a threshold.

### `evidence-confidence-scaffold`

Feeds:

- evidence ladder
- confidence posture
- article grounding cues

### `open-question-missingness-extractor`

Feeds:

- open questions
- unresolved boundaries
- “what remains unsettled”

### `reasoning-primitive-detector`

Feeds:

- pattern-and-transfer module
- article-level reusable insight

## User adjustability

User adjustment should happen in three tiers.

### Tier 1: global profile

Examples:

- `explainer_default`
- `narrative_leaning`
- `research_heavy`
- `pattern_transfer`

Storage suggestion:

- `product/inner_world_v1/config/long_form.json`

### Tier 2: module toggles

Examples:

- disable `object-field`
- emphasize `entry-vector`
- compress `open-questions-and-boundaries`

Suggested config shape:

```json
{
  "profile": "explainer_default",
  "modules": {
    "entry-vector": { "enabled": true, "weight": "medium" },
    "object-field": { "enabled": false },
    "pattern-and-transfer": { "weight": "heavy" }
  }
}
```

### Tier 3: per-thought overrides

Not needed in the first implementation, but the data model should allow it.

Useful later for:

- one-off article re-renders
- user preference experiments
- premium or advanced authoring controls

## Frontend integration strategy

### Phase 1: zero-UI-break rollout

Do not change the frontend contract first.

Keep rendering:

- `thought.article_markdown`

Add extra fields to the thought payload, but let the UI ignore them until needed.

This means the frontend will automatically pick up the new structure as soon as regenerated markdown is better.

### Phase 2: inspectable section rendering

After generator stabilization, upgrade the article detail UI to optionally use:

- `article_sections`

Benefits:

- module-aware rendering
- collapsible sections
- future reader customization
- easier evidence/source drill-down per section

Suggested frontend changes later:

- show active modules
- show profile badge
- show section-specific evidence chips

## Rollout plan

### Step 1

Create `src/conversation_os/long_form.py` with:

- blueprint loader
- module manifest loader
- article context builder
- section renderer

### Step 2

Add article payload generation in `thought_factory.py`.

### Step 3

Extend `ThoughtPacket` schema in `models.py` with optional long-form metadata fields.

### Step 4

Add default config file:

- `product/inner_world_v1/config/long_form.json`

### Step 5

Rebuild:

- `thought_packets.jsonl`
- `latest_feed.json`
- `latest_archive.json`

### Step 6

Verify in the miniapp that the article view reads more like the new modular blueprint without any UI changes.

### Step 7

Only after that, add optional frontend section-aware rendering.

## Testing strategy

### Unit tests

Add tests for:

- config loading
- module ordering
- module toggles
- profile resolution
- conditional contradiction module activation

### Content tests

Fixture tests should assert that generated long-form output contains:

- early thesis
- explicit tension block
- evidence block
- pattern / transfer section
- bounded close

### Regression tests

Assert:

- feed still builds
- archive still builds
- article markdown still exists
- frontend contract remains compatible

## Success criteria

The implementation is successful when:

- generated articles visibly follow the modular long-form blueprint
- the format can be adjusted without editing generator code
- the same structure works across different domains
- the article output becomes stronger without requiring immediate frontend rewrite
- the frontend naturally picks up the improved article shape through regenerated markdown

## Recommended first implementation boundary

Do not try to make the whole article system interactive on day one.

First ship:

1. blueprint-driven article assembly
2. persisted section metadata
3. config-based module toggles
4. backwards-compatible markdown rendering

That is enough to make the new long-form approach real inside the framework.
