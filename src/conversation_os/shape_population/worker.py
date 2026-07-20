"""Executable Shape population worker loop and CLI entrypoints."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from conversation_os.source_content_store import SourceContentStore
from conversation_os.shape_population.model_gateway import ShapeModelGateway, StubModelClient
from conversation_os.shape_population.orchestrator import ShapePopulationOrchestrator, enqueue_after_ingest
from conversation_os.shape_population.storage import ShapePopulationStore
from conversation_os.storage import repo_root_from

MODULE_ID = "kernel.shape_population.worker"
CONTRACT_VERSION = "1.0.0"
PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "build_worker",
    "run_worker",
    "main",
)
__all__ = list(PUBLIC_API)


def build_worker(
    root: Path | str,
    *,
    gateway: ShapeModelGateway | None = None,
    lease_owner: str = "shape-population-worker",
    max_attempts: int = 3,
) -> ShapePopulationOrchestrator:
    root_path = Path(root)
    store = ShapePopulationStore(root_path)
    content_store = SourceContentStore(root_path)
    if gateway is None:
        # Production deployments inject a real model client; default is fail-closed stub.
        gateway = ShapeModelGateway(
            StubModelClient([]),
            content_store=content_store,
            store=store,
        )
    else:
        if gateway.content_store is None:
            gateway.content_store = content_store
        if gateway.store is None:
            gateway.store = store
    return ShapePopulationOrchestrator(
        store=store,
        gateway=gateway,
        content_store=content_store,
        vault_root=root_path,
        lease_owner=lease_owner,
        max_attempts=max_attempts,
    )


def run_worker(
    root: Path | str,
    *,
    limit: int = 1,
    gateway: ShapeModelGateway | None = None,
    lease_owner: str = "shape-population-worker",
) -> dict[str, Any]:
    worker = build_worker(root, gateway=gateway, lease_owner=lease_owner)
    results: list[dict[str, Any]] = []
    for _ in range(max(0, int(limit))):
        outcome = worker.run_once()
        if outcome is None:
            break
        results.append(outcome)
    return {
        "processed": len(results),
        "results": results,
        "lease_owner": lease_owner,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Shape population asynchronous worker")
    sub = parser.add_subparsers(dest="command", required=True)

    worker = sub.add_parser("worker", help="Claim and process queued Shape population jobs")
    worker.add_argument("--root", default="", help="Repo/runtime root (defaults to cwd repo root)")
    worker.add_argument("--limit", type=int, default=1)
    worker.add_argument("--lease-owner", default="shape-population-worker")

    enqueue = sub.add_parser("enqueue", help="Enqueue a vault source for Shape population")
    enqueue.add_argument("--root", default="")
    enqueue.add_argument("--source-id", required=True)
    enqueue.add_argument("--evaluate", action="store_true")

    status = sub.add_parser("status", help="Inspect a job by id")
    status.add_argument("--root", default="")
    status.add_argument("--job-id", required=True)

    args = parser.parse_args(argv)
    root = Path(args.root) if args.root else repo_root_from(Path.cwd())
    store = ShapePopulationStore(root)

    if args.command == "enqueue":
        result = enqueue_after_ingest(
            args.source_id,
            store=store,
            vault_root=root,
            evaluate=bool(args.evaluate),
        )
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    if args.command == "status":
        job = store.get_job(args.job_id) if hasattr(store, "get_job") else None
        if job is None and hasattr(store, "_job_from_row"):
            with store._read_conn() as conn:  # noqa: SLF001 - CLI inspection helper
                row = conn.execute(
                    "SELECT * FROM population_jobs WHERE job_id = ?",
                    (args.job_id,),
                ).fetchone()
            job = None if row is None else store._job_from_row(row)  # noqa: SLF001
        print(json.dumps(job or {"error": "job_not_found", "job_id": args.job_id}, indent=2, sort_keys=True))
        return 0 if job is not None else 1
    if args.command == "worker":
        outcome = run_worker(root, limit=args.limit, lease_owner=args.lease_owner)
        print(json.dumps(outcome, indent=2, sort_keys=True))
        return 0
    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
