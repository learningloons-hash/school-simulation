"""Version-controlled prompts for memory importance scoring (senna-iter-49)."""

from __future__ import annotations

import json
from typing import Any

IMPORTANCE_PROMPT_VERSION = "v1"


def build_single_turn_importance_prompt(
    *,
    prompt_version: str,
    round_number: int,
    turn_index: int,
    agent_name: str,
    agent_role: str,
    raw_response: str,
) -> tuple[str, str]:
    """Return (system, user) messages for a single-turn importance score."""
    system = (
        "You are a memory-importance scorer for a multi-agent simulation. "
        "Rate how important this agent utterance would be for the speaker to recall later "
        "(1 = trivial / forgettable, 10 = pivotal / must remember). "
        f"Prompt version: {prompt_version}."
    )
    user = "\n".join(
        [
            f"Round {round_number}, turn {turn_index}",
            f"Speaker: {agent_name} ({agent_role})",
            "",
            "Utterance:",
            raw_response.strip() or "(empty)",
            "",
            "Respond with exactly one block:",
            "<importance_score>",
            json.dumps({"score": 5, "rationale": "brief reason"}, indent=2),
            "</importance_score>",
            "Replace score with an integer 1–10.",
        ]
    )
    return system, user


def build_batch_importance_prompt(
    *,
    prompt_version: str,
    round_number: int,
    turns: list[dict[str, Any]],
) -> tuple[str, str]:
    """Return (system, user) for scoring all turns in a round in one call."""
    system = (
        "You are a memory-importance scorer for a multi-agent simulation. "
        "For each listed turn, rate how important the utterance would be for the speaker "
        "to recall later (1 = trivial, 10 = pivotal). "
        f"Prompt version: {prompt_version}."
    )
    lines = [f"Round {round_number} — score every turn below.", ""]
    for t in turns:
        lines.append(
            f"- turn_id={t['turn_id']} | {t.get('agent_name', '?')} ({t.get('agent_role', '?')}) "
            f"turn_index={t.get('turn_index', '?')}"
        )
        lines.append(f"  utterance: {(t.get('raw_response') or '').strip()[:2000]}")
        lines.append("")
    example = {
        "turn_scores": [{"turn_id": turns[0]["turn_id"], "score": 5}] if turns else [],
    }
    lines.extend(
        [
            "Respond with exactly one block listing every turn_id:",
            "<importance_score>",
            json.dumps(example, indent=2),
            "</importance_score>",
        ]
    )
    return system, "\n".join(lines)
