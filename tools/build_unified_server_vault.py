#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"

import sys

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from conversation_os.product_inner_world import export_state, generate_daily_batch
from conversation_os.storage import ensure_dir, write_json, write_markdown
from conversation_os.vault_ingest import ingest_text_content


REMOTE_HOST = "talha@192.168.0.102"
TEXT_PATTERNS = ("*.md", "*.markdown", "*.txt")


@dataclass(frozen=True)
class RemoteCorpus:
    corpus_id: str
    source_type: str
    source_family: str
    roots: List[str]


REMOTE_CORPORA = [
    RemoteCorpus(
        corpus_id="thought_tube",
        source_type="thought_tube_seed",
        source_family="thought_tube",
        roots=[
            "/home/talha/.openclaw/workspace/.thought-tube/seeds/active",
            "/home/talha/.openclaw/workspace/.thought-tube/seeds/archive",
            "/home/talha/.openclaw/workspace/.thought-tube/backend/sessions",
            "/home/talha/.openclaw/workspace/containers/thought-tube/knowledge",
            "/home/talha/.openclaw/workspace/containers/thought-tube/legacy_sources",
            "/home/talha/.openclaw/workspace/containers/thought-tube/pipelines_v1/structured_knowledge/docs",
            "/home/talha/.openclaw/workspace/containers/thought-tube/pipelines_v1/pattern_engine/artifacts",
            "/home/talha/.openclaw/workspace/containers/thought-tube/pipelines_v1/review",
            "/home/talha/.openclaw/workspace/containers/thought-tube/session_context",
            "/home/talha/.openclaw/workspace/containers/thought-tube/demo/demo_v1/artifacts/runs",
        ],
    ),
    RemoteCorpus(
        corpus_id="openclaw_conversations",
        source_type="openclaw_conversation",
        source_family="openclaw_conversations",
        roots=[
            "/home/talha/.openclaw/workspace/transcripts",
            "/home/talha/.openclaw/workspace/casts",
            "/home/talha/.openclaw/workspace/brain-vomits/entries",
            "/home/talha/.openclaw/workspace/brain-vomits/inputs/raw-transcripts",
            "/home/talha/.openclaw/workspace/meta-observatory/artifacts/session_packets",
            "/home/talha/.openclaw/workspace/meta-observatory/artifacts/decision_attachments",
            "/home/talha/.openclaw/workspace/meta-observatory/artifacts/session_syntheses",
            "/home/talha/.openclaw/workspace/meta-observatory/artifacts/fragment_observations",
        ],
    ),
    RemoteCorpus(
        corpus_id="chat_converter",
        source_type="chat_converter_conversation",
        source_family="chat_converter",
        roots=[
            "/home/talha/apps/chat_converter/output",
        ],
    ),
]


def now_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")


def slug_path(path: str) -> str:
    return path.strip("/").replace("/", "__")


def run(cmd: List[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, check=True, text=True, capture_output=True)


def rsync_remote_tree(remote_root: str, local_root: Path) -> Dict:
    ensure_dir(local_root)
    cmd = [
        "rsync",
        "-az",
        "--prune-empty-dirs",
        "--include=*/",
    ]
    for pattern in TEXT_PATTERNS:
        cmd.append(f"--include={pattern}")
    cmd.extend(
        [
            "--exclude=*",
            f"{REMOTE_HOST}:{remote_root.rstrip('/')}/",
            f"{str(local_root)}/",
        ]
    )
    result = run(cmd)
    files = [path for path in local_root.rglob("*") if path.is_file()]
    return {
        "remote_root": remote_root,
        "local_root": str(local_root),
        "file_count": len(files),
        "stdout": result.stdout.strip(),
    }


def backup_runtime(product_root: Path) -> Dict[str, str]:
    backups_root = product_root / "backups"
    stamp = now_stamp()
    target = backups_root / f"pre-unified-server-vault-{stamp}"
    ensure_dir(target)
    copied: Dict[str, str] = {}
    for name in ["data", "exports"]:
        source = product_root / name
        if source.exists():
            shutil.copytree(source, target / name)
            copied[name] = str(target / name)
    return copied


def reset_runtime(product_root: Path) -> None:
    for name in ["data", "exports", "runs"]:
        target = product_root / name
        if target.exists():
            shutil.rmtree(target)
    ensure_dir(product_root / "data")
    ensure_dir(product_root / "exports")
    ensure_dir(product_root / "runs")


def ingest_snapshot(vault_root: Path) -> Dict:
    product_root = REPO_ROOT / "product" / "inner_world_v1"
    backup = backup_runtime(product_root)
    reset_runtime(product_root)

    ingested_files: List[Dict] = []
    for corpus in REMOTE_CORPORA:
        for remote_root in corpus.roots:
            local_root = vault_root / "raw" / corpus.corpus_id / slug_path(remote_root)
            if not local_root.exists():
                continue
            for local_path in sorted(path for path in local_root.rglob("*") if path.is_file()):
                relative = local_path.relative_to(local_root).as_posix()
                remote_file = f"{remote_root.rstrip('/')}/{relative}" if relative != "." else remote_root
                content = local_path.read_text(encoding="utf-8", errors="ignore")
                ingest_result = ingest_text_content(
                    REPO_ROOT,
                    title=local_path.stem.replace("-", " ").replace("_", " "),
                    content=content,
                    source_ref=remote_file,
                    source_type=corpus.source_type,
                    source_family=corpus.source_family,
                    metadata={
                        "vault_id": vault_root.name,
                        "corpus_id": corpus.corpus_id,
                        "remote_root": remote_root,
                        "relative_path": relative,
                        "snapshot_path": str(local_path),
                    },
                )
                ingested_files.append(
                    {
                        "corpus_id": corpus.corpus_id,
                        "remote_file": remote_file,
                        "local_path": str(local_path),
                        "seeded_count": ingest_result["seeded_count"],
                    }
                )

    batch = generate_daily_batch(REPO_ROOT, limit=5, domain_overlays=["research", "art", "entrepreneurship"])
    state = export_state(REPO_ROOT)
    return {
        "backup": backup,
        "ingested_files": ingested_files,
        "batch_count": batch["count"],
        "state": {
            "source_count": len(state["source_registry"]),
            "chunk_count": len(state["chunk_index"]),
            "thought_packets": len(state["thought_packets"]),
            "review_queue": len(state["review_queue"]),
            "insight_candidates": len(state["insight_candidates"]) if isinstance(state["insight_candidates"], list) else 0,
        },
    }


def write_vault_summary(vault_root: Path, sync_log: List[Dict], ingest_result: Dict) -> None:
    summary = {
        "vault_id": vault_root.name,
        "built_at": datetime.now(timezone.utc).isoformat(),
        "sync_log": sync_log,
        "ingest_result": ingest_result,
    }
    write_json(vault_root / "manifest.json", summary)

    lines = [
        f"# {vault_root.name}",
        "",
        f"- built_at: {summary['built_at']}",
        f"- synced_roots: {len(sync_log)}",
        f"- ingested_files: {len(ingest_result['ingested_files'])}",
        f"- source_count: {ingest_result['state']['source_count']}",
        f"- chunk_count: {ingest_result['state']['chunk_count']}",
        f"- thought_packets: {ingest_result['state']['thought_packets']}",
        f"- review_queue: {ingest_result['state']['review_queue']}",
        f"- insight_candidates: {ingest_result['state']['insight_candidates']}",
        "",
        "## Corpora",
    ]
    for row in sync_log:
        lines.extend(
            [
                f"- {row['corpus_id']}: {row['remote_root']}",
                f"  - file_count: {row['file_count']}",
                f"  - local_root: {row['local_root']}",
            ]
        )
    write_markdown(vault_root / "SUMMARY.md", "\n".join(lines))


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a unified Inner World vault from remote OpenClaw and Chat Converter corpora.")
    parser.add_argument("--vault-id", default=f"server-unified-vault-{datetime.now().strftime('%Y-%m-%d')}")
    parser.add_argument("--skip-sync", action="store_true")
    args = parser.parse_args()

    vault_root = REPO_ROOT / "vaults" / args.vault_id
    raw_root = vault_root / "raw"
    ensure_dir(raw_root)

    sync_log: List[Dict] = []
    if not args.skip_sync:
        for corpus in REMOTE_CORPORA:
            for remote_root in corpus.roots:
                local_root = raw_root / corpus.corpus_id / slug_path(remote_root)
                record = rsync_remote_tree(remote_root, local_root)
                sync_log.append({"corpus_id": corpus.corpus_id, **record})
    else:
        manifest_path = vault_root / "manifest.json"
        if manifest_path.exists():
            sync_log = json.loads(manifest_path.read_text(encoding="utf-8")).get("sync_log", [])

    ingest_result = ingest_snapshot(vault_root)
    write_vault_summary(vault_root, sync_log, ingest_result)
    print(
        json.dumps(
            {
                "vault_root": str(vault_root),
                "synced_roots": len(sync_log),
                "ingested_files": len(ingest_result["ingested_files"]),
                "state": ingest_result["state"],
                "batch_count": ingest_result["batch_count"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
