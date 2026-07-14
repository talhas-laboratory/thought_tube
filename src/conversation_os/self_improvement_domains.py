from __future__ import annotations

DOMAIN_KEYWORDS = {
    "ui_ux": ("ui", "ux", "mobile", "screen", "scroll", "layout", "button", "capture surface", "visual"),
    "agent_behavior": ("tone", "answer", "reply", "response", "agent behavior", "too verbose", "too quiet", "prompt", "assistant"),
    "backend_setup": ("backend", "service", "auth", "latency", "timeout", "server", "cloudflared", "api"),
    "tool_creation": ("tool", "cli", "command", "script", "automation"),
    "thought_pipeline_config": ("pipeline", "insight", "retrieval", "ranking", "provenance", "capsule"),
    "bridge_work": ("bridge", "control packet", "sidecar", "session", "routing", "context policy"),
    "deployment_release": ("deploy", "release", "rollback", "version", "production"),
}
DOMAIN_PRIORITY = [
    "deployment_release",
    "bridge_work",
    "thought_pipeline_config",
    "agent_behavior",
    "backend_setup",
    "tool_creation",
    "ui_ux",
]
DOMAIN_RISK = {
    "ui_ux": "medium",
    "agent_behavior": "high",
    "backend_setup": "high",
    "tool_creation": "medium",
    "thought_pipeline_config": "high",
    "bridge_work": "high",
    "deployment_release": "critical",
}
DOMAIN_TESTS = {
    "ui_ux": ["pwa_tests", "build", "browser_smoke"],
    "agent_behavior": ["golden_conversation_examples", "prompt_diff", "bridge_trace_review"],
    "backend_setup": ["python_tests", "service_smoke", "rollback_plan"],
    "tool_creation": ["cli_tests", "dry_run", "docs"],
    "thought_pipeline_config": ["fixture_pipeline_eval", "trace_comparison", "provenance_check"],
    "bridge_work": ["control_packet_tests", "context_policy_tests", "fallback_tests"],
    "deployment_release": ["release_manifest", "gate_report", "rollback_dry_run", "live_smoke"],
}
DOMAIN_LAYER_HINTS = {
    "ui_ux": ["frontend"],
    "agent_behavior": ["agent_config", "bridge"],
    "backend_setup": ["backend", "deployment"],
    "tool_creation": ["tools"],
    "thought_pipeline_config": ["pipelines", "retrieval"],
    "bridge_work": ["bridge", "backend"],
    "deployment_release": ["deployment", "release_management"],
}


def classify_feedback_domain(raw_text: str) -> str:
    text = raw_text.lower()
    scores = {
        domain: sum(1 for keyword in keywords if keyword in text)
        for domain, keywords in DOMAIN_KEYWORDS.items()
    }
    best_score = max(scores.values()) if scores else 0
    if best_score <= 0:
        return "backend_setup"
    for domain in DOMAIN_PRIORITY:
        if scores.get(domain, 0) == best_score:
            return domain
    return "backend_setup"
