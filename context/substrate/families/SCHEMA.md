# Substrate algorithm manifest schema

Source manifests live at `context/substrate/families/{family}/{id}.json` with a paired spec at `{id}.md`.

`python tools/substrate_index.py refresh` generates:

- `context/substrate/AGENT_INDEX.md`
- `context/substrate/browse_map.json`
- `context/substrate/registry.json`
- `context/substrate/families/{family}/INDEX.md`
- `context/substrate/generated/purpose/{id}.md` — **purpose artifact per algorithm**
- `context/substrate/generated/purpose-index.json`

## Required fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Stable algorithm id, e.g. `structure.mtsf.graph` |
| `title` | string | Human title |
| `family` | string | One of: `framing`, `structure`, `governance`, `tension`, `epistemics`, `transfer` |
| `purpose` | string | One paragraph: what this part does and why it exists |
| `extracts` | string[] | What it reads or derives from upstream |
| `depends_on` | string[] | Other algorithm ids or module ids |
| `feeds_into` | string[] | Downstream algorithm ids or pipelines |

## Recommended fields (purpose artifact generation)

| Field | Type | Description |
|-------|------|-------------|
| `code_module` | string | Repo-relative Python path |
| `graph_layer` | string | `T0`–`T4`, `pipeline`, `ontology`, `eval`, or `map` |
| `module_id` | string | Linked `context/substrate/modules/*.json` id |
| `artifacts` | object[] | `{ "name", "path", "purpose" }` session/global outputs |
| `cli_commands` | string[] | Primary CLI invocations |
| `inputs` | string[] | Input shapes (events, drafts, indexes) |
| `outputs` | string[] | Output shapes |
| `when_to_use` | string[] | Agent instructions |
| `do_not` | string[] | Anti-patterns |

The paired `.md` spec is the narrative body; the first paragraph becomes the index preview.
