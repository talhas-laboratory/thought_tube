#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from conversation_os.miniapp import build_miniapp_ui_enhancement_assets, inject_miniapp_ui_enhancement  # noqa: E402
from conversation_os.openclaw_miniapp import build_openclaw_bundle, install_openclaw_bundle  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build or install the Inner World OpenClaw miniapp bundle.")
    parser.add_argument("--app-id", default="inner-world")
    parser.add_argument("--api-base-url", default="/apps/api/inner-world")
    parser.add_argument("--output-dir")
    parser.add_argument("--install-to")
    return parser


def _write_enhanced_bundle_assets(bundle_dir: Path) -> None:
    assets = build_miniapp_ui_enhancement_assets()
    index_path = bundle_dir / "index.html"
    if index_path.exists():
        index_path.write_text(inject_miniapp_ui_enhancement(index_path.read_text(encoding="utf-8")), encoding="utf-8")
    for filename, content in assets.items():
        (bundle_dir / filename).write_text(content, encoding="utf-8")


if __name__ == "__main__":
    args = build_parser().parse_args()
    if args.install_to:
        payload = install_openclaw_bundle(
            ROOT,
            apps_root=Path(args.install_to).expanduser().resolve(),
            app_id=args.app_id,
            api_base_url=args.api_base_url,
        )
    else:
        payload = build_openclaw_bundle(
            ROOT,
            output_dir=Path(args.output_dir).expanduser().resolve() if args.output_dir else None,
            app_id=args.app_id,
            api_base_url=args.api_base_url,
        )
    _write_enhanced_bundle_assets(Path(payload.get("installed_to") or payload["bundle_dir"]))
    sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
