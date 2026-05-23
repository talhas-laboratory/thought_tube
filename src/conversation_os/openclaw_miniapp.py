from __future__ import annotations

import json
import shutil
from pathlib import Path


MODULE_ID = "surface.inner_world.openclaw_miniapp"
CONTRACT_VERSION = "1.0"
PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "default_bundle_dir",
    "build_openclaw_bundle",
    "install_openclaw_bundle",
)
__all__ = list(PUBLIC_API)


def _miniapp_source_dir(root: Path) -> Path:
    return root / "product" / "inner_world_v1" / "miniapp"


def default_bundle_dir(root: Path, app_id: str = "inner-world") -> Path:
    return root / "product" / "inner_world_v1" / "openclaw_bundle" / app_id


def _runtime_config_js(api_base_url: str) -> str:
    payload = {"apiBaseUrl": api_base_url.rstrip("/") or "/api"}
    return "\n".join(
        [
            "window.INNER_WORLD_CONFIG = Object.assign({}, window.INNER_WORLD_CONFIG || {},",
            f"  {json.dumps(payload, ensure_ascii=False, indent=2)}",
            ");",
            "",
        ]
    )


def build_openclaw_bundle(
    root: Path,
    output_dir: Path | None = None,
    app_id: str = "inner-world",
    title: str = "Inner World",
    description: str = "Private thought feed, article expansion, and scoped self-chat.",
    api_base_url: str = "/apps/api/inner-world",
) -> dict:
    source_dir = _miniapp_source_dir(root)
    destination = output_dir or default_bundle_dir(root, app_id)
    destination.mkdir(parents=True, exist_ok=True)

    copied_files = []
    for source in sorted(source_dir.iterdir()):
        if source.name.startswith("."):
            continue
        target = destination / source.name
        if source.is_dir():
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(source, target)
        else:
            shutil.copy2(source, target)
        copied_files.append(str(target))

    runtime_config = destination / "runtime-config.js"
    runtime_config.write_text(_runtime_config_js(api_base_url), encoding="utf-8")
    copied_files.append(str(runtime_config))

    app_manifest = destination / "app.json"
    app_manifest.write_text(
        json.dumps(
            {
                "id": app_id,
                "title": title,
                "description": description,
                "icon": "🫧",
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    copied_files.append(str(app_manifest))

    readme = destination / "README.md"
    readme.write_text(
        "\n".join(
            [
                f"# {title} OpenClaw Miniapp",
                "",
                "This bundle is meant to be copied into an OpenClaw miniapps root.",
                "",
                "Expected runtime:",
                f"- static app path: `/apps/{app_id}/`",
                f"- API base URL: `{api_base_url.rstrip('/') or '/api'}`",
                "",
                "The frontend stays static; the Inner World Python service provides the API.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    copied_files.append(str(readme))

    return {
        "app_id": app_id,
        "bundle_dir": str(destination),
        "api_base_url": api_base_url.rstrip("/") or "/api",
        "files": copied_files,
    }


def install_openclaw_bundle(
    root: Path,
    apps_root: Path,
    app_id: str = "inner-world",
    api_base_url: str = "/apps/api/inner-world",
) -> dict:
    bundle = build_openclaw_bundle(root, app_id=app_id, api_base_url=api_base_url)
    destination = apps_root / app_id
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(Path(bundle["bundle_dir"]), destination)
    return {
        **bundle,
        "installed_to": str(destination),
    }
