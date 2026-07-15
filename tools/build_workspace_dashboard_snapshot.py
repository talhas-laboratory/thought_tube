#!/usr/bin/env python3
"""Build Workspace OS dashboard snapshot from git projections."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from conversation_os.workspace_dashboard import build_workspace_dashboard_snapshot


def main() -> int:
    parser = argparse.ArgumentParser(description="Build workspace dashboard snapshot JSON")
    parser.add_argument(
        "--output",
        default="product/inner_world_v1/miniapp/workspace-dashboard-snapshot.json",
        help="Output path relative to repo root",
    )
    args = parser.parse_args()
    snapshot = build_workspace_dashboard_snapshot(ROOT)
    output = ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), "workspace_count": snapshot["workspace_count"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
