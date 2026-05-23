# Runtime Rebuild Runbook

Use this sequence when the Inner World runtime needs a clean rebuild after schema, pipeline, or synthesis changes.

## Clean rebuild

1. Back up the current runtime surface.
2. Reset `product/inner_world_v1/{data,exports,runs}` if a true clean rebuild is required.
3. Run `python3 tools/conversation_os.py inner-world library-sync`.
4. Run `python3 tools/conversation_os.py inner-world derive --resume`.
5. Inspect `python3 tools/conversation_os.py inner-world runtime-status`.

## Targeted recovery

If a rebuild is interrupted:

1. Run `python3 tools/conversation_os.py inner-world runtime-status`.
2. Check the last completed stage and any running or failed stage in the pipeline summary.
3. Restart with `python3 tools/conversation_os.py inner-world derive --resume`.
4. If a specific stage needs to be rerun, use:
   - `python3 tools/conversation_os.py inner-world derive --from-stage <component> --resume`
   - `python3 tools/conversation_os.py inner-world derive --only-stage <component>`
   - add `--force` when a completed stage must be recomputed even if its artifacts still exist

## Notes

- `library-sync` refreshes raw substrate ingestion only. It does not trigger a full derive.
- Resume skips completed stages only when their expected artifact files still exist.
- `--profile` adds detailed timing/counter summaries for the slow abstraction and bubble stages.
