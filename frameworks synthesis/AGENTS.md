# AGENTS

This folder is an append-only framework series.

## Non-negotiable rules

- Never overwrite an existing numbered entry.
- Never rename an existing numbered entry unless the user explicitly asks.
- Never reuse an existing series index.
- Always create a new entry with the next unused index.
- Always update `README.md` and `SERIES_MANIFEST.json` when adding a new entry.

## Required workflow

1. Read `README.md`.
2. Read `SERIES_MANIFEST.json`.
3. Find the highest existing series index.
4. Create a new file with the next unused index.
5. Append the new entry to the manifest.
6. Append the new entry to the README index.

## Explicit prohibition

If the user asks for a revision to an existing entry, create a new successor
entry unless they explicitly say to modify the existing file in place.
