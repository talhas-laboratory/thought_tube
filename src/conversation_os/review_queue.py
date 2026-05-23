from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from .storage import read_jsonl, write_jsonl


MODULE_ID = "kernel.governance.review_queue"
CONTRACT_VERSION = "1.0"
PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "review_queue_path",
    "promotion_packets_path",
    "load_review_queue",
    "load_promotion_packets",
    "write_review_state",
)
__all__ = list(PUBLIC_API)


def review_queue_path(root: Path) -> Path:
    return root / "product" / "inner_world_v1" / "data" / "review_queue.jsonl"


def promotion_packets_path(root: Path) -> Path:
    return root / "product" / "inner_world_v1" / "data" / "promotion_packets.jsonl"


def load_review_queue(root: Path) -> List[Dict]:
    return read_jsonl(review_queue_path(root))


def load_promotion_packets(root: Path) -> List[Dict]:
    return read_jsonl(promotion_packets_path(root))


def write_review_state(root: Path, review_rows: List[Dict], promotion_rows: List[Dict]) -> None:
    write_jsonl(review_queue_path(root), review_rows)
    write_jsonl(promotion_packets_path(root), promotion_rows)
