# Build Packet — Normalization

Read [Implementation Foundations](../../shape-intelligence-population/derived/IMPLEMENTATION_FOUNDATIONS.md) first.

## Owner and interface

Create `src/conversation_os/shape_population/normalization.py` with `normalize_source(request) -> NormalizedSource`. It is invoked by the ingest orchestrator, never by a population agent.

Input: immutable source bytes/text, declared modality, supplied metadata, source locator, ingestion timestamp. Output: source record plus ordered segment records. Preserve raw content reference; normalize structure only.

Required fields: `source_id`, `content_sha256`, `modality`, `metadata`, `normalization_version`, `segments[]`; each segment has `segment_id`, `ordinal`, `char_start`, `char_end`, optional byte offsets, `structure_path`, `text`, and `text_sha256`.

## Rules

- IDs derive from content digest + normalization version + deterministic structure path, never model output.
- Reconstructing segments in order must reproduce the normalized source representation exactly.
- Preserve headings, speaker turns, tables/code blocks, and source metadata. Do not summarize, infer topics, or classify Shapes.
- Unsupported modality, undecodable bytes, and offset ambiguity yield explicit rejection records—never silent repair.

## Fixtures and tests

Create `tests/fixtures/shape_population/normalization/` with: plain text, markdown, transcript, Unicode/combining characters, code/table, malformed encoding, and a large document.

`tests/test_shape_population_normalization.py` must prove: exact reconstruction; repeat-run identical IDs/digests; offset correctness; Unicode preservation; stable structure paths; no semantic fields; explicit malformed-input failure; re-ingest idempotency; redaction provenance retention; large-input segment/budget bounds.

Run: `pytest tests/test_shape_population_normalization.py -q`.
