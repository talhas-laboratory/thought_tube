from __future__ import annotations

from typing import Dict


MODULE_ID = "kernel.reasoning.judgment"
CONTRACT_VERSION = "1.0"
PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "classify_run",
)
__all__ = list(PUBLIC_API)


def classify_run(packet: Dict) -> Dict:
    reports = packet.get("conscious_articulation", {}).get("evaluation_reports", {})
    confidence = reports.get("confidence_report", {}).get("confidence", 0.0)
    novelty = reports.get("relevance_report", {}).get("novelty", 0.0)
    relevance = reports.get("relevance_report", {}).get("relevance", 0.0)
    fidelity = reports.get("fidelity_report", {}).get("status", "fail")
    genericity = reports.get("genericity_report", {}).get("status", "fail")
    review_status = packet.get("memory_commit", {}).get("review_status", "needs_human_review")

    evidence_status = "grounded" if fidelity == "pass" and confidence >= 0.7 else "speculative"
    approved = review_status == "approved_for_surface"
    return {
        "approved": approved,
        "review_status": review_status,
        "evidence_status": evidence_status,
        "confidence_score": round(confidence, 2),
        "novelty_score": round(novelty, 2),
        "relevance_score": round(relevance, 2),
        "fidelity_status": fidelity,
        "genericity_status": genericity,
    }
