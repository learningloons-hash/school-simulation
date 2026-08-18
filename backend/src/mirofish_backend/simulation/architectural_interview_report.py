"""JSON report builder for post-run architectural interview (senna-iter-47)."""

from __future__ import annotations

from typing import Any

from mirofish_backend.diagnostics.architectural_interview import summarize_interview_results


def build_architectural_interview_report_json(bundle: dict[str, Any] | None) -> dict[str, Any]:
    if bundle is None:
        raise ValueError("export bundle is required")
    responses = bundle.get("architectural_interview_responses") or []
    scores = bundle.get("architectural_interview_scores") or []
    summary = summarize_interview_results(responses, scores)
    return {
        "simulation_id": (bundle.get("run") or {}).get("id"),
        "instrument": "architectural_interview",
        "purpose": "memory/context component diagnostic (not simulation validity)",
        **summary,
    }
