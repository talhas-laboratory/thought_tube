# Agent Bridge — Component Readiness

Date: 2026-06-25  
Last verified: 2026-06-25 (local repo + `talha@192.168.0.102` server spot-check)

Related:

- [Summary](00-summary.md)
- [Architecture](01-architecture.md)

---

## Executive summary

| Metric | Assessment |
|--------|------------|
| **Overall readiness** | ~40% — foundation exists, reliable connection not yet possible |
| **Feasible** | Yes |
| **Blockers** | ControlPacket contract, bridge→agent wire, server deploy, path fix, surface integration |
| **Safe to start** | Phase 0 (contract + plumbing) immediately |

**Reliably connectable today:** OpenClaw thought chat + ocean retrieval API on server.  
**Not connectable today:** Agent-powered bridge on any live surface.

---

## Summary matrix

| # | Component | Status | Reliable to connect? |
|---|-----------|--------|---------------------|
| 1 | Bridge spine | Partial | Local only; not on server |
| 2 | Typed state models | Ready | Yes |
| 3 | ControlPacket / ContextPolicy | Not built | **No — blocker** |
| 4 | Knowledge ocean (cold path) | Ready | Yes |
| 5 | Retrieval hot path | Partial | Server yes; local path split |
| 6 | Context assembly | Partial | Core layers yes |
| 7 | Bridge behaviors (modular) | Partial | 4 hardcoded behaviors |
| 8 | OpenClaw agent | Ready | `thought_tube_router` on server |
| 9 | Agent invocation plumbing | Partial | Chat/assist yes; bridge no |
| 10 | Bridge-mode prompt + JSON | Not built | **No — blocker** |
| 11 | Execution plane (agent) | Partial | Thought chat yes; bridge no |
| 12 | Pipeline / operators | Ready | Yes (fallback role) |
| 13 | Learning loop | Partial | `reasoning run` only |
| 14 | Personal interface / bridge_state | Partial | Rewrite tests failing locally |
| 15 | Heuristic fallback | Ready | Yes |
| 16 | Inspectability | Partial | JSONL only |
| 17 | Tests | Partial | 31 heuristic tests; no agent bridge tests |
| 18 | Server deployment | Not ready | Bridge modules missing |
| 19 | Live surface wiring | Not ready | Chat bypasses bridge |
| 20 | Bridge config | Not built | Chat config only |

---

## 1. Bridge spine

**Modules:** `reasoning_bridge.py`, `active_field.py`, `reasoning_router.py`, `reasoning_runtime.py`, `reasoning_evaluator.py`, `reasoning_learning.py`

| Check | Local | Server |
|-------|-------|--------|
| Code present | Yes | **No — all 6 missing** |
| Imports clean | Yes | N/A |
| Tests | 31/31 pass (`test_reasoning_pipeline_runtime.py`) | N/A |
| CLI entry | `reasoning run` | N/A |
| Live surfaces | Not wired | N/A |
| OpenClaw | Not wired | N/A |

**Flow implemented:**

```
classify_turn → get_context_bundle → build_active_field → route_reasoning
  → run_pipeline → evaluate → learn (optional)
```

**Gaps:**

- No agent hook in `classify_turn`
- Not deployed to OpenClaw server container
- Not called from `chat_with_thought` or miniapp

**Verdict:** Built and tested locally as heuristic bridge. **Not ready for production connection.**

---

## 2. Typed state models

**Owner:** `src/conversation_os/models.py`

| Type | Ready | Persisted |
|------|-------|-----------|
| `ReasoningRequest` | Yes | Optional |
| `ContextState` | Yes | `context_states.jsonl` |
| `ActiveFieldState` | Yes | `active_fields.jsonl` |
| `ReasoningResult` | Yes | `reasoning_results.jsonl` |
| `ReasoningLearningEvent` | Yes | `reasoning_learning_events.jsonl` |
| `ControlPacket` | **No** | — |
| `ContextPolicy` | **No** | — |

**Verdict:** State types ready. **Handoff contract not ready.**

---

## 3. ControlPacket / ContextPolicy

**Status:** Not built

- No classes in `models.py`
- No validation layer
- No `control_packets.jsonl` artifact
- Architecture defined in `docs/product-thesis/07-state-dependent-reasoning-architecture.md`

**Impact:** Agent output format undefined. Infrastructure cannot validate or clamp. Execution receives implicit dicts.

**Verdict:** **P0 blocker** for reliable agent bridge.

---

## 4. Knowledge ocean (cold path)

**Owner:** `library_tracker.derive_graph`, `knowledge_layer.build_knowledge_layer`

| Check | Local | Server |
|-------|-------|--------|
| `semantic_capsules.jsonl` | ~108k rows (`runtime/product_state/`) | ~108k rows (`product/`) |
| Full derive DAG | Yes | Yes |
| Resume / lock | Yes | Yes |
| Bubbles, links, meta | Yes | Yes |

**Verdict:** **Ready.** Not a blocker.

---

## 5. Retrieval hot path

**Owner:** `knowledge_layer.build_retrieval_bundle`

| Check | Status |
|-------|--------|
| Scoring + pond anchoring | Ready |
| Link neighbor walk | Ready |
| Alias resolution | Ready |
| Cross-pond mode | Ready |
| Path resolution | **Broken locally** |

**Path issue:**

| Module | Reads from |
|--------|------------|
| `knowledge_layer.py` | `product/inner_world_v1/data/` (hardcoded) |
| `product_inner_world._data_dir()` | `product_runtime_dir()` → prefers `runtime/product_state/` |

**Observed behavior:**

| Environment | `build_retrieval_bundle` without fix |
|-------------|--------------------------------------|
| Local (before partial derive) | 0 capsules |
| Local (after accidental derive to product/) | 8 capsules from 21-row subset |
| Server | Works (~108k capsules in `product/`) |

**Verdict:** Engine ready. **Path unification required** for reliable local dev and unified deploy.

---

## 6. Context assembly

**Owner:** `reasoning_bridge.get_context_bundle`

| Layer | Chat bridge req. | Implemented |
|-------|------------------|-------------|
| Current turn | Yes | Via `ReasoningRequest` |
| Recent conversation | Yes | `session_local` |
| Working context | Yes | `ContextState` fields |
| Session context | Yes | Session events |
| Context bubble / pond | Partial | Via retrieval `anchor_pond` |
| Semantic capsules | Yes | `global_fallback` |
| Meta-layer records | No | Only via capsule summaries |
| Source evidence | Partial | `source_refs`; chunk text only via `thread_packet` |
| Interaction profile | Yes | `user_local` from `bridge_state` |
| Provisional capture | No | Not in bridge path |
| Staleness scoring | No | Not implemented |

**Verdict:** **Partial** — sufficient for v1 agent bridge; not complete vs requirements doc.

---

## 7. Bridge behaviors

**Owner:** `reasoning_bridge.BRIDGE_BEHAVIOR_RULES`

| Check | Status |
|-------|--------|
| 4 behaviors defined | Yes |
| Priority + override routing | Yes |
| Operator bias propagation | Yes |
| Learning confirmation | Yes (`bridge_behavior:{id}` patterns) |
| Loadable spec files | **No** |
| Agent-selectable menu | **No** (heuristic match only) |

**Verdict:** **Partial** — works for v1 if behavior menu passed to agent as fixed JSON list.

---

## 8. OpenClaw agent (`thought_tube_router`)

**Verified on server** (`talha@192.168.0.102`):

| Check | Status |
|-------|--------|
| Agent registered | Yes |
| Model | `moonshot/kimi-k2.5` |
| `runtime.json` agent | `thought_tube_router` |
| `chat_backend` | `openclaw_gateway` |
| `openclaw-miniapps.service` | active |
| Backend :8422 | running |
| Bridge-specific instructions | **Not configured** |

**Also on server:**

- `inner_world_dimension_fast`
- `inner_world_dimension_semantic`
- `inner_world_dimension_judge`

**Verdict:** **Ready** as invocation target. Not configured for bridge mode.

---

## 9. Agent invocation plumbing

| Pattern | Module | Bridge use |
|---------|--------|------------|
| `request_openclaw_reply` | `chat_backends.py` | Execution (future) |
| `_run_bubble_assist` | `context_bubbles.py` | Pattern reference |
| Thought assist | `thought_factory.py` | Pattern reference |
| Dimension classify | `library_tracker.py` | Pattern reference |
| `bridge_controller` | **Missing** | **Needed** |

**Missing:**

- `classify_with_agent(candidates) -> ControlPacket`
- Bridge prompt template
- JSON schema validation + retry
- Timeout → heuristic fallback wiring

**Verdict:** **Partial** — 80% of subprocess pattern exists.

---

## 10. Bridge-mode prompt + JSON contract

**Status:** Not built

No prompt template, no `ControlPacket` parser, no validation tests.

**Reference implementations to copy:**

- `context_bubbles._bubble_assist_prompt` + `_extract_assist_json`
- `library_tracker` dimension classification JSON extraction

**Verdict:** **P0 blocker** (small build, critical path).

---

## 11. Execution plane

| Path | Mechanism | OpenClaw | Bridge |
|------|-----------|----------|--------|
| `chat_with_thought` | `request_openclaw_reply` | Yes | No |
| `reasoning run` | `operators.build_user_response` | No | Yes (heuristic) |
| Target | packet → trimmed bundle → agent | Planned | Planned |

**`compose_openclaw_message`:** Thought-scoped (character, evidence snippets, thread history). Needs sibling for control-packet execution.

**Verdict:** **Partial** — execution via agent proven for chat; not connected to bridge.

---

## 12. Pipeline / operator system

| Check | Status |
|-------|--------|
| 8 pipeline specs in `product/inner_world_v1/pipelines/` | Yes |
| `OPERATOR_REGISTRY` | Yes |
| `run_pipeline` | Yes |
| Bridge behavior branches in operators | Yes |
| Template-only responses (no LLM) | Yes |

**Role in new architecture:** Fallback execution path when agent execution disabled or fails.

**Verdict:** **Ready** as fallback.

---

## 13. Learning loop

| Step | `reasoning run` | Live chat |
|------|-----------------|-----------|
| `record_learning_event` | Yes | No |
| `persist_bridge_behavior_preferences` | Yes | No |
| `bridge_state.json` update | Yes | No |

**Verdict:** **Partial** — loop exists; not end-to-end on surfaces.

---

## 14. Personal interface / bridge_state

**Path:** `product/personal_interface_v1/data/bridge_state.json`

| Check | Status |
|-------|--------|
| Default schema | Yes |
| `behavior_patterns` | Yes |
| Shared with reasoning bridge | Yes |
| Rewrite path | Tests failing locally (`Rewrite backend is not configured`) |

**Verdict:** **Partial** — state file ready; personal interface unstable locally.

---

## 15. Heuristic fallback

**Owner:** Current `classify_turn` + `_match_bridge_behaviors`

| Check | Status |
|-------|--------|
| Turn classification heuristics | Yes |
| Behavior matching | Yes |
| Tested | Yes |
| Suitable as agent fallback | Yes |

**Verdict:** **Ready** — keep when agent fails.

---

## 16. Inspectability

| Artifact | Exists | CLI/UI |
|----------|--------|--------|
| `context_states.jsonl` | Yes | No |
| `active_fields.jsonl` | Yes | No |
| `reasoning_results.jsonl` | Yes | No |
| `context_switch_events.jsonl` | Yes | No |
| `control_packets.jsonl` | **No** | No |
| `reasoning inspect` command | **No** | No |

`active_field.attributes.context_bundle` embeds full bundle (heavy but inspectable in raw JSONL).

**Verdict:** **Partial** — data logged, not operationally accessible.

---

## 17. Tests

| Suite | Result | Coverage |
|-------|--------|----------|
| `test_reasoning_pipeline_runtime.py` | 31/31 pass | Heuristic bridge end-to-end |
| Agent bridge integration | **None** | — |
| ControlPacket validation | **None** | — |
| Path resolution (knowledge_layer) | **None** | `test_runtime_layout` covers layout helper only |
| OpenClaw live agent | Mocked in main suite | Chat backend |
| Server e2e | **None** | — |

**Full suite note:** Last full run 377 passed / 41 failed (~16 min). Failures clustered in personal interface, mobile miniapp, engineering guard, session lifecycle — unrelated to bridge spine tests.

**Verdict:** Heuristic bridge tested; **agent bridge untested.**

---

## 18. Server deployment

**Server:** `talha@192.168.0.102`  
**Repo path:** `/home/talha/.openclaw/workspace/containers/inner-world`

| Item | Status |
|------|--------|
| `chat_backends.py` | Present |
| `reasoning_bridge.py` | **Missing** |
| `active_field.py` | **Missing** |
| `reasoning_router.py` | **Missing** |
| `reasoning_runtime.py` | **Missing** |
| `reasoning_evaluator.py` | **Missing** |
| `reasoning_learning.py` | **Missing** |
| Ocean data | Present |
| `thought_tube_router` | Present |
| Backend process | Running |
| `deploy_inner_world_to_openclaw.py` syncs `src/` | Yes — server mirror stale |

**Verdict:** **Not ready** — server has chat-era code, not bridge-era code.

---

## 19. Live surface wiring

| Surface | Bridge | OpenClaw | Ocean |
|---------|--------|----------|-------|
| `reasoning run` CLI | Heuristic | No | When paths align |
| `chat_with_thought` | No | Yes | Via thread_packet |
| Miniapp `/retrieval-bundle` | No | No | Direct query |
| Miniapp chat | No | Via chat | Indirect |
| Mobile surface | No | Partial | Partial |
| GPT bridge :8093 | No | No | Repo search only |

**Verdict:** **Not ready** — surfaces do not converge on one bridge entrypoint.

---

## 20. Configuration

**Current `product/inner_world_v1/config/runtime.json`:**

```json
{
  "chat_backend": "openclaw_gateway",
  "openclaw": {
    "agent": "thought_tube_router",
    "thinking": "low",
    "timeout_seconds": 60
  },
  "model_roles": { "... dimension agents ..." }
}
```

**Missing bridge config:**

- `bridge.enabled`
- `bridge.agent`
- `bridge.fallback`
- `bridge.timeout_seconds`
- `bridge.behavior_specs_dir`
- `bridge.execution_mode` (`agent` | `operators`)

**Verdict:** Chat config ready; **bridge config not defined.**

---

## What is connectable today (no new code)

```
Server OpenClaw
  → thought_tube_router
  → chat_with_thought (thread_packet from meta/chunks)
  → GET /retrieval-bundle (ocean query, no bridge)
```

---

## Build order (recommended)

| Priority | Work | Unblocks |
|----------|------|----------|
| **P0** | `ControlPacket` + `ContextPolicy` in `models.py` | Agent contract |
| **P0** | `knowledge_layer` paths → `product_runtime_dir()` | Reliable retrieval |
| **P0** | `bridge_controller.py` | Agent intelligence |
| **P0** | `bridge` section in `runtime.json` | Configuration |
| **P1** | Wire `classify_turn` → agent + fallback | Bridge live locally |
| **P1** | Persist `control_packets.jsonl` | Inspectability |
| **P1** | Deploy reasoning modules to server | Server parity |
| **P1** | Agent bridge tests (mocked) | Reliability |
| **P2** | Execution: packet → `request_openclaw_reply` | Full two-plane loop |
| **P2** | Wire `chat_with_thought` through bridge | Live surfaces |
| **P2** | `reasoning inspect` CLI | Operations |
| **P3** | Behavior spec files | Modularity |
| **P3** | Live feedback → learning on surfaces | Closed loop |

---

## Readiness by phase

| Phase | Ready? | Notes |
|-------|--------|-------|
| Phase 0 — Contract + plumbing | **Can start now** | Models, path fix, bridge_controller, config |
| Phase 1 — Bridge intelligence local | **After P0** | Heuristic fallback already exists |
| Phase 2 — Execution connection | **After P1** | Reuse chat_backends pattern |
| Phase 3 — Surfaces + server | **After P1–P2** | Deploy + wire chat |
| Phase 4 — Modularity | **After P3 stable** | Behavior spec files |

---

## Verification commands

### Local

```bash
# Bridge spine tests
pytest tests/test_reasoning_pipeline_runtime.py -q

# Retrieval path check
PYTHONPATH=src python3 -c "
from pathlib import Path
from conversation_os.knowledge_layer import load_semantic_capsules
from conversation_os.runtime_layout import product_runtime_dir
root = Path('.')
print('canonical:', product_runtime_dir(root, 'inner_world_v1', 'data'))
print('kl_capsules:', len(load_semantic_capsules(root)))
"

# Bridge + ocean connection
PYTHONPATH=src python3 -c "
from pathlib import Path
from conversation_os.reasoning_bridge import classify_turn, get_context_bundle
root = Path('.')
ctx = classify_turn(root, {'request_id':'t','session_id':'','raw_text':'bridge test','caller_hints':{},'domain_hints':[],'source_refs':[]})
ctx['depth_mode'] = 'contextual'
cb = get_context_bundle(root, ctx)
print('layers:', cb['context_state']['bundle_layers'])
print('global_count:', cb['global_fallback']['count'])
"
```

### Server

```bash
ssh talha@192.168.0.102 '
  python3 -c "import json; c=json.load(open(\"/home/talha/.openclaw/openclaw.json\")); print([a[\"id\"] for a in c[\"agents\"][\"list\"]])"
  wc -l /home/talha/.openclaw/workspace/containers/inner-world/product/inner_world_v1/data/semantic_capsules.jsonl
  for f in reasoning_bridge.py reasoning_runtime.py; do
    test -f /home/talha/.openclaw/workspace/containers/inner-world/src/conversation_os/$f && echo OK:$f || echo MISSING:$f
  done
'
```

---

## Changelog

| Date | Change |
|------|--------|
| 2026-06-25 | Initial readiness assessment from repo + server spot-check |
