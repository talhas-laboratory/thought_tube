from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List


def load_plugin(root: Path, plugin_id: str) -> Dict:
    plugin_dir = root / "plugins" / plugin_id
    return json.loads((plugin_dir / "plugin.json").read_text(encoding="utf-8"))


def load_plugins(root: Path, plugin_ids: List[str] | None = None) -> List[Dict]:
    plugins_root = root / "plugins"
    if plugin_ids:
        discovered: List[Dict] = []
        for plugin_id in plugin_ids:
            plugin_dir = plugins_root / plugin_id
            if not plugin_dir.is_dir() or plugin_id.startswith("."):
                continue
            discovered.append(load_plugin(root, plugin_id))
        return discovered

    discovered = []
    for plugin_dir in sorted(plugins_root.iterdir()):
        if not plugin_dir.is_dir() or plugin_dir.name.startswith("."):
            continue
        discovered.append(load_plugin(root, plugin_dir.name))
    return discovered
