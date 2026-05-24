#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from textwrap import dedent, indent


ROOT = Path(__file__).resolve().parents[1]
PORTABLE_ROOT = ROOT / "product" / "inner_world_v1" / "portable"
OUTPUT_DIR = PORTABLE_ROOT / "world-studio-master-library"
ZIP_BASENAME = PORTABLE_ROOT / "world-studio-master-library"
WORLD_ID = "world-daylight-architecture-trial-b6c969e8df86"
WORLD_DIR = ROOT / "product" / "inner_world_v1" / "data" / "worldbuilding_studio" / "worlds" / WORLD_ID
PACKETS_DIR = ROOT / "product" / "inner_world_v1" / "data" / "worldbuilding_studio" / "packets"
DATA_ROOT = ROOT / "product" / "inner_world_v1" / "data" / "worldbuilding_studio"
EXPERIMENTS_DIR = WORLD_DIR / "experiments"
SOURCE_FILES = [
    ROOT / "src" / "conversation_os" / "worldbuilding_studio.py",
    ROOT / "src" / "conversation_os" / "cli.py",
    ROOT / "src" / "conversation_os" / "miniapp.py",
    ROOT / "src" / "conversation_os" / "worldbuilding_studio_mcp.py",
    ROOT / "tools" / "build_world_studio_master_library.py",
    ROOT / "tools" / "run_three_state_showcase.py",
    ROOT / "tools" / "build_world_studio_portable_pack.py",
    ROOT / "tools" / "sync_inner_world_ui_to_openclaw.py",
    ROOT / "tools" / "tunnel_inner_world_openclaw.py",
    ROOT / "tools" / "deploy_inner_world_to_openclaw.py",
    ROOT / "tools" / "run_inner_world_backend.py",
    ROOT / "tools" / "run_semantic_credit_sweep.py",
    ROOT / "product" / "inner_world_v1" / "miniapp" / "world-studio.html",
    ROOT / "product" / "inner_world_v1" / "miniapp" / "world-studio.css",
    ROOT / "product" / "inner_world_v1" / "miniapp" / "world-studio.js",
]
GUIDE_FILES = [
    ROOT / "docs" / "guides" / "worldbuilding-studio-agent-workflow.md",
    ROOT / "docs" / "guides" / "worldbuilding-studio-operator-manuscript.md",
    ROOT / "AGENTS.md",
    ROOT / "product" / "inner_world_v1" / "README.md",
]
SELECTED_PACKET_IDS = [
    "world-packet-2d1b657db802",
    "world-packet-6490f301c753",
    "world-packet-d4ff5923835a",
    "world-packet-2c31e9dc86d6",
    "world-packet-4a13aa2df66b",
    "world-packet-14339d2d55e2",
    "world-packet-5230fe06f5c6",
]
EXPERIMENT_MANIFEST_NAMES = [
    "semantic-credit-sweep-2026-05-08T233125Z0000",
    "semantic-credit-sweep-2026-05-08T233355Z0000",
    "semantic-credit-sweep-2026-05-08T233636Z0000",
    "semantic-image-probes-2026-05-08T233907Z",
    "semantic-image-submit-2026-05-08T234032Z",
    "semantic-final-one-credit-2026-05-08T234108Z",
]


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def copy_tree(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(
        src,
        dst,
        ignore=shutil.ignore_patterns(".DS_Store", "*.lock", "__pycache__", "*.pyc"),
    )


def copy_file(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def run_json(cmd: list[str]) -> dict | list | None:
    completed = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        return None
    text = completed.stdout.strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def run_text(cmd: list[str]) -> str:
    completed = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=False)
    return (completed.stdout or completed.stderr).strip()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def sanitize_runtime_config() -> dict:
    config = load_json(ROOT / "product" / "inner_world_v1" / "config" / "runtime.sample.json")
    runtime_path = Path.home() / ".config" / "inner_space" / "world_studio_runtime.json"
    if runtime_path.exists():
        runtime = load_json(runtime_path)
        visual = runtime.get("world_studio", {}).get("visual_embeddings", {})
        if visual:
            config.setdefault("world_studio", {}).setdefault("visual_embeddings", {})
            config["world_studio"]["visual_embeddings"]["model"] = visual.get("model", config["world_studio"]["visual_embeddings"].get("model", ""))
            if config["world_studio"]["visual_embeddings"].get("api_key") is not None:
                config["world_studio"]["visual_embeddings"]["api_key"] = "<REDACTED>"
    return config


def filtered_world_events() -> list[dict]:
    rows = load_jsonl(DATA_ROOT / "events.jsonl")
    return [row for row in rows if row.get("world_id") == WORLD_ID]


def filtered_execution_runs() -> list[dict]:
    return load_jsonl(WORLD_DIR / "executions" / "execution_runs.jsonl")


def experiment_manifest(run_name: str) -> dict:
    path = EXPERIMENTS_DIR / run_name / "manifest.json"
    if not path.exists():
        return {}
    return load_json(path)


def pack_artifact_path(path_str: str | None) -> str:
    if not path_str:
        return ""
    path = Path(path_str)
    try:
        rel = path.relative_to(WORLD_DIR)
        return str(Path("04-artifacts") / "worlds" / WORLD_ID / rel)
    except ValueError:
        try:
            rel = path.relative_to(ROOT)
            return str(rel)
        except ValueError:
            return path_str


def packet_snapshots() -> dict[str, dict]:
    snapshots: dict[str, dict] = {}
    for packet_id in SELECTED_PACKET_IDS:
        packet_dir = PACKETS_DIR / packet_id
        if not packet_dir.exists():
            continue
        snapshots[packet_id] = {
            "context_packet": load_json(packet_dir / "context_packet.json"),
            "higgsfield_execution_packet": load_json(packet_dir / "higgsfield_execution_packet.json"),
            "evaluation": load_json(packet_dir / "evaluation.json"),
        }
    return snapshots


def relative_paths(paths: list[Path], base: Path = ROOT) -> list[str]:
    return [str(path.relative_to(base)) for path in paths]


def build_docs(output: Path) -> None:
    world = load_json(WORLD_DIR / "world.json")
    account_status = run_json(["higgsfield", "account", "status", "--json"]) or {}
    seedance_model = run_json(["higgsfield", "model", "get", "seedance_2_0", "--json"]) or {}
    image_model = run_json(["higgsfield", "model", "get", "cinematic_studio_2_5", "--json"]) or {}
    cinematic_studio_3_model = run_json(["higgsfield", "model", "get", "cinematic_studio_3_0", "--json"]) or {}
    events = filtered_world_events()
    executions = filtered_execution_runs()
    packets = packet_snapshots()
    character_profiles = load_jsonl(WORLD_DIR / "characters" / "character_profiles.jsonl")
    character_features = load_jsonl(WORLD_DIR / "characters" / "character_feature_objects.jsonl")
    motion_objects = load_jsonl(WORLD_DIR / "motion" / "motion_objects.jsonl")
    motion_bindings = load_jsonl(WORLD_DIR / "motion" / "motion_bindings.jsonl")
    experiment_manifests = {name: experiment_manifest(name) for name in EXPERIMENT_MANIFEST_NAMES}
    broken_sweep = experiment_manifests["semantic-credit-sweep-2026-05-08T233125Z0000"]
    intermediate_sweep = experiment_manifests["semantic-credit-sweep-2026-05-08T233355Z0000"]
    clean_sweep = experiment_manifests["semantic-credit-sweep-2026-05-08T233636Z0000"]
    image_probe_manifest = experiment_manifests["semantic-image-probes-2026-05-08T233907Z"]
    image_submit_manifest = experiment_manifests["semantic-image-submit-2026-05-08T234032Z"]
    final_one_credit_manifest = experiment_manifests["semantic-final-one-credit-2026-05-08T234108Z"]
    built_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    showcase_path = WORLD_DIR / "showcases" / "three-state-traversal-showcase.mp4"
    world_files = [path for path in WORLD_DIR.rglob("*") if path.is_file() and ".lock" not in path.name and path.name != ".DS_Store"]
    chronology_lines = []
    for row in events:
        event_type = row.get("event_type", "")
        created = row.get("created_at", "")
        detail = ""
        if row.get("packet_id"):
            detail = f" packet={row['packet_id']}"
        if row.get("execution_id"):
            detail += f" execution={row['execution_id']}"
        if row.get("provider_job_id"):
            detail += f" provider_job={row['provider_job_id']}"
        if row.get("anchor_role"):
            detail += f" anchor={row['anchor_role']}"
        chronology_lines.append(f"- `{created}` `{event_type}`{detail}")
    execution_summary = "\n".join(
        [
            f"- `{row.get('execution_id')}` | packet `{row.get('packet_id')}` | status `{row.get('status')}` | provider job `{row.get('provider_job_id') or 'none'}`"
            for row in executions
        ]
    )
    packet_table = "\n".join(
        [
            f"| `{packet_id}` | `{snapshot['higgsfield_execution_packet'].get('status')}` | `{snapshot['higgsfield_execution_packet'].get('anchor_media_strategy', 'none')}` | `{snapshot['higgsfield_execution_packet'].get('model_preference')}` |"
            for packet_id, snapshot in packets.items()
        ]
    )
    seedance_params = ", ".join(param["name"] for param in seedance_model.get("params", []))
    image_params = ", ".join(param["name"] for param in image_model.get("params", []))
    cinematic_studio_3_params = ", ".join(param["name"] for param in cinematic_studio_3_model.get("params", []))
    credits = account_status.get("credits", "unknown")
    email = account_status.get("email", "unknown")
    plan = account_status.get("subscription_plan_type", "unknown")
    features_by_character: dict[str, list[dict]] = {}
    for row in character_features:
        features_by_character.setdefault(row.get("character_id", ""), []).append(row)

    character_lines = []
    for profile in character_profiles:
        summary = profile.get("summary", "").strip()
        if summary:
            character_lines.append(f"- `{profile.get('name')}` (`{profile.get('character_id')}`): {summary}")
        else:
            character_lines.append(f"- `{profile.get('name')}` (`{profile.get('character_id')}`)")
    character_summary = "\n".join(character_lines) or "- none"

    hermit_profile = next((row for row in character_profiles if row.get("name") == "The Hermit"), None)
    hermit_features = features_by_character.get(hermit_profile.get("character_id", ""), []) if hermit_profile else []
    hermit_feature_lines = "\n".join(
        f"- `{feature.get('label') or feature.get('feature_type')}`: {feature.get('summary', '').strip()}"
        for feature in hermit_features
        if feature.get("summary")
    ) or "- none"

    motion_object_lines = "\n".join(
        f"- `{row.get('label')}` (`{row.get('motion_id')}`) | scope `{row.get('scope')}` | action: {row.get('primary_action')}"
        for row in motion_objects
    ) or "- none"
    motion_binding_lines = "\n".join(
        f"- `{row.get('motion_id')}` -> `{row.get('target_kind')}/{row.get('target_id')}` when `{', '.join(row.get('when_tags', []))}`"
        for row in motion_bindings
    ) or "- none"

    clean_rows = clean_sweep.get("experiments", [])
    clean_completed = [row for row in clean_rows if row.get("refresh_status") == "completed"]
    clean_ip_blocked = [row for row in clean_rows if row.get("refresh_status") == "ip_detected"]
    clean_other_failed = [row for row in clean_rows if row.get("refresh_status") not in {"completed", "ip_detected"}]
    clean_spent = sum(int(row.get("credits_delta", 0) or 0) for row in clean_rows)
    clean_completed_lines = "\n".join(
        f"- `{row.get('experiment_id')}` | `{row.get('model')}` | {row.get('credits_delta')} credits | result `{pack_artifact_path(row.get('local_video')) or row.get('result_url')}`"
        for row in clean_completed
    ) or "- none"
    clean_blocked_lines = "\n".join(
        f"- `{row.get('experiment_id')}` | `{row.get('model')}` | status `ip_detected`"
        for row in clean_ip_blocked
    ) or "- none"
    clean_failed_lines = "\n".join(
        f"- `{row.get('experiment_id')}` | `{row.get('model')}` | error path `{pack_artifact_path(row.get('artifact_dir'))}`"
        for row in clean_other_failed
    ) or "- none"

    image_probe_rows = image_probe_manifest.get("items", [])
    image_submit_rows = image_submit_manifest.get("items", [])
    image_completed = [row for row in image_probe_rows + image_submit_rows if row.get("refresh_status") == "completed"]
    image_failed = [row for row in image_submit_rows if row.get("refresh_status") != "completed"]
    image_spent = sum(int(row.get("credits_delta", 0) or 0) for row in image_probe_rows + image_submit_rows)
    image_completed_lines = "\n".join(
        f"- `{row.get('slug')}` | {row.get('credits_delta')} credits | result `{pack_artifact_path(row.get('local_path')) or row.get('result_url')}`"
        for row in image_completed
    ) or "- none"
    image_failed_lines = "\n".join(
        f"- `{row.get('slug')}` | error `{row.get('error', '')}`"
        for row in image_failed
    ) or "- none"

    final_one_credit_path = (
        EXPERIMENTS_DIR
        / "semantic-final-one-credit-2026-05-08T234108Z"
        / "semantic-final-one-credit.png"
    )
    final_one_credit_pack_path = pack_artifact_path(str(final_one_credit_path))
    clean_completed_lines_indented = indent(clean_completed_lines, "  ")
    clean_blocked_lines_indented = indent(clean_blocked_lines, "  ")
    clean_failed_lines_indented = indent(clean_failed_lines, "  ")
    image_completed_lines_indented = indent(image_completed_lines, "  ")
    image_failed_lines_indented = indent(image_failed_lines, "  ")

    write(
        output / "README.md",
        dedent(
            f"""
            # World Studio Master Library

            This is a portable master folder for the Worldbuilding Studio and the full three-state traversal experiment.

            It is designed to let another agent:

            - understand how the system works end to end
            - inspect the exact artifacts produced by the trial world
            - reason about benefits and failure modes without reopening the full repo
            - simulate future changes using the copied docs, code snapshots, packets, and logs

            This pack was built at `{built_at}` from the repo at `/Users/talhauddin/software/inner_space`.

            ## What is in here

            - `AGENT_INDEX.md`: fastest entrypoint for another agent
            - `AGENT_CONFIG.yaml`: retrieval and routing hints
            - `00-overview/`: system summary, benefits, reasoning policy
            - `01-workflow/`: end-to-end flow, interfaces, CLI behavior, model influence
            - `02-architecture/`: deep architecture notes and storage contracts
            - `03-experiment-log/`: chronology, fixes, incidents, object logs, showcase analysis
            - `03-experiment-log/semantic-credit-burn-findings.md`: detailed report on the zero-credit exploration sweep
            - `04-artifacts/`: copied world state, packets, anchors, videos, model snapshots
            - `05-source-snapshots/`: copied source files and UI files
            - `06-simulation-kit/`: probe cases and agent prompts
            - `configs/`: redacted runtime and provider model snapshots

            ## Important boundary

            This pack does **not** include verbatim private chain-of-thought. It includes observable actions, externalized rationale, engineering decisions, failure analysis, copied artifacts, and code snapshots.

            ## Showcase output

            Final stitched video:

            - [three-state-traversal-showcase.mp4](./04-artifacts/worlds/{WORLD_ID}/showcases/three-state-traversal-showcase.mp4)
            """
        ),
    )

    write(
        output / "AGENT_INDEX.md",
        dedent(
            f"""
            # Agent Index

            Start here if you are an agent dropped into this folder.

            ## Mission

            Explain, evaluate, improve, and simulate the Worldbuilding Studio and its Higgsfield execution loop using only this pack.

            ## Fastest routes

            - For a high-level orientation: `README.md`
            - For system behavior: `00-overview/system-summary.md`
            - For workflow and commands: `01-workflow/end-to-end-worldbuilding-loop.md`
            - For Higgsfield CLI and model contracts: `01-workflow/higgsfield-cli-reference.md`
            - For architecture: `02-architecture/architecture-overview.md`
            - For the current leverage gap: `02-architecture/current-implementation-gap.md`
            - For the exact experiment history: `03-experiment-log/chronology.md`
            - For the latest detailed findings report: `03-experiment-log/semantic-credit-burn-findings.md`
            - For explicit character and motion objects: `03-experiment-log/character-and-motion-objects.md`
            - For what broke and what was fixed: `03-experiment-log/fixes-and-incidents.md`
            - For copied packets and videos: `04-artifacts/README.md`
            - For code: `05-source-snapshots/README.md`
            - For simulation prompts: `06-simulation-kit/README.md`

            ## Recommended agent behavior

            1. Read `00-overview/reasoning-policy.md`.
            2. Read `00-overview/system-summary.md`.
            3. Decide whether the user is asking about workflow, architecture, provider behavior, or optimization.
            4. Open the smallest relevant file first.
            5. Use the copied packet and execution artifacts as ground truth for claims about the trial run.
            6. Use the copied source snapshots when you need exact implementation detail.

            ## If asked whether the system beats normal prompting

            Start with:

            - `00-overview/benefits-vs-normal-prompting.md`
            - `03-experiment-log/semantic-credit-burn-findings.md`
            - `03-experiment-log/showcase-analysis.md`
            - `04-artifacts/worlds/{WORLD_ID}/`
            """
        ),
    )

    write(
        output / "AGENT_CONFIG.yaml",
        dedent(
            """
            mission: "Portable master library for World Studio system understanding, experiment review, and simulation."
            default_entrypoint: "AGENT_INDEX.md"
            retrieval:
              preferred_mode: "lexical-first"
              architecture_entry: "02-architecture/architecture-overview.md"
              workflow_entry: "01-workflow/end-to-end-worldbuilding-loop.md"
              experiment_entry: "03-experiment-log/chronology.md"
              gap_entry: "02-architecture/current-implementation-gap.md"
              artifacts_entry: "04-artifacts/README.md"
              simulation_entry: "06-simulation-kit/README.md"
            constraints:
              - "Do not claim access to hidden chain-of-thought; use the external decision log instead."
              - "Treat copied packets, execution logs, and source snapshots as the canonical evidence inside this pack."
              - "When discussing provider behavior, distinguish system-side bugs from Higgsfield-side latency or validation."
            """
        ),
    )

    write(
        output / "HANDOFF_PROMPT.txt",
        dedent(
            f"""
            Work from this pack as if it were the primary knowledge surface for the World Studio system.

            Start with:
            1. AGENT_INDEX.md
            2. 00-overview/system-summary.md
            3. 03-experiment-log/chronology.md
            4. 03-experiment-log/character-and-motion-objects.md
            5. 02-architecture/current-implementation-gap.md

            Use the copied artifacts under 04-artifacts as ground truth for the trial world `{WORLD_ID}`.
            Use 05-source-snapshots when exact implementation details matter.
            Use 06-simulation-kit for probe prompts and optimization drills.
            """
        ),
    )

    write(
        output / "00-overview" / "system-summary.md",
        dedent(
            f"""
            # System Summary

            World Studio is an explicit world OS layered on top of Inner Space. It does not treat worldbuilding as one large prompt. It treats it as a stored, inspectable, reusable substrate.

            ## Core idea

            The system separates worldbuilding into durable layers:

            - `SourceEvidence`: text notes, image references, captions
            - explicit world records: character, place, object, rule, motif, visual traits
            - inferred graph links: cross-layer relationships with visible support
            - canon assets: reusable reference artifacts for scenes
            - scene packets: structured execution bundles
            - execution runs and generated assets

            In practice this means later generation can reuse a world without restating the whole world in every prompt.

            The current trial world also contains first-class:

            - character profiles and linked feature objects
            - motion objects and motion bindings
            - state-specific visual references
            - canon anchors

            ## Trial world snapshot

            - world id: `{world.get('world_id')}`
            - world name: `{world.get('name')}`
            - summary: `{world.get('summary')}`
            - packet ids: `{", ".join(world.get('packet_ids', []))}`
            - generated assets: `{", ".join(world.get('asset_ids', []))}`
            - copied world files in this pack: `{len(world_files)}`

            ## Character snapshot

            {character_summary}

            ## Motion snapshot

            - motion object count: `{len(motion_objects)}`
            - motion binding count: `{len(motion_bindings)}`

            ## Trial experiment result

            The three-state traversal showcase generated:

            - one daylight clip
            - one corrected nighttime clip
            - one corrected dream clip
            - one stitched final video of about 12.2 seconds

            The later credit-burn sweep then spent the remaining Higgsfield balance on controlled comparisons:

            - clean video sweep credits spent: `{clean_spent}`
            - completed video runs: `{len(clean_completed)}`
            - provider IP blocks: `{len(clean_ip_blocked)}`
            - completed image probes: `{len(image_completed)}`
            - current account balance at pack build: `{credits}`

            ## Provider snapshot

            - account email: `{email}`
            - plan: `{plan}`
            - available credits at pack build: `{credits}`

            ## Why this system exists

            Normal prompting can produce a single shot quickly, but it is weak at:

            - preserving provenance
            - keeping multi-scene continuity
            - reusing exact visual logic between runs
            - showing what changed when something drifted
            - separating system bugs from provider behavior

            World Studio addresses those by storing a world graph, compiling packets, and recording execution runs explicitly.

            ## Current implementation gap

            The representation layer is currently stronger than the last-mile generation compiler.

            In plain terms:

            - the semantic space stores more detail than Higgsfield is consistently made to use
            - character, motion, and visual objects are real and reusable
            - but too much of that structure still gets flattened into a prompt before execution

            Read `02-architecture/current-implementation-gap.md` for the direct analysis.
            """
        ),
    )

    write(
        output / "00-overview" / "benefits-vs-normal-prompting.md",
        dedent(
            """
            # Benefits vs Normal Prompting

            This file is the direct answer to the question: does the worldbuilding system provide any real advantage over normal prompting?

            ## Where the system clearly helps

            1. **Continuity**
               - The same man, route, and architecture lineage can be preserved across multiple states.
               - State shifts can be expressed through a controlled change in anchor, prompt, and retrieved traits rather than rewriting the whole premise from scratch.

            2. **Inspectability**
               - You can inspect evidence, visual traits, canon assets, packets, execution runs, and generated assets separately.
               - That makes debugging concrete. In this experiment, the wrong night anchor and the unsupported `generate_audio` param were visible and fixable.

            3. **Reuse**
               - Once the world holds reusable day/night/dream references, later scenes can compile from them instead of improvising style again.

            4. **Failure isolation**
               - The system can distinguish:
                 - retrieval behavior
                 - packet compilation
                 - adapter behavior
                 - provider validation
                 - provider latency

            5. **Benchmarkability**
               - The credit-burn sweep made it possible to run direct-prompt, semantic-compile, and Seedance-reference variants against the same world and character.
               - That is the beginning of a real benchmark harness rather than anecdotal prompting.

            ## Where the system is still weaker than ideal

            1. **Prompt noise**
               - The compiled prompts still carry some clumsy text fragments from earlier ingestion.
               - This reduces elegance relative to a hand-written single prompt.

            2. **Extraction quality**
               - Some world primitives and motifs are too blunt or too literal.
               - Better normalization would improve both canon quality and final prompts.

            3. **Latency**
               - A one-off prompt can be faster for trivial tasks.
               - This system pays an upfront structure cost.

            ## Practical verdict

            For a single disposable shot, normal prompting may still be simpler.

            For:

            - multi-scene continuity
            - reference-heavy worldbuilding
            - state transitions
            - repeatable experimentation
            - debugging provider behavior

            the World Studio approach is materially better.

            ## Measured findings from the zero-credit sweep

            - Clean sweep video credits spent: `{clean_spent}`
            - Direct baseline completed:
              - day: yes
              - night: yes
            - Semantic compiler completed:
              - day: yes
              - night: yes
            - Seedance completed:
              - night: yes
              - day: blocked by `ip_detected`
            - Dream video tests did not run because the remaining balance after the completed day/night sweep was below the per-run cost.

            The practical read is:

            - the semantic system is already useful for continuity, stored character logic, motion reuse, and provider-debug visibility
            - it is **not yet clearly dominant** over a strong hand-written prompt at the final generation layer
            - the largest remaining gap is still prompt compaction and provider-facing control, not ontology or storage

            ## What would strengthen the advantage

            - cleaner prompt compaction from world records
            - sharper category extraction for lens/style/architecture buckets
            - first-class support for state-specific canon anchor selection
            - explicit provider param schemas per model
            - tighter benchmark harnesses that compare direct, semantic, and multimodal variants on the same shot
            """
        ),
    )

    write(
        output / "00-overview" / "reasoning-policy.md",
        dedent(
            """
            # Reasoning Policy

            The user asked for the full reasoning and process.

            This pack does **not** contain verbatim hidden chain-of-thought.

            Instead, it contains:

            - observable chronology
            - packet states
            - execution logs
            - failure traces
            - code snapshots
            - reconstructed decision summaries
            - explicit engineering rationale

            This is deliberate. It gives another agent the information needed to reason about the system without pretending to expose private internal traces that are not part of the public artifact surface.

            Use `03-experiment-log/decision-log.md` as the canonical externalized rationale file.
            """
        ),
    )

    write(
        output / "01-workflow" / "end-to-end-worldbuilding-loop.md",
        dedent(
            """
            # End-to-End Worldbuilding Loop

            ## Loop

            1. Create or choose a world.
            2. Ingest text evidence.
            3. Ingest visual references with notes.
            4. Inspect evidence, graph, and visual context.
            5. Ask the next question only if needed.
            6. Generate canon assets.
            7. Compile a scene from canon.
            8. Execute the packet through Higgsfield.
            9. Record generated assets and execution runs back into the world state.

            ## Commands

            ```bash
            cd /Users/talhauddin/software/inner_space

            python3 tools/conversation_os.py world-studio guide
            python3 tools/conversation_os.py world-studio ingest-evidence --world-id <world_id> --source-text "..."
            python3 tools/conversation_os.py world-studio ingest-visual-reference --world-id <world_id> --source-path ./ref.png --note "..." --categories architecture_style,lighting_language
            python3 tools/conversation_os.py world-studio inspect-visual-world --world-id <world_id>
            python3 tools/conversation_os.py world-studio compile-visual-context --world-id <world_id> --query-text "..."
            python3 tools/conversation_os.py world-studio generate-canon --world-id <world_id>
            python3 tools/conversation_os.py world-studio compile-scene-from-canon --world-id <world_id> --scene-text "..."
            python3 tools/conversation_os.py world-studio execute-packet --packet-id <packet_id> --mode auto
            ```

            ## Trial-world variation

            In the three-state showcase, the loop became:

            1. ingest reference batches
            2. generate three first-party anchor stills
            3. compile one packet per state
            4. execute three Seedance clips
            5. stitch the clips
            """
        ),
    )

    write(
        output / "01-workflow" / "cli-api-mcp-reference.md",
        dedent(
            """
            # CLI, API, and MCP Reference

            ## CLI surfaces

            Main entrypoint:

            - `python3 tools/conversation_os.py world-studio ...`

            Key subcommands:

            - `guide`
            - `create-world`
            - `ingest-evidence`
            - `ingest-visual-reference`
            - `inspect-evidence`
            - `inspect-knowledge`
            - `inspect-graph`
            - `inspect-visual-world`
            - `compile-visual-context`
            - `create-character-profile`
            - `update-character-profile`
            - `update-character-feature`
            - `inspect-character-system`
            - `create-motion-object`
            - `bind-motion-object`
            - `inspect-motion-system`
            - `compile-motion-plan`
            - `next-question`
            - `generate-canon`
            - `compile-scene`
            - `compile-scene-from-canon`
            - `execute-packet`
            - `executions`
            - `get-packet`
            - `record-asset`
            - `evaluate-output`

            ## API surfaces

            The miniapp backend exposes these paths:

            - `GET /api/world-studio/worlds`
            - `GET /api/world-studio/guide`
            - `GET /api/world-studio/executions`
            - `GET /api/world-studio/execution/<execution_id>`
            - `GET /api/world-studio/world/<world_id>/next-question`
            - `GET /api/world-studio/world/<world_id>/evidence`
            - `GET /api/world-studio/world/<world_id>/graph`
            - `GET /api/world-studio/world/<world_id>/knowledge`
            - `GET /api/world-studio/world/<world_id>/visual`
            - `POST /api/world-studio/world`
            - `POST /api/world-studio/population/start`
            - `POST /api/world-studio/population/answer`
            - `POST /api/world-studio/ingest-evidence`
            - `POST /api/world-studio/ingest-visual-reference`
            - `POST /api/world-studio/generate-canon`
            - `POST /api/world-studio/compile-visual-context`
            - `POST /api/world-studio/compile-scene`
            - `POST /api/world-studio/compile-scene-from-canon`
            - `POST /api/world-studio/execute-packet`
            - `POST /api/world-studio/demo`

            ## MCP surface

            `src/conversation_os/worldbuilding_studio_mcp.py` wraps the same operations for MCP-style access. The system remains packet-first even when called through MCP.
            """
        ),
    )

    write(
        output / "01-workflow" / "higgsfield-cli-reference.md",
        dedent(
            f"""
            # Higgsfield CLI Reference

            This section documents the provider-side surface actually used by the system.

            ## Core commands

            - `higgsfield auth login`
            - `higgsfield account status --json`
            - `higgsfield model list --json`
            - `higgsfield model get <model> --json`
            - `higgsfield upload create <path>`
            - `higgsfield generate create <model> --prompt "..." [media flags]`
            - `higgsfield generate get <job_id> --json`
            - `higgsfield generate wait <job_id> --timeout 45m --interval 5s --quiet --json`

            ## How the World Studio adapter uses it

            1. Materialize each media input from a local file path or URL.
            2. Upload local media with `higgsfield upload create`.
            3. Translate packet params into CLI flags.
            4. Call `higgsfield generate create <model> ...`.
            5. Extract the job id.
            6. Poll with `higgsfield generate wait`.
            7. Record the provider response and asset URLs back into the world state.

            ## Seedance 2.0 contract snapshot

            Supported params at pack build:

            - `{seedance_params}`

            Important implication:

            - `generate_audio` is **not** a valid top-level create param for the CLI adapter on this model.
            - The provider may still return `generate_audio: true` in the result payload, but that does not mean the caller can send it.

            ## Cinematic Studio 2.5 contract snapshot

            Supported params at pack build:

            - `{image_params}`

            This image model was used to create the first-party state anchors before video generation.

            ## Cinematic Studio 3.0 contract snapshot

            Supported params at pack build:

            - `{cinematic_studio_3_params}`

            This video model was used as the fallback path during the Hermit dream-sequence scene when Seedance did not return a usable completion.

            ## Current account snapshot

            - email: `{email}`
            - plan: `{plan}`
            - credits: `{credits}`
            """
        ),
    )

    write(
        output / "01-workflow" / "model-behavior-and-influence.md",
        dedent(
            """
            # Model Behavior and Influence

            ## Gemini embedding layer

            World Studio uses `google/gemini-embedding-2-preview` through OpenRouter for visual/text embedding.

            Practical effect:

            - image references + notes become retrievable world evidence
            - later visual queries pull mode-specific references instead of all references equally

            In the trial world, that let the system separate:

            - detailed daytime monumental architecture
            - washed-over nighttime sacred architecture
            - softened dream-state imagery

            ## Cinematic Studio 2.5 image model

            Used here for:

            - `day_anchor`
            - `night_anchor`
            - `dream_anchor`

            Main influence channels:

            - prompt
            - aspect ratio
            - resolution
            - optional media references

            ## Seedance 2.0 video model

            Used here for the final clips.

            Main influence channels:

            - prompt
            - `start_image`
            - aspect ratio
            - duration
            - resolution
            - optional `genre` and `mode`

            In practice, the strongest control in this experiment came from:

            1. correct per-state `start_image`
            2. concise state prompt
            3. continuity language about the same man, route, and sacred architecture lineage

            ## Character and motion layers

            The system now also carries:

            - character profiles
            - linked feature objects
            - motion objects
            - motion bindings

            These can compile into packets even without anchor media. The current limitation is that they still influence the provider mostly through compiled prose rather than true object-level provider controls.

            ## What actually changed the output

            - Day clip: the day anchor and long-lens ceremonial language
            - Night clip: the night anchor and washed-over nocturnal prompt language
            - Dream clip: the dream anchor and reduced-detail dreamy prompt language

            ## What made things worse

            - reusing the wrong anchor for a later state
            - over-noisy prompt text inherited from rough world records
            - sending unsupported CLI params
            """
        ),
    )

    write(
        output / "02-architecture" / "architecture-overview.md",
        dedent(
            """
            # Architecture Overview

            ```mermaid
            flowchart TD
              A["User Notes + Reference Images"] --> B["World Studio Ingestion"]
              B --> C["Evidence Store"]
              B --> D["World Graph"]
              B --> E["Visual Reference Store"]
              D --> Q["Character Profiles + Feature Objects"]
              D --> R["Motion Objects + Motion Bindings"]
              D --> F["Canon Generation"]
              E --> F
              F --> G["Canon Assets"]
              D --> H["Scene Compilation"]
              Q --> H
              R --> H
              G --> H
              H --> I["Context Packet"]
              H --> J["Higgsfield Packet"]
              H --> K["Evaluation Packet"]
              J --> L["Higgsfield CLI Adapter"]
              L --> M["Upload Media"]
              M --> N["Generate Create"]
              N --> O["Generate Wait"]
              O --> P["Generated Assets + Execution Runs"]
              P --> D
            ```

            ## Main modules

            - `worldbuilding_studio.py`: core data model, ingestion, canon, packet compilation, execution
            - `cli.py`: command-line routing
            - `miniapp.py`: HTTP API routing
            - `worldbuilding_studio_mcp.py`: MCP wrapper surface
            - `run_semantic_credit_sweep.py`: controlled benchmark harness for direct vs semantic vs Seedance experiments
            - miniapp `world-studio.html/js/css`: human-facing UI

            ## Design stance

            The system is deliberately packet-first:

            - it stores world state before generation
            - it compiles explicit execution packets
            - it records execution results back into storage

            This is what makes the system inspectable and replayable.

            ## Important current reality

            The architecture is ahead of the final control layer.

            The world graph now carries characters, feature objects, motion objects, and bindings, but Higgsfield still mostly experiences them through compiled prompt text plus optional media references.

            That means the system has real memory and modularity, but not yet full object-level control at render time.
            """
        ),
    )

    write(
        output / "02-architecture" / "data-model-and-storage.md",
        dedent(
            f"""
            # Data Model and Storage

            ## World directory layout

            World path in the experiment:

            - `04-artifacts/worlds/{WORLD_ID}/`

            Important subdirectories:

            - `evidence/`
            - `graph/`
            - `visual/`
            - `characters/`
            - `motion/`
            - `canon/`
            - `scene/`
            - `executions/`
            - `generated_anchors/`
            - `showcases/`

            ## Packet directory layout

            Each packet lives under `04-artifacts/packets/<packet_id>/` and includes:

            - `context_packet.json`
            - `higgsfield_execution_packet.json`
            - `remotion_composition_props.json`
            - `evaluation.json`
            - sometimes `packet_bundle.json`

            ## Trial packet states

            | Packet | Status | Anchor strategy | Model |
            | --- | --- | --- | --- |
            {packet_table}

            ## Key observations

            - `world.json` is a compact snapshot, not the only truth source.
            - JSONL files under `evidence/`, `graph/`, `visual/`, `characters/`, `motion/`, `scene/`, and `executions/` are the durable event/data layers.
            - Lock files exist in the live repo but are omitted from this pack because they are runtime coordination artifacts, not knowledge artifacts.
            """
        ),
    )

    write(
        output / "02-architecture" / "packet-and-execution-lifecycle.md",
        dedent(
            """
            # Packet and Execution Lifecycle

            ## Packet build

            `compile_scene_from_canon(...)` produces:

            - semantic connective layer
            - selected canon assets
            - layer constraints
            - shot plan
            - context packet
            - Higgsfield packet
            - evaluation packet

            ## Execution build

            `execute_higgsfield_packet(...)` does:

            1. build the Higgsfield request payload
            2. mark execution as submitted
            3. call the live client or prepared-mode client
            4. record provider result
            5. record generated asset ids
            6. update packet status and execution runs

            ## Important adapter behavior

            The Higgsfield CLI client:

            - auto-uploads local media
            - can download remote media references to temp files
            - converts media roles into CLI flags like `--start-image`
            - normalizes image and video responses separately

            ## Trial-run lesson

            Two adapter details mattered:

            - provider param filtering had to be model-aware
            - state-specific anchor selection had to be explicit for showcase clips
            """
        ),
    )

    write(
        output / "02-architecture" / "ui-and-server-topology.md",
        dedent(
            """
            # UI and Server Topology

            ## Browser UI

            The main human-facing UI is the World Studio miniapp:

            - `world-studio.html`
            - `world-studio.css`
            - `world-studio.js`

            The UI was redesigned into a conversation-first spatial canvas rather than a form dashboard.

            ## Server hosting

            The system supports server-hosted OpenClaw deployment with:

            - `tools/deploy_inner_world_to_openclaw.py`
            - `tools/sync_inner_world_ui_to_openclaw.py`
            - `tools/tunnel_inner_world_openclaw.py`

            Practical workflow:

            - app runs on the server
            - this machine edits the repo
            - UI-only changes can sync live
            - backend changes require full deploy

            ## Portable UI slice

            There is already a disconnected frontend slice:

            - `product/inner_world_v1/portable/world-studio-portable`

            This master pack complements that by documenting the entire system and experiment, not just the frontend.
            """
        ),
    )

    write(
        output / "02-architecture" / "mobile-artifacts-integration.md",
        dedent(
            """
            # Mobile Artifacts Integration

            Mobile artifacts are a separate ingestion surface exposed by the Inner World backend.

            ## Canonical roots

            Server canonical path:

            - `/home/talha/.openclaw/workspace/containers/inner-world/mobile_artifacts`

            Local default path:

            - `mobile_artifacts/` in the repo root

            Backend default:

            - `tools/run_inner_world_backend.py` uses `DEFAULT_GPT_ARTIFACT_ROOT = ROOT / "mobile_artifacts"`

            ## Available operations

            - list mobile artifacts
            - read one artifact
            - search artifacts
            - save a chat as a markdown artifact
            - inspect local sync status

            ## Actual saved artifact shape

            Artifacts are written as markdown files with frontmatter, roughly:

            - `artifact_id`
            - `title`
            - `source`
            - `created_at_utc`
            - `updated_at_utc`
            - `tags`
            - `related_paths`
            - `ingest_into_session`

            ## How to use mobile artifacts to enhance World Studio

            1. Capture field notes, phone sketches, image captions, or conversation artifacts into `mobile_artifacts`.
            2. Sync them from server if needed.
            3. Re-ingest the relevant text/image ideas into World Studio as evidence or visual references.
            4. Use tags and related paths to connect them back to specific worlds or UI surfaces.

            ## Important distinction

            Mobile artifacts are not automatically part of the world graph.

            They are a staging surface. Another agent or workflow still needs to:

            - read them
            - extract relevant evidence
            - ingest them into World Studio
            """
        ),
    )

    write(
        output / "02-architecture" / "current-implementation-gap.md",
        dedent(
            """
            # Current Implementation Gap

            This file records the current honest assessment of the system after the world, character, motion, and showcase work.

            ## Short version

            The semantic space is partly useful and partly under-leveraged.

            The representation layer is now real:

            - world records
            - visual references and traits
            - canon assets
            - character profiles and linked feature objects
            - motion objects and bindings
            - scene packets
            - execution runs

            But the execution layer still compresses too much of that structure into prompt text before generation.

            ## Where the system already helps

            - persistence across scenes
            - inspectable world state
            - reusable visual states
            - reusable characters
            - reusable motion grammar
            - clearer debugging of provider failures versus system failures

            ## Where the gap still is

            1. **Flattening at compile time**
               - many graph distinctions collapse into one final prompt
               - Higgsfield does not yet receive a sufficiently structured control surface for all objects

            2. **Selective retrieval is not strict enough**
               - the system often knows more than the active packet uses
               - retrieved world facts are not compacted tightly enough by relevance

            3. **Prompt compaction is not disciplined enough**
               - rough ingestion text can leak into the final prompt
               - this makes the final prompt weaker than it should be relative to the semantic graph behind it

            4. **Object-level control is partial**
               - character objects and motion objects exist
               - but the provider still mainly sees prose, optional media, and a few hard params

            5. **Benchmarking is incomplete**
               - the system should be judged against a strong hand-written prompt plus minimal references
               - that comparison is not yet formalized enough

            6. **Reference-first models still hit provider-side constraints**
               - Seedance is the right conceptual fit for the semantic world
               - but provider states like `ip_detected` still interrupt the cleanest multimodal path
               - the system can now distinguish that as a provider/network issue, but it cannot remove it

            ## Practical verdict

            For one-off shots, the system can still be overkill.

            For continuity-heavy worldbuilding, state transitions, reusable characters, and iterative debugging, the system is already more useful than a pure prompt-only loop.

            The work still needed is not more ontology for its own sake. The work needed is stronger translation from stored semantics to provider-visible control.

            ## Immediate optimization targets

            - stricter retrieval and compaction
            - cleaner prompt synthesis from objects
            - clearer mapping from character objects to shot-visible constraints
            - clearer mapping from motion objects to model-visible motion phrasing
            - benchmark harness against direct handcrafted prompts
            - richer artifact review loops so finished outputs feed back into object refinement
            """
        ),
    )

    write(
        output / "03-experiment-log" / "chronology.md",
        dedent(
            f"""
            # Chronology

            This is the observable chronology for the trial world `{WORLD_ID}` and the three-state showcase.

            ## Event timeline

            {chr(10).join(chronology_lines)}

            ## Execution runs

            {execution_summary}

            ## Zero-credit sweep chronology

            The event log above does not fully capture the later experiment harness, because those runs were organized through standalone manifests rather than world events alone.

            ### Broken first sweep

            - run: `semantic-credit-sweep-2026-05-08T233125Z0000`
            - immediate finding: `cinematic_studio_3_0` rejected the forwarded `resolution` param
            - consequence: no credits spent, but the adapter contract was wrong

            ### Intermediate rerun

            - run: `semantic-credit-sweep-2026-05-08T233355Z0000`
            - immediate finding: a follow-up direct path still had a malformed model argument shape
            - consequence: still no useful spend; runner needed a cleaner submit path

            ### Clean main sweep

            - run: `semantic-credit-sweep-2026-05-08T233636Z0000`
            - credits spent on video runs: `{clean_spent}`
            - completed runs:
            {clean_completed_lines_indented}
            - provider/network blocked:
            {clean_blocked_lines_indented}
            - not run because credits were below threshold:
            {clean_failed_lines_indented}

            ### Image probes

            - recovered probe run: `semantic-image-probes-2026-05-08T233907Z`
            - create-only image batch: `semantic-image-submit-2026-05-08T234032Z`
            - completed image artifacts:
            {image_completed_lines_indented}
            - image failures after balance ran low:
            {image_failed_lines_indented}

            ### Final exhaustion move

            - run: `semantic-final-one-credit-2026-05-08T234108Z`
            - output: `{final_one_credit_pack_path}`
            - credits before: `{final_one_credit_manifest.get('credits_before', {}).get('credits', 'unknown')}`
            - credits after: `{final_one_credit_manifest.get('credits_after', {}).get('credits', 'unknown')}`
            """
        ),
    )

    write(
        output / "03-experiment-log" / "character-and-motion-objects.md",
        dedent(
            f"""
            # Character and Motion Objects

            This file logs the explicit character and motion objects created during the experiment so another agent can reason about the system without reopening live state.

            ## Characters present in the trial world

            {character_summary}

            ## The Hermit

            The main populated character in the current world is `The Hermit` (`world-character-d32bfa40cf92`).

            Profile summary:

            - old man
            - buzzed hair
            - long grey beard
            - deep indigo robes with Tuareg-adjacent color logic
            - heavy tired eyes
            - distinct facial structure
            - curious gaze
            - deep, spiritual, focused
            - slow measured movement with no wasted gesture

            Linked feature objects:

            {hermit_feature_lines}

            ## Motion objects created

            {motion_object_lines}

            ## Motion bindings created

            {motion_binding_lines}

            ## Motion objects used in the Hermit dream scene

            The dream prayer scene used these objects directly:

            - `Meditative Stillness And Eye Opening` for character behavior
            - `Close Up Reveal Pullback` for camera behavior
            - `Soft Robe Drift` for cloth behavior

            ## Why these objects matter

            They show the intended direction of the system:

            - character identity should be stored once and reused
            - motion behavior should be reusable and bindable by object and scene
            - scene prompts should increasingly be compiled from these objects rather than improvised from scratch
            """
        ),
    )

    write(
        output / "03-experiment-log" / "fixes-and-incidents.md",
        dedent(
            """
            # Fixes and Incidents

            ## Fixed in or before this experiment

            1. **Live Higgsfield execution bridge**
               - Added direct execution through the official Higgsfield CLI.

            2. **Seedance media handoff**
               - System now compiles and uploads real media for Seedance instead of relying on implicit or broken reference flow.

            3. **JSONL append safety**
               - Parallel ingestion previously risked corrupting JSONL writes; locking was added earlier in development.

            4. **State-specific showcase anchors**
               - The experiment showed that generic canon selection could flatten state changes.
               - Fix: explicit anchor override per showcase beat.

            5. **Provider param filtering**
               - First attempt at param passthrough was too permissive.
               - Symptom: `Error: Unknown params: generate_audio`
               - Fix: only forward model-supported params such as `aspect_ratio`, `duration`, `resolution`, `genre`, and `mode`.

            6. **Portable pack completeness**
               - Earlier master-library builds predated the new `characters/` and `motion/` world directories.
               - Fix: rebuild the pack after the character and motion layers were added so the portable copy carries those artifacts too.

            7. **Model-specific provider param filtering**
               - The first credit-burn sweep proved that the adapter could not safely forward the same params to every Higgsfield model.
               - Fix: explicit per-model allowed-param filtering, including the narrower `cinematic_studio_3_0` contract.

            8. **Submit-first experiment runner**
               - Sequential waits were the wrong shape for intentionally spending the remaining credit balance on comparisons.
               - Fix: the experiment runner was reshaped to submit first, then poll and recover artifacts separately.

            ## Incidents observed in this run

            1. **Night packet using the day anchor**
               - Cause: canon selection did not guarantee state-specific anchor choice.
               - Result: would have collapsed the intended visual transition.
               - Resolution: explicit manual override for the showcase path.

            2. **Silent provider wait**
               - Cause: long-running Seedance jobs do not print much through the CLI wait loop.
               - Resolution: direct job inspection with `higgsfield generate get <job_id> --json`.

            3. **Intermediate failed execution**
               - Packet: `world-packet-d4ff5923835a`
               - Error: unsupported `generate_audio`
               - Kept in history as a real failure artifact.

            4. **Hermit dream scene generated three provider attempts**
               - one full Seedance packet execution
               - one simplified Seedance retry
               - one `cinematic_studio_3_0` fallback
               - this was not three intended deliverables; it was one scene with multiple generation attempts as the execution path was tightened

            5. **Broken first credit sweep**
               - root cause: `cinematic_studio_3_0` rejected `resolution`
               - effect: zero-credit dry failure, but valuable contract discovery

            6. **Broken second credit sweep**
               - root cause: malformed direct-run model argument shape
               - effect: still no useful spend, runner needed cleanup

            7. **Seedance day run blocked by provider network status**
               - clean semantic multimodal submission still ended in `ip_detected`
               - this is preserved as a meaningful provider-side artifact, not a silent failure

            ## Still open or worth improving

            - early provider job id persistence could be clearer during in-progress runs
            - prompt compaction from rough world records is still noisy
            - category extraction for some visual traits remains blunt
            - the semantic world model is richer than the current last-mile control surface; too much structure still collapses into prompt text
            - direct-vs-semantic benchmarking should be promoted from ad hoc experiments into a permanent workflow surface
            """
        ),
    )

    write(
        output / "03-experiment-log" / "showcase-analysis.md",
        dedent(
            """
            # Showcase Analysis

            ## Goal

            Demonstrate that one world graph can express:

            - one recurring subject
            - one recurring architectural lineage
            - one recurring forward route
            - three different rendering states

            ## What worked

            - The system successfully produced first-party day, night, and dream anchors.
            - Those anchors let Seedance operate from owned canonical references instead of raw uploaded screenshots.
            - The final stitched short is a concrete proof that the pipeline can preserve identity while changing style state.

            ## What did not work automatically

            - The generic canon path did not sufficiently guarantee correct per-state anchor binding for the showcase.
            - The prompt text still contains some awkward fragments inherited from world records.
            - Character and motion objects exist, but they are not yet translated into provider-visible control as strongly as the world model implies.

            ## Why this still matters

            These problems are implementation details, not conceptual failures.

            The experiment showed a real difference between:

            - naive prompting from a loose idea
            - a structured world system that can surface, inspect, and correct the sources of drift

            ## Practical conclusion

            The system is already useful for continuity-heavy, reference-heavy generation. It is not yet maximally elegant, but it is already more debuggable and more reusable than a pure prompt-only loop.

            The current gap is not missing ontology. The gap is the compiler layer between ontology and generation.
            """
        ),
    )

    write(
        output / "03-experiment-log" / "decision-log.md",
        dedent(
            """
            # Decision Log

            This is an externalized engineering rationale log, not a verbatim hidden reasoning transcript.

            ## Key decisions

            1. **Store worlds explicitly rather than summarize them into one master prompt**
               - Reason: continuity and inspectability.

            2. **Use Gemini embeddings for visual retrieval**
               - Reason: multimodal reference + note retrieval is a better fit than text-only embeddings.

            3. **Use first-party canon stills before Seedance**
               - Reason: safer and more stable than pushing third-party screenshots directly into final multimodal video generation.

            4. **Use one clip per state rather than one 12-second all-in-one generation**
               - Reason: clearer state separation and easier debugging.

            5. **Keep failed packets and runs**
               - Reason: failure artifacts are part of the system’s learning surface.

            6. **Package the experiment into a portable knowledge folder**
               - Reason: another agent should be able to simulate, inspect, and optimize without depending on live repo memory.
            """
        ),
    )

    write(
        output / "04-artifacts" / "README.md",
        dedent(
            f"""
            # Artifacts

            This directory contains copied artifacts from the trial world and the supporting provider snapshots.

            ## Included

            - `worlds/{WORLD_ID}/`: copied world state
              - includes `characters/` and `motion/` directories from the live world
              - includes `experiments/` from the Higgsfield credit-burn sweep
            - `packets/`: copied packet directories for the showcase and one failed intermediate packet
            - `logs/events-{WORLD_ID}.jsonl`: world-specific filtered event log
            - `logs/execution-runs.jsonl`: copied execution run records
            - `provider/account-status.json`
            - `provider/seedance_2_0.json`
            - `provider/cinematic_studio_2_5.json`
            - `provider/cinematic_studio_3_0.json`

            ## Why this matters

            Another agent can inspect:

            - what was ingested
            - which characters and motion objects were created
            - what canon was created
            - what packets were produced
            - what actually ran
            - which runs failed and why
            - how many credits each run consumed
            - which outputs came from direct prompts versus semantic compilation versus Seedance
            """
        ),
    )

    write(
        output / "04-artifacts" / "mobile-artifacts" / "README.md",
        dedent(
            """
            # Mobile Artifacts Instructions

            This subfolder documents how mobile artifacts can enhance or change the system.

            ## Use case

            Mobile artifacts are a staging surface for:

            - phone-captured visual references
            - chat exports
            - short field notes
            - lightweight concept captures

            ## Source of truth

            Server root:

            - `/home/talha/.openclaw/workspace/containers/inner-world/mobile_artifacts`

            Local default:

            - `./mobile_artifacts/`

            ## Sync

            Pull hint exposed by the backend:

            ```bash
            rsync -az talha@192.168.0.102:/home/talha/.openclaw/workspace/containers/inner-world/mobile_artifacts/ ./mobile_artifacts/
            ```

            ## Enhancement pattern

            1. Save the artifact.
            2. Search/read it through the backend or locally.
            3. Extract any world-relevant evidence.
            4. Re-ingest into World Studio using:

            ```bash
            python3 tools/conversation_os.py world-studio ingest-evidence ...
            python3 tools/conversation_os.py world-studio ingest-visual-reference ...
            ```

            ## Recommendation

            Treat mobile artifacts as raw signal, not final world truth.
            """
        ),
    )

    write(
        output / "05-source-snapshots" / "README.md",
        dedent(
            """
            # Source Snapshots

            This directory contains copied source files relevant to the World Studio system and the three-state showcase.

            Use these when:

            - exact implementation detail matters
            - you want to propose a code change from the pack alone
            - you need to compare documented behavior against the actual code

            Important files:

            - `src/conversation_os/worldbuilding_studio.py`
            - `src/conversation_os/cli.py`
            - `src/conversation_os/miniapp.py`
            - `src/conversation_os/worldbuilding_studio_mcp.py`
            - `tools/run_three_state_showcase.py`
            - `tools/run_inner_world_backend.py`
            - `product/inner_world_v1/miniapp/world-studio.*`
            """
        ),
    )

    write(
        output / "03-experiment-log" / "semantic-credit-burn-findings.md",
        dedent(
            f"""
            # Semantic Credit-Burn Findings

            This report covers the controlled sweep that intentionally spent the remaining Higgsfield balance to test whether the semantic world model adds practical value beyond direct prompting.

            ## Executive summary

            The sweep proved three things clearly:

            1. The semantic system is already useful as a **world memory, comparison, and debugging layer**.
            2. The semantic system is **not yet fully winning at the final prompt-execution layer** because too much structure still collapses into prose.
            3. The execution adapter and provider-contract work were necessary. Without them, the semantic layer would have been impossible to evaluate fairly.

            ## What was run

            ### Video sweep

            Main run: `semantic-credit-sweep-2026-05-08T233636Z0000`

            Completed video runs:
            {clean_completed_lines_indented}

            Blocked video run:
            {clean_blocked_lines_indented}

            Not executed because remaining balance fell below per-run cost:
            {clean_failed_lines_indented}

            ### Image probes

            Completed image runs:
            {image_completed_lines_indented}

            Failed image runs after low balance:
            {image_failed_lines_indented}

            Final one-credit exhaustion artifact:
            - `{final_one_credit_pack_path}`

            ## Credits and cost profile

            - first broken sweep spent: `0`
            - second broken sweep spent: `0`
            - clean video sweep spent: `{clean_spent}`
            - image probes spent: `{image_spent}`
            - final one-credit image spent: `{final_one_credit_manifest.get('credits_before', {}).get('credits', 0) - final_one_credit_manifest.get('credits_after', {}).get('credits', 0)}`
            - account balance at build time: `{credits}`

            ## What the system demonstrably did better than direct prompting

            ### 1. Continuity scaffolding

            The system preserved:

            - a named world with persistent state buckets
            - a persistent character (`The Hermit`)
            - reusable visual states (day, night, dream)
            - reusable motion objects
            - canon and packet history

            A direct prompt can imitate that for one shot, but it cannot store and re-query it cleanly.

            ### 2. Controlled comparison

            The sweep made it possible to compare:

            - direct prompt, same model
            - semantic compile, same model
            - semantic canon + Seedance

            That is the real differentiator versus prompt-first creative tools. A prompt-first tool can help make outputs; this system can also preserve the reasoning surface that explains *why one output path differed from another*.

            ### 3. Failure attribution

            The system isolated distinct failure classes:

            - adapter bug: unsupported `resolution` forwarded to `cinematic_studio_3_0`
            - runner bug: malformed model argument during early rerun
            - provider/network issue: `ip_detected` on Seedance day run
            - economic boundary: later dream tests failed only because the account balance was below the required credit cost

            In a prompt-only tool, those often collapse into “it didn’t work.”

            ## What the system still does worse than it should

            ### 1. Prompt compaction is still noisy

            The semantic compiler often emits prompts that still contain:

            - rough ingestion fragments
            - duplicated trait language
            - broad category labels where a cleaner shot-language phrase should exist

            That weakens the last-mile advantage.

            ### 2. Object leverage is partial

            Character objects and motion objects exist, but the provider still mainly receives:

            - prose prompt
            - optional media
            - a few hard params

            So the model is not yet consuming the semantic graph as strongly as the internal system suggests.

            ### 3. Multimodal reference flow remains provider-sensitive

            Seedance is the best conceptual fit for the system, but the day run still hit `ip_detected`. That means the world model can prepare a better multimodal packet than a direct prompt, but the provider can still interrupt the evaluation.

            ## Practical verdict

            The semantic world is **not overkill** if the goal is:

            - reusable worldbuilding
            - character persistence
            - motion reuse
            - state-specific scene variation
            - benchmarkable generation workflows
            - artifact-level debugging

            The semantic world **is overbuilt relative to final output quality** if the goal is only:

            - one disposable shot
            - minimal iteration
            - no need to inspect or reuse the world later

            ## Why this matters relative to prompt-first tools like Flora

            The likely edge over prompt-first tooling is not just “better prompt text.” The edge is:

            - explicit stored objects
            - inspectable provenance
            - scene packet history
            - execution history
            - repeatable comparisons across model strategies

            If World Studio is improved properly, it should outperform prompt-first tools on **continuity, auditability, and optimization loops**, even when raw first-pass output quality is initially similar.

            ## Highest-value next improvements

            1. Build a stricter prompt-compaction layer.
            2. Add artifact review feedback back into object refinement.
            3. Formalize benchmark scenes so direct vs semantic vs multimodal comparisons become routine.
            4. Expand model-specific contracts so every model receives only the params and control forms it actually supports.
            5. Tighten object-to-prompt translation so character, motion, and state objects influence the result more directly.
            """
        ),
    )

    write(
        output / "02-architecture" / "experiment-harness-and-provider-contracts.md",
        dedent(
            f"""
            # Experiment Harness And Provider Contracts

            This file documents the architecture that made the zero-credit sweep possible.

            ## Purpose

            The harness exists to separate three concerns:

            1. **world semantics**
            2. **packet compilation**
            3. **provider execution behavior**

            ## Components

            - runner: `tools/run_semantic_credit_sweep.py`
            - compiler / adapter: `src/conversation_os/worldbuilding_studio.py`
            - provider CLI: Higgsfield official local CLI
            - manifests written under:
              - `product/inner_world_v1/data/worldbuilding_studio/worlds/{WORLD_ID}/experiments/`

            ## Why the harness mattered

            The early broken sweeps showed that without a controlled runner, it is too easy to confuse:

            - a semantic-model weakness
            - an adapter bug
            - a provider schema mismatch

            ## Provider contracts discovered in this run

            ### `cinematic_studio_3_0`

            Supported execution params observed:
            - `{cinematic_studio_3_params}`

            Important negative finding:
            - forwarding `resolution` caused the first sweep to fail immediately

            ### `seedance_2_0`

            Supported execution params observed:
            - `{seedance_params}`

            Important behavior:
            - reference-driven multimodal packets work structurally
            - provider-side states like `ip_detected` can still interrupt the run after a valid submission

            ### `cinematic_studio_2_5`

            Supported image params observed:
            - `{image_params}`

            Practical use in this experiment:
            - semantic portraits and state keyframes

            ## Architectural lesson

            The semantic system cannot be judged honestly unless the provider contract layer is explicit and model-specific.

            In practice that means:

            - do not treat “Higgsfield” as one uniform capability
            - maintain per-model allowed params
            - maintain per-model cost assumptions
            - maintain per-model control strategies

            ## Current architectural gap

            The provider contract layer is now better than before, but the object-to-provider translation is still shallow. The next architectural improvement should be **stronger object compaction**, not more object types.
            """
        ),
    )

    write(
        output / "06-simulation-kit" / "README.md",
        dedent(
            """
            # Simulation Kit

            This folder exists so another agent can "run simulations" by reasoning against the pack.

            ## Recommended simulation types

            - workflow simulation: what happens after a new reference image is added?
            - provider simulation: what fields actually reach Seedance?
            - continuity simulation: how would a fourth state be added?
            - optimization simulation: what would make the prompts cleaner?
            - product simulation: does the system actually outperform normal prompting for a given task?

            Start with:

            - `probe-cases.json`
            - `optimization-questions.md`
            - `agent-playbook.md`
            """
        ),
    )

    probe_cases = [
        {
            "id": "probe-compare-prompting",
            "goal": "Assess whether the system gives a real advantage over one-shot prompting.",
            "recommended_sources": [
                "00-overview/benefits-vs-normal-prompting.md",
                "03-experiment-log/showcase-analysis.md",
                f"04-artifacts/worlds/{WORLD_ID}/showcases/",
            ],
        },
        {
            "id": "probe-night-anchor-bug",
            "goal": "Explain why the first night attempt drifted and how the fix worked.",
            "recommended_sources": [
                "03-experiment-log/fixes-and-incidents.md",
                "04-artifacts/packets/world-packet-d4ff5923835a/",
                "04-artifacts/packets/world-packet-2c31e9dc86d6/",
            ],
        },
        {
            "id": "probe-seedance-param-contract",
            "goal": "Explain which params Seedance 2.0 accepts and why `generate_audio` failed as an input param.",
            "recommended_sources": [
                "01-workflow/higgsfield-cli-reference.md",
                "04-artifacts/provider/seedance_2_0.json",
                "03-experiment-log/fixes-and-incidents.md",
            ],
        },
        {
            "id": "probe-mobile-artifacts",
            "goal": "Design a concrete path for using mobile artifacts to influence a world.",
            "recommended_sources": [
                "02-architecture/mobile-artifacts-integration.md",
                "04-artifacts/mobile-artifacts/README.md",
            ],
        },
        {
            "id": "probe-fourth-state",
            "goal": "Simulate adding a fourth visual state, such as storm or ritual-fire dusk.",
            "recommended_sources": [
                "01-workflow/model-behavior-and-influence.md",
                "02-architecture/packet-and-execution-lifecycle.md",
                "03-experiment-log/decision-log.md",
            ],
        },
        {
            "id": "probe-semantic-gap",
            "goal": "Assess whether the semantic space is overbuilt relative to the current generation compiler and identify the highest-leverage fixes.",
            "recommended_sources": [
                "02-architecture/current-implementation-gap.md",
                "03-experiment-log/character-and-motion-objects.md",
                "00-overview/benefits-vs-normal-prompting.md",
            ],
        },
    ]
    write_json(output / "06-simulation-kit" / "probe-cases.json", probe_cases)

    write(
        output / "06-simulation-kit" / "optimization-questions.md",
        dedent(
            """
            # Optimization Questions

            Use these to pressure-test the system:

            1. Which fields in `world.json` are too lossy to be useful for prompt compilation?
            2. Which visual categories need sharper normalization?
            3. How should state anchors be represented so manual override is unnecessary?
            4. Should provider param schemas be cached locally per Higgsfield model?
            5. How should prompt compaction strip ingestion noise without losing world specificity?
            6. When is this system not worth the overhead compared with a direct prompt?
            7. Which semantic objects are not currently buying any measurable control at generation time?
            8. Which parts of the character and motion layers should become harder constraints instead of prose?
            """
        ),
    )

    write(
        output / "06-simulation-kit" / "agent-playbook.md",
        dedent(
            """
            # Agent Playbook

            If asked to work only from this folder:

            1. Open `AGENT_INDEX.md`.
            2. Read the relevant overview and architecture docs.
            3. Inspect copied packets and execution logs before making claims about the showcase.
            4. Use `probe-cases.json` to structure your analysis.
            5. If recommending changes, separate:
               - world-model changes
               - prompt-compaction changes
               - execution-adapter changes
               - provider-side unknowns
            """
        ),
    )

    write_json(
        output / "portable-pack.json",
        {
            "name": "world-studio-master-library",
            "built_at": built_at,
            "world_id": WORLD_ID,
            "world_name": world.get("name", ""),
            "repo_root": str(ROOT),
            "showcase_output": f"04-artifacts/worlds/{WORLD_ID}/showcases/three-state-traversal-showcase.mp4",
            "source_snapshot_count": len(SOURCE_FILES),
            "guide_snapshot_count": len(GUIDE_FILES),
        },
    )


def build_registry(output: Path) -> None:
    resources = []
    for path in sorted(output.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(output)
        resources.append(
            {
                "path": str(rel),
                "kind": rel.parts[0] if len(rel.parts) > 1 else "root",
                "size_bytes": path.stat().st_size,
            }
        )
    write_json(output / "resource_registry.json", {"resources": resources})


def build_pack() -> Path:
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    build_docs(OUTPUT_DIR)

    # Config snapshots
    write_json(OUTPUT_DIR / "configs" / "runtime.sample.redacted.json", sanitize_runtime_config())
    write_json(OUTPUT_DIR / "configs" / "seedance_2_0.json", run_json(["higgsfield", "model", "get", "seedance_2_0", "--json"]) or {})
    write_json(OUTPUT_DIR / "configs" / "cinematic_studio_2_5.json", run_json(["higgsfield", "model", "get", "cinematic_studio_2_5", "--json"]) or {})
    write_json(OUTPUT_DIR / "configs" / "cinematic_studio_3_0.json", run_json(["higgsfield", "model", "get", "cinematic_studio_3_0", "--json"]) or {})
    write_json(OUTPUT_DIR / "configs" / "account-status.json", run_json(["higgsfield", "account", "status", "--json"]) or {})

    # Supporting docs
    for src in GUIDE_FILES:
        copy_file(src, OUTPUT_DIR / "supporting-docs" / src.relative_to(ROOT))

    # Source snapshots
    for src in SOURCE_FILES:
        copy_file(src, OUTPUT_DIR / "05-source-snapshots" / src.relative_to(ROOT))

    # Portable UI snapshot
    portable_ui = ROOT / "product" / "inner_world_v1" / "portable" / "world-studio-portable"
    if portable_ui.exists():
        copy_tree(portable_ui, OUTPUT_DIR / "05-source-snapshots" / "portable-ui" / portable_ui.name)

    # World and packet artifacts
    copy_tree(WORLD_DIR, OUTPUT_DIR / "04-artifacts" / "worlds" / WORLD_ID)
    for packet_id in SELECTED_PACKET_IDS:
        packet_src = PACKETS_DIR / packet_id
        if packet_src.exists():
            copy_tree(packet_src, OUTPUT_DIR / "04-artifacts" / "packets" / packet_id)

    # Logs
    write_json(
        OUTPUT_DIR / "04-artifacts" / "logs" / f"world-summary-{WORLD_ID}.json",
        load_json(WORLD_DIR / "world.json"),
    )
    events = [row for row in filtered_world_events()]
    write(
        OUTPUT_DIR / "04-artifacts" / "logs" / f"events-{WORLD_ID}.jsonl",
        "\n".join(json.dumps(row, ensure_ascii=False) for row in events),
    )
    executions = filtered_execution_runs()
    write(
        OUTPUT_DIR / "04-artifacts" / "logs" / "execution-runs.jsonl",
        "\n".join(json.dumps(row, ensure_ascii=False) for row in executions),
    )

    # Provider snapshots
    write_json(OUTPUT_DIR / "04-artifacts" / "provider" / "account-status.json", run_json(["higgsfield", "account", "status", "--json"]) or {})
    write_json(OUTPUT_DIR / "04-artifacts" / "provider" / "seedance_2_0.json", run_json(["higgsfield", "model", "get", "seedance_2_0", "--json"]) or {})
    write_json(OUTPUT_DIR / "04-artifacts" / "provider" / "cinematic_studio_2_5.json", run_json(["higgsfield", "model", "get", "cinematic_studio_2_5", "--json"]) or {})
    write_json(OUTPUT_DIR / "04-artifacts" / "provider" / "cinematic_studio_3_0.json", run_json(["higgsfield", "model", "get", "cinematic_studio_3_0", "--json"]) or {})

    build_registry(OUTPUT_DIR)
    shutil.make_archive(str(ZIP_BASENAME), "zip", OUTPUT_DIR)
    return OUTPUT_DIR


def main() -> int:
    result = build_pack()
    print(json.dumps({"output_dir": str(result), "zip_path": str(ZIP_BASENAME) + ".zip"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
