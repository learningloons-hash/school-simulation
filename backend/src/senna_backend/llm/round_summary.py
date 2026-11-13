"""
Deterministic per-round context summary — no LLM call.

Builds a compact structured block from agent turns already in the DB:
  [Round N — <policy_event>]
  AgentName: support=0.72, resistance=0.21, posture=cautiously_supportive — "Opening snippet…"
  ...

This block is injected into subsequent rounds instead of growing raw peer history,
keeping per-call prompt size O(1) regardless of total rounds.
"""

from __future__ import annotations

import json
import re

_STATE_BLOCK = re.compile(r"<state>\s*([\s\S]*?)\s*</state>", re.IGNORECASE)
_STATE_WRAPPER = re.compile(r"<state>\s*[\s\S]*?\s*</state>", re.IGNORECASE)


def _extract_state(raw_response: str) -> dict:
    m = _STATE_BLOCK.search(raw_response or "")
    if not m:
        return {}
    try:
        return json.loads(m.group(1).strip())
    except Exception:
        return {}


def _strip_state(text: str) -> str:
    return _STATE_WRAPPER.sub("", text or "").strip()


def build_round_summary(
    *,
    round_number: int,
    policy_event: str,
    turns: list[dict],
    snippet_chars: int = 80,
) -> str:
    """
    Args:
        turns: list of dicts with keys agent_name, raw_response (as returned by get_turns_for_round).
        snippet_chars: max chars of cleaned response text to include per agent.
    Returns:
        Multi-line string suitable for injecting into future prompts.
    """
    lines = [f"[Round {round_number} — {policy_event}]"]
    for turn in turns:
        name = turn.get("agent_name", "?")
        raw = turn.get("raw_response", "")
        state = _extract_state(raw)
        clean = _strip_state(raw)
        snippet = clean[:snippet_chars].replace("\n", " ")
        if len(clean) > snippet_chars:
            snippet += "…"
        sup = state.get("support_level")
        res = state.get("resistance_level")
        posture = state.get("belief_posture", "?")
        sup_s = f"{float(sup):.2f}" if isinstance(sup, (int, float)) else "?"
        res_s = f"{float(res):.2f}" if isinstance(res, (int, float)) else "?"
        lines.append(f"{name}: support={sup_s}, resistance={res_s}, posture={posture} — \"{snippet}\"")
    return "\n".join(lines)
