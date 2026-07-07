#!/usr/bin/env python3
"""Batch-import markdown transcripts and rebuild the global MTSF content graph."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from conversation_os.cli import session_import  # noqa: E402
from conversation_os.mtsf_graph import (  # noqa: E402
    load_global_content_graph,
    rebuild_global_content_graph,
    read_graph_events,
)


def _slug_session_id(path: Path) -> str:
    stem = path.stem
    date_match = re.match(r"^(\d{4}-\d{2}-\d{2})", stem)
    if date_match:
        topic = re.sub(r"^\d{4}-\d{2}-\d{2}_?", "", stem)
        topic = re.sub(r"^chatgpt---", "", topic, flags=re.IGNORECASE)
        topic = re.sub(r"[^a-z0-9]+", "-", topic.lower()).strip("-")[:40]
        base = f"brainwalk-{date_match.group(1)}"
        return f"{base}-{topic}" if topic and topic not in base else base
    slug = re.sub(r"[^a-z0-9]+", "-", stem.lower()).strip("-")
    return slug[:64] or "import-batch"


def _title_from_path(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    if text.startswith("---"):
        block = text.split("---", 2)
        if len(block) >= 3:
            for line in block[1].splitlines():
                if line.strip().startswith("title:"):
                    return line.split(":", 1)[1].strip().strip('"')
    return path.stem.replace("_", " ")


def main() -> int:
    parser = argparse.ArgumentParser(description="Batch import uploads into MTSF sessions")
    parser.add_argument(
        "paths",
        nargs="*",
        help="Markdown files or directories (default: Cursor uploads folder if present)",
    )
    parser.add_argument("--domains", default="research,cognition,brainwalk")
    parser.add_argument("--tags", default="brainwalk,import-batch")
    parser.add_argument("--mtsf-mode", default="fast", choices=["fast", "deep", "off"])
    parser.add_argument("--mtsf-llm", default="off", choices=["auto", "agent", "off", "force"])
    parser.add_argument("--skip-existing", action="store_true", default=True)
    parser.add_argument("--no-rebuild-global", action="store_true")
    parser.add_argument(
        "--manifest-path",
        default=str(ROOT / "memory" / "mtsf" / "batch_import_manifest.json"),
    )
    args = parser.parse_args()

    candidates: list[Path] = []
    if args.paths:
        for raw in args.paths:
            path = Path(raw)
            if path.is_dir():
                candidates.extend(sorted(path.glob("*.md")))
            elif path.is_file():
                candidates.append(path)
    else:
        uploads = Path("/home/ubuntu/.cursor/projects/workspace/uploads")
        if uploads.exists():
            candidates = sorted(uploads.glob("*.md"))

    if not candidates:
        print(json.dumps({"error": "no_markdown_files_found", "paths": args.paths}, indent=2))
        return 1

    runs: list[dict] = []
    session_ids: list[str] = []

    for path in candidates:
        session_id = _slug_session_id(path)
        manifest_session = ROOT / "memory" / "sessions" / session_id / "manifest.json"
        if args.skip_existing and manifest_session.exists():
            runs.append(
                {
                    "source_path": str(path),
                    "session_id": session_id,
                    "status": "skipped_existing",
                }
            )
            session_ids.append(session_id)
            continue

        title = _title_from_path(path)
        try:
            result = session_import(
                ROOT,
                argparse.Namespace(
                    source_path=str(path),
                    title=title,
                    session_id=session_id,
                    participants="user,assistant",
                    source_type="imported_transcript",
                    domains=args.domains,
                    tags=args.tags,
                    task_id=None,
                    request=f"Batch import: {title}",
                    task_type="import_batch",
                    mtsf_mode=args.mtsf_mode,
                    mtsf_llm=args.mtsf_llm,
                ),
            )
            ingest = result.get("mtsf_ingest", {})
            graph = ingest.get("graph", {}) if isinstance(ingest, dict) else {}
            runs.append(
                {
                    "source_path": str(path),
                    "session_id": session_id,
                    "title": title,
                    "status": "imported",
                    "entity_count": ingest.get("entity_count"),
                    "relation_count": ingest.get("relation_count"),
                    "node_count": graph.get("node_count"),
                    "validation_ok": ingest.get("validation_ok"),
                }
            )
            session_ids.append(session_id)
        except Exception as exc:  # noqa: BLE001
            runs.append(
                {
                    "source_path": str(path),
                    "session_id": session_id,
                    "title": title,
                    "status": "failed",
                    "error": str(exc),
                }
            )

    rebuild_result: dict = {}
    if not args.no_rebuild_global:
        imported_ids = [row["session_id"] for row in runs if row["status"] in {"imported", "skipped_existing"}]
        rebuild_result = rebuild_global_content_graph(ROOT, session_ids=imported_ids or None)

    global_graph = load_global_content_graph(ROOT)
    alias_edges = sum(len(v) for v in global_graph.get("adjacency", {}).get("alias", {}).values())

    manifest = {
        "batch_id": f"batch-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "imported_at": datetime.now(timezone.utc).isoformat(),
        "mtsf_mode": args.mtsf_mode,
        "runs": runs,
        "session_ids": sorted(set(session_ids)),
        "rebuild": rebuild_result,
        "global_graph_summary": {
            "node_count": len(global_graph.get("nodes", {})),
            "sessions_contributed": len(global_graph.get("sessions_contributed", {})),
            "alias_edge_count": alias_edges,
            "path": str(ROOT / "memory" / "mtsf" / "global_content_graph.json"),
        },
        "recent_graph_events": read_graph_events(ROOT, limit=10),
    }

    manifest_path = Path(args.manifest_path)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    failed = [row for row in runs if row["status"] == "failed"]
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
