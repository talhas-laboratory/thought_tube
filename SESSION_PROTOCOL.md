# SESSION PROTOCOL

## Session lifecycle

### Start

Create a session manifest with:

- title
- participants
- source type
- domains
- started timestamp

### Append

Every meaningful turn becomes an event with:

- actor
- kind
- content
- optional tags
- optional source ref

### Checkpoint

Checkpoint creates:

- ordered transcript
- manifest refresh

Checkpoint is lightweight. It does not create durable cards by itself.

### Close

Closing a session triggers:

- transcript refresh
- session packet
- structure map
- decision attachments
- session synthesis
- memory card candidates
- decision register update
- open question update
- current state refresh
- domain map refresh

### Import parity

Imported transcripts or notes must be normalized into a session and then processed through the same pipeline as live sessions.

## Event kinds

- `request`
- `response`
- `decision`
- `note`
- `artifact`
- `checkpoint`
- `import`
- `feedback`

## Source and derived boundaries

- Source of truth: `memory/events/` and explicit import files
- Derived: `memory/sessions/<session_id>/`, `memory/cards/`, `context/task_packs/`, `product/inner_world_v1/exports/`
