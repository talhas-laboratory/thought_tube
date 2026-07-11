#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from conversation_os.thoughtboard_miniapp import serve_thoughtboard_miniapp  # noqa: E402

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the Thoughtboard miniapp server locally.")
    parser.add_argument("--host", default=DEFAULT_HOST, help="Host to bind the server to")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Port to run the server on")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    base_url = f"http://{args.host}:{args.port}"
    print(f"Thoughtboard embed JS: {base_url}/thoughtboard/embed.js")
    print(f"Thoughtboard feed API: {base_url}/api/thoughtboard/feed")
    serve_thoughtboard_miniapp(
        ROOT,
        host=args.host,
        port=args.port,
    )


if __name__ == "__main__":
    main()
