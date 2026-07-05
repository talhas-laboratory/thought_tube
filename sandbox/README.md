# Sandbox

Isolated workspaces for focused chat threads. Each sandbox scopes source material, derived artifacts, experiments, and session continuity for one line of work.

## Active sandboxes

| Sandbox | Session | Purpose |
|---------|---------|---------|
| [2026-07-05-metaphysical-thought-space](2026-07-05-metaphysical-thought-space/README.md) | `session-98b310abc3e0` | Latent-space / thought-space framework extraction and follow-on work |

## Rules

1. **Source stays in `sources/`** — imports, uploads, external references (pointers or manifests; not merged with derived output).
2. **Artifacts register in `artifacts/`** — framework docs, schemas, examples, generated outputs.
3. **Experiments stay in `experiments/`** — throwaway probes; promote to `artifacts/` when stable.
4. **Bind to a Conversation OS session** — append meaningful turns; checkpoint at artifact boundaries.
5. **Do not edit raw event logs** — use `session append` / import; derived layers live under `memory/` (gitignored).

## Create a new sandbox

```bash
python3 tools/conversation_os.py session start --title "Your sandbox title"
mkdir -p sandbox/YYYY-MM-DD-your-slug/{sources,artifacts,examples,experiments,notes}
```

Copy `manifest.json` and `session.json` from an existing sandbox as templates.
