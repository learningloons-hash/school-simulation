"""Memory context diagnostics report (senna-iter-45)."""

from __future__ import annotations

from typing import Any


def build_memory_context_report_json(bundle: dict[str, Any] | None) -> dict[str, Any]:
    if not bundle:
        raise ValueError("export bundle is empty")
    summary = bundle.get("memory_context_summary")
    if not isinstance(summary, dict):
        raise ValueError("export bundle has no memory_context_summary")
    log = bundle.get("memory_context_log") or []
    return {
        "memory_context_summary": summary,
        "memory_context_log_count": len(log),
    }
