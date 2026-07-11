# Handoffs — Mobile Thought Capture

## 2026-06-27 — Phase 1 complete; capture PWA shipped

**Done:**

| Task | Deliverable |
|------|-------------|
| MTC-001 | `/capture` immersive shell in `product/thought_capture_pwa/` |
| MTC-002 | ScrollEngine (`following` \| `detached`) |
| MTC-003 | Presence gating + nudge/shape local composer |
| MTC-004 | GestureZone lens peek on locus unit |
| MTC-005 | Post-send soft affordances |
| MTC-008 | Bridge section adapter (outbound + compose read) |
| MTC-006 | Bridge compose spine — nudge/shape → `run_reasoning` insertions |

**Artifact root:** `product/thought_capture_pwa/` (DEC-005).  
**Legacy:** `product/mobile_surface_v1/` — atlas demo only; do not extend for capture.

**Verification:** `artifacts/2026-06-27-mtc-001-capture-shell.md` + per-task artifacts under `artifacts/`.

**Next:**

1. **MTC-007** — `/develop` route stub + `SemanticBlock`
2. Manual iOS Safari QA — checkboxes in MTC-001 artifact
3. Live compose QA with `INNER_WORLD_BRIDGE_ENABLED=true` + backend on `:8422`

**Dev:**

```bash
cd product/thought_capture_pwa && npm run dev
# http://localhost:5173/capture
```

## 2026-06-27 — Subproject created from conversation bundle

**Done:** Decomposition, spec, contracts, workboard, task queue. Bundle copied to `mobile_artifacts/2026-06-27/`.

**Superseded note:** Original handoff said add `capture-app.tsx` to `mobile_surface_v1`. DEC-005 replaced this with new PWA at `thought_capture_pwa/`.
