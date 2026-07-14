# Agent Rules

**Universal workspace protocol:** [`docs/workspaces/WORKSPACE-AGENT-PROTOCOL.md`](../../workspaces/WORKSPACE-AGENT-PROTOCOL.md)  
**Foundation close-out:** [`LOCAL-AGENT-BOOT.md`](./LOCAL-AGENT-BOOT.md)

- Prefer sparse, high-signal updates over verbose status narratives.
- Keep task packets self-contained enough for another agent to resume.
- Record coordination changes in the **live workspace API** — not by hand-editing task status in git.
- After live mutations, run `python3 tools/workspace_projection_sync.py publish --workspace-id unified-framework-synthesis` before handoff.
- Use append-only `UPDATES.jsonl` for activity history; let sync update `Status:` lines in task files.
- Preserve provenance for imported context and sidecar work.
- Do not mark work done without test or verification evidence recorded in the live service.
- Escalate blockers early with the smallest concrete question.
