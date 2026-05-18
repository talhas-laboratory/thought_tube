#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.conversation_os.cli import repo_root_from
from src.conversation_os.worldbuilding_studio import orchestrate_three_state_showcase


def main() -> int:
    root = repo_root_from()
    result = orchestrate_three_state_showcase(
        Path(root),
        "world-daylight-architecture-trial-b6c969e8df86",
    )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
