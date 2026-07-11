#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    skill_script = Path.home() / ".codex" / "skills" / "agent-work-board" / "scripts" / "create_work_board.py"
    if not skill_script.exists():
        print(
            f"Missing skill script: {skill_script}\n"
            "Install the `agent-work-board` skill under ~/.codex/skills first.",
            file=sys.stderr,
        )
        return 1

    command = [sys.executable, str(skill_script), "--root", str(repo_root), *sys.argv[1:]]
    completed = subprocess.run(command, cwd=repo_root)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
