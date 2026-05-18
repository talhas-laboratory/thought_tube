#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from conversation_os.worldbuilding_studio import (  # noqa: E402
    HiggsfieldCliClient,
    _find_higgsfield_cli_binary,
    _first_result_url,
    _supported_higgsfield_param_names,
    compile_scene,
    compile_scene_from_canon,
    get_packet_bundle,
    slugify,
    utc_now,
)


WORLD_ID = "world-daylight-architecture-trial-b6c969e8df86"
DEFAULT_ASPECT_RATIO = "16:9"
DEFAULT_DURATION = 4


@dataclass
class ExperimentSpec:
    experiment_id: str
    scene_key: str
    title: str
    kind: str
    model: str
    duration_seconds: int
    aspect_ratio: str
    scene_text: str
    direct_prompt: str = ""


SCENES = {
    "day_walk": (
        "Daylight scene. The Hermit crosses the pale ceremonial courtyard in daylight, deep indigo robe against pale ivory stone, "
        "compressed monumental towers behind him. He pauses beneath a carved opening, lifts his tired but curious eyes, then continues forward "
        "with slow spiritual focus."
    ),
    "night_threshold": (
        "Nighttime scene. The Hermit moves through a washed-over moonlit sacred courtyard toward a quiet threshold. The architecture is simplified, "
        "painterly, and less detailed, with deep blue sky, hushed stillness, and the same sacred geometry held in reduced nocturnal form."
    ),
    "dream_prayer": (
        "Dream sequence. Close up of The Hermit's face in deep meditation and prayer. His heavy tired features are softened by dusk and dream haze. "
        "He slowly opens his eyes. The camera gently pulls back to reveal The Hermit sitting outside during dusk, surrounded by small books and "
        "ritualistic paintings laid carefully on the floor."
    ),
    "day_to_night": (
        "State transition. The Hermit walks forward through the same sacred route as daylight monumental stone gradually gives way to washed-over night. "
        "The same architecture persists while detail softens, the sky deepens blue, and the threshold becomes moonlit."
    ),
    "night_to_dream": (
        "State transition. The Hermit remains on the same path as moonlit night slips into dream. The scene loses surface detail, blue-white bloom grows, "
        "edges soften, and the sacred courtyard becomes memory-like rather than literal."
    ),
}


EXPERIMENTS: list[ExperimentSpec] = [
    ExperimentSpec(
        experiment_id="exp-01-direct-day",
        scene_key="day_walk",
        title="Direct baseline: daylight walk",
        kind="direct_cli",
        model="cinematic_studio_3_0",
        duration_seconds=DEFAULT_DURATION,
        aspect_ratio=DEFAULT_ASPECT_RATIO,
        scene_text=SCENES["day_walk"],
        direct_prompt=(
            "Wide cinematic shot of an old man in deep indigo robes walking slowly across a pale monumental courtyard in daylight. "
            "Telephoto compression, giant towers and carved arches behind him, quiet spiritual atmosphere. He pauses under a carved opening, "
            "looks up with tired curious eyes, then continues forward. Natural human motion, restrained camera."
        ),
    ),
    ExperimentSpec(
        experiment_id="exp-02-semantic-day",
        scene_key="day_walk",
        title="Semantic prompt compiler: daylight walk",
        kind="semantic_compile",
        model="cinematic_studio_3_0",
        duration_seconds=DEFAULT_DURATION,
        aspect_ratio=DEFAULT_ASPECT_RATIO,
        scene_text=SCENES["day_walk"],
    ),
    ExperimentSpec(
        experiment_id="exp-03-seedance-day",
        scene_key="day_walk",
        title="Semantic canon + Seedance: daylight walk",
        kind="semantic_canon",
        model="seedance_2_0",
        duration_seconds=DEFAULT_DURATION,
        aspect_ratio=DEFAULT_ASPECT_RATIO,
        scene_text=SCENES["day_walk"],
    ),
    ExperimentSpec(
        experiment_id="exp-04-direct-night",
        scene_key="night_threshold",
        title="Direct baseline: night threshold",
        kind="direct_cli",
        model="cinematic_studio_3_0",
        duration_seconds=DEFAULT_DURATION,
        aspect_ratio=DEFAULT_ASPECT_RATIO,
        scene_text=SCENES["night_threshold"],
        direct_prompt=(
            "Wide cinematic shot of an old man in deep indigo robes moving through a washed-over moonlit sacred courtyard at night. "
            "Simplified painterly architecture, deep blue sky, green dome silhouette, quiet threshold ahead. The motion is slow, grounded, and contemplative."
        ),
    ),
    ExperimentSpec(
        experiment_id="exp-05-semantic-night",
        scene_key="night_threshold",
        title="Semantic prompt compiler: night threshold",
        kind="semantic_compile",
        model="cinematic_studio_3_0",
        duration_seconds=DEFAULT_DURATION,
        aspect_ratio=DEFAULT_ASPECT_RATIO,
        scene_text=SCENES["night_threshold"],
    ),
    ExperimentSpec(
        experiment_id="exp-06-seedance-night",
        scene_key="night_threshold",
        title="Semantic canon + Seedance: night threshold",
        kind="semantic_canon",
        model="seedance_2_0",
        duration_seconds=DEFAULT_DURATION,
        aspect_ratio=DEFAULT_ASPECT_RATIO,
        scene_text=SCENES["night_threshold"],
    ),
    ExperimentSpec(
        experiment_id="exp-07-direct-dream",
        scene_key="dream_prayer",
        title="Direct baseline: dream prayer reveal",
        kind="direct_cli",
        model="cinematic_studio_3_0",
        duration_seconds=DEFAULT_DURATION,
        aspect_ratio=DEFAULT_ASPECT_RATIO,
        scene_text=SCENES["dream_prayer"],
        direct_prompt=(
            "Dreamlike close-up of an old hermit in deep blue robes, eyes closed in prayer. He slowly opens his eyes. "
            "The camera gently pulls back to reveal him seated outside at dusk, surrounded by small books and ritual paintings on the floor. "
            "Soft reduced-detail dream atmosphere, blue-white glow, natural stillness."
        ),
    ),
    ExperimentSpec(
        experiment_id="exp-08-semantic-dream",
        scene_key="dream_prayer",
        title="Semantic prompt compiler: dream prayer reveal",
        kind="semantic_compile",
        model="cinematic_studio_3_0",
        duration_seconds=DEFAULT_DURATION,
        aspect_ratio=DEFAULT_ASPECT_RATIO,
        scene_text=SCENES["dream_prayer"],
    ),
    ExperimentSpec(
        experiment_id="exp-09-seedance-dream",
        scene_key="dream_prayer",
        title="Semantic canon + Seedance: dream prayer reveal",
        kind="semantic_canon",
        model="seedance_2_0",
        duration_seconds=DEFAULT_DURATION,
        aspect_ratio=DEFAULT_ASPECT_RATIO,
        scene_text=SCENES["dream_prayer"],
    ),
    ExperimentSpec(
        experiment_id="exp-10-seedance-day-night",
        scene_key="day_to_night",
        title="Semantic canon + Seedance: day to night transition",
        kind="semantic_canon",
        model="seedance_2_0",
        duration_seconds=5,
        aspect_ratio=DEFAULT_ASPECT_RATIO,
        scene_text=SCENES["day_to_night"],
    ),
    ExperimentSpec(
        experiment_id="exp-11-seedance-night-dream",
        scene_key="night_to_dream",
        title="Semantic canon + Seedance: night to dream transition",
        kind="semantic_canon",
        model="seedance_2_0",
        duration_seconds=5,
        aspect_ratio=DEFAULT_ASPECT_RATIO,
        scene_text=SCENES["night_to_dream"],
    ),
]

EXHAUSTION_TAIL: list[ExperimentSpec] = [
    ExperimentSpec(
        experiment_id="tail-seedance-dream",
        scene_key="dream_prayer",
        title="Tail burn: semantic canon + Seedance dream prayer reveal",
        kind="semantic_canon",
        model="seedance_2_0",
        duration_seconds=5,
        aspect_ratio=DEFAULT_ASPECT_RATIO,
        scene_text=SCENES["dream_prayer"],
    ),
    ExperimentSpec(
        experiment_id="tail-seedance-day-night",
        scene_key="day_to_night",
        title="Tail burn: semantic canon + Seedance day to night transition",
        kind="semantic_canon",
        model="seedance_2_0",
        duration_seconds=5,
        aspect_ratio=DEFAULT_ASPECT_RATIO,
        scene_text=SCENES["day_to_night"],
    ),
    ExperimentSpec(
        experiment_id="tail-seedance-night-dream",
        scene_key="night_to_dream",
        title="Tail burn: semantic canon + Seedance night to dream transition",
        kind="semantic_canon",
        model="seedance_2_0",
        duration_seconds=5,
        aspect_ratio=DEFAULT_ASPECT_RATIO,
        scene_text=SCENES["night_to_dream"],
    ),
]


def account_status() -> dict[str, Any]:
    completed = subprocess.run(
        ["higgsfield", "account", "status", "--json"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or completed.stdout.strip() or "Failed to read Higgsfield account status")
    return json.loads(completed.stdout)


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def download_result(url: str, target_path: Path) -> str:
    request = Request(url, headers={"User-Agent": "inner-space-semantic-credit-sweep"})
    with urlopen(request, timeout=120) as response:  # noqa: S310
        target_path.write_bytes(response.read())
    return str(target_path)


def copy_packet_bundle(packet_id: str, target_dir: Path) -> None:
    packet_dir = ROOT / "product" / "inner_world_v1" / "data" / "worldbuilding_studio" / "packets" / packet_id
    if target_dir.exists():
        shutil.rmtree(target_dir)
    shutil.copytree(packet_dir, target_dir)


def submit_job_nowait(
    client: HiggsfieldCliClient,
    *,
    model: str,
    prompt: str,
    params: dict[str, Any],
    medias: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    allowed = _supported_higgsfield_param_names(model)
    filtered = {key: value for key, value in params.items() if key in allowed and value not in {None, ""}}
    with tempfile.TemporaryDirectory(prefix="semantic-credit-sweep-") as tempdir_name:
        tempdir = Path(tempdir_name)
        upload_cache: dict[str, str] = {}
        create_args = [
            "generate",
            "create",
            model,
            "--prompt",
            prompt,
        ]
        for key, value in filtered.items():
            if isinstance(value, (dict, list)):
                continue
            create_args.extend([f"--{key}", str(value).lower() if isinstance(value, bool) else str(value)])
        for media in medias or []:
            value = str(media.get("value", "")).strip()
            if not value:
                continue
            role = str(media.get("role", "image")).strip() or "image"
            if value not in upload_cache:
                upload_cache[value] = client._upload_media_input(value, role, tempdir)  # noqa: SLF001
            create_args.extend([client._media_flag(role), upload_cache[value]])  # noqa: SLF001
        created = client._run_json(create_args)  # noqa: SLF001
    rows = created if isinstance(created, list) else [created]
    first = rows[0] if rows else {}
    job_id = ""
    if isinstance(first, str):
        job_id = first
    elif isinstance(first, dict):
        job_id = str(first.get("id") or first.get("job_id") or "")
    return {
        "status": "submitted" if job_id else "unknown",
        "job_id": job_id,
        "raw_response": created,
    }


def get_job_status(client: HiggsfieldCliClient, job_id: str) -> dict[str, Any]:
    payload = client._run_json(["generate", "get", job_id])  # noqa: SLF001
    rows = payload if isinstance(payload, list) else [payload]
    first = rows[0] if rows else {}
    if not isinstance(first, dict):
        return {"status": "unknown", "raw_response": payload, "result_url": ""}
    return {
        "status": str(first.get("status", "unknown")),
        "raw_response": payload,
        "result_url": str(first.get("result_url", "")).strip(),
    }


def run_direct_cli(client: HiggsfieldCliClient, spec: ExperimentSpec, exp_dir: Path) -> dict[str, Any]:
    write_text(exp_dir / "manual_prompt.txt", spec.direct_prompt)
    response = submit_job_nowait(
        client,
        model=spec.model,
        prompt=spec.direct_prompt,
        params={
        "duration": spec.duration_seconds,
        "aspect_ratio": spec.aspect_ratio,
        "resolution": "720p",
        },
    )
    write_json(exp_dir / "provider_response.json", response)
    return {
        "status": response.get("status"),
        "provider_job_id": response.get("job_id", ""),
        "result_url": "",
        "local_video": "",
        "response": response,
    }


def run_semantic(client: HiggsfieldCliClient, spec: ExperimentSpec, exp_dir: Path) -> dict[str, Any]:
    compile_fn = compile_scene_from_canon if spec.kind == "semantic_canon" else compile_scene
    compiled = compile_fn(
        ROOT,
        WORLD_ID,
        spec.scene_text,
        duration_seconds=spec.duration_seconds,
        aspect_ratio=spec.aspect_ratio,
        model_preference=spec.model,
    )
    packet_id = compiled["packet_id"]
    copy_packet_bundle(packet_id, exp_dir / "packet_bundle")
    write_json(exp_dir / "compile_result.json", compiled)
    bundle = get_packet_bundle(ROOT, packet_id)
    packet = bundle["higgsfield_execution_packet"]
    response = submit_job_nowait(
        client,
        model=packet["resolved_model"],
        prompt=packet["compiled_prompt"],
        params=dict(packet.get("params", {})),
        medias=list(packet.get("medias", [])),
    )
    write_json(exp_dir / "execution_result.json", response)
    return {
        "packet_id": packet_id,
        "compile_result": compiled,
        "execution": response,
        "result_url": "",
        "local_video": "",
    }


def run_one(
    spec: ExperimentSpec,
    run_root: Path,
    manifest: dict[str, Any],
    client: HiggsfieldCliClient,
    *,
    suffix: str = "",
) -> tuple[dict[str, Any], int]:
    before = account_status()
    experiment_id = spec.experiment_id if not suffix else f"{spec.experiment_id}-{suffix}"
    exp_dir = ensure_dir(run_root / experiment_id)
    write_json(
        exp_dir / "spec.json",
        {
            "experiment_id": experiment_id,
            "scene_key": spec.scene_key,
            "title": spec.title,
            "kind": spec.kind,
            "model": spec.model,
            "duration_seconds": spec.duration_seconds,
            "aspect_ratio": spec.aspect_ratio,
            "scene_text": spec.scene_text,
            "direct_prompt": spec.direct_prompt,
        },
    )
    write_text(exp_dir / "scene_text.txt", spec.scene_text)
    try:
        if spec.kind == "direct_cli":
            result = run_direct_cli(client, spec, exp_dir)
        else:
            result = run_semantic(client, spec, exp_dir)
        status = str(result.get("status") or result.get("execution", {}).get("status") or "unknown")
    except Exception as exc:  # noqa: BLE001
        result = {"error": str(exc)}
        status = "failed"
        write_json(exp_dir / "error.json", result)
    after = account_status()
    row = {
        "experiment_id": experiment_id,
        "title": spec.title,
        "kind": spec.kind,
        "model": spec.model,
        "status": status,
        "credits_before": before.get("credits"),
        "credits_after": after.get("credits"),
        "credits_delta": (before.get("credits") or 0) - (after.get("credits") or 0),
        "artifact_dir": str(exp_dir),
        "result": result,
    }
    manifest["experiments"].append(row)
    manifest["credits_current"] = after
    write_json(run_root / "manifest.json", manifest)
    return row, int(after.get("credits") or 0)


def refresh_results(run_root: Path, manifest: dict[str, Any], client: HiggsfieldCliClient) -> None:
    for row in manifest.get("experiments", []):
        provider_job_id = (
            row.get("result", {}).get("provider_job_id")
            or row.get("result", {}).get("execution", {}).get("job_id")
            or row.get("result", {}).get("response", {}).get("job_id")
        )
        if not provider_job_id:
            continue
        status = get_job_status(client, provider_job_id)
        row["polled_status"] = status.get("status")
        row["polled_response"] = status.get("raw_response")
        result_url = status.get("result_url", "")
        if result_url:
            row["result_url"] = result_url
            exp_dir = Path(row["artifact_dir"])
            target = exp_dir / f"{slugify(row['experiment_id'])}.mp4"
            if not target.exists():
                try:
                    download_result(result_url, target)
                    row["local_video"] = str(target)
                except Exception as exc:  # noqa: BLE001
                    row["download_error"] = str(exc)
    write_json(run_root / "manifest.json", manifest)


def main() -> int:
    cli_binary = _find_higgsfield_cli_binary()
    if not cli_binary:
        raise RuntimeError("Higgsfield CLI binary not found")
    client = HiggsfieldCliClient(ROOT, cli_binary)
    started_at = utc_now()
    run_id = f"semantic-credit-sweep-{started_at.replace(':', '').replace('+', 'Z')}"
    run_root = ensure_dir(
        ROOT
        / "product"
        / "inner_world_v1"
        / "data"
        / "worldbuilding_studio"
        / "worlds"
        / WORLD_ID
        / "experiments"
        / run_id
    )
    manifest: dict[str, Any] = {
        "run_id": run_id,
        "world_id": WORLD_ID,
        "started_at": started_at,
        "experiments": [],
        "credits_start": account_status(),
    }
    write_json(run_root / "manifest.json", manifest)

    for spec in EXPERIMENTS:
        row, current_credits = run_one(spec, run_root, manifest, client)
        if current_credits <= 0:
            break

    failed_tail_attempts = 0
    tail_index = 0
    while int(manifest.get("credits_current", {}).get("credits") or 0) > 0 and failed_tail_attempts < 2:
        spec = EXHAUSTION_TAIL[tail_index % len(EXHAUSTION_TAIL)]
        suffix = f"r{tail_index + 1:02d}"
        row, current_credits = run_one(spec, run_root, manifest, client, suffix=suffix)
        tail_index += 1
        delta = int(row.get("credits_delta") or 0)
        status_text = json.dumps(row.get("result", {}), ensure_ascii=False).lower()
        if delta <= 0 and ("insufficient" in status_text or "credit" in status_text or row.get("status") == "failed"):
            failed_tail_attempts += 1
        else:
            failed_tail_attempts = 0
        if current_credits <= 0:
            break

    refresh_results(run_root, manifest, client)
    manifest["finished_at"] = utc_now()
    manifest["credits_end"] = account_status()
    write_json(run_root / "manifest.json", manifest)
    print(json.dumps({"run_root": str(run_root), "manifest": str(run_root / "manifest.json")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
