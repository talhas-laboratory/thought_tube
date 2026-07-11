# Agent Bridge Implementation

Date: 2026-06-25

This folder is the implementation packet for wiring **OpenClaw agent intelligence** into the **reasoning bridge layer** without collapsing the two-plane architecture.

## Documents (read in order)

| # | Document | Purpose |
|---|----------|---------|
| 1 | [00-summary.md](00-summary.md) | What we are building, why, and success criteria |
| 2 | [01-architecture.md](01-architecture.md) | Deep description of each architectural part |
| 3 | [02-component-readiness.md](02-component-readiness.md) | Current status of every component and connection readiness |
| 4 | [03-implementation-plan.md](03-implementation-plan.md) | Checkbox tasks by phase (start here to build) |

## Related canonical docs

- [State-Dependent Reasoning Architecture](../../product-thesis/07-state-dependent-reasoning-architecture.md)
- [Chat Bridge Requirements](../../product-thesis/03-chat-bridge-requirements.md)
- [Reasoning Pipeline Implementation Plan](../../plans/2026-06-10-reasoning-pipeline-implementation-plan.md)
- [Bounded OpenClaw Semantic Assist](../../plans/2026-04-23-bounded-openclaw-semantic-assist-architecture.md)
- [Inner World OpenClaw Server Architecture](../../plans/2026-04-14-inner-world-openclaw-server-architecture.md)
- [Deployment Guide](../../guides/deployment-guide.md)

## Primary code owners (target)

| Concern | Module |
|---------|--------|
| Bridge infrastructure | `src/conversation_os/reasoning_bridge.py` |
| Agent bridge controller (new) | `src/conversation_os/bridge_controller.py` (proposed) |
| Control packet models (new) | `src/conversation_os/models.py` |
| Retrieval / ocean query | `src/conversation_os/knowledge_layer.py` |
| OpenClaw invocation | `src/conversation_os/chat_backends.py` |
| Runtime orchestration | `src/conversation_os/reasoning_runtime.py` |
| Config | `product/inner_world_v1/config/runtime.json` |
| Dedicated agent (server) | `thought_tube_router` in `~/.openclaw/openclaw.json` |

## Status at a glance

**Feasible, not yet reliably connectable.** Foundation exists locally; agent exists on server; contract and wiring are missing.
