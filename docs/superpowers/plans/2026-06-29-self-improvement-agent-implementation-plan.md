# Self Improvement Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a governed self-improvement mode that turns product/system feedback into versioned, test-gated work packets and releases without allowing uncontrolled production mutation.

**Architecture:** Keep the normal `thought_tube_router` agent focused on conversational assistance. Add a separate `thought_tube_self_improve` agent that emits structured `SystemImprovementPacket` records, release plans, rollback plans, and feedback events. Code owns validation, persistence, release manifests, deploy gates, and rollback; the agent proposes and classifies.

**Tech Stack:** Python 3.11, existing `conversation_os` modules, JSON/JSONL runtime state, OpenClaw gateway agents, `product/inner_world_v1/config/runtime.json`, deployment scripts in `tools/`, pytest, PWA Vitest/build where frontend is affected.

---

## Operating Principles

1. **Proposal before mutation.** The self-improvement agent may create packets, plans, and proposed changes. It must not deploy or mutate production config by default.
2. **Version everything that can affect behavior.** Source commit, runtime config, bridge behaviors, agent config, thought pipeline config, PWA bundle, backend service env, and deployed release state must all be identifiable.
3. **No deploy without evidence.** Deployment requires a release candidate manifest, test gate report, rollback plan, and environment verification.
4. **Rollback is a product feature.** Every release must be restorable by exact release id, not by memory or manual reconstruction.
5. **Feedback is typed.** UI/UX, backend, bridge, agent behavior, tool creation, and pipeline configuration feedback follow separate gates.
6. **Sparse and durable.** The system should create high-quality records, not noisy task spam.

---

## Scope

### In Scope

- `thought_tube_self_improve` agent configuration in runtime config.
- New `SystemImprovementPacket`, `FeedbackEvent`, `ReleaseManifest`, `ReleaseGateReport`, and `RollbackPlan` contracts.
- Classification of self-improvement feedback domains:
  - `ui_ux`
  - `agent_behavior`
  - `backend_setup`
  - `tool_creation`
  - `thought_pipeline_config`
  - `bridge_work`
  - `deployment_release`
- Proposal-only self-improvement mode exposed through CLI first.
- Workboard/task packet creation for accepted improvement packets.
- Release manifest generation and validation.
- Deployment gate runner that blocks unsafe deploys.
- Rollback manifest and rollback dry-run support.
- Tests for packet validation, feedback routing, release gates, and deploy-script integration.

### Out Of Scope For First Release

- Fully autonomous production deployment.
- Live code modification by the self-improvement agent.
- Automatic prompt/config mutation without review.
- Multi-user approval workflow.
- Replacing existing deploy scripts.
- Building a full UI for release management.

---

## File Structure

### Create

- `src/conversation_os/self_improvement.py`
  - Owns packet models, validation, domain classification, risk mapping, and feedback-to-gate rules.

- `src/conversation_os/self_improvement_agent.py`
  - Owns OpenClaw invocation for `thought_tube_self_improve`, JSON extraction, and fallback to deterministic packet drafting.

- `src/conversation_os/release_management.py`
  - Owns release manifests, build fingerprints, gate reports, rollback plans, and release status persistence.

- `tools/self_improvement_packet.py`
  - CLI to create/inspect/validate self-improvement packets.

- `tools/inner_world_release.py`
  - CLI to create release candidates, validate gates, inspect current deployed version, and dry-run rollback.

- `product/inner_world_v1/config/self_improvement.json`
  - Declarative domain policy, risk tiers, required gates, and agent permissions.

- `product/inner_world_v1/config/agent_configs/thought_tube_self_improve.json`
  - Versioned agent contract for the self-improvement agent.

- `product/inner_world_v1/releases/README.md`
  - Explains release manifest storage and rollback expectations.

- `tests/test_self_improvement_packets.py`
  - Packet contract and domain/risk mapping tests.

- `tests/test_self_improvement_agent.py`
  - Agent JSON handling and deterministic fallback tests.

- `tests/test_release_management.py`
  - Release manifest, gate report, rollback, and fingerprint tests.

- `tests/test_deploy_release_gates.py`
  - Integration tests around deploy script gate checks.

### Modify

- `product/inner_world_v1/config/runtime.json`
  - Add disabled-by-default `self_improvement` section pointing at `thought_tube_self_improve`.

- `product/inner_world_v1/config/runtime.sample.json`
  - Document safe defaults.

- `tools/deploy_inner_world_to_openclaw.py`
  - Add release gate validation before production deploy.
  - Emit release manifest after successful deploy.

- `tools/deploy_thought_capture_pwa_to_openclaw.py`
  - Add release gate validation and release manifest output for the notes surface.

- `docs/guides/deployment-guide.md`
  - Add versioned release and rollback workflow.

- `docs/workboards/inner-space-agent-ops/README.md`
  - Link self-improvement packets to the existing board protocol.

---

## Data Contracts

### SystemImprovementPacket

```json
{
  "schema_version": "1.0",
  "packet_id": "sip-20260629-example",
  "created_at": "2026-06-29T00:00:00Z",
  "status": "proposed",
  "source": {
    "session_id": "bridge-session-inner-space-codex-deploy-audit",
    "turn_id": "bridge-turn-...",
    "raw_user_signal": "The capture page is slow after deployment.",
    "provenance_refs": []
  },
  "classification": {
    "domain": "backend_setup",
    "risk": "high",
    "affected_layers": ["backend", "deployment"],
    "change_type": "reliability_fix"
  },
  "problem": {
    "observed": "Live compose latency exceeded the release budget.",
    "expected": "Live compose returns a bridge-agent answer under the configured timeout.",
    "evidence": []
  },
  "proposal": {
    "summary": "Investigate and tighten compose runtime path.",
    "files_or_configs": ["src/conversation_os/mobile_capture_compose.py"],
    "runtime_effect": "Changes bridge execution latency for the notes surface.",
    "alternatives_considered": []
  },
  "gates": {
    "required_tests": ["tests/test_mobile_capture_compose.py"],
    "required_smokes": ["authenticated_notes_compose"],
    "required_reviews": ["release_gate_review"],
    "rollback_required": true
  },
  "release": {
    "version_bump": "patch",
    "deploy_allowed": false,
    "approval_required": true,
    "rollback_plan": "Restore previous release manifest and restart affected services."
  }
}
```

### ReleaseManifest

```json
{
  "schema_version": "1.0",
  "release_id": "inner-world-20260629T000000Z",
  "created_at": "2026-06-29T00:00:00Z",
  "source": {
    "git_commit": "unknown",
    "git_status_clean": false,
    "branch": "main"
  },
  "artifacts": {
    "backend": {
      "paths": ["src/conversation_os", "tools"],
      "fingerprint": "sha256:..."
    },
    "runtime_config": {
      "paths": ["product/inner_world_v1/config/runtime.json"],
      "fingerprint": "sha256:..."
    },
    "pwa_bundle": {
      "paths": ["product/thought_capture_pwa/dist"],
      "fingerprint": "sha256:..."
    },
    "agent_configs": {
      "paths": ["product/inner_world_v1/config/agent_configs"],
      "fingerprint": "sha256:..."
    }
  },
  "gates": {
    "status": "blocked",
    "report_path": "product/inner_world_v1/releases/release-id/gate_report.json"
  },
  "rollback": {
    "previous_release_id": "",
    "plan_path": "product/inner_world_v1/releases/release-id/rollback_plan.json"
  }
}
```

---

## Phase 0: Baseline Inventory And Safety Boundary

**Outcome:** The repo records the exact current deployment model and defines what self-improvement is allowed to do.

**Files:**
- Create: `product/inner_world_v1/config/self_improvement.json`
- Create: `product/inner_world_v1/config/agent_configs/thought_tube_self_improve.json`
- Modify: `product/inner_world_v1/config/runtime.json`
- Modify: `product/inner_world_v1/config/runtime.sample.json`
- Test: `tests/test_self_improvement_packets.py`

- [ ] **Step 1: Write failing config tests**

Create `tests/test_self_improvement_packets.py` with tests that assert the self-improvement config exists, is disabled by default, and defines all feedback domains.

```python
from pathlib import Path
import json


ROOT = Path(__file__).resolve().parents[1]


def test_self_improvement_config_declares_required_domains():
    path = ROOT / "product" / "inner_world_v1" / "config" / "self_improvement.json"
    payload = json.loads(path.read_text())
    domains = {item["domain"] for item in payload["feedback_domains"]}
    assert domains == {
        "ui_ux",
        "agent_behavior",
        "backend_setup",
        "tool_creation",
        "thought_pipeline_config",
        "bridge_work",
        "deployment_release",
    }


def test_runtime_self_improvement_is_proposal_only_by_default():
    path = ROOT / "product" / "inner_world_v1" / "config" / "runtime.sample.json"
    payload = json.loads(path.read_text())
    config = payload["self_improvement"]
    assert config["enabled"] is False
    assert config["agent"] == "thought_tube_self_improve"
    assert config["default_authority"] == "propose"
    assert config["allow_production_deploy"] is False
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
pytest tests/test_self_improvement_packets.py -q
```

Expected: fails because config files/sections do not exist yet.

- [ ] **Step 3: Add self-improvement policy config**

Create `product/inner_world_v1/config/self_improvement.json`:

```json
{
  "schema_version": "1.0",
  "updated_at": "2026-06-29T00:00:00Z",
  "agent_id": "thought_tube_self_improve",
  "default_authority": "propose",
  "allow_direct_code_mutation": false,
  "allow_production_deploy": false,
  "feedback_domains": [
    {
      "domain": "ui_ux",
      "default_risk": "medium",
      "required_gates": ["pwa_tests", "build", "browser_smoke"],
      "artifact_roots": ["product/thought_capture_pwa", "product/mobile_surface_v1", "product/inner_world_v1/miniapp"]
    },
    {
      "domain": "agent_behavior",
      "default_risk": "high",
      "required_gates": ["golden_conversation_examples", "prompt_diff", "bridge_trace_review"],
      "artifact_roots": ["product/inner_world_v1/config/agent_configs", "product/inner_world_v1/config/bridge_behaviors"]
    },
    {
      "domain": "backend_setup",
      "default_risk": "high",
      "required_gates": ["python_tests", "service_smoke", "rollback_plan"],
      "artifact_roots": ["src/conversation_os", "tools", "product/inner_world_v1/config"]
    },
    {
      "domain": "tool_creation",
      "default_risk": "medium",
      "required_gates": ["cli_tests", "dry_run", "docs"],
      "artifact_roots": ["tools", "src/conversation_os"]
    },
    {
      "domain": "thought_pipeline_config",
      "default_risk": "high",
      "required_gates": ["fixture_pipeline_eval", "trace_comparison", "provenance_check"],
      "artifact_roots": ["product/inner_world_v1/pipelines", "product/inner_world_v1/config"]
    },
    {
      "domain": "bridge_work",
      "default_risk": "high",
      "required_gates": ["control_packet_tests", "context_policy_tests", "fallback_tests"],
      "artifact_roots": ["src/conversation_os", "product/inner_world_v1/config/bridge_behaviors"]
    },
    {
      "domain": "deployment_release",
      "default_risk": "critical",
      "required_gates": ["release_manifest", "gate_report", "rollback_dry_run", "live_smoke"],
      "artifact_roots": ["tools", "docs/guides", "product/inner_world_v1/releases"]
    }
  ]
}
```

- [ ] **Step 4: Add versioned agent contract**

Create `product/inner_world_v1/config/agent_configs/thought_tube_self_improve.json`:

```json
{
  "schema_version": "1.0",
  "agent_id": "thought_tube_self_improve",
  "version": "0.1.0",
  "role": "governed_system_improvement_agent",
  "model": "moonshot/kimi-k2.5",
  "thinking": "high",
  "timeout_seconds": 90,
  "default_authority": "propose",
  "allowed_outputs": [
    "SystemImprovementPacket",
    "ReleasePlan",
    "RollbackPlan",
    "ReleaseGateReport",
    "FeedbackEvent"
  ],
  "forbidden_actions": [
    "direct_production_deploy",
    "direct_runtime_config_mutation",
    "direct_agent_prompt_mutation",
    "silent_test_bypass"
  ],
  "required_behavior": [
    "classify the feedback domain",
    "assign risk",
    "name affected layers",
    "define tests and smokes",
    "define rollback path",
    "preserve provenance"
  ]
}
```

- [ ] **Step 5: Add runtime config section**

Modify both `runtime.json` and `runtime.sample.json`:

```json
{
  "self_improvement": {
    "enabled": false,
    "agent": "thought_tube_self_improve",
    "model": "moonshot/kimi-k2.5",
    "thinking": "high",
    "timeout_seconds": 90,
    "default_authority": "propose",
    "allow_production_deploy": false,
    "config_path": "product/inner_world_v1/config/self_improvement.json",
    "agent_config_path": "product/inner_world_v1/config/agent_configs/thought_tube_self_improve.json"
  }
}
```

- [ ] **Step 6: Run config tests**

Run:

```bash
pytest tests/test_self_improvement_packets.py -q
```

Expected: passes.

---

## Phase 1: Packet Contracts And Feedback Classification

**Outcome:** The system can deterministically create and validate self-improvement packets before any agent integration.

**Files:**
- Create: `src/conversation_os/self_improvement.py`
- Modify: `tests/test_self_improvement_packets.py`

- [ ] **Step 1: Add failing packet contract tests**

Extend `tests/test_self_improvement_packets.py`:

```python
from conversation_os.self_improvement import (
    classify_feedback_domain,
    default_packet_for_feedback,
    validate_system_improvement_packet,
)


def test_classify_bridge_feedback():
    packet = default_packet_for_feedback(
        raw_text="The bridge pulled too much context and leaked sidecar material.",
        session_id="session-1",
        turn_id="turn-1",
    )
    assert packet["classification"]["domain"] == "bridge_work"
    assert packet["classification"]["risk"] == "high"
    assert "context_policy_tests" in packet["gates"]["required_tests"]


def test_classify_ui_feedback():
    assert classify_feedback_domain("The mobile capture UI jumps when the answer streams.") == "ui_ux"


def test_packet_validation_rejects_deploy_allowed_without_approval():
    packet = default_packet_for_feedback(
        raw_text="Deploy this runtime config change.",
        session_id="session-1",
        turn_id="turn-1",
    )
    packet["release"]["deploy_allowed"] = True
    packet["release"]["approval_required"] = False
    errors = validate_system_improvement_packet(packet)
    assert "deploy_allowed requires approval_required" in errors
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
pytest tests/test_self_improvement_packets.py -q
```

Expected: fails because `conversation_os.self_improvement` does not exist.

- [ ] **Step 3: Implement deterministic packet generation**

Create `src/conversation_os/self_improvement.py` with:

```python
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from typing import Any, Dict, List


DOMAIN_KEYWORDS = {
    "ui_ux": ("ui", "ux", "mobile", "screen", "scroll", "layout", "button", "capture surface", "visual"),
    "agent_behavior": ("tone", "answer", "agent behavior", "too verbose", "too quiet", "prompt", "assistant"),
    "backend_setup": ("backend", "service", "auth", "latency", "timeout", "server", "cloudflared", "api"),
    "tool_creation": ("tool", "cli", "command", "script", "automation"),
    "thought_pipeline_config": ("pipeline", "insight", "retrieval", "ranking", "provenance", "capsule"),
    "bridge_work": ("bridge", "context", "control packet", "sidecar", "session", "routing"),
    "deployment_release": ("deploy", "release", "rollback", "version", "production"),
}

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


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def classify_feedback_domain(raw_text: str) -> str:
    text = raw_text.lower()
    scores = {
        domain: sum(1 for keyword in keywords if keyword in text)
        for domain, keywords in DOMAIN_KEYWORDS.items()
    }
    best_domain = max(scores, key=scores.get)
    if scores[best_domain] == 0:
        return "backend_setup"
    return best_domain


def _packet_id(raw_text: str, session_id: str, turn_id: str) -> str:
    digest = sha256(f"{session_id}\\n{turn_id}\\n{raw_text}".encode("utf-8")).hexdigest()[:12]
    return f"sip-{digest}"


def default_packet_for_feedback(raw_text: str, session_id: str, turn_id: str) -> Dict[str, Any]:
    domain = classify_feedback_domain(raw_text)
    return {
        "schema_version": "1.0",
        "packet_id": _packet_id(raw_text, session_id, turn_id),
        "created_at": utc_now(),
        "status": "proposed",
        "source": {
            "session_id": session_id,
            "turn_id": turn_id,
            "raw_user_signal": raw_text,
            "provenance_refs": [],
        },
        "classification": {
            "domain": domain,
            "risk": DOMAIN_RISK[domain],
            "affected_layers": [],
            "change_type": "system_feedback",
        },
        "problem": {
            "observed": raw_text,
            "expected": "",
            "evidence": [],
        },
        "proposal": {
            "summary": "",
            "files_or_configs": [],
            "runtime_effect": "",
            "alternatives_considered": [],
        },
        "gates": {
            "required_tests": list(DOMAIN_TESTS[domain]),
            "required_smokes": [],
            "required_reviews": ["release_gate_review"] if DOMAIN_RISK[domain] in {"high", "critical"} else [],
            "rollback_required": DOMAIN_RISK[domain] in {"high", "critical"},
        },
        "release": {
            "version_bump": "patch",
            "deploy_allowed": False,
            "approval_required": True,
            "rollback_plan": "",
        },
    }


def validate_system_improvement_packet(packet: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    for key in ["schema_version", "packet_id", "source", "classification", "problem", "proposal", "gates", "release"]:
        if key not in packet:
            errors.append(f"missing {key}")
    release = packet.get("release", {})
    if release.get("deploy_allowed") and not release.get("approval_required"):
        errors.append("deploy_allowed requires approval_required")
    classification = packet.get("classification", {})
    if classification.get("domain") not in DOMAIN_RISK:
        errors.append("unknown feedback domain")
    if classification.get("risk") == "critical" and not packet.get("gates", {}).get("rollback_required"):
        errors.append("critical risk requires rollback_required")
    return errors
```

- [ ] **Step 4: Run packet tests**

Run:

```bash
pytest tests/test_self_improvement_packets.py -q
```

Expected: passes.

---

## Phase 2: Self-Improvement Agent Boundary

**Outcome:** The system can ask `thought_tube_self_improve` for a structured packet and safely fall back when the agent response is invalid.

**Files:**
- Create: `src/conversation_os/self_improvement_agent.py`
- Create: `tests/test_self_improvement_agent.py`

- [ ] **Step 1: Write failing agent boundary tests**

Create `tests/test_self_improvement_agent.py`:

```python
from unittest.mock import Mock

from conversation_os.self_improvement_agent import draft_self_improvement_packet


def test_agent_packet_accepts_valid_json(monkeypatch):
    completed = Mock()
    completed.returncode = 0
    completed.stdout = '{"packet_id":"sip-agent","schema_version":"1.0","source":{"session_id":"s","turn_id":"t","raw_user_signal":"x","provenance_refs":[]},"classification":{"domain":"ui_ux","risk":"medium","affected_layers":[],"change_type":"system_feedback"},"problem":{"observed":"x","expected":"","evidence":[]},"proposal":{"summary":"","files_or_configs":[],"runtime_effect":"","alternatives_considered":[]},"gates":{"required_tests":["pwa_tests"],"required_smokes":[],"required_reviews":[],"rollback_required":false},"release":{"version_bump":"patch","deploy_allowed":false,"approval_required":true,"rollback_plan":""}}'
    completed.stderr = ""
    monkeypatch.setattr("subprocess.run", lambda *args, **kwargs: completed)

    packet = draft_self_improvement_packet("ui is jumpy", "s", "t", use_agent=True)

    assert packet["packet_id"] == "sip-agent"
    assert packet["classification"]["domain"] == "ui_ux"


def test_agent_packet_falls_back_on_invalid_json(monkeypatch):
    completed = Mock()
    completed.returncode = 0
    completed.stdout = "I think you should improve the bridge."
    completed.stderr = ""
    monkeypatch.setattr("subprocess.run", lambda *args, **kwargs: completed)

    packet = draft_self_improvement_packet("bridge leaked context", "s", "t", use_agent=True)

    assert packet["packet_id"].startswith("sip-")
    assert packet["classification"]["domain"] == "bridge_work"
    assert packet["attributes"]["fallback_reason"] == "invalid_agent_packet"
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
pytest tests/test_self_improvement_agent.py -q
```

Expected: fails because module does not exist.

- [ ] **Step 3: Implement agent invocation wrapper**

Create `src/conversation_os/self_improvement_agent.py`:

```python
from __future__ import annotations

import json
import subprocess
from typing import Any, Dict

from .self_improvement import default_packet_for_feedback, validate_system_improvement_packet


def _extract_json_object(text: str) -> Dict[str, Any]:
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end < start:
        raise ValueError("no json object found")
    return json.loads(text[start : end + 1])


def _agent_prompt(raw_text: str, session_id: str, turn_id: str) -> str:
    return (
        "You are thought_tube_self_improve. Emit one SystemImprovementPacket JSON object only. "
        "Do not answer conversationally. Do not claim deploy authority. "
        f"session_id={session_id}\\nturn_id={turn_id}\\nraw_user_signal={raw_text}"
    )


def draft_self_improvement_packet(
    raw_text: str,
    session_id: str,
    turn_id: str,
    *,
    use_agent: bool = False,
    timeout_seconds: int = 90,
) -> Dict[str, Any]:
    if not use_agent:
        return default_packet_for_feedback(raw_text, session_id, turn_id)

    try:
        completed = subprocess.run(
            [
                "openclaw",
                "agent",
                "--agent",
                "thought_tube_self_improve",
                "--thinking",
                "high",
                "--message",
                _agent_prompt(raw_text, session_id, turn_id),
                "--json",
            ],
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
        if completed.returncode != 0:
            raise RuntimeError(completed.stderr.strip() or "openclaw exited nonzero")
        packet = _extract_json_object(completed.stdout)
        errors = validate_system_improvement_packet(packet)
        if errors:
            raise ValueError("; ".join(errors))
        return packet
    except Exception:
        packet = default_packet_for_feedback(raw_text, session_id, turn_id)
        packet.setdefault("attributes", {})["fallback_reason"] = "invalid_agent_packet"
        return packet
```

- [ ] **Step 4: Run agent boundary tests**

Run:

```bash
pytest tests/test_self_improvement_agent.py tests/test_self_improvement_packets.py -q
```

Expected: passes.

---

## Phase 3: CLI And Workboard Attachment

**Outcome:** A user or agent can create, inspect, and validate self-improvement packets locally, then attach them to `docs/workboards/inner-space-agent-ops`.

**Files:**
- Create: `tools/self_improvement_packet.py`
- Modify: `docs/workboards/inner-space-agent-ops/README.md`
- Test: `tests/test_self_improvement_cli.py`

- [ ] **Step 1: Write failing CLI tests**

Create `tests/test_self_improvement_cli.py`:

```python
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_self_improvement_packet_cli_dry_run_outputs_packet():
    result = subprocess.run(
        [
            sys.executable,
            "tools/self_improvement_packet.py",
            "create",
            "--text",
            "The bridge should not leak sidecar context.",
            "--session-id",
            "s",
            "--turn-id",
            "t",
            "--dry-run",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    payload = json.loads(result.stdout)
    assert payload["classification"]["domain"] == "bridge_work"
    assert payload["release"]["deploy_allowed"] is False
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
pytest tests/test_self_improvement_cli.py -q
```

Expected: fails because CLI does not exist.

- [ ] **Step 3: Implement minimal CLI**

Create `tools/self_improvement_packet.py`:

```python
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from conversation_os.self_improvement_agent import draft_self_improvement_packet  # noqa: E402
from conversation_os.self_improvement import validate_system_improvement_packet  # noqa: E402


def _cmd_create(args: argparse.Namespace) -> int:
    packet = draft_self_improvement_packet(
        args.text,
        args.session_id,
        args.turn_id,
        use_agent=args.use_agent,
    )
    if args.dry_run:
        print(json.dumps(packet, indent=2, sort_keys=True))
        return 0
    out_dir = ROOT / "docs" / "workboards" / "inner-space-agent-ops" / "inbox"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{packet['packet_id']}.json"
    out_path.write_text(json.dumps(packet, indent=2, sort_keys=True) + "\\n")
    print(str(out_path))
    return 0


def _cmd_validate(args: argparse.Namespace) -> int:
    packet = json.loads(Path(args.path).read_text())
    errors = validate_system_improvement_packet(packet)
    if errors:
        print("\\n".join(errors), file=sys.stderr)
        return 1
    print("ok")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Create or validate self-improvement packets.")
    sub = parser.add_subparsers(dest="cmd", required=True)
    create = sub.add_parser("create")
    create.add_argument("--text", required=True)
    create.add_argument("--session-id", required=True)
    create.add_argument("--turn-id", required=True)
    create.add_argument("--use-agent", action="store_true")
    create.add_argument("--dry-run", action="store_true")
    create.set_defaults(func=_cmd_create)
    validate = sub.add_parser("validate")
    validate.add_argument("path")
    validate.set_defaults(func=_cmd_validate)
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Document board attachment**

Add to `docs/workboards/inner-space-agent-ops/README.md`:

````markdown
## Self-Improvement Packet Intake

Self-improvement packets enter through `inbox/` and must be triaged before they become tasks.

Packet creation:

```bash
python3 tools/self_improvement_packet.py create \
  --text "The bridge should not leak sidecar context." \
  --session-id bridge-session-inner-space-codex-deploy-audit \
  --turn-id bridge-turn-example
```

Triage rules:

- `low` and `medium` risk packets may become normal board tasks.
- `high` risk packets require acceptance criteria, tests, and rollback notes before work starts.
- `critical` risk packets require an explicit decision record before implementation.
````

- [ ] **Step 5: Run CLI tests**

Run:

```bash
pytest tests/test_self_improvement_cli.py tests/test_self_improvement_agent.py tests/test_self_improvement_packets.py -q
```

Expected: passes.

---

## Phase 4: Release Manifest And Version Fingerprints

**Outcome:** The repo can produce a release candidate manifest with fingerprints for source, config, agent config, PWA bundle, and runtime-affecting artifacts.

**Files:**
- Create: `src/conversation_os/release_management.py`
- Create: `tools/inner_world_release.py`
- Create: `product/inner_world_v1/releases/README.md`
- Create: `tests/test_release_management.py`

- [ ] **Step 1: Write failing release manifest tests**

Create `tests/test_release_management.py`:

```python
from pathlib import Path

from conversation_os.release_management import build_release_manifest, validate_release_manifest


ROOT = Path(__file__).resolve().parents[1]


def test_build_release_manifest_contains_expected_artifacts():
    manifest = build_release_manifest(ROOT, release_id="test-release")
    assert manifest["release_id"] == "test-release"
    assert "runtime_config" in manifest["artifacts"]
    assert "agent_configs" in manifest["artifacts"]
    assert manifest["gates"]["status"] == "blocked"


def test_release_manifest_validation_requires_rollback_plan():
    manifest = build_release_manifest(ROOT, release_id="test-release")
    manifest["rollback"]["plan_path"] = ""
    errors = validate_release_manifest(manifest)
    assert "rollback plan path is required" in errors
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
pytest tests/test_release_management.py -q
```

Expected: fails because release module does not exist.

- [ ] **Step 3: Implement release manifest builder**

Create `src/conversation_os/release_management.py`:

```python
from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _hash_paths(root: Path, paths: Iterable[str]) -> str:
    digest = hashlib.sha256()
    for rel in sorted(paths):
        path = root / rel
        if not path.exists():
            digest.update(f"missing:{rel}\\n".encode("utf-8"))
            continue
        if path.is_file():
            digest.update(rel.encode("utf-8"))
            digest.update(path.read_bytes())
            continue
        for child in sorted(p for p in path.rglob("*") if p.is_file()):
            digest.update(str(child.relative_to(root)).encode("utf-8"))
            digest.update(child.read_bytes())
    return "sha256:" + digest.hexdigest()


def _git_value(root: Path, args: List[str], default: str) -> str:
    try:
        result = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=False)
    except OSError:
        return default
    if result.returncode != 0:
        return default
    return result.stdout.strip() or default


def build_release_manifest(root: Path, release_id: str | None = None) -> Dict[str, Any]:
    release_id = release_id or "inner-world-" + _utc_now().replace(":", "").replace("-", "")
    artifact_paths = {
        "backend": ["src/conversation_os", "tools"],
        "runtime_config": ["product/inner_world_v1/config/runtime.json"],
        "bridge_behaviors": ["product/inner_world_v1/config/bridge_behaviors"],
        "agent_configs": ["product/inner_world_v1/config/agent_configs"],
        "pipelines": ["product/inner_world_v1/pipelines"],
        "pwa_bundle": ["product/thought_capture_pwa/dist"],
    }
    artifacts = {
        key: {"paths": paths, "fingerprint": _hash_paths(root, paths)}
        for key, paths in artifact_paths.items()
    }
    dirty = _git_value(root, ["status", "--short"], "")
    return {
        "schema_version": "1.0",
        "release_id": release_id,
        "created_at": _utc_now(),
        "source": {
            "git_commit": _git_value(root, ["rev-parse", "HEAD"], "unknown"),
            "branch": _git_value(root, ["branch", "--show-current"], "unknown"),
            "git_status_clean": dirty == "",
        },
        "artifacts": artifacts,
        "gates": {
            "status": "blocked",
            "report_path": f"product/inner_world_v1/releases/{release_id}/gate_report.json",
        },
        "rollback": {
            "previous_release_id": "",
            "plan_path": f"product/inner_world_v1/releases/{release_id}/rollback_plan.json",
        },
    }


def validate_release_manifest(manifest: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    if not manifest.get("release_id"):
        errors.append("release_id is required")
    if not manifest.get("rollback", {}).get("plan_path"):
        errors.append("rollback plan path is required")
    if "runtime_config" not in manifest.get("artifacts", {}):
        errors.append("runtime_config artifact is required")
    if "agent_configs" not in manifest.get("artifacts", {}):
        errors.append("agent_configs artifact is required")
    return errors


def write_release_manifest(root: Path, manifest: Dict[str, Any]) -> Path:
    release_dir = root / "product" / "inner_world_v1" / "releases" / manifest["release_id"]
    release_dir.mkdir(parents=True, exist_ok=True)
    path = release_dir / "manifest.json"
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\\n")
    return path
```

- [ ] **Step 4: Implement release CLI**

Create `tools/inner_world_release.py`:

```python
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from conversation_os.release_management import (  # noqa: E402
    build_release_manifest,
    validate_release_manifest,
    write_release_manifest,
)


def _cmd_candidate(args: argparse.Namespace) -> int:
    manifest = build_release_manifest(ROOT, release_id=args.release_id)
    errors = validate_release_manifest(manifest)
    if errors:
        print("\\n".join(errors), file=sys.stderr)
        return 1
    if args.dry_run:
        print(json.dumps(manifest, indent=2, sort_keys=True))
        return 0
    print(write_release_manifest(ROOT, manifest))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Manage Inner World release manifests.")
    sub = parser.add_subparsers(dest="cmd", required=True)
    candidate = sub.add_parser("candidate")
    candidate.add_argument("--release-id")
    candidate.add_argument("--dry-run", action="store_true")
    candidate.set_defaults(func=_cmd_candidate)
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5: Add releases README**

Create `product/inner_world_v1/releases/README.md`:

```markdown
# Inner World Releases

This directory stores release manifests, gate reports, and rollback plans.

Each release directory must include:

- `manifest.json`
- `gate_report.json`
- `rollback_plan.json`

Production deployment should point to one exact release id. Rollback restores the previous release manifest and its artifact/config snapshot.
```

- [ ] **Step 6: Run release tests**

Run:

```bash
pytest tests/test_release_management.py -q
python3 tools/inner_world_release.py candidate --release-id test-release --dry-run
```

Expected: tests pass and CLI prints a manifest.

---

## Phase 5: Gate Runner And Deployment Blocking

**Outcome:** Deploy scripts can require release gate evidence and block production deployment when gates fail.

**Files:**
- Modify: `src/conversation_os/release_management.py`
- Modify: `tools/deploy_inner_world_to_openclaw.py`
- Modify: `tools/deploy_thought_capture_pwa_to_openclaw.py`
- Create: `tests/test_deploy_release_gates.py`

- [ ] **Step 1: Write failing gate tests**

Create `tests/test_deploy_release_gates.py`:

```python
from conversation_os.release_management import evaluate_release_gates


def test_release_gates_block_missing_required_checks():
    report = evaluate_release_gates(
        required_checks=["python_tests", "rollback_dry_run"],
        completed_checks=["python_tests"],
    )
    assert report["status"] == "blocked"
    assert report["missing_checks"] == ["rollback_dry_run"]


def test_release_gates_pass_when_required_checks_complete():
    report = evaluate_release_gates(
        required_checks=["python_tests", "rollback_dry_run"],
        completed_checks=["rollback_dry_run", "python_tests"],
    )
    assert report["status"] == "passed"
    assert report["missing_checks"] == []
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
pytest tests/test_deploy_release_gates.py -q
```

Expected: fails because `evaluate_release_gates` does not exist.

- [ ] **Step 3: Add gate evaluator**

Add to `src/conversation_os/release_management.py`:

```python
def evaluate_release_gates(required_checks: List[str], completed_checks: List[str]) -> Dict[str, Any]:
    completed = set(completed_checks)
    missing = [check for check in required_checks if check not in completed]
    return {
        "schema_version": "1.0",
        "status": "passed" if not missing else "blocked",
        "required_checks": list(required_checks),
        "completed_checks": list(completed_checks),
        "missing_checks": missing,
    }
```

- [ ] **Step 4: Add deploy script gate flag**

Modify both deploy scripts to accept:

```python
parser.add_argument(
    "--release-gate-report",
    help="Path to a release gate report JSON. Production deploy is blocked unless status is passed.",
)
parser.add_argument(
    "--allow-ungated-deploy",
    action="store_true",
    help="Bypass release gate report. Use only for emergency manual recovery.",
)
```

Add a helper near argument handling:

```python
def _assert_release_gate(args: argparse.Namespace) -> None:
    if getattr(args, "allow_ungated_deploy", False):
        return
    report_path = getattr(args, "release_gate_report", None)
    if not report_path:
        raise SystemExit("--release-gate-report is required unless --allow-ungated-deploy is set")
    report = json.loads(Path(report_path).read_text())
    if report.get("status") != "passed":
        raise SystemExit(f"release gates blocked deploy: {report.get('missing_checks', [])}")
```

Call `_assert_release_gate(args)` before any remote sync or service restart.

- [ ] **Step 5: Run gate tests**

Run:

```bash
pytest tests/test_deploy_release_gates.py tests/test_release_management.py -q
```

Expected: passes.

---

## Phase 6: Domain-Specific Feedback Gates

**Outcome:** Each feedback domain maps to concrete test and smoke requirements, so the self-improvement agent cannot treat all changes as generic.

**Files:**
- Modify: `src/conversation_os/self_improvement.py`
- Modify: `tests/test_self_improvement_packets.py`

- [ ] **Step 1: Add domain gate tests**

Add tests:

```python
def test_backend_feedback_requires_service_smoke_and_rollback():
    packet = default_packet_for_feedback("backend auth deploy broke the API", "s", "t")
    assert packet["classification"]["domain"] == "backend_setup"
    assert "service_smoke" in packet["gates"]["required_tests"]
    assert packet["gates"]["rollback_required"] is True


def test_agent_behavior_feedback_requires_examples_and_trace_review():
    packet = default_packet_for_feedback("the assistant tone is too verbose and ignores context", "s", "t")
    assert packet["classification"]["domain"] == "agent_behavior"
    assert "golden_conversation_examples" in packet["gates"]["required_tests"]
    assert "bridge_trace_review" in packet["gates"]["required_tests"]


def test_deployment_feedback_is_critical():
    packet = default_packet_for_feedback("we need rollback before production deploy", "s", "t")
    assert packet["classification"]["domain"] == "deployment_release"
    assert packet["classification"]["risk"] == "critical"
    assert "rollback_dry_run" in packet["gates"]["required_tests"]
```

- [ ] **Step 2: Run tests**

Run:

```bash
pytest tests/test_self_improvement_packets.py -q
```

Expected: passes after tuning keyword precedence if needed.

- [ ] **Step 3: Fix classification precedence if tests fail**

If `deployment_release` loses to `backend_setup`, update `classify_feedback_domain` to apply explicit priority:

```python
DOMAIN_PRIORITY = [
    "deployment_release",
    "bridge_work",
    "thought_pipeline_config",
    "agent_behavior",
    "backend_setup",
    "tool_creation",
    "ui_ux",
]
```

Then select the highest-priority domain among nonzero scores.

---

## Phase 7: Rollback Plan Dry Run

**Outcome:** The release CLI can create a rollback plan and validate that the previous release manifest is available before deployment.

**Files:**
- Modify: `src/conversation_os/release_management.py`
- Modify: `tools/inner_world_release.py`
- Modify: `tests/test_release_management.py`

- [ ] **Step 1: Add rollback tests**

Add:

```python
from conversation_os.release_management import build_rollback_plan


def test_build_rollback_plan_targets_previous_release():
    plan = build_rollback_plan(
        current_release_id="inner-world-new",
        previous_release_id="inner-world-old",
    )
    assert plan["current_release_id"] == "inner-world-new"
    assert plan["target_release_id"] == "inner-world-old"
    assert plan["status"] == "dry_run"
    assert "restore_manifest" in plan["steps"]
```

- [ ] **Step 2: Implement rollback plan builder**

Add to `release_management.py`:

```python
def build_rollback_plan(current_release_id: str, previous_release_id: str) -> Dict[str, Any]:
    return {
        "schema_version": "1.0",
        "current_release_id": current_release_id,
        "target_release_id": previous_release_id,
        "status": "dry_run",
        "steps": [
            "restore_manifest",
            "restore_runtime_config",
            "restore_agent_configs",
            "restore_pwa_bundle_if_present",
            "restart_inner_world_service",
            "restart_openclaw_miniapps_if_needed",
            "run_post_rollback_smoke",
        ],
    }
```

- [ ] **Step 3: Add CLI rollback dry run**

Add subcommand:

```python
rollback = sub.add_parser("rollback-plan")
rollback.add_argument("--current-release-id", required=True)
rollback.add_argument("--previous-release-id", required=True)
rollback.set_defaults(func=_cmd_rollback_plan)
```

Add handler:

```python
def _cmd_rollback_plan(args: argparse.Namespace) -> int:
    from conversation_os.release_management import build_rollback_plan

    plan = build_rollback_plan(args.current_release_id, args.previous_release_id)
    print(json.dumps(plan, indent=2, sort_keys=True))
    return 0
```

- [ ] **Step 4: Run rollback tests**

Run:

```bash
pytest tests/test_release_management.py -q
python3 tools/inner_world_release.py rollback-plan --current-release-id inner-world-new --previous-release-id inner-world-old
```

Expected: tests pass and CLI prints rollback plan JSON.

---

## Phase 8: Documentation And Deployment Guide Integration

**Outcome:** A future agent can operate the system without guessing the release workflow.

**Files:**
- Modify: `docs/guides/deployment-guide.md`
- Modify: `docs/workboards/inner-space-agent-ops/README.md`
- Create: `docs/implementation/self-improvement-agent/README.md`

- [ ] **Step 1: Add implementation README**

Create `docs/implementation/self-improvement-agent/README.md`:

```markdown
# Self-Improvement Agent

The self-improvement agent is `thought_tube_self_improve`.

It converts product/system feedback into governed update packets. It does not deploy by default.

## Runtime Contract

- Normal assistant: `thought_tube_router`
- Self-improvement agent: `thought_tube_self_improve`
- Default authority: `propose`
- Production deploy authority: disabled

## Feedback Domains

- `ui_ux`
- `agent_behavior`
- `backend_setup`
- `tool_creation`
- `thought_pipeline_config`
- `bridge_work`
- `deployment_release`

## Required Flow

1. Create `SystemImprovementPacket`.
2. Triage packet into workboard task.
3. Implement with tests.
4. Create release candidate manifest.
5. Run gate report.
6. Deploy only if gates pass and rollback exists.
7. Record post-deploy evidence.
```

- [ ] **Step 2: Update deployment guide**

Add a section:

````markdown
## Versioned Releases And Rollback

Production deploys should be attached to a release manifest.

Create a candidate:

```bash
python3 tools/inner_world_release.py candidate --release-id inner-world-YYYYMMDDTHHMMSSZ
```

Deploy scripts require a passing gate report unless explicitly bypassed for emergency recovery:

```bash
python3 tools/deploy_inner_world_to_openclaw.py --release-gate-report product/inner_world_v1/releases/<release_id>/gate_report.json
```

Rollback planning:

```bash
python3 tools/inner_world_release.py rollback-plan \
  --current-release-id <current> \
  --previous-release-id <previous>
```
````

- [ ] **Step 3: Run docs and focused tests**

Run:

```bash
pytest \
  tests/test_self_improvement_packets.py \
  tests/test_self_improvement_agent.py \
  tests/test_self_improvement_cli.py \
  tests/test_release_management.py \
  tests/test_deploy_release_gates.py -q
```

Expected: passes.

---

## Phase 9: First Live Dry Run

**Outcome:** The system can process a real self-improvement request without changing production.

**Files:**
- No required code changes if previous phases passed.

- [ ] **Step 1: Create a packet from this project thread**

Run:

```bash
python3 tools/self_improvement_packet.py create \
  --text "Create versioned rollback and gate-controlled deployment for self-improvement mode." \
  --session-id bridge-session-inner-space-codex-deploy-audit \
  --turn-id bridge-turn-self-improvement-plan \
  --dry-run
```

Expected: JSON packet with `deployment_release` or `backend_setup`, `deploy_allowed=false`, and rollback gates.

- [ ] **Step 2: Create a release candidate dry run**

Run:

```bash
python3 tools/inner_world_release.py candidate --release-id self-improve-dry-run --dry-run
```

Expected: release manifest JSON includes source, runtime config, agent configs, pipeline configs, and blocked gate status.

- [ ] **Step 3: Confirm deploy scripts block ungated deploy**

Run the deploy script in the safest available dry-run/test mode if present. If no dry-run exists, test this behavior only through `tests/test_deploy_release_gates.py` until a dry-run flag is added.

- [ ] **Step 4: Record result in workboard**

Add a short entry to `docs/workboards/inner-space-agent-ops/UPDATES.jsonl` with:

```json
{"kind":"self_improvement_dry_run","status":"verified","packet_domain":"deployment_release","deploy_allowed":false}
```

---

## Acceptance Criteria

The implementation is complete when:

- `thought_tube_self_improve` has a versioned config file.
- Runtime config exposes self-improvement mode disabled by default.
- A self-improvement packet can be created deterministically without OpenClaw.
- OpenClaw agent invocation accepts valid packet JSON and falls back on invalid output.
- Packets classify all required domains and assign risk/gates.
- Release manifests fingerprint backend, config, bridge behaviors, agent configs, pipelines, and PWA bundle.
- Deploy scripts can block production deployment without a passing release gate report.
- Rollback plan dry-run exists for every release candidate.
- Deployment guide explains release candidate, gate report, deploy, and rollback flow.
- Focused tests pass.

---

## Verification Commands

Run the focused self-improvement suite:

```bash
pytest \
  tests/test_self_improvement_packets.py \
  tests/test_self_improvement_agent.py \
  tests/test_self_improvement_cli.py \
  tests/test_release_management.py \
  tests/test_deploy_release_gates.py -q
```

Run existing bridge/reasoning checks after touching bridge-adjacent behavior:

```bash
pytest \
  tests/test_reasoning_runtime_agent_bridge.py \
  tests/test_mobile_capture_compose.py \
  tests/test_conversation_os.py -k "capture_host_requires_basic_auth or capture_host_fails_closed or restart_cloudflared" -q
```

Run frontend checks after UI/UX packets are implemented:

```bash
cd product/thought_capture_pwa
npm test -- --run
npm run build
npm audit --omit=dev
```

Run deployment candidate dry run:

```bash
python3 tools/inner_world_release.py candidate --release-id self-improve-verification --dry-run
```

---

## Rollout Strategy

1. **Local proposal-only:** packet creation and release candidate dry-runs only.
2. **Workboard attached:** packets can create durable workboard tasks, but no automatic patching.
3. **Patch preparation:** agent can propose file changes through Codex execution, still no deploy.
4. **Gate-controlled staging:** release gate reports become mandatory for staging-like deploys.
5. **Gate-controlled production:** deploy scripts require release gate reports by default.
6. **Rollback exercised:** every production deploy has a previous-release rollback dry-run.

---

## Residual Risks

- Agent packet quality can be inconsistent. The deterministic validator and fallback must remain permanent.
- Release fingerprints do not by themselves snapshot every remote dependency. The deploy scripts need explicit remote-state capture before production promotion.
- A dirty worktree can still be deployed if manually bypassed. The gate report should record this and make the bypass visible.
- Prompt and behavior changes are hard to test with normal unit tests. Golden examples and trace inspection are mandatory for agent behavior changes.
- The first rollback implementation is a dry run. Actual rollback execution should be implemented only after manifests and snapshots prove stable.
