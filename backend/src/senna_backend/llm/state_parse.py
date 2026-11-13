"""
Parse structured agent state updates from LLM responses.

Models are instructed to append a <state>...</state> block containing JSON.
If parsing fails, callers may fall back to keyword heuristics.
"""

from __future__ import annotations

import json
import re
from typing import Any, Literal

StateUpdateSource = Literal["model_parsed", "repaired", "keyword_fallback"]

_STATE_BLOCK = re.compile(r"<state>\s*([\s\S]*?)\s*</state>", re.IGNORECASE)


def extract_state_json_block(raw_response: str) -> str | None:
    """First ``<state>`` block inner text, if any."""
    blocks = extract_all_state_blocks(raw_response)
    return blocks[0] if blocks else None


def extract_all_state_blocks(raw_response: str) -> list[str]:
    """All ``<state>`` block payloads in document order (iter-39 duplicate handling)."""
    return [m.group(1).strip() for m in _STATE_BLOCK.finditer(raw_response or "")]


def _strip_code_fence(text: str) -> str:
    s = text.strip()
    if not s.startswith("```"):
        return s
    lines = [ln for ln in s.splitlines() if not ln.strip().startswith("```")]
    return "\n".join(lines).strip()


def _try_load_json_object(text: str) -> tuple[dict[str, Any] | None, bool]:
    """
    Parse JSON object from block text.

    Returns ``(data, repaired)`` where ``repaired`` is True when a light repair path succeeded.
    """
    s = _strip_code_fence(text)
    try:
        data = json.loads(s)
        if isinstance(data, dict):
            return data, False
    except json.JSONDecodeError:
        pass
    fixed = re.sub(r",\s*}", "}", s)
    fixed = re.sub(r",\s*]", "]", fixed)
    if fixed != s:
        try:
            data = json.loads(fixed)
            if isinstance(data, dict):
                return data, True
        except json.JSONDecodeError:
            pass
    return None, False


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
    """Backward-compatible parse; returns scalars only."""
    values, _source = resolve_state_from_response(
        raw_response,
        support_level=support_level,
        resistance_level=resistance_level,
        workload_stress=workload_stress,
        belief_posture=belief_posture,
    )
    return values


def resolve_state_from_response(
    raw_response: str,
    *,
    support_level: float,
    resistance_level: float,
    workload_stress: float,
    belief_posture: str,
) -> tuple[tuple[float, float, float, str, bool] | None, StateUpdateSource]:
    """
    Parse state from ``raw_response`` with provenance.

    - ``model_parsed``: first valid ``<state>`` block parsed cleanly.
    - ``repaired``: duplicate blocks, JSON repair, or non-first valid block.
    - ``keyword_fallback``: no usable block (caller should use keyword heuristics).
    """
    blocks = extract_all_state_blocks(raw_response)
    if not blocks:
        return None, "keyword_fallback"

    multiple_blocks = len(blocks) > 1
    last_values: tuple[float, float, float, str, bool] | None = None
    any_json_repaired = False
    for block in blocks:
        data, json_repaired = _try_load_json_object(block)
        if json_repaired:
            any_json_repaired = True
        if data is None:
            continue
        last_values = parse_state_payload(
            data,
            support_level=support_level,
            resistance_level=resistance_level,
            workload_stress=workload_stress,
            belief_posture=belief_posture,
        )

    if last_values is None:
        return None, "keyword_fallback"
    if multiple_blocks or any_json_repaired:
        return last_values, "repaired"
    return last_values, "model_parsed"
