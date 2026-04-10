"""
Parse structured agent state updates from LLM responses.

Models are instructed to append a <state>...</state> block containing JSON.
If parsing fails, callers may fall back to keyword heuristics.
"""

from __future__ import annotations

import json
import re
from typing import Any

_STATE_BLOCK = re.compile(r"<state>\s*([\s\S]*?)\s*</state>", re.IGNORECASE)


def extract_state_json_block(raw_response: str) -> str | None:
    m = _STATE_BLOCK.search(raw_response or "")
    if not m:
        return None
    return m.group(1).strip()


def parse_state_payload(
    payload: dict[str, Any],
    *,
    support_level: float,
    resistance_level: float,
    workload_stress: float,
    belief_posture: str,
) -> tuple[float, float, float, str, bool]:
    """
    Returns (support, resistance, workload, posture, perceived_conflict).
    Missing keys reuse previous scalar values; posture defaults to previous if absent.
    """
    def _f(key: str, prev: float) -> float:
        v = payload.get(key)
        if isinstance(v, bool) or v is None:
            return prev
        try:
            return float(v)
        except (TypeError, ValueError):
            return prev

    s = _f("support_level", support_level)
    r = _f("resistance_level", resistance_level)
    w = _f("workload_stress", workload_stress)
    posture = payload.get("belief_posture")
    if not isinstance(posture, str) or not posture.strip():
        posture = belief_posture
    else:
        posture = posture.strip()

    conflict = payload.get("perceived_conflict")
    if isinstance(conflict, bool):
        perceived = conflict
    else:
        perceived = r > s + 0.05

    return (s, r, w, posture, perceived)


def try_parse_state_from_response(
    raw_response: str,
    *,
    support_level: float,
    resistance_level: float,
    workload_stress: float,
    belief_posture: str,
) -> tuple[float, float, float, str, bool] | None:
    block = extract_state_json_block(raw_response)
    if not block:
        return None
    try:
        data = json.loads(block)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    return parse_state_payload(
        data,
        support_level=support_level,
        resistance_level=resistance_level,
        workload_stress=workload_stress,
        belief_posture=belief_posture,
    )
