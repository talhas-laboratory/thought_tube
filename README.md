# Thought Tube

Thought Tube is a stripped-down public release of the Conversation OS framework.

This version keeps the framework code, CLI, and tests, while excluding private or generated substrate such as:

- conversation memory and event logs
- context and task-pack outputs
- vault contents and derived knowledge layers
- local product state, exports, and mobile artifacts

## What It Is

Conversation OS treats conversations as durable working material instead of disposable chat. The core loop is:

`session -> events -> checkpoint -> close -> transcript + analysis + materialization`

The repository includes:

- the `conversation_os` Python package in `src/`
- the CLI entrypoint in `tools/conversation_os.py`
- tests for the core workflow
- product-oriented modules such as Inner World and Worldbuilding Studio, but without bundled private data

## Quick Start

Install the package in a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

Initialize an empty local workspace:

```bash
python3 tools/conversation_os.py init
```

Refresh the codebase overview:

```bash
python3 tools/conversation_os.py repo-overview refresh
```

Start a session:

```bash
python3 tools/conversation_os.py session start --title "Example session"
```

## Core Commands

```bash
python3 tools/conversation_os.py init
python3 tools/conversation_os.py session start --title "My session"
python3 tools/conversation_os.py session append --session-id <session_id> --actor user --kind request --content "..."
python3 tools/conversation_os.py session checkpoint --session-id <session_id>
python3 tools/conversation_os.py session close --session-id <session_id>
python3 tools/conversation_os.py task-pack build --task-id <task_id> --request "..."
python3 tools/conversation_os.py repo-overview refresh
python3 tools/conversation_os.py engineering-guard assess --request "..." --purpose "..." --proposed-paths "..."
```

## Repository Shape

- `src/conversation_os/`: framework and product modules
- `tools/`: runnable entrypoints and helper scripts
- `tests/`: regression coverage for the framework

Generated runtime state is intentionally ignored and recreated locally when needed.

## Testing

```bash
pytest
```
