# Transcript Mirrors

This directory is for low-effort, human-facing copies of session transcripts.

Use the Conversation OS CLI to keep the mirror in sync:

```bash
python3 tools/conversation_os.py session checkpoint --session-id <session_id>
python3 tools/conversation_os.py session transcript --session-id <session_id>
```

The transcript command writes a copy of `memory/sessions/<session_id>/ordered_transcript.md` to:

```bash
docs/transcripts/<session_id>.md
```

If you want the mirror somewhere else, pass `--output <path>`.
