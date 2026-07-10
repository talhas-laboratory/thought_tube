# Bridge Workspace Binding — Mobile Thought Capture PWA

How the Thought Tube bridge keeps agents inside the **sol-frontend** / **thought_capture_pwa** workspace when building the PWA.

## Short answer

**Yes.** Bind the bridge session to `element_key: frontend`, holodeck `sol-frontend`, and subproject `sol-frontend-mobile-capture`. Every `prepare_turn` then injects workspace scope, artifact roots, and steering constraints into `.thought-tube/latest-steering.md`.

---

## What gets injected each turn

```text
prepare_turn
  → element binding (#frontend or session fields)
  → workspace_binding bundle (holodeck + subproject config)
  → steering_constraints (scope rules)
  → continuity markdown (holodeck goal + artifact roots + SCROLL/MOTION paths)
```

Agents see:

- `primary_artifact_root: product/thought_capture_pwa/`
- `subproject_id: sol-frontend-mobile-capture`
- Pillar / scroll / motion / contract doc paths
- Constraints: stay in scope_in; read SCROLL/MOTION before UI work

---

## Configuration (repo)

| File | Role |
|---|---|
| `product/inner_world_v1/config/runtime.json` | `default_session_binding` for Cursor hooks |
| `product/inner_world_v1/config/workspace_subprojects.json` | PWA subproject doc paths |
| `memory/workspaces/sol-frontend/manifest.json` | Holodeck scope + `active_subproject_id` |
| `src/conversation_os/element_workspace_binding.py` | Binding builder |

### Default binding (Cursor)

```json
"default_session_binding": {
  "element_key": "frontend",
  "holodeck_id": "sol-frontend",
  "subproject_id": "sol-frontend-mobile-capture"
}
```

---

## How to bind a session

### Option A — Automatic (Cursor hook)

On session start, `.cursor/hooks/bridge_session_start.py` reads `default_session_binding` and sets env:

- `THOUGHT_TUBE_ELEMENT_KEY=frontend`
- `THOUGHT_TUBE_HOLODECK_ID=sol-frontend`
- `THOUGHT_TUBE_SUBPROJECT_ID=sol-frontend-mobile-capture`

### Option B — CLI

```bash
python3 tools/bridge_session.py start \
  --session-id 26ef2474-c2bd-4dda-a4b1-7815b6df28cf \
  --element-key frontend \
  --holodeck-id sol-frontend \
  --surface cursor \
  --restart
```

### Option C — Hashtag per turn

```text
#frontend — implement capture shell in thought_capture_pwa
```

Hashtag binds element on that turn and syncs session when active.

---

## Agent obligations when bound

1. Implement PWA only under `product/thought_capture_pwa/`
2. Read `PILLARS.md`, `SCROLL.md`, `MOTION.md` before UI/scroll work
3. Do not extend `mobile_surface_v1` for capture (legacy demo)
4. Honor steering constraints in `latest-steering.md`
5. Record scope expansions in `DECISIONS.md`

---

## Verify binding

```bash
python3 tools/bridge_prepare_turn.py --text "#frontend build capture shell" \
  --session-id <id> --surface cursor --json | jq '.result.steering_markdown'
```

Look for sections: **Workspace binding**, **Active workspace scope**, **Workspace constraints**.

---

## Code path

- `element_workspace_binding.build_workspace_binding_bundle()`
- `bridge_prepare.merge_workspace_binding_into_preview()`
- `element_capture.build_element_context_bundle()` appends binding markdown to continuity
