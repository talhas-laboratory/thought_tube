#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess


DEFAULT_REMOTE = "talha@192.168.0.102"
DEFAULT_LOCAL_PORT = 9310
DEFAULT_REMOTE_PORT = 3010


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Open an SSH tunnel to the server-hosted Inner World OpenClaw app.")
    parser.add_argument("--remote", default=DEFAULT_REMOTE)
    parser.add_argument("--local-port", type=int, default=DEFAULT_LOCAL_PORT)
    parser.add_argument("--remote-port", type=int, default=DEFAULT_REMOTE_PORT)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    print(f"Forwarding http://127.0.0.1:{args.local_port}/apps/inner-world/ -> {args.remote}:127.0.0.1:{args.remote_port}")
    print("Keep this process running while you use the server-hosted app from this machine.")
    subprocess.run(
        [
            "ssh",
            "-N",
            "-L",
            f"{args.local_port}:127.0.0.1:{args.remote_port}",
            args.remote,
        ],
        check=True,
    )


if __name__ == "__main__":
    main()
