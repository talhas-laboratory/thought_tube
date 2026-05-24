#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from conversation_os.miniapp import serve_miniapp  # noqa: E402


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8421
DEFAULT_DOMAINS = ["research", "art", "entrepreneurship"]


def _split_domains(raw_value: str) -> list[str]:
    return [item.strip() for item in raw_value.split(",") if item.strip()]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the Inner World miniapp locally through the existing backend surface.")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--domains", default=",".join(DEFAULT_DOMAINS))
    parser.add_argument("--refresh-on-start", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    domain_overlays = _split_domains(args.domains)
    base_url = f"http://{args.host}:{args.port}"
    print(f"Inner World miniapp: {base_url}/")
    print(f"Inner World mobile surface: {base_url}/mobile/")
    print(f"Inner World API base: {base_url}/api/")
    print(f"Domain overlays: {', '.join(domain_overlays) if domain_overlays else '(none)'}")
    print(f"Refresh on start: {'yes' if args.refresh_on_start else 'no'}")
    serve_miniapp(
        ROOT,
        host=args.host,
        port=args.port,
        domain_overlays=domain_overlays,
        refresh_on_start=args.refresh_on_start,
    )


if __name__ == "__main__":
    main()
