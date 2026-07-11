# Agent Bridge Implementation Plan

> **For agentic workers:** Use subagent-driven development or executing-plans workflow when implementing this plan. Steps use checkbox syntax for tracking.

**Goal:** Wire `thought_tube_router` (OpenClaw) into the reasoning bridge as control-plane intelligence — classifying turns, selecting bridge behaviors, and emitting validated `ControlPacket` JSON — while code owns retrieval, budgets, provenance, and persistence.

**Architecture:** Preserve the two-plane model. Infrastructure prepares candidate context from session, workspace, user profile, and knowledge ocean. The agent judges classification and disclosure. Execution answers inside the packet. Heuristic bridge remains permanent fallback.

**Tech Stack:** Python 3.11, existing JSON/JSONL storage, dataclasses in `models.py`, `openclaw agent --json` via subprocess, `thought_tube_router` on gateway, deterministic infrastructure first

Related:

- [Summary](00-summary.md)
- [Architecture](01-architecture.md)
- [Component readiness](02-component-readiness.md)
- [Reasoning Pipeline Implementation Plan](../../plans/2026-06-10-reasoning-pipeline-implementation-plan.md)

---

## Scope and sequencing

This plan intentionally does **not** start with:

- replacing cold-path `derive_graph` with LLM graph building
- removing heuristic fallback entirely
- MCP-facing bridge tools
- behavior authoring UI
- full chat-bridge requirements doc layer 1–9 parity in one slice

First implementation target:

- `ControlPacket` and `ContextPolicy` contracts
- unified runtime data paths for retrieval
- `bridge_controller.py` with agent invoke + JSON validation + fallback
- `bridge` config in `runtime.json`
- agent-backed `classify_turn` behind a feature flag
- `ContextPolicy` enforcement inside `get_context_bundle`
- `control_packets.jsonl` persistence
- mocked agent integration tests

Deferred after first reliable slice:

- agent execution plane (second OpenClaw call)
- `chat_with_thought` bridge wiring
- server deploy + live gateway tests
- behavior spec files on disk
- `reasoning inspect` CLI

---

## Testing strategy

The bridge should be tested as a layered protocol, not as one end-to-end feature.

Each layer needs:

- local tests for its own contract
- at least one integration test proving it composes correctly with adjacent layers
- at least one failure-path test proving it degrades correctly

### Test bands

1. **Contract tests**

- owner modules: `src/conversation_os/models.py`
- verifies:
  - `ContextPolicy` and `ControlPacket` required fields
  - `to_dict()` / `from_dict()` round-trip
  - enum coercion and fallback behavior
  - policy clamping
  - `incognito` invariants

2. **Deterministic bridge infrastructure tests**

- owner modules: `reasoning_bridge.py`, `knowledge_layer.py`, `runtime_layout.py`
- verifies:
  - canonical vs legacy runtime path resolution
  - candidate package assembly
  - layer inclusion and exclusion
  - bundle budgets and retrieval caps
  - cross-ocean gating
  - context switch detection
  - runtime artifact persistence

3. **Agent boundary tests**

- owner modules: `bridge_controller.py`
- verifies:
  - valid OpenClaw JSON -> validated `ControlPacket`
  - malformed JSON -> heuristic fallback
  - prose / empty responses rejected
  - timeout and nonzero exit handling
  - unknown behavior ids stripped
  - validation warnings and raw payload capture

4. **Runtime integration tests**

- owner modules: `reasoning_runtime.py`, `reasoning_bridge.py`
- verifies:
  - agent-backed `classify_turn` vs heuristic fallback
  - `control_packets.jsonl` persistence
  - effective `ContextPolicy` enforcement in `get_context_bundle`
  - `incognito` disables retrieval expansion and durable learning
  - route selection remains stable

5. **Live smoke tests**

- scope:
  - opt-in local gateway smoke
  - opt-in server smoke
  - later, thought-chat surface smoke
- purpose:
  - confirm the real OpenClaw path works after mocked tests pass

### Layer-by-layer assertions

Each context layer must have explicit assertions:

- `session_local`
  - recent event cap
  - ordering
  - empty session behavior
- `workspace_local`
  - `workspace_id` / `thought_id` binding
  - no spurious workspace injection
- `user_local`
  - `behavior_patterns` exposure
  - presentation/personalization exposure
- `global_fallback`
  - retrieval count
  - alias hits
  - anchor pond
  - neighbor cap
  - cross-pond inclusion or exclusion
- policy layer
  - allowlist/blocklist behavior across all bundle layers
- learning layer
  - feedback persistence only when policy permits it

### Mocking policy

Keep real:

- JSONL reads and writes
- runtime layout helpers
- retrieval on small fixture corpora
- bundle assembly and policy enforcement

Mock:

- `subprocess.run` for OpenClaw
- gateway reachability
- server deployment and SSH checks

### Fixture strategy

Prefer small, purpose-built fixtures over broad repo snapshots:

- 5-10 semantic capsules
- a few context links including one cross-pond edge
- one session event stream with 8-12 events
- one `bridge_state.json` fixture with a few behavior patterns
- runtime config fixtures for:
  - heuristic mode
  - bridge-enabled mode
  - `incognito`
  - agent execution mode

### Recommended test files

- `tests/test_control_packet_contract.py`
- `tests/test_knowledge_layer_runtime_paths.py`
- `tests/test_bridge_controller.py`
- `tests/test_reasoning_bridge_policy.py`
- `tests/test_reasoning_runtime_agent_bridge.py`
- `tests/test_agent_bridge_live.py`

Do not collapse the entire bridge into one large `tests/test_agent_bridge.py` file unless there is a strong reason. Split tests by owner and contract.

---

## Execution gates

Before any code task starts, run the repo-required guard with the smallest plausible edit surface for that task.

Required preflight:

```bash
python3 tools/conversation_os.py repo-overview refresh
python3 tools/conversation_os.py engineering-guard assess \
  --request "<task-specific request>" \
  --purpose "<concrete user/system effect>" \
  --proposed-paths "<comma-separated task paths>"
```

Rules:

- If the guard is not `ready`, narrow the task before editing code.
- Run `repo-overview refresh` again after adding new modules or manifests.
- Run `repo-overview validate` before handoff.
- Do not expand past declared owner modules if a test failure suggests a wider refactor.

---

## Problem statement

The heuristic bridge spine exists locally and passes tests, but:

1. bridge intelligence is keyword-based, not agent-backed
2. there is no strict `ControlPacket` handoff to execution
3. `knowledge_layer` reads `product/` while canonical ocean lives in `runtime/product_state/` locally
4. bridge modules are not deployed to the OpenClaw server
5. live chat bypasses the bridge and talks to OpenClaw directly
6. `thought_tube_router` exists on the server but has no bridge-mode contract

Target hot path:

`ReasoningRequest → prepare_candidates → agent ControlPacket (or heuristic fallback) → validate/clamp → context bundle → active field → route → execute → evaluate → learn`

---

## Existing owners to preserve

### Do not move bridge logic into

- `meta_layer.py`
- `runtime_pipeline.py`
- `library_tracker.derive_graph` cold path

### Reuse, do not replace

- `reasoning_bridge.py` (extend, do not rewrite from scratch)
- `knowledge_layer.build_retrieval_bundle`
- `chat_backends.request_openclaw_reply` (execution phase)
- `context_bubbles._extract_assist_json` patterns (JSON parse)
- `BRIDGE_BEHAVIOR_RULES` (until spec loader lands)

---

## File map

### New files

- `src/conversation_os/bridge_controller.py`
  - agent bridge invoke, prompt compose, JSON parse, validate, fallback dispatch
- `tests/test_control_packet_contract.py`
  - `ContextPolicy` / `ControlPacket` contract tests
- `tests/test_knowledge_layer_runtime_paths.py`
  - runtime path and retrieval fixture tests
- `tests/test_bridge_controller.py`
  - mocked OpenClaw agent boundary tests
- `tests/test_reasoning_bridge_policy.py`
  - context bundle and policy enforcement tests
- `tests/test_reasoning_runtime_agent_bridge.py`
  - runtime integration and fallback tests
- `tests/test_agent_bridge_live.py`
  - opt-in live gateway and server smoke tests
- `product/inner_world_v1/config/runtime.sample.json` (update)
  - document `bridge` section
- `context/substrate/modules/kernel.reasoning.bridge_controller.json` (optional manifest)

### Modified files

- `src/conversation_os/models.py`
  - add `ContextPolicy`, `ControlPacket`
- `src/conversation_os/knowledge_layer.py`
  - path helpers via `product_runtime_dir()`
- `src/conversation_os/reasoning_bridge.py`
  - `prepare_bridge_candidates()`, agent hook in `classify_turn`, packet persistence path
- `src/conversation_os/reasoning_runtime.py`
  - consume `ControlPacket`, persist `control_packets.jsonl`
- `src/conversation_os/runtime_layout.py`
  - optional shared `inner_world_data_dir(root)` helper if dedup needed
- `product/inner_world_v1/config/runtime.json`
  - add `bridge` section (disabled by default until tests pass)

### Phase 2+ files (later tasks)

- `src/conversation_os/chat_backends.py` — `compose_execution_message()`
- `src/conversation_os/product_inner_world.py` — wire `chat_with_thought` through bridge
- `src/conversation_os/cli.py` — `reasoning inspect`
- `product/inner_world_v1/config/bridge_behaviors/*.json` — declarative specs

---

## Runtime artifact layout

New artifact:

- `product/inner_world_v1/data/reasoning_runtime/control_packets.jsonl`
  - or canonical path via `product_runtime_dir()` when fixed

Each row:

- full `ControlPacket`
- `routing_source`: `agent` | `heuristic` | `hybrid`
- `agent_raw_response` (optional, truncated)
- `validation_warnings` (optional)

Persistence rules:

- `run_reasoning` must persist the validated packet, not only packet-derived `ContextState`
- retain fallback metadata when heuristic mode is used after an agent failure
- preserve truncated raw agent output separately from the validated packet for inspectability
- recommended helpers:
  - `context_state_from_control_packet(packet)`
  - `_control_packets_path(root)`
  - `persist_control_packet(root, packet, metadata)`

---

## Contracts

### `ContextPolicy`

Required fields:

- `mode` — `none`, `recent_local`, `semantic_narrow`, `graph_contextual`, `cross_ocean_exploration`, `evidence_strict`
- `depth_mode` — `focused`, `contextual`, `deep`, `incognito`
- `token_budget` — int
- `include_layers` — list of strings
- `exclude_layers` — list of strings
- `cross_ocean` — bool
- `retrieval_limit` — int
- `neighbor_limit` — int

### `ControlPacket`

Required fields:

- `packet_id`
- `request_id`
- `active_topic`
- `object_scope`
- `object_id`
- `user_goal`
- `reasoning_posture`
- `factual_anchor_level`
- `bridge_behaviors` — list of behavior id strings
- `pipeline_id`
- `context_policy` — `ContextPolicy`
- `steering_constraints` — list of strings
- `confidence` — float 0–1
- `routing_source` — `agent` | `heuristic` | `hybrid`

Optional fields:

- `parent_object_id`
- `dimension_axis`
- `current_tension`
- `answer_shape`
- `attributes`

Validation rules infrastructure must enforce after agent returns:

- clamp `retrieval_limit` / `neighbor_limit` to hard maxima per `depth_mode`
- filter unknown `bridge_behaviors` ids
- reject `incognito` bundles that include learning side effects
- coerce invalid enums to heuristic defaults
- enforce `include_layers` / `exclude_layers` before any execution handoff
- enforce `cross_ocean=false` even when `depth_mode=deep`

Compatibility rule:

- `bridge.enabled=false` should preserve current heuristic behavior semantically
- do not require byte-for-byte equality for ids, timestamps, or JSONL row ordering

---

## Phase 0 — Contract and plumbing

### Task 1: Add `ContextPolicy` and `ControlPacket` dataclasses

**Files:**

- Modify: `src/conversation_os/models.py`
- Create: `tests/test_control_packet_contract.py`

- [ ] **Step 1: Write failing contract tests**

Add tests for:

- `ContextPolicy` required fields and `to_dict()` round-trip
- `ControlPacket` required fields and `to_dict()` round-trip
- JSON-serializable nested `context_policy`
- sane defaults for optional fields
- enum-like string fields preserved literally

- [ ] **Step 2: Implement dataclasses**

Add to `models.py` with `to_dict()` / optional `from_dict()` helpers.

- [ ] **Step 3: Run contract tests**

```bash
pytest tests/test_control_packet_contract.py -v
```

---

### Task 2: Unify knowledge layer data paths

**Files:**

- Modify: `src/conversation_os/knowledge_layer.py`
- Modify: `tests/test_runtime_layout.py`
- Create: `tests/test_knowledge_layer_runtime_paths.py`
- Test: path resolution against canonical `runtime/product_state/`

- [ ] **Step 1: Write failing path test**

Assert `load_semantic_capsules(root)` returns rows when capsules exist only under `runtime/product_state/inner_world_v1/data/`.

- [ ] **Step 2: Replace hardcoded paths**

Change `_capsules_path`, `_nodes_path`, `_edges_path`, `_context_links_path`, `_link_governance_path` to use:

```python
from .runtime_layout import product_runtime_dir

def _data_dir(root: Path) -> Path:
    return product_runtime_dir(root, "inner_world_v1", "data")
```

- [ ] **Step 3: Align `reasoning_bridge._runtime_dir`**

Use same `product_runtime_dir()` helper for `reasoning_runtime/` artifacts.

- [ ] **Step 4: Decide and test write policy**

Document which path new artifacts should be written to when both canonical and legacy paths are absent.

Required decision:

- either pre-create canonical `runtime/product_state/...` directories and write there
- or intentionally retain legacy fallback for writes until a later migration

Do not leave this implicit; `product_runtime_dir()` currently falls back to legacy when canonical does not exist.

- [ ] **Step 5: Run path + retrieval tests**

```bash
pytest tests/test_runtime_layout.py tests/test_knowledge_layer_runtime_paths.py -v
pytest tests/test_reasoning_pipeline_runtime.py -k "context_bundle" -v
```

---

### Task 3: Implement `bridge_controller.py`

**Files:**

- Create: `src/conversation_os/bridge_controller.py`
- Create: `tests/test_bridge_controller.py`

- [ ] **Step 1: Write failing controller tests (mocked subprocess)**

Cover:

- valid agent JSON → `ControlPacket`
- malformed JSON → raises or returns `None` for fallback
- unknown behavior ids stripped
- over-budget policy clamped
- timeout → fallback signal

- [ ] **Step 2: Implement candidate package builder**

```python
def build_bridge_candidate_package(root, request, *, retrieval_bundle, bridge_state, heuristic_preview=None) -> dict
```

- [ ] **Step 3: Implement bridge prompt composer**

Include:

- role: control-plane JSON only
- turn text + session preview
- retrieval candidate summaries (labels, types, scores)
- behavior menu from `BRIDGE_BEHAVIOR_RULES`
- user pattern summary
- JSON schema excerpt

- [ ] **Step 4: Implement `invoke_bridge_agent`**

Mirror `context_bubbles._run_bubble_assist` subprocess pattern:

```bash
openclaw agent --agent <id> --thinking <level> --message <prompt> --json
```

Respect `openclaw_local` vs `openclaw_gateway` from config.

Define the bridge invocation contract explicitly:

- whether bridge calls set `--session-id`
- whether bridge calls ever use `--deliver`
- how bridge config maps onto existing `openclaw` runtime settings
- timeout/failure handling for gateway, local, malformed JSON, and empty JSON

- [ ] **Step 5: Implement `parse_control_packet` + `validate_control_packet`**

Reuse JSON extraction patterns from `context_bubbles._extract_assist_json`.

- [ ] **Step 6: Implement `classify_with_agent`**

Returns `(ControlPacket, metadata)` or `None` on failure.

- [ ] **Step 7: Run controller tests**

```bash
pytest tests/test_bridge_controller.py -v
```

---

### Task 4: Add bridge config to `runtime.json`

**Files:**

- Modify: `product/inner_world_v1/config/runtime.sample.json`
- Modify: `product/inner_world_v1/config/runtime.json` (bridge disabled by default)
- Modify: `src/conversation_os/bridge_controller.py` — config loader
- Modify: `tests/test_bridge_controller.py`

- [ ] **Step 1: Document `bridge` section in sample config**

```json
{
  "bridge": {
    "enabled": false,
    "agent": "thought_tube_router",
    "thinking": "low",
    "timeout_seconds": 25,
    "fallback": "heuristic",
    "emit_heuristic_preview": true
  }
}
```

- [ ] **Step 2: Implement `load_bridge_config(root)`**

Env overrides:

- `INNER_WORLD_BRIDGE_ENABLED`
- `INNER_WORLD_BRIDGE_AGENT`
- `INNER_WORLD_BRIDGE_TIMEOUT`

- [ ] **Step 3: Add config loader test**

```bash
pytest tests/test_bridge_controller.py -k config -v
```

---

### Task 5: Wire agent hook into `classify_turn`

**Files:**

- Modify: `src/conversation_os/reasoning_bridge.py`
- Modify: `src/conversation_os/reasoning_runtime.py`
- Create: `tests/test_reasoning_runtime_agent_bridge.py`
- Test: `tests/test_reasoning_pipeline_runtime.py`

- [ ] **Step 1: Write failing integration tests (mocked agent)**

When `bridge.enabled=true`:

- `classify_turn` returns packet-derived `ContextState`
- `routing_source` recorded
- fallback on agent failure matches current heuristic test expectations

- [ ] **Step 2: Implement `prepare_bridge_candidates`**

Pre-fetch retrieval bundle using active topic heuristic before agent call.

- [ ] **Step 3: Branch in `classify_turn`**

```python
if bridge_config.enabled:
    packet = classify_with_agent(...)
    if packet:
        return context_state_from_control_packet(packet)
return heuristic_classify_turn(...)
```

- [ ] **Step 4: Persist `control_packets.jsonl` in `run_reasoning`**

Persist:

- validated `ControlPacket`
- routing source and fallback reason
- validation warnings
- truncated raw agent payload when present

- [ ] **Step 5: Run integration tests**

```bash
pytest tests/test_reasoning_runtime_agent_bridge.py tests/test_reasoning_pipeline_runtime.py -v
```

---

### Task 6: Apply `ContextPolicy` inside `get_context_bundle`

**Files:**

- Modify: `src/conversation_os/reasoning_bridge.py`
- Modify: `src/conversation_os/reasoning_runtime.py`
- Create: `tests/test_reasoning_bridge_policy.py`
- Modify: `tests/test_reasoning_runtime_agent_bridge.py`
- Test: `tests/test_reasoning_pipeline_runtime.py`

- [ ] **Step 1: Write failing policy enforcement tests**

Cover:

- `include_layers` allowlist excludes undeclared layers
- `exclude_layers` removes blocked layers even if depth defaults would include them
- `cross_ocean=false` disables cross-pond expansion in deep mode
- `retrieval_limit` / `neighbor_limit` clamp to hard maxima
- `incognito` disables global retrieval and leaves no durable learning side effects

- [ ] **Step 2: Apply `context_policy` to bundle assembly**

Use the validated packet policy as the disclosure contract. Depth defaults remain fallback only when no packet policy exists.

- [ ] **Step 3: Guard learning in `run_reasoning`**

If the effective policy is `incognito`, skip `record_learning_event()` and `persist_bridge_behavior_preferences()`.

- [ ] **Step 4: Run policy tests**

```bash
pytest tests/test_reasoning_bridge_policy.py tests/test_reasoning_runtime_agent_bridge.py -k "context_policy or incognito" -v
pytest tests/test_reasoning_pipeline_runtime.py -k "context_bundle or learning" -v
```

---

### Phase 0 validation

```bash
python3 tools/conversation_os.py repo-overview refresh
python3 tools/conversation_os.py repo-overview validate
pytest \
  tests/test_control_packet_contract.py \
  tests/test_knowledge_layer_runtime_paths.py \
  tests/test_bridge_controller.py \
  tests/test_reasoning_bridge_policy.py \
  tests/test_reasoning_runtime_agent_bridge.py \
  tests/test_reasoning_pipeline_runtime.py -v
```

Phase 0 success:

- [ ] `ControlPacket` validates and persists
- [ ] retrieval works from canonical runtime path locally
- [ ] mocked agent path produces packet; failure falls back to heuristic
- [ ] `ContextPolicy` is enforced before any execution handoff
- [ ] `incognito` disables retrieval expansion and durable learning
- [ ] `bridge.enabled=false` preserves current heuristic behavior semantically

---

## Phase 1 — Agent bridge live locally

### Task 7: Optional live gateway smoke test

**Files:**

- Create: `tests/test_agent_bridge_live.py`

- [ ] **Step 1: Add opt-in live test**

Skip unless `INNER_WORLD_BRIDGE_LIVE_TEST=1` and gateway reachable.

- [ ] **Step 2: Run manual smoke**

```bash
INNER_WORLD_BRIDGE_ENABLED=1 \
INNER_WORLD_BRIDGE_LIVE_TEST=1 \
pytest tests/test_agent_bridge_live.py -k live -v
```

- [ ] **Step 3: Run CLI smoke**

```bash
# enable bridge in runtime.json first
python3 tools/conversation_os.py reasoning run \
  --text "How should we connect the bridge to the knowledge ocean?" \
  --session-id bridge-smoke-001
```

---

### Phase 1 validation

- [ ] `reasoning run` works with `bridge.enabled=true` on dev machine
- [ ] `control_packets.jsonl` row written per run
- [ ] heuristic fallback verified by forcing agent timeout in test

---

## Phase 2 — Execution connection

### Task 8: Execution message composer

**Files:**

- Modify: `src/conversation_os/chat_backends.py`
- Modify: `tests/test_reasoning_runtime_agent_bridge.py`

- [ ] **Step 1: Write failing compose tests**

`compose_execution_message(packet, trimmed_bundle, user_text)` includes steering constraints and excludes out-of-policy layers.

- [ ] **Step 2: Implement composer**

Sibling to `compose_openclaw_message`, not a replacement.

- [ ] **Step 3: Implement `trim_context_bundle(bundle, policy)`**

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_reasoning_runtime_agent_bridge.py -k execution_compose -v
```

---

### Task 9: Agent execution path in `run_reasoning`

**Files:**

- Modify: `src/conversation_os/reasoning_runtime.py`
- Modify: `product/inner_world_v1/config/runtime.json` — `bridge.execution_mode`

- [ ] **Step 1: Add `execution_mode` config**

Values: `operators` (default) | `agent`

- [ ] **Step 2: Write failing e2e test (mocked OpenClaw)**

When `execution_mode=agent`, `run_reasoning` calls `request_openclaw_reply` instead of template operators.

- [ ] **Step 3: Implement branch after routing**

- [ ] **Step 4: Run e2e tests**

```bash
pytest tests/test_reasoning_runtime_agent_bridge.py -k end_to_end -v
```

---

### Phase 2 validation

- [ ] Full loop: bridge packet → trimmed context → agent answer → evaluation
- [ ] `execution_mode=operators` still works (no regression)

---

## Phase 3 — Surfaces and server

### Task 10: Deploy bridge modules to OpenClaw server

**Files:**

- Use: `tools/deploy_inner_world_to_openclaw.py`

- [ ] **Step 1: Verify sync includes `src/conversation_os/reasoning_*.py` and `bridge_controller.py`**

- [ ] **Step 2: Deploy to server**

```bash
python3 tools/deploy_inner_world_to_openclaw.py
```

- [ ] **Step 3: Verify on server**

```bash
ssh talha@192.168.0.102 '
  for f in reasoning_bridge.py bridge_controller.py reasoning_runtime.py; do
    test -f /home/talha/.openclaw/workspace/containers/inner-world/src/conversation_os/$f && echo OK:$f || echo MISSING:$f
  done
'
```

- [ ] **Step 4: Enable bridge in server `runtime.json` cautiously**

Start with `bridge.enabled=false` in production until smoke passes.

---

### Task 11: Wire `chat_with_thought` through bridge

**Files:**

- Modify: `src/conversation_os/product_inner_world.py`

- [ ] **Step 1: Write failing test**

`chat_with_thought` invokes bridge entrypoint before OpenClaw execution.

- [ ] **Step 2: Build `ReasoningRequest` from thought thread turn**

Map `thought_id`, `user_message`, session/thread ids into `caller_hints`.

- [ ] **Step 3: Call `run_reasoning` or thin wrapper**

- [ ] **Step 4: Run targeted tests**

```bash
pytest tests/test_conversation_os.py -k "thought_chat or chat_with_thought" -v
```

---

### Task 12: `reasoning inspect` CLI

**Files:**

- Modify: `src/conversation_os/cli.py`

- [ ] **Step 1: Add `reasoning inspect --request-id`**

Print: control packet, context layers, routing_source, retrieval summary.

- [ ] **Step 2: Add CLI test**

```bash
pytest tests/test_reasoning_runtime_agent_bridge.py -k inspect -v
```

---

### Phase 3 validation

- [ ] Server has bridge modules
- [ ] Local and server retrieval both hit ocean
- [ ] Thought chat uses bridge on flag

---

## Phase 4 — Modularity

### Task 13: Behavior spec loader

**Files:**

- Create: `product/inner_world_v1/config/bridge_behaviors/*.json`
- Modify: `src/conversation_os/reasoning_bridge.py`

- [ ] **Step 1: Write failing loader tests**

- [ ] **Step 2: Implement `load_bridge_behavior_specs(root)`**

Fall back to `BRIDGE_BEHAVIOR_RULES` if directory missing.

- [ ] **Step 3: Pass specs to agent candidate package**

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_reasoning_bridge_policy.py -k behavior_specs -v
```

---

### Task 14: Live learning on surfaces

**Files:**

- Modify: `src/conversation_os/product_inner_world.py`
- Modify: feedback handlers in miniapp path

- [ ] **Step 1: Map thought feedback to `ReasoningLearningEvent`**

- [ ] **Step 2: Persist via `record_learning_event` + `persist_bridge_behavior_preferences`**

- [ ] **Step 3: Add tests**

```bash
pytest tests/test_reasoning_runtime_agent_bridge.py -k learning -v
```

---

## Final validation

Before claiming agent bridge ready:

```bash
python3 tools/conversation_os.py repo-overview refresh
python3 tools/conversation_os.py repo-overview validate
pytest \
  tests/test_control_packet_contract.py \
  tests/test_knowledge_layer_runtime_paths.py \
  tests/test_bridge_controller.py \
  tests/test_reasoning_bridge_policy.py \
  tests/test_reasoning_runtime_agent_bridge.py \
  tests/test_reasoning_pipeline_runtime.py -v
```

If `product_inner_world.py` or `chat_backends.py` touched:

```bash
pytest tests/test_conversation_os.py -k "inner_world or openclaw" -v
```

Server smoke (manual):

```bash
ssh talha@192.168.0.102 '
  cd /home/talha/.openclaw/workspace/containers/inner-world
  PYTHONPATH=src python3 tools/conversation_os.py reasoning run \
    --text "bridge server smoke" --session-id bridge-server-smoke-001
'
```

---

## Success criteria

The agent bridge slice is successful if:

- [ ] infrastructure prepares candidates without cold-path derive
- [ ] agent returns valid `ControlPacket` or heuristic fallback activates silently
- [ ] retrieval hits ocean on both local dev and server
- [ ] budgets are enforced after agent proposes policy
- [ ] layer allowlists/blocklists are enforced before execution
- [ ] `incognito` prevents retrieval expansion and durable learning
- [ ] every run persists inspectable `control_packets.jsonl`
- [ ] `bridge.enabled=false` is semantically compatible with current heuristic bridge tests
- [ ] optional: execution mode returns agent answer inside packet constraints

---

## Deferred work

After the slice works:

- separate `thought_tube_bridge` agent in `openclaw.json` if role confusion appears
- MCP bridge tools
- provisional capture candidates in bridge path
- staleness scoring for reused context
- full chat-bridge requirements 9-layer assembly
- incubation / resurfacing slow loop

Do not start there. The control packet must become reliable before surfaces multiply.

---

## Philosophical alignment note

This plan matches the agreed architecture:

- bridge = modular context assembly + integration
- agent = judgment over bounded candidates, not ocean owner
- code = policy, provenance, persistence
- learning = conservative, explicit feedback only
- `thought_tube_router` = existing dedicated agent, new bridge mode

The bridge layer solves turn-time orientation and bounded context.
The control packet solves inspectable handoff.
Execution solves user-visible intelligence inside constraints.
