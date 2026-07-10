# SOL Frontend Workboard

Purpose: coordinate frontend element work against binding pillars. Every task, decision, and implementation change in this workspace must trace to `PILLARS.md`.

Board id: `sol-frontend`  
Holodeck: `memory/workspaces/sol-frontend/`  
Element: `frontend`  
Owner: `talha`  
Created: `2026-06-27`  
Status: `active`

## Agent start protocol

1. Read `PILLARS.md` first — it is the decision spine.
2. Read `README.md`, `TASKS.md`, `GATES.md`, `DECISIONS.md`, latest `UPDATES.jsonl`.
3. Claim one task; map it to pillar(s) in the task packet.
4. Record architectural choices in `DECISIONS.md` before relying on them.
5. Attach verification evidence before `review` or `done`.

## Workspace stack

```text
PILLARS.md (decision spine)
  → Holodeck sol-frontend (active incubation)
  → this workboard (coordination)
  → subproject: sol-frontend-mobile-capture (mobile thought capture)
  → artifact roots (`thought_capture_pwa`, mobile_surface_v1 demo, miniapp, thoughtboard)
  → element captures / promotions (frontend semantic space)
```

## Active subproject

**[Mobile Thought Capture](../sol-frontend-mobile-capture/README.md)** — phase 1 complete in `product/thought_capture_pwa/`; phase 2 partial (MTC-006 remaining).

## Scope

**In:**
- `product/mobile_surface_v1/`
- `product/inner_world_v1/miniapp/`
- `product/thoughtboard_v1/`
- Surface adapter contracts and `SurfaceProfile` for frontend
- Frontend Holodeck artifacts and research promotion

**Out:**
- Backend bridge/runtime unless required for a surfaced contract
- Marketing/monetization exploration (sidecar elements only)
- Full Inner World Shell native packaging (pillar 8 — later phase)

## Board shape

- `PILLARS.md` — binding frontend decision pillars
- `TASKS.md` — task index
- `tasks/` — one packet per work item
- `GATES.md` — completion gates (includes pillar check)
- `DECISIONS.md` — decision log
- `UPDATES.jsonl` — append-only activity
- `HANDOFFS.md` — agent transfer notes
- `AGENTS.md` — operating rules
- `artifacts/` — plans, screenshots, research outputs

## Session binding

```text
#frontend — <what you're building>
```

Or:

```bash
python3 tools/bridge_session.py start --session-id <id> --element-key frontend --holodeck-id sol-frontend
```
