"""Executable Shape population worker loop and CLI entrypoints."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from conversation_os.source_content_store import SourceContentStore
from conversation_os.shape_population.model_gateway import OpenClawModelClient, ShapeModelGateway, StubModelClient
from conversation_os.shape_population.orchestrator import (
    ShapePopulationOrchestrator,
    apply_approved_promotion_live,
    build_post_ingest_hook,
    enqueue_after_ingest,
)
from conversation_os.shape_population.storage import ShapePopulationStore
from conversation_os.storage import repo_root_from

MODULE_ID = "kernel.shape_population.worker"
CONTRACT_VERSION = "1.1.0"
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
        # Production default: a dedicated OpenClaw identity. Tests inject a stub.
        gateway = ShapeModelGateway(
            OpenClawModelClient(cwd=str(root_path)),
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
    controls = worker.store.get_operator_controls()
    if controls.get("paused"):
        return {
            "processed": 0,
            "results": [],
            "lease_owner": lease_owner,
            "paused": True,
            "controls": controls,
        }
    results: list[dict[str, Any]] = []
    for _ in range(max(0, int(limit))):
        if worker.store.get_operator_controls().get("drain") and not results:
            # Drain: do not start claiming once drain is set mid-loop after progress;
            # initial claim_job already returns None when drain is set.
            pass
        outcome = worker.run_once()
        if outcome is None:
            break
        results.append(outcome)
    return {
        "processed": len(results),
        "results": results,
        "lease_owner": lease_owner,
        "controls": worker.store.get_operator_controls(),
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

    status = sub.add_parser("status", help="Inspect worker controls and optional job id")
    status.add_argument("--root", default="")
    status.add_argument("--job-id", default="")

    pause = sub.add_parser("pause", help="Pause claiming new jobs")
    pause.add_argument("--root", default="")
    pause.add_argument("--reason", default="operator_pause")

    resume = sub.add_parser("resume", help="Resume claiming jobs")
    resume.add_argument("--root", default="")
    resume.add_argument("--reason", default="operator_resume")

    drain = sub.add_parser("drain", help="Drain: stop claiming new jobs")
    drain.add_argument("--root", default="")
    drain.add_argument("--reason", default="operator_drain")

    jobs = sub.add_parser("jobs", help="List recent jobs")
    jobs.add_argument("--root", default="")
    jobs.add_argument("--state", default="")
    jobs.add_argument("--limit", type=int, default=20)

    cancel = sub.add_parser("cancel", help="Cancel a job")
    cancel.add_argument("--root", default="")
    cancel.add_argument("--job-id", required=True)
    cancel.add_argument("--reason", default="operator_cancel")

    retry = sub.add_parser("retry", help="Requeue a failed/cancelled/dead-letter job")
    retry.add_argument("--root", default="")
    retry.add_argument("--job-id", required=True)
    retry.add_argument("--reason", default="operator_retry")

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
        payload: dict[str, Any] = {
            "controls": store.get_operator_controls(),
            "hook": "build_post_ingest_hook",
            "live_apply": "apply_approved_promotion_live",
        }
        if args.job_id:
            payload["job"] = store.get_job(args.job_id) or {
                "error": "job_not_found",
                "job_id": args.job_id,
            }
            print(json.dumps(payload, indent=2, sort_keys=True))
            return 0 if payload["job"].get("job_id") else 1
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    if args.command == "pause":
        print(json.dumps(store.pause_worker(reason=args.reason), indent=2, sort_keys=True))
        return 0
    if args.command == "resume":
        print(json.dumps(store.resume_worker(reason=args.reason), indent=2, sort_keys=True))
        return 0
    if args.command == "drain":
        print(json.dumps(store.drain_worker(reason=args.reason), indent=2, sort_keys=True))
        return 0
    if args.command == "jobs":
        print(json.dumps(store.list_jobs(state=args.state, limit=args.limit), indent=2, sort_keys=True))
        return 0
    if args.command == "cancel":
        print(json.dumps(store.cancel_job(args.job_id, reason=args.reason), indent=2, sort_keys=True))
        return 0
    if args.command == "retry":
        print(json.dumps(store.retry_job(args.job_id, reason=args.reason), indent=2, sort_keys=True))
        return 0
    if args.command == "worker":
        outcome = run_worker(root, limit=args.limit, lease_owner=args.lease_owner)
        print(json.dumps(outcome, indent=2, sort_keys=True))
        return 0
    # Keep symbols referenced for operators/docs.
    _ = (build_post_ingest_hook, apply_approved_promotion_live, StubModelClient)
    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
