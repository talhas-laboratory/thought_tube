# Agent Bridge — Goal and Scope

Date: 2026-06-25

Related:

- [Architecture](01-architecture.md)
- [Component readiness](02-component-readiness.md)
- [State-Dependent Reasoning Architecture](../../product-thesis/07-state-dependent-reasoning-architecture.md)

---

## What we want to do

Build a **reliable bridge layer** that acts as a modular **context assembly and integration** system, with **`thought_tube_router`** (OpenClaw) providing **bridge intelligence** — not answers.

The bridge should:

1. Read each user turn as new evidence
2. Update live state (topic, object scope, goal, tension, posture)
3. Assemble the **smallest useful context bundle** from session, workspace, user profile, and knowledge ocean
4. Emit a strict, inspectable **`ControlPacket`**
5. Hand off to an execution plane (same agent or sibling invocation) that answers **inside** those bounds
6. Evaluate the result and learn conservatively from explicit feedback

The bridge **shapes conditions**. It does not replace the knowledge ocean, bypass budgets, or answer directly in bridge mode.

---

## Core design claim

> Each user turn is new evidence that updates a live state, and that state should determine both the next reasoning transformation and how much context is disclosed.

We are implementing the missing middle of that claim:

`user input → infrastructure prepares candidates → agent classifies/routes → validated control packet → bounded execution → evaluation → learning`

---

## Architectural stance (agreed)

### Bridge = infrastructure + policy + integration

The bridge is **not** primarily a chatbot. It is:

| Function | Owner |
|----------|-------|
| Retrieval mechanics, pond routing, link walk | Code (`knowledge_layer`) |
| Layer assembly, budget enforcement, provenance | Code (`reasoning_bridge`) |
| Behavior menu, policy defaults | Declarative specs + config |
| Turn classification, disclosure judgment, routing | Agent (`thought_tube_router`, bridge mode) |
| User-facing answer | Agent (execution mode) or pipeline fallback |

### Two-plane model (preserved)

| Plane | Role | Implementation |
|-------|------|----------------|
| **Control** | Classify, route, budget, packet | Bridge infrastructure + `thought_tube_router` (bridge mode) |
| **Execution** | Reason, write, synthesize | `thought_tube_router` (execution mode) or template operators (fallback) |

### Hot path vs cold path (preserved)

| Path | When | Must not |
|------|------|----------|
| **Hot** (per turn) | Classify, retrieve small bundle, route, execute | Depend on full graph rebuild |
| **Cold** (batch) | `derive_graph`, meta layer, bubbles, capsules | Run on every message |

The knowledge ocean is a **context source**, not a per-turn compute obligation.

---

## Why `thought_tube_router`

The dedicated OpenClaw agent already exists on the production server:

- Registered in `~/.openclaw/openclaw.json`
- Referenced in `product/inner_world_v1/config/runtime.json`
- Used today for thought chat and bounded semantic assist

We reuse it in a **new invocation mode**:

| Mode | Input | Output |
|------|-------|--------|
| **Bridge** | Turn text + candidate context + behavior menu | `ControlPacket` JSON |
| **Execution** | User message + control packet + trimmed context | Answer prose |

Same agent ID is acceptable for v1 if the prompt and output contract differ strictly. A dedicated `thought_tube_bridge` agent can be split later if roles blur.

---

## What success looks like

### Functional

- A user turn on a live surface flows through bridge before execution
- Agent proposes classification and disclosure; infrastructure validates and enforces caps
- Retrieval hits the knowledge ocean reliably (server and local dev)
- Invalid agent JSON falls back to existing heuristics without user-visible failure
- Every run leaves an inspectable control packet artifact

### Modular / customizable

- Bridge behaviors are loadable specs (not only Python `if/else`)
- Context policies are configurable per surface, depth mode, or caller hints
- New behaviors can be added without rewriting the bridge spine

### Operational

- Bridge modules deployed to OpenClaw server container
- Integration tests cover agent bridge path (mocked + optional live)
- `reasoning inspect` (or equivalent) explains routing decisions

---

## Explicit non-goals (this phase)

- Replacing the cold-path derive pipeline with LLM graph building
- Memory dumping or silent durable promotion from chat
- Making the agent search 108k capsules directly each turn
- Removing heuristic fallback entirely
- MCP-facing bridge tools (until local control packet is stable)

---

## Implementation phases

### Phase 0 — Contract and plumbing (blockers)

1. Add `ControlPacket` and `ContextPolicy` to `models.py`
2. Fix `knowledge_layer` path resolution via `product_runtime_dir()`
3. Add `bridge_controller.py`: prompt, invoke agent, parse JSON, fallback
4. Add `bridge` section to `runtime.json`

### Phase 1 — Bridge intelligence live (local)

1. Wire `classify_turn` → agent with heuristic fallback
2. Emit and persist control packet per `reasoning run`
3. Tests: schema validation, fallback, mocked agent responses

### Phase 2 — Execution connection

1. Second invocation: packet + trimmed context → `request_openclaw_reply`
2. Or: retire template-only `build_user_response` for agent-backed paths
3. End-to-end `reasoning run` with live gateway (optional flag)

### Phase 3 — Surfaces and server

1. Deploy reasoning modules to OpenClaw server mirror
2. Wire `chat_with_thought` through bridge
3. Miniapp / mobile paths use same bridge entrypoint
4. `reasoning inspect` CLI

### Phase 4 — Modularity

1. Behavior spec files under `product/inner_world_v1/config/bridge_behaviors/`
2. Authoring doc + validation CLI
3. Learning loop connected to live feedback surfaces

---

## Key risks and mitigations

| Risk | Mitigation |
|------|------------|
| Agent answers in bridge mode | Prompt: JSON only; validate schema; reject prose |
| Latency per turn | Agent does judgment only; retrieval stays in code; cache candidate bundles |
| Non-deterministic routing | Log packet; user correction → learning events; heuristic fallback |
| Agent bypasses budgets | Infrastructure trims after agent proposes |
| Path split (runtime vs product) | Unify via `product_runtime_dir()` everywhere |
| Server drift | Deploy script must sync `src/conversation_os/reasoning_*` |

---

## One-sentence summary

**Turn the bridge into a modular context assembly platform steered by `thought_tube_router` in bridge mode, with code owning retrieval and policy and the agent owning classification, routing, and disclosure judgment — then hand a strict control packet to execution.**
