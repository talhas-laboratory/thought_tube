from __future__ import annotations

from pathlib import Path

from ..vault_adapters.openclaw_conversations import ingest_openclaw_directory


def sync_openclaw_vault(root: Path, source_dir: Path) -> dict:
    return ingest_openclaw_directory(root, source_dir)
