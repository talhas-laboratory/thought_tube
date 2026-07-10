# Reasoning Pipeline Build Report

Research date: 2026-06-10

## Purpose

This report consolidates the current conversation into one build-oriented document.

It covers:

- the main learnings from the creative human cognition research
- what reasoning pipelines are
- what they help with
- how they should work mechanically
- how to build them in this repo using the current module owners and runtime surfaces

This is not a generic AI architecture memo. It is a repo-specific construction guide for turning the current Conversation OS substrate into a reasoning system that can help users integrate partial thoughts into larger idea structures.

## Short Answer

The core claim from the conversation is:

The project should not mainly automate "answering." It should automate or assist the user's repeated idea-forming transformations.

That means the system should help a user take a fragment, determine what larger idea it belongs to, process it through relevant dimensions, decide whether it should expand, narrow, tension, suspend, or integrate, and then learn from the user's corrections.

The repo already has the right cold-path substrate for this:

- append-only capture
- analysis units
- meta extraction
- shape signatures
- thread abstractions
- context bubbles
- knowledge-layer retrieval
- small packet-based operator pipelines

What is missing is a hot-path reasoning runtime that can:

- build a live active state for the current fragment
- route to the right reasoning pipeline
- evaluate the result
- store user corrections as future reasoning signal

## Learnings From The Creative Human Cognition Report

The main research result is stable:

Creative thinking is not one thing. It is a regulated interaction between:

- associative expansion
- control and evaluation
- reframing
- incubation
- resurfacing
- elaboration
- integration

The strongest cross-domain process model from the research report is:

`problem framing -> semantic expansion -> constraint shaping -> incubation/replay -> candidate resurfacing -> evaluation/selection -> elaboration -> integration`

The strongest recurring failure modes are:

- fixation on dominant representations
- premature convergence
- weak problem framing
- poor novelty selection
- ambiguity overload
- translation failure
- mismanaged incubation
- metacognitive blind spots

The key implication for this project is:

The system should not optimize only for retrieval or summarization. It should optimize for helping the user move a fragment through the right transformation sequence without collapsing it too early or leaving it permanently unformed.

## Problem Definition

The problem this system should solve is:

A user often has partial cognitive pressure rather than a clean request.

This may appear as:

- a phrase
- an image
- a tension
- a question
- an analogy
- a memory
- a mood
- a design signal
- a lyric line

That fragment usually does not matter in isolation. It matters because it may belong to a larger internal structure:

- a worldview
- a project
- a song
- a film
- a product concept
- a design language
- a research thesis

The user's real work is not "generate an answer." Their real work is:

1. determine what the fragment is really about
2. determine what larger idea it touches
3. process it through relevant dimensions
4. test whether it should be expanded, constrained, suspended, or integrated
5. update the larger internal structure accordingly

So the system should assist with:

- framing
- defixation
- structured expansion
- controlled narrowing
- resurfacing
- evaluation
- integration

## What Reasoning Pipelines Are

In this project, a reasoning pipeline is not a prompt template.

A reasoning pipeline is:

`a controlled sequence of state transformations that moves a fragment from raw pressure to evaluated integration`

More concretely, a reasoning pipeline does five jobs:

1. frames the current fragment
2. activates the relevant context and dimensions
3. applies selected reasoning operators in sequence
4. evaluates whether the transformation was useful
5. emits an outcome and learning signal

That means reasoning pipelines are the layer between:

- durable substrate

and

- live assistance

Without them, the system can store and retrieve. With them, the system can help a user work through a thought.

## What Reasoning Pipelines Help With

Reasoning pipelines are useful whenever the user is not asking for a simple fact or direct completion.

They help most with:

- placing a fragment into a larger idea
- breaking fixation on the first obvious interpretation
- deciding whether a thought should expand or narrow a concept
- preserving useful tension instead of flattening it
- distinguishing core signal from surrounding noise
- handling ambiguity without either collapsing too early or drifting forever
- helping a user convert vague material into workable structure
- learning a user's repeated reasoning moves over time

In practice, this means the system can become better at:

- product concept formation
- research thesis formation
- lyric development
- worldbuilding
- long-horizon strategy thinking
- design language development

## Core Conceptual Model

The best model from the conversation is:

`fragment -> active field -> operator sequence -> evaluation -> integration -> learning`

Where:

- `fragment` is the current piece of incoming thought
- `active field` is the bounded semantic state relevant now
- `operator sequence` is the chosen reasoning path
- `evaluation` judges whether the result is strong enough
- `integration` decides what happens to the fragment
- `learning` captures how the user responded

## Runtime State Model

The runtime should distinguish three layers clearly:

- `evidence`: append-only source material from the current turn and prior turns
- `state`: bounded mutable control variables for the current turn
- `shape`: the current arrangement of active state variables, object relations, and conceptual orientation

This distinction matters because each new user turn should be treated as new evidence that may update part of the live state without resetting the whole reasoning environment.

A good runtime therefore does not rebuild the user's world from scratch every turn. It updates only the variables affected strongly enough by the new evidence and emits a structural switch only when the active topic, goal, object scope, or reasoning family has meaningfully changed.

## Pipeline Mechanics

### 1. Fragment Intake

Input:

- raw user text
- optional attachments or references
- recent local conversation

Output:

- `ThoughtFragment`
- `ReasoningRequest`

The system should preserve:

- raw text
- source refs
- session id
- timestamp
- initial domain hints

### 2. Retrieval

The system must not reason over the whole library every turn.

It should first build a bounded retrieval bundle from the current fragment.

Current owner:

- [knowledge_layer.py](/Users/talhauddin/software/inner_space/src/conversation_os/knowledge_layer.py:808)

The bundle should include:

- relevant capsules
- nearby links
- source refs
- anchor pond
- alias hits

### 3. Bridge-Orchestrated Context Construction

The repo research changed one important implementation detail:

The hot path should not begin inside `ActiveFieldState` construction alone.

It should begin in a bridge-like runtime owner that:

- classifies the turn
- binds or confirms the active workspace
- chooses retrieval depth
- assembles the smallest useful context bundle
- records context switches when state meaningfully changes

This matches the bridge requirements in:

- [03-chat-bridge-requirements.md](/Users/talhauddin/software/inner_space/docs/product-thesis/03-chat-bridge-requirements.md:47)
- [personal_interface.py](/Users/talhauddin/software/inner_space/src/conversation_os/personal_interface.py:589)
- [holodeck.py](/Users/talhauddin/software/inner_space/src/conversation_os/holodeck.py:389)

The bridge should own a bounded `ContextState` or theme tuple:

- `active_topic`
- `user_goal`
- `current_tension`
- `answer_shape`
- `active_workspace_id`
- `depth_mode`
- `confidence`
- `object_scope`
- `object_id`
- `parent_object_id`
- `dimension_axis`

This `ContextState` is the runtime control surface that sits before `ActiveFieldState`.

This lets the bridge distinguish between:

- continuation of the same main object
- a sub-object on another dimension of the same main object
- a parallel object that should remain adjacent but separate
- a genuinely new main object

Without this distinction, the runtime will either flatten unrelated thought into one thread or fragment one developing idea too aggressively.

### 4. Active Field Construction

This is the main missing runtime owner.

The `ActiveFieldState` should be built from:

- current fragment
- `ContextState`
- retrieval bundle
- bridge state
- recent thread context
- workspace-local context
- shape hints
- user profile / personalization

It should contain:

- `fragment_role`
- `candidate_parent_ideas`
- `active_dimensions`
- `active_tensions`
- `constraints`
- `ambiguity_level`
- `fixation_risk`
- `novelty_confidence`
- `fit_targets`
- `suggested_reasoning_family`
- `source_refs`

This object is the live working state for the turn.

This object is the live semantic working state for the turn.

It should also carry lightweight perturbation markers when relevant, such as:

- imported conversation
- prior thread
- image or artifact
- external reference
- tool output

These are not just citations. They are possible causes of topological change in the active field.

`ContextState` decides what world is active.
`ActiveFieldState` decides what structure inside that world should be reasoned over.

### 5. Routing

The system should not run one universal pipeline for all fragments.

It should choose a reasoning family based on the active field.

Examples:

- `problem_reframing_v1`
- `idea_embedding_v1`
- `defixation_v1`
- `candidate_evaluation_v1`
- `tension_preservation_v1`
- `cross_domain_transfer_v1`

Routing should depend on:

- ambiguity
- fixation
- tension
- domain lens
- whether the user is expanding or narrowing
- whether the user appears to be embedding, reframing, suspending, or evaluating

### 6. Operator Execution

Each reasoning pipeline should be executed as an ordered operator sequence.

This repo already has the right execution pattern in:

- [pipeline_runner.py](/Users/talhauddin/software/inner_space/src/conversation_os/pipeline_runner.py:36)
- [pipelines.py](/Users/talhauddin/software/inner_space/src/conversation_os/pipelines.py:21)
- [operators.py](/Users/talhauddin/software/inner_space/src/conversation_os/operators.py:811)

The difference is that the existing operators are mainly extraction-oriented. The next phase should add reasoning-oriented operators and, later, user-shaped transformation operators.

Examples:

- `classify_fragment_role`
- `identify_parent_ideas`
- `activate_dimensions`
- `detect_fixation_risk`
- `generate_counterframes`
- `surface_candidate_transformations`
- `score_fit_vs_novelty`
- `prepare_probe`
- `prepare_candidate_integration`

Later, the system should also model user-specific moves such as:

- preserve tension
- suspend placement
- expand symbolic dimensions before practical ones
- narrow ambiguity early
- translate image into structure

These are closer to the actual philosophical target of the project than generic reasoning operators alone.

### 7. Evaluation

The system should not trust the first produced articulation.

It should explicitly judge:

- did the move preserve signal
- did it avoid generic flattening
- did it fit the user's larger idea
- did it protect novelty where needed
- did it over-collapse ambiguity
- should the result be integrated, suspended, rejected, or left as tension

This is similar in spirit to the current quality gates in:

- [operators.py](/Users/talhauddin/software/inner_space/src/conversation_os/operators.py:663)

but it needs to become richer and more domain-aware.

### 8. Outcome

The system should emit both:

- a user-facing response
- a machine-facing result

Machine-facing result:

- `integration_verdict`
- `recommended_next_operator`
- `suspension_reason`
- `fit_score`
- `novelty_score`
- `confidence`

User-facing result:

- direct answer
- candidate reframing
- clarified tension
- proposed integration
- next question or probe

### 9. Learning

The system should learn not from silent assumptions but from the user's reactions.

Important signals:

- accepted framing
- rejected framing
- preferred abstraction level
- preferred challenge level
- repeated moves under similar conditions
- which transformations the user uses most often

This is where symbiotic assistance becomes learned personalization.

The first learning target should remain narrow:

- repeated reasoning moves
- accepted and rejected framings
- preferred abstraction shifts
- repeated transformation choices under similar conditions

The system should learn from observable conversational behavior, not from speculative claims about the user's hidden psychology.

This is also where the bridge plan and the philosophical framework meet:

- the bridge owns turn-time routing and bounded state
- the reasoning runtime owns structured transformation
- the learning layer gradually infers the user's repeatable operators

## How This Maps To Current Repo Surfaces

### Existing Cold Path

The repo already has a strong cold path.

Relevant modules:

- [storage.py](/Users/talhauddin/software/inner_space/src/conversation_os/storage.py)
- [analysis.py](/Users/talhauddin/software/inner_space/src/conversation_os/analysis.py)
- [analysis_units.py](/Users/talhauddin/software/inner_space/src/conversation_os/analysis_units.py:85)
- [meta_layer.py](/Users/talhauddin/software/inner_space/src/conversation_os/meta_layer.py:1231)
- [thread_abstractions.py](/Users/talhauddin/software/inner_space/src/conversation_os/thread_abstractions.py:279)
- [context_bubbles.py](/Users/talhauddin/software/inner_space/src/conversation_os/context_bubbles.py:1286)
- [knowledge_layer.py](/Users/talhauddin/software/inner_space/src/conversation_os/knowledge_layer.py:977)
- [conversation_synthesis.py](/Users/talhauddin/software/inner_space/src/conversation_os/conversation_synthesis.py)
- [runtime_pipeline.py](/Users/talhauddin/software/inner_space/src/conversation_os/runtime_pipeline.py:29)
- [library_tracker.py](/Users/talhauddin/software/inner_space/src/conversation_os/library_tracker.py:3492)

This path already gives the system:

- durable raw capture
- analysis units
- meta records
- shape signatures
- knowledge capsules
- structured retrieval

### Existing Hot Path Pieces

The repo has the beginning of a hot path, but not the full reasoning runtime.

Relevant modules:

- [pipeline_runner.py](/Users/talhauddin/software/inner_space/src/conversation_os/pipeline_runner.py:36)
- [pipelines.py](/Users/talhauddin/software/inner_space/src/conversation_os/pipelines.py:21)
- [operators.py](/Users/talhauddin/software/inner_space/src/conversation_os/operators.py:398)
- [personal_interface.py](/Users/talhauddin/software/inner_space/src/conversation_os/personal_interface.py:589)
- [personal_interface_mcp.py](/Users/talhauddin/software/inner_space/src/conversation_os/personal_interface_mcp.py:39)
- [holodeck.py](/Users/talhauddin/software/inner_space/src/conversation_os/holodeck.py:389)

This already gives:

- packet execution
- ordered operators
- bridge state
- lightweight personalization signals
- workspace-local contextualization primitives

Repo research also shows an important asymmetry:

- `personal_interface.py` already owns reply adaptation and a thin bridge state
- `knowledge_layer.py` already owns bounded retrieval bundles
- `holodeck.py` already owns bounded workspace context

What is still missing is the explicit runtime owner that composes those three into one bounded turn-time control plane.

### Missing Owners

The clearest missing modules are:

- `reasoning_bridge.py`
- `active_field.py`
- `reasoning_router.py`
- `reasoning_evaluator.py`
- `reasoning_learning.py`
- `incubation.py`
- `resurfacing.py`

These should be new first-class owners rather than hidden inside existing modules.

## How Pattern Recognition Works In Practice

Pattern recognition should not be imagined as magical subconscious simulation.

It should work like this:

1. convert raw text into bounded units
2. extract structured features
3. compare them to stored structures
4. choose which structures are active now
5. run a reasoning path over that active subset

The current code already does versions of this:

- [operators.py](/Users/talhauddin/software/inner_space/src/conversation_os/operators.py:398) detects dimensions, tensions, primitives, and relevance heuristically
- [models.py](/Users/talhauddin/software/inner_space/src/conversation_os/models.py:769) stores shape signatures as structured entities, states, relations, constraints, and candidate shapes
- [knowledge_layer.py](/Users/talhauddin/software/inner_space/src/conversation_os/knowledge_layer.py:808) retrieves bounded context instead of dumping the full library into one prompt

The next step is to make this dynamic at turn time.

## How Dynamic Reasoning Should Work

Dynamic reasoning means:

The system does not produce an answer directly from the fragment alone. It first constructs a working semantic state and only then chooses a reasoning path.

The runtime loop should be:

1. receive fragment
2. classify turn into `ContextState`
3. bind or confirm active workspace
4. assemble bounded context bundle
5. build `ActiveFieldState`
6. route to pipeline family
7. run pipeline operators
8. evaluate result
9. return response and machine verdict
10. record user correction
11. record context switch if state changed

This is dynamic because:

- the same type of fragment can route differently depending on context
- a user who prefers preserved tension will get different moves than a user who prefers immediate synthesis
- a lyric fragment and a product fragment can use the same architecture but different operators and evaluation criteria

Each step in this loop should preserve stable state when possible.

Low-impact turns may only update one or two variables such as abstraction level or answer shape.
Medium-impact turns may update the active field.
High-impact turns may trigger a context switch or a new main object.

This keeps the runtime adaptive without making it unstable.

## What "Automating Subconscious Thought" Should Mean

The system should not claim to read or replicate literal subconscious processes.

The correct implementation target is:

`model the repeatable outputs of the user's latent processing and the transformations they apply when those outputs surface`

In practice, this means:

- the system observes which fragments reappear
- it records how the user tends to treat tension, ambiguity, and integration
- it reuses those patterns when similar material appears later

The slow loop should support this by:

- replaying unresolved fragments offline
- building candidate links
- surfacing them later when relevant

That is the closest practical software analogue to incubation.

## Backend Construction Guide For This Repo

### Phase 1: Build The Active Field Runtime

Create:

- `src/conversation_os/reasoning_bridge.py`
- `src/conversation_os/active_field.py`

Responsibilities:

- define `ContextState`
- classify turn and bind runtime context before reasoning begins
- assemble a bounded four-layer context bundle:
  - session-local
  - workspace-local
  - user-local
  - global fallback
- define `ActiveFieldState`
- compile the current fragment, `ContextState`, retrieval bundle, and bridge state into one runtime object
- attach relevant shape hints, tensions, and candidate parent ideas

Suggested functions:

- `classify_turn(...)`
- `bind_workspace(...)`
- `get_context_bundle(...)`
- `record_context_switch(...)`
- `build_active_field(root: Path, fragment: Dict[str, Any], *, session_id: str = "", surface: str = "") -> Dict[str, Any]`
- `score_candidate_parent_ideas(...)`
- `detect_fixation_risk(...)`
- `detect_ambiguity_level(...)`

Dependencies:

- [knowledge_layer.py](/Users/talhauddin/software/inner_space/src/conversation_os/knowledge_layer.py:808)
- [meta_layer.py](/Users/talhauddin/software/inner_space/src/conversation_os/meta_layer.py)
- [conversation_synthesis.py](/Users/talhauddin/software/inner_space/src/conversation_os/conversation_synthesis.py)
- [personal_interface.py](/Users/talhauddin/software/inner_space/src/conversation_os/personal_interface.py:635)
- [holodeck.py](/Users/talhauddin/software/inner_space/src/conversation_os/holodeck.py:389)

### Phase 2: Build The Router

Create:

- `src/conversation_os/reasoning_router.py`

Responsibilities:

- inspect `ActiveFieldState`
- choose pipeline family
- choose operator overrides when needed

Suggested pipeline ids:

- `problem_reframing_v1`
- `idea_embedding_v1`
- `candidate_evaluation_v1`
- `defixation_v1`
- `tension_preservation_v1`

### Phase 3: Extend Pipeline Specs

Extend:

- [pipelines.py](/Users/talhauddin/software/inner_space/src/conversation_os/pipelines.py:21)

Add new specs under:

- `product/inner_world_v1/pipelines/*.json`

Suggested first spec:

`idea_embedding_v1`

Suggested steps:

- `classify_fragment_role`
- `identify_parent_ideas`
- `activate_dimensions`
- `generate_candidate_transformations`
- `score_candidate_transformations`
- `choose_best_probe_or_integration`
- `build_user_response`

### Phase 4: Extend Operators

Extend:

- [operators.py](/Users/talhauddin/software/inner_space/src/conversation_os/operators.py:811)

The existing operator registry already fits the design. Do not replace it. Add new operators.

Suggested operators:

- `classify_fragment_role`
- `identify_parent_ideas`
- `activate_dimensions`
- `detect_fixation_risk`
- `generate_counterframes`
- `generate_candidate_transformations`
- `score_candidate_transformations`
- `build_user_response`

### Phase 5: Add Evaluation

Create:

- `src/conversation_os/reasoning_evaluator.py`

Responsibilities:

- evaluate novelty preservation
- evaluate fit to parent idea
- evaluate whether ambiguity was handled correctly
- decide integration, suspension, rejection, or tension preservation

Output:

- `integration_verdict`
- `novelty_score`
- `fit_score`
- `tension_preservation_score`
- `recommended_next_action`

### Phase 6: Capture Learning Signals

Extend either:

- [personal_interface.py](/Users/talhauddin/software/inner_space/src/conversation_os/personal_interface.py)

or add a small new owner:

- `src/conversation_os/reasoning_learning.py`

Responsibilities:

- persist accepted or rejected framings
- track preferred abstraction levels
- track repeated transformation choices
- accumulate behavior patterns that can feed future routing

This should remain conservative. Do not let one turn rewrite the user's profile.

The learning target should be described precisely:

The first version learns:

- routing preferences
- preferred abstraction and challenge levels
- tolerance for preserved tension
- repeated transformation choices

The first version does **not** yet learn a complete model of the user's latent operator system.

That remains a later phase.

### Phase 7: Add Slow Incubation Later

Create later:

- `src/conversation_os/incubation.py`
- `src/conversation_os/resurfacing.py`

Responsibilities:

- select unresolved fragments
- compare them to stored concepts and shapes offline
- store candidate latent links
- resurface them when the active field matches

This should come after the hot path works.

## Recommended Implementation Order

1. Add `ActiveFieldState` contract.
2. Add `ContextState` contract.
3. Build the bridge entrypoint and bounded context bundle assembly.
4. Build `active_field.py`.
5. Add `idea_embedding_v1` pipeline spec.
6. Add new operators for fragment role, parent idea selection, and candidate transformations.
7. Build `reasoning_router.py`.
8. Build `reasoning_evaluator.py`.
9. Add learning signal persistence.
10. Only then add incubation/resurfacing.

This order keeps the first usable version symbiotic and inspectable.

## Suggested Data Contracts

### `ReasoningRequest`

Fields:

- `request_id`
- `session_id`
- `surface`
- `raw_text`
- `source_refs`
- `timestamp`
- `domain_hints`

### `ContextState`

Fields:

- `context_id`
- `request_id`
- `active_topic`
- `user_goal`
- `current_tension`
- `answer_shape`
- `active_workspace_id`
- `depth_mode`
- `confidence`
- `bundle_layers`
- `context_switch_trigger`

### `ActiveFieldState`

Fields:

- `field_id`
- `context_id`
- `fragment_role`
- `candidate_parent_ideas`
- `active_dimensions`
- `active_tensions`
- `constraints`
- `ambiguity_level`
- `fixation_risk`
- `novelty_confidence`
- `fit_targets`
- `retrieval_bundle_ref`
- `source_refs`

### `ReasoningResult`

Fields:

- `result_id`
- `pipeline_id`
- `response_text`
- `integration_verdict`
- `fit_score`
- `novelty_score`
- `confidence`
- `recommended_next_action`
- `trace`

## What Should Remain Unchanged

Do not move this logic into:

- `meta_layer.py`
- `knowledge_layer.py`
- `runtime_pipeline.py`

Those modules already have clean responsibilities:

- extraction
- retrieval
- cold-path orchestration

The new reasoning system should consume those layers, not absorb them.

Do not replace the packet runner with a third-party workflow framework first. The repo already has:

- a runtime DAG
- pipeline specs
- an operator registry
- JSON run artifacts

Use those.

## Libraries And Frameworks

Current external dependency surface is deliberately small.

Declared dependency:

- [pyproject.toml](/Users/talhauddin/software/inner_space/pyproject.toml)
  - `mcp`

Everything else is mostly:

- Python stdlib
- file-backed JSON / JSONL
- repo-owned pipeline and storage logic

Recommended stance:

- keep orchestration in-repo
- use the current packet runner and operator registry
- consider `DSPy` later for optimizing operator prompts or evaluation prompts
- consider `NetworkX` later only if graph traversal and scoring become too complex
- do not start by replacing repo orchestration with LangGraph

## Bottom Line

The conversation's final architecture is coherent.

The repo already has a strong cold-path substrate and a minimal packet-based reasoning shell. Repo research adds one important correction:

The hot path should be owned by a bounded bridge control plane that sits above retrieval and above reply rewriting.

So the next real step is not a rewrite. It is to add a bridge-owned hot-path reasoning runtime with:

- `ContextState`
- `ActiveFieldState`
- routing
- richer operators
- evaluation
- conservative learning

That would let the system move from:

`capture and organize thought`

to:

`help a user process, integrate, and learn from thought in real time`

That is in line with the philosophical framework established in this conversation:

- start symbiotically
- preserve bounded state and source isolation
- learn user-specific transformation habits gradually
- delay deeper subconscious-style resurfacing until the fast runtime is correct
