# Element Contracts

Contracts for the product element layer. Version 1.

## ElementBinding

Binds a bridge session or Holodeck to a product element.

| Field | Type | Required | Description |
|---|---|---|---|
| `element_key` | string | no | Primary element: `frontend`, `backend`, `marketing`, `monetization` |
| `element_keys_secondary` | string[] | no | Additional elements |
| `topology_mode` | string | yes | `spine`, `sidecar`, or `parallel` |
| `holodeck_id` | string | no | Linked Holodeck workspace id |
| `element_method` | string | yes | `none`, `hashtag`, `explicit`, `session`, `holodeck`, `heuristic` |
| `element_confidence` | number | yes | 0.0–1.0 |
| `flags` | string[] | no | Turn flags: `promote`, `ingest`, `deep` |

### Rules

- Explicit hashtag or `element_key` on session start always wins over heuristic inference.
- Session binding persists across turns until overridden by a new explicit hashtag.
- `topology_mode=sidecar` prevents default promotion into the main product spine.

## ElementProposal

Output of the element router before durable promotion. Phase 2+.

| Field | Type | Description |
|---|---|---|
| `primary` | string | Proposed primary element |
| `secondary` | string[] | Secondary elements |
| `confidence` | number | Proposal confidence |
| `method` | string | `explicit`, `session`, `heuristic` |

## ElementCapture

Provisional element-scoped material. Phase 2+.

| Field | Type | Description |
|---|---|---|
| `capture_id` | string | Unique id |
| `element_key` | string | Owning element |
| `status` | string | `provisional`, `promoted`, `rejected` |
| `source_kind` | string | `session_turn`, `ingest`, `holodeck_event` |
| `source_ref` | string | Provenance pointer |
| `raw_text` | string | Preserved source text |
| `thesis` | string | Compressed meaning (optional until promotion) |
| `confidence` | number | Capture confidence |

## ElementPromotion

Durable promotion record. Phase 4+.

| Field | Type | Description |
|---|---|---|
| `promotion_id` | string | Unique id |
| `capture_id` | string | Source capture |
| `element_key` | string | Target element |
| `thesis` | string | Durable thesis |
| `reason` | string | Why promoted |
| `confidence` | number | Promotion confidence |
| `rollback_path` | string | How to demote or correct |

## Integration

- `ElementBinding` informs `PurposeState` and `ContextPolicy` retrieval boundaries.
- `ElementProposal` feeds provisional capture only; not durable memory.
- `ElementPromotion` must pass `PromotionPolicy` and correction gates before ocean indexing.
