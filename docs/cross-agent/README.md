# Cross-Agent Working Space

Foreign coding agents (Codex, ChatGPT, Claude, local agents) can use this repo as a **shared continuity surface** to read Cursor design threads, continue implementation, review work, or plan next steps — without relying on Cursor chat history alone.

## Start here (foreign agent boot)

Read in this order:

1. [`AGENTS.md`](../../AGENTS.md) — required discipline and core commands
2. [`context/substrate/AGENT_OPERATING_BRIEF.md`](../../context/substrate/AGENT_OPERATING_BRIEF.md) — repo orientation
3. **[`docs/workspaces/unified-framework-synthesis/README.md`](../workspaces/unified-framework-synthesis/README.md)** — **full framework workspace** (sources, analyses, continuity)
4. [`docs/continuity/INDEX.md`](../continuity/INDEX.md) — registry of captured Cursor threads
5. **Your thread's task pack** — `docs/task_packs/{task-id}.md`

Then orient on code:

```bash
python3 tools/conversation_os.py repo-overview refresh
python3 tools/conversation_os.py repo-overview lookup --query "your task"
python3 tools/conversation_os.py engineering-guard assess \
  --request "..." --purpose "..." --proposed-paths "..."
```

## Three git-tracked surfaces

| Surface | Path | Purpose |
|---------|------|---------|
| **Continuity index** | `docs/continuity/INDEX.md` | Map threads → transcripts → task packs → PRs |
| **Full transcript** | `docs/continuity/*.md` | Complete chat arc (`# User` / `# Assistant` format) |
| **Task pack** | `docs/task_packs/*.{md,json}` | Curated handoff: decisions, next actions, constraints |

Optional local machine replay (gitignored):

| Surface | Path | Purpose |
|---------|------|---------|
| Event log | `memory/events/{session_id}.jsonl` | Append-only turn replay |
| Session artifacts | `memory/sessions/{session_id}/` | Transcript, MTSF extraction, analysis |

## Active threads

| Thread | Workspace | Task pack | Transcript |
|--------|-----------|-----------|------------|
| **Unified framework synthesis** | [**full workspace**](../workspaces/unified-framework-synthesis/README.md) | `unified-framework-continuity-4f48` | [thread + 8 analyses](../workspaces/unified-framework-synthesis/) |
| **Phase 1 kernel implementation (review)** | [REVIEWER-START](../workboards/unified-metaphysical-foundation/REVIEWER-START.md) | PR [#11](https://github.com/talhas-laboratory/thought_tube/pull/11) | `cursor/metaphysical-kernel-contracts-423a` |
| MTSF activation | — | `mtsf-activation-continuity-4f48` | [cursor-mtsf-activation-thread-2026-07-07.md](../continuity/cursor-mtsf-activation-thread-2026-07-07.md) |

## Capture a new Cursor thread

### 1. Write continuity transcript

Create `docs/continuity/cursor-{slug}-{date}.md`:

```markdown
---
session_id: cursor-{slug}-4f48
task_pack_id: {slug}-continuity-4f48
title: Short thread title
domains: research, structure, product
branches:
  - cursor/{branch-name}
prs:
  - https://github.com/talhas-laboratory/thought_tube/pull/N
captured_at: YYYY-MM-DD
---

# User

...

# Assistant

...
```

Use `# User` and `# Assistant` headings (required for `session import` parser).

### 2. Build task pack

```bash
python3 tools/conversation_os.py task-pack build \
  --task-id {slug}-continuity-4f48 \
  --request "Continue ..." \
  --task-type continuity_handoff \
  --domains research,structure,product
```

Copy or mirror output to `docs/task_packs/` for git tracking.

### 3. Import for machine replay (optional, local)

```bash
python3 tools/conversation_os.py session import \
  --source-path docs/continuity/cursor-{slug}-{date}.md \
  --session-id cursor-{slug}-4f48 \
  --title "..." \
  --task-id {slug}-continuity-4f48 \
  --request "..." \
  --domains research,structure,product \
  --mtsf-mode deep
```

### 4. Update registry

- Add row to `docs/continuity/INDEX.md`
- Add row to this file's **Active threads** table

## What foreign agents should do

| Intent | Read | Then |
|--------|------|------|
| **Continue design** | Transcript + synthesis docs | Propose schema/plan changes only |
| **Implement code** | Task pack + `AGENT_OPERATING_BRIEF` | `engineering-guard` → smallest edit |
| **Review PR** | Task pack + transcript decision register | Compare against agreed next actions |
| **Plan next phase** | `docs/plans/` synthesis docs | Update task pack, not parallel ontology |

## What task packs are (and are not)

Task packs are **curated, capped handoffs** per [`CONTEXT_ROUTING.md`](../../CONTEXT_ROUTING.md):

- They tell you what to build, what was decided, what's open
- They are **not** a dump of the entire repo or entire chat
- For full chat arc, read `docs/continuity/{thread}.md`

## Holodeck (multi-agent feature work)

For bounded feature incubation across agents, use Holodeck workspaces:

```bash
python3 tools/conversation_os.py holodeck task-pack \
  --workspace-id <id> \
  --task-id <id> \
  --request "..."
```

See [`docs/plans/2026-04-26-holodeck-workspace-architecture.md`](../plans/2026-04-26-holodeck-workspace-architecture.md).

## Related docs

- [Unified framework synthesis](../plans/2026-07-10-unified-framework-synthesis.md)
- [Three-framework comparison](../frameworks/THREE_FRAMEWORK_COMPARATIVE_EVALUATION.md)
- [SESSION_PROTOCOL.md](../../SESSION_PROTOCOL.md)
- [CONTEXT_ROUTING.md](../../CONTEXT_ROUTING.md)

## Planned improvements

- Cursor export → continuity markdown normalizer (`tools/normalize_cursor_export.py`)
- Conversation OS MCP for foreign agents (`session_import`, `task_pack_build`, `continuity_index`)
- Auto-mirror `context/task_packs/` → `docs/task_packs/` on close
