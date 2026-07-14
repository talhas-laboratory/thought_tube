from __future__ import annotations

from pathlib import Path


MODULE_ID = "kernel.foundation.runtime_layout"
CONTRACT_VERSION = "1.0"
PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "product_source_dir",
    "product_config_dir",
    "product_runtime_dir",
    "ensure_product_runtime_dir",
    "product_artifact_dir",
)
__all__ = list(PUBLIC_API)


RUNTIME_FAMILIES = {"data", "runs"}
ARTIFACT_FAMILIES = {"exports", "backups", "portable", "openclaw_bundle"}


def product_source_dir(root: Path, product_name: str) -> Path:
    return root / "product" / product_name


def product_config_dir(root: Path, product_name: str) -> Path:
    return product_source_dir(root, product_name) / "config"


def product_runtime_dir(root: Path, product_name: str, family: str) -> Path:
    if family not in RUNTIME_FAMILIES:
        raise ValueError(f"Unsupported runtime family: {family}")
    canonical = root / "runtime" / "product_state" / product_name / family
    legacy = product_source_dir(root, product_name) / family
    if canonical.exists():
        return canonical
    if legacy.exists():
        return legacy
    return legacy


def ensure_product_runtime_dir(root: Path, product_name: str, family: str) -> Path:
    if family not in RUNTIME_FAMILIES:
        raise ValueError(f"Unsupported runtime family: {family}")
    path = root / "runtime" / "product_state" / product_name / family
    path.mkdir(parents=True, exist_ok=True)
    return path


def product_artifact_dir(root: Path, product_name: str, family: str) -> Path:
    if family not in ARTIFACT_FAMILIES:
        raise ValueError(f"Unsupported artifact family: {family}")
    if family == "backups":
        canonical = root / "artifacts" / "backups" / product_name / family
    else:
        canonical = root / "artifacts" / "exports" / product_name / family
    legacy = product_source_dir(root, product_name) / family
    if canonical.exists():
        return canonical
    if legacy.exists():
        return legacy
    return legacy
