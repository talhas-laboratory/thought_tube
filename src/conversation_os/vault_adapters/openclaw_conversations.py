from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from ..vault_ingest import ingest_source_file


MODULE_ID = "assembly.adapters.openclaw_conversations"
CONTRACT_VERSION = "1.0"
PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "SUPPORTED_SUFFIXES",
    "ingest_openclaw_directory",
)
__all__ = list(PUBLIC_API)


SUPPORTED_SUFFIXES = {".md", ".txt", ".json"}


def ingest_openclaw_directory(root: Path, source_dir: Path) -> Dict:
    files: List[Path] = []
    for path in sorted(source_dir.rglob("*")):
        if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES:
            files.append(path)

    ingested = []
    for path in files:
        result = ingest_source_file(root, path, source_type="openclaw_conversation")
        ingested.append({"path": str(path), "source_id": result["source_id"], "seeded_count": result["seeded_count"]})
    return {"source_dir": str(source_dir), "file_count": len(files), "ingested": ingested}
