# Product Elements

Owner: `talha`  
Created: `2026-06-27`  
Status: `active-v1`

## Purpose

Product elements are the business-facing dimensions of Inner Space work: frontend, backend, marketing, and monetization. They sit **orthogonal** to the eleven semantic operating systems in `SYSTEMS.md`. Elements route sessions, ingests, and Holodecks into bounded semantic spaces without forking the core ontology.

## Elements (v1)

| Key | Label | Holodeck | Status | Primary systems |
|---|---|---|---|---|
| `frontend` | Frontend | `sol-frontend` | active | #10 Surface adapters, #11 Shared workspaces |
| `backend` | Backend | `sol-backend` | active | #4 Capture, #7 Gates, #8 Agent work |
| `marketing` | Marketing | `sol-marketing` | seeded | #6 Lens layer, #11 Shared workspaces |
| `monetization` | Monetization | `sol-monetization` | seeded | #6 Lens layer, #7 Gates |

Machine-readable registry: `product/inner_world_v1/config/product_elements.json`

## Session binding

Bind an element for the duration of a tracked bridge session:

```text
#frontend — mobile capture polish
```

Or start a session with an explicit element:

```bash
python3 tools/bridge_session.py start --session-id <id> --element-key frontend
```

Binding fields on the session record:

- `element_key` — primary product element
- `element_keys_secondary` — additional elements when material spans domains
- `topology_mode` — `spine`, `sidecar`, or `parallel` (`#sidecar` sets sidecar)
- `holodeck_id` — linked Holodeck workspace from the element registry
- `auto_promote_review` — set when `#promote` appears on a turn

## Routing hashtags

| Hashtag | Effect |
|---|---|
| `#frontend` `#backend` `#marketing` `#monetization` | Bind product element |
| `#sidecar` | Topology: isolated exploration |
| `#parallel` | Topology: parallel branch |
| `#promote` | Flag session for promotion review (phase 4) |
| `#ingest` | Flag turn for provisional capture (phase 2) |
| `#deep` | Request deeper global retrieval |

## Artifact roots

Each element lists repo paths that anchor implementation work:

- **Frontend:** `product/mobile_surface_v1/`, miniapp, thoughtboard showcase
- **Backend:** `src/conversation_os/`, bridge tools, runtime config
- **Marketing:** product thesis, plans (GTM and positioning material)
- **Monetization:** (TBD — pricing and packaging docs)

## Holodecks

Each element has a named Holodeck workspace under `memory/workspaces/`:

- `sol-frontend` (**active**, pillars + workboard at `docs/workboards/sol-frontend/`)
- `sol-backend` (paused, seeded)
- `sol-marketing` (paused, seeded)
- `sol-monetization` (paused, seeded)

Element Holodecks start `paused` until actively incubated, then move to `active`.

## Unified ingest (phase 5)

External material routes through `ingest_to_element_space()`:

| Source | Module | Default element routing |
|---|---|---|
| Mobile capture | `append_mobile_capture` | `frontend` via surface hints |
| Thoughtboard paste | `ingest_pasted_conversation` | content heuristic |
| Development idea | `record_development_idea` | dev dimensions → element map |
| Manual / CLI / MCP | `tools/element_ingest.py`, `bridge_ingest_to_element` | explicit or heuristic |

Provisional captures use `capture_trigger=external_ingest` for ingest paths.

## Provisional captures (phase 2)

Turns that match capture triggers are written to:

`product/inner_world_v1/data/element_captures/{element_key}.jsonl`

Triggers:

- `#ingest` or `#promote` on the turn
- build/evaluate goal + bound element + sufficient length/confidence
- explicit decision language (`decide`, `record this`, …)

## Promotion (phase 4)

- `#promote` flags the session for curator review on session end
- MCP: `bridge_review_element_captures` with optional `auto_apply=true`
- Promoted records land in `element_captures/promoted/{element_key}.jsonl`

## Related docs

- `ELEMENT_CONTRACTS.md` — durable contracts for binding, proposal, capture, promotion
- `CONNECTIONS.md` — how elements connect to the semantic OS
- `SYSTEMS.md` — infrastructure systems (not business elements)
