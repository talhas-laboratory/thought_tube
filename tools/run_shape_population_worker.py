#!/usr/bin/env python3
"""CLI wrapper for the Shape population worker."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from conversation_os.shape_population.worker import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
