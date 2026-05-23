from __future__ import annotations

from pathlib import Path

from ..vault_adapters.openclaw_conversations import ingest_openclaw_directory


MODULE_ID = "assembly.adapters.openclaw_sync"
CONTRACT_VERSION = "1.0"
PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "sync_openclaw_vault",
)
__all__ = list(PUBLIC_API)


def sync_openclaw_vault(root: Path, source_dir: Path) -> dict:
    return ingest_openclaw_directory(root, source_dir)
