#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request


DEFAULT_BRIDGE_URL = "https://inner-world-gpt.talhaslaboratory.xyz"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Invoke the Inner World GPT bridge Telegram binding repair endpoint."
    )
    parser.add_argument("--bridge-url", default=os.getenv("INNER_WORLD_GPT_PUBLIC_BASE_URL", DEFAULT_BRIDGE_URL))
    parser.add_argument("--action-key", default=os.getenv("INNER_WORLD_GPT_ACTION_KEY", ""))
    parser.add_argument("--no-restart-gateway", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    action_key = args.action_key.strip()
    if not action_key:
        raise SystemExit("INNER_WORLD_GPT_ACTION_KEY or --action-key is required.")

    payload = json.dumps({"restart_gateway": not args.no_restart_gateway}).encode("utf-8")
    request = urllib.request.Request(
        f"{args.bridge_url.rstrip('/')}/openclaw/telegram-fix",
        data=payload,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "X-Inner-World-Action-Key": action_key,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        print(body)
        raise SystemExit(exc.code) from exc

    print(body)
    result = json.loads(body)
    if not result.get("ok"):
        raise SystemExit("telegram binding fix reported remaining issues")


if __name__ == "__main__":
    main()
