# Cross-Agent Workspace Design

**Date:** 2026-07-10

## Problem

Foreign agents (Codex, ChatGPT, local agents) need to read **full Cursor design threads**, deep analyses, and source framework docs — not only curated task packs.

---

## Solution: three git-tracked surfaces

| Surface | Path |
|---------|------|
| Foreign agent entry | `docs/cross-agent/README.md` |
| **This workspace** | `docs/workspaces/unified-framework-synthesis/` |
| Continuity registry | `docs/continuity/INDEX.md` |

---

## What task packs are not

Curated, capped handoffs per `CONTEXT_ROUTING.md`. For **full arc**, read continuity transcript + workspace analyses.

---

## Holodeck linkage

Holodeck workspace `unified-framework-synthesis-4f48` links same artifacts for machine operations (local `memory/workspaces/`, gitignored). Git-tracked mirror is **this docs workspace**.

---

## Foreign agent boot

```bash
cat docs/cross-agent/README.md
cat docs/workspaces/unified-framework-synthesis/README.md
cat docs/workspaces/unified-framework-synthesis/continuity/thread-transcript.md
```

---

## Planned

- Cursor export normalizer
- Conversation OS MCP
- Auto-sync holodeck derived → `docs/workspaces/.../derived/`
