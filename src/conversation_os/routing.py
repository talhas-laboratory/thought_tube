from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List

from .conversation_synthesis import search_concepts
from .models import TaskContextPack
from .storage import (
    indexes_dir,
    plans_dir,
    read_json,
    sorted_files,
    task_packs_dir,
    workspace_materialized_paths,
    write_json,
    write_markdown,
)


def _keyword_score(text: str, query: str) -> int:
    words = [word.lower() for word in query.split() if len(word) > 2]
    lowered = text.lower()
    return sum(1 for word in words if word in lowered)


def _numbered_items(path: Path) -> List[str]:
    if not path.exists():
        return []
    items = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if re.match(r"^\d+\.", stripped):
            items.append(stripped)
    return items


def _bullet_items(path: Path) -> List[str]:
    if not path.exists():
        return []
    items = []
    seen = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped.startswith("- "):
            continue
        value = stripped[2:].strip()
        if value.lower().startswith("no "):
            continue
        if value in seen:
            continue
        seen.add(value)
        items.append(value)
    return items


def _status_priority(status: str) -> int:
    return {"accepted": 3, "active": 2, "open": 1}.get(status, 0)


def _card_type_priority(card_type: str) -> int:
    return {"decision": 3, "state": 2, "open_question": 1}.get(card_type, 0)


def _session_rank(manifest: Dict, request: str, domain_overlays: List[str]) -> Dict:
    score_text = " ".join(
        [
            manifest.get("title", ""),
            " ".join(manifest.get("domains", [])),
            manifest.get("status", ""),
        ]
    )
    score = _keyword_score(score_text, request)
    domain_bonus = 2 if set(manifest.get("domains", [])) & set(domain_overlays) else 0
    manifest["_score"] = score + domain_bonus
    manifest["_sort_key"] = manifest.get("ended_at") or manifest.get("started_at") or ""
    return manifest


def _card_rank(payload: Dict, request: str, domain_overlays: List[str]) -> Dict:
    score_text = " ".join(
        [
            payload.get("title", ""),
            payload.get("summary", ""),
            " ".join(payload.get("tags", [])),
            " ".join(payload.get("domains", [])),
        ]
    )
    score = _keyword_score(score_text, request)
    domain_bonus = 2 if set(payload.get("domains", [])) & set(domain_overlays) else 0
    status_bonus = 1 if payload.get("status") in {"accepted", "active"} else 0
    payload["_score"] = score + domain_bonus + status_bonus
    return payload


def build_task_pack(
    root: Path,
    task_id: str,
    request: str,
    task_type: str,
    domain_overlays: List[str],
    constraints: List[str],
) -> Dict:
    tenets_path = root / "TENETS.md"
    tenets = _numbered_items(tenets_path)
    reference_docs = {
        "tenets": str(tenets_path),
        "product_thesis": str(root / "PRODUCT_THESIS.md"),
        "current_state": str(indexes_dir(root) / "current_state.md"),
        "open_questions": str(indexes_dir(root) / "open_questions.md"),
        "decision_register": str(indexes_dir(root) / "decision_register.md"),
        "domain_map": str(indexes_dir(root) / "domain_map.json"),
    }

    cards = []
    for path in sorted_files(root / "memory" / "cards", "*.json"):
        payload = _card_rank(read_json(path), request, domain_overlays)
        cards.append(payload)
    cards.sort(
        key=lambda item: (
            item["_score"],
            _status_priority(item.get("status", "")),
            _card_type_priority(item.get("card_type", "")),
            item.get("card_id", ""),
        ),
        reverse=True,
    )
    scored_cards = [card for card in cards if card["_score"] > 0]
    fallback_cards = sorted(
        cards,
        key=lambda item: (
            _status_priority(item.get("status", "")),
            _card_type_priority(item.get("card_type", "")),
            item.get("card_id", ""),
        ),
        reverse=True,
    )
    relevant_cards = [
        {k: v for k, v in card.items() if not k.startswith("_")}
        for card in (scored_cards[:8] or fallback_cards[:5])
    ]
    deduped_cards = []
    seen_card_titles = set()
    for card in relevant_cards:
        title = card.get("title", "")
        if title in seen_card_titles:
            continue
        seen_card_titles.add(title)
        deduped_cards.append(card)
    relevant_cards = deduped_cards

    sessions = []
    sessions_root = root / "memory" / "sessions"
    if sessions_root.exists():
        for session_dir in sorted(sessions_root.iterdir()):
            manifest_path = session_dir / "manifest.json"
            if not manifest_path.exists():
                continue
            manifest = _session_rank(read_json(manifest_path), request, domain_overlays)
            sessions.append(manifest)
    sessions.sort(
        key=lambda item: (item["_score"], item.get("_sort_key", ""), item["session_id"]),
        reverse=True,
    )
    scored_sessions = [item for item in sessions if item["_score"] > 0]
    fallback_sessions = sorted(
        sessions,
        key=lambda item: (item.get("_sort_key", ""), item["session_id"]),
        reverse=True,
    )
    relevant_sessions = [
        {k: v for k, v in item.items() if not k.startswith("_")}
        for item in (scored_sessions[:6] or fallback_sessions[:3])
    ]

    active_plans = []
    for plan_path in sorted_files(plans_dir(root), "*.md"):
        text = plan_path.read_text(encoding="utf-8")
        score = _keyword_score(text + " " + plan_path.name, request)
        active_plans.append({"path": str(plan_path), "score": score})
    active_plans.sort(key=lambda item: (item["score"], item["path"]), reverse=True)
    scored_plans = [item for item in active_plans if item["score"] > 0]
    chosen_plans = scored_plans[:4] or active_plans[:2]

    open_questions = _bullet_items(indexes_dir(root) / "open_questions.md")
    relevant_concepts = [
        {key: value for key, value in concept.items() if not key.startswith("_")}
        for concept in search_concepts(root, request, limit=6)
    ]

    next_actions = [
        "Review the product thesis and tenets before making changes.",
        "Inspect the most relevant session and decision cards first.",
        "Check relevant concepts for reusable patterns before starting a new implementation thread.",
        "Update the task pack after major new decisions are made.",
    ]

    pack = TaskContextPack(
        task_id=task_id,
        request=request,
        task_type=task_type,
        domain_overlays=domain_overlays,
        tenets=tenets,
        relevant_sessions=relevant_sessions,
        relevant_cards=relevant_cards,
        active_plans=chosen_plans,
        constraints=constraints,
        open_questions=open_questions[:8],
        next_actions=next_actions,
        reference_docs=reference_docs,
        relevant_concepts=relevant_concepts,
    )
    payload = pack.to_dict()
    write_json(task_packs_dir(root) / f"{task_id}.json", payload)
    md = [
        f"# Task Pack — {task_id}",
        "",
        f"- request: {request}",
        f"- task_type: {task_type}",
        f"- domain_overlays: {', '.join(domain_overlays) if domain_overlays else 'none'}",
        "",
        "## Reference Docs",
        "",
    ]
    md.extend([f"- {label}: {path}" for label, path in reference_docs.items()])
    md.extend(
        [
            "",
            "## Tenets",
            "",
        ]
    )
    md.extend([f"- {item}" for item in tenets] or ["- none"])
    md.extend(
        [
            "",
            "## Relevant Sessions",
            "",
        ]
    )
    md.extend(
        [
            f"- {item['session_id']}: {item.get('title', item['session_id'])}"
            for item in relevant_sessions
        ]
        or ["- none"]
    )
    md.extend(
        [
            "",
            "## Relevant Cards",
            "",
        ]
    )
    md.extend([f"- {item['title']}" for item in relevant_cards] or ["- none"])
    md.extend(
        [
            "",
            "## Relevant Concepts",
            "",
        ]
    )
    md.extend(
        [
            f"- {item['label']} ({item.get('status', 'provisional')}, confidence {item.get('confidence', 0.0)})"
            for item in relevant_concepts
        ]
        or ["- none"]
    )
    md.extend(
        [
            "",
            "## Active Plans",
            "",
        ]
    )
    md.extend([f"- {item['path']}" for item in chosen_plans] or ["- none"])
    md.extend(
        [
            "",
            "## Open Questions",
            "",
        ]
    )
    md.extend([f"- {item}" for item in open_questions[:8]] or ["- none"])
    md.extend(
        [
            "",
            "## Next Actions",
            "",
        ]
    )
    md.extend([f"- {item}" for item in next_actions])
    write_markdown(task_packs_dir(root) / f"{task_id}.md", "\n".join(md))
    return payload


def enrich_task_pack_with_workspace(
    root: Path,
    task_id: str,
    workspace_id: str,
    pack: Dict,
    manifest: Dict,
    snapshot: Dict,
    constraints: List[str],
) -> Dict:
    def _blocked_workspace_line(item: Dict) -> str:
        reasons = "; ".join(item.get("blocker_reasons", [])) or "explicitly blocked"
        return f"- {item['work_item_id']}: {item['title']} [{item.get('status', 'unknown')}] :: {reasons}"

    pack["workspace_id"] = workspace_id
    pack["workspace_goal"] = manifest.get("goal", "")
    pack["workspace_purpose"] = manifest.get("purpose", "")
    pack["workspace_success_condition"] = manifest.get("success_condition", "")
    pack["workspace_scope_in"] = list(manifest.get("scope_in", []))
    pack["workspace_scope_out"] = list(manifest.get("scope_out", []))
    pack["workspace_domain_overlays"] = list(manifest.get("domain_overlays", []))
    pack["workspace_template_key"] = manifest.get("template_key", "")
    pack["workspace_template_fields"] = dict(manifest.get("template_fields", {}))
    pack["workspace_summary_ref"] = str(workspace_materialized_paths(root, workspace_id)["summary"])
    pack["workspace_linked_session_ids"] = list(manifest.get("linked_session_ids", []))
    pack["workspace_linked_task_pack_ids"] = list(manifest.get("linked_task_pack_ids", []))
    pack["workspace_active_items"] = snapshot.get("active_items", [])
    pack["workspace_blocked_items"] = snapshot.get("blocked_items", [])
    pack["workspace_pending_tests"] = snapshot.get("pending_tests", [])
    pack["workspace_integration_candidates"] = snapshot.get("integration_candidates", [])
    pack["constraints"] = constraints

    json_path = task_packs_dir(root) / f"{task_id}.json"
    md_path = task_packs_dir(root) / f"{task_id}.md"
    existing_md = md_path.read_text(encoding="utf-8") if md_path.exists() else ""
    md_sections = [existing_md.rstrip(), "", "## Workspace Context", ""]
    md_sections.extend(
        [
            f"- workspace_id: {workspace_id}",
            f"- goal: {pack['workspace_goal'] or 'none'}",
            f"- purpose: {pack['workspace_purpose'] or 'none'}",
            f"- success_condition: {pack['workspace_success_condition'] or 'none'}",
            f"- scope_in: {', '.join(pack['workspace_scope_in']) if pack['workspace_scope_in'] else 'none'}",
            f"- scope_out: {', '.join(pack['workspace_scope_out']) if pack['workspace_scope_out'] else 'none'}",
            f"- domains: {', '.join(pack['workspace_domain_overlays']) if pack['workspace_domain_overlays'] else 'none'}",
            f"- template: {pack['workspace_template_key'] or 'none'}",
            f"- linked_task_packs: {', '.join(pack['workspace_linked_task_pack_ids']) if pack['workspace_linked_task_pack_ids'] else 'none'}",
            f"- summary_ref: {pack['workspace_summary_ref']}",
        ]
    )
    if pack["workspace_template_fields"]:
        md_sections.extend(["", "## Workspace Template Context", ""])
        md_sections.extend(
            [f"- {key}: {value}" for key, value in pack["workspace_template_fields"].items()]
            or ["- none"]
        )
    md_sections.extend(["", "## Active Workspace Items", ""])
    md_sections.extend(
        [f"- {item['work_item_id']}: {item['title']} [{item['status']}]" for item in pack["workspace_active_items"]]
        or ["- none"]
    )
    md_sections.extend(["", "## Blocked Workspace Items", ""])
    md_sections.extend(
        [_blocked_workspace_line(item) for item in pack["workspace_blocked_items"]]
        or ["- none"]
    )
    md_sections.extend(["", "## Pending Workspace Tests", ""])
    md_sections.extend(
        [f"- {item['test_id']}: {item['intent']} [{item['latest_result']}]" for item in pack["workspace_pending_tests"]]
        or ["- none"]
    )
    md_sections.extend(["", "## Workspace Integration Candidates", ""])
    md_sections.extend(
        [
            f"- {item['promotion_id']}: {item['title']} -> {item['target_kind']} [{item['status']}]"
            for item in pack["workspace_integration_candidates"]
        ]
        or ["- none"]
    )

    write_markdown(md_path, "\n".join(md_sections))
    write_json(json_path, pack)
    return pack
