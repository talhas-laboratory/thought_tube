# Sandbox: Metaphysical Thought-Space

**Created:** 2026-07-05  
**Live session:** `session-98b310abc3e0`  
**Source import:** `import-60295cf68ac1`

This sandbox holds everything produced in the chat thread that began with the **"05.07._Latent Space and Transformers"** conversation — framework extraction, schemas, examples, and future experiments.

## Quick links

| What | Where |
|------|-------|
| Framework (canonical) | [`docs/frameworks/metaphysical-thought-space/`](../../docs/frameworks/metaphysical-thought-space/README.md) |
| PR | https://github.com/talhas-laboratory/thought_tube/pull/2 |
| Source conversation | [`sources/manifest.json`](sources/manifest.json) |
| Worked example entity | [`examples/sacred-loneliness.entity.json`](examples/sacred-loneliness.entity.json) |
| Artifact registry | [`artifacts/index.json`](artifacts/index.json) |

## Directory layout

```text
sandbox/2026-07-05-metaphysical-thought-space/
├── README.md              ← you are here
├── manifest.json          ← sandbox contract
├── session.json           ← Conversation OS session binding
├── CHANGELOG.md           ← activity log for this sandbox
├── sources/               ← provenance (imports, uploads)
├── artifacts/             ← stable outputs registry
├── examples/              ← schema instances / demos
├── experiments/           ← probes and drafts (promote when stable)
└── notes/                 ← scratch thinking (non-canonical)
```

## Workflow for this chat

1. Do work inside this sandbox tree (or `docs/frameworks/metaphysical-thought-space/` for canonical framework edits).
2. Register new stable outputs in `artifacts/index.json`.
3. Append session events:
   ```bash
   python3 tools/conversation_os.py session append \
     --session-id session-98b310abc3e0 \
     --actor user --kind request --content "..."
   ```
4. Checkpoint when an artifact boundary is reached:
   ```bash
   python3 tools/conversation_os.py session checkpoint --session-id session-98b310abc3e0
   ```
5. Keep experiments disposable until they earn a place in `artifacts/` or the framework.

## Scope

**In scope:** MTSF modules, ontologies, schemas, mappings, examples, discovery/actualization experiments, Inner World integration notes.

**Out of scope:** Unrelated product surfaces, core capture/routing changes without guard assessment.

## Branch

Active development branch: `cursor/metaphysical-thought-space-framework-4f48`
