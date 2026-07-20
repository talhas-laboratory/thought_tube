#!/usr/bin/env python3
"""Provision least-privilege OpenClaw agents for Shape population roles."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from conversation_os.chat_backends import ensure_bridge_openclaw_agent  # noqa: E402
from conversation_os.storage import ensure_dir, repo_root_from  # noqa: E402

ROLE_AGENTS = (
    "shape_population_proposer",
    "shape_population_critic",
    "shape_population_synthesizer",
    "shape_population_evaluator",
)
WORKER_AGENT = "shape_population_worker"


def _config_dir(root: Path) -> Path:
    return root / "product" / "inner_world_v1" / "config" / "agent_configs"


def provision_shape_population_agents(root: Path, *, workspace: str = "", model: str = "") -> dict:
    config_dir = _config_dir(root)
    ensure_dir(config_dir)
    provisioned = []
    missing = []
    for agent_id in ROLE_AGENTS:
        path = config_dir / f"{agent_id}.json"
        if not path.exists():
            missing.append(agent_id)
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        tools = payload.get("allowed_tools") or []
        forbidden = set(payload.get("forbidden_actions") or [])
        if "apply_promotion" in tools or "approve" in tools:
            raise SystemExit(f"{agent_id} must not allow apply/approve tools")
        if "shell" not in forbidden or "filesystem" not in forbidden:
            raise SystemExit(f"{agent_id} must forbid shell/filesystem")
        provisioned.append(
            {
                "agent_id": agent_id,
                "role": payload.get("role"),
                "allowed_tools": tools,
                "config_path": str(path.relative_to(root)),
                "prompt_version": payload.get("prompt_version"),
            }
        )
    worker = ensure_bridge_openclaw_agent(
        root, agent_id=WORKER_AGENT, model_id=model, workspace=workspace
    )
    return {
        "ok": not missing,
        "provisioned": provisioned,
        "missing": missing,
        "worker": {**worker, "authority": "broad operational; no human approval or canonical apply/rollback"},
        "note": "Role configs govern outputs; the worker identity is live-bound to OpenClaw.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--workspace", default="")
    parser.add_argument("--model", default="")
    args = parser.parse_args()
    root = repo_root_from(ROOT)
    result = provision_shape_population_agents(root, workspace=args.workspace, model=args.model)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"ok={result['ok']} provisioned={len(result['provisioned'])} missing={result['missing']}")
        for row in result["provisioned"]:
            print(f"- {row['agent_id']}: tools={row['allowed_tools']}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
